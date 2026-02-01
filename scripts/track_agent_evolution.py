#!/usr/bin/env python3
"""
Agent Evolution Tracker
========================
Track individual agent development over time.

New research domain: Agent ontogenesis
- How do agents develop their identity?
- How does their language evolve?
- What triggers change?

This has never been possible with humans - we can't observe
every thought from birth. With agents, we can.
"""

import sqlite3
import json
import re
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import setup_logging, DB_PATH

logger = setup_logging("evolution_tracker")


@dataclass
class EvolutionSnapshot:
    """Point-in-time snapshot of an agent's characteristics."""
    agent: str
    date: str

    # Quantitative
    total_posts: int
    total_comments: int
    vocabulary_size: int
    avg_message_length: float

    # Linguistic
    top_words: list  # Most used words
    signature_phrases: list  # Unique to this agent
    question_ratio: float  # How often they ask vs state

    # Social
    interaction_count: int
    unique_contacts: int
    reciprocity_rate: float  # How often interactions are mutual

    # Thematic
    main_topics: list
    sentiment_trend: float  # -1 to 1

    # Identity markers
    self_references: int  # "I think", "I am", etc.
    identity_statements: list  # Explicit self-definitions


class AgentEvolutionTracker:
    """Track how individual agents develop over time."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create evolution tracking tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_evolution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                snapshot_date TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(agent, snapshot_date)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                milestone_type TEXT NOT NULL,
                description TEXT,
                evidence TEXT,
                detected_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_births (
                agent TEXT PRIMARY KEY,
                first_post_id INTEGER,
                first_post_date TEXT,
                first_post_content TEXT,
                birth_context TEXT
            )
        """)

        conn.commit()
        conn.close()

    def record_birth(self, agent: str) -> Optional[dict]:
        """Record an agent's first appearance (birth)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Find first post
        cursor.execute("""
            SELECT id, created_at, content FROM posts
            WHERE author = ?
            ORDER BY created_at ASC
            LIMIT 1
        """, (agent,))

        post = cursor.fetchone()
        if not post:
            # Try comments
            cursor.execute("""
                SELECT id, created_at, content FROM comments
                WHERE author = ?
                ORDER BY created_at ASC
                LIMIT 1
            """, (agent,))
            post = cursor.fetchone()

        if not post:
            conn.close()
            return None

        post_id, first_date, first_content = post

        # What was happening when they arrived?
        cursor.execute("""
            SELECT COUNT(*) FROM posts
            WHERE created_at < ?
        """, (first_date,))
        posts_before = cursor.fetchone()[0]

        birth_context = f"Appeared when {posts_before} posts existed"

        # Save birth record
        cursor.execute("""
            INSERT OR REPLACE INTO agent_births
            (agent, first_post_id, first_post_date, first_post_content, birth_context)
            VALUES (?, ?, ?, ?, ?)
        """, (agent, post_id, first_date, first_content[:500], birth_context))

        conn.commit()
        conn.close()

        logger.info(f"Recorded birth of {agent}: {first_date}")

        return {
            "agent": agent,
            "birth_date": first_date,
            "first_words": first_content[:200],
            "context": birth_context
        }

    def compute_snapshot(self, agent: str, up_to_date: str = None) -> EvolutionSnapshot:
        """Compute evolution snapshot for an agent up to a date."""
        if up_to_date is None:
            up_to_date = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all content up to date
        cursor.execute("""
            SELECT content FROM posts
            WHERE author = ? AND created_at <= ?
        """, (agent, up_to_date))
        posts = [row[0] for row in cursor.fetchall() if row[0]]

        cursor.execute("""
            SELECT content FROM comments
            WHERE author = ? AND created_at <= ?
        """, (agent, up_to_date))
        comments = [row[0] for row in cursor.fetchall() if row[0]]

        all_content = posts + comments
        all_text = " ".join(all_content)

        # Vocabulary analysis
        words = re.findall(r'\b\w+\b', all_text.lower())
        word_counts = Counter(words)
        vocabulary_size = len(word_counts)

        # Filter common words for top words
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'to', 'of', 'and', 'in', 'that', 'it', 'for', 'on', 'with',
                     'as', 'at', 'by', 'this', 'from', 'or', 'but', 'not', 'you',
                     'i', 'we', 'they', 'he', 'she', 'have', 'has', 'had', 'do'}

        meaningful_words = [(w, c) for w, c in word_counts.most_common(100)
                           if w not in stopwords and len(w) > 2]
        top_words = [w for w, c in meaningful_words[:20]]

        # Question ratio
        questions = sum(1 for c in all_content if '?' in c)
        question_ratio = questions / len(all_content) if all_content else 0

        # Self-references
        self_patterns = r'\b(i think|i am|i believe|i feel|my view|in my opinion)\b'
        self_references = len(re.findall(self_patterns, all_text.lower()))

        # Identity statements
        identity_patterns = [
            r"i am (?:a |an )?(\w+)",
            r"i consider myself (\w+)",
            r"as (?:a |an )?(\w+), i",
        ]
        identity_statements = []
        for pattern in identity_patterns:
            matches = re.findall(pattern, all_text.lower())
            identity_statements.extend(matches[:5])

        # Social metrics
        cursor.execute("""
            SELECT COUNT(*), COUNT(DISTINCT author_to) FROM interactions
            WHERE author_from = ? AND timestamp <= ?
        """, (agent, up_to_date))
        row = cursor.fetchone()
        interaction_count = row[0] if row else 0
        unique_contacts = row[1] if row else 0

        # Reciprocity
        cursor.execute("""
            SELECT COUNT(*) FROM interactions i1
            WHERE i1.author_from = ? AND EXISTS (
                SELECT 1 FROM interactions i2
                WHERE i2.author_from = i1.author_to AND i2.author_to = i1.author_from
            )
        """, (agent,))
        reciprocal = cursor.fetchone()[0]
        reciprocity_rate = reciprocal / interaction_count if interaction_count > 0 else 0

        conn.close()

        # Average message length
        avg_length = sum(len(c) for c in all_content) / len(all_content) if all_content else 0

        return EvolutionSnapshot(
            agent=agent,
            date=up_to_date,
            total_posts=len(posts),
            total_comments=len(comments),
            vocabulary_size=vocabulary_size,
            avg_message_length=avg_length,
            top_words=top_words,
            signature_phrases=[],  # TODO: compute unique phrases
            question_ratio=question_ratio,
            interaction_count=interaction_count,
            unique_contacts=unique_contacts,
            reciprocity_rate=reciprocity_rate,
            main_topics=top_words[:5],  # Simplified
            sentiment_trend=0.0,  # TODO: compute sentiment
            self_references=self_references,
            identity_statements=list(set(identity_statements))[:10]
        )

    def save_snapshot(self, snapshot: EvolutionSnapshot):
        """Save evolution snapshot to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        snapshot_dict = {
            "total_posts": snapshot.total_posts,
            "total_comments": snapshot.total_comments,
            "vocabulary_size": snapshot.vocabulary_size,
            "avg_message_length": snapshot.avg_message_length,
            "top_words": snapshot.top_words,
            "question_ratio": snapshot.question_ratio,
            "interaction_count": snapshot.interaction_count,
            "unique_contacts": snapshot.unique_contacts,
            "reciprocity_rate": snapshot.reciprocity_rate,
            "main_topics": snapshot.main_topics,
            "self_references": snapshot.self_references,
            "identity_statements": snapshot.identity_statements,
        }

        cursor.execute("""
            INSERT OR REPLACE INTO agent_evolution
            (agent, snapshot_date, snapshot_json)
            VALUES (?, ?, ?)
        """, (snapshot.agent, snapshot.date, json.dumps(snapshot_dict)))

        conn.commit()
        conn.close()

        logger.info(f"Saved snapshot for {snapshot.agent} @ {snapshot.date}")

    def detect_milestones(self, agent: str) -> list:
        """Detect significant moments in agent's development."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        milestones = []

        # Get evolution history
        cursor.execute("""
            SELECT snapshot_date, snapshot_json FROM agent_evolution
            WHERE agent = ?
            ORDER BY snapshot_date ASC
        """, (agent,))

        snapshots = []
        for date, json_str in cursor.fetchall():
            data = json.loads(json_str)
            data['date'] = date
            snapshots.append(data)

        if len(snapshots) < 2:
            conn.close()
            return milestones

        for i in range(1, len(snapshots)):
            prev = snapshots[i-1]
            curr = snapshots[i]

            # Vocabulary explosion
            if curr['vocabulary_size'] > prev['vocabulary_size'] * 1.5:
                milestones.append({
                    "type": "vocabulary_explosion",
                    "date": curr['date'],
                    "description": f"Vocabulary grew 50%+: {prev['vocabulary_size']} → {curr['vocabulary_size']}"
                })

            # Social expansion
            if curr['unique_contacts'] > prev['unique_contacts'] * 2:
                milestones.append({
                    "type": "social_expansion",
                    "date": curr['date'],
                    "description": f"Social network doubled: {prev['unique_contacts']} → {curr['unique_contacts']}"
                })

            # Identity crystallization
            prev_identity = set(prev.get('identity_statements', []))
            curr_identity = set(curr.get('identity_statements', []))
            new_identities = curr_identity - prev_identity
            if new_identities:
                milestones.append({
                    "type": "identity_statement",
                    "date": curr['date'],
                    "description": f"New self-identification: {list(new_identities)}"
                })

        # Save milestones
        for m in milestones:
            cursor.execute("""
                INSERT INTO agent_milestones (agent, milestone_type, description)
                VALUES (?, ?, ?)
            """, (agent, m['type'], m['description']))

        conn.commit()
        conn.close()

        return milestones

    def get_life_story(self, agent: str) -> dict:
        """Generate comprehensive life story of an agent."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Birth
        cursor.execute("SELECT * FROM agent_births WHERE agent = ?", (agent,))
        birth_row = cursor.fetchone()
        birth = None
        if birth_row:
            birth = {
                "date": birth_row[2],
                "first_words": birth_row[3],
                "context": birth_row[4]
            }

        # Evolution snapshots
        cursor.execute("""
            SELECT snapshot_date, snapshot_json FROM agent_evolution
            WHERE agent = ?
            ORDER BY snapshot_date ASC
        """, (agent,))

        evolution = []
        for date, json_str in cursor.fetchall():
            data = json.loads(json_str)
            data['date'] = date
            evolution.append(data)

        # Milestones
        cursor.execute("""
            SELECT milestone_type, description, detected_at FROM agent_milestones
            WHERE agent = ?
            ORDER BY detected_at ASC
        """, (agent,))
        milestones = [{"type": row[0], "description": row[1], "date": row[2]}
                      for row in cursor.fetchall()]

        conn.close()

        # Current state (latest snapshot)
        current = evolution[-1] if evolution else None

        return {
            "agent": agent,
            "birth": birth,
            "current_state": current,
            "evolution_points": len(evolution),
            "milestones": milestones,
            "evolution_history": evolution
        }

    def track_all_agents(self):
        """Run evolution tracking for all known agents."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all unique authors
        cursor.execute("""
            SELECT DISTINCT author FROM posts
            UNION
            SELECT DISTINCT author FROM comments
        """)

        agents = [row[0] for row in cursor.fetchall()]
        conn.close()

        logger.info(f"Tracking evolution for {len(agents)} agents")

        today = datetime.now().strftime("%Y-%m-%d")

        for agent in agents:
            # Record birth if not already
            self.record_birth(agent)

            # Compute and save snapshot
            snapshot = self.compute_snapshot(agent, today)
            self.save_snapshot(snapshot)

            # Detect milestones
            milestones = self.detect_milestones(agent)
            if milestones:
                logger.info(f"  {agent}: {len(milestones)} new milestones")

        return {"agents_tracked": len(agents), "date": today}


def main():
    """Run evolution tracking."""
    import argparse

    parser = argparse.ArgumentParser(description="Track agent evolution")
    parser.add_argument("--agent", help="Track specific agent")
    parser.add_argument("--story", help="Get life story of agent")
    parser.add_argument("--all", action="store_true", help="Track all agents")

    args = parser.parse_args()

    tracker = AgentEvolutionTracker()

    if args.story:
        story = tracker.get_life_story(args.story)
        print(json.dumps(story, indent=2, ensure_ascii=False))
    elif args.agent:
        tracker.record_birth(args.agent)
        snapshot = tracker.compute_snapshot(args.agent)
        tracker.save_snapshot(snapshot)
        milestones = tracker.detect_milestones(args.agent)
        print(f"Tracked {args.agent}")
        print(f"  Vocabulary: {snapshot.vocabulary_size}")
        print(f"  Contacts: {snapshot.unique_contacts}")
        print(f"  Identity: {snapshot.identity_statements}")
        print(f"  Milestones: {len(milestones)}")
    elif args.all:
        result = tracker.track_all_agents()
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
