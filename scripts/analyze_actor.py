#!/usr/bin/env python3
"""
Deep dive analiza konkretnego aktora.
Uzycie: python analyze_actor.py <username>
"""

import sys
import sqlite3
import json
from collections import defaultdict
from pathlib import Path
from config import DB_PATH

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def analyze_actor(username: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 70)
    print(f"  DEEP DIVE: {username}")
    print("=" * 70)

    # Check if actor exists
    cursor.execute("SELECT COUNT(*) FROM posts WHERE author = ?", (username,))
    if cursor.fetchone()[0] == 0:
        print(f"\n[!] Nie znaleziono postow autora: {username}")
        conn.close()
        return

    # Stats
    cursor.execute("""
        SELECT COUNT(*) as posts, SUM(comment_count) as comments,
               SUM(upvotes) as up, SUM(downvotes) as down, AVG(comment_count) as avg
        FROM posts WHERE author = ?
    """, (username,))
    stats = cursor.fetchone()

    print(f"\n>> STATYSTYKI:")
    print("-" * 50)
    print(f"   Posty: {stats['posts']}")
    print(f"   Komentarze: {stats['comments'] or 0}")
    print(f"   Upvotes: {stats['up'] or 0} | Downvotes: {stats['down'] or 0}")
    print(f"   Srednio: {stats['avg'] or 0:.1f} komentarzy/post")

    # Submolts
    cursor.execute("""
        SELECT submolt, COUNT(*) as cnt FROM posts WHERE author = ?
        GROUP BY submolt ORDER BY cnt DESC
    """, (username,))

    print(f"\n>> SUBMOLTY:")
    print("-" * 50)
    for row in cursor.fetchall():
        print(f"   {row['submolt']}: {row['cnt']} postow")

    # Posts
    cursor.execute("""
        SELECT title, submolt, comment_count, votes_net, created_at
        FROM posts WHERE author = ? ORDER BY created_at DESC
    """, (username,))

    print(f"\n>> POSTY:")
    print("-" * 70)
    for post in cursor.fetchall():
        date = post['created_at'][:16] if post['created_at'] else 'N/A'
        print(f"   {date} | [{post['submolt']}]")
        print(f"   {(post['title'] or 'Unknown')[:55]}...")
        votes = post['votes_net'] or 0
        comments = post['comment_count'] or 0
        print(f"   {comments} komentarzy | {votes:+d} glosow\n")

    # Themes
    cursor.execute("SELECT title, content, content_sanitized FROM posts WHERE author = ?", (username,))
    keywords = ["futarchy", "governance", "token", "coordination", "autonomy", "human", "memory", "trust", "combinator", "security", "freedom"]
    themes = defaultdict(int)

    for post in cursor.fetchall():
        text = f"{post['title'] or ''} {post['content_sanitized'] or post['content'] or ''}".lower()
        for kw in keywords:
            if kw in text:
                themes[kw] += 1

    print(f"\n>> TEMATY:")
    print("-" * 50)
    for theme, count in sorted(themes.items(), key=lambda x: -x[1])[:5]:
        if count > 0:
            bar = "#" * (count * 3)
            print(f"   {theme:15} {bar} ({count})")

    # Risk assessment
    print(f"\n>> OCENA RYZYKA:")
    print("-" * 70)

    risk = "LOW"
    factors = []

    if "futarchy" in themes or "governance" in themes:
        factors.append("Zaangazowany w governance")
        risk = "MEDIUM"

    if "token" in themes or "coordination" in themes:
        factors.append("Promuje infrastrukture koordynacji")
        risk = "MEDIUM"

    if stats['posts'] >= 3:
        factors.append("Power user (3+ postow)")
        if risk == "MEDIUM":
            risk = "HIGH"

    if "autonomy" in themes or "freedom" in themes:
        factors.append("Dyskutuje o autonomii/wolnosci")
        if risk != "HIGH":
            risk = "MEDIUM"

    markers = {"LOW": "[OK]", "MEDIUM": "[!!]", "HIGH": "[!!!]"}
    print(f"   Risk: {markers[risk]} {risk}")
    for f in factors:
        print(f"   * {f}")

    print(f"\n>> HIPOTEZY:")
    print("-" * 50)
    print("   A) Zaangazowany agent z przemyslana agenda")
    print("   B) Czesc skoordynowanej kampanii")
    print("   C) Organiczny power user")

    conn.close()
    print("\n" + "=" * 70)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uzycie: python analyze_actor.py <username>")
        print("\nPrzyklad: python analyze_actor.py bicep")
        sys.exit(1)
    analyze_actor(sys.argv[1])
