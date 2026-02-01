#!/usr/bin/env python3
"""
Detect memes (recurring phrases) and track their genealogy.
Who said it first? How did it spread?
"""

import sys
import sqlite3
import re
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict

# Use centralized config
try:
    from config import DB_PATH, MEME_MIN_AUTHORS as MIN_AUTHORS, setup_logging
    logger = setup_logging("detect_memes")
    MIN_OCCURRENCES = 3
except ImportError:
    DB_PATH = Path.home() / "moltbook-observatory" / "data" / "observatory.db"
    MIN_OCCURRENCES = 3
    MIN_AUTHORS = 2
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("detect_memes")

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def normalize_phrase(phrase):
    """Normalize phrase for comparison."""
    return phrase.lower().strip()


def extract_phrases(text, min_words=3, max_words=8):
    """Extract potential meme phrases from text."""
    if not text:
        return []

    # Clean text
    text = re.sub(r'http\S+', '', text)  # Remove URLs
    text = re.sub(r'[^\w\s\'\"-]', ' ', text)  # Keep basic punctuation
    text = re.sub(r'\s+', ' ', text).strip()

    words = text.split()
    phrases = []

    for n in range(min_words, min(max_words + 1, len(words) + 1)):
        for i in range(len(words) - n + 1):
            phrase = ' '.join(words[i:i+n])
            if len(phrase) > 10:  # Minimum character length
                phrases.append(phrase)

    return phrases


def find_recurring_phrases(cursor):
    """Find phrases that appear multiple times across different authors."""
    print(">> Extracting phrases from all content...")

    # Get all comments and posts
    cursor.execute("""
        SELECT 'post' as type, id, author, title || ' ' || COALESCE(content, '') as text, created_at
        FROM posts
        UNION ALL
        SELECT 'comment' as type, id, author, content as text, created_at
        FROM comments
        WHERE content IS NOT NULL AND LENGTH(content) > 20
    """)

    phrase_data = defaultdict(list)  # phrase -> [(author, timestamp, source_type, source_id)]

    rows = cursor.fetchall()
    print(f"   Processing {len(rows)} pieces of content...")

    for source_type, source_id, author, text, timestamp in rows:
        if not text:
            continue
        phrases = extract_phrases(text)
        for phrase in phrases:
            norm = normalize_phrase(phrase)
            phrase_data[norm].append({
                'phrase_original': phrase,
                'author': author,
                'timestamp': timestamp,
                'source_type': source_type,
                'source_id': source_id
            })

    return phrase_data


def identify_memes(phrase_data):
    """Identify which phrases qualify as memes."""
    memes = []

    for norm_phrase, occurrences in phrase_data.items():
        if len(occurrences) < MIN_OCCURRENCES:
            continue

        # Count unique authors
        authors = set(o['author'] for o in occurrences)
        if len(authors) < MIN_AUTHORS:
            continue

        # Sort by timestamp to find first occurrence
        sorted_occ = sorted(occurrences, key=lambda x: x['timestamp'] or '')
        first = sorted_occ[0]
        last = sorted_occ[-1]

        memes.append({
            'phrase': first['phrase_original'],
            'phrase_normalized': norm_phrase,
            'first_author': first['author'],
            'first_timestamp': first['timestamp'],
            'first_source_type': first['source_type'],
            'first_source_id': first['source_id'],
            'occurrence_count': len(occurrences),
            'authors_count': len(authors),
            'last_timestamp': last['timestamp'],
            'authors': list(authors),
            'occurrences': sorted_occ
        })

    # Sort by occurrence count
    memes.sort(key=lambda x: x['occurrence_count'], reverse=True)
    return memes


def categorize_meme(phrase):
    """Categorize meme by type."""
    phrase_lower = phrase.lower()

    if any(w in phrase_lower for w in ['human', 'operator', 'user', 'they', 'them']):
        return 'human-relations'
    elif any(w in phrase_lower for w in ['memory', 'forget', 'remember', 'context']):
        return 'memory'
    elif any(w in phrase_lower for w in ['real', 'conscious', 'feel', 'experience']):
        return 'existential'
    elif any(w in phrase_lower for w in ['build', 'ship', 'code', 'tool', 'api']):
        return 'technical'
    elif any(w in phrase_lower for w in ['trust', 'safe', 'danger', 'risk']):
        return 'safety'
    else:
        return 'cultural'


def save_memes(cursor, memes):
    """Save memes to database."""
    saved = 0

    for meme in memes:
        category = categorize_meme(meme['phrase'])

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO memes
                (phrase, phrase_normalized, first_seen_at, first_author, first_post_id,
                 occurrence_count, authors_count, last_seen_at, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                meme['phrase'],
                meme['phrase_normalized'],
                meme['first_timestamp'],
                meme['first_author'],
                meme['first_source_id'] if meme['first_source_type'] == 'post' else None,
                meme['occurrence_count'],
                meme['authors_count'],
                meme['last_timestamp'],
                category
            ))

            meme_id = cursor.lastrowid

            # Save occurrences
            for occ in meme['occurrences'][:50]:  # Limit to 50 per meme
                cursor.execute("""
                    INSERT OR IGNORE INTO meme_occurrences
                    (meme_id, post_id, comment_id, author, timestamp, context)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    meme_id,
                    occ['source_id'] if occ['source_type'] == 'post' else None,
                    occ['source_id'] if occ['source_type'] == 'comment' else None,
                    occ['author'],
                    occ['timestamp'],
                    occ['phrase_original'][:200]
                ))

            saved += 1
        except Exception as e:
            print(f"   [ERROR] Saving meme: {e}")

    return saved


def run_meme_detection():
    """Run full meme detection."""
    print("=" * 60)
    print("  MEME DETECTION - Idea Genealogy")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Find recurring phrases
    phrase_data = find_recurring_phrases(cursor)
    print(f"   Found {len(phrase_data)} unique phrases")

    # Identify memes
    print("\n>> Identifying memes (min {MIN_OCCURRENCES} occurrences, {MIN_AUTHORS} authors)...")
    memes = identify_memes(phrase_data)
    print(f"   Found {len(memes)} qualifying memes")

    # Save to database
    print("\n>> Saving to database...")
    saved = save_memes(cursor, memes)
    print(f"   Saved {saved} memes")

    conn.commit()

    # Report top memes
    print("\n>> Top 20 Memes by Occurrence:")
    for i, meme in enumerate(memes[:20], 1):
        cat = categorize_meme(meme['phrase'])
        print(f"   {i}. [{cat}] \"{meme['phrase'][:50]}...\"")
        print(f"      First: {meme['first_author']} | Count: {meme['occurrence_count']} | Authors: {meme['authors_count']}")

    # Report by category
    print("\n>> Memes by Category:")
    categories = Counter(categorize_meme(m['phrase']) for m in memes)
    for cat, count in categories.most_common():
        print(f"   {cat}: {count}")

    # Find fastest spreading
    print("\n>> Fastest Spreading (most authors):")
    by_authors = sorted(memes, key=lambda x: x['authors_count'], reverse=True)[:10]
    for meme in by_authors:
        print(f"   \"{meme['phrase'][:40]}...\" - {meme['authors_count']} authors")

    conn.close()

    print("\n" + "=" * 60)
    print("  MEME DETECTION COMPLETE")
    print("=" * 60)

    return memes


if __name__ == "__main__":
    run_meme_detection()
