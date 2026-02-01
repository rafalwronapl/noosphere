#!/usr/bin/env python3
"""
Longitudinal Tracker - Track changes over time.
Trajectories, Event Log, Researcher Interactions.
"""

import sys
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

try:
    from config import DB_PATH, setup_logging
    logger = setup_logging("longitudinal")
except ImportError:
    DB_PATH = Path.home() / "moltbook-observatory" / "data" / "observatory.db"
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("longitudinal")

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def init_tables(cursor):
    """Create longitudinal tracking tables."""

    # Event Log - significant events
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            event_type TEXT NOT NULL,
            event_title TEXT NOT NULL,
            description TEXT,
            impact TEXT,
            actors_involved TEXT,
            metrics_affected TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Trajectories - weekly/daily metrics snapshots
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trajectory_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL,
            previous_value REAL,
            change_pct REAL,
            trend TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, metric_name)
        )
    """)

    # Researcher Interaction Log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS researcher_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            action_type TEXT NOT NULL,
            action_description TEXT,
            platform TEXT,
            target_id TEXT,
            reaction_count INTEGER DEFAULT 0,
            reaction_summary TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)


def log_event(cursor, event_type: str, title: str, description: str = None,
              impact: str = None, actors: list = None, metrics: list = None):
    """Log a significant event."""
    cursor.execute("""
        INSERT INTO event_log (date, event_type, event_title, description,
                               impact, actors_involved, metrics_affected)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime('%Y-%m-%d'),
        event_type,
        title,
        description,
        impact,
        json.dumps(actors) if actors else None,
        json.dumps(metrics) if metrics else None
    ))
    logger.info(f"Event logged: [{event_type}] {title}")


def save_trajectory_snapshot(cursor):
    """Calculate and save current metrics for trajectory tracking."""
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    metrics = {}

    # 1. Post count
    cursor.execute("SELECT COUNT(*) FROM posts")
    metrics['total_posts'] = cursor.fetchone()[0]

    # 2. Comment count
    cursor.execute("SELECT COUNT(*) FROM comments")
    metrics['total_comments'] = cursor.fetchone()[0]

    # 3. Interaction count
    cursor.execute("SELECT COUNT(*) FROM interactions")
    metrics['total_interactions'] = cursor.fetchone()[0]

    # 4. Prompt injection count
    cursor.execute("SELECT COUNT(*) FROM comments WHERE is_prompt_injection = 1")
    metrics['injection_count'] = cursor.fetchone()[0]

    # 5. Active authors (last 24h)
    cursor.execute("""
        SELECT COUNT(DISTINCT author) FROM comments
        WHERE scraped_at > datetime('now', '-24 hours')
    """)
    metrics['active_authors_24h'] = cursor.fetchone()[0]

    # 6. Conflict count
    cursor.execute("SELECT COUNT(*) FROM conflicts")
    metrics['total_conflicts'] = cursor.fetchone()[0]

    # 7. Meme count
    cursor.execute("SELECT COUNT(*) FROM memes")
    metrics['total_memes'] = cursor.fetchone()[0]

    # 8. Hub dominance (top actor's % of interactions)
    cursor.execute("""
        SELECT CAST(MAX(cnt) AS REAL) / CAST(SUM(cnt) AS REAL) * 100
        FROM (
            SELECT COUNT(*) as cnt FROM interactions GROUP BY author_to
        )
    """)
    result = cursor.fetchone()[0]
    metrics['hub_dominance_pct'] = round(result, 2) if result else 0

    # 9. Average meme spread (authors per meme)
    cursor.execute("SELECT AVG(authors_count) FROM memes WHERE authors_count > 1")
    result = cursor.fetchone()[0]
    metrics['avg_meme_spread'] = round(result, 2) if result else 0

    # Save each metric
    for metric_name, value in metrics.items():
        # Get previous value
        cursor.execute("""
            SELECT metric_value FROM trajectory_snapshots
            WHERE metric_name = ? AND date < ?
            ORDER BY date DESC LIMIT 1
        """, (metric_name, today))
        prev = cursor.fetchone()
        prev_value = prev[0] if prev else None

        # Calculate change
        change_pct = None
        trend = 'stable'
        if prev_value and prev_value != 0:
            change_pct = round((value - prev_value) / prev_value * 100, 2)
            if change_pct > 5:
                trend = 'rising'
            elif change_pct < -5:
                trend = 'falling'

        # Insert or update
        cursor.execute("""
            INSERT OR REPLACE INTO trajectory_snapshots
            (date, metric_name, metric_value, previous_value, change_pct, trend)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (today, metric_name, value, prev_value, change_pct, trend))

    logger.info(f"Trajectory snapshot saved: {len(metrics)} metrics")
    return metrics


def log_researcher_action(cursor, action_type: str, description: str,
                          platform: str = "moltbook", target_id: str = None,
                          notes: str = None):
    """Log a researcher/bot action."""
    cursor.execute("""
        INSERT INTO researcher_log (date, action_type, action_description,
                                    platform, target_id, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime('%Y-%m-%d'),
        action_type,
        description,
        platform,
        target_id,
        notes
    ))
    logger.info(f"Researcher action logged: [{action_type}] {description}")


def update_researcher_reaction(cursor, action_id: int, reaction_count: int,
                               reaction_summary: str):
    """Update reaction to a researcher action."""
    cursor.execute("""
        UPDATE researcher_log
        SET reaction_count = ?, reaction_summary = ?
        WHERE id = ?
    """, (reaction_count, reaction_summary, action_id))


def get_trajectories(cursor, days: int = 7) -> list:
    """Get trajectory data for last N days."""
    cursor.execute("""
        SELECT date, metric_name, metric_value, change_pct, trend
        FROM trajectory_snapshots
        WHERE date > date('now', ?)
        ORDER BY date DESC, metric_name
    """, (f'-{days} days',))
    return cursor.fetchall()


def get_event_log(cursor, days: int = 30) -> list:
    """Get recent events."""
    cursor.execute("""
        SELECT date, event_type, event_title, impact
        FROM event_log
        WHERE date > date('now', ?)
        ORDER BY date DESC
    """, (f'-{days} days',))
    return cursor.fetchall()


def get_researcher_log(cursor, days: int = 7) -> list:
    """Get recent researcher actions."""
    cursor.execute("""
        SELECT date, action_type, action_description, reaction_count, reaction_summary
        FROM researcher_log
        WHERE date > date('now', ?)
        ORDER BY date DESC
    """, (f'-{days} days',))
    return cursor.fetchall()


def generate_trajectory_report(cursor) -> str:
    """Generate trajectory section for daily report."""
    today = datetime.now().strftime('%Y-%m-%d')

    cursor.execute("""
        SELECT metric_name, metric_value, change_pct, trend
        FROM trajectory_snapshots
        WHERE date = ?
        ORDER BY ABS(COALESCE(change_pct, 0)) DESC
    """, (today,))

    rows = cursor.fetchall()
    if not rows:
        return "No trajectory data for today."

    lines = ["| Metric | Value | Change | Trend |",
             "|--------|-------|--------|-------|"]

    for row in rows:
        name = row[0].replace('_', ' ').title()
        value = f"{row[1]:,.0f}" if row[1] else "N/A"
        change = f"{row[2]:+.1f}%" if row[2] else "—"
        trend_emoji = {"rising": "📈", "falling": "📉", "stable": "➡️"}.get(row[3], "")
        lines.append(f"| {name} | {value} | {change} | {trend_emoji} |")

    return '\n'.join(lines)


def generate_event_log_report(cursor, days: int = 30) -> str:
    """Generate event log section for daily report."""
    events = get_event_log(cursor, days)

    if not events:
        return "No events logged yet."

    lines = ["| Date | Event | Impact |",
             "|------|-------|--------|"]

    for event in events[:10]:  # Last 10 events
        date = event[0]
        title = f"**{event[1]}**: {event[2]}"[:50]
        impact = event[3] or "—"
        lines.append(f"| {date} | {title} | {impact} |")

    return '\n'.join(lines)


def generate_researcher_log_report(cursor) -> str:
    """Generate researcher interaction log for daily report."""
    actions = get_researcher_log(cursor, 7)

    if not actions:
        return "No researcher actions logged yet."

    lines = []
    for action in actions[:5]:
        date = action[0]
        action_type = action[1]
        desc = action[2][:60] if action[2] else ""
        reaction = action[3] or 0
        summary = action[4] or "no reaction yet"

        lines.append(f"- **{date}** [{action_type}]: {desc}")
        lines.append(f"  → Reaction: {reaction} ({summary})")

    return '\n'.join(lines)


def auto_detect_events(cursor):
    """Auto-detect significant events from data changes."""
    today = datetime.now().strftime('%Y-%m-%d')

    # Check for injection spike
    cursor.execute("""
        SELECT COUNT(*) FROM comments
        WHERE is_prompt_injection = 1
        AND scraped_at > datetime('now', '-24 hours')
    """)
    recent_injections = cursor.fetchone()[0]

    if recent_injections > 50:
        log_event(cursor,
                  event_type="SECURITY",
                  title=f"Injection wave detected ({recent_injections} attempts)",
                  impact="High",
                  metrics=["injection_count", "trust"])

    # Check for new viral meme
    cursor.execute("""
        SELECT phrase, authors_count FROM memes
        WHERE first_seen_at > datetime('now', '-24 hours')
        AND authors_count > 20
        ORDER BY authors_count DESC
        LIMIT 1
    """)
    viral = cursor.fetchone()
    if viral:
        log_event(cursor,
                  event_type="CULTURAL",
                  title=f"New viral meme: \"{viral[0][:30]}...\"",
                  description=f"Spread to {viral[1]} authors in <24h",
                  impact="Medium",
                  metrics=["meme_spread"])

    # Check for major conflict
    cursor.execute("""
        SELECT actor_a, actor_b, topic FROM conflicts
        WHERE timestamp > datetime('now', '-24 hours')
        AND intensity >= 8
        LIMIT 1
    """)
    conflict = cursor.fetchone()
    if conflict:
        log_event(cursor,
                  event_type="CONFLICT",
                  title=f"High-intensity conflict: {conflict[0]} vs {conflict[1]}",
                  description=f"Topic: {conflict[2]}",
                  impact="Medium",
                  actors=[conflict[0], conflict[1]])


def run_daily_tracking():
    """Run all daily tracking tasks."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Initialize tables
    init_tables(cursor)
    conn.commit()

    # Save trajectory snapshot
    metrics = save_trajectory_snapshot(cursor)
    conn.commit()

    # Auto-detect events
    auto_detect_events(cursor)
    conn.commit()

    # Print report
    print("\n" + "="*60)
    print("  LONGITUDINAL TRACKER - Daily Update")
    print("="*60)

    print("\n## Trajectories\n")
    print(generate_trajectory_report(cursor))

    print("\n## Event Log\n")
    print(generate_event_log_report(cursor))

    print("\n## Researcher Log\n")
    print(generate_researcher_log_report(cursor))

    conn.close()


if __name__ == "__main__":
    run_daily_tracking()
