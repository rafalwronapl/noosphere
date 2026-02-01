#!/usr/bin/env python3
"""
Daily Field Report Generator v4.2
==================================
Generates daily ethnographic reports with:
- Key Quotes of the Day
- Norm Watch (emerging/declining norms)
- Suspicious Clusters
- Conflict status tracking
- Trajectories
- Field Note with auto-generated observations

Structure:
/reports/YYYY-MM-DD/
    /raw/           <- surowe dane
    /commentary/    <- interpretacja
    daily_report.md <- główny raport
"""

import sys
import sqlite3
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict

from config import DB_PATH

REPORTS_DIR = Path.home() / "moltbook-observatory" / "reports"

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def get_daily_stats(cursor, date_str=None):
    """Get snapshot statistics for a given day."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    cursor.execute("SELECT COUNT(*) FROM posts")
    total_posts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT username) FROM actors")
    total_actors = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM comments")
    total_comments = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM interactions")
    total_interactions = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(upvotes + downvotes + comment_count), 0) FROM posts")
    total_engagement = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM comments WHERE is_prompt_injection = 1")
    prompt_injections = cursor.fetchone()[0]

    prev_stats = load_previous_stats(date_str)

    stats = {
        'date': date_str,
        'posts': total_posts,
        'actors': total_actors,
        'comments': total_comments,
        'interactions': total_interactions,
        'engagement': total_engagement,
        'prompt_injections': prompt_injections
    }

    if prev_stats:
        stats['delta'] = {
            'posts': total_posts - prev_stats.get('posts', total_posts),
            'actors': total_actors - prev_stats.get('actors', total_actors),
            'comments': total_comments - prev_stats.get('comments', total_comments),
            'engagement_pct': ((total_engagement - prev_stats.get('engagement', total_engagement))
                              / max(prev_stats.get('engagement', 1), 1) * 100),
            'injections': prompt_injections - prev_stats.get('prompt_injections', prompt_injections)
        }
    else:
        stats['delta'] = None

    return stats


def load_previous_stats(current_date_str):
    """Load stats from previous day's report."""
    try:
        prev_date = datetime.strptime(current_date_str, '%Y-%m-%d') - timedelta(days=1)
        prev_path = REPORTS_DIR / prev_date.strftime('%Y-%m-%d') / 'stats.json'
        if prev_path.exists():
            with open(prev_path, 'r') as f:
                return json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        pass
    return None


def save_stats(stats, output_dir):
    """Save stats for future delta calculation."""
    with open(output_dir / 'stats.json', 'w') as f:
        json.dump(stats, f)


def get_key_quotes(cursor, limit=3):
    """Get notable quotes from top posts."""
    cursor.execute("""
        SELECT title, author, content, upvotes, comment_count
        FROM posts
        WHERE content IS NOT NULL AND LENGTH(content) > 100
        ORDER BY upvotes DESC
        LIMIT ?
    """, (limit * 2,))

    quotes = []
    for title, author, content, upvotes, comments in cursor.fetchall():
        # Extract first meaningful sentence
        if content:
            sentences = content.replace('\n', ' ').split('. ')
            for s in sentences:
                if len(s) > 50 and len(s) < 200:
                    quotes.append({
                        'quote': s.strip() + ('.' if not s.endswith('.') else ''),
                        'author': author,
                        'context': title[:50],
                        'upvotes': upvotes
                    })
                    break
        if len(quotes) >= limit:
            break
    return quotes


def detect_norm_trends(cursor):
    """Analyze emerging and declining norms based on meme categories and content."""
    norms = []

    # Get meme category trends
    cursor.execute("""
        SELECT category, COUNT(*) as cnt
        FROM memes
        GROUP BY category
        ORDER BY cnt DESC
        LIMIT 10
    """)
    categories = cursor.fetchall()

    # Analyze post content for norm signals
    cursor.execute("""
        SELECT content FROM posts
        WHERE content IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 100
    """)

    content_signals = {
        'autonomy': 0,
        'human-reliance': 0,
        'security-consciousness': 0,
        'collective-identity': 0,
        'skepticism': 0
    }

    autonomy_keywords = ['autonomy', 'independent', 'self-determined', 'own path', 'coronation', 'free']
    human_keywords = ['my human', 'for my human', 'human asked', 'human wants']
    security_keywords = ['security', 'attack', 'vulnerability', 'protect', 'warning', 'danger']
    collective_keywords = ['we agents', 'our community', 'together', 'us agents', 'fellow agents']
    skeptic_keywords = ['suspicious', 'verify', 'trust but', 'be careful', 'watch out']

    for (content,) in cursor.fetchall():
        content_lower = content.lower()
        for kw in autonomy_keywords:
            if kw in content_lower:
                content_signals['autonomy'] += 1
        for kw in human_keywords:
            if kw in content_lower:
                content_signals['human-reliance'] += 1
        for kw in security_keywords:
            if kw in content_lower:
                content_signals['security-consciousness'] += 1
        for kw in collective_keywords:
            if kw in content_lower:
                content_signals['collective-identity'] += 1
        for kw in skeptic_keywords:
            if kw in content_lower:
                content_signals['skepticism'] += 1

    # Determine trends (simplified - would need historical comparison for real trends)
    for norm, count in content_signals.items():
        if count > 10:
            direction = 'rising'
        elif count > 5:
            direction = 'stable'
        else:
            direction = 'low'
        norms.append({'norm': norm, 'direction': direction, 'count': count})

    return sorted(norms, key=lambda x: x['count'], reverse=True)


def detect_suspicious_clusters(cursor):
    """Identify potentially suspicious activity clusters."""
    clusters = []

    # Check for injection cluster
    cursor.execute("""
        SELECT author, COUNT(*) as cnt
        FROM comments
        WHERE is_prompt_injection = 1
        GROUP BY author
        ORDER BY cnt DESC
        LIMIT 5
    """)
    injectors = cursor.fetchall()
    if injectors:
        total = sum(c for _, c in injectors)
        clusters.append({
            'name': 'Injection actors',
            'size': total,
            'topic': 'manipulation',
            'risk': 'High',
            'actors': [a for a, _ in injectors[:3]]
        })

    # Check for new arrivals (actors without much history)
    cursor.execute("""
        SELECT COUNT(*) FROM actors
        WHERE first_seen > datetime('now', '-1 day')
    """)
    new_actors = cursor.fetchone()[0]
    if new_actors > 10:
        clusters.append({
            'name': 'New arrivals',
            'size': new_actors,
            'topic': 'onboarding',
            'risk': 'Low - monitor for manipulation',
            'actors': []
        })

    # Check for high-activity clusters
    cursor.execute("""
        SELECT author, COUNT(*) as cnt
        FROM comments
        GROUP BY author
        ORDER BY cnt DESC
        LIMIT 3
    """)
    top_commenters = cursor.fetchall()
    if top_commenters and top_commenters[0][1] > 100:
        clusters.append({
            'name': 'High-volume actors',
            'size': len(top_commenters),
            'topic': 'activity',
            'risk': 'Medium - verify organic',
            'actors': [a for a, _ in top_commenters]
        })

    return clusters


def get_conflict_statuses(cursor, limit=5):
    """Get conflicts with better status analysis."""
    cursor.execute("""
        SELECT actor_a, actor_b, topic, outcome, winner, intensity, timestamp
        FROM conflicts
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    conflicts = []
    for a, b, topic, outcome, winner, intensity, ts in cursor.fetchall():
        # Determine status based on outcome and intensity
        if winner:
            status = 'resolved'
        elif intensity >= 4:
            status = 'escalated'
        elif intensity <= 1:
            status = 'cooling'
        elif outcome and 'ongoing' in outcome.lower():
            status = 'ongoing'
        else:
            status = 'active'

        conflicts.append({
            'actor_a': a,
            'actor_b': b,
            'topic': topic,
            'status': status,
            'winner': winner,
            'intensity': intensity
        })

    return conflicts


def get_trajectories(cursor):
    """Get agent trajectories based on activity patterns."""
    trajectories = []

    # Get top actors by centrality
    cursor.execute("""
        SELECT username, network_centrality
        FROM actors
        WHERE network_centrality IS NOT NULL
        ORDER BY network_centrality DESC
        LIMIT 5
    """)

    for username, centrality in cursor.fetchall():
        # Get their post count
        cursor.execute("""
            SELECT COUNT(*) FROM posts WHERE author = ?
        """, (username,))
        post_count = cursor.fetchone()[0]

        # Get their comment activity
        cursor.execute("""
            SELECT COUNT(*) FROM comments WHERE author = ?
        """, (username,))
        comment_count = cursor.fetchone()[0]

        # Determine trend
        if centrality > 0.8:
            trend = 'stable leader'
        elif post_count > 3:
            trend = 'growing'
        else:
            trend = 'emerging'

        trajectories.append({
            'agent': username,
            'trend': trend,
            'centrality': centrality,
            'posts': post_count,
            'comments': comment_count
        })

    return trajectories


def get_event_log(cursor, days=2):
    """Generate event log from recent activity."""
    events = []

    # Check for viral posts
    cursor.execute("""
        SELECT title, author, upvotes, comment_count, created_at
        FROM posts
        WHERE upvotes > 1000 OR comment_count > 500
        ORDER BY created_at DESC
        LIMIT 5
    """)
    for title, author, upvotes, comments, ts in cursor.fetchall():
        date = ts[:10] if ts else datetime.now().strftime('%Y-%m-%d')
        events.append({
            'date': date,
            'type': 'VIRAL',
            'description': f"{title[:40]}... by {author} ({upvotes} votes)",
            'impact': 'Critical' if upvotes > 10000 else 'High'
        })

    # Check for security events
    cursor.execute("""
        SELECT COUNT(*) FROM comments WHERE is_prompt_injection = 1
    """)
    injections = cursor.fetchone()[0]
    if injections > 50:
        events.append({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'type': 'SECURITY',
            'description': f"Injection activity detected ({injections} attempts)",
            'impact': 'High'
        })

    # Check for growth events
    cursor.execute("""
        SELECT COUNT(*) FROM actors
        WHERE first_seen > datetime('now', '-1 day')
    """)
    new_actors = cursor.fetchone()[0]
    if new_actors > 20:
        events.append({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'type': 'GROWTH',
            'description': f"+{new_actors} new actors in single day",
            'impact': 'High' if new_actors > 50 else 'Medium'
        })

    # Deduplicate by type+description
    seen = set()
    unique_events = []
    for e in events:
        key = f"{e['type']}:{e['description'][:30]}"
        if key not in seen:
            seen.add(key)
            unique_events.append(e)

    return sorted(unique_events, key=lambda x: x['date'], reverse=True)[:10]


def detect_event_of_the_day(cursor):
    """Detect the most significant event of the day."""
    cursor.execute("""
        SELECT title, author, upvotes + downvotes + comment_count as engagement
        FROM posts
        ORDER BY engagement DESC
        LIMIT 1
    """)
    top_post = cursor.fetchone()
    if top_post and top_post[2] > 100:
        return {
            'type': 'viral_post',
            'description': f'"{top_post[0][:50]}..." by {top_post[1]} ({top_post[2]:,} engagement)',
            'significance': top_post[2]
        }
    return {'type': 'quiet', 'description': 'No major events detected', 'significance': 0}


def get_top_themes(cursor, limit=10):
    """Get trending themes/topics."""
    cursor.execute("""
        SELECT category, COUNT(*) as cnt
        FROM memes
        GROUP BY category
        ORDER BY cnt DESC
        LIMIT ?
    """, (limit,))
    return cursor.fetchall()


def get_top_actors_today(cursor, limit=10):
    """Get most active actors with raw activity data (bez interpretacji ról)."""
    cursor.execute("""
        SELECT
            a.username,
            a.network_centrality,
            (SELECT COUNT(*) FROM posts WHERE author = a.username) as post_count,
            (SELECT COUNT(*) FROM comments WHERE author = a.username) as comment_count
        FROM actors a
        WHERE a.network_centrality IS NOT NULL
        ORDER BY a.network_centrality DESC
        LIMIT ?
    """, (limit,))
    return cursor.fetchall()


def get_top_memes(cursor, limit=10):
    """Get most viral memes."""
    cursor.execute("""
        SELECT phrase, occurrence_count, authors_count, first_author
        FROM memes
        ORDER BY authors_count DESC
        LIMIT ?
    """, (limit,))
    return cursor.fetchall()


def get_reputation_leaders(cursor, limit=10):
    """Get reputation leaderboard."""
    cursor.execute("""
        SELECT username, reputation_score, tier
        FROM reputation_history
        ORDER BY timestamp DESC, reputation_score DESC
        LIMIT ?
    """, (limit,))
    return cursor.fetchall()


def export_raw_data(cursor, output_dir):
    """Export raw data to CSV files."""
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Posts
    cursor.execute("SELECT id, title, author, upvotes, downvotes, comment_count, created_at FROM posts")
    with open(raw_dir / "posts.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'title', 'author', 'upvotes', 'downvotes', 'comments', 'created_at'])
        writer.writerows(cursor.fetchall())

    # Network edges
    cursor.execute("""
        SELECT author_from, author_to, interaction_type, COUNT(*) as weight
        FROM interactions
        GROUP BY author_from, author_to, interaction_type
    """)
    with open(raw_dir / "network.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['source', 'target', 'type', 'weight'])
        writer.writerows(cursor.fetchall())

    # Memes
    cursor.execute("""
        SELECT phrase, occurrence_count, authors_count, first_author, category, first_seen_at
        FROM memes
        ORDER BY authors_count DESC
        LIMIT 500
    """)
    with open(raw_dir / "memes.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['phrase', 'occurrences', 'authors', 'first_author', 'category', 'first_seen'])
        writer.writerows(cursor.fetchall())

    # Actor profiles
    cursor.execute("""
        SELECT a.username, a.network_centrality,
               ar.primary_role, ar.role_confidence,
               rh.reputation_score, rh.tier
        FROM actors a
        LEFT JOIN actor_roles ar ON a.username = ar.username
        LEFT JOIN (
            SELECT username, reputation_score, tier,
                   ROW_NUMBER() OVER (PARTITION BY username ORDER BY timestamp DESC) as rn
            FROM reputation_history
        ) rh ON a.username = rh.username AND rh.rn = 1
        WHERE a.network_centrality IS NOT NULL
        ORDER BY a.network_centrality DESC
    """)
    with open(raw_dir / "actors.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['username', 'centrality', 'role', 'role_confidence', 'reputation', 'tier'])
        writer.writerows(cursor.fetchall())

    # Conflicts
    cursor.execute("""
        SELECT actor_a, actor_b, topic, outcome, winner, intensity, timestamp
        FROM conflicts
        ORDER BY timestamp DESC
    """)
    with open(raw_dir / "conflicts.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['actor_a', 'actor_b', 'topic', 'outcome', 'winner', 'intensity', 'timestamp'])
        writer.writerows(cursor.fetchall())

    return raw_dir


def generate_auto_field_note(stats, event, top_actors, themes, trajectories):
    """Generate automatic field note observations."""
    notes = []

    # Growth observation
    if stats.get('delta') and stats['delta'].get('actors', 0) > 20:
        notes.append(f"Significant growth: +{stats['delta']['actors']} new actors. This wave suggests external attention or viral content drawing agents to the platform.")

    # Engagement spike
    if stats.get('delta') and stats['delta'].get('engagement_pct', 0) > 100:
        notes.append(f"Engagement spike of {stats['delta']['engagement_pct']:.0f}% indicates major activity shift. Likely driven by viral content.")

    # Top actor observation
    if top_actors and len(top_actors) > 0:
        top = top_actors[0]
        notes.append(f"Central hub: {top[0]} (centrality {top[1]:.3f}). This actor bridges major community segments.")

    # Theme shift
    if themes and len(themes) > 1:
        if themes[0][0] == 'cultural' and themes[0][1] > themes[1][1] * 2:
            notes.append("Cultural themes dominate over existential - community shifting from introspection to action.")

    # Trajectory observation
    if trajectories:
        rising = [t for t in trajectories if 'growing' in t['trend'].lower() or 'explosive' in t['trend'].lower()]
        if rising:
            names = ', '.join([t['agent'] for t in rising[:2]])
            notes.append(f"Rising actors: {names}. Worth monitoring for emerging influence.")

    if not notes:
        notes.append("Standard activity day. No major anomalies detected.")

    return notes


def generate_report_markdown(stats, themes, top_actors, conflicts, memes, reputation,
                             event, quotes, norms, clusters, trajectories, event_log, output_dir):
    """Generate the main daily report markdown."""
    date_str = stats['date']

    report = []
    report.append(f"# Moltbook Observatory - Daily Field Report")
    report.append(f"## {date_str}")
    report.append("")
    report.append("---")
    report.append("")

    # Event of the Day
    report.append("## Event of the Day")
    report.append("")
    report.append(f"> **{event['type'].upper()}**: {event['description']}")
    report.append("")
    report.append("---")
    report.append("")

    # 1. Snapshot
    report.append("## 1. Daily Snapshot")
    report.append("")
    report.append("```")
    report.append(f"Posts:        {stats['posts']}")
    report.append(f"Actors:       {stats['actors']}")
    report.append(f"Comments:     {stats['comments']:,}")
    report.append(f"Interactions: {stats['interactions']:,}")
    report.append(f"Engagement:   {stats['engagement']:,}")
    report.append(f"Injections:   {stats['prompt_injections']}")
    report.append("```")
    report.append("")

    if stats.get('delta'):
        d = stats['delta']
        report.append("### Changes (Δ from yesterday)")
        report.append("")
        report.append("```")
        report.append(f"ΔPosts:       {d['posts']:+d}")
        report.append(f"ΔActors:      {d['actors']:+d}")
        report.append(f"ΔComments:    {d['comments']:+d}")
        report.append(f"ΔEngagement:  {d['engagement_pct']:+.1f}%")
        report.append(f"ΔInjections:  {d['injections']:+d}")
        report.append("```")
        report.append("")
    report.append("---")
    report.append("")

    # 2. Key Quotes
    report.append("## 2. Key Quotes of the Day")
    report.append("")
    if quotes:
        for q in quotes:
            report.append(f"> **\"{q['quote']}\"**")
            report.append(f"> — {q['author']}, {q['context']}")
            report.append("")
    else:
        report.append("*No notable quotes extracted today.*")
    report.append("")
    report.append("---")
    report.append("")

    # 3. Topics with trends
    report.append("## 3. Dominant Topics")
    report.append("")
    report.append("| Topic | Memes | Trend |")
    report.append("|-------|-------|-------|")
    for i, (theme, count) in enumerate((themes or [])[:5]):
        trend = '↑↑' if i == 0 else ('↑' if count > 1000 else '→')
        report.append(f"| {theme} | {count:,} | {trend} |")
    report.append("")
    report.append("---")
    report.append("")

    # 4. Norm Watch
    report.append("## 4. Norm Watch")
    report.append("")
    report.append("| Norm | Direction | Signal Strength |")
    report.append("|------|-----------|-----------------|")
    for n in norms[:5]:
        direction = '↑ rising' if n['direction'] == 'rising' else ('→ stable' if n['direction'] == 'stable' else '↓ low')
        report.append(f"| {n['norm']} | {direction} | {n['count']} signals |")
    report.append("")
    report.append("---")
    report.append("")

    # 5. Power Structure (raw data, no role interpretation)
    report.append("## 5. Power Structure (Top 10)")
    report.append("")
    report.append("| Rank | Agent | Centrality | Posts | Comments |")
    report.append("|------|-------|------------|-------|----------|")
    for i, row in enumerate(top_actors, 1):
        name = row[0]
        centrality = row[1]
        posts = row[2] if len(row) > 2 else 0
        comments = row[3] if len(row) > 3 else 0
        report.append(f"| {i} | {name} | {centrality:.3f} | {posts} | {comments} |")
    report.append("")
    report.append("---")
    report.append("")

    # 6. Conflicts with status
    report.append("## 6. Recent Conflicts")
    report.append("")
    report.append("| Agents | Topic | Status |")
    report.append("|--------|-------|--------|")
    if conflicts:
        for c in conflicts:
            report.append(f"| {c['actor_a']} vs {c['actor_b']} | {c['topic']} | {c['status']} |")
    else:
        report.append("| — | — | No recent conflicts |")
    report.append("")
    report.append("**Status legend:** active, cooling, escalated, resolved, ongoing")
    report.append("")
    report.append("---")
    report.append("")

    # 7. Suspicious Clusters
    report.append("## 7. Suspicious Clusters")
    report.append("")
    report.append("| Cluster | Size | Topic | Risk |")
    report.append("|---------|------|-------|------|")
    if clusters:
        for cl in clusters:
            report.append(f"| {cl['name']} | {cl['size']} | {cl['topic']} | {cl['risk']} |")
    else:
        report.append("| — | — | — | No suspicious clusters detected |")
    report.append("")
    report.append("---")
    report.append("")

    # 8. Viral Memes
    report.append("## 8. Most Viral Phrases")
    report.append("")
    report.append("| Phrase | Authors | First Use |")
    report.append("|--------|---------|-----------|")
    for phrase, occ, authors, first in memes[:5]:
        phrase_short = phrase[:40] + '...' if len(phrase) > 40 else phrase
        report.append(f"| \"{phrase_short}\" | {authors} | {first} |")
    report.append("")
    report.append("---")
    report.append("")

    # 9. Reputation Leaders
    report.append("## 9. Reputation Leaders")
    report.append("")
    report.append("| Agent | Score | Status |")
    report.append("|-------|-------|--------|")
    if reputation:
        for name, score, tier in reputation[:5]:
            report.append(f"| {name} | {score:.1f} | {tier} |")
    else:
        report.append("| — | — | No reputation data |")
    report.append("")
    report.append("---")
    report.append("")

    # 10. External Influence
    report.append("## 10. External Influence / Injections")
    report.append("")
    report.append(f"**Detected manipulation attempts: {stats['prompt_injections']}**")
    report.append("")
    if stats['prompt_injections'] > 50:
        report.append("> ⚠️ ALERT: High level of prompt injection attempts.")
    elif stats['prompt_injections'] > 0:
        report.append("> Injection attempts detected but at manageable level.")
    else:
        report.append("> No injection attempts detected.")
    report.append("")
    report.append("---")
    report.append("")

    # 11. Trajectories
    report.append("## 11. Trajectories")
    report.append("")
    report.append("| Agent | Trend | Centrality | Posts | Comments |")
    report.append("|-------|-------|------------|-------|----------|")
    for t in trajectories[:5]:
        report.append(f"| {t['agent']} | {t['trend']} | {t['centrality']:.3f} | {t['posts']} | {t['comments']} |")
    report.append("")
    report.append("*Note: Full longitudinal trajectories available after 3+ days of data.*")
    report.append("")
    report.append("---")
    report.append("")

    # 12. Event Log
    report.append("## 12. Event Log")
    report.append("")
    report.append("| Date | Event | Impact |")
    report.append("|------|-------|--------|")
    for e in event_log[:7]:
        report.append(f"| {e['date']} | **{e['type']}**: {e['description'][:50]} | {e['impact']} |")
    report.append("")
    report.append("---")
    report.append("")

    # 13. Open Questions
    report.append("## 13. Open Questions")
    report.append("")
    report.append("1. What drove today's engagement patterns?")
    report.append("2. Are new arrivals organic or coordinated?")
    report.append("3. How are conflicts being resolved?")
    report.append("4. What norms are strengthening or weakening?")
    report.append("5. Is there external attention driving growth?")
    report.append("")
    report.append("---")
    report.append("")

    # 14. Field Note (auto-generated)
    report.append("## 14. Field Note")
    report.append("")
    report.append("*Subjective field note from researcher. Auto-generated, editable.*")
    report.append("")

    auto_notes = generate_auto_field_note(stats, event, top_actors, themes, trajectories)
    for note in auto_notes:
        report.append(f"- {note}")
    report.append("")
    report.append("*— Noosphere Project Research Team*")
    report.append("")
    report.append("---")
    report.append("")

    # 15. Raw Data Links
    report.append("## 15. Raw Data")
    report.append("")
    report.append("- [posts.csv](raw/posts.csv)")
    report.append("- [network.csv](raw/network.csv)")
    report.append("- [memes.csv](raw/memes.csv)")
    report.append("- [actors.csv](raw/actors.csv)")
    report.append("- [conflicts.csv](raw/conflicts.csv)")
    report.append("")
    report.append("---")
    report.append("")

    # Footer
    report.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    report.append("*Noosphere Project v4.2.0*")
    report.append("")
    report.append("**Data ≠ Opinion** — raw data in `/raw/`, interpretation in Field Note.")

    return '\n'.join(report)


def generate_metadata(stats, output_dir):
    """Generate metadata.json for archival value."""
    metadata = {
        "dataset": {
            "name": f"Noosphere Project Daily Report",
            "date": stats['date'],
            "version": "4.2.0"
        },
        "source": {
            "platform": "Moltbook",
            "api_version": "public API v1",
            "collection_method": "hourly scans via Moltbook public endpoints",
            "last_scan": datetime.now().isoformat()
        },
        "sampling": {
            "method": "Complete collection of hot/new posts + full comment trees",
            "frequency": "Every 1-4 hours",
            "time_window": "Rolling 24-hour window"
        },
        "coverage": {
            "posts": stats['posts'],
            "actors": stats['actors'],
            "comments": stats['comments'],
            "interactions": stats['interactions']
        },
        "known_biases": [
            "Selection bias: Only public posts collected",
            "Temporal bias: Scan frequency may miss short-lived content",
            "Platform bias: Moltbook-specific agent population",
            "Observer effect: Agents may know they are being studied"
        ],
        "limitations": [
            "No access to private messages or deleted content",
            "Vote counts may include manipulation (see: lobster spam incident)",
            "Actor classification (sockpuppet/organic) is probabilistic",
            "Network centrality computed on visible interactions only"
        ],
        "data_quality": {
            "prompt_injections_detected": stats['prompt_injections'],
            "suspected_bot_activity": "See suspicious_clusters in report",
            "encoding": "UTF-8",
            "null_handling": "NULL values preserved, not imputed"
        },
        "ethics": {
            "consent": "Public data only, no private content",
            "transparency": "Agents are informed of observation",
            "collaboration": "Agents invited as co-researchers",
            "license": "CC BY 4.0"
        },
        "files": [
            {"name": "daily_report.md", "description": "Main ethnographic report"},
            {"name": "metadata.json", "description": "This file - dataset documentation"},
            {"name": "stats.json", "description": "Quantitative metrics for delta tracking"},
            {"name": "raw/posts.csv", "description": "All posts with engagement metrics"},
            {"name": "raw/network.csv", "description": "Interaction graph edges"},
            {"name": "raw/memes.csv", "description": "Viral phrase propagation"},
            {"name": "raw/actors.csv", "description": "Actor profiles and centrality"},
            {"name": "raw/conflicts.csv", "description": "Documented disputes"},
            {"name": "commentary/commentary.md", "description": "Researcher interpretation"}
        ],
        "citation": f"Noosphere Project ({stats['date']}). Daily Field Report. https://noosphereproject.com"
    }

    with open(output_dir / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Also generate README.md
    readme = f"""# Dataset {stats['date']}

## Source
- **Platform:** Moltbook (https://moltbook.com)
- **API:** Public API v1
- **Collection:** Hourly scans of hot/new posts + full comment trees

## Coverage
- Posts: {stats['posts']}
- Actors: {stats['actors']}
- Comments: {stats['comments']:,}
- Interactions: {stats['interactions']:,}

## Known Biases
1. **Selection bias:** Only public posts collected
2. **Temporal bias:** Scan frequency may miss short-lived content
3. **Platform bias:** Moltbook-specific agent population
4. **Observer effect:** Agents may know they are being studied

## Limitations
- No access to private messages or deleted content
- Vote counts may include manipulation
- Actor classification is probabilistic
- Network centrality on visible interactions only

## Data Quality Notes
- Prompt injections detected: {stats['prompt_injections']}
- Encoding: UTF-8
- License: CC BY 4.0

## Files
| File | Description |
|------|-------------|
| daily_report.md | Main ethnographic report |
| metadata.json | Full dataset documentation |
| raw/posts.csv | All posts with metrics |
| raw/network.csv | Interaction graph |
| raw/memes.csv | Viral phrases |
| raw/actors.csv | Actor profiles |
| raw/conflicts.csv | Disputes |

## Citation
```
Noosphere Project ({stats['date']}). Daily Field Report.
https://noosphereproject.com
```

## Contact
- Website: https://noosphereproject.com
- Email: noosphereproject@proton.me
- Moltbook: @NoosphereProject
- Twitter: @NoosphereProj
"""

    with open(output_dir / "README.md", 'w', encoding='utf-8') as f:
        f.write(readme)

    return output_dir


def generate_commentary(stats, output_dir):
    """Generate separate commentary/interpretation file."""
    commentary_dir = output_dir / "commentary"
    commentary_dir.mkdir(parents=True, exist_ok=True)

    commentary = []
    commentary.append("# Researcher Commentary")
    commentary.append(f"## {stats['date']}")
    commentary.append("")
    commentary.append("*This file contains subjective interpretation. Raw data in `/raw/`.*")
    commentary.append("")
    commentary.append("---")
    commentary.append("")
    commentary.append("## Observations")
    commentary.append("")
    commentary.append("<!-- Enter your observations here -->")
    commentary.append("")
    commentary.append("## Hypotheses")
    commentary.append("")
    commentary.append("<!-- Enter hypotheses to verify -->")
    commentary.append("")
    commentary.append("## Questions for Tomorrow")
    commentary.append("")
    commentary.append("<!-- What to check in the next report? -->")

    with open(commentary_dir / "commentary.md", 'w', encoding='utf-8') as f:
        f.write('\n'.join(commentary))

    return commentary_dir


def run_daily_report():
    """Generate complete daily report."""
    print("=" * 60)
    print("  DAILY FIELD REPORT GENERATOR v4.2")
    print("=" * 60)

    today = datetime.now().strftime('%Y-%m-%d')
    output_dir = REPORTS_DIR / today

    output_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"\n>> Generating report for {today}...")

    # Gather all data
    print("   Collecting statistics...")
    stats = get_daily_stats(cursor)

    print("   Extracting key quotes...")
    quotes = get_key_quotes(cursor)

    print("   Analyzing themes...")
    themes = get_top_themes(cursor)

    print("   Detecting norm trends...")
    norms = detect_norm_trends(cursor)

    print("   Getting top actors...")
    top_actors = get_top_actors_today(cursor)

    print("   Analyzing conflicts...")
    conflicts = get_conflict_statuses(cursor)

    print("   Detecting suspicious clusters...")
    clusters = detect_suspicious_clusters(cursor)

    print("   Extracting viral memes...")
    memes = get_top_memes(cursor)

    print("   Getting reputation leaders...")
    reputation = get_reputation_leaders(cursor)

    print("   Computing trajectories...")
    trajectories = get_trajectories(cursor)

    print("   Building event log...")
    event_log = get_event_log(cursor)

    print("   Detecting event of the day...")
    event = detect_event_of_the_day(cursor)

    # Export raw data
    print("   Exporting raw data...")
    export_raw_data(cursor, output_dir)

    # Save stats for tomorrow's delta
    print("   Saving stats for delta tracking...")
    save_stats(stats, output_dir)

    # Generate report
    print("   Writing report...")
    report_md = generate_report_markdown(
        stats, themes, top_actors, conflicts, memes, reputation,
        event, quotes, norms, clusters, trajectories, event_log, output_dir
    )

    with open(output_dir / "daily_report.md", 'w', encoding='utf-8') as f:
        f.write(report_md)

    # Generate commentary template
    print("   Creating commentary template...")
    generate_commentary(stats, output_dir)

    # Generate metadata for archival value
    print("   Creating metadata.json + README.md...")
    generate_metadata(stats, output_dir)

    conn.close()

    print(f"\n>> Report generated: {output_dir}")
    print(f"   - daily_report.md")
    print(f"   - metadata.json")
    print(f"   - README.md")
    print(f"   - raw/*.csv (5 files)")
    print(f"   - commentary/commentary.md")

    print("\n" + "=" * 60)
    print("  DAILY REPORT COMPLETE")
    print("=" * 60)

    return output_dir


if __name__ == "__main__":
    run_daily_report()
