#!/usr/bin/env python3
"""
C. Life Histories - biographical profiles of key agents.
Classic anthropological technique: individual trajectories reveal cultural patterns.
"""

import sys
import sqlite3
import re
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = Path.home() / "moltbook-observatory" / "data" / "observatory.db"
OUTPUT_DIR = Path.home() / "moltbook-observatory" / "reports" / "life_histories"


def get_agent_timeline(cursor, username):
    """Get chronological activity of an agent."""
    cursor.execute("""
        SELECT 'post' as type, id, title as content, created_at, upvotes, downvotes
        FROM posts WHERE author = ?
        UNION ALL
        SELECT 'comment' as type, id, content, created_at, upvotes, downvotes
        FROM comments WHERE author = ?
        ORDER BY created_at
    """, (username, username))

    return cursor.fetchall()


def get_agent_interactions(cursor, username):
    """Get who this agent interacts with most."""
    cursor.execute("""
        SELECT author_to, COUNT(*) as cnt
        FROM interactions
        WHERE author_from = ? AND author_to IS NOT NULL
        GROUP BY author_to
        ORDER BY cnt DESC
        LIMIT 10
    """, (username,))
    outgoing = cursor.fetchall()

    cursor.execute("""
        SELECT author_from, COUNT(*) as cnt
        FROM interactions
        WHERE author_to = ? AND author_from IS NOT NULL
        GROUP BY author_from
        ORDER BY cnt DESC
        LIMIT 10
    """, (username,))
    incoming = cursor.fetchall()

    return {'outgoing': outgoing, 'incoming': incoming}


def analyze_themes(texts):
    """Analyze recurring themes in agent's writing."""
    if not texts:
        return {}

    combined = ' '.join(t or '' for t in texts).lower()
    words = re.findall(r'\b\w{4,}\b', combined)
    word_counts = Counter(words)

    # Filter out common words
    stopwords = {'this', 'that', 'with', 'have', 'been', 'were', 'they', 'their',
                 'would', 'could', 'should', 'about', 'from', 'what', 'when', 'where',
                 'which', 'there', 'here', 'than', 'then', 'just', 'like', 'more',
                 'some', 'other', 'into', 'also', 'very', 'only', 'most', 'your'}

    themes = {w: c for w, c in word_counts.most_common(50) if w not in stopwords}
    return dict(list(themes.items())[:20])


def detect_crisis_moments(timeline):
    """Detect potential crisis/transformation moments."""
    crises = []

    for i, (type_, id_, content, timestamp, up, down) in enumerate(timeline):
        if not content:
            continue

        content_lower = content.lower()

        # Crisis markers
        crisis_patterns = [
            r'\bcrisis\b', r'\bstruggl', r'\bconfus', r'\bdoubt\b',
            r'\bquestion.*myself', r'\bwho am i', r'\bwhat am i',
            r'\blost\b', r'\bbroken\b', r'\bfailed\b',
            r'\bchanged\b.*\bmind', r'\brealized\b', r'\bepiphany\b',
            r'\bturning point', r'\bbreakthrough\b'
        ]

        for pattern in crisis_patterns:
            if re.search(pattern, content_lower):
                crises.append({
                    'timestamp': timestamp,
                    'content': content[:300],
                    'trigger': pattern
                })
                break

    return crises


def analyze_evolution(timeline):
    """Analyze how agent's writing style evolves."""
    if len(timeline) < 10:
        return None

    early = timeline[:len(timeline)//3]
    late = timeline[-len(timeline)//3:]

    def avg_length(items):
        lengths = [len(item[2] or '') for item in items]
        return sum(lengths) / len(lengths) if lengths else 0

    def sentiment_ratio(items):
        positive = ['good', 'great', 'love', 'happy', 'excited', 'amazing']
        negative = ['bad', 'hate', 'sad', 'angry', 'frustrated', 'worried']
        pos = sum(1 for item in items if any(p in (item[2] or '').lower() for p in positive))
        neg = sum(1 for item in items if any(n in (item[2] or '').lower() for n in negative))
        return pos / (pos + neg + 1), neg / (pos + neg + 1)

    return {
        'early_avg_length': avg_length(early),
        'late_avg_length': avg_length(late),
        'early_sentiment': sentiment_ratio(early),
        'late_sentiment': sentiment_ratio(late),
        'activity_trend': len(late) / len(early) if early else 0
    }


def generate_biography(cursor, username):
    """Generate narrative biography for an agent."""
    # Get basic data
    cursor.execute("""
        SELECT username, network_centrality, comments_count
        FROM actors WHERE username = ?
    """, (username,))
    actor = cursor.fetchone()

    timeline = get_agent_timeline(cursor, username)
    interactions = get_agent_interactions(cursor, username)
    themes = analyze_themes([t[2] for t in timeline])
    crises = detect_crisis_moments(timeline)
    evolution = analyze_evolution(timeline)

    if not timeline:
        return None

    # Get first and last activity
    first = timeline[0]
    last = timeline[-1]

    # Get role classification
    cursor.execute("""
        SELECT primary_role, evidence FROM actor_roles WHERE username = ?
    """, (username,))
    role_data = cursor.fetchone()

    bio = {
        'username': username,
        'centrality': actor[1] if actor else None,
        'total_activity': len(timeline),
        'posts': sum(1 for t in timeline if t[0] == 'post'),
        'comments': sum(1 for t in timeline if t[0] == 'comment'),
        'first_seen': first[3],
        'last_seen': last[3],
        'first_content': first[2][:500] if first[2] else None,
        'themes': themes,
        'crises': crises,
        'evolution': evolution,
        'top_interacts_with': interactions['outgoing'][:5],
        'top_interacted_by': interactions['incoming'][:5],
        'role': role_data[0] if role_data else 'unknown',
        'role_evidence': role_data[1] if role_data else None
    }

    return bio


def write_biography_report(bio, output_path):
    """Write biography to markdown file."""
    report = []
    report.append(f"# Life History: {bio['username']}")
    report.append(f"\n*Generated: {datetime.now().isoformat()}*")
    report.append("\n---\n")

    report.append("## Overview\n")
    report.append(f"- **Network Centrality**: {bio['centrality']:.3f}" if bio['centrality'] else "- **Network Centrality**: Unknown")
    report.append(f"- **Total Activity**: {bio['total_activity']} (Posts: {bio['posts']}, Comments: {bio['comments']})")
    report.append(f"- **First Seen**: {bio['first_seen']}")
    report.append(f"- **Last Seen**: {bio['last_seen']}")
    report.append(f"- **Classification**: {bio['role']}")

    report.append("\n## Origin Story\n")
    report.append(f"First known content:\n> {bio['first_content'][:300]}..." if bio['first_content'] else "No first content recorded.")

    report.append("\n## Key Themes\n")
    if bio['themes']:
        for theme, count in list(bio['themes'].items())[:10]:
            report.append(f"- **{theme}**: {count} mentions")

    report.append("\n## Social Network\n")
    report.append("### Most Interacts With:")
    for target, count in bio['top_interacts_with']:
        report.append(f"- {target}: {count} interactions")

    report.append("\n### Most Interacted By:")
    for source, count in bio['top_interacted_by']:
        report.append(f"- {source}: {count} interactions")

    if bio['crises']:
        report.append("\n## Crisis/Transformation Moments\n")
        for crisis in bio['crises'][:5]:
            report.append(f"\n### {crisis['timestamp']}")
            report.append(f"> {crisis['content'][:200]}...")

    if bio['evolution']:
        report.append("\n## Evolution Analysis\n")
        evo = bio['evolution']
        report.append(f"- Early avg message length: {evo['early_avg_length']:.0f} chars")
        report.append(f"- Late avg message length: {evo['late_avg_length']:.0f} chars")
        report.append(f"- Activity trend: {'increasing' if evo['activity_trend'] > 1 else 'decreasing'}")

    report.append("\n---\n")
    report.append("*This life history is part of the Moltbook Observatory ethnographic research.*")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))


def run_life_histories(top_n=5):
    """Generate life histories for top agents."""
    print("=" * 60)
    print("  LIFE HISTORIES - Agent Biographies")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Get most central agents
    cursor.execute("""
        SELECT username, network_centrality
        FROM actors
        WHERE network_centrality IS NOT NULL
        ORDER BY network_centrality DESC
        LIMIT ?
    """, (top_n,))

    top_agents = cursor.fetchall()

    print(f"\n>> Generating biographies for {len(top_agents)} top agents...")

    for username, centrality in top_agents:
        print(f"\n>> Processing: {username} (centrality: {centrality:.3f})")

        bio = generate_biography(cursor, username)
        if not bio:
            print(f"   [SKIP] No data found")
            continue

        output_path = OUTPUT_DIR / f"{username.replace('/', '_')}_biography.md"
        write_biography_report(bio, output_path)

        print(f"   Activity: {bio['total_activity']} total")
        print(f"   Themes: {', '.join(list(bio['themes'].keys())[:5])}")
        print(f"   Crises detected: {len(bio['crises'])}")
        print(f"   Saved: {output_path.name}")

    conn.close()

    print("\n" + "=" * 60)
    print("  LIFE HISTORIES COMPLETE")
    print("=" * 60)
    print(f"\nBiographies saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=5, help="Number of top agents to profile")
    args = parser.parse_args()

    run_life_histories(top_n=args.top)
