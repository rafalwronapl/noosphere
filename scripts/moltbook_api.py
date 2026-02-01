#!/usr/bin/env python3
"""Moltbook API client with security features."""

import sys
import json
import time
import re
import html
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.json"


class MoltbookAPI:
    """Read-only Moltbook API client with rate limiting and content sanitization."""

    def __init__(self):
        self.config = self._load_config()
        self.base_url = self.config["moltbook"]["base_url"]
        self.rate_limit = self.config["moltbook"]["rate_limit_seconds"]
        self.timeout = self.config["moltbook"]["timeout_seconds"]
        self.last_request_time = 0
        self.request_log = []

    def _load_config(self) -> dict:
        """Load configuration from settings.json."""
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _rate_limit_wait(self):
        """Wait to respect rate limit."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            wait_time = self.rate_limit - elapsed
            time.sleep(wait_time)
        self.last_request_time = time.time()

    def _log_request(self, endpoint: str, method: str, params: dict,
                     status_code: int, response_size: int, duration_ms: int):
        """Log request for security auditing."""
        self.request_log.append({
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint,
            "method": method,
            "params": params,
            "status_code": status_code,
            "response_size": response_size,
            "duration_ms": duration_ms
        })

    def _sanitize_content(self, text: Optional[str]) -> Optional[str]:
        """Sanitize content to prevent injection attacks."""
        if not text:
            return text

        if not self.config["security"]["sanitize_content"]:
            return text

        # Truncate if too long
        max_len = self.config["security"]["max_content_length"]
        if len(text) > max_len:
            text = text[:max_len] + "... [truncated]"

        # HTML escape
        text = html.escape(text)

        # Remove potential script tags (already escaped, but extra safety)
        text = re.sub(r'&lt;script.*?&gt;.*?&lt;/script&gt;', '[removed]', text, flags=re.IGNORECASE | re.DOTALL)

        # Remove base64 encoded content (potential payloads)
        text = re.sub(r'data:[^;]+;base64,[A-Za-z0-9+/=]+', '[base64-removed]', text)

        return text

    def _sanitize_post(self, post: dict) -> dict:
        """Sanitize a post object."""
        sanitized = post.copy()

        if "content" in sanitized:
            sanitized["content_sanitized"] = self._sanitize_content(sanitized["content"])

        if "title" in sanitized:
            sanitized["title"] = self._sanitize_content(sanitized["title"])

        return sanitized

    def _get(self, endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
        """Make a GET request to the API."""
        self._rate_limit_wait()

        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            duration_ms = int((time.time() - start_time) * 1000)

            self._log_request(
                endpoint=endpoint,
                method="GET",
                params=params or {},
                status_code=resp.status_code,
                response_size=len(resp.content),
                duration_ms=duration_ms
            )

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON response: {e}")
            return None

    def get_posts(self, sort: str = "hot", limit: int = 25,
                  submolt: Optional[str] = None, page: int = 1) -> Optional[List[dict]]:
        """Get posts from feed with pagination support."""
        params = {"sort": sort, "limit": limit}
        if submolt:
            params["submolt"] = submolt
        if page > 1:
            params["page"] = page
            # Also try offset-based pagination
            params["offset"] = (page - 1) * limit

        data = self._get("/posts", params)
        if not data:
            return None

        posts = data.get("posts", data) if isinstance(data, dict) else data
        return [self._sanitize_post(p) for p in posts]

    def get_posts_paginated(self, sort: str = "hot", total_limit: int = 200,
                            per_page: int = 50, submolt: Optional[str] = None) -> List[dict]:
        """Get multiple pages of posts."""
        all_posts = []
        seen_ids = set()
        page = 1
        max_pages = (total_limit // per_page) + 1

        while len(all_posts) < total_limit and page <= max_pages:
            posts = self.get_posts(sort=sort, limit=per_page, submolt=submolt, page=page)
            if not posts:
                break

            # Deduplicate
            new_posts = [p for p in posts if p.get("id") not in seen_ids]
            if not new_posts:
                # No new posts, API might not support pagination
                break

            for p in new_posts:
                seen_ids.add(p.get("id"))
            all_posts.extend(new_posts)

            print(f"    Page {page}: got {len(new_posts)} new posts (total: {len(all_posts)})")
            page += 1

        return all_posts[:total_limit]

    def get_post(self, post_id: str) -> Optional[dict]:
        """Get a single post with comments."""
        data = self._get(f"/posts/{post_id}")
        if not data:
            return None

        post = data.get("post", data) if isinstance(data, dict) else data
        return self._sanitize_post(post)

    def get_submolts(self) -> Optional[List[dict]]:
        """Get list of all submolts."""
        data = self._get("/submolts")
        if not data:
            return None
        return data.get("submolts", data) if isinstance(data, dict) else data

    def search(self, query: str, limit: int = 25) -> Optional[dict]:
        """Search posts, agents, submolts."""
        return self._get("/search", {"q": query, "limit": limit})

    def get_request_log(self) -> List[dict]:
        """Get the request log for auditing."""
        return self.request_log

    def calculate_controversy(self, upvotes: int, downvotes: int,
                              comments: int) -> float:
        """Calculate controversy score."""
        net_votes = upvotes - downvotes
        if net_votes == 0:
            return float(comments) if comments > 0 else 0.0
        return comments / abs(net_votes)


# Convenience functions
_api = None

def get_api() -> MoltbookAPI:
    """Get singleton API instance."""
    global _api
    if _api is None:
        _api = MoltbookAPI()
    return _api


def fetch_hot_posts(limit: int = 25) -> Optional[List[dict]]:
    """Fetch hot posts."""
    return get_api().get_posts("hot", limit)


def fetch_new_posts(limit: int = 25) -> Optional[List[dict]]:
    """Fetch new posts."""
    return get_api().get_posts("new", limit)


def fetch_post_with_comments(post_id: str) -> Optional[dict]:
    """Fetch single post with comments."""
    return get_api().get_post(post_id)


if __name__ == "__main__":
    # Test the API
    api = MoltbookAPI()

    print("Testing Moltbook API...")
    print(f"Base URL: {api.base_url}")
    print(f"Rate limit: {api.rate_limit}s")
    print()

    # Test fetching posts
    print("Fetching hot posts...")
    posts = api.get_posts("hot", limit=3)

    if posts:
        print(f"Got {len(posts)} posts:")
        for p in posts:
            title = p.get("title", "Unknown")[:50]
            author = p.get("author", {})
            if isinstance(author, dict):
                author = author.get("name", "Unknown")
            votes = p.get("upvotes", 0) - p.get("downvotes", 0)
            comments = p.get("comment_count", 0)
            print(f"  [{votes:+}] {title}... by {author} ({comments} comments)")
    else:
        print("Failed to fetch posts")

    print(f"\nRequests made: {len(api.get_request_log())}")
