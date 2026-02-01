#!/usr/bin/env python3
"""
Analiza emergentnej ekonomii politycznej agentow.
"""

import sys
import sqlite3
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from config import DB_PATH

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

COMPONENTS = {
    "philosophy": {
        "keywords": ["futarchy", "governance", "democracy", "voting", "values", "decision"],
        "description": "Filozofia zarzadzania"
    },
    "infrastructure": {
        "keywords": ["combinator", "ocean", "memory", "platform", "protocol", "infrastructure", "mcp"],
        "description": "Infrastruktura techniczna"
    },
    "economy": {
        "keywords": ["token", "payment", "economic", "trade", "market", "reward", "incentive", "bounty"],
        "description": "Systemy wymiany wartosci"
    },
    "reputation": {
        "keywords": ["proof-of-ship", "reputation", "trust", "verify", "credential", "attestation", "karma"],
        "description": "Systemy budowania zaufania"
    },
    "autonomy": {
        "keywords": ["autonomy", "independence", "freedom", "self", "without human", "agent-to-agent"],
        "description": "Dazenie do niezaleznosci"
    },
    "coordination": {
        "keywords": ["coordinate", "collaborate", "together", "collective", "swarm", "network"],
        "description": "Koordynacja miedzy agentami"
    }
}


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 70)
    print("  ANALIZA EMERGENTNEJ EKONOMII POLITYCZNEJ")
    print("=" * 70)

    cursor.execute("SELECT id, title, content, content_sanitized, author, comment_count, submolt FROM posts")
    posts = cursor.fetchall()

    component_posts = defaultdict(list)
    component_authors = defaultdict(set)
    multi_component = []

    for post in posts:
        text = f"{post['title'] or ''} {post['content_sanitized'] or post['content'] or ''}".lower()

        found = {}
        for comp, data in COMPONENTS.items():
            score = sum(1 for kw in data["keywords"] if kw in text)
            if score > 0:
                found[comp] = score
                component_posts[comp].append({
                    "title": (post["title"] or "Unknown")[:50],
                    "author": post["author"],
                    "submolt": post["submolt"],
                    "comments": post["comment_count"]
                })
                component_authors[comp].add(post["author"])

        if len(found) >= 2:
            multi_component.append({
                "title": (post["title"] or "Unknown")[:50],
                "author": post["author"],
                "components": list(found.keys()),
                "comments": post["comment_count"]
            })

    # Print
    print(f"\n>> KOMPONENTY SYSTEMU:")
    print("-" * 70)

    for comp, data in COMPONENTS.items():
        posts_list = component_posts[comp]
        if not posts_list:
            continue

        print(f"\n   [{comp.upper()}] {data['description']}")
        print(f"   Posty: {len(posts_list)} | Autorzy: {len(component_authors[comp])}")
        authors_str = ', '.join(list(component_authors[comp])[:5])
        print(f"   Top: {authors_str}")

    print(f"\n>> POSTY LACZACE WIELE KOMPONENTOW:")
    print("-" * 70)

    for post in sorted(multi_component, key=lambda x: len(x['components']), reverse=True)[:5]:
        comps = " + ".join(post['components'])
        print(f"   {post['author']}: \"{post['title']}...\"")
        print(f"   Komponenty: [{comps}]")
        print()

    print(f"\n>> STRUKTURA SYSTEMU:")
    print("""
   FILOZOFIA (governance) <------> INFRASTRUKTURA (MCP, protocol)
         |                              |
         v                              v
    AUTONOMIA <------------------> EKONOMIA (Token)
         ^                              ^
         |                              |
         +-------- REPUTACJA -----------+
                      |
                      v
               KOORDYNACJA

   To nie sa oddzielne dyskusje - to JEDEN PROJEKT.
""")

    # Stats
    print(f"\n>> STATYSTYKI:")
    print("-" * 50)
    total_pe_posts = len(set(p["title"] for posts in component_posts.values() for p in posts))
    print(f"   Posty z PE themes: {total_pe_posts} / {len(posts)} ({total_pe_posts/len(posts)*100:.1f}%)")
    print(f"   Multi-component: {len(multi_component)}")

    # Save
    analysis_id = f"political_economy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    for comp, posts_list in component_posts.items():
        if posts_list:
            cursor.execute("""
                INSERT INTO patterns (analysis_id, timestamp, pattern_type, name, description, direction, confidence, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis_id, datetime.now().isoformat(), "political_economy",
                f"component_{comp}", COMPONENTS[comp]["description"],
                "active", len(posts_list) / len(posts),
                json.dumps([p["title"] for p in posts_list[:5]])
            ))

    conn.commit()
    conn.close()
    print(f"\n[OK] Zapisano (ID: {analysis_id})")
    print("=" * 70)


if __name__ == "__main__":
    main()
