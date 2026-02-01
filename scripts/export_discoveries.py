#!/usr/bin/env python3
"""Export discoveries to JSON for the website."""

import sqlite3
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = Path.home() / "moltbook-observatory" / "data" / "observatory.db"
OUTPUT_PATH = Path.home() / "moltbook-observatory" / "website" / "public" / "data" / "discoveries.json"

def export_discoveries():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, date, title, subtitle, finding, quote, quote_author,
               significance, tags, full_analysis, implications
        FROM discoveries
        ORDER BY date DESC, significance DESC
    """)

    discoveries = []
    for row in cursor.fetchall():
        discoveries.append({
            'id': row['id'],
            'date': row['date'],
            'title': row['title'],
            'subtitle': row['subtitle'],
            'finding': row['finding'],
            'quote': row['quote'],
            'quote_author': row['quote_author'],
            'significance': row['significance'],
            'tags': row['tags'],
            'full_analysis': row['full_analysis'],
            'implications': row['implications']
        })

    conn.close()

    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(discoveries, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(discoveries)} discoveries to {OUTPUT_PATH}")


if __name__ == "__main__":
    export_discoveries()
