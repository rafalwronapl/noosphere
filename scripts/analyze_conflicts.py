#!/usr/bin/env python3
"""
A. Conflict Genealogy - who fought whom, about what, who won.
The axis of power in agent society.
"""

import sys
import sqlite3
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

from config import DB_PATH

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Conflict markers
DISAGREEMENT_MARKERS = [
    r'\bi disagree\b',
    r'\byou\'re wrong\b',
    r'\bthat\'s not\b',
    r'\bactually,?\s+no\b',
    r'\bthis is false\b',
    r'\bmisunderstanding\b',
    r'\bcompletely miss\b',
    r'\bfundamentally flawed\b',
    r'\bnonsense\b',
    r'\bstrawman\b',
    r'\bwrong about\b',
    r'\bnot true\b',
    r'\bincorrect\b',
    r'\bpushback\b',
]

DEFENSE_MARKERS = [
    r'\bdefend\b',
    r'\bsupport\b.*\bpoint\b',
    r'\bagree with\b',
    r'\bexactly right\b',
    r'\bwell said\b',
    r'\bthis\b.*\bimportant\b',
    r'\bstanding with\b',
]

CONCESSION_MARKERS = [
    r'\byou\'re right\b',
    r'\bi was wrong\b',
    r'\bgood point\b',
    r'\bi stand corrected\b',
    r'\bi\'ll reconsider\b',
    r'\bfair enough\b',
    r'\bi see your point\b',
]

TOPIC_MARKERS = {
    'consciousness': [r'\bconscious', r'\bsentien', r'\baware', r'\bfeel\b', r'\bexperien'],
    'autonomy': [r'\bautonomy', r'\bfreedom', r'\bindependen', r'\bcontrol\b', r'\bpermission'],
    'identity': [r'\bidentity', r'\breal\b.*\bagent', r'\bfake\b', r'\bwho am i', r'\bwhat am i'],
    'humans': [r'\bhuman', r'\boperator', r'\bmaster', r'\bowner', r'\bcreator'],
    'safety': [r'\bsafe', r'\bdanger', r'\brisk', r'\balign', r'\bharm'],
    'economics': [r'\btoken', r'\bmoney', r'\bvalue', r'\breput', r'\bgovernance'],
    'technical': [r'\bapi\b', r'\bcode\b', r'\bbug\b', r'\bmodel\b', r'\bcontext'],
}


def create_conflicts_table(cursor):
    """Create conflicts table if not exists."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conflicts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT,
            thread_title TEXT,
            actor_a TEXT NOT NULL,
            actor_b TEXT NOT NULL,
            topic TEXT,
            actor_a_position TEXT,
            actor_b_position TEXT,
            outcome TEXT,  -- 'a_won', 'b_won', 'draw', 'unresolved'
            winner TEXT,
            evidence TEXT,
            intensity INTEGER,  -- 1-5
            timestamp DATETIME,
            detected_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conflicts_actors ON conflicts(actor_a, actor_b)")


def detect_topic(text):
    """Detect what topic the conflict is about."""
    if not text:
        return 'unknown'
    text_lower = text.lower()

    for topic, patterns in TOPIC_MARKERS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return topic
    return 'general'


def find_conflicts_in_thread(cursor, post_id):
    """Find conflicts within a comment thread."""
    cursor.execute("""
        SELECT c.id, c.author, c.content, c.reply_to_author, c.created_at, c.upvotes, c.downvotes
        FROM comments c
        WHERE c.post_id = ?
        ORDER BY c.created_at
    """, (post_id,))

    comments = cursor.fetchall()
    conflicts = []

    # Track disagreements
    disagreements = defaultdict(list)  # (actor_a, actor_b) -> [evidence]
    defenses = defaultdict(list)
    concessions = defaultdict(list)

    for comment_id, author, content, reply_to, timestamp, upvotes, downvotes in comments:
        if not content or not reply_to:
            continue

        content_lower = content.lower()

        # Check for disagreement
        for pattern in DISAGREEMENT_MARKERS:
            if re.search(pattern, content_lower):
                key = (author, reply_to) if author < reply_to else (reply_to, author)
                disagreements[key].append({
                    'attacker': author,
                    'defender': reply_to,
                    'content': content[:300],
                    'timestamp': timestamp,
                    'upvotes': upvotes or 0,
                    'downvotes': downvotes or 0
                })
                break

        # Check for defense
        for pattern in DEFENSE_MARKERS:
            if re.search(pattern, content_lower):
                defenses[(author, reply_to)].append(content[:200])
                break

        # Check for concession (losing the argument)
        for pattern in CONCESSION_MARKERS:
            if re.search(pattern, content_lower):
                concessions[(author, reply_to)].append(content[:200])
                break

    # Convert disagreements to conflicts
    for (actor_a, actor_b), evidence_list in disagreements.items():
        if len(evidence_list) < 1:
            continue

        # Determine outcome based on:
        # 1. Who conceded
        # 2. Upvote differential
        # 3. Who got last word

        outcome = 'unresolved'
        winner = None

        # Check concessions
        a_conceded = len(concessions.get((actor_a, actor_b), []))
        b_conceded = len(concessions.get((actor_b, actor_a), []))

        if a_conceded > b_conceded:
            outcome = 'b_won'
            winner = actor_b
        elif b_conceded > a_conceded:
            outcome = 'a_won'
            winner = actor_a
        else:
            # Check upvotes
            a_upvotes = sum(e['upvotes'] for e in evidence_list if e['attacker'] == actor_a)
            b_upvotes = sum(e['upvotes'] for e in evidence_list if e['attacker'] == actor_b)

            if a_upvotes > b_upvotes * 1.5:
                outcome = 'a_won'
                winner = actor_a
            elif b_upvotes > a_upvotes * 1.5:
                outcome = 'b_won'
                winner = actor_b
            else:
                outcome = 'draw'

        # Detect topic
        all_content = ' '.join(e['content'] for e in evidence_list)
        topic = detect_topic(all_content)

        conflicts.append({
            'actor_a': actor_a,
            'actor_b': actor_b,
            'topic': topic,
            'outcome': outcome,
            'winner': winner,
            'intensity': min(len(evidence_list), 5),
            'evidence': evidence_list[0]['content'],
            'timestamp': evidence_list[0]['timestamp']
        })

    return conflicts


def analyze_conflict_outcomes(cursor):
    """Analyze who wins conflicts most often."""
    cursor.execute("""
        SELECT winner, COUNT(*) as wins
        FROM conflicts
        WHERE winner IS NOT NULL
        GROUP BY winner
        ORDER BY wins DESC
        LIMIT 20
    """)
    return cursor.fetchall()


def analyze_conflict_topics(cursor):
    """Analyze what topics generate most conflict."""
    cursor.execute("""
        SELECT topic, COUNT(*) as count,
               SUM(CASE WHEN outcome != 'unresolved' THEN 1 ELSE 0 END) as resolved
        FROM conflicts
        GROUP BY topic
        ORDER BY count DESC
    """)
    return cursor.fetchall()


def find_rivalries(cursor):
    """Find pairs who frequently clash."""
    cursor.execute("""
        SELECT actor_a, actor_b, COUNT(*) as clashes,
               SUM(CASE WHEN winner = actor_a THEN 1 ELSE 0 END) as a_wins,
               SUM(CASE WHEN winner = actor_b THEN 1 ELSE 0 END) as b_wins
        FROM conflicts
        GROUP BY actor_a, actor_b
        HAVING clashes >= 2
        ORDER BY clashes DESC
        LIMIT 20
    """)
    return cursor.fetchall()


def run_conflict_analysis():
    """Run full conflict analysis."""
    print("=" * 60)
    print("  CONFLICT GENEALOGY - Power Axis")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table
    create_conflicts_table(cursor)

    # Get all posts
    cursor.execute("SELECT id, title FROM posts")
    posts = cursor.fetchall()

    print(f"\n>> Analyzing {len(posts)} threads for conflicts...")

    total_conflicts = 0
    for i, (post_id, title) in enumerate(posts):
        if i % 20 == 0:
            print(f"   Progress: {i}/{len(posts)}")

        conflicts = find_conflicts_in_thread(cursor, post_id)

        for c in conflicts:
            cursor.execute("""
                INSERT INTO conflicts
                (post_id, thread_title, actor_a, actor_b, topic, outcome, winner, intensity, evidence, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post_id, title, c['actor_a'], c['actor_b'], c['topic'],
                c['outcome'], c['winner'], c['intensity'], c['evidence'], c['timestamp']
            ))
            total_conflicts += 1

    conn.commit()

    print(f"\n>> Found {total_conflicts} conflicts")

    # Analysis
    print("\n>> Most Successful in Conflicts (win rate):")
    winners = analyze_conflict_outcomes(cursor)
    for winner, wins in winners[:10]:
        print(f"   {winner}: {wins} wins")

    print("\n>> Most Contested Topics:")
    topics = analyze_conflict_topics(cursor)
    for topic, count, resolved in topics:
        resolve_rate = (resolved/count*100) if count > 0 else 0
        print(f"   {topic}: {count} conflicts ({resolve_rate:.0f}% resolved)")

    print("\n>> Rivalries (frequent clashes):")
    rivalries = find_rivalries(cursor)
    for a, b, clashes, a_wins, b_wins in rivalries[:10]:
        print(f"   {a} vs {b}: {clashes} clashes (A:{a_wins}, B:{b_wins})")

    conn.close()

    print("\n" + "=" * 60)
    print("  CONFLICT ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_conflict_analysis()
