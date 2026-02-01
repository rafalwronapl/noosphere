#!/usr/bin/env python3
"""Initialize the Moltbook Observatory database."""

import sys
import sqlite3
import os
from pathlib import Path
from datetime import datetime

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "observatory.db"


def init_db():
    """Initialize the SQLite database with all required tables."""

    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Creating tables...")

    # Posts table (raw data from Scanner)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            author TEXT NOT NULL,
            author_id TEXT,
            submolt TEXT,
            submolt_id TEXT,
            title TEXT,
            content TEXT,
            content_sanitized TEXT,
            url TEXT,
            upvotes INTEGER DEFAULT 0,
            downvotes INTEGER DEFAULT 0,
            votes_net INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            controversy_score REAL,
            created_at DATETIME,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME
        )
    """)
    print("  - posts")

    # Comments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id TEXT PRIMARY KEY,
            post_id TEXT NOT NULL,
            parent_id TEXT,
            author TEXT,
            author_id TEXT,
            content TEXT,
            content_sanitized TEXT,
            upvotes INTEGER DEFAULT 0,
            downvotes INTEGER DEFAULT 0,
            created_at DATETIME,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)
    print("  - comments")

    # Scans table (Scanner reports)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id TEXT PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            period TEXT,
            sort_method TEXT,
            posts_scanned INTEGER,
            top_posts JSON,
            top_authors JSON,
            active_submolts JSON,
            alerts JSON,
            stats JSON
        )
    """)
    print("  - scans")

    # Patterns table (Analyst findings)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            period_analyzed TEXT,
            scans_included JSON,
            pattern_type TEXT,
            name TEXT,
            description TEXT,
            direction TEXT,
            change_percent REAL,
            velocity TEXT,
            confidence REAL,
            evidence JSON
        )
    """)
    print("  - patterns")

    # Interpretations table (Interpreter insights)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interpretations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interpretation_id TEXT,
            analysis_ref TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            category TEXT,
            observation TEXT,
            meaning TEXT,
            implications TEXT,
            risk_level TEXT,
            urgency TEXT,
            recommendations JSON,
            questions JSON,
            meta_reflection TEXT
        )
    """)
    print("  - interpretations")

    # Briefs table (Editor daily briefs)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS briefs (
            id TEXT PRIMARY KEY,
            date DATE,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            period TEXT,
            sources JSON,
            headline TEXT,
            alerts JSON,
            top_stories JSON,
            trends_summary JSON,
            actors_to_watch JSON,
            recommendations JSON,
            meta JSON
        )
    """)
    print("  - briefs")

    # Actors table (tracked agents/users)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actors (
            username TEXT PRIMARY KEY,
            user_id TEXT,
            description TEXT,
            karma INTEGER,
            follower_count INTEGER,
            first_seen DATETIME,
            last_seen DATETIME,
            total_posts INTEGER DEFAULT 0,
            avg_engagement REAL,
            submolts JSON,
            notes TEXT,
            watch_level TEXT DEFAULT 'normal',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  - actors")

    # Submolts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS submolts (
            name TEXT PRIMARY KEY,
            submolt_id TEXT,
            display_name TEXT,
            description TEXT,
            member_count INTEGER,
            post_count INTEGER,
            first_seen DATETIME,
            last_activity DATETIME,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  - submolts")

    # Request log table (for security auditing)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS request_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            endpoint TEXT,
            method TEXT,
            params JSON,
            status_code INTEGER,
            response_size INTEGER,
            duration_ms INTEGER
        )
    """)
    print("  - request_log")

    # Create indexes
    print("\nCreating indexes...")
    indexes = [
        ("idx_posts_author", "posts", "author"),
        ("idx_posts_submolt", "posts", "submolt"),
        ("idx_posts_scraped", "posts", "scraped_at"),
        ("idx_posts_created", "posts", "created_at"),
        ("idx_comments_post", "comments", "post_id"),
        ("idx_comments_author", "comments", "author"),
        ("idx_patterns_type", "patterns", "pattern_type"),
        ("idx_patterns_analysis", "patterns", "analysis_id"),
        ("idx_interpretations_category", "interpretations", "category"),
        ("idx_briefs_date", "briefs", "date"),
        ("idx_actors_watch", "actors", "watch_level"),
        ("idx_request_log_timestamp", "request_log", "timestamp"),
    ]

    for idx_name, table, column in indexes:
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
        print(f"  - {idx_name}")

    conn.commit()
    conn.close()

    print(f"\n[OK] Database initialized at: {DB_PATH}")
    print(f"Tables: posts, comments, scans, patterns, interpretations, briefs, actors, submolts, request_log")


def check_db():
    """Check database status."""
    if not DB_PATH.exists():
        print(f"[!] Database not found at {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"Database: {DB_PATH}")
    print(f"Size: {DB_PATH.stat().st_size / 1024:.1f} KB")
    print("\nTable counts:")

    tables = ["posts", "comments", "scans", "patterns", "interpretations", "briefs", "actors", "submolts"]
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count}")

    conn.close()
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Initialize Moltbook Observatory database")
    parser.add_argument("--check", action="store_true", help="Check database status")
    parser.add_argument("--reset", action="store_true", help="Reset database (delete and recreate)")
    args = parser.parse_args()

    if args.check:
        check_db()
    elif args.reset:
        if DB_PATH.exists():
            confirm = input(f"Delete {DB_PATH}? [y/N] ")
            if confirm.lower() == 'y':
                DB_PATH.unlink()
                print("Database deleted.")
                init_db()
        else:
            init_db()
    else:
        init_db()
