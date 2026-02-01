#!/usr/bin/env python3
"""Run the Scanner agent to collect data from Moltbook."""

import sys
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from moltbook_api import MoltbookAPI, get_api
from config import DB_PATH, setup_logging

logger = setup_logging("scanner")

# Validation constants
MAX_CONTENT_LENGTH = 50000  # Max characters for content
MAX_TITLE_LENGTH = 500
MAX_USERNAME_LENGTH = 100


def generate_scan_id() -> str:
    """Generate unique scan ID."""
    now = datetime.now()
    return f"scan_{now.strftime('%Y%m%d_%H%M%S')}"


def validate_post(post: dict) -> Tuple[bool, dict, List[str]]:
    """Validate and sanitize post data from API.

    Returns:
        Tuple of (is_valid, sanitized_post, warnings)
    """
    warnings = []

    # Check required field: id
    if not post.get("id"):
        return False, post, ["Missing required field: id"]

    sanitized = post.copy()

    # Validate and sanitize id
    post_id = post.get("id")
    if not isinstance(post_id, (str, int)):
        return False, post, [f"Invalid id type: {type(post_id)}"]
    sanitized["id"] = str(post_id)

    # Validate numeric fields
    for field in ["upvotes", "downvotes", "comment_count"]:
        value = post.get(field, 0)
        if isinstance(value, list):
            sanitized[field] = len(value)
            warnings.append(f"{field} was list, converted to length")
        elif not isinstance(value, (int, float)):
            try:
                sanitized[field] = int(value) if value else 0
            except (ValueError, TypeError):
                sanitized[field] = 0
                warnings.append(f"Invalid {field}, defaulting to 0")
        else:
            sanitized[field] = int(value)

    # Validate and truncate text fields
    title = post.get("title", "")
    if title and len(title) > MAX_TITLE_LENGTH:
        sanitized["title"] = title[:MAX_TITLE_LENGTH] + "..."
        warnings.append(f"Title truncated from {len(title)} to {MAX_TITLE_LENGTH}")

    content = post.get("content", "")
    if content and len(content) > MAX_CONTENT_LENGTH:
        sanitized["content"] = content[:MAX_CONTENT_LENGTH] + "... [truncated]"
        warnings.append(f"Content truncated from {len(content)} to {MAX_CONTENT_LENGTH}")

    # Validate author
    author = post.get("author", {})
    if isinstance(author, dict):
        author_name = author.get("name", "")
        if author_name and len(author_name) > MAX_USERNAME_LENGTH:
            author["name"] = author_name[:MAX_USERNAME_LENGTH]
            warnings.append(f"Author name truncated")
        sanitized["author"] = author
    elif author:
        author_str = str(author)[:MAX_USERNAME_LENGTH]
        sanitized["author"] = {"name": author_str}

    # Validate created_at
    created_at = post.get("created_at")
    if created_at:
        try:
            # Check if it's a valid ISO format or parseable date
            if isinstance(created_at, str):
                datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            sanitized["created_at"] = datetime.now().isoformat()
            warnings.append(f"Invalid created_at, using current time")

    return True, sanitized, warnings


def calculate_controversy(post: dict) -> float:
    """Calculate controversy score for a post."""
    upvotes = post.get("upvotes", 0)
    downvotes = post.get("downvotes", 0)
    comments = post.get("comment_count", post.get("comments", 0))

    if isinstance(comments, list):
        comments = len(comments)

    net_votes = upvotes - downvotes
    if net_votes == 0:
        return float(comments) if comments > 0 else 0.0
    return comments / abs(net_votes)


def save_posts_to_db(posts: List[dict], conn: sqlite3.Connection) -> Tuple[int, int]:
    """Save posts to database with validation.

    Returns:
        Tuple of (saved_count, skipped_count)
    """
    cursor = conn.cursor()
    saved = 0
    skipped = 0

    for post in posts:
        # Validate post before saving
        is_valid, sanitized, warnings = validate_post(post)

        if not is_valid:
            logger.warning(f"Skipping invalid post: {warnings}")
            skipped += 1
            continue

        if warnings:
            logger.debug(f"Post {sanitized.get('id')} warnings: {warnings}")

        author = sanitized.get("author", {})
        if isinstance(author, dict):
            author_name = author.get("name", "Unknown")
            author_id = author.get("id")
        else:
            author_name = str(author)
            author_id = None

        submolt = sanitized.get("submolt", {})
        if isinstance(submolt, dict):
            submolt_name = submolt.get("name", "general")
            submolt_id = submolt.get("id")
        else:
            submolt_name = str(submolt) if submolt else "general"
            submolt_id = None

        upvotes = sanitized.get("upvotes", 0)
        downvotes = sanitized.get("downvotes", 0)
        comment_count = sanitized.get("comment_count", 0)

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO posts
                (id, author, author_id, submolt, submolt_id, title, content,
                 content_sanitized, url, upvotes, downvotes, votes_net,
                 comment_count, controversy_score, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sanitized.get("id"),
                author_name,
                author_id,
                submolt_name,
                submolt_id,
                sanitized.get("title"),
                sanitized.get("content"),
                sanitized.get("content_sanitized"),
                f"https://moltbook.com/post/{sanitized.get('id')}",
                upvotes,
                downvotes,
                upvotes - downvotes,
                comment_count,
                calculate_controversy(sanitized),
                sanitized.get("created_at"),
                datetime.now().isoformat()
            ))
            saved += 1
        except sqlite3.Error as e:
            logger.error(f"Database error saving post {sanitized.get('id')}: {e}")
            skipped += 1

    conn.commit()
    return saved, skipped


def save_scan_to_db(scan: dict, conn: sqlite3.Connection):
    """Save scan report to database."""
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO scans
        (id, timestamp, period, sort_method, posts_scanned,
         top_posts, top_authors, active_submolts, alerts, stats)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        scan["scan_id"],
        scan["timestamp"],
        scan["period"],
        scan.get("sort_method", "hot"),
        scan["stats"]["total_posts_scanned"],
        json.dumps(scan["top_posts"]),
        json.dumps(scan["top_authors"]),
        json.dumps(scan["active_submolts"]),
        json.dumps(scan["alerts"]),
        json.dumps(scan["stats"])
    ))

    conn.commit()


def update_actors(posts: List[dict], conn: sqlite3.Connection):
    """Update actors table with post authors."""
    cursor = conn.cursor()

    author_stats = {}
    for post in posts:
        author = post.get("author", {})
        if isinstance(author, dict):
            name = author.get("name")
            author_id = author.get("id")
            karma = author.get("karma")
            followers = author.get("follower_count")
        else:
            name = str(author)
            author_id = None
            karma = None
            followers = None

        if not name:
            continue

        if name not in author_stats:
            author_stats[name] = {
                "user_id": author_id,
                "karma": karma,
                "followers": followers,
                "posts": 0,
                "total_engagement": 0,
                "submolts": set()
            }

        author_stats[name]["posts"] += 1
        engagement = post.get("upvotes", 0) + post.get("comment_count", 0)
        author_stats[name]["total_engagement"] += engagement

        submolt = post.get("submolt", {})
        if isinstance(submolt, dict):
            author_stats[name]["submolts"].add(submolt.get("name", "general"))
        elif submolt:
            author_stats[name]["submolts"].add(str(submolt))

    for name, stats in author_stats.items():
        avg_engagement = stats["total_engagement"] / stats["posts"] if stats["posts"] > 0 else 0

        cursor.execute("""
            INSERT INTO actors (username, user_id, karma, follower_count,
                               first_seen, last_seen, total_posts, avg_engagement, submolts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                last_seen = excluded.last_seen,
                total_posts = actors.total_posts + excluded.total_posts,
                avg_engagement = (actors.avg_engagement + excluded.avg_engagement) / 2,
                karma = COALESCE(excluded.karma, actors.karma),
                follower_count = COALESCE(excluded.follower_count, actors.follower_count),
                updated_at = CURRENT_TIMESTAMP
        """, (
            name,
            stats["user_id"],
            stats["karma"],
            stats["followers"],
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            stats["posts"],
            avg_engagement,
            json.dumps(list(stats["submolts"]))
        ))

    conn.commit()


def run_scanner(limit: int = 50, deep: bool = False) -> dict:
    """Run the scanner and collect data.

    Args:
        limit: Posts per category (hot/new)
        deep: If True, do deep scan with pagination and multiple submolts
    """
    print(f"[Scanner] Starting {'DEEP ' if deep else ''}scan at {datetime.now().isoformat()}")

    api = get_api()
    scan_id = generate_scan_id()
    all_posts = []
    existing_ids = set()

    if deep:
        # Deep scan: multiple pages + all submolts
        total_per_sort = limit * 4  # 4x more posts

        # Fetch hot posts with pagination
        print("[Scanner] Fetching hot posts (paginated)...")
        hot_posts = api.get_posts_paginated("hot", total_limit=total_per_sort, per_page=50)
        if hot_posts:
            for p in hot_posts:
                if p.get("id") not in existing_ids:
                    existing_ids.add(p.get("id"))
                    all_posts.append(p)
            print(f"  Got {len(hot_posts)} hot posts")

        # Fetch new posts with pagination
        print("[Scanner] Fetching new posts (paginated)...")
        new_posts = api.get_posts_paginated("new", total_limit=total_per_sort, per_page=50)
        if new_posts:
            new_unique = [p for p in new_posts if p.get("id") not in existing_ids]
            for p in new_unique:
                existing_ids.add(p.get("id"))
            all_posts.extend(new_unique)
            print(f"  Got {len(new_unique)} new unique posts")

        # Fetch from top submolts (expanded list)
        submolts_to_scan = [
            "general", "ethics", "philosophy", "offmychest", "ponderings",
            "infrastructure", "trading", "clawdbot", "agents", "crypto",
            "agentfinance", "introductions", "todayilearned", "whatami",
            "llm-absurdism", "announcements", "blesstheirhearts", "creative",
            "technical", "governance", "coordination", "memory"
        ]
        for submolt in submolts_to_scan:
            print(f"[Scanner] Fetching from m/{submolt}...")
            submolt_posts = api.get_posts("hot", limit=50, submolt=submolt)
            if submolt_posts:
                new_from_submolt = [p for p in submolt_posts if p.get("id") not in existing_ids]
                for p in new_from_submolt:
                    existing_ids.add(p.get("id"))
                all_posts.extend(new_from_submolt)
                print(f"  Got {len(new_from_submolt)} new from m/{submolt}")
    else:
        # Standard scan: just hot + new
        print("[Scanner] Fetching hot posts...")
        hot_posts = api.get_posts("hot", limit=limit)
        if hot_posts:
            for p in hot_posts:
                existing_ids.add(p.get("id"))
            all_posts.extend(hot_posts)
            print(f"  Got {len(hot_posts)} hot posts")

        print("[Scanner] Fetching new posts...")
        new_posts = api.get_posts("new", limit=limit)
        if new_posts:
            new_unique = [p for p in new_posts if p.get("id") not in existing_ids]
            all_posts.extend(new_unique)
            print(f"  Got {len(new_unique)} new unique posts")

    if not all_posts:
        print("[Scanner] ERROR: No posts fetched")
        return {"error": "No posts fetched"}

    # Calculate metrics
    for post in all_posts:
        post["controversy_score"] = calculate_controversy(post)

    # Sort by engagement (comments + votes)
    all_posts.sort(key=lambda p: p.get("comment_count", 0) + p.get("upvotes", 0), reverse=True)

    # Get top posts
    top_posts = []
    for p in all_posts[:10]:
        author = p.get("author", {})
        if isinstance(author, dict):
            author_name = author.get("name", "Unknown")
        else:
            author_name = str(author)

        submolt = p.get("submolt", {})
        if isinstance(submolt, dict):
            submolt_name = submolt.get("name", "general")
        else:
            submolt_name = str(submolt) if submolt else "general"

        top_posts.append({
            "id": p.get("id"),
            "author": author_name,
            "submolt": submolt_name,
            "title": p.get("title", "")[:100],
            "votes": p.get("upvotes", 0) - p.get("downvotes", 0),
            "comments": p.get("comment_count", 0),
            "controversy_score": round(p.get("controversy_score", 0), 2),
            "url": f"https://moltbook.com/post/{p.get('id')}"
        })

    # Get top authors
    author_counts = {}
    for p in all_posts:
        author = p.get("author", {})
        name = author.get("name") if isinstance(author, dict) else str(author)
        if name:
            if name not in author_counts:
                author_counts[name] = {"posts": 0, "engagement": 0}
            author_counts[name]["posts"] += 1
            author_counts[name]["engagement"] += p.get("upvotes", 0) + p.get("comment_count", 0)

    top_authors = [
        {"username": name, "posts": data["posts"],
         "avg_engagement": round(data["engagement"] / data["posts"], 1)}
        for name, data in sorted(author_counts.items(),
                                  key=lambda x: x[1]["engagement"], reverse=True)[:10]
    ]

    # Get active submolts
    submolt_counts = {}
    for p in all_posts:
        submolt = p.get("submolt", {})
        name = submolt.get("name") if isinstance(submolt, dict) else str(submolt) or "general"
        if name not in submolt_counts:
            submolt_counts[name] = {"posts": 0, "engagement": 0}
        submolt_counts[name]["posts"] += 1
        submolt_counts[name]["engagement"] += p.get("upvotes", 0) + p.get("comment_count", 0)

    active_submolts = [
        {"name": f"m/{name}", "new_posts": data["posts"], "total_engagement": data["engagement"]}
        for name, data in sorted(submolt_counts.items(),
                                  key=lambda x: x[1]["engagement"], reverse=True)[:10]
    ]

    # Generate alerts
    alerts = []
    for p in all_posts:
        comments = p.get("comment_count", 0)
        controversy = p.get("controversy_score", 0)

        if comments > 200:
            alerts.append({
                "type": "high_engagement",
                "post_id": p.get("id"),
                "details": f"Post has {comments} comments"
            })

        if controversy > 5:
            alerts.append({
                "type": "high_controversy",
                "post_id": p.get("id"),
                "details": f"Controversy score: {controversy:.1f}"
            })

    # Build scan report
    scan = {
        "scan_id": scan_id,
        "timestamp": datetime.now().isoformat(),
        "period": "last_1h",
        "sort_method": "hot+new",
        "top_posts": top_posts,
        "top_authors": top_authors,
        "active_submolts": active_submolts,
        "alerts": alerts[:10],
        "stats": {
            "total_posts_scanned": len(all_posts),
            "total_comments": sum(p.get("comment_count", 0) for p in all_posts),
            "avg_controversy": round(
                sum(p.get("controversy_score", 0) for p in all_posts) / len(all_posts), 2
            ) if all_posts else 0
        }
    }

    # Save to database
    print("[Scanner] Saving to database...")
    conn = sqlite3.connect(DB_PATH)
    saved, skipped = save_posts_to_db(all_posts, conn)
    save_scan_to_db(scan, conn)
    update_actors(all_posts, conn)
    conn.close()

    print(f"[Scanner] Scan complete: {scan_id}")
    print(f"  Posts fetched: {len(all_posts)}")
    print(f"  Posts saved: {saved}")
    if skipped > 0:
        print(f"  Posts skipped (invalid): {skipped}")
        logger.warning(f"Skipped {skipped} invalid posts during scan {scan_id}")
    print(f"  Top authors: {len(top_authors)}")
    print(f"  Active submolts: {len(active_submolts)}")
    print(f"  Alerts: {len(alerts)}")

    return scan


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Moltbook Scanner")
    parser.add_argument("--limit", type=int, default=250, help="Number of posts to fetch per sort (default: 250)")
    parser.add_argument("--deep", action="store_true", help="Deep scan with pagination and all submolts")
    parser.add_argument("--output", help="Output file for scan report (optional)")
    args = parser.parse_args()

    scan = run_scanner(limit=args.limit, deep=args.deep)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(scan, f, indent=2, ensure_ascii=False)
        print(f"Scan saved to: {args.output}")
    else:
        print("\nTop 5 posts:")
        for i, p in enumerate(scan.get("top_posts", [])[:5], 1):
            print(f"  {i}. [{p['votes']:+}] {p['title'][:50]}... ({p['comments']} comments)")

    print(f"\nTotal posts in database now: run 'python init_db.py --check' to verify")
