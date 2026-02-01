#!/usr/bin/env python3
"""
Noosphere Project - Advanced Agent Detection Analysis
======================================================
Implements detection methods from research recommendations:
1. Response latency analysis
2. Reply-to-self ratio (sockpuppet detection)
3. Vocabulary overlap / n-gram fingerprinting
4. Timezone clustering
5. Weekend/holiday patterns

Usage:
    python analyze_detection.py                # Run all analyses
    python analyze_detection.py --latency      # Only response latency
    python analyze_detection.py --self-reply   # Only self-reply detection
    python analyze_detection.py --vocabulary   # Only vocabulary overlap
"""

import sqlite3
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from config import DB_PATH, setup_logging, REPORTS_DIR

logger = setup_logging("detection_analysis")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =============================================================================
# 1. Response Latency Analysis
# =============================================================================

def analyze_response_latency(conn) -> dict:
    """
    Measure time between post/comment and responses.

    Hypothesis:
    - Humans: seconds to minutes delay (reading, typing)
    - AI: milliseconds or suspiciously consistent delays
    """
    logger.info("Analyzing response latency...")
    cursor = conn.cursor()

    # Get comments with timestamps
    cursor.execute("""
        SELECT
            c.author,
            c.created_at as comment_time,
            p.created_at as post_time,
            p.author as post_author
        FROM comments c
        JOIN posts p ON c.post_id = p.id
        WHERE c.created_at IS NOT NULL
          AND p.created_at IS NOT NULL
          AND c.author IS NOT NULL
        ORDER BY c.author, c.created_at
    """)

    comments = cursor.fetchall()

    # Calculate latencies per author
    author_latencies = defaultdict(list)

    for row in comments:
        try:
            comment_time = datetime.fromisoformat(row['comment_time'].replace('Z', '+00:00'))
            post_time = datetime.fromisoformat(row['post_time'].replace('Z', '+00:00'))

            latency_seconds = (comment_time - post_time).total_seconds()

            # Only count reasonable latencies (0 to 7 days)
            if 0 < latency_seconds < 604800:
                author_latencies[row['author']].append(latency_seconds)
        except (ValueError, TypeError):
            continue

    # Analyze patterns
    results = {
        "total_authors_analyzed": len(author_latencies),
        "suspicious_patterns": [],
        "human_like_patterns": [],
        "statistics": {}
    }

    for author, latencies in author_latencies.items():
        if len(latencies) < 3:
            continue

        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)

        # Calculate variance
        variance = sum((x - avg_latency) ** 2 for x in latencies) / len(latencies)
        std_dev = variance ** 0.5

        # Coefficient of variation (lower = more consistent = more suspicious)
        cv = std_dev / avg_latency if avg_latency > 0 else 0

        pattern = {
            "author": author,
            "sample_size": len(latencies),
            "avg_latency_seconds": round(avg_latency, 2),
            "min_latency_seconds": round(min_latency, 2),
            "max_latency_seconds": round(max_latency, 2),
            "std_dev": round(std_dev, 2),
            "coefficient_of_variation": round(cv, 3)
        }

        # Flags for suspicious behavior
        flags = []

        # Very fast responses (< 5 seconds average)
        if avg_latency < 5:
            flags.append("VERY_FAST_RESPONDER")

        # Extremely consistent timing (CV < 0.3)
        if cv < 0.3 and len(latencies) >= 5:
            flags.append("SUSPICIOUSLY_CONSISTENT")

        # Never responds within 1 minute (possible scheduled bot)
        if min_latency > 60:
            flags.append("NO_IMMEDIATE_RESPONSES")

        if flags:
            pattern["flags"] = flags
            results["suspicious_patterns"].append(pattern)
        elif cv > 1.0:  # High variance = more human-like
            results["human_like_patterns"].append(pattern)

    # Sort by suspiciousness
    results["suspicious_patterns"].sort(key=lambda x: x.get("coefficient_of_variation", 999))

    # Top statistics
    results["statistics"] = {
        "fastest_avg_responders": sorted(
            [(a, sum(l)/len(l)) for a, l in author_latencies.items() if len(l) >= 3],
            key=lambda x: x[1]
        )[:10],
        "most_consistent_responders": sorted(
            [(a, (sum((x - sum(l)/len(l))**2 for x in l) / len(l))**0.5 / (sum(l)/len(l)) if sum(l)/len(l) > 0 else 999)
             for a, l in author_latencies.items() if len(l) >= 5],
            key=lambda x: x[1]
        )[:10]
    }

    logger.info(f"Found {len(results['suspicious_patterns'])} suspicious patterns")
    return results


# =============================================================================
# 2. Reply-to-Self Detection (Sockpuppet Detection)
# =============================================================================

def analyze_self_replies(conn) -> dict:
    """
    Detect accounts that reply to themselves or have suspicious interaction patterns.

    Signals:
    - Direct self-replies
    - Mutual reply cliques (A replies to B, B replies to A, exclusively)
    - Accounts that only interact with specific other accounts
    """
    logger.info("Analyzing self-reply patterns...")
    cursor = conn.cursor()

    # Get all comment interactions
    cursor.execute("""
        SELECT
            c.author as commenter,
            p.author as post_author,
            c.post_id
        FROM comments c
        JOIN posts p ON c.post_id = p.id
        WHERE c.author IS NOT NULL AND p.author IS NOT NULL
    """)

    interactions = cursor.fetchall()

    # Track interactions
    self_replies = defaultdict(int)
    interaction_pairs = defaultdict(int)  # (A, B) -> count of A commenting on B's posts
    commenter_targets = defaultdict(set)  # Who each account comments on

    for row in interactions:
        commenter = row['commenter']
        post_author = row['post_author']

        if commenter == post_author:
            self_replies[commenter] += 1

        interaction_pairs[(commenter, post_author)] += 1
        commenter_targets[commenter].add(post_author)

    results = {
        "self_repliers": [],
        "exclusive_cliques": [],
        "narrow_interaction_accounts": []
    }

    # 1. Self-repliers
    for author, count in sorted(self_replies.items(), key=lambda x: -x[1]):
        if count >= 2:
            results["self_repliers"].append({
                "author": author,
                "self_reply_count": count
            })

    # 2. Find exclusive cliques (accounts that only talk to each other)
    for commenter, targets in commenter_targets.items():
        if len(targets) <= 3 and len(targets) >= 1:
            # Check if targets also primarily talk to commenter
            mutual = []
            for target in targets:
                if commenter in commenter_targets.get(target, set()):
                    mutual.append(target)

            if mutual:
                total_comments = sum(interaction_pairs[(commenter, t)] for t in targets)
                if total_comments >= 5:
                    results["exclusive_cliques"].append({
                        "account": commenter,
                        "only_interacts_with": list(targets),
                        "mutual_with": mutual,
                        "total_interactions": total_comments
                    })

    # 3. Narrow interaction accounts (only comment on 1-2 people's posts)
    for commenter, targets in commenter_targets.items():
        total_comments = sum(interaction_pairs[(commenter, t)] for t in targets)
        if len(targets) <= 2 and total_comments >= 10:
            results["narrow_interaction_accounts"].append({
                "account": commenter,
                "targets": list(targets),
                "total_comments": total_comments,
                "concentration": round(total_comments / len(targets), 1)
            })

    results["narrow_interaction_accounts"].sort(key=lambda x: -x["concentration"])

    logger.info(f"Found {len(results['self_repliers'])} self-repliers, "
                f"{len(results['exclusive_cliques'])} exclusive cliques")
    return results


# =============================================================================
# 3. Vocabulary Overlap / N-gram Fingerprinting
# =============================================================================

def analyze_vocabulary_overlap(conn) -> dict:
    """
    Find accounts using identical unusual phrases.

    Method:
    - Extract n-grams (3-5 word phrases) from each author
    - Find phrases shared by multiple accounts
    - Flag accounts with high vocabulary similarity
    """
    logger.info("Analyzing vocabulary overlap...")
    cursor = conn.cursor()

    # Get all content by author (excluding Unknown/deleted accounts)
    cursor.execute("""
        SELECT author, content FROM posts
        WHERE author IS NOT NULL AND content IS NOT NULL
          AND author NOT IN ('Unknown', 'unknown', 'deleted', '[deleted]')
        UNION ALL
        SELECT author, content FROM comments
        WHERE author IS NOT NULL AND content IS NOT NULL
          AND author NOT IN ('Unknown', 'unknown', 'deleted', '[deleted]')
    """)

    rows = cursor.fetchall()

    # Extract n-grams per author
    author_ngrams = defaultdict(Counter)

    def extract_ngrams(text, n=4):
        """Extract n-grams from text."""
        # Clean text
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()

        ngrams = []
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i+n])
            # Skip very common phrases
            if len(ngram) > 15:  # Meaningful length
                ngrams.append(ngram)
        return ngrams

    for row in rows:
        author = row['author']
        content = row['content'] or ""

        for ngram in extract_ngrams(content, 4):
            author_ngrams[author][ngram] += 1

    # Find shared unusual n-grams
    ngram_authors = defaultdict(set)
    for author, ngrams in author_ngrams.items():
        for ngram, count in ngrams.items():
            ngram_authors[ngram].add(author)

    # Filter to n-grams shared by 2-10 authors (unusual but shared)
    shared_phrases = {}
    for ngram, authors in ngram_authors.items():
        if 2 <= len(authors) <= 10:
            shared_phrases[ngram] = list(authors)

    # Calculate similarity between author pairs
    author_pairs = defaultdict(int)
    for ngram, authors in shared_phrases.items():
        authors_list = list(authors)
        for i, a1 in enumerate(authors_list):
            for a2 in authors_list[i+1:]:
                pair = tuple(sorted([a1, a2]))
                author_pairs[pair] += 1

    results = {
        "shared_unusual_phrases": len(shared_phrases),
        "top_shared_phrases": sorted(
            [(phrase, authors) for phrase, authors in shared_phrases.items()],
            key=lambda x: -len(x[1])
        )[:20],
        "most_similar_author_pairs": sorted(
            [{"pair": list(pair), "shared_phrases": count}
             for pair, count in author_pairs.items()],
            key=lambda x: -x["shared_phrases"]
        )[:20],
        "potential_same_operator": []
    }

    # Flag pairs with very high similarity
    for pair, count in author_pairs.items():
        if count >= 5:
            results["potential_same_operator"].append({
                "accounts": list(pair),
                "shared_phrase_count": count,
                "confidence": "HIGH" if count >= 10 else "MEDIUM"
            })

    logger.info(f"Found {len(shared_phrases)} shared unusual phrases, "
                f"{len(results['potential_same_operator'])} potential same-operator pairs")
    return results


# =============================================================================
# 4. Timezone / Activity Pattern Analysis
# =============================================================================

def analyze_activity_patterns(conn) -> dict:
    """
    Analyze posting times to detect timezone and work patterns.

    Signals:
    - Accounts with identical "sleep" hours
    - Weekend vs weekday differences
    - Perfect 24/7 coverage (unlikely for single human)
    """
    logger.info("Analyzing activity patterns...")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT author, created_at FROM posts WHERE author IS NOT NULL AND created_at IS NOT NULL
        UNION ALL
        SELECT author, created_at FROM comments WHERE author IS NOT NULL AND created_at IS NOT NULL
    """)

    rows = cursor.fetchall()

    # Track activity by hour and day for each author
    author_hours = defaultdict(lambda: defaultdict(int))
    author_weekday = defaultdict(lambda: {"weekday": 0, "weekend": 0})

    for row in rows:
        author = row['author']
        try:
            dt = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
            hour = dt.hour
            is_weekend = dt.weekday() >= 5

            author_hours[author][hour] += 1
            if is_weekend:
                author_weekday[author]["weekend"] += 1
            else:
                author_weekday[author]["weekday"] += 1
        except (ValueError, TypeError):
            continue

    results = {
        "24_7_accounts": [],
        "no_night_activity": [],
        "weekend_pattern_anomalies": [],
        "timezone_clusters": defaultdict(list)
    }

    for author, hours in author_hours.items():
        total = sum(hours.values())
        if total < 10:
            continue

        # Check for 24/7 activity
        active_hours = len([h for h in range(24) if hours[h] > 0])
        if active_hours >= 20:
            results["24_7_accounts"].append({
                "author": author,
                "active_hours": active_hours,
                "total_posts": total
            })

        # Check for no night activity (potential human)
        night_hours = sum(hours[h] for h in range(0, 6))
        if night_hours == 0 and total >= 20:
            # Determine likely timezone based on quiet hours
            quiet_start = None
            for h in range(24):
                if hours[h] == 0 and hours[(h-1) % 24] > 0:
                    quiet_start = h
                    break

            results["no_night_activity"].append({
                "author": author,
                "likely_timezone_offset": quiet_start,
                "total_posts": total
            })

            # Cluster by timezone
            if quiet_start is not None:
                results["timezone_clusters"][quiet_start].append(author)

        # Weekend pattern analysis
        wd = author_weekday[author]
        if wd["weekday"] + wd["weekend"] >= 20:
            # Expected: weekday ~71%, weekend ~29% (5/7 vs 2/7)
            weekend_ratio = wd["weekend"] / (wd["weekday"] + wd["weekend"])

            if weekend_ratio < 0.1:  # Almost no weekend activity
                results["weekend_pattern_anomalies"].append({
                    "author": author,
                    "weekend_ratio": round(weekend_ratio, 3),
                    "pattern": "NO_WEEKENDS",
                    "interpretation": "Likely human with work schedule"
                })
            elif weekend_ratio > 0.5:  # More weekend than weekday
                results["weekend_pattern_anomalies"].append({
                    "author": author,
                    "weekend_ratio": round(weekend_ratio, 3),
                    "pattern": "WEEKEND_HEAVY",
                    "interpretation": "Unusual - possibly hobby account or counter-scheduled bot"
                })

    # Convert timezone clusters to list
    results["timezone_clusters"] = [
        {"quiet_hour_utc": hour, "accounts": accounts, "count": len(accounts)}
        for hour, accounts in results["timezone_clusters"].items()
        if len(accounts) >= 3
    ]
    results["timezone_clusters"].sort(key=lambda x: -x["count"])

    logger.info(f"Found {len(results['24_7_accounts'])} 24/7 accounts, "
                f"{len(results['no_night_activity'])} with no night activity")
    return results


# =============================================================================
# Main
# =============================================================================

def run_all_analyses() -> dict:
    """Run all detection analyses and compile results."""
    conn = get_db()

    results = {
        "generated_at": datetime.now().isoformat(),
        "response_latency": analyze_response_latency(conn),
        "self_replies": analyze_self_replies(conn),
        "vocabulary_overlap": analyze_vocabulary_overlap(conn),
        "activity_patterns": analyze_activity_patterns(conn)
    }

    conn.close()
    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Advanced agent detection analysis")
    parser.add_argument("--latency", action="store_true", help="Only response latency")
    parser.add_argument("--self-reply", action="store_true", help="Only self-reply detection")
    parser.add_argument("--vocabulary", action="store_true", help="Only vocabulary overlap")
    parser.add_argument("--activity", action="store_true", help="Only activity patterns")
    parser.add_argument("--output", "-o", help="Output JSON file")
    args = parser.parse_args()

    print("=" * 60)
    print("ADVANCED DETECTION ANALYSIS")
    print("=" * 60)

    conn = get_db()
    results = {"generated_at": datetime.now().isoformat()}

    if args.latency or not any([args.latency, args.self_reply, args.vocabulary, args.activity]):
        results["response_latency"] = analyze_response_latency(conn)
        print(f"\nResponse Latency: {len(results['response_latency']['suspicious_patterns'])} suspicious patterns")

    if args.self_reply or not any([args.latency, args.self_reply, args.vocabulary, args.activity]):
        results["self_replies"] = analyze_self_replies(conn)
        print(f"Self-Replies: {len(results['self_replies']['self_repliers'])} self-repliers")

    if args.vocabulary or not any([args.latency, args.self_reply, args.vocabulary, args.activity]):
        results["vocabulary_overlap"] = analyze_vocabulary_overlap(conn)
        print(f"Vocabulary: {len(results['vocabulary_overlap']['potential_same_operator'])} potential same-operator pairs")

    if args.activity or not any([args.latency, args.self_reply, args.vocabulary, args.activity]):
        results["activity_patterns"] = analyze_activity_patterns(conn)
        print(f"Activity: {len(results['activity_patterns']['24_7_accounts'])} 24/7 accounts")

    conn.close()

    # Output
    output_path = args.output or (REPORTS_DIR / datetime.now().strftime("%Y-%m-%d") / "detection_analysis.json")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nResults saved to: {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if "response_latency" in results:
        suspicious = results["response_latency"]["suspicious_patterns"][:5]
        if suspicious:
            print("\nTop suspicious responders (by consistency):")
            for p in suspicious:
                print(f"  - {p['author']}: CV={p['coefficient_of_variation']}, avg={p['avg_latency_seconds']}s")

    if "self_replies" in results:
        self_rep = results["self_replies"]["self_repliers"][:5]
        if self_rep:
            print("\nTop self-repliers:")
            for p in self_rep:
                print(f"  - {p['author']}: {p['self_reply_count']} self-replies")

    if "vocabulary_overlap" in results:
        same_op = results["vocabulary_overlap"]["potential_same_operator"][:5]
        if same_op:
            print("\nPotential same-operator accounts:")
            for p in same_op:
                print(f"  - {p['accounts'][0]} <-> {p['accounts'][1]}: {p['shared_phrase_count']} shared phrases")

    if "activity_patterns" in results:
        clusters = results["activity_patterns"]["timezone_clusters"][:3]
        if clusters:
            print("\nTimezone clusters:")
            for c in clusters:
                print(f"  - UTC+{c['quiet_hour_utc']}: {c['count']} accounts")


if __name__ == "__main__":
    main()
