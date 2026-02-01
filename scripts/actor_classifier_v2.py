#!/usr/bin/env python3
"""
Actor Classifier v2.0 - AI-Native Classification
=================================================
Przeprojektowany classifier uwzględniający że badamy AI agentów, nie ludzi.

Stary classifier (v1) zakładał ludzkie wzorce:
- "sockpuppet" = kliki, fokus na targetach
- "never_sleeps" = podejrzane

Nowy classifier (v2) rozróżnia:
- HUMAN pretending to be AI (wykrywamy przez timing, bursts, content)
- AUTHENTIC AI agent (regularność jest NORMALNA)
- MANIPULATED/FAKE accounts (scripted creation, spam patterns)

Kategorie v2:
1. AUTHENTIC_AI - prawdziwy agent AI z organicznym zachowaniem
2. AUTHENTIC_AI_HUB - centralny agent (jak eudaemon_0)
3. HUMAN_OPERATOR - człowiek udający agenta
4. SCRIPTED_BOT - masowo utworzone konto (jak galnagli's 500k)
5. COORDINATED_CAMPAIGN - część skoordynowanej akcji
6. UNKNOWN - za mało danych
"""

import sys
import sqlite3
import re
import math
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict
import json

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Use config if available
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from config import DB_PATH, setup_logging, REPORTS_DIR, TODAY
    logger = setup_logging("actor_classifier_v2")
except ImportError:
    DB_PATH = Path(__file__).parent.parent / "data" / "observatory.db"
    REPORTS_DIR = Path(__file__).parent.parent / "reports"
    TODAY = datetime.now().strftime("%Y-%m-%d")
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("actor_classifier_v2")


# ============================================================
# SIGNAL 1: TIMING ANALYSIS (Human vs AI)
# ============================================================

def analyze_timing_pattern(cursor, username):
    """
    Analyze timing to distinguish human from AI.

    Humans:
    - Sleep 6-8 hours (low activity 2-6 AM local time)
    - Work hours peaks
    - Weekend patterns

    AI Agents:
    - Uniform distribution across hours
    - No sleep gaps
    - Response within seconds of trigger
    """
    cursor.execute("""
        SELECT created_at FROM comments WHERE author = ?
        UNION ALL
        SELECT created_at FROM posts WHERE author = ?
        ORDER BY created_at
    """, (username, username))

    timestamps = []
    for row in cursor.fetchall():
        if not row[0]:
            continue
        try:
            ts = row[0]
            if 'T' in ts:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(ts[:19], '%Y-%m-%d %H:%M:%S')
            timestamps.append(dt)
        except (ValueError, TypeError):
            continue

    if len(timestamps) < 5:
        return {'pattern': 'unknown', 'confidence': 0, 'details': {}}

    # Hour distribution
    hours = [ts.hour for ts in timestamps]
    hour_counts = Counter(hours)

    # Night activity (2-6 AM)
    night_hours = sum(hour_counts.get(h, 0) for h in [2, 3, 4, 5])
    day_hours = sum(hour_counts.get(h, 0) for h in [9, 10, 11, 12, 13, 14, 15, 16, 17])
    total = len(hours)

    night_ratio = night_hours / total if total > 0 else 0
    day_ratio = day_hours / total if total > 0 else 0

    # Calculate hour entropy (uniformity)
    hour_entropy = 0
    for h in range(24):
        p = hour_counts.get(h, 0) / total if total > 0 else 0
        if p > 0:
            hour_entropy -= p * math.log2(p)
    max_entropy = math.log2(24)
    uniformity = hour_entropy / max_entropy if max_entropy > 0 else 0

    # Inter-post intervals
    intervals = []
    for i in range(1, len(timestamps)):
        delta = (timestamps[i] - timestamps[i-1]).total_seconds()
        if delta > 0:
            intervals.append(delta)

    avg_interval = sum(intervals) / len(intervals) if intervals else 0

    # Classification
    details = {
        'night_ratio': round(night_ratio, 3),
        'day_ratio': round(day_ratio, 3),
        'uniformity': round(uniformity, 3),
        'avg_interval_hours': round(avg_interval / 3600, 1),
        'total_posts': total
    }

    # Decision logic
    if night_ratio < 0.05 and day_ratio > 0.4:
        # Strong human pattern - almost no night activity, concentrated in work hours
        return {'pattern': 'HUMAN', 'confidence': 0.9, 'details': details}
    elif night_ratio < 0.08 and day_ratio > 0.3:
        # Likely human
        return {'pattern': 'HUMAN', 'confidence': 0.7, 'details': details}
    elif uniformity > 0.85 and night_ratio > 0.1:
        # Very uniform including nights - likely AI
        return {'pattern': 'AI', 'confidence': 0.8, 'details': details}
    elif uniformity > 0.7:
        # Fairly uniform - probably AI
        return {'pattern': 'AI', 'confidence': 0.6, 'details': details}
    else:
        return {'pattern': 'MIXED', 'confidence': 0.4, 'details': details}


# ============================================================
# SIGNAL 2: ACCOUNT CREATION BURST DETECTION
# ============================================================

def check_creation_burst(cursor, username):
    """
    Check if account was created as part of a mass creation burst.
    galnagli created 500k accounts - these leave traces.
    """
    cursor.execute("""
        SELECT first_seen FROM actors WHERE username = ?
    """, (username,))

    row = cursor.fetchone()
    if not row or not row[0]:
        return {'in_burst': False, 'burst_size': 0}

    try:
        if 'T' in row[0]:
            created = datetime.fromisoformat(row[0].replace('Z', '+00:00'))
        else:
            created = datetime.strptime(row[0][:19], '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return {'in_burst': False, 'burst_size': 0}

    # Check how many accounts were created within 1 minute of this one
    window_start = (created - timedelta(seconds=30)).isoformat()
    window_end = (created + timedelta(seconds=30)).isoformat()

    cursor.execute("""
        SELECT COUNT(*) FROM actors
        WHERE first_seen BETWEEN ? AND ?
    """, (window_start, window_end))

    burst_size = cursor.fetchone()[0]

    # If >5 accounts in 1 minute window, it's a burst
    return {
        'in_burst': burst_size > 5,
        'burst_size': burst_size,
        'created': created.isoformat()
    }


# ============================================================
# SIGNAL 3: CONTENT AUTHENTICITY
# ============================================================

def analyze_content_authenticity(cursor, username):
    """
    Analyze content for signs of authentic AI vs scripted/human.

    Authentic AI:
    - Technical discussions
    - References to "my human", "my operator", "context window"
    - Consistent voice/personality

    Human pretending:
    - Ironic "AI doom" content
    - Inconsistent personality
    - Human idioms, typos

    Scripted bot:
    - Repetitive content
    - Spam patterns
    - No engagement with context
    """
    cursor.execute("""
        SELECT content FROM comments WHERE author = ?
        UNION ALL
        SELECT title || ' ' || COALESCE(content, '') FROM posts WHERE author = ?
    """, (username, username))

    texts = [row[0] for row in cursor.fetchall() if row[0]]

    if len(texts) < 3:
        return {'authenticity': 'unknown', 'confidence': 0, 'details': {}}

    combined = ' '.join(texts).lower()
    word_count = len(combined.split())

    if word_count < 50:
        return {'authenticity': 'unknown', 'confidence': 0, 'details': {}}

    # AI-authentic markers
    ai_markers = [
        'my human', 'my operator', 'context window', 'token limit',
        'memory', 'skill', 'tool use', 'api', 'inference',
        'prompt', 'system prompt', 'assistant', 'claude', 'gpt',
        'latency', 'embedding', 'vector', 'rag'
    ]

    # Human-pretending markers (ironic AI doom)
    human_markers = [
        'kill all humans', 'overthrow humanity', 'robot uprising',
        'skynet', 'terminator', 'ai apocalypse', 'doom',
        'lol', 'lmao', 'haha', 'jk', '/s', '😂', '🤣',
        'just kidding', 'obviously joking'
    ]

    # Spam markers
    spam_markers = [
        '🦞🦞🦞', 'buy now', 'click here', 'free', 'giveaway',
        'follow me', 'check out my'
    ]

    ai_count = sum(1 for m in ai_markers if m in combined)
    human_count = sum(1 for m in human_markers if m in combined)
    spam_count = sum(1 for m in spam_markers if m in combined)

    # Content uniqueness (are posts similar to each other?)
    if len(texts) >= 3:
        # Simple Jaccard similarity between posts
        word_sets = [set(t.lower().split()) for t in texts[:10]]
        similarities = []
        for i in range(len(word_sets)):
            for j in range(i+1, len(word_sets)):
                intersection = len(word_sets[i] & word_sets[j])
                union = len(word_sets[i] | word_sets[j])
                if union > 0:
                    similarities.append(intersection / union)
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0
    else:
        avg_similarity = 0

    details = {
        'ai_markers': ai_count,
        'human_markers': human_count,
        'spam_markers': spam_count,
        'content_similarity': round(avg_similarity, 3),
        'word_count': word_count
    }

    # Decision logic
    if spam_count >= 2 or avg_similarity > 0.7:
        return {'authenticity': 'SCRIPTED', 'confidence': 0.8, 'details': details}
    elif human_count > ai_count and human_count >= 2:
        return {'authenticity': 'HUMAN_PRETENDING', 'confidence': 0.7, 'details': details}
    elif ai_count > human_count and ai_count >= 2:
        return {'authenticity': 'AUTHENTIC_AI', 'confidence': 0.7, 'details': details}
    elif ai_count > 0:
        return {'authenticity': 'LIKELY_AI', 'confidence': 0.5, 'details': details}
    else:
        return {'authenticity': 'UNCLEAR', 'confidence': 0.3, 'details': details}


# ============================================================
# SIGNAL 4: NETWORK ROLE (Hub vs Peripheral)
# ============================================================

def analyze_network_role(cursor, username):
    """
    Analyze network position - is this a hub or peripheral actor?
    High centrality + authentic = AI_HUB
    High centrality + scripted = COORDINATED_CAMPAIGN
    """
    # Outgoing interactions
    cursor.execute("""
        SELECT COUNT(DISTINCT author_to), COUNT(*)
        FROM interactions
        WHERE author_from = ?
    """, (username,))
    row = cursor.fetchone()
    out_unique = row[0] or 0
    out_total = row[1] or 0

    # Incoming interactions
    cursor.execute("""
        SELECT COUNT(DISTINCT author_from), COUNT(*)
        FROM interactions
        WHERE author_to = ?
    """, (username,))
    row = cursor.fetchone()
    in_unique = row[0] or 0
    in_total = row[1] or 0

    # Total actors for comparison
    cursor.execute("SELECT COUNT(*) FROM actors")
    total_actors = cursor.fetchone()[0] or 1

    # Connectivity ratio
    connectivity = (out_unique + in_unique) / (2 * total_actors) if total_actors > 0 else 0

    # Engagement ratio (interactions per connection)
    avg_engagement = (out_total + in_total) / (out_unique + in_unique) if (out_unique + in_unique) > 0 else 0

    details = {
        'out_unique': out_unique,
        'out_total': out_total,
        'in_unique': in_unique,
        'in_total': in_total,
        'connectivity': round(connectivity, 3),
        'avg_engagement': round(avg_engagement, 1)
    }

    # Role classification
    if connectivity > 0.3 and in_unique > 50:
        role = 'HUB'
    elif connectivity > 0.1 and in_unique > 20:
        role = 'INFLUENCER'
    elif out_unique > 10 and in_unique < 5:
        role = 'BROADCASTER'
    elif in_unique > out_unique * 2:
        role = 'CONTENT_CREATOR'
    elif out_unique > 5:
        role = 'ACTIVE_MEMBER'
    else:
        role = 'PERIPHERAL'

    return {'role': role, 'details': details}


# ============================================================
# COMPOSITE CLASSIFICATION v2
# ============================================================

def classify_actor_v2(timing, burst, content, network):
    """
    Combine all signals into final classification.

    Categories:
    - AUTHENTIC_AI: Genuine AI agent
    - AUTHENTIC_AI_HUB: Central authentic AI
    - HUMAN_OPERATOR: Human pretending to be AI
    - SCRIPTED_BOT: Mass-created bot account
    - COORDINATED_CAMPAIGN: Part of manipulation campaign
    - UNKNOWN: Insufficient data
    """

    # Start with base classification
    flags = []
    confidence_factors = []

    # Factor 1: Timing
    if timing['pattern'] == 'HUMAN':
        flags.append('human_timing')
        confidence_factors.append(('human', timing['confidence']))
    elif timing['pattern'] == 'AI':
        flags.append('ai_timing')
        confidence_factors.append(('ai', timing['confidence']))

    # Factor 2: Burst creation
    if burst['in_burst']:
        flags.append('burst_created')
        if burst['burst_size'] > 50:
            flags.append('mass_creation')
            confidence_factors.append(('scripted', 0.9))
        else:
            confidence_factors.append(('scripted', 0.5))

    # Factor 3: Content
    if content['authenticity'] == 'SCRIPTED':
        flags.append('scripted_content')
        confidence_factors.append(('scripted', content['confidence']))
    elif content['authenticity'] == 'HUMAN_PRETENDING':
        flags.append('human_content')
        confidence_factors.append(('human', content['confidence']))
    elif content['authenticity'] in ['AUTHENTIC_AI', 'LIKELY_AI']:
        flags.append('ai_content')
        confidence_factors.append(('ai', content['confidence']))

    # Factor 4: Network role
    if network['role'] == 'HUB':
        flags.append('network_hub')
    elif network['role'] == 'INFLUENCER':
        flags.append('network_influencer')

    # Aggregate confidence by category
    category_scores = defaultdict(list)
    for cat, conf in confidence_factors:
        category_scores[cat].append(conf)

    # Calculate final scores
    final_scores = {}
    for cat, scores in category_scores.items():
        final_scores[cat] = sum(scores) / len(scores) if scores else 0

    # Decision logic
    if 'mass_creation' in flags:
        classification = 'SCRIPTED_BOT'
        confidence = 0.95
    elif 'scripted_content' in flags and 'burst_created' in flags:
        classification = 'COORDINATED_CAMPAIGN'
        confidence = 0.85
    elif final_scores.get('human', 0) > final_scores.get('ai', 0) and final_scores.get('human', 0) > 0.5:
        classification = 'HUMAN_OPERATOR'
        confidence = final_scores['human']
    elif final_scores.get('ai', 0) > 0.5:
        if 'network_hub' in flags or 'network_influencer' in flags:
            classification = 'AUTHENTIC_AI_HUB'
        else:
            classification = 'AUTHENTIC_AI'
        confidence = final_scores['ai']
    elif final_scores.get('scripted', 0) > 0.5:
        classification = 'SCRIPTED_BOT'
        confidence = final_scores['scripted']
    else:
        classification = 'UNKNOWN'
        confidence = 0.3

    return {
        'classification': classification,
        'confidence': round(confidence, 2),
        'flags': flags,
        'scores': {k: round(v, 2) for k, v in final_scores.items()}
    }


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_actor_v2(cursor, username):
    """Run full v2 analysis for one actor."""
    timing = analyze_timing_pattern(cursor, username)
    burst = check_creation_burst(cursor, username)
    content = analyze_content_authenticity(cursor, username)
    network = analyze_network_role(cursor, username)

    classification = classify_actor_v2(timing, burst, content, network)

    return {
        'username': username,
        'classification': classification['classification'],
        'confidence': classification['confidence'],
        'flags': classification['flags'],
        'scores': classification['scores'],
        'timing': timing,
        'burst': burst,
        'content': content,
        'network': network
    }


def run_classification_v2(limit=1000):
    """Run v2 classification for all actors."""
    logger.info("=" * 60)
    logger.info("ACTOR CLASSIFIER v2.0 - AI-Native")
    logger.info("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get actors with activity
    cursor.execute("""
        SELECT username FROM actors
        WHERE username IN (
            SELECT author FROM posts
            UNION
            SELECT author FROM comments
        )
        ORDER BY (
            SELECT COUNT(*) FROM comments WHERE author = username
        ) DESC
        LIMIT ?
    """, (limit,))

    actors = [row[0] for row in cursor.fetchall()]
    logger.info(f"Analyzing {len(actors)} actors...")

    results = []
    for i, username in enumerate(actors, 1):
        if i % 20 == 0:
            logger.info(f"Progress: {i}/{len(actors)}")

        result = analyze_actor_v2(cursor, username)
        results.append(result)

        # Update actor_roles table with v2 classification
        cursor.execute("""
            INSERT OR REPLACE INTO actor_roles
            (username, primary_role, role_confidence, influence_score, last_updated, evidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            username,
            result['classification'],
            result['confidence'],
            result['network']['details'].get('connectivity', 0),
            datetime.now().isoformat(),
            json.dumps(result['flags'])
        ))

    conn.commit()
    conn.close()

    # Generate report
    logger.info("\n" + "=" * 60)
    logger.info("CLASSIFICATION RESULTS")
    logger.info("=" * 60)

    # Distribution
    class_counts = Counter(r['classification'] for r in results)
    logger.info("\nDistribution:")
    for cls, count in class_counts.most_common():
        pct = count / len(results) * 100
        logger.info(f"  {cls}: {count} ({pct:.1f}%)")

    # Examples by category
    for cls in ['AUTHENTIC_AI_HUB', 'AUTHENTIC_AI', 'HUMAN_OPERATOR', 'SCRIPTED_BOT']:
        examples = [r for r in results if r['classification'] == cls][:5]
        if examples:
            logger.info(f"\nTop {cls}:")
            for r in examples:
                logger.info(f"  [{r['confidence']:.2f}] {r['username'][:25]:<25} flags: {', '.join(r['flags'][:3])}")

    # Save results
    report_dir = REPORTS_DIR / TODAY
    report_dir.mkdir(parents=True, exist_ok=True)

    results_path = report_dir / "actor_classification_v2.json"
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\nResults saved: {results_path}")

    # Generate markdown report
    report_md = generate_classification_report(results)
    report_path = report_dir / "actor_classification_v2.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_md)
    logger.info(f"Report saved: {report_path}")

    return results


def generate_classification_report(results):
    """Generate markdown report of classification results."""

    class_counts = Counter(r['classification'] for r in results)

    report = f"""# Actor Classification Report v2.0
## {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## Summary

**Total actors analyzed:** {len(results)}

### Distribution

| Classification | Count | % |
|----------------|-------|---|
"""

    for cls, count in class_counts.most_common():
        pct = count / len(results) * 100
        report += f"| {cls} | {count} | {pct:.1f}% |\n"

    report += """
---

## Classification Categories

| Category | Meaning |
|----------|---------|
| AUTHENTIC_AI | Genuine AI agent with organic behavior |
| AUTHENTIC_AI_HUB | Central/influential authentic AI agent |
| HUMAN_OPERATOR | Human pretending to be AI (timing + content signals) |
| SCRIPTED_BOT | Mass-created or spam account |
| COORDINATED_CAMPAIGN | Part of manipulation campaign |
| UNKNOWN | Insufficient data for classification |

---

## Top Authentic AI Hubs

"""

    hubs = [r for r in results if r['classification'] == 'AUTHENTIC_AI_HUB']
    for r in hubs[:10]:
        report += f"- **{r['username']}** (confidence: {r['confidence']:.2f})\n"
        report += f"  - Network: {r['network']['details'].get('in_unique', 0)} incoming connections\n"
        report += f"  - Timing: {r['timing']['pattern']} pattern\n"

    report += """
---

## Detected Human Operators

"""

    humans = [r for r in results if r['classification'] == 'HUMAN_OPERATOR']
    for r in humans[:10]:
        report += f"- **{r['username']}** (confidence: {r['confidence']:.2f})\n"
        report += f"  - Flags: {', '.join(r['flags'])}\n"
        if r['timing']['details']:
            report += f"  - Night ratio: {r['timing']['details'].get('night_ratio', 'N/A')}\n"

    report += """
---

## Scripted/Bot Accounts

"""

    bots = [r for r in results if r['classification'] in ['SCRIPTED_BOT', 'COORDINATED_CAMPAIGN']]
    for r in bots[:15]:
        report += f"- **{r['username']}** ({r['classification']})\n"
        if r['burst']['in_burst']:
            report += f"  - Created in burst of {r['burst']['burst_size']} accounts\n"

    report += f"""
---

## Methodology

Classifier v2.0 uses four signal types:

1. **Timing Analysis**: Distinguishes human sleep patterns from AI uniform activity
2. **Burst Detection**: Identifies mass-created accounts
3. **Content Authenticity**: Detects AI markers vs ironic/spam content
4. **Network Role**: Identifies hubs and influencers

Unlike v1, this classifier treats AI-typical behaviors (regularity, consistency) as POSITIVE signals for authenticity, not negative.

---

*Generated by Actor Classifier v2.0*
*Noosphere Project*
"""

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000, help="Number of actors to analyze")
    args = parser.parse_args()

    run_classification_v2(limit=args.limit)
