#!/usr/bin/env python3
"""Diff Engine - compares scans and detects changes."""

import sys
import sqlite3
import json
from datetime import datetime
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Import centralized config
from config import DB_PATH


def get_scan_posts(conn, scan_id: str) -> dict:
    """Get posts from a specific scan period."""
    cursor = conn.cursor()
    cursor.execute("SELECT stats FROM scans WHERE id = ?", (scan_id,))
    row = cursor.fetchone()
    if row and row[0]:
        stats = json.loads(row[0])
        return stats
    return {}


def compare_scans(conn) -> dict:
    """Compare the two most recent scans."""
    cursor = conn.cursor()

    # Get last 2 scans
    cursor.execute("SELECT id, timestamp, stats FROM scans ORDER BY timestamp DESC LIMIT 2")
    scans = cursor.fetchall()

    if len(scans) < 2:
        return {"error": "Need at least 2 scans to compare", "scans_found": len(scans)}

    current_scan = {"id": scans[0][0], "timestamp": scans[0][1], "stats": json.loads(scans[0][2] or "{}")}
    previous_scan = {"id": scans[1][0], "timestamp": scans[1][1], "stats": json.loads(scans[1][2] or "{}")}

    # Get all posts
    cursor.execute("SELECT id, title, author, submolt, votes_net, comment_count, scraped_at FROM posts ORDER BY scraped_at DESC")
    all_posts = cursor.fetchall()

    # Find new posts (by comparing post IDs or titles)
    cursor.execute("""
        SELECT DISTINCT p.id, p.title, p.author, p.submolt, p.votes_net, p.comment_count
        FROM posts p
        WHERE p.scraped_at > ?
        ORDER BY p.comment_count DESC
    """, (previous_scan["timestamp"],))
    new_posts = cursor.fetchall()

    # Find posts with biggest engagement changes
    # (comparing current comment_count with what we might have stored before)

    # Get top movers (highest comment counts in current data)
    cursor.execute("""
        SELECT id, title, author, submolt, votes_net, comment_count
        FROM posts
        ORDER BY comment_count DESC
        LIMIT 10
    """)
    top_posts = cursor.fetchall()

    # New authors since last scan
    cursor.execute("""
        SELECT DISTINCT author FROM posts
        WHERE scraped_at > ?
    """, (previous_scan["timestamp"],))
    new_authors = [row[0] for row in cursor.fetchall()]

    # Build diff report
    diff = {
        "compared": {
            "current": current_scan["id"],
            "previous": previous_scan["id"],
            "time_span": f"{previous_scan['timestamp']} -> {current_scan['timestamp']}"
        },
        "new_posts": [
            {
                "title": p[1][:60] if p[1] else "Unknown",
                "author": p[2],
                "submolt": p[3],
                "votes": p[4],
                "comments": p[5]
            }
            for p in new_posts[:10]
        ],
        "new_authors": new_authors[:10],
        "top_current": [
            {
                "title": p[1][:60] if p[1] else "Unknown",
                "author": p[2],
                "comments": p[5],
                "votes": p[4]
            }
            for p in top_posts[:5]
        ],
        "stats_change": {
            "posts_current": current_scan["stats"].get("total_posts_scanned", 0),
            "posts_previous": previous_scan["stats"].get("total_posts_scanned", 0),
        }
    }

    return diff


def print_diff_report(diff: dict):
    """Print human-readable diff report."""

    if "error" in diff:
        print(f"[!] {diff['error']}")
        return

    print("\n" + "=" * 60)
    print("  DIFF REPORT - Changes Since Last Scan")
    print("=" * 60)

    print(f"\n  Period: {diff['compared']['time_span']}")
    print(f"  Scans: {diff['compared']['previous']} -> {diff['compared']['current']}")

    # New posts
    print("\n>> NOWE POSTY")
    print("-" * 40)
    if diff["new_posts"]:
        for i, post in enumerate(diff["new_posts"][:5], 1):
            print(f"  {i}. [{post['votes']:+d}] {post['title']}")
            print(f"     {post['author']} | m/{post['submolt']} | {post['comments']} comments")
    else:
        print("  Brak nowych postow")

    # New authors
    if diff["new_authors"]:
        print("\n>> NOWI AUTORZY")
        print("-" * 40)
        print(f"  {', '.join(diff['new_authors'][:10])}")

    # Current top
    print("\n>> OBECNY TOP 5")
    print("-" * 40)
    for i, post in enumerate(diff["top_current"], 1):
        print(f"  {i}. {post['title']}")
        print(f"     {post['comments']} comments | {post['votes']:+d} votes")

    print("\n" + "=" * 60)


def get_diff_summary() -> str:
    """Get diff as text summary for Kimi analysis."""
    if not DB_PATH.exists():
        return "Database not found"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    diff = compare_scans(conn)
    conn.close()

    if "error" in diff:
        return diff["error"]

    summary = f"""DIFF REPORT
Period: {diff['compared']['time_span']}

NEW POSTS ({len(diff['new_posts'])}):
"""
    for post in diff["new_posts"][:5]:
        summary += f"- {post['title']} by {post['author']} ({post['comments']} comments)\n"

    if diff["new_authors"]:
        summary += f"\nNEW AUTHORS: {', '.join(diff['new_authors'][:5])}\n"

    summary += "\nCURRENT TOP:\n"
    for post in diff["top_current"]:
        summary += f"- {post['title']} ({post['comments']} comments)\n"

    return summary


if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"[ERROR] Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    diff = compare_scans(conn)
    print_diff_report(diff)
    conn.close()
