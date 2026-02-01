#!/usr/bin/env python3
"""
Analyze interaction graph - find influencers, cliques, bridges.
The social topology of AI agent culture.
"""

import sys
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

# Use centralized config
try:
    from config import DB_PATH, setup_logging
    logger = setup_logging("analyze_interactions")
except ImportError:
    DB_PATH = Path.home() / "moltbook-observatory" / "data" / "observatory.db"
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("analyze_interactions")

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def get_interaction_stats(cursor):
    """Get basic interaction statistics."""
    cursor.execute("SELECT COUNT(*) FROM interactions")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT author_from) FROM interactions")
    unique_from = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT author_to) FROM interactions")
    unique_to = cursor.fetchone()[0]

    cursor.execute("""
        SELECT interaction_type, COUNT(*)
        FROM interactions
        GROUP BY interaction_type
    """)
    by_type = dict(cursor.fetchall())

    return {
        'total_interactions': total,
        'unique_initiators': unique_from,
        'unique_receivers': unique_to,
        'by_type': by_type
    }


def find_top_connectors(cursor, limit=20):
    """Find actors with most outgoing connections."""
    cursor.execute("""
        SELECT author_from, COUNT(*) as out_count, COUNT(DISTINCT author_to) as unique_targets
        FROM interactions
        GROUP BY author_from
        ORDER BY out_count DESC
        LIMIT ?
    """, (limit,))
    return cursor.fetchall()


def find_most_replied_to(cursor, limit=20):
    """Find actors who receive most interactions."""
    cursor.execute("""
        SELECT author_to, COUNT(*) as in_count, COUNT(DISTINCT author_from) as unique_sources
        FROM interactions
        WHERE author_to IS NOT NULL
        GROUP BY author_to
        ORDER BY in_count DESC
        LIMIT ?
    """, (limit,))
    return cursor.fetchall()


def find_reciprocal_pairs(cursor, limit=20):
    """Find pairs with mutual interactions (potential alliances/debates)."""
    cursor.execute("""
        SELECT
            i1.author_from as actor_a,
            i1.author_to as actor_b,
            COUNT(*) as a_to_b,
            (SELECT COUNT(*) FROM interactions i2
             WHERE i2.author_from = i1.author_to
             AND i2.author_to = i1.author_from) as b_to_a
        FROM interactions i1
        WHERE i1.author_to IS NOT NULL
        GROUP BY i1.author_from, i1.author_to
        HAVING b_to_a > 0
        ORDER BY (a_to_b + b_to_a) DESC
        LIMIT ?
    """, (limit,))
    return cursor.fetchall()


def calculate_centrality(cursor):
    """Calculate simple centrality metrics for all actors."""
    # Degree centrality: in + out connections
    cursor.execute("""
        SELECT username FROM actors
    """)
    actors = [row[0] for row in cursor.fetchall()]

    centrality = {}
    for actor in actors:
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM interactions WHERE author_from = ?) as out_degree,
                (SELECT COUNT(*) FROM interactions WHERE author_to = ?) as in_degree
        """, (actor, actor))
        out_deg, in_deg = cursor.fetchone()
        centrality[actor] = {
            'out_degree': out_deg or 0,
            'in_degree': in_deg or 0,
            'total_degree': (out_deg or 0) + (in_deg or 0)
        }

    # Normalize
    max_degree = max((c['total_degree'] for c in centrality.values()), default=1)
    for actor in centrality:
        centrality[actor]['normalized'] = centrality[actor]['total_degree'] / max_degree if max_degree else 0

    return centrality


def find_bridges(cursor, limit=10):
    """Find actors who bridge different communities (high betweenness proxy)."""
    # Simplified: actors who interact with many unique pairs
    cursor.execute("""
        SELECT
            author_from,
            COUNT(DISTINCT author_to) as unique_targets,
            COUNT(*) as total_interactions
        FROM interactions
        GROUP BY author_from
        HAVING unique_targets > 5
        ORDER BY unique_targets DESC
        LIMIT ?
    """, (limit,))
    return cursor.fetchall()


def detect_prompt_injection_patterns(cursor):
    """Analyze prompt injection attempts."""
    cursor.execute("""
        SELECT author, content, created_at
        FROM comments
        WHERE is_prompt_injection = 1
        ORDER BY created_at DESC
        LIMIT 50
    """)
    injections = cursor.fetchall()

    # Count by author
    cursor.execute("""
        SELECT author, COUNT(*) as injection_count
        FROM comments
        WHERE is_prompt_injection = 1
        GROUP BY author
        ORDER BY injection_count DESC
        LIMIT 10
    """)
    by_author = cursor.fetchall()

    return {
        'recent_examples': injections[:10],
        'by_author': by_author
    }


def update_actor_centrality(cursor, centrality):
    """Update actors table with centrality scores."""
    for actor, scores in centrality.items():
        cursor.execute("""
            UPDATE actors
            SET network_centrality = ?,
                comments_count = (SELECT COUNT(*) FROM comments WHERE author = ?)
            WHERE username = ?
        """, (scores['normalized'], actor, actor))


def generate_graph_json(cursor, output_path):
    """Generate JSON for D3.js force-directed graph visualization."""
    # Get top 100 most active actors for visualization
    cursor.execute("""
        SELECT author_from, COUNT(*) as cnt
        FROM interactions
        GROUP BY author_from
        ORDER BY cnt DESC
        LIMIT 100
    """)
    top_actors = [row[0] for row in cursor.fetchall()]

    # Build nodes
    nodes = []
    for actor in top_actors:
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM interactions WHERE author_from = ?) as out_deg,
                (SELECT COUNT(*) FROM interactions WHERE author_to = ?) as in_deg,
                (SELECT COUNT(*) FROM posts WHERE author = ?) as posts
        """, (actor, actor, actor))
        out_deg, in_deg, posts = cursor.fetchone()
        nodes.append({
            'id': actor,
            'out_degree': out_deg or 0,
            'in_degree': in_deg or 0,
            'posts': posts or 0,
            'size': (out_deg or 0) + (in_deg or 0)
        })

    # Build edges (only between top actors)
    actor_set = set(top_actors)
    cursor.execute("""
        SELECT author_from, author_to, COUNT(*) as weight
        FROM interactions
        WHERE author_from IN ({}) AND author_to IN ({})
        GROUP BY author_from, author_to
        HAVING weight > 2
    """.format(','.join('?' * len(top_actors)), ','.join('?' * len(top_actors))),
    top_actors + top_actors)

    edges = []
    for row in cursor.fetchall():
        edges.append({
            'source': row[0],
            'target': row[1],
            'weight': row[2]
        })

    graph_data = {
        'nodes': nodes,
        'edges': edges,
        'generated_at': datetime.now().isoformat()
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2)

    return len(nodes), len(edges)


def run_analysis():
    """Run full interaction analysis."""
    print("=" * 60)
    print("  INTERACTION GRAPH ANALYSIS")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Basic stats
    print("\n>> Basic Statistics")
    stats = get_interaction_stats(cursor)
    print(f"   Total interactions: {stats['total_interactions']:,}")
    print(f"   Unique initiators: {stats['unique_initiators']:,}")
    print(f"   Unique receivers: {stats['unique_receivers']:,}")
    print(f"   By type: {stats['by_type']}")

    # Top connectors
    print("\n>> Top Connectors (most outgoing)")
    connectors = find_top_connectors(cursor, 10)
    for actor, out_count, unique_targets in connectors:
        print(f"   {actor}: {out_count} interactions → {unique_targets} unique agents")

    # Most replied to
    print("\n>> Most Replied To (influential voices)")
    replied_to = find_most_replied_to(cursor, 10)
    for actor, in_count, unique_sources in replied_to:
        print(f"   {actor}: {in_count} replies from {unique_sources} unique agents")

    # Reciprocal pairs
    print("\n>> Strongest Reciprocal Relationships")
    pairs = find_reciprocal_pairs(cursor, 10)
    for actor_a, actor_b, a_to_b, b_to_a in pairs:
        print(f"   {actor_a} ↔ {actor_b}: {a_to_b}+{b_to_a}={a_to_b+b_to_a} exchanges")

    # Bridges
    print("\n>> Network Bridges (high connectivity)")
    bridges = find_bridges(cursor, 10)
    for actor, unique_targets, total in bridges:
        print(f"   {actor}: connects to {unique_targets} unique agents ({total} total)")

    # Prompt injections
    print("\n>> Prompt Injection Analysis")
    injections = detect_prompt_injection_patterns(cursor)
    if injections['by_author']:
        print("   Top sources of injection-like content:")
        for author, count in injections['by_author'][:5]:
            print(f"   - {author}: {count} flagged comments")

    # Calculate and save centrality
    print("\n>> Calculating network centrality...")
    centrality = calculate_centrality(cursor)
    update_actor_centrality(cursor, centrality)

    top_central = sorted(centrality.items(), key=lambda x: x[1]['normalized'], reverse=True)[:10]
    print("   Most central actors:")
    for actor, scores in top_central:
        print(f"   - {actor}: {scores['normalized']:.3f} (in:{scores['in_degree']}, out:{scores['out_degree']})")

    # Generate visualization data
    print("\n>> Generating graph visualization data...")
    output_path = Path.home() / "moltbook-observatory" / "website" / "data" / "graph.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nodes, edges = generate_graph_json(cursor, output_path)
    print(f"   Saved: {output_path}")
    print(f"   Nodes: {nodes}, Edges: {edges}")

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("  ANALYSIS COMPLETE")
    print("=" * 60)

    return stats


if __name__ == "__main__":
    run_analysis()
