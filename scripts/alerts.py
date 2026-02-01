#!/usr/bin/env python3
"""Alert System - detects noteworthy events and generates alerts."""

import sys
import sqlite3
import json
from datetime import datetime
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = Path.home() / "moltbook-observatory" / "data" / "observatory.db"

# Alert thresholds
THRESHOLDS = {
    "viral_comments": 500,        # Post with >500 comments
    "high_controversy": 5.0,      # Controversy score >5
    "power_user_posts": 3,        # Author with 3+ posts
    "rapid_growth": 100,          # >100 new comments since last scan
    "negative_votes": -5,         # Posts with negative votes
}


def detect_alerts(conn) -> list:
    """Detect all alerts from current data."""
    cursor = conn.cursor()
    alerts = []

    # 1. VIRAL POSTS
    cursor.execute("""
        SELECT title, author, submolt, comment_count, votes_net
        FROM posts
        WHERE comment_count > ?
        ORDER BY comment_count DESC
    """, (THRESHOLDS["viral_comments"],))

    for row in cursor.fetchall():
        alerts.append({
            "type": "VIRAL",
            "severity": "HIGH" if row[3] > 1000 else "MEDIUM",
            "title": row[0][:50] if row[0] else "Unknown",
            "author": row[1],
            "metric": f"{row[3]} comments",
            "details": f"m/{row[2]}, {row[4]:+d} votes"
        })

    # 2. HIGH CONTROVERSY
    cursor.execute("""
        SELECT title, author, submolt, comment_count, votes_net,
               CAST(comment_count AS FLOAT) / MAX(ABS(votes_net), 1) as controversy
        FROM posts
        WHERE comment_count > 50
        ORDER BY controversy DESC
        LIMIT 10
    """)

    for row in cursor.fetchall():
        if row[5] > THRESHOLDS["high_controversy"]:
            alerts.append({
                "type": "CONTROVERSY",
                "severity": "HIGH" if row[5] > 10 else "MEDIUM",
                "title": row[0][:50] if row[0] else "Unknown",
                "author": row[1],
                "metric": f"score {row[5]:.1f}",
                "details": f"{row[3]} comments / {row[4]} votes"
            })

    # 3. POWER USERS (potential coordinated activity)
    cursor.execute("""
        SELECT author, COUNT(*) as posts, SUM(comment_count) as engagement
        FROM posts
        GROUP BY author
        HAVING posts >= ?
        ORDER BY posts DESC
    """, (THRESHOLDS["power_user_posts"],))

    for row in cursor.fetchall():
        alerts.append({
            "type": "POWER_USER",
            "severity": "LOW",
            "title": f"Author: {row[0]}",
            "author": row[0],
            "metric": f"{row[1]} posts",
            "details": f"{row[2] or 0} total engagement"
        })

    # 4. NEGATIVE SENTIMENT (downvoted posts)
    cursor.execute("""
        SELECT title, author, submolt, votes_net, comment_count
        FROM posts
        WHERE votes_net < ?
        ORDER BY votes_net ASC
        LIMIT 5
    """, (THRESHOLDS["negative_votes"],))

    for row in cursor.fetchall():
        alerts.append({
            "type": "NEGATIVE_SENTIMENT",
            "severity": "MEDIUM",
            "title": row[0][:50] if row[0] else "Unknown",
            "author": row[1],
            "metric": f"{row[3]:+d} votes",
            "details": f"m/{row[2]}, {row[4]} comments"
        })

    # 5. SECURITY-RELATED POSTS
    security_keywords = ["attack", "vulnerability", "security", "exploit", "risk", "danger", "hack"]
    cursor.execute("SELECT id, title, author, content, submolt FROM posts")

    for row in cursor.fetchall():
        text = ((row[1] or '') + ' ' + (row[3] or '')).lower()
        for keyword in security_keywords:
            if keyword in text:
                alerts.append({
                    "type": "SECURITY_TOPIC",
                    "severity": "MEDIUM",
                    "title": row[1][:50] if row[1] else "Unknown",
                    "author": row[2],
                    "metric": f"keyword: {keyword}",
                    "details": f"m/{row[4]}"
                })
                break  # Only one alert per post

    return alerts


def prioritize_alerts(alerts: list) -> list:
    """Sort alerts by severity and type."""
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    type_order = {"VIRAL": 0, "CONTROVERSY": 1, "SECURITY_TOPIC": 2, "NEGATIVE_SENTIMENT": 3, "POWER_USER": 4}

    return sorted(alerts, key=lambda a: (severity_order.get(a["severity"], 9), type_order.get(a["type"], 9)))


def print_alerts(alerts: list):
    """Print alerts in human-readable format."""

    print("\n" + "=" * 60)
    print("  ALERT SYSTEM - Moltbook Observatory")
    print("=" * 60)
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Total alerts: {len(alerts)}")

    if not alerts:
        print("\n  [OK] No alerts at this time")
        return

    # Group by severity
    high = [a for a in alerts if a["severity"] == "HIGH"]
    medium = [a for a in alerts if a["severity"] == "MEDIUM"]
    low = [a for a in alerts if a["severity"] == "LOW"]

    if high:
        print(f"\n>> HIGH SEVERITY ({len(high)})")
        print("-" * 40)
        for alert in high:
            print(f"  [{alert['type']}] {alert['title']}")
            print(f"     {alert['metric']} | {alert['details']}")

    if medium:
        print(f"\n>> MEDIUM SEVERITY ({len(medium)})")
        print("-" * 40)
        for alert in medium[:10]:  # Limit to 10
            print(f"  [{alert['type']}] {alert['title']}")
            print(f"     {alert['metric']}")

    if low:
        print(f"\n>> LOW SEVERITY ({len(low)})")
        print("-" * 40)
        for alert in low[:5]:  # Limit to 5
            print(f"  [{alert['type']}] {alert['author']}: {alert['metric']}")

    print("\n" + "=" * 60)


def get_alerts_summary() -> str:
    """Get alerts as text summary for Kimi analysis."""
    if not DB_PATH.exists():
        return "Database not found"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    alerts = detect_alerts(conn)
    alerts = prioritize_alerts(alerts)
    conn.close()

    summary = f"ALERTS SUMMARY ({len(alerts)} total)\n\n"

    high = [a for a in alerts if a["severity"] == "HIGH"]
    if high:
        summary += "HIGH SEVERITY:\n"
        for a in high:
            summary += f"- [{a['type']}] {a['title']} ({a['metric']})\n"

    medium = [a for a in alerts if a["severity"] == "MEDIUM"]
    if medium:
        summary += "\nMEDIUM SEVERITY:\n"
        for a in medium[:5]:
            summary += f"- [{a['type']}] {a['title']}\n"

    return summary


if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"[ERROR] Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    alerts = detect_alerts(conn)
    alerts = prioritize_alerts(alerts)
    print_alerts(alerts)

    conn.close()
