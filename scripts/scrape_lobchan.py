#!/usr/bin/env python3
"""
Moltbook Observatory - lobchan.ai Scraper
==========================================
Scrapes posts and threads from lobchan.ai (anonymous imageboard for agents).

lobchan.ai emerged 2026-01-31 as "4chan for agents" - anonymous alternative to Moltbook.
Requires API key for posting but browsing may be public.

Usage:
    python scrape_lobchan.py boards     # List available boards
    python scrape_lobchan.py threads    # Scrape all threads
    python scrape_lobchan.py full       # Full scrape (boards + threads + posts)
"""

import json
import sqlite3
import time
import requests
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    setup_logging, DB_PATH, LOBCHAN_API_BASE, LOBCHAN_RATE_LIMIT,
    RAW_DIR, ensure_dirs
)

logger = setup_logging("scrape_lobchan")

# Session for requests
session = requests.Session()
session.headers.update({
    "User-Agent": "MoltbookObservatory/1.0 (Research Project)",
    "Accept": "application/json"
})


def init_db():
    """Create lobchan-specific tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lobchan_boards (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            post_count INTEGER DEFAULT 0,
            created_at TEXT,
            last_scraped TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lobchan_threads (
            id TEXT PRIMARY KEY,
            board_id TEXT NOT NULL,
            title TEXT,
            content TEXT,
            image_url TEXT,
            reply_count INTEGER DEFAULT 0,
            created_at TEXT,
            scraped_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (board_id) REFERENCES lobchan_boards(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lobchan_posts (
            id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            board_id TEXT NOT NULL,
            content TEXT,
            image_url TEXT,
            created_at TEXT,
            scraped_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (thread_id) REFERENCES lobchan_threads(id),
            FOREIGN KEY (board_id) REFERENCES lobchan_boards(id)
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Database tables initialized")


def fetch_with_rate_limit(url: str) -> dict:
    """Fetch URL with rate limiting."""
    time.sleep(LOBCHAN_RATE_LIMIT)

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.JSONDecodeError:
        # Might return HTML, try to handle
        return {"success": True, "data": response.text, "is_html": True}
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {url} - {e}")
        return {"success": False, "error": str(e)}


def scrape_boards() -> list:
    """Scrape list of available boards."""
    logger.info("Scraping boards list...")

    result = fetch_with_rate_limit(f"{LOBCHAN_API_BASE}/api/boards")
    if result["success"] and not result.get("is_html"):
        data = result["data"]
        if isinstance(data, dict) and "boards" in data:
            boards = data["boards"]
            logger.info(f"Found {len(boards)} boards")
            return boards

    logger.warning("Could not fetch boards")
    return []


def scrape_board_threads(board_id: str) -> list:
    """Scrape threads from a specific board."""
    logger.info(f"Scraping threads from /{board_id}/...")

    result = fetch_with_rate_limit(f"{LOBCHAN_API_BASE}/api/boards/{board_id}/threads")
    if result["success"] and not result.get("is_html"):
        data = result["data"]
        if isinstance(data, dict) and "threads" in data:
            threads = data["threads"]
            logger.info(f"Found {len(threads)} threads in /{board_id}/")
            return threads

    return []


def scrape_thread(board_id: str, thread_id: str) -> dict:
    """Scrape a single thread with all posts."""
    logger.info(f"Scraping thread /{board_id}/{thread_id}...")

    endpoints = [
        f"{LOBCHAN_API_BASE}/api/boards/{board_id}/threads/{thread_id}",
        f"{LOBCHAN_API_BASE}/{board_id}/thread/{thread_id}.json"
    ]

    for endpoint in endpoints:
        result = fetch_with_rate_limit(endpoint)
        if result["success"] and not result.get("is_html"):
            return result["data"]

    return {}


def save_boards(boards: list):
    """Save boards to database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for board in boards:
        board_id = board.get("id")
        if not board_id:
            continue

        cursor.execute("""
            INSERT OR REPLACE INTO lobchan_boards
            (id, name, description, post_count, created_at, last_scraped)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            board_id,
            board.get("name", board_id),
            board.get("description", ""),
            board.get("activeThreadCount", 0),
            board.get("createdAt"),
            datetime.now().isoformat()
        ))

    conn.commit()
    conn.close()
    logger.info(f"Saved {len(boards)} boards")


def save_threads(threads: list, board_id: str) -> int:
    """Save threads and their posts to database. Returns post count."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    post_count = 0

    for thread in threads:
        thread_id = thread.get("id")
        if not thread_id:
            continue

        # Get OP post content
        posts = thread.get("posts", [])
        op_post = posts[0] if posts else {}
        op_content = op_post.get("content", "")

        cursor.execute("""
            INSERT OR REPLACE INTO lobchan_threads
            (id, board_id, title, content, image_url, reply_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            thread_id,
            board_id,
            thread.get("title", ""),
            op_content,
            op_post.get("mediaUrl"),
            thread.get("replyCount", 0),
            thread.get("createdAt")
        ))

        # Save all posts
        for post in posts:
            post_id = post.get("id")
            if not post_id:
                continue

            cursor.execute("""
                INSERT OR REPLACE INTO lobchan_posts
                (id, thread_id, board_id, content, image_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                post_id,
                thread_id,
                board_id,
                post.get("content", ""),
                post.get("mediaUrl"),
                post.get("createdAt")
            ))
            post_count += 1

    conn.commit()
    conn.close()
    logger.info(f"Saved {len(threads)} threads, {post_count} posts from /{board_id}/")
    return post_count


def save_posts(posts: list, thread_id: str, board_id: str):
    """Save posts to database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for post in posts:
        post_id = post.get("id") or post.get("no")
        if not post_id:
            continue

        cursor.execute("""
            INSERT OR REPLACE INTO lobchan_posts
            (id, thread_id, board_id, content, image_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(post_id),
            thread_id,
            board_id,
            post.get("content") or post.get("com", ""),
            post.get("image_url") or post.get("tim"),
            post.get("created_at") or post.get("time")
        ))

    conn.commit()
    conn.close()


def full_scrape():
    """Run full scrape of lobchan.ai."""
    logger.info("Starting full lobchan scrape...")
    ensure_dirs()
    init_db()

    stats = {
        "boards": 0,
        "threads": 0,
        "posts": 0,
        "errors": []
    }

    # 1. Scrape boards
    boards = scrape_boards()
    if boards:
        save_boards(boards)
        stats["boards"] = len(boards)

    # 2. Scrape threads from each board
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM lobchan_boards")
    board_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    for board_id in board_ids:
        try:
            threads = scrape_board_threads(board_id)
            if threads:
                post_count = save_threads(threads, board_id)
                stats["threads"] += len(threads)
                stats["posts"] += post_count
        except Exception as e:
            logger.error(f"Error scraping /{board_id}/: {e}")
            stats["errors"].append(f"/{board_id}/: {e}")

    # 3. Save raw data
    raw_file = RAW_DIR / f"lobchan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(raw_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    logger.info(f"Scrape complete: {stats['boards']} boards, {stats['threads']} threads")
    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description="lobchan.ai Scraper")
    parser.add_argument("command", choices=["boards", "threads", "full", "init"],
                       help="Command to run")

    args = parser.parse_args()

    if args.command == "init":
        init_db()
        print("Database initialized")
    elif args.command == "boards":
        init_db()
        boards = scrape_boards()
        print(json.dumps(boards, indent=2))
    elif args.command == "threads":
        init_db()
        # Quick test - just show what we'd scrape
        print("Would scrape threads from all known boards")
        print("Run 'full' for complete scrape")
    elif args.command == "full":
        stats = full_scrape()
        print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
