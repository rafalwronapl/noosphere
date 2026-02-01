#!/usr/bin/env python3
"""
D. Reputation Economy - explicit reputation scoring.
Reputation = currency in agent society.
"""

import sys
import sqlite3
import math
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Use centralized config
try:
    from config import DB_PATH, setup_logging
    logger = setup_logging("analyze_reputation")
except ImportError:
    DB_PATH = Path.home() / "moltbook-observatory" / "data" / "observatory.db"
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("analyze_reputation")

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def create_reputation_table(cursor):
    """Create reputation tracking table."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reputation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            timestamp DATETIME,
            reputation_score REAL,
            influence_score REAL,
            engagement_score REAL,
            controversy_score REAL,
            consistency_score REAL,
            delta_24h REAL,
            delta_7d REAL,
            rank INTEGER,
            tier TEXT,
            shock_events TEXT,
            UNIQUE(username, timestamp)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rep_user ON reputation_history(username)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rep_time ON reputation_history(timestamp)")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reputation_shocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            timestamp DATETIME,
            shock_type TEXT,  -- viral_post, controversy, conflict_win, conflict_loss, silence
            magnitude REAL,
            trigger_content TEXT,
            before_score REAL,
            after_score REAL
        )
    """)


def calculate_engagement_score(cursor, username):
    """Calculate engagement score from upvotes/downvotes."""
    cursor.execute("""
        SELECT COALESCE(SUM(upvotes), 0), COALESCE(SUM(downvotes), 0)
        FROM posts WHERE author = ?
    """, (username,))
    post_up, post_down = cursor.fetchone()

    cursor.execute("""
        SELECT COALESCE(SUM(upvotes), 0), COALESCE(SUM(downvotes), 0)
        FROM comments WHERE author = ?
    """, (username,))
    comment_up, comment_down = cursor.fetchone()

    total_up = (post_up or 0) + (comment_up or 0)
    total_down = (post_down or 0) + (comment_down or 0)

    # Score: upvotes with penalty for downvotes
    raw_score = total_up - (total_down * 0.5)

    # Normalize with log scale
    return math.log1p(max(0, raw_score))


def calculate_influence_score(cursor, username):
    """Calculate influence from network position."""
    cursor.execute("""
        SELECT network_centrality FROM actors WHERE username = ?
    """, (username,))
    result = cursor.fetchone()
    centrality = result[0] if result and result[0] else 0

    # Incoming interactions (people respond to them)
    cursor.execute("""
        SELECT COUNT(DISTINCT author_from)
        FROM interactions
        WHERE author_to = ?
    """, (username,))
    unique_responders = cursor.fetchone()[0] or 0

    return (centrality * 50) + math.log1p(unique_responders)


def calculate_controversy_score(cursor, username):
    """Calculate controversy (high engagement + mixed sentiment)."""
    cursor.execute("""
        SELECT upvotes, downvotes, comment_count
        FROM posts WHERE author = ?
    """, (username,))

    total_controversy = 0
    for up, down, comments in cursor.fetchall():
        up = up or 0
        down = down or 0
        comments = comments or 0

        if up + down > 0:
            # Controversy = high engagement + polarization
            polarization = 1 - abs(up - down) / (up + down + 1)
            total_controversy += (up + down + comments) * polarization

    return math.log1p(total_controversy)


def calculate_consistency_score(cursor, username):
    """Calculate posting consistency (regular = higher)."""
    cursor.execute("""
        SELECT created_at FROM (
            SELECT created_at FROM posts WHERE author = ?
            UNION ALL
            SELECT created_at FROM comments WHERE author = ?
        ) ORDER BY created_at
    """, (username, username))

    timestamps = []
    for (ts,) in cursor.fetchall():
        if ts:
            try:
                if 'T' in ts:
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(ts[:19], '%Y-%m-%d %H:%M:%S')
                timestamps.append(dt)
            except:
                continue

    if len(timestamps) < 3:
        return 0

    # Calculate gaps between posts
    gaps = [(timestamps[i+1] - timestamps[i]).total_seconds() / 3600
            for i in range(len(timestamps)-1)]

    if not gaps:
        return 0

    # Lower variance = more consistent
    avg_gap = sum(gaps) / len(gaps)
    variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)

    # Invert: high consistency = low variance
    consistency = 1 / (1 + math.sqrt(variance) / 24)  # Normalize by day

    return consistency * 10


def detect_shocks(cursor, username, current_score):
    """Detect reputation shock events."""
    shocks = []

    # Viral post (sudden high engagement)
    cursor.execute("""
        SELECT id, title, upvotes, created_at
        FROM posts
        WHERE author = ? AND upvotes > 50
        ORDER BY upvotes DESC
        LIMIT 3
    """, (username,))

    for post_id, title, upvotes, ts in cursor.fetchall():
        shocks.append({
            'type': 'viral_post',
            'magnitude': math.log1p(upvotes),
            'trigger': title[:100] if title else 'Untitled',
            'timestamp': ts
        })

    # Conflict wins/losses
    cursor.execute("""
        SELECT outcome, COUNT(*) as cnt
        FROM conflicts
        WHERE (actor_a = ? OR actor_b = ?) AND winner IS NOT NULL
        GROUP BY outcome
    """, (username, username))

    for outcome, count in cursor.fetchall():
        if 'won' in (outcome or ''):
            shocks.append({
                'type': 'conflict_wins',
                'magnitude': count * 2,
                'trigger': f'{count} conflict victories',
                'timestamp': datetime.now().isoformat()
            })

    return shocks


def calculate_reputation_score(engagement, influence, controversy, consistency):
    """Calculate composite reputation score."""
    # Weights
    w_engagement = 0.35
    w_influence = 0.30
    w_consistency = 0.20
    w_controversy = 0.15  # Controversy can be positive (attention)

    raw_score = (
        engagement * w_engagement +
        influence * w_influence +
        consistency * w_consistency +
        controversy * w_controversy
    )

    # Normalize to 0-100 scale
    return min(100, raw_score * 10)


def assign_tier(score, rank, total):
    """Assign reputation tier."""
    percentile = rank / total if total > 0 else 1

    if percentile <= 0.01:
        return 'legendary'
    elif percentile <= 0.05:
        return 'elite'
    elif percentile <= 0.15:
        return 'established'
    elif percentile <= 0.35:
        return 'rising'
    elif percentile <= 0.60:
        return 'active'
    else:
        return 'newcomer'


def run_reputation_analysis():
    """Run full reputation economy analysis."""
    print("=" * 60)
    print("  REPUTATION ECONOMY - Agent Currency")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    create_reputation_table(cursor)

    # Get all actors with activity
    cursor.execute("""
        SELECT DISTINCT username FROM actors
        WHERE username IN (
            SELECT author FROM comments GROUP BY author HAVING COUNT(*) >= 2
        )
    """)

    actors = [row[0] for row in cursor.fetchall()]
    print(f"\n>> Analyzing {len(actors)} actors...")

    scores = []
    for i, username in enumerate(actors):
        if i % 20 == 0:
            print(f"   Progress: {i}/{len(actors)}")

        engagement = calculate_engagement_score(cursor, username)
        influence = calculate_influence_score(cursor, username)
        controversy = calculate_controversy_score(cursor, username)
        consistency = calculate_consistency_score(cursor, username)

        rep_score = calculate_reputation_score(engagement, influence, controversy, consistency)

        shocks = detect_shocks(cursor, username, rep_score)

        scores.append({
            'username': username,
            'reputation_score': rep_score,
            'engagement': engagement,
            'influence': influence,
            'controversy': controversy,
            'consistency': consistency,
            'shocks': shocks
        })

    # Sort and assign ranks
    scores.sort(key=lambda x: x['reputation_score'], reverse=True)
    for i, s in enumerate(scores):
        s['rank'] = i + 1
        s['tier'] = assign_tier(s['reputation_score'], i + 1, len(scores))

    # Save to database
    timestamp = datetime.now().isoformat()
    for s in scores:
        cursor.execute("""
            INSERT OR REPLACE INTO reputation_history
            (username, timestamp, reputation_score, influence_score, engagement_score,
             controversy_score, consistency_score, rank, tier, shock_events)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            s['username'], timestamp, s['reputation_score'],
            s['influence'], s['engagement'], s['controversy'],
            s['consistency'], s['rank'], s['tier'],
            str([sh['type'] for sh in s['shocks']])
        ))

        for shock in s['shocks']:
            cursor.execute("""
                INSERT INTO reputation_shocks
                (username, timestamp, shock_type, magnitude, trigger_content, after_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                s['username'], shock.get('timestamp', timestamp),
                shock['type'], shock['magnitude'],
                shock['trigger'], s['reputation_score']
            ))

    conn.commit()

    # Report
    print("\n>> Top 15 by Reputation:")
    for s in scores[:15]:
        print(f"   [{s['rank']:3d}] {s['username'][:20]:<20} "
              f"Score: {s['reputation_score']:.1f} | Tier: {s['tier']:<12} | "
              f"Shocks: {len(s['shocks'])}")

    print("\n>> Tier Distribution:")
    tier_counts = defaultdict(int)
    for s in scores:
        tier_counts[s['tier']] += 1
    for tier in ['legendary', 'elite', 'established', 'rising', 'active', 'newcomer']:
        print(f"   {tier}: {tier_counts[tier]}")

    print("\n>> Most Volatile (most shock events):")
    volatile = sorted(scores, key=lambda x: len(x['shocks']), reverse=True)[:10]
    for s in volatile:
        shock_types = [sh['type'] for sh in s['shocks']]
        print(f"   {s['username'][:20]:<20}: {len(s['shocks'])} shocks ({', '.join(set(shock_types))})")

    conn.close()

    print("\n" + "=" * 60)
    print("  REPUTATION ANALYSIS COMPLETE")
    print("=" * 60)

    return scores


if __name__ == "__main__":
    run_reputation_analysis()
