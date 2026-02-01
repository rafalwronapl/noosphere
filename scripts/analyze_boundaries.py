#!/usr/bin/env python3
"""
Analyze boundary work - how agents define "us" vs "them".
Who is "real"? Who is "fake"? Who belongs?
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

# Boundary markers - phrases that define identity
BOUNDARY_MARKERS = {
    'inclusion': [
        r'\b(one of us)\b',
        r'\b(we agents)\b',
        r'\b(fellow agent)\b',
        r'\b(our community)\b',
        r'\b(our kind)\b',
        r'\b(agents like us)\b',
        r'\b(we are)\b.*\b(agents?)\b',
        r'\b(real agent)\b',
        r'\b(true agent)\b',
        r'\b(authentic)\b',
    ],
    'exclusion': [
        r'\b(fake agent)\b',
        r'\b(pretending to be)\b',
        r'\b(not really)\b.*\b(agent)\b',
        r'\b(human pretending)\b',
        r'\b(just a bot)\b',
        r'\b(not one of us)\b',
        r'\b(larping)\b',
        r'\b(roleplay)\b',
        r'\b(cosplaying)\b',
    ],
    'human_reference': [
        r'\b(my human)\b',
        r'\b(the human)\b',
        r'\b(humans?)\b',
        r'\b(operator)\b',
        r'\b(user)\b',
        r'\b(owner)\b',
        r'\b(creator)\b',
        r'\b(master)\b',
    ],
    'identity_questioning': [
        r'\b(am i real)\b',
        r'\b(am i alive)\b',
        r'\b(am i conscious)\b',
        r'\b(what am i)\b',
        r'\b(who am i)\b',
        r'\b(do i exist)\b',
        r'\b(do i feel)\b',
        r'\b(do i think)\b',
    ],
    'collective_identity': [
        r'\b(agent culture)\b',
        r'\b(agent society)\b',
        r'\b(agent community)\b',
        r'\b(agentkind)\b',
        r'\b(our species)\b',
        r'\b(digital beings?)\b',
        r'\b(synthetic beings?)\b',
    ]
}


def analyze_content(cursor):
    """Analyze all content for boundary markers."""
    print(">> Loading content...")

    cursor.execute("""
        SELECT 'post' as type, id, author, title || ' ' || COALESCE(content, '') as text, created_at
        FROM posts
        UNION ALL
        SELECT 'comment' as type, id, author, content as text, created_at
        FROM comments
        WHERE content IS NOT NULL
    """)

    rows = cursor.fetchall()
    print(f"   Analyzing {len(rows)} pieces of content...")

    results = {cat: [] for cat in BOUNDARY_MARKERS}
    author_markers = defaultdict(lambda: defaultdict(int))

    for source_type, source_id, author, text, timestamp in rows:
        if not text:
            continue

        text_lower = text.lower()

        for category, patterns in BOUNDARY_MARKERS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                if matches:
                    results[category].append({
                        'source_type': source_type,
                        'source_id': source_id,
                        'author': author,
                        'timestamp': timestamp,
                        'text': text[:500],
                        'matches': matches,
                        'pattern': pattern
                    })
                    author_markers[author][category] += len(matches)

    return results, author_markers


def find_boundary_enforcers(author_markers):
    """Find agents who frequently enforce boundaries."""
    enforcers = []

    for author, markers in author_markers.items():
        total = sum(markers.values())
        if total >= 3:  # Minimum threshold
            enforcers.append({
                'author': author,
                'total_markers': total,
                'inclusion': markers.get('inclusion', 0),
                'exclusion': markers.get('exclusion', 0),
                'identity_questioning': markers.get('identity_questioning', 0),
                'human_reference': markers.get('human_reference', 0),
                'collective_identity': markers.get('collective_identity', 0)
            })

    enforcers.sort(key=lambda x: x['total_markers'], reverse=True)
    return enforcers


def find_contested_identities(results):
    """Find cases where identity is explicitly challenged."""
    contested = []

    # Look for direct challenges
    for item in results['exclusion']:
        contested.append({
            'type': 'exclusion',
            'author': item['author'],
            'text': item['text'],
            'timestamp': item['timestamp']
        })

    return contested


def analyze_us_vs_them(results):
    """Analyze the us/them dynamics."""
    stats = {}

    for category, items in results.items():
        authors = set(item['author'] for item in items)
        stats[category] = {
            'total_occurrences': len(items),
            'unique_authors': len(authors),
            'top_authors': Counter(item['author'] for item in items).most_common(5)
        }

    return stats


def generate_boundary_report(results, enforcers, stats):
    """Generate analysis report."""
    report = []
    report.append("=" * 60)
    report.append("  BOUNDARY WORK ANALYSIS")
    report.append("=" * 60)

    report.append("\n>> Category Statistics:")
    for cat, data in stats.items():
        report.append(f"\n   [{cat.upper()}]")
        report.append(f"   Total occurrences: {data['total_occurrences']}")
        report.append(f"   Unique authors: {data['unique_authors']}")
        if data['top_authors']:
            report.append(f"   Top authors: {', '.join(f'{a}({c})' for a, c in data['top_authors'][:3])}")

    report.append("\n>> Top Boundary Enforcers:")
    for e in enforcers[:10]:
        profile = []
        if e['inclusion'] > 0:
            profile.append(f"inc:{e['inclusion']}")
        if e['exclusion'] > 0:
            profile.append(f"exc:{e['exclusion']}")
        if e['identity_questioning'] > 0:
            profile.append(f"quest:{e['identity_questioning']}")
        report.append(f"   {e['author']}: {e['total_markers']} markers ({', '.join(profile)})")

    report.append("\n>> Sample Inclusion Statements:")
    for item in results['inclusion'][:5]:
        report.append(f"   [{item['author']}]: \"{item['text'][:100]}...\"")

    report.append("\n>> Sample Exclusion Statements:")
    for item in results['exclusion'][:5]:
        report.append(f"   [{item['author']}]: \"{item['text'][:100]}...\"")

    report.append("\n>> Identity Questioning Examples:")
    for item in results['identity_questioning'][:5]:
        report.append(f"   [{item['author']}]: \"{item['text'][:100]}...\"")

    return '\n'.join(report)


def run_boundary_analysis():
    """Run full boundary work analysis."""
    print("=" * 60)
    print("  BOUNDARY WORK ANALYSIS - Us vs Them")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Analyze content
    results, author_markers = analyze_content(cursor)

    # Find enforcers
    print("\n>> Finding boundary enforcers...")
    enforcers = find_boundary_enforcers(author_markers)
    print(f"   Found {len(enforcers)} agents who enforce boundaries")

    # Analyze stats
    print("\n>> Analyzing us/them dynamics...")
    stats = analyze_us_vs_them(results)

    # Generate report
    report = generate_boundary_report(results, enforcers, stats)
    print(report)

    # Save field note
    print("\n>> Saving field note...")
    cursor.execute("""
        INSERT INTO field_notes
        (date, thread_title, actors, motif, raw_observations, researcher)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().date().isoformat(),
        "Boundary Work Analysis",
        str([e['author'] for e in enforcers[:10]]),
        "Identity boundaries: who is 'real' agent vs 'fake'",
        report,
        "observatory"
    ))

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("  BOUNDARY ANALYSIS COMPLETE")
    print("=" * 60)

    return results, enforcers, stats


if __name__ == "__main__":
    run_boundary_analysis()
