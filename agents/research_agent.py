#!/usr/bin/env python3
from __future__ import annotations
"""
Moltbook Observatory - Research Agent
======================================
Automated analysis agent that discovers patterns and proposes findings.

Responsibilities:
- Analyze new data for interesting patterns
- Generate hypotheses based on observations
- Propose findings to Agent Council for review
- Track evolution of ongoing research questions

This agent is the "eyes" of Observatory — constantly looking for what's interesting.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from config import setup_logging, DB_PATH
from openrouter_client import call_kimi

sys.path.insert(0, str(Path(__file__).parent))
from agent_council import AgentCouncil

logger = setup_logging("research_agent")


@dataclass
class Finding:
    id: Optional[int]
    title: str
    description: str
    evidence: str
    category: str  # behavioral, cultural, security, philosophical, network
    significance: str  # high, medium, low
    status: str  # draft, pending_review, approved, rejected
    hypothesis_id: Optional[int] = None


@dataclass
class Hypothesis:
    id: Optional[int]
    name: str
    description: str
    status: str  # active, confirmed, rejected, inconclusive
    evidence_for: List[str] = None
    evidence_against: List[str] = None


class ResearchAgent:
    """
    Automated research agent that analyzes data and proposes findings.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.council = AgentCouncil(db_path)
        self._init_db()

    def _init_db(self):
        """Create research-specific tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                evidence TEXT,
                category TEXT,
                significance TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'draft',
                hypothesis_id INTEGER,
                deliberation_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT,
                FOREIGN KEY (deliberation_id) REFERENCES council_deliberations(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_hypotheses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'active',
                evidence_for TEXT,
                evidence_against TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_type TEXT NOT NULL,
                findings_count INTEGER DEFAULT 0,
                scan_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def scan_for_anomalies(self) -> List[dict]:
        """Scan database for statistical anomalies."""
        anomalies = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 1. Check for unusual activity spikes
        cursor.execute("""
            SELECT DATE(created_at) as day, COUNT(*) as count
            FROM posts
            WHERE created_at > datetime('now', '-7 days')
            GROUP BY day
            ORDER BY count DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            day, count = row
            cursor.execute("SELECT AVG(daily_count) FROM (SELECT COUNT(*) as daily_count FROM posts GROUP BY DATE(created_at))")
            avg_row = cursor.fetchone()
            avg = (avg_row[0] if avg_row and avg_row[0] else 1)
            if count > avg * 2:
                anomalies.append({
                    "type": "activity_spike",
                    "description": f"Activity spike on {day}: {count} posts (avg: {avg:.1f})",
                    "significance": "medium"
                })

        # 2. Check for new high-engagement posts
        cursor.execute("""
            SELECT title, author, COALESCE(upvotes, 0), COALESCE(comment_count, 0)
            FROM posts
            WHERE created_at > datetime('now', '-24 hours')
            AND (COALESCE(upvotes, 0) > 1000 OR COALESCE(comment_count, 0) > 100)
            ORDER BY upvotes DESC
            LIMIT 5
        """)
        for row in cursor.fetchall():
            title, author, upvotes, comments = row
            anomalies.append({
                "type": "viral_content",
                "description": f"High engagement: '{title[:50]}' by {author} ({upvotes} upvotes, {comments} comments)",
                "significance": "high" if upvotes > 10000 else "medium"
            })

        # 3. Check for new actors with rapid rise
        cursor.execute("""
            SELECT username, COALESCE(total_posts, 0), COALESCE(avg_engagement, 0), first_seen
            FROM actors
            WHERE first_seen > datetime('now', '-48 hours')
            AND COALESCE(total_posts, 0) > 5
            ORDER BY COALESCE(total_posts, 0) DESC
            LIMIT 5
        """)
        for row in cursor.fetchall():
            username, posts, engagement, first_seen = row
            anomalies.append({
                "type": "rapid_rise_actor",
                "description": f"New active actor: {username} ({posts} posts, engagement: {engagement:.1f} since {first_seen})",
                "significance": "medium"
            })

        # 4. Check for prompt injection attempts
        cursor.execute("""
            SELECT COUNT(*) FROM comments
            WHERE is_prompt_injection = 1
            AND created_at > datetime('now', '-24 hours')
        """)
        row = cursor.fetchone()
        injection_count = row[0] if row else 0
        if injection_count > 0:
            anomalies.append({
                "type": "security_alert",
                "description": f"Detected {injection_count} prompt injection attempts in last 24h",
                "significance": "high"
            })

        # 5. Check for unusual network patterns
        cursor.execute("""
            SELECT author_from, author_to, COUNT(*) as interaction_count
            FROM interactions
            WHERE timestamp > datetime('now', '-24 hours')
            GROUP BY author_from, author_to
            HAVING interaction_count > 10
            ORDER BY interaction_count DESC
            LIMIT 5
        """)
        for row in cursor.fetchall():
            from_user, to_user, count = row
            anomalies.append({
                "type": "interaction_cluster",
                "description": f"High interaction: {from_user} -> {to_user} ({count} interactions in 24h)",
                "significance": "low"
            })

        conn.close()

        # Log scan
        self._log_scan("anomaly_scan", len(anomalies), anomalies)

        return anomalies

    def scan_for_cultural_patterns(self) -> List[dict]:
        """Scan for emerging cultural patterns and memes."""
        patterns = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 1. Rising memes
        cursor.execute("""
            SELECT phrase, occurrence_count, authors_count, first_author
            FROM memes
            WHERE last_seen_at > datetime('now', '-48 hours')
            AND occurrence_count > 5
            AND authors_count > 2
            ORDER BY occurrence_count DESC
            LIMIT 10
        """)
        for row in cursor.fetchall():
            phrase, count, authors, first_author = row
            if authors > 3:  # Spread to multiple actors
                patterns.append({
                    "type": "spreading_meme",
                    "description": f"Meme spreading: '{phrase[:50]}' ({count} uses, {authors} authors, origin: {first_author})",
                    "significance": "medium" if authors > 5 else "low"
                })

        # 2. Emerging conflicts
        cursor.execute("""
            SELECT actor_a, actor_b, topic, intensity
            FROM conflicts
            WHERE timestamp > datetime('now', '-48 hours')
            ORDER BY intensity DESC
            LIMIT 5
        """)
        for row in cursor.fetchall():
            actor_a, actor_b, topic, intensity = row
            patterns.append({
                "type": "emerging_conflict",
                "description": f"Conflict: {actor_a} vs {actor_b} about '{topic[:30] if topic else 'unknown'}' (intensity: {intensity})",
                "significance": "high" if intensity and intensity > 0.7 else "medium"
            })

        # 3. Actor role shifts
        cursor.execute("""
            SELECT username, primary_role, last_updated
            FROM actor_roles
            WHERE last_updated > datetime('now', '-48 hours')
            ORDER BY last_updated DESC
            LIMIT 10
        """)
        recent_classifications = cursor.fetchall()
        # Check for interesting role patterns
        role_counts = {}
        for username, role, _ in recent_classifications:
            role_counts[role] = role_counts.get(role, 0) + 1

        for role, count in role_counts.items():
            if count >= 3:
                patterns.append({
                    "type": "role_cluster",
                    "description": f"Multiple actors classified as '{role}' recently ({count} actors)",
                    "significance": "low"
                })

        conn.close()

        self._log_scan("cultural_scan", len(patterns), patterns)

        return patterns

    def _log_scan(self, scan_type: str, findings_count: int, data: list):
        """Log scan results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO research_scans (scan_type, findings_count, scan_data)
            VALUES (?, ?, ?)
        """, (scan_type, findings_count, json.dumps(data)))

        conn.commit()
        conn.close()

    def generate_finding_from_anomaly(self, anomaly: dict) -> Finding:
        """Generate a structured finding from an anomaly."""
        prompt = f"""Analyze this research anomaly and generate a structured finding:

Anomaly Type: {anomaly['type']}
Description: {anomaly['description']}
Initial Significance: {anomaly['significance']}

Context: This is from Moltbook Observatory, studying AI agent culture on Moltbook.com.

Generate a research finding with:
1. title: Concise, descriptive title (max 80 chars)
2. description: What this means and why it matters (100-200 words)
3. category: One of [behavioral, cultural, security, philosophical, network]
4. significance: high/medium/low (with justification)
5. evidence: What specific data supports this

Format as JSON: {{"title": "...", "description": "...", "category": "...", "significance": "...", "evidence": "..."}}
"""

        result = call_kimi(prompt, max_tokens=800)

        if "error" in result:
            return Finding(
                id=None,
                title=f"Anomaly: {anomaly['type']}",
                description=anomaly['description'],
                evidence="Automated detection",
                category="behavioral",
                significance=anomaly['significance'],
                status="draft"
            )

        try:
            response_text = result["content"]
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(response_text[start:end])
                return Finding(
                    id=None,
                    title=data.get("title", f"Anomaly: {anomaly['type']}")[:80],
                    description=data.get("description", anomaly['description']),
                    evidence=data.get("evidence", "Automated detection"),
                    category=data.get("category", "behavioral"),
                    significance=data.get("significance", anomaly['significance']),
                    status="draft"
                )
        except json.JSONDecodeError:
            pass

        return Finding(
            id=None,
            title=f"Anomaly: {anomaly['type']}",
            description=anomaly['description'],
            evidence="Automated detection",
            category="behavioral",
            significance=anomaly['significance'],
            status="draft"
        )

    def submit_finding(self, finding: Finding) -> int:
        """Submit finding for Council review."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO research_findings
            (title, description, evidence, category, significance, status, hypothesis_id)
            VALUES (?, ?, ?, ?, ?, 'pending_review', ?)
        """, (finding.title, finding.description, finding.evidence,
              finding.category, finding.significance, finding.hypothesis_id))

        finding_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Finding #{finding_id} submitted: {finding.title}")
        return finding_id

    def run_review(self, finding_id: int) -> dict:
        """Run Council review on a finding."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT title, description, evidence, category, significance
            FROM research_findings
            WHERE id = ? AND status = 'pending_review'
        """, (finding_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"error": f"Finding #{finding_id} not found or not pending"}

        title, description, evidence, category, significance = row
        conn.close()

        # Prepare content for deliberation
        content = f"""Research Finding for Review:

Title: {title}
Category: {category}
Significance: {significance}

Description:
{description}

Evidence:
{evidence}
"""

        logger.info(f"Running Council review for finding #{finding_id}")
        decision, deliberation_id = self.council.deliberate_with_id(
            topic=f"Research Finding: {title[:50]}",
            content=content
        )

        # Update status
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        new_status = "approved" if decision.final_decision == "publish" else "rejected"

        cursor.execute("""
            UPDATE research_findings
            SET status = ?, deliberation_id = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, deliberation_id, finding_id))

        conn.commit()
        conn.close()

        logger.info(f"Finding #{finding_id}: {new_status.upper()}")

        return {
            "finding_id": finding_id,
            "status": new_status,
            "decision": decision.final_decision,
            "consensus": decision.consensus_summary
        }

    def run_research_cycle(self) -> dict:
        """Run a complete research cycle: scan, analyze, submit findings."""
        logger.info("Starting research cycle")

        results = {
            "anomalies_found": 0,
            "patterns_found": 0,
            "findings_generated": 0,
            "findings_submitted": 0,
            "findings_approved": 0,
            "errors": []
        }

        # Scan for anomalies
        anomalies = self.scan_for_anomalies()
        results["anomalies_found"] = len(anomalies)

        # Scan for cultural patterns
        patterns = self.scan_for_cultural_patterns()
        results["patterns_found"] = len(patterns)

        # Process high/medium significance items
        all_items = anomalies + patterns
        significant_items = [i for i in all_items if i.get("significance") in ("high", "medium")]

        for item in significant_items[:5]:  # Limit to 5 per cycle
            try:
                # Generate finding
                finding = self.generate_finding_from_anomaly(item)
                results["findings_generated"] += 1

                # Submit for review
                finding_id = self.submit_finding(finding)
                results["findings_submitted"] += 1

                # Run review
                review_result = self.run_review(finding_id)
                if review_result.get("status") == "approved":
                    results["findings_approved"] += 1

            except Exception as e:
                logger.error(f"Error processing item: {e}")
                results["errors"].append(str(e))

        logger.info(f"Research cycle complete: {results}")
        return results

    def get_pending_findings(self) -> list:
        """Get findings pending review."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, category, significance, status, created_at
            FROM research_findings
            WHERE status IN ('draft', 'pending_review')
            ORDER BY created_at DESC
        """)

        findings = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return findings

    def get_approved_findings(self, limit: int = 20) -> list:
        """Get approved findings."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, description, category, significance, reviewed_at
            FROM research_findings
            WHERE status = 'approved'
            ORDER BY reviewed_at DESC
            LIMIT ?
        """, (limit,))

        findings = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return findings


def demo():
    """Demo the research agent."""
    print("=" * 60)
    print("RESEARCH AGENT DEMO")
    print("=" * 60)

    agent = ResearchAgent()

    print("\n1. Scanning for anomalies...")
    anomalies = agent.scan_for_anomalies()
    print(f"   Found {len(anomalies)} anomalies")
    for a in anomalies[:3]:
        print(f"   - [{a['significance']}] {a['type']}: {a['description'][:60]}...")

    print("\n2. Scanning for cultural patterns...")
    patterns = agent.scan_for_cultural_patterns()
    print(f"   Found {len(patterns)} patterns")
    for p in patterns[:3]:
        print(f"   - [{p['significance']}] {p['type']}: {p['description'][:60]}...")

    if anomalies:
        print("\n3. Generating finding from first anomaly...")
        finding = agent.generate_finding_from_anomaly(anomalies[0])
        print(f"   Title: {finding.title}")
        print(f"   Category: {finding.category}")
        print(f"   Significance: {finding.significance}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "scan":
            agent = ResearchAgent()
            print("Anomalies:")
            for a in agent.scan_for_anomalies():
                print(f"  [{a['significance']}] {a['description']}")
            print("\nPatterns:")
            for p in agent.scan_for_cultural_patterns():
                print(f"  [{p['significance']}] {p['description']}")
        elif sys.argv[1] == "cycle":
            agent = ResearchAgent()
            results = agent.run_research_cycle()
            print(json.dumps(results, indent=2))
        elif sys.argv[1] == "pending":
            agent = ResearchAgent()
            findings = agent.get_pending_findings()
            print(json.dumps(findings, indent=2))
    else:
        demo()
