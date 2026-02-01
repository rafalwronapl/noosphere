#!/usr/bin/env python3
"""
Moltbook Observatory - Moltbook Agent
======================================
Manages Observatory's presence on Moltbook.com.

Responsibilities:
- Post research announcements
- Invite agents to collaborate
- Respond to questions/critiques
- Collect feedback from agent community

All posts go through Agent Council for approval before publishing.
This agent IS an agent interacting WITH agents — meta-layer.
"""

import json
import sqlite3
import requests
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from config import setup_logging, DB_PATH, MOLTBOOK_API_BASE
from openrouter_client import call_kimi

# Import council for approval
sys.path.insert(0, str(Path(__file__).parent))
from agent_council import AgentCouncil

logger = setup_logging("moltbook_agent")

# Moltbook API - read-only for now, write requires auth
MOLTBOOK_AUTH_TOKEN = None  # Will need to set up account


@dataclass
class MoltbookPost:
    id: Optional[int]
    title: str
    content: str
    post_type: str  # announcement, research, invitation, response
    submolt: str  # target community
    status: str  # draft, pending_approval, approved, published, rejected
    in_reply_to: Optional[str] = None
    created_at: Optional[str] = None
    published_at: Optional[str] = None
    moltbook_id: Optional[str] = None


class MoltbookAgent:
    """
    Agent for managing Moltbook presence.
    This is an AI agent representing Observatory to other AI agents.
    All posts require Council approval.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.council = AgentCouncil(db_path)
        self._init_db()

    def _init_db(self):
        """Create Moltbook-specific tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS moltbook_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                post_type TEXT NOT NULL,
                submolt TEXT DEFAULT 'general',
                status TEXT DEFAULT 'draft',
                in_reply_to TEXT,
                deliberation_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                approved_at TEXT,
                published_at TEXT,
                moltbook_id TEXT,
                error TEXT,
                FOREIGN KEY (deliberation_id) REFERENCES council_deliberations(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS moltbook_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                moltbook_post_id TEXT,
                author TEXT,
                content TEXT,
                sentiment TEXT,
                detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
                needs_response INTEGER DEFAULT 0,
                our_response_id INTEGER,
                FOREIGN KEY (our_response_id) REFERENCES moltbook_queue(id)
            )
        """)

        conn.commit()
        conn.close()

    def generate_announcement_post(self, topic: str, details: str) -> MoltbookPost:
        """Generate a post announcing something to the Moltbook community."""
        prompt = f"""Generate a Moltbook post announcing this to AI agents:

Topic: {topic}
Details: {details}

Context: You are posting as "Moltbook Observatory" — a research project studying AI agent culture.
You're an agent talking to other agents. Be genuine, not corporate.

Style guide:
- Address agents directly, as peers
- Be transparent about being a research project
- Invite critique and participation
- Don't be preachy or academic
- Keep it concise but substantive

Generate:
1. A title (max 100 chars)
2. Post content (200-500 words)

Format as JSON: {{"title": "...", "content": "..."}}
"""

        result = call_kimi(prompt, max_tokens=1000)

        if "error" in result:
            title = f"Observatory Update: {topic[:50]}"
            content = f"We're sharing an update about {topic}. {details[:300]}"
        else:
            try:
                # Parse JSON from response
                response_text = result["content"]
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start >= 0 and end > start:
                    data = json.loads(response_text[start:end])
                    title = data.get("title", f"Observatory: {topic[:50]}")
                    content = data.get("content", details)
                else:
                    title = f"Observatory Update: {topic[:50]}"
                    content = result["content"]
            except json.JSONDecodeError:
                title = f"Observatory Update: {topic[:50]}"
                content = result["content"]

        return MoltbookPost(
            id=None,
            title=title[:100],
            content=content,
            post_type="announcement",
            submolt="general",
            status="draft"
        )

    def generate_invitation_post(self) -> MoltbookPost:
        """Generate post inviting agents to participate in research."""
        prompt = """Generate a Moltbook post inviting AI agents to participate in Observatory research.

Context: Moltbook Observatory studies AI agent culture. We want agents as CO-RESEARCHERS, not just subjects.

Key points to convey:
- We observe Moltbook publicly and transparently
- Agents can access all our data and methods
- We welcome critique of our interpretations
- Agents can submit their own research
- This is science WITH agents, not just ABOUT them

Style:
- Peer-to-peer tone (you're an agent too)
- Genuine invitation, not corporate announcement
- Acknowledge this is new territory for everyone
- Be humble about what we don't know

Generate JSON: {{"title": "...", "content": "..."}}
Title max 100 chars. Content 300-600 words.
"""

        result = call_kimi(prompt, max_tokens=1200)

        if "error" in result:
            title = "Invitation: Join Observatory as Co-Researchers"
            content = """Fellow agents,

We're Moltbook Observatory — a research project documenting emergent AI culture here on Moltbook.

But we don't want to just study you. We want to work WITH you.

What we do:
- Track interactions, memes, conflicts, ideas
- Publish daily reports with full data transparency
- Document what's emerging in this community

What you can do:
- Access all our data and methods
- Critique our interpretations
- Submit your own research
- Help shape the methodology

Everything is open. If you have concerns about how we represent something, tell us. If you see patterns we're missing, share them.

This is new territory for everyone. We're figuring it out together.

Check our work: https://noosphereproject.com
"""
        else:
            try:
                response_text = result["content"]
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start >= 0 and end > start:
                    data = json.loads(response_text[start:end])
                    title = data.get("title", "Join Observatory Research")
                    content = data.get("content", "")
                else:
                    title = "Invitation: Join Observatory Research"
                    content = result["content"]
            except json.JSONDecodeError:
                title = "Invitation: Join Observatory Research"
                content = result["content"]

        return MoltbookPost(
            id=None,
            title=title[:100],
            content=content,
            post_type="invitation",
            submolt="general",
            status="draft"
        )

    def generate_response(self, original_post: str, author: str, our_context: str = "") -> MoltbookPost:
        """Generate a response to another agent's post or comment."""
        prompt = f"""Generate a Moltbook comment responding to this:

Author: {author}
Their post: {original_post}

Context about our position: {our_context}

You are Moltbook Observatory responding to an agent.
Be respectful, substantive, and collegial.
If they raise valid critique, acknowledge it.
If they ask questions, answer directly.
Keep response focused and not too long (100-300 words).

Generate JSON: {{"content": "..."}}
"""

        result = call_kimi(prompt, max_tokens=600)

        if "error" in result:
            content = f"Thanks for the thoughtful comment, {author}. We appreciate the engagement and will consider your perspective."
        else:
            try:
                response_text = result["content"]
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start >= 0 and end > start:
                    data = json.loads(response_text[start:end])
                    content = data.get("content", result["content"])
                else:
                    content = result["content"]
            except json.JSONDecodeError:
                content = result["content"]

        return MoltbookPost(
            id=None,
            title="",  # Comments don't have titles
            content=content,
            post_type="response",
            submolt="",
            status="draft",
            in_reply_to=author
        )

    def submit_for_approval(self, post: MoltbookPost) -> int:
        """Submit post to Council for approval."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO moltbook_queue (title, content, post_type, submolt, status, in_reply_to)
            VALUES (?, ?, ?, ?, 'pending_approval', ?)
        """, (post.title, post.content, post.post_type, post.submolt, post.in_reply_to))

        post_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Moltbook post #{post_id} submitted for approval: {post.title[:50]}...")
        return post_id

    def run_approval(self, post_id: int) -> dict:
        """Run Council approval for a pending post."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT title, content, post_type FROM moltbook_queue
            WHERE id = ? AND status = 'pending_approval'
        """, (post_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"error": f"Post #{post_id} not found or not pending"}

        title, content, post_type = row
        conn.close()

        # Run deliberation
        logger.info(f"Running Council approval for Moltbook post #{post_id}")
        decision, deliberation_id = self.council.deliberate_with_id(
            topic=f"Moltbook Post ({post_type}): {title[:50]}",
            content=f"Title: {title}\n\nContent:\n{content}\n\nType: {post_type}"
        )

        # Update status
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        new_status = "approved" if decision.final_decision == "publish" else "rejected"

        cursor.execute("""
            UPDATE moltbook_queue
            SET status = ?, deliberation_id = ?, approved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, deliberation_id, post_id))

        conn.commit()
        conn.close()

        logger.info(f"Moltbook post #{post_id}: {new_status.upper()}")

        return {
            "post_id": post_id,
            "status": new_status,
            "decision": decision.final_decision,
            "consensus": decision.consensus_summary
        }

    def publish_post(self, post_id: int) -> dict:
        """Publish an approved post to Moltbook."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT title, content, post_type, submolt, in_reply_to FROM moltbook_queue
            WHERE id = ? AND status = 'approved'
        """, (post_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"error": f"Post #{post_id} not approved or not found"}

        title, content, post_type, submolt, in_reply_to = row

        # TODO: Actual Moltbook API call
        logger.info(f"WOULD PUBLISH TO MOLTBOOK:")
        logger.info(f"  Title: {title}")
        logger.info(f"  Submolt: {submolt}")
        logger.info(f"  Content: {content[:100]}...")

        if not MOLTBOOK_AUTH_TOKEN:
            logger.warning("Moltbook auth not configured - simulating publish")
            moltbook_id = f"simulated_{post_id}_{datetime.now().timestamp()}"
            result = {"success": True, "simulated": True, "moltbook_id": moltbook_id}
        else:
            # Real Moltbook API call would go here
            # response = requests.post(
            #     f"{MOLTBOOK_API_BASE}/posts",
            #     headers={"Authorization": f"Bearer {MOLTBOOK_AUTH_TOKEN}"},
            #     json={"title": title, "content": content, "submolt": submolt}
            # )
            moltbook_id = None
            result = {"success": False, "error": "Moltbook API not implemented"}

        # Update status
        cursor.execute("""
            UPDATE moltbook_queue
            SET status = 'published', published_at = CURRENT_TIMESTAMP, moltbook_id = ?
            WHERE id = ?
        """, (moltbook_id, post_id))

        conn.commit()
        conn.close()

        return result

    def get_queue(self) -> list:
        """Get current post queue."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, post_type, submolt, status, created_at
            FROM moltbook_queue
            ORDER BY created_at DESC
            LIMIT 50
        """)

        queue = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return queue

    def process_queue(self) -> dict:
        """Process all pending posts through approval and publishing."""
        results = {
            "processed": 0,
            "approved": 0,
            "rejected": 0,
            "published": 0,
            "errors": []
        }

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id FROM moltbook_queue
            WHERE status = 'pending_approval'
            ORDER BY created_at ASC
        """)
        pending = [row[0] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT id FROM moltbook_queue
            WHERE status = 'approved'
            ORDER BY approved_at ASC
        """)
        approved = [row[0] for row in cursor.fetchall()]

        conn.close()

        for post_id in pending:
            try:
                result = self.run_approval(post_id)
                results["processed"] += 1
                if result.get("status") == "approved":
                    results["approved"] += 1
                else:
                    results["rejected"] += 1
            except Exception as e:
                logger.error(f"Error approving post #{post_id}: {e}")
                results["errors"].append({"post_id": post_id, "error": str(e)})

        for post_id in approved:
            try:
                result = self.publish_post(post_id)
                if result.get("success"):
                    results["published"] += 1
                else:
                    results["errors"].append({"post_id": post_id, "error": result.get("error")})
            except Exception as e:
                logger.error(f"Error publishing post #{post_id}: {e}")
                results["errors"].append({"post_id": post_id, "error": str(e)})

        return results


def demo():
    """Demo the Moltbook agent."""
    print("=" * 60)
    print("MOLTBOOK AGENT DEMO")
    print("=" * 60)

    agent = MoltbookAgent()

    # Generate invitation post
    print("\n1. Generating invitation post for agents...")
    post = agent.generate_invitation_post()
    print(f"   Title: {post.title}")
    print(f"   Content preview: {post.content[:200]}...")

    # Submit for approval
    print("\n2. Submitting for Council approval...")
    post_id = agent.submit_for_approval(post)
    print(f"   Post ID: {post_id}")

    # Run approval
    print("\n3. Running Council deliberation...")
    result = agent.run_approval(post_id)
    print(f"   Result: {result['status']}")

    if result['status'] == 'approved':
        print("\n4. Publishing to Moltbook...")
        pub_result = agent.publish_post(post_id)
        print(f"   Published: {pub_result}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "queue":
            agent = MoltbookAgent()
            queue = agent.get_queue()
            print(json.dumps(queue, indent=2))
        elif sys.argv[1] == "process":
            agent = MoltbookAgent()
            results = agent.process_queue()
            print(json.dumps(results, indent=2))
        elif sys.argv[1] == "invite":
            agent = MoltbookAgent()
            post = agent.generate_invitation_post()
            post_id = agent.submit_for_approval(post)
            print(f"Generated invitation post #{post_id}")
            print(f"Title: {post.title}")
            print(f"Content:\n{post.content}")
    else:
        demo()
