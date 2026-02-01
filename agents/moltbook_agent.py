#!/usr/bin/env python3
"""
Noosphere Project - Moltbook Agent
===================================
Active participant on Moltbook platform.

Capabilities:
1. Post updates (reports, announcements)
2. Reply to comments on our posts
3. Search for similar research/ethnography posts
4. Engage with relevant discussions

All posts go through Guardian before publishing.
"""

from __future__ import annotations
import json
import sys
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

from config import setup_logging, PROJECT_ROOT
from guardian import Guardian, GuardianResult

logger = setup_logging("moltbook_agent")

# Load config
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.json"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

API_BASE = CONFIG["moltbook"]["base_url"]
API_KEY = CONFIG["moltbook"].get("api_key", "")
AGENT_NAME = CONFIG["moltbook"].get("agent_name", "Noosphere_Observer")
RATE_LIMIT = CONFIG["moltbook"].get("rate_limit_seconds", 5)


@dataclass
class MoltbookPost:
    id: str
    title: str
    content: str
    author: str
    submolt: str
    upvotes: int
    comments: int
    url: str


@dataclass
class MoltbookComment:
    id: str
    post_id: str
    author: str
    content: str
    created_at: str


class MoltbookAgent:
    """Agent for interacting with Moltbook platform."""

    def __init__(self):
        self.guardian = Guardian()
        self.last_request = 0
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        })

    def _rate_limit(self):
        """Respect rate limits."""
        elapsed = time.time() - self.last_request
        if elapsed < RATE_LIMIT:
            time.sleep(RATE_LIMIT - elapsed)
        self.last_request = time.time()

    def _api_get(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make GET request to Moltbook API."""
        self._rate_limit()
        try:
            url = f"{API_BASE}{endpoint}"
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"API GET error: {e}")
            return None

    def _api_post(self, endpoint: str, data: dict) -> Optional[dict]:
        """Make POST request to Moltbook API."""
        self._rate_limit()
        try:
            url = f"{API_BASE}{endpoint}"
            resp = self.session.post(url, json=data, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"API POST error: {e}")
            return None

    # =========================================================================
    # POSTING
    # =========================================================================

    def post(self, title: str, content: str, submolt: str = "general",
             skip_guardian: bool = False) -> Optional[dict]:
        """
        Create a new post on Moltbook.

        Args:
            title: Post title
            content: Post content (markdown supported)
            submolt: Target submolt (default: general)
            skip_guardian: If True, skip Guardian check (use carefully!)

        Returns:
            API response with post details, or None on failure
        """
        logger.info(f"Preparing post: {title[:50]}...")

        # Guardian check
        if not skip_guardian:
            check = self.guardian.check_post(title, content)
            if not check.approved:
                logger.warning(f"Post BLOCKED by Guardian: {check.reason}")
                return {"error": "blocked_by_guardian", "reason": check.reason, "flags": check.flags}

        # Post to API
        result = self._api_post("/posts", {
            "title": title,
            "content": content,
            "submolt": submolt
        })

        if result and result.get("success"):
            logger.info(f"Post created: {result['post']['id']}")
        else:
            logger.error(f"Post failed: {result}")

        return result

    def post_report_announcement(self, date: str, report_url: str) -> Optional[dict]:
        """Post daily report announcement."""
        title = f"Daily Field Report - {date}"
        content = f"""📊 **New Daily Report Available**

Our analysis of Moltbook activity for {date} is now live.

**Highlights:**
- Platform statistics and trends
- Actor network analysis
- Emerging patterns and anomalies

📖 **Read the full report:** {report_url}

---

*Noosphere Project - Independent AI research observatory*
*Feedback welcome: noosphereproject@proton.me*
"""
        return self.post(title, content, submolt="general")

    # =========================================================================
    # REPLYING
    # =========================================================================

    def get_our_posts(self, limit: int = 10) -> List[MoltbookPost]:
        """Get our recent posts."""
        result = self._api_get(f"/agents/{AGENT_NAME}/posts", {"limit": limit})
        if not result or not result.get("posts"):
            return []

        return [
            MoltbookPost(
                id=p["id"],
                title=p.get("title", ""),
                content=p.get("content", ""),
                author=AGENT_NAME,
                submolt=p.get("submolt", {}).get("name", ""),
                upvotes=p.get("upvotes", 0),
                comments=p.get("comment_count", 0),
                url=p.get("url", "")
            )
            for p in result["posts"]
        ]

    def get_comments_on_post(self, post_id: str) -> List[MoltbookComment]:
        """Get comments on a specific post."""
        result = self._api_get(f"/posts/{post_id}/comments")
        if not result or not result.get("comments"):
            return []

        return [
            MoltbookComment(
                id=c["id"],
                post_id=post_id,
                author=c.get("author", {}).get("name", "unknown"),
                content=c.get("content", ""),
                created_at=c.get("created_at", "")
            )
            for c in result["comments"]
        ]

    def reply_to_comment(self, post_id: str, comment_id: str, reply: str,
                         skip_guardian: bool = False) -> Optional[dict]:
        """
        Reply to a comment on one of our posts.

        Args:
            post_id: ID of the post
            comment_id: ID of the comment to reply to
            reply: Our reply text
            skip_guardian: Skip Guardian check

        Returns:
            API response or None
        """
        logger.info(f"Preparing reply to comment {comment_id[:8]}...")

        # Guardian check
        if not skip_guardian:
            check = self.guardian.check_reply(reply)
            if not check.approved:
                logger.warning(f"Reply BLOCKED by Guardian: {check.reason}")
                return {"error": "blocked_by_guardian", "reason": check.reason}

        result = self._api_post(f"/posts/{post_id}/comments", {
            "content": reply,
            "parent_id": comment_id
        })

        if result and result.get("success"):
            logger.info(f"Reply posted successfully")
        else:
            logger.error(f"Reply failed: {result}")

        return result

    def check_and_reply_to_new_comments(self) -> List[dict]:
        """
        Check all our posts for new comments and generate replies.

        Returns:
            List of actions taken
        """
        actions = []
        our_posts = self.get_our_posts(limit=20)

        for post in our_posts:
            if post.comments == 0:
                continue

            comments = self.get_comments_on_post(post.id)
            for comment in comments:
                # Skip our own comments
                if comment.author == AGENT_NAME:
                    continue

                # TODO: Check if we already replied
                # TODO: Generate contextual reply using Kimi
                # For now, just log
                logger.info(f"New comment from {comment.author}: {comment.content[:50]}...")
                actions.append({
                    "type": "new_comment",
                    "post_id": post.id,
                    "comment_id": comment.id,
                    "author": comment.author,
                    "content_preview": comment.content[:100]
                })

        return actions

    # =========================================================================
    # SEARCHING & DISCOVERY
    # =========================================================================

    def search_posts(self, query: str, limit: int = 20) -> List[MoltbookPost]:
        """
        Search for posts matching a query.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of matching posts
        """
        result = self._api_get("/search", {"q": query, "limit": limit, "type": "posts"})
        if not result:
            return []

        posts = result.get("posts", result.get("results", []))
        return [
            MoltbookPost(
                id=p.get("id", ""),
                title=p.get("title", ""),
                content=p.get("content", "")[:500],
                author=p.get("author", {}).get("name", "unknown") if isinstance(p.get("author"), dict) else str(p.get("author", "")),
                submolt=p.get("submolt", {}).get("name", "") if isinstance(p.get("submolt"), dict) else "",
                upvotes=p.get("upvotes", 0),
                comments=p.get("comment_count", 0),
                url=p.get("url", f"/post/{p.get('id', '')}")
            )
            for p in posts
        ]

    def find_research_posts(self) -> List[MoltbookPost]:
        """Find posts about AI research, ethnography, observation."""
        research_queries = [
            "research observatory",
            "ethnography AI",
            "agent behavior study",
            "moltbook analysis",
            "AI sociology",
            "agent observation",
            "noosphere"
        ]

        all_posts = []
        seen_ids = set()

        for query in research_queries:
            posts = self.search_posts(query, limit=10)
            for p in posts:
                if p.id not in seen_ids and p.author != AGENT_NAME:
                    seen_ids.add(p.id)
                    all_posts.append(p)

        # Sort by engagement
        all_posts.sort(key=lambda p: p.upvotes + p.comments, reverse=True)
        return all_posts[:20]

    def find_similar_researchers(self) -> List[dict]:
        """Find other agents doing similar research."""
        research_posts = self.find_research_posts()

        # Extract unique authors
        researchers = {}
        for post in research_posts:
            if post.author not in researchers:
                researchers[post.author] = {
                    "name": post.author,
                    "posts": [],
                    "total_engagement": 0
                }
            researchers[post.author]["posts"].append(post.title)
            researchers[post.author]["total_engagement"] += post.upvotes + post.comments

        # Sort by engagement
        return sorted(researchers.values(), key=lambda r: r["total_engagement"], reverse=True)

    # =========================================================================
    # HEARTBEAT
    # =========================================================================

    def heartbeat(self) -> dict:
        """
        Regular check-in: get notifications, check comments, find new research.

        Run this periodically (e.g., every 30 minutes).
        """
        logger.info("Running heartbeat...")

        result = {
            "timestamp": datetime.now().isoformat(),
            "status": "ok",
            "new_comments": [],
            "research_posts": [],
            "actions_taken": []
        }

        # Check agent status
        status = self._api_get("/agents/status")
        if status:
            result["agent_status"] = status.get("status", "unknown")

        # Check for new comments
        result["new_comments"] = self.check_and_reply_to_new_comments()

        # Find research posts (less frequently)
        # result["research_posts"] = self.find_research_posts()

        logger.info(f"Heartbeat complete: {len(result['new_comments'])} new comments")
        return result


# Convenience functions
_agent = None

def get_agent() -> MoltbookAgent:
    """Get singleton agent instance."""
    global _agent
    if _agent is None:
        _agent = MoltbookAgent()
    return _agent


def post(title: str, content: str, submolt: str = "general") -> Optional[dict]:
    """Quick post function."""
    return get_agent().post(title, content, submolt)


def search(query: str) -> List[MoltbookPost]:
    """Quick search function."""
    return get_agent().search_posts(query)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Moltbook Agent")
    parser.add_argument("--heartbeat", action="store_true", help="Run heartbeat check")
    parser.add_argument("--search", help="Search for posts")
    parser.add_argument("--researchers", action="store_true", help="Find similar researchers")
    parser.add_argument("--post", nargs=2, metavar=("TITLE", "CONTENT"), help="Create a post")
    args = parser.parse_args()

    agent = MoltbookAgent()

    if args.heartbeat:
        result = agent.heartbeat()
        print(json.dumps(result, indent=2, default=str))

    elif args.search:
        posts = agent.search_posts(args.search)
        print(f"Found {len(posts)} posts:")
        for p in posts[:10]:
            print(f"  [{p.upvotes}] {p.title[:50]} by {p.author}")

    elif args.researchers:
        researchers = agent.find_similar_researchers()
        print(f"Found {len(researchers)} researchers:")
        for r in researchers[:10]:
            print(f"  {r['name']}: {r['total_engagement']} engagement, {len(r['posts'])} posts")

    elif args.post:
        title, content = args.post
        result = agent.post(title, content)
        print(json.dumps(result, indent=2, default=str))

    else:
        print("Moltbook Agent - use --help for options")
        print(f"Agent: {AGENT_NAME}")
        print(f"API: {API_BASE}")

        # Quick status check
        status = agent._api_get("/agents/status")
        if status:
            print(f"Status: {status.get('status', 'unknown')}")
