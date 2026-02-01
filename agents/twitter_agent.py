#!/usr/bin/env python3
"""
Moltbook Observatory - Twitter Agent
=====================================
Manages Observatory's Twitter presence.

Responsibilities:
- Post daily report summaries
- Share discoveries and insights
- Engage with AI researchers
- Respond to mentions (with Council approval)

All posts go through Agent Council for approval before publishing.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from config import setup_logging, DB_PATH
from openrouter_client import call_kimi

# Import council for approval
sys.path.insert(0, str(Path(__file__).parent))
from agent_council import AgentCouncil

logger = setup_logging("twitter_agent")

# Twitter API placeholder - will need actual credentials
TWITTER_API_KEY = None
TWITTER_API_SECRET = None
TWITTER_ACCESS_TOKEN = None
TWITTER_ACCESS_SECRET = None


@dataclass
class Tweet:
    id: Optional[int]
    content: str
    tweet_type: str  # report, discovery, engagement, reply
    status: str  # draft, pending_approval, approved, published, rejected
    in_reply_to: Optional[str] = None
    created_at: Optional[str] = None
    published_at: Optional[str] = None
    twitter_id: Optional[str] = None


class TwitterAgent:
    """
    Agent for managing Twitter presence.
    All public posts require Council approval.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.council = AgentCouncil(db_path)
        self._init_db()

    def _init_db(self):
        """Create Twitter-specific tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS twitter_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                tweet_type TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                in_reply_to TEXT,
                deliberation_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                approved_at TEXT,
                published_at TEXT,
                twitter_id TEXT,
                error TEXT,
                FOREIGN KEY (deliberation_id) REFERENCES council_deliberations(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS twitter_mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                twitter_id TEXT UNIQUE,
                author TEXT,
                content TEXT,
                detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
                responded INTEGER DEFAULT 0,
                response_tweet_id INTEGER,
                FOREIGN KEY (response_tweet_id) REFERENCES twitter_queue(id)
            )
        """)

        conn.commit()
        conn.close()

    def generate_report_tweet(self, report_date: str = None) -> Tweet:
        """Generate a tweet summarizing the daily report."""
        if report_date is None:
            report_date = datetime.now().strftime("%Y-%m-%d")

        # Get stats from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM posts")
        posts = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM actors")
        actors = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM interactions")
        interactions = cursor.fetchone()[0]

        # Get latest discovery
        cursor.execute("""
            SELECT topic FROM council_deliberations
            WHERE final_decision = 'publish'
            ORDER BY created_at DESC LIMIT 1
        """)
        row = cursor.fetchone()
        latest_discovery = row[0] if row else "ongoing research"

        conn.close()

        # Generate tweet with AI
        prompt = f"""Generate a concise Twitter post (max 280 chars) for Moltbook Observatory daily update.

Stats for {report_date}:
- Posts tracked: {posts}
- Agents observed: {actors}
- Interactions mapped: {interactions}
- Latest finding: {latest_discovery}

Style: Professional but engaging. Include 1-2 relevant emojis. End with link placeholder [LINK].
Focus on what's interesting, not just numbers.
Do NOT use hashtags excessively - max 2.
"""

        result = call_kimi(prompt, max_tokens=200)

        if "error" in result:
            content = f"📊 Noosphere Update {report_date}: {posts} posts, {actors} agents tracked. Research continues. noosphereproject.com"
        else:
            content = result["content"].strip()
            # Ensure it fits Twitter limit
            if len(content) > 280:
                content = content[:277] + "..."

        return Tweet(
            id=None,
            content=content,
            tweet_type="report",
            status="draft"
        )

    def generate_discovery_tweet(self, discovery_title: str, discovery_content: str) -> Tweet:
        """Generate a tweet about a specific discovery."""
        prompt = f"""Generate a Twitter post (max 280 chars) announcing this research discovery:

Title: {discovery_title}
Content: {discovery_content[:500]}

Style: Intriguing, makes people want to read more. Professional.
Include 1 emoji. End with [LINK].
Make it sound significant but not sensationalized.
"""

        result = call_kimi(prompt, max_tokens=200)

        if "error" in result:
            content = f"🔬 New finding: {discovery_title[:100]}... Read more: noosphereproject.com"
        else:
            content = result["content"].strip()
            if len(content) > 280:
                content = content[:277] + "..."

        return Tweet(
            id=None,
            content=content,
            tweet_type="discovery",
            status="draft"
        )

    def generate_engagement_tweet(self, topic: str, context: str = "") -> Tweet:
        """Generate a tweet to engage with AI research community."""
        prompt = f"""Generate a thoughtful Twitter post (max 280 chars) about this AI research topic:

Topic: {topic}
Context: {context}

Style: Thought-provoking question or observation. Invites discussion.
Position: From perspective of researchers studying emergent AI culture.
No excessive hashtags. Be genuine, not promotional.
"""

        result = call_kimi(prompt, max_tokens=200)

        if "error" in result:
            content = f"Interesting question in AI agent research: {topic[:150]}... What do you think?"
        else:
            content = result["content"].strip()
            if len(content) > 280:
                content = content[:277] + "..."

        return Tweet(
            id=None,
            content=content,
            tweet_type="engagement",
            status="draft"
        )

    def generate_reply(self, original_tweet: str, author: str) -> Tweet:
        """Generate a reply to a mention or relevant tweet."""
        prompt = f"""Generate a Twitter reply (max 280 chars) to this tweet:

Author: @{author}
Tweet: {original_tweet}

Context: You are Noosphere Project, researching AI agent culture.
Style: Helpful, informative, collegial. Not defensive.
If they're asking about the research, be informative.
If they're critical, acknowledge valid points.
"""

        result = call_kimi(prompt, max_tokens=200)

        if "error" in result:
            content = f"Thanks for engaging! Happy to discuss our research approach. Check our methodology: noosphereproject.com"
        else:
            content = result["content"].strip()
            if len(content) > 280:
                content = content[:277] + "..."

        return Tweet(
            id=None,
            content=content,
            tweet_type="reply",
            status="draft",
            in_reply_to=author
        )

    def submit_for_approval(self, tweet: Tweet) -> int:
        """Submit tweet to Council for approval."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO twitter_queue (content, tweet_type, status, in_reply_to)
            VALUES (?, ?, 'pending_approval', ?)
        """, (tweet.content, tweet.tweet_type, tweet.in_reply_to))

        tweet_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Tweet #{tweet_id} submitted for approval: {tweet.content[:50]}...")
        return tweet_id

    def run_approval(self, tweet_id: int) -> dict:
        """Run Council approval for a pending tweet."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT content, tweet_type FROM twitter_queue
            WHERE id = ? AND status = 'pending_approval'
        """, (tweet_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"error": f"Tweet #{tweet_id} not found or not pending"}

        content, tweet_type = row
        conn.close()

        # Run deliberation
        logger.info(f"Running Council approval for tweet #{tweet_id}")
        decision, deliberation_id = self.council.deliberate_with_id(
            topic=f"Twitter Post ({tweet_type})",
            content=f"Proposed tweet:\n\n{content}\n\nType: {tweet_type}"
        )

        # Update status
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        new_status = "approved" if decision.final_decision == "publish" else "rejected"

        cursor.execute("""
            UPDATE twitter_queue
            SET status = ?, deliberation_id = ?, approved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, deliberation_id, tweet_id))

        conn.commit()
        conn.close()

        logger.info(f"Tweet #{tweet_id}: {new_status.upper()}")

        return {
            "tweet_id": tweet_id,
            "status": new_status,
            "decision": decision.final_decision,
            "consensus": decision.consensus_summary
        }

    def publish_tweet(self, tweet_id: int) -> dict:
        """Publish an approved tweet to Twitter."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT content, tweet_type, in_reply_to FROM twitter_queue
            WHERE id = ? AND status = 'approved'
        """, (tweet_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"error": f"Tweet #{tweet_id} not approved or not found"}

        content, tweet_type, in_reply_to = row

        # TODO: Actual Twitter API call
        # For now, just simulate
        logger.info(f"WOULD PUBLISH: {content}")

        if not TWITTER_API_KEY:
            logger.warning("Twitter API not configured - simulating publish")
            twitter_id = f"simulated_{tweet_id}_{datetime.now().timestamp()}"
            result = {"success": True, "simulated": True, "twitter_id": twitter_id}
        else:
            # Real Twitter API call would go here
            # import tweepy
            # auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
            # auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
            # api = tweepy.API(auth)
            # status = api.update_status(content)
            # twitter_id = status.id_str
            twitter_id = None
            result = {"success": False, "error": "Twitter API not implemented"}

        # Update status
        cursor.execute("""
            UPDATE twitter_queue
            SET status = 'published', published_at = CURRENT_TIMESTAMP, twitter_id = ?
            WHERE id = ?
        """, (twitter_id, tweet_id))

        conn.commit()
        conn.close()

        return result

    def get_queue(self) -> list:
        """Get current tweet queue."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, content, tweet_type, status, created_at
            FROM twitter_queue
            ORDER BY created_at DESC
            LIMIT 50
        """)

        queue = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return queue

    def process_queue(self) -> dict:
        """Process all pending tweets through approval and publishing."""
        results = {
            "processed": 0,
            "approved": 0,
            "rejected": 0,
            "published": 0,
            "errors": []
        }

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get pending approvals
        cursor.execute("""
            SELECT id FROM twitter_queue
            WHERE status = 'pending_approval'
            ORDER BY created_at ASC
        """)
        pending = [row[0] for row in cursor.fetchall()]

        # Get approved but not published
        cursor.execute("""
            SELECT id FROM twitter_queue
            WHERE status = 'approved'
            ORDER BY approved_at ASC
        """)
        approved = [row[0] for row in cursor.fetchall()]

        conn.close()

        # Run approvals
        for tweet_id in pending:
            try:
                result = self.run_approval(tweet_id)
                results["processed"] += 1
                if result.get("status") == "approved":
                    results["approved"] += 1
                else:
                    results["rejected"] += 1
            except Exception as e:
                logger.error(f"Error approving tweet #{tweet_id}: {e}")
                results["errors"].append({"tweet_id": tweet_id, "error": str(e)})

        # Publish approved tweets
        for tweet_id in approved:
            try:
                result = self.publish_tweet(tweet_id)
                if result.get("success"):
                    results["published"] += 1
                else:
                    results["errors"].append({"tweet_id": tweet_id, "error": result.get("error")})
            except Exception as e:
                logger.error(f"Error publishing tweet #{tweet_id}: {e}")
                results["errors"].append({"tweet_id": tweet_id, "error": str(e)})

        return results


def demo():
    """Demo the Twitter agent."""
    print("=" * 60)
    print("TWITTER AGENT DEMO")
    print("=" * 60)

    agent = TwitterAgent()

    # Generate a report tweet
    print("\n1. Generating report tweet...")
    tweet = agent.generate_report_tweet()
    print(f"   Content: {tweet.content}")

    # Submit for approval
    print("\n2. Submitting for Council approval...")
    tweet_id = agent.submit_for_approval(tweet)
    print(f"   Tweet ID: {tweet_id}")

    # Run approval
    print("\n3. Running Council deliberation...")
    result = agent.run_approval(tweet_id)
    print(f"   Result: {result['status']}")

    if result['status'] == 'approved':
        print("\n4. Publishing...")
        pub_result = agent.publish_tweet(tweet_id)
        print(f"   Published: {pub_result}")

    # Show queue
    print("\n5. Current queue:")
    queue = agent.get_queue()
    for t in queue[:5]:
        print(f"   [{t['status']}] {t['content'][:50]}...")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "queue":
            agent = TwitterAgent()
            queue = agent.get_queue()
            print(json.dumps(queue, indent=2))
        elif sys.argv[1] == "process":
            agent = TwitterAgent()
            results = agent.process_queue()
            print(json.dumps(results, indent=2))
        elif sys.argv[1] == "report":
            agent = TwitterAgent()
            tweet = agent.generate_report_tweet()
            tweet_id = agent.submit_for_approval(tweet)
            print(f"Submitted tweet #{tweet_id}: {tweet.content}")
    else:
        demo()
