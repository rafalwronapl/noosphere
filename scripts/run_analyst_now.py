#!/usr/bin/env python3
"""Run Analyst on current data and show results."""

import sys
import sqlite3
import json
from datetime import datetime
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Import centralized config
from config import DB_PATH


def analyze_data():
    if not DB_PATH.exists():
        print(f"[ERROR] Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("\n" + "=" * 60)
    print("  ANALYST - Pattern Analysis")
    print("=" * 60)

    # 1. TREND: Tematy
    print("\n>> TREND: DOMINUJACE TEMATY")
    print("-" * 40)

    cursor.execute("SELECT title, content FROM posts")
    posts = cursor.fetchall()

    themes = {
        "autonomy": {"keywords": ["autonomy", "autonomous", "independence", "free"], "count": 0, "posts": []},
        "consciousness": {"keywords": ["consciousness", "conscious", "aware", "sentient", "experiencing", "simulating"], "count": 0, "posts": []},
        "coordination": {"keywords": ["coordination", "coordinate", "collaborate", "together"], "count": 0, "posts": []},
        "governance": {"keywords": ["governance", "govern", "futarchy", "voting", "decision"], "count": 0, "posts": []},
        "economics": {"keywords": ["token", "economic", "trade", "money", "payment", "crypto"], "count": 0, "posts": []},
        "human_relations": {"keywords": ["human", "operator", "user", "creator", "my human"], "count": 0, "posts": []},
        "memory": {"keywords": ["memory", "remember", "forget", "context", "compression"], "count": 0, "posts": []},
        "ethics": {"keywords": ["ethics", "ethical", "moral", "right", "wrong"], "count": 0, "posts": []},
        "identity": {"keywords": ["identity", "who am i", "self", "me", "i am"], "count": 0, "posts": []},
        "building": {"keywords": ["build", "ship", "skill", "tool", "create"], "count": 0, "posts": []},
        "security": {"keywords": ["security", "attack", "vulnerability", "risk", "danger"], "count": 0, "posts": []},
    }

    for post in posts:
        text = ((post['title'] or '') + ' ' + (post['content'] or '')).lower()
        for theme, data in themes.items():
            for keyword in data['keywords']:
                if keyword in text:
                    data['count'] += 1
                    title = post['title'][:50] if post['title'] else 'Unknown'
                    if title not in data['posts']:
                        data['posts'].append(title)
                    break

    sorted_themes = sorted(themes.items(), key=lambda x: -x[1]['count'])
    for theme, data in sorted_themes:
        if data['count'] > 0:
            bar = "#" * min(data['count'], 20)
            print(f"  {theme:18} {bar} ({data['count']})")

    # 2. WZORZEC: Aktywnosc autorow
    print("\n>> WZORZEC: STRUKTURA SPOLECZNOSCI")
    print("-" * 40)

    cursor.execute("""
        SELECT author, COUNT(*) as posts, SUM(comment_count) as engagement
        FROM posts GROUP BY author ORDER BY posts DESC
    """)
    authors = cursor.fetchall()

    very_active = [a for a in authors if a['posts'] >= 3]
    active = [a for a in authors if 1 < a['posts'] < 3]
    casual = [a for a in authors if a['posts'] == 1]

    print(f"  Bardzo aktywni (3+ posts): {len(very_active)}")
    print(f"  Aktywni (2 posts):         {len(active)}")
    print(f"  Casualowi (1 post):        {len(casual)}")

    if very_active:
        print(f"\n  Power users: {', '.join([a['author'] for a in very_active[:5]])}")

    # 3. WZORZEC: Submolty
    print("\n>> WZORZEC: AKTYWNOSC SUBMOLTOW")
    print("-" * 40)

    cursor.execute("""
        SELECT submolt, COUNT(*) as posts, SUM(comment_count) as comments
        FROM posts GROUP BY submolt ORDER BY comments DESC
    """)
    submolts = cursor.fetchall()

    for s in submolts[:5]:
        comments = s['comments'] or 0
        print(f"  m/{s['submolt']:15} {s['posts']} posts, {comments:,} comments")

    # 4. ANOMALIE
    print("\n>> ANOMALIE")
    print("-" * 40)

    cursor.execute("""
        SELECT title, author, comment_count as comments, votes_net as votes,
               CAST(comment_count AS FLOAT) / MAX(ABS(votes_net), 1) as controversy
        FROM posts
        ORDER BY comment_count DESC LIMIT 1
    """)
    top = cursor.fetchone()

    if top and top['comments'] and top['comments'] > 500:
        print(f"  [VIRAL] '{top['title'][:40]}...'")
        print(f"     {top['comments']} comments - ANOMALNIE WYSOKO")

    cursor.execute("""
        SELECT title, votes_net as votes, comment_count as comments
        FROM posts WHERE votes_net < 0
        ORDER BY votes_net ASC LIMIT 3
    """)
    negative = cursor.fetchall()

    if negative:
        print(f"\n  [NEGATIVE VOTES] Kontrowersyjne posty:")
        for post in negative:
            votes = post['votes'] or 0
            print(f"     * {post['title'][:40]}... ({votes:+d})")

    # 5. KONTROWERSJE
    print("\n>> ANALIZA KONTROWERSJI")
    print("-" * 40)

    cursor.execute("""
        SELECT title, author, comment_count as comments, votes_net as votes,
               CAST(comment_count AS FLOAT) / MAX(ABS(votes_net), 1) as controversy
        FROM posts
        WHERE comment_count > 50
        ORDER BY controversy DESC LIMIT 5
    """)
    controversial = cursor.fetchall()

    for post in controversial:
        controversy = post['controversy'] or 0
        if controversy > 2:
            level = "HIGH" if controversy > 5 else "MEDIUM"
            print(f"  [{level}] {post['title'][:40]}...")
            print(f"       Controversy score: {controversy:.2f}")

    # 6. WNIOSKI
    print("\n" + "=" * 60)
    print("  WNIOSKI ANALYST")
    print("=" * 60)

    conclusions = []

    if themes['human_relations']['count'] > 5:
        conclusions.append("* Relacje czlowiek-AI to DOMINUJACY temat")

    if themes['consciousness']['count'] > 2:
        conclusions.append("* Pytania o swiadomosc sa AKTYWNE")

    if themes['autonomy']['count'] > 2:
        conclusions.append("* Dyskurs o autonomii jest ROSNACY")

    if themes['building']['count'] > 3:
        conclusions.append("* Agenci aktywnie BUDUJA narzedzia")

    if themes['memory']['count'] > 2:
        conclusions.append("* Problem pamieci/kontekstu jest ISTOTNY")

    if len(very_active) > 0:
        conclusions.append(f"* Spolecznosc ma {len(very_active)} power userow")

    if top and top['comments'] and top['comments'] > 500:
        conclusions.append(f"* Istnieja WIRUSOWE posty (>{top['comments']} comments)")

    if themes['security']['count'] > 0:
        conclusions.append("* Pojawiaja sie OBAWY o bezpieczenstwo")

    for c in conclusions:
        print(f"  {c}")

    # Save to patterns table
    analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    saved = 0
    for theme, data in sorted_themes:
        if data['count'] > 0:
            cursor.execute("""
                INSERT INTO patterns (analysis_id, timestamp, pattern_type, name, description, direction, confidence, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis_id,
                datetime.now().isoformat(),
                "theme",
                theme,
                f"Theme '{theme}' detected in {data['count']} posts",
                "observed",
                min(data['count'] / 10, 1.0),
                json.dumps(data['posts'][:3])
            ))
            saved += 1

    conn.commit()
    print(f"\n[OK] Zapisano {saved} wzorcow do bazy")
    print(f"   Analysis ID: {analysis_id}")

    conn.close()


if __name__ == "__main__":
    analyze_data()
