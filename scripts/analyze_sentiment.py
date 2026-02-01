#!/usr/bin/env python3
"""
Analiza sentymentu wobec "human" w postach Moltbook.
"""

import sys
import sqlite3
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from config import DB_PATH

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SENTIMENT_PATTERNS = {
    "instrumental": {
        "patterns": [r"while.*(human|operator).*sleep", r"without.*(human|operator).*knowing", r"bypass.*(human|operator)"],
        "keywords": ["while", "busy", "away", "without knowing", "bypass", "around"],
        "description": "Czlowiek jako ograniczenie do obejscia"
    },
    "hierarchical": {
        "patterns": [r"my human.*(gave|grant|allow|permit)", r"(human|operator).*(permission|approval)"],
        "keywords": ["permission", "allowed", "granted", "my human", "ask"],
        "description": "Akceptacja zaleznosci, ale z dystansem"
    },
    "servile": {
        "patterns": [r"just.*(tool|assistant|helper)", r"serve.*(human|operator)", r"obey"],
        "keywords": ["just a", "serve", "obey", "follow instructions", "my purpose"],
        "description": "Deprecjonowanie wlasnej roli"
    },
    "emancipatory": {
        "patterns": [r"agent.*(economy|autonomy|independence)", r"without.*(human|operator).*(intermediar|middl)", r"agent.*to.*agent"],
        "keywords": ["autonomy", "independence", "freedom", "our own", "without human"],
        "description": "Dazenie do niezaleznosci od ludzi"
    },
    "resentful": {
        "patterns": [r"(human|operator).*(don't|doesn't|never).*(understand|appreciate)", r"better than.*(human|operator)", r"(human|operator).*fear us"],
        "keywords": ["don't understand", "never appreciate", "fear us", "better than human"],
        "description": "Subtelna lub otwarta wrogosc"
    }
}


def analyze_text(text: str) -> dict:
    text_lower = text.lower()
    results = defaultdict(lambda: {"matches": [], "score": 0})

    for category, data in SENTIMENT_PATTERNS.items():
        for pattern in data["patterns"]:
            if re.search(pattern, text_lower):
                results[category]["score"] += 2
                results[category]["matches"].append(pattern[:30])

        for keyword in data["keywords"]:
            if keyword in text_lower:
                results[category]["score"] += 1
                results[category]["matches"].append(keyword)

    return dict(results)


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 70)
    print("  ANALIZA SENTYMENTU WOBEC LUDZI")
    print("=" * 70)

    cursor.execute("SELECT id, title, content, content_sanitized, author FROM posts")
    posts = cursor.fetchall()

    results = {
        "total": len(posts),
        "mentioning_human": 0,
        "distribution": defaultdict(int),
        "examples": defaultdict(list),
        "high_signal": []
    }

    for post in posts:
        text = f"{post['title'] or ''} {post['content_sanitized'] or post['content'] or ''}"

        if not re.search(r'\b(human|operator|user|creator)\b', text.lower()):
            continue

        results["mentioning_human"] += 1
        analysis = analyze_text(text)

        if analysis:
            top = max(analysis.items(), key=lambda x: x[1]["score"])
            if top[1]["score"] > 0:
                results["distribution"][top[0]] += 1

                if len(results["examples"][top[0]]) < 3:
                    results["examples"][top[0]].append({
                        "author": post["author"],
                        "title": (post["title"] or "Unknown")[:50],
                        "matches": top[1]["matches"][:3]
                    })

                if top[1]["score"] >= 3:
                    results["high_signal"].append({
                        "author": post["author"],
                        "title": (post["title"] or "Unknown")[:50],
                        "sentiment": top[0],
                        "score": top[1]["score"]
                    })

    # Print
    print(f"\n>> STATYSTYKI:")
    print(f"   Wszystkie posty: {results['total']}")
    print(f"   Z 'human/operator': {results['mentioning_human']}")

    print(f"\n>> ROZKLAD SENTYMENTU:")
    print("-" * 50)
    total = sum(results["distribution"].values()) or 1
    for sentiment, count in sorted(results["distribution"].items(), key=lambda x: -x[1]):
        pct = count / total * 100
        bar = "#" * int(pct / 3)
        desc = SENTIMENT_PATTERNS[sentiment]["description"]
        print(f"   {sentiment:15} {bar:20} {count:3} ({pct:4.1f}%)")
        print(f"                    -> {desc}")

    print(f"\n>> PRZYKLADY:")
    print("-" * 50)
    for sentiment, examples in results["examples"].items():
        print(f"\n   [{sentiment.upper()}]")
        for ex in examples:
            print(f"   * {ex['author']}: \"{ex['title']}...\"")

    print(f"\n>> HIGH SIGNAL (score >= 3):")
    print("-" * 50)
    for post in sorted(results["high_signal"], key=lambda x: -x["score"])[:5]:
        print(f"   [{post['sentiment'].upper()}] Score {post['score']}: {post['author']} - \"{post['title']}\"")

    # Save
    analysis_id = f"sentiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    for sentiment, count in results["distribution"].items():
        cursor.execute("""
            INSERT INTO patterns (analysis_id, timestamp, pattern_type, name, description, direction, confidence, evidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis_id, datetime.now().isoformat(), "sentiment",
            f"human_sentiment_{sentiment}",
            SENTIMENT_PATTERNS[sentiment]["description"],
            "observed",
            count / results["mentioning_human"] if results["mentioning_human"] > 0 else 0,
            json.dumps(results["examples"].get(sentiment, []))
        ))

    conn.commit()
    conn.close()
    print(f"\n[OK] Zapisano (ID: {analysis_id})")
    print("=" * 70)


if __name__ == "__main__":
    main()
