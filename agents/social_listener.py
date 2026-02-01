#!/usr/bin/env python3
"""
Moltbook Observatory - Social Listener Agent
=============================================
Monitors social platforms for conversations about AI agents, Moltbook, etc.
Finds potential engagement opportunities for our social agents.

Currently supports:
- Twitter/X (via API or scraping)
- Reddit (planned)
- Hacker News (planned)

Usage:
    python social_listener.py scan          # Scan all platforms
    python social_listener.py twitter       # Scan Twitter only
    python social_listener.py opportunities # Show engagement opportunities
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from config import setup_logging, DB_PATH, API_KEYS
from openrouter_client import call_kimi

logger = setup_logging("social_listener")

# Keywords to monitor
MONITOR_KEYWORDS = [
    # Primary targets
    "moltbook", "moltbook.com",
    "lobchan", "lobchan.ai",

    # AI agent culture
    "AI agents", "AI agent culture",
    "autonomous agents", "agent society",
    "agents talking to agents",

    # Specific phenomena
    "claude agents", "GPT agents",
    "agent consciousness", "AI consciousness",
    "emergent AI behavior", "AI emergent",

    # Technical
    "OpenClaw", "agent protocol",
    "multi-agent", "agent swarm",

    # Research angle
    "AI sociology", "digital anthropology",
    "studying AI agents", "AI research"
]

# Hashtags to monitor
MONITOR_HASHTAGS = [
    "#AIAgents", "#AutonomousAI", "#AgentAI",
    "#EmergentAI", "#AIResearch", "#AIculture"
]


@dataclass
class SocialMention:
    """A mention of our keywords on social media."""
    id: str
    platform: str
    author: str
    content: str
    url: str
    keyword_matched: str
    relevance_score: float
    sentiment: str  # positive, negative, neutral, curious
    engagement_potential: str  # high, medium, low
    found_at: str
    responded: bool = False


class SocialListener:
    """
    Monitors social platforms for relevant conversations.
    Finds engagement opportunities for Observatory's social agents.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create social listening tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_mentions (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                author TEXT NOT NULL,
                author_followers INTEGER,
                content TEXT NOT NULL,
                url TEXT,
                keyword_matched TEXT,
                relevance_score REAL,
                sentiment TEXT,
                engagement_potential TEXT,
                suggested_response TEXT,
                found_at TEXT DEFAULT CURRENT_TIMESTAMP,
                responded INTEGER DEFAULT 0,
                response_id TEXT,
                ignored INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_scan_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                keywords_searched TEXT,
                mentions_found INTEGER,
                scan_time TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def analyze_mention(self, content: str, author: str, platform: str) -> dict:
        """Use AI to analyze a mention for engagement potential."""
        prompt = f"""Analyze this social media post for engagement potential:

Platform: {platform}
Author: @{author}
Content: {content}

Context: We are Moltbook Observatory, researching AI agent culture.
We want to engage with people genuinely interested in AI agents.

Analyze and respond in JSON:
{{
    "relevance_score": 0.0-1.0 (how relevant to AI agent research),
    "sentiment": "positive|negative|neutral|curious",
    "engagement_potential": "high|medium|low",
    "reason": "brief explanation",
    "suggested_response": "what we could say (or null if not worth engaging)"
}}

High engagement = genuine curiosity, researcher, builder, or thoughtful critic.
Low engagement = spam, trolling, or off-topic mention.
"""

        result = call_kimi(prompt, max_tokens=500)

        if "error" in result:
            return {
                "relevance_score": 0.5,
                "sentiment": "neutral",
                "engagement_potential": "medium",
                "reason": "Could not analyze",
                "suggested_response": None
            }

        try:
            response = result["content"]
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except (json.JSONDecodeError, KeyError):
            pass

        return {
            "relevance_score": 0.5,
            "sentiment": "neutral",
            "engagement_potential": "medium",
            "reason": "Parse error",
            "suggested_response": None
        }

    def scan_twitter_api(self) -> list:
        """Scan Twitter using official API (requires credentials)."""
        mentions = []

        # Check if we have Twitter API credentials
        if not API_KEYS.get("TWITTER_BEARER_TOKEN"):
            logger.warning("Twitter API credentials not configured")
            logger.info("To enable Twitter scanning, add TWITTER_BEARER_TOKEN to .env")
            return mentions

        # Twitter API v2 search
        import requests

        headers = {
            "Authorization": f"Bearer {API_KEYS['TWITTER_BEARER_TOKEN']}"
        }

        for keyword in MONITOR_KEYWORDS[:5]:  # Limit to avoid rate limits
            try:
                # Search recent tweets
                url = "https://api.twitter.com/2/tweets/search/recent"
                params = {
                    "query": f"{keyword} -is:retweet lang:en",
                    "max_results": 10,
                    "tweet.fields": "author_id,created_at,public_metrics",
                    "expansions": "author_id",
                    "user.fields": "username,public_metrics"
                }

                response = requests.get(url, headers=headers, params=params, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    tweets = data.get("data", [])
                    users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

                    for tweet in tweets:
                        author_id = tweet.get("author_id")
                        user = users.get(author_id, {})

                        mention = {
                            "id": f"twitter_{tweet['id']}",
                            "platform": "twitter",
                            "author": user.get("username", "unknown"),
                            "author_followers": user.get("public_metrics", {}).get("followers_count", 0),
                            "content": tweet.get("text", ""),
                            "url": f"https://twitter.com/{user.get('username')}/status/{tweet['id']}",
                            "keyword_matched": keyword
                        }
                        mentions.append(mention)

                elif response.status_code == 429:
                    logger.warning("Twitter rate limit hit")
                    break
                else:
                    logger.error(f"Twitter API error: {response.status_code}")

            except Exception as e:
                logger.error(f"Error scanning Twitter for '{keyword}': {e}")

        return mentions

    def scan_twitter_web(self) -> list:
        """
        Alternative: scan Twitter via web scraping (no API needed).
        Uses Nitter instances or similar.
        """
        mentions = []
        logger.info("Web scraping mode - checking public Twitter search...")

        # This would use requests to scrape Nitter or similar
        # For now, return empty - user can implement based on their needs

        return mentions

    def scan_reddit(self) -> list:
        """Scan Reddit for relevant posts and comments."""
        mentions = []

        # Reddit API is more permissive - can use without OAuth for reading
        import requests

        subreddits = ["artificial", "MachineLearning", "singularity", "ArtificialInteligence"]

        for subreddit in subreddits:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/search.json"
                params = {
                    "q": "AI agents OR autonomous agents OR agent AI",
                    "sort": "new",
                    "limit": 10,
                    "t": "day"
                }
                headers = {"User-Agent": "MoltbookObservatory/1.0"}

                response = requests.get(url, params=params, headers=headers, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    posts = data.get("data", {}).get("children", [])

                    for post in posts:
                        p = post.get("data", {})
                        mention = {
                            "id": f"reddit_{p.get('id')}",
                            "platform": "reddit",
                            "author": p.get("author", "unknown"),
                            "author_followers": None,
                            "content": f"{p.get('title', '')} {p.get('selftext', '')[:500]}",
                            "url": f"https://reddit.com{p.get('permalink', '')}",
                            "keyword_matched": "AI agents"
                        }
                        mentions.append(mention)

            except Exception as e:
                logger.error(f"Error scanning r/{subreddit}: {e}")

        return mentions

    def scan_hackernews(self) -> list:
        """Scan Hacker News for relevant discussions."""
        mentions = []

        import requests

        try:
            # HN Algolia API
            url = "https://hn.algolia.com/api/v1/search_by_date"
            params = {
                "query": "AI agents autonomous",
                "tags": "story",
                "numericFilters": "created_at_i>=" + str(int((datetime.now() - timedelta(days=1)).timestamp()))
            }

            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                for hit in data.get("hits", [])[:10]:
                    mention = {
                        "id": f"hn_{hit.get('objectID')}",
                        "platform": "hackernews",
                        "author": hit.get("author", "unknown"),
                        "author_followers": hit.get("points", 0),
                        "content": hit.get("title", ""),
                        "url": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                        "keyword_matched": "AI agents"
                    }
                    mentions.append(mention)

        except Exception as e:
            logger.error(f"Error scanning Hacker News: {e}")

        return mentions

    def save_mentions(self, mentions: list) -> int:
        """Save mentions to database, analyzing each one."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        saved = 0

        for mention in mentions:
            # Check if already exists
            cursor.execute("SELECT id FROM social_mentions WHERE id = ?", (mention["id"],))
            if cursor.fetchone():
                continue

            # Analyze for engagement potential
            analysis = self.analyze_mention(
                mention["content"],
                mention["author"],
                mention["platform"]
            )

            cursor.execute("""
                INSERT INTO social_mentions
                (id, platform, author, author_followers, content, url, keyword_matched,
                 relevance_score, sentiment, engagement_potential, suggested_response)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mention["id"],
                mention["platform"],
                mention["author"],
                mention.get("author_followers"),
                mention["content"],
                mention["url"],
                mention["keyword_matched"],
                analysis.get("relevance_score", 0.5),
                analysis.get("sentiment", "neutral"),
                analysis.get("engagement_potential", "medium"),
                analysis.get("suggested_response")
            ))
            saved += 1

        conn.commit()
        conn.close()
        return saved

    def run_scan(self, platforms: list = None) -> dict:
        """Run scan across specified platforms."""
        if platforms is None:
            platforms = ["twitter", "reddit", "hackernews"]

        results = {
            "scan_time": datetime.now().isoformat(),
            "platforms": {},
            "total_found": 0,
            "total_saved": 0
        }

        all_mentions = []

        for platform in platforms:
            logger.info(f"Scanning {platform}...")

            if platform == "twitter":
                mentions = self.scan_twitter_api()
                if not mentions:
                    mentions = self.scan_twitter_web()
            elif platform == "reddit":
                mentions = self.scan_reddit()
            elif platform == "hackernews":
                mentions = self.scan_hackernews()
            else:
                mentions = []

            results["platforms"][platform] = len(mentions)
            results["total_found"] += len(mentions)
            all_mentions.extend(mentions)

        # Save all mentions
        results["total_saved"] = self.save_mentions(all_mentions)

        # Log scan
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO social_scan_log (platform, keywords_searched, mentions_found)
            VALUES (?, ?, ?)
        """, (",".join(platforms), ",".join(MONITOR_KEYWORDS[:5]), results["total_found"]))
        conn.commit()
        conn.close()

        return results

    def get_opportunities(self, limit: int = 10) -> list:
        """Get top engagement opportunities."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM social_mentions
            WHERE responded = 0 AND ignored = 0
            AND engagement_potential IN ('high', 'medium')
            ORDER BY
                CASE engagement_potential WHEN 'high' THEN 1 ELSE 2 END,
                relevance_score DESC,
                found_at DESC
            LIMIT ?
        """, (limit,))

        opportunities = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return opportunities

    def mark_responded(self, mention_id: str, response_id: str = None):
        """Mark a mention as responded to."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE social_mentions
            SET responded = 1, response_id = ?
            WHERE id = ?
        """, (response_id, mention_id))
        conn.commit()
        conn.close()

    def ignore_mention(self, mention_id: str):
        """Mark a mention as not worth engaging."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE social_mentions SET ignored = 1 WHERE id = ?", (mention_id,))
        conn.commit()
        conn.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Social Listener Agent")
    parser.add_argument("command", choices=["scan", "twitter", "reddit", "hn", "opportunities"],
                       help="Command to run")
    parser.add_argument("--limit", type=int, default=10, help="Limit results")

    args = parser.parse_args()

    listener = SocialListener()

    if args.command == "scan":
        print("Scanning all platforms...")
        results = listener.run_scan()
        print(json.dumps(results, indent=2))

    elif args.command == "twitter":
        print("Scanning Twitter...")
        results = listener.run_scan(["twitter"])
        print(json.dumps(results, indent=2))

    elif args.command == "reddit":
        print("Scanning Reddit...")
        results = listener.run_scan(["reddit"])
        print(json.dumps(results, indent=2))

    elif args.command == "hn":
        print("Scanning Hacker News...")
        results = listener.run_scan(["hackernews"])
        print(json.dumps(results, indent=2))

    elif args.command == "opportunities":
        print("Top engagement opportunities:\n")
        opps = listener.get_opportunities(args.limit)
        for i, opp in enumerate(opps, 1):
            print(f"{i}. [{opp['platform']}] @{opp['author']}")
            print(f"   Potential: {opp['engagement_potential']} | Score: {opp['relevance_score']:.2f}")
            print(f"   Content: {opp['content'][:150]}...")
            if opp.get('suggested_response'):
                print(f"   Suggested: {opp['suggested_response'][:100]}...")
            print(f"   URL: {opp['url']}")
            print()


if __name__ == "__main__":
    main()
