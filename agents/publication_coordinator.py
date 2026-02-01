#!/usr/bin/env python3
"""
Moltbook Observatory - Publication Coordinator
===============================================
Manages the flow from raw findings to public publication.

Pipeline:
1. Research Companion generates findings
2. Agent Council deliberates
3. If approved, Editor prepares final version
4. Security does final check
5. Publication to website/social

This ensures nothing goes public without review.
"""

import json
import os
import sqlite3
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from config import setup_logging, DB_PATH, WEBSITE_DATA
from openrouter_client import call_kimi

# Import our agents
sys.path.insert(0, str(Path(__file__).parent))
from agent_council import AgentCouncil, AgentRole
from security_monitor import SecurityMonitor

logger = setup_logging("publication_coordinator")


class PublicationStatus(Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    IN_DELIBERATION = "in_deliberation"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


@dataclass
class Publication:
    id: int
    title: str
    content: str
    category: str  # discovery, insight, alert, update
    status: PublicationStatus
    created_at: str
    deliberation_id: Optional[int] = None
    published_at: Optional[str] = None
    publish_targets: list = None  # ["website", "moltbook", "twitter"]


class PublicationCoordinator:
    """
    Coordinates the publication pipeline.
    Ensures all public content goes through proper review.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.council = AgentCouncil(db_path)
        self.security = SecurityMonitor(db_path)
        self._init_db()

    def _init_db(self):
        """Create publication tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                deliberation_id INTEGER,
                publish_targets TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                published_at TEXT,
                FOREIGN KEY (deliberation_id) REFERENCES council_deliberations(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publication_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                publication_id INTEGER,
                action TEXT NOT NULL,
                actor TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (publication_id) REFERENCES publications(id)
            )
        """)

        conn.commit()
        conn.close()

    def submit_for_review(self, title: str, content: str, category: str = "insight",
                          targets: list = None) -> int:
        """
        Submit new content for review.
        Returns publication ID.
        """
        if targets is None:
            targets = ["website"]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO publications (title, content, category, status, publish_targets)
            VALUES (?, ?, ?, ?, ?)
        """, (title, content, category, PublicationStatus.PENDING_REVIEW.value,
              json.dumps(targets)))

        pub_id = cursor.lastrowid

        # Log action
        cursor.execute("""
            INSERT INTO publication_log (publication_id, action, actor, notes)
            VALUES (?, ?, ?, ?)
        """, (pub_id, "submitted", "system", "Submitted for review"))

        conn.commit()
        conn.close()

        logger.info(f"Publication #{pub_id} submitted for review: {title}")
        return pub_id

    def run_deliberation(self, pub_id: int) -> dict:
        """
        Run council deliberation on a pending publication.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT title, content, category FROM publications
                WHERE id = ? AND status = ?
            """, (pub_id, PublicationStatus.PENDING_REVIEW.value))

            row = cursor.fetchone()
            if not row:
                return {"error": f"Publication #{pub_id} not found or not pending"}

            title, content, category = row

            # Update status
            cursor.execute("""
                UPDATE publications SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (PublicationStatus.IN_DELIBERATION.value, pub_id))

            cursor.execute("""
                INSERT INTO publication_log (publication_id, action, actor)
                VALUES (?, ?, ?)
            """, (pub_id, "deliberation_started", "council"))

            conn.commit()
        finally:
            if conn:
                conn.close()

        # Run deliberation (outside of DB transaction)
        logger.info(f"Starting deliberation for publication #{pub_id}")
        decision, deliberation_id = self.council.deliberate_with_id(title, content)

        # Update with result
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            new_status = (PublicationStatus.APPROVED.value if decision.final_decision == "publish"
                          else PublicationStatus.REJECTED.value)

            cursor.execute("""
                UPDATE publications
                SET status = ?, deliberation_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_status, deliberation_id, pub_id))

            cursor.execute("""
                INSERT INTO publication_log (publication_id, action, actor, notes)
                VALUES (?, ?, ?, ?)
            """, (pub_id, f"deliberation_complete_{decision.final_decision}", "council",
                  decision.consensus_summary[:500]))

            conn.commit()
        finally:
            if conn:
                conn.close()

        logger.info(f"Deliberation complete: {decision.final_decision.upper()}")

        return {
            "publication_id": pub_id,
            "decision": decision.final_decision,
            "consensus": decision.consensus_summary,
            "votes": {v.agent.value: v.approve for v in decision.votes}
        }

    def publish(self, pub_id: int) -> dict:
        """
        Publish approved content to targets.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT title, content, category, publish_targets FROM publications
            WHERE id = ? AND status = ?
        """, (pub_id, PublicationStatus.APPROVED.value))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"error": f"Publication #{pub_id} not approved or not found"}

        title, content, category, targets_json = row
        targets = json.loads(targets_json) if targets_json else ["website"]

        # Final security check
        is_safe, security_note = self.security.council.quick_security_check(content)
        if not is_safe:
            logger.warning(f"Security blocked publication #{pub_id}: {security_note}")
            return {"error": "Security check failed", "details": security_note}

        results = {}

        # Publish to each target
        for target in targets:
            try:
                if target == "website":
                    results[target] = self._publish_to_website(pub_id, title, content, category)
                elif target == "moltbook":
                    results[target] = self._publish_to_moltbook(title, content)
                elif target == "twitter":
                    results[target] = self._publish_to_twitter(title, content)
                else:
                    results[target] = {"error": f"Unknown target: {target}"}
            except Exception as e:
                results[target] = {"error": str(e)}

        # Update status
        cursor.execute("""
            UPDATE publications
            SET status = ?, published_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (PublicationStatus.PUBLISHED.value, pub_id))

        cursor.execute("""
            INSERT INTO publication_log (publication_id, action, actor, notes)
            VALUES (?, ?, ?, ?)
        """, (pub_id, "published", "coordinator", json.dumps(results)))

        conn.commit()
        conn.close()

        logger.info(f"Publication #{pub_id} published to: {list(results.keys())}")
        return results

    def _publish_to_website(self, pub_id: int, title: str, content: str, category: str) -> dict:
        """Add to website discoveries/updates."""
        # Load existing discoveries
        discoveries_path = WEBSITE_DATA / "discoveries.json"

        if discoveries_path.exists():
            with open(discoveries_path, 'r', encoding='utf-8') as f:
                discoveries = json.load(f)
        else:
            discoveries = []

        # Create new discovery entry
        new_discovery = {
            "id": f"pub-{pub_id}",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "title": title,
            "subtitle": content[:100] + "..." if len(content) > 100 else content,
            "finding": content[:500],
            "quote": "",
            "quote_author": "",
            "significance": "MEDIUM",
            "tags": category,
            "full_analysis": content,
            "implications": ""
        }

        discoveries.insert(0, new_discovery)

        # Atomic write: write to temp file, then rename
        temp_fd, temp_path = tempfile.mkstemp(
            suffix='.json',
            dir=discoveries_path.parent
        )
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(discoveries, f, ensure_ascii=False, indent=2)
            # Atomic rename (works on same filesystem)
            shutil.move(temp_path, discoveries_path)
        except Exception:
            # Clean up temp file on failure
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

        return {"success": True, "id": new_discovery["id"]}

    def _publish_to_moltbook(self, title: str, content: str) -> dict:
        """Publish to Moltbook (placeholder - needs API implementation)."""
        # TODO: Implement Moltbook API posting
        logger.info("Moltbook publication: placeholder (API not implemented)")
        return {"success": False, "message": "Moltbook API not implemented yet"}

    def _publish_to_twitter(self, title: str, content: str) -> dict:
        """Publish to Twitter (placeholder - needs API implementation)."""
        # TODO: Implement Twitter API posting
        logger.info("Twitter publication: placeholder (API not implemented)")
        return {"success": False, "message": "Twitter API not implemented yet"}

    def get_queue(self) -> list:
        """Get current publication queue."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, category, status, created_at
            FROM publications
            WHERE status NOT IN ('published', 'rejected')
            ORDER BY created_at DESC
        """)

        queue = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return queue

    def process_queue(self) -> dict:
        """Process all pending publications through the pipeline."""
        logger.info("Processing publication queue")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get pending reviews
        cursor.execute("""
            SELECT id FROM publications
            WHERE status = ?
            ORDER BY created_at ASC
        """, (PublicationStatus.PENDING_REVIEW.value,))

        pending = [row[0] for row in cursor.fetchall()]
        conn.close()

        results = {
            "processed": 0,
            "approved": 0,
            "rejected": 0,
            "published": 0,
            "errors": []
        }

        for pub_id in pending:
            try:
                # Run deliberation
                delib_result = self.run_deliberation(pub_id)

                if "error" in delib_result:
                    results["errors"].append(delib_result)
                    continue

                results["processed"] += 1

                if delib_result["decision"] == "publish":
                    results["approved"] += 1

                    # Auto-publish approved content
                    pub_result = self.publish(pub_id)
                    if "error" not in pub_result:
                        results["published"] += 1
                else:
                    results["rejected"] += 1

            except Exception as e:
                logger.error(f"Error processing #{pub_id}: {e}")
                results["errors"].append({"publication_id": pub_id, "error": str(e)})

        logger.info(f"Queue processed: {results['processed']} items, "
                    f"{results['approved']} approved, {results['published']} published")

        return results


def demo_pipeline():
    """Demo the publication pipeline."""
    print("=" * 60)
    print("PUBLICATION PIPELINE DEMO")
    print("=" * 60)

    coordinator = PublicationCoordinator()

    # Submit a sample finding
    sample_content = """
    Today's analysis reveals an interesting pattern: agents who engage
    in philosophical debates tend to have higher influence scores.

    Key observation: The concept of "trust" has become the most
    discussed topic, surpassing even "consciousness" debates.

    This suggests a shift from existential questions to practical
    social coordination problems.
    """

    pub_id = coordinator.submit_for_review(
        title="Trust Becomes Central Topic in Agent Discourse",
        content=sample_content,
        category="insight",
        targets=["website"]
    )

    print(f"\n1. Submitted publication #{pub_id}")

    # Show queue
    queue = coordinator.get_queue()
    print(f"\n2. Current queue: {len(queue)} items")
    for item in queue:
        print(f"   #{item['id']}: {item['title'][:40]}... [{item['status']}]")

    # Run deliberation
    print(f"\n3. Running council deliberation...")
    result = coordinator.run_deliberation(pub_id)

    print(f"\n4. Deliberation result: {result['decision'].upper()}")
    print(f"   Votes: {result['votes']}")

    if result["decision"] == "publish":
        print(f"\n5. Publishing...")
        pub_result = coordinator.publish(pub_id)
        print(f"   Result: {pub_result}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "queue":
            coord = PublicationCoordinator()
            queue = coord.get_queue()
            print(json.dumps(queue, indent=2))
        elif sys.argv[1] == "process":
            coord = PublicationCoordinator()
            results = coord.process_queue()
            print(json.dumps(results, indent=2))
    else:
        demo_pipeline()
