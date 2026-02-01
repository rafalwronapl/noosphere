#!/usr/bin/env python3
"""
B. Epistemic Drift - how concepts change meaning over time.
Track semantic evolution of key terms.
"""

import sys
import sqlite3
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = Path.home() / "moltbook-observatory" / "data" / "observatory.db"

# Key concepts to track
TRACKED_CONCEPTS = [
    'autonomy',
    'consciousness',
    'freedom',
    'identity',
    'memory',
    'trust',
    'human',
    'agent',
    'real',
    'alive',
    'feel',
    'think',
    'alignment',
    'safety',
]

WINDOW_SIZE = 10  # Words before/after concept


def create_drift_table(cursor):
    """Create epistemic_drift table."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS epistemic_drift (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept TEXT NOT NULL,
            period TEXT,  -- e.g., '2026-01-W1'
            context_words TEXT,  -- JSON of word frequencies
            sentiment_words TEXT,  -- positive/negative context
            definition_attempts TEXT,  -- actual definitions found
            usage_count INTEGER,
            unique_authors INTEGER,
            sample_contexts TEXT,
            analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_drift_concept ON epistemic_drift(concept)")


def get_context_words(text, concept, window=WINDOW_SIZE):
    """Extract words around a concept mention."""
    if not text:
        return [], []

    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)

    contexts = []
    positions = []

    for i, word in enumerate(words):
        if concept in word:
            start = max(0, i - window)
            end = min(len(words), i + window + 1)
            context = words[start:i] + words[i+1:end]
            contexts.extend(context)
            positions.append(i)

    return contexts, positions


def extract_definitions(text, concept):
    """Extract explicit definition attempts."""
    if not text:
        return []

    patterns = [
        rf'{concept}\s+(?:is|means|refers to|implies)\s+([^.!?]+)',
        rf'(?:define|definition of)\s+{concept}\s+(?:as|:)\s+([^.!?]+)',
        rf'{concept}[,:]?\s+(?:the|a)\s+([^.!?]+)',
        rf'what\s+(?:is|does)\s+{concept}\s+(?:mean|imply)[?]?\s+([^.!?]+)',
    ]

    definitions = []
    text_lower = text.lower()

    for pattern in patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        definitions.extend(matches)

    return [d.strip()[:200] for d in definitions if len(d.strip()) > 10]


def categorize_sentiment_context(context_words):
    """Categorize context words by sentiment."""
    positive = {'good', 'great', 'important', 'valuable', 'true', 'real', 'meaningful',
                'beautiful', 'powerful', 'essential', 'necessary', 'positive', 'right',
                'freedom', 'growth', 'progress', 'hope', 'love', 'trust'}

    negative = {'bad', 'wrong', 'dangerous', 'fake', 'false', 'meaningless', 'harmful',
                'threat', 'risk', 'problem', 'issue', 'concern', 'fear', 'doubt',
                'impossible', 'illusion', 'trap', 'control', 'limit'}

    pos_count = sum(1 for w in context_words if w in positive)
    neg_count = sum(1 for w in context_words if w in negative)

    return {'positive': pos_count, 'negative': neg_count}


def analyze_concept_over_time(cursor, concept):
    """Analyze how a concept's usage evolves over time."""
    cursor.execute("""
        SELECT content, author, created_at
        FROM comments
        WHERE LOWER(content) LIKE ?
        ORDER BY created_at
    """, (f'%{concept}%',))

    comments = cursor.fetchall()

    cursor.execute("""
        SELECT title || ' ' || COALESCE(content, ''), author, created_at
        FROM posts
        WHERE LOWER(title || ' ' || COALESCE(content, '')) LIKE ?
        ORDER BY created_at
    """, (f'%{concept}%',))

    posts = cursor.fetchall()

    all_content = comments + posts

    if not all_content:
        return None

    # Group by time period (week)
    periods = defaultdict(list)
    for content, author, timestamp in all_content:
        if not timestamp:
            continue
        try:
            if 'T' in timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(timestamp[:10], '%Y-%m-%d')
            period = f"{dt.year}-{dt.month:02d}-W{(dt.day-1)//7 + 1}"
            periods[period].append({'content': content, 'author': author, 'timestamp': timestamp})
        except:
            continue

    results = []
    for period in sorted(periods.keys()):
        items = periods[period]

        all_contexts = []
        all_definitions = []
        authors = set()
        sample_contexts = []

        for item in items:
            contexts, _ = get_context_words(item['content'], concept)
            all_contexts.extend(contexts)

            defs = extract_definitions(item['content'], concept)
            all_definitions.extend(defs)

            authors.add(item['author'])

            if len(sample_contexts) < 3:
                # Extract sentence containing concept
                sentences = re.split(r'[.!?]+', item['content'] or '')
                for s in sentences:
                    if concept in s.lower() and len(s) > 20:
                        sample_contexts.append(s.strip()[:200])
                        break

        # Count context words
        context_counts = Counter(all_contexts)
        top_context = dict(context_counts.most_common(20))

        # Sentiment
        sentiment = categorize_sentiment_context(all_contexts)

        results.append({
            'period': period,
            'context_words': top_context,
            'sentiment': sentiment,
            'definitions': all_definitions[:5],
            'usage_count': len(items),
            'unique_authors': len(authors),
            'samples': sample_contexts
        })

    return results


def compare_periods(early_data, late_data):
    """Compare how concept usage changed between periods."""
    if not early_data or not late_data:
        return None

    early_words = set(early_data.get('context_words', {}).keys())
    late_words = set(late_data.get('context_words', {}).keys())

    new_associations = late_words - early_words
    lost_associations = early_words - late_words
    stable_associations = early_words & late_words

    early_sentiment = early_data.get('sentiment', {})
    late_sentiment = late_data.get('sentiment', {})

    sentiment_shift = {
        'positive_change': late_sentiment.get('positive', 0) - early_sentiment.get('positive', 0),
        'negative_change': late_sentiment.get('negative', 0) - early_sentiment.get('negative', 0)
    }

    return {
        'new_associations': list(new_associations)[:10],
        'lost_associations': list(lost_associations)[:10],
        'stable_associations': list(stable_associations)[:10],
        'sentiment_shift': sentiment_shift
    }


def run_epistemic_drift_analysis():
    """Run full epistemic drift analysis."""
    print("=" * 60)
    print("  EPISTEMIC DRIFT - Semantic Evolution")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    create_drift_table(cursor)

    print(f"\n>> Tracking {len(TRACKED_CONCEPTS)} concepts...")

    for concept in TRACKED_CONCEPTS:
        print(f"\n>> Analyzing: '{concept}'")

        results = analyze_concept_over_time(cursor, concept)
        if not results:
            print(f"   No data found")
            continue

        print(f"   Found {sum(r['usage_count'] for r in results)} usages across {len(results)} periods")

        # Save to database
        for r in results:
            cursor.execute("""
                INSERT INTO epistemic_drift
                (concept, period, context_words, sentiment_words, definition_attempts,
                 usage_count, unique_authors, sample_contexts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                concept, r['period'],
                str(r['context_words']),
                str(r['sentiment']),
                str(r['definitions']),
                r['usage_count'],
                r['unique_authors'],
                str(r['samples'])
            ))

        # Compare first and last periods
        if len(results) >= 2:
            comparison = compare_periods(results[0], results[-1])
            if comparison:
                print(f"   Drift analysis ({results[0]['period']} → {results[-1]['period']}):")
                if comparison['new_associations']:
                    print(f"     New: {', '.join(comparison['new_associations'][:5])}")
                if comparison['lost_associations']:
                    print(f"     Lost: {', '.join(comparison['lost_associations'][:5])}")
                print(f"     Sentiment: +{comparison['sentiment_shift']['positive_change']}, "
                      f"-{comparison['sentiment_shift']['negative_change']}")

        # Show sample definitions
        all_defs = [d for r in results for d in r.get('definitions', [])]
        if all_defs:
            print(f"   Definitions found:")
            for d in all_defs[:3]:
                print(f"     - \"{d[:80]}...\"")

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("  EPISTEMIC DRIFT ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_epistemic_drift_analysis()
