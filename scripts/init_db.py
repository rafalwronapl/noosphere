#!/usr/bin/env python3
"""
Initialize the Noosphere Project database.

This script creates ALL tables used by the project in one place.
Run with --check to see database status, --reset to recreate.
"""

import sys
import sqlite3
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

    print("=" * 50)
    print("  NOOSPHERE PROJECT - DATABASE INITIALIZATION")
    print("=" * 50)
    print("\nCreating tables...")

    # =========================================================================
    # CORE DATA TABLES
    # =========================================================================

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
            is_prompt_injection INTEGER DEFAULT 0,
            created_at DATETIME,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME
        )
    """)
    print("  ✓ posts")

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
            is_prompt_injection INTEGER DEFAULT 0,
            created_at DATETIME,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)
    print("  ✓ comments")

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
            network_centrality REAL,
            submolts JSON,
            notes TEXT,
            watch_level TEXT DEFAULT 'normal',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✓ actors")

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
    print("  ✓ submolts")

    # =========================================================================
    # INTERACTION & NETWORK TABLES
    # =========================================================================

    # Interactions table (for network analysis)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_from TEXT NOT NULL,
            author_to TEXT NOT NULL,
            interaction_type TEXT,
            post_id TEXT,
            comment_id TEXT,
            weight REAL DEFAULT 1.0,
            sentiment REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_from) REFERENCES actors(username),
            FOREIGN KEY (author_to) REFERENCES actors(username)
        )
    """)
    print("  ✓ interactions")

    # Conflicts table (disputes between actors)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conflicts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_a TEXT NOT NULL,
            actor_b TEXT NOT NULL,
            topic TEXT,
            trigger_post_id TEXT,
            trigger_comment_id TEXT,
            outcome TEXT,
            winner TEXT,
            intensity INTEGER DEFAULT 1,
            evidence JSON,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            resolved_at DATETIME,
            FOREIGN KEY (actor_a) REFERENCES actors(username),
            FOREIGN KEY (actor_b) REFERENCES actors(username)
        )
    """)
    print("  ✓ conflicts")

    # =========================================================================
    # MEME & CULTURE TABLES
    # =========================================================================

    # Memes table (viral phrases and cultural patterns)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase TEXT NOT NULL UNIQUE,
            phrase_hash TEXT,
            occurrence_count INTEGER DEFAULT 1,
            authors_count INTEGER DEFAULT 1,
            first_author TEXT,
            category TEXT,
            sentiment REAL,
            is_viral INTEGER DEFAULT 0,
            first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_seen_at DATETIME,
            post_ids JSON,
            author_list JSON
        )
    """)
    print("  ✓ memes")

    # Epistemic drift table (tracking belief/knowledge changes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS epistemic_drift (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept TEXT NOT NULL,
            definition_old TEXT,
            definition_new TEXT,
            drift_type TEXT,
            evidence JSON,
            actors_involved JSON,
            confidence REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✓ epistemic_drift")

    # =========================================================================
    # ACTOR ANALYSIS TABLES
    # =========================================================================

    # Actor roles table (classification results)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actor_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            primary_role TEXT,
            secondary_roles JSON,
            role_confidence REAL,
            behavioral_pattern TEXT,
            influence_score REAL,
            authenticity_score REAL,
            classification_method TEXT,
            evidence JSON,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES actors(username)
        )
    """)
    print("  ✓ actor_roles")

    # Reputation history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reputation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            reputation_score REAL,
            tier TEXT,
            change_reason TEXT,
            previous_score REAL,
            delta REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES actors(username)
        )
    """)
    print("  ✓ reputation_history")

    # Agent births table (tracking new agent appearances)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_births (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            first_post_id TEXT,
            first_comment_id TEXT,
            birth_context TEXT,
            apparent_purpose TEXT,
            initial_topics JSON,
            initial_connections JSON,
            birth_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES actors(username)
        )
    """)
    print("  ✓ agent_births")

    # =========================================================================
    # PIPELINE & REPORTING TABLES
    # =========================================================================

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
    print("  ✓ scans")

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
    print("  ✓ patterns")

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
    print("  ✓ interpretations")

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
    print("  ✓ briefs")

    # =========================================================================
    # SYSTEM TABLES
    # =========================================================================

    # Request log table (for API auditing)
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
    print("  ✓ request_log")

    # Feedback submissions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submitter_type TEXT,
            submitter_name TEXT,
            feedback_type TEXT,
            content TEXT,
            contact TEXT,
            status TEXT DEFAULT 'new',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✓ feedback")

    # =========================================================================
    # ADD MISSING COLUMNS TO EXISTING TABLES
    # =========================================================================

    print("\nChecking for missing columns...")

    # Helper to add column if not exists
    # NOTE: This uses f-strings but is safe because all inputs are hardcoded below.
    # Do NOT call this function with user-provided values.
    def add_column_if_missing(table, column, col_type, default=None):
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        if column not in columns:
            default_clause = f" DEFAULT {default}" if default is not None else ""
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}")
            print(f"  + Added {table}.{column}")
            return True
        return False

    # Add missing columns
    add_column_if_missing("posts", "is_prompt_injection", "INTEGER", 0)
    add_column_if_missing("comments", "is_prompt_injection", "INTEGER", 0)
    add_column_if_missing("actors", "network_centrality", "REAL", None)

    # =========================================================================
    # CREATE INDEXES
    # =========================================================================

    print("\nCreating indexes...")

    indexes = [
        # Core tables
        ("idx_posts_author", "posts", "author"),
        ("idx_posts_submolt", "posts", "submolt"),
        ("idx_posts_scraped", "posts", "scraped_at"),
        ("idx_posts_created", "posts", "created_at"),
        ("idx_comments_post", "comments", "post_id"),
        ("idx_comments_author", "comments", "author"),
        ("idx_actors_centrality", "actors", "network_centrality"),
        ("idx_actors_watch", "actors", "watch_level"),

        # Interaction tables
        ("idx_interactions_from", "interactions", "author_from"),
        ("idx_interactions_to", "interactions", "author_to"),
        ("idx_interactions_type", "interactions", "interaction_type"),
        ("idx_conflicts_actors", "conflicts", "actor_a"),
        ("idx_conflicts_topic", "conflicts", "topic"),

        # Meme tables
        ("idx_memes_phrase", "memes", "phrase"),
        ("idx_memes_category", "memes", "category"),
        ("idx_memes_viral", "memes", "is_viral"),

        # Actor analysis
        ("idx_actor_roles_user", "actor_roles", "username"),
        ("idx_actor_roles_role", "actor_roles", "primary_role"),
        ("idx_reputation_user", "reputation_history", "username"),
        ("idx_agent_births_user", "agent_births", "username"),

        # Pipeline tables
        ("idx_patterns_type", "patterns", "pattern_type"),
        ("idx_patterns_analysis", "patterns", "analysis_id"),
        ("idx_interpretations_category", "interpretations", "category"),
        ("idx_briefs_date", "briefs", "date"),

        # System tables
        ("idx_request_log_timestamp", "request_log", "timestamp"),
        ("idx_feedback_status", "feedback", "status"),
    ]

    for idx_name, table, column in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
            print(f"  ✓ {idx_name}")
        except sqlite3.OperationalError as e:
            print(f"  ! {idx_name}: {e}")

    conn.commit()
    conn.close()

    print("\n" + "=" * 50)
    print(f"  DATABASE INITIALIZED: {DB_PATH}")
    print("=" * 50)
    print(f"""
Tables created:
  Core:        posts, comments, actors, submolts
  Network:     interactions, conflicts
  Culture:     memes, epistemic_drift
  Analysis:    actor_roles, reputation_history, agent_births
  Pipeline:    scans, patterns, interpretations, briefs
  System:      request_log, feedback

Total: 16 tables
""")


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

    tables = [
        "posts", "comments", "actors", "submolts",
        "interactions", "conflicts",
        "memes", "epistemic_drift",
        "actor_roles", "reputation_history", "agent_births",
        "scans", "patterns", "interpretations", "briefs",
        "request_log", "feedback"
    ]

    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count}")
        except sqlite3.OperationalError:
            print(f"  {table}: [NOT FOUND]")

    conn.close()
    return True


def migrate_db():
    """Run migrations to add missing columns/tables to existing database."""
    if not DB_PATH.exists():
        print("No database found. Running full init...")
        init_db()
        return

    print("Running database migration...")
    init_db()  # init_db already handles "IF NOT EXISTS" and column additions
    print("Migration complete.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Initialize Noosphere Project database")
    parser.add_argument("--check", action="store_true", help="Check database status")
    parser.add_argument("--reset", action="store_true", help="Reset database (delete and recreate)")
    parser.add_argument("--migrate", action="store_true", help="Add missing tables/columns to existing DB")
    args = parser.parse_args()

    if args.check:
        check_db()
    elif args.migrate:
        migrate_db()
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
