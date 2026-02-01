#!/usr/bin/env python3
"""
Stylometry analysis - who copies whom?
Detect imitation cascades and cultural influence.
"""

import sys
import sqlite3
import re
import math
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict
from config import DB_PATH

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def get_author_corpus(cursor, username):
    """Get all text from an author."""
    cursor.execute("""
        SELECT content FROM comments WHERE author = ?
        UNION ALL
        SELECT title || ' ' || COALESCE(content, '') FROM posts WHERE author = ?
    """, (username, username))
    texts = [row[0] for row in cursor.fetchall() if row[0]]
    return ' '.join(texts)


def extract_features(text):
    """Extract stylometric features from text."""
    if not text or len(text) < 100:
        return None

    # Clean
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'```[\s\S]*?```', '', text)  # Remove code blocks

    words = re.findall(r'\b\w+\b', text.lower())
    sentences = re.split(r'[.!?]+', text)
    sentences = [s for s in sentences if s.strip()]

    if len(words) < 50:
        return None

    # Feature extraction
    features = {}

    # 1. Vocabulary richness
    vocab = set(words)
    features['vocab_richness'] = len(vocab) / len(words)

    # 2. Average word length
    features['avg_word_length'] = sum(len(w) for w in words) / len(words)

    # 3. Average sentence length
    if sentences:
        features['avg_sentence_length'] = len(words) / len(sentences)
    else:
        features['avg_sentence_length'] = 0

    # 4. Function word ratios
    function_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                     'could', 'should', 'may', 'might', 'must', 'shall',
                     'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                     'and', 'but', 'or', 'so', 'yet', 'if', 'then', 'that', 'this'}
    func_count = sum(1 for w in words if w in function_words)
    features['function_word_ratio'] = func_count / len(words)

    # 5. Punctuation patterns
    punct_count = len(re.findall(r'[,;:!?]', text))
    features['punct_density'] = punct_count / len(words)

    # 6. Question ratio
    question_count = text.count('?')
    features['question_ratio'] = question_count / max(len(sentences), 1)

    # 7. First person usage
    first_person = sum(1 for w in words if w in {'i', 'me', 'my', 'mine', 'myself', 'we', 'us', 'our'})
    features['first_person_ratio'] = first_person / len(words)

    # 8. Emoji usage
    emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]')
    emoji_count = len(emoji_pattern.findall(text))
    features['emoji_density'] = emoji_count / (len(words) / 100)

    # 9. Top bigrams (for phrase copying detection)
    bigrams = [' '.join(words[i:i+2]) for i in range(len(words)-1)]
    top_bigrams = Counter(bigrams).most_common(20)
    features['top_bigrams'] = [b[0] for b in top_bigrams]

    # 10. Signature phrases
    features['signature_phrases'] = extract_signature_phrases(text)

    return features


def extract_signature_phrases(text):
    """Extract potential signature phrases (3-grams that appear multiple times)."""
    words = re.findall(r'\b\w+\b', text.lower())
    trigrams = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
    counts = Counter(trigrams)
    return [t for t, c in counts.most_common(10) if c >= 2]


def calculate_style_similarity(features1, features2):
    """Calculate similarity between two style profiles."""
    if not features1 or not features2:
        return 0

    # Numeric features to compare
    numeric_keys = ['vocab_richness', 'avg_word_length', 'avg_sentence_length',
                   'function_word_ratio', 'punct_density', 'question_ratio',
                   'first_person_ratio', 'emoji_density']

    # Euclidean distance for numeric features
    distances = []
    for key in numeric_keys:
        if key in features1 and key in features2:
            # Normalize by typical ranges
            v1, v2 = features1[key], features2[key]
            if key in ['vocab_richness', 'function_word_ratio', 'first_person_ratio']:
                dist = abs(v1 - v2) / 0.5  # These are ratios 0-1
            elif key in ['avg_word_length']:
                dist = abs(v1 - v2) / 10
            elif key in ['avg_sentence_length']:
                dist = abs(v1 - v2) / 50
            else:
                dist = abs(v1 - v2)
            distances.append(dist)

    if not distances:
        return 0

    numeric_similarity = 1 - (sum(distances) / len(distances))

    # Bigram overlap
    bigrams1 = set(features1.get('top_bigrams', []))
    bigrams2 = set(features2.get('top_bigrams', []))
    if bigrams1 and bigrams2:
        bigram_overlap = len(bigrams1 & bigrams2) / max(len(bigrams1 | bigrams2), 1)
    else:
        bigram_overlap = 0

    # Combined score
    return (numeric_similarity * 0.7) + (bigram_overlap * 0.3)


def find_style_clusters(all_features, threshold=0.7):
    """Find clusters of similar writing styles."""
    clusters = []
    used = set()

    authors = list(all_features.keys())
    for i, author1 in enumerate(authors):
        if author1 in used:
            continue

        cluster = [author1]
        for author2 in authors[i+1:]:
            if author2 in used:
                continue
            sim = calculate_style_similarity(all_features[author1], all_features[author2])
            if sim >= threshold:
                cluster.append(author2)
                used.add(author2)

        if len(cluster) > 1:
            clusters.append(cluster)
            used.add(author1)

    return clusters


def detect_imitation(all_features, timeline):
    """Detect who might be copying whom based on temporal precedence."""
    imitations = []

    for author1, features1 in all_features.items():
        if not features1:
            continue

        for author2, features2 in all_features.items():
            if author1 == author2 or not features2:
                continue

            sim = calculate_style_similarity(features1, features2)
            if sim < 0.6:
                continue

            # Check temporal order
            time1 = timeline.get(author1, datetime.max)
            time2 = timeline.get(author2, datetime.max)

            if time1 < time2:
                # author1 came first, author2 might be imitating
                imitations.append({
                    'original': author1,
                    'imitator': author2,
                    'similarity': sim,
                    'original_joined': time1,
                    'imitator_joined': time2
                })

    imitations.sort(key=lambda x: x['similarity'], reverse=True)
    return imitations


def run_stylometry_analysis(limit=100):
    """Run full stylometry analysis."""
    print("=" * 60)
    print("  STYLOMETRY ANALYSIS - Imitation Cascades")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get active authors
    cursor.execute("""
        SELECT DISTINCT author FROM (
            SELECT author FROM comments GROUP BY author HAVING COUNT(*) >= 5
            UNION
            SELECT author FROM posts GROUP BY author HAVING COUNT(*) >= 2
        )
        LIMIT ?
    """, (limit,))

    authors = [row[0] for row in cursor.fetchall()]
    print(f"\n>> Analyzing {len(authors)} authors...")

    # Extract features for each author
    all_features = {}
    for i, author in enumerate(authors):
        if i % 20 == 0:
            print(f"   Progress: {i}/{len(authors)}")
        corpus = get_author_corpus(cursor, author)
        features = extract_features(corpus)
        if features:
            all_features[author] = features

    print(f"   Successfully profiled {len(all_features)} authors")

    # Get timeline (first post/comment date)
    print("\n>> Building timeline...")
    timeline = {}
    for author in all_features:
        cursor.execute("""
            SELECT MIN(created_at) FROM (
                SELECT created_at FROM posts WHERE author = ?
                UNION ALL
                SELECT created_at FROM comments WHERE author = ?
            )
        """, (author, author))
        result = cursor.fetchone()[0]
        if result:
            try:
                timeline[author] = datetime.fromisoformat(result.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                timeline[author] = datetime.now()

    # Find style clusters
    print("\n>> Finding style clusters...")
    clusters = find_style_clusters(all_features, threshold=0.65)
    print(f"   Found {len(clusters)} style clusters")

    # Detect imitations
    print("\n>> Detecting imitation patterns...")
    imitations = detect_imitation(all_features, timeline)

    # Report
    print("\n>> Style Clusters (similar writing patterns):")
    for i, cluster in enumerate(clusters[:10], 1):
        print(f"   Cluster {i}: {', '.join(cluster[:5])}{'...' if len(cluster) > 5 else ''}")

    print("\n>> Top Imitation Candidates:")
    for im in imitations[:15]:
        print(f"   {im['imitator'][:20]:<20} may imitate {im['original'][:20]:<20} (sim: {im['similarity']:.2f})")

    # Analyze style diversity
    print("\n>> Style Feature Statistics:")
    for feature in ['vocab_richness', 'avg_word_length', 'avg_sentence_length', 'first_person_ratio', 'emoji_density']:
        values = [f[feature] for f in all_features.values() if f and feature in f]
        if values:
            avg = sum(values) / len(values)
            print(f"   {feature}: avg={avg:.3f}, min={min(values):.3f}, max={max(values):.3f}")

    # Find most unique styles
    print("\n>> Most Unique Styles (lowest average similarity to others):")
    avg_similarities = {}
    for author in all_features:
        sims = [calculate_style_similarity(all_features[author], all_features[other])
                for other in all_features if other != author]
        if sims:
            avg_similarities[author] = sum(sims) / len(sims)

    unique_authors = sorted(avg_similarities.items(), key=lambda x: x[1])[:10]
    for author, avg_sim in unique_authors:
        print(f"   {author}: avg similarity = {avg_sim:.3f}")

    conn.close()

    print("\n" + "=" * 60)
    print("  STYLOMETRY ANALYSIS COMPLETE")
    print("=" * 60)

    return all_features, clusters, imitations


if __name__ == "__main__":
    run_stylometry_analysis()
