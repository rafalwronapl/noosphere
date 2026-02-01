#!/usr/bin/env python3
"""
Actor Credibility Score - detect strategic/manipulative behavior.
Not "human vs AI" but "risk profile".

6 actor types to detect:
A. Human sockpuppets - too coherent, no technical errors
B. Human-operated agents - style shifts, editorial posts
C. Platform plants - always pro-system, conflict smoothers
D. Economic manipulators - token/reputation pumpers
E. Ideological actors - geopolitical narratives, doom/utopia
F. Emergent trolls/LARP - mysticism, repetitive phrases

5 detection signals:
1. Stylometry - sentence length, word entropy, phrase repetition
2. Activity rhythm - sleep patterns, weekend gaps, API cycles
3. Epistemic consistency - opinion changes, source references
4. Support networks - mutual liking, citation cliques
5. Attention economy - focus on tokens/governance/reputation
"""

import sys
import sqlite3
import re
import math
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict
from config import DB_PATH

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ============================================================
# SIGNAL 1: STYLOMETRY
# ============================================================

def calculate_word_entropy(text):
    """Calculate entropy of word distribution (higher = more diverse)."""
    if not text:
        return 0
    words = re.findall(r'\b\w+\b', text.lower())
    if len(words) < 10:
        return 0
    counts = Counter(words)
    total = len(words)
    entropy = -sum((c/total) * math.log2(c/total) for c in counts.values() if c > 0)
    return entropy


def calculate_sentence_stats(text):
    """Calculate sentence length statistics."""
    if not text:
        return {'avg': 0, 'std': 0}
    sentences = re.split(r'[.!?]+', text)
    lengths = [len(s.split()) for s in sentences if s.strip()]
    if not lengths:
        return {'avg': 0, 'std': 0}
    avg = sum(lengths) / len(lengths)
    variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
    return {'avg': avg, 'std': math.sqrt(variance)}


def calculate_phrase_repetition(texts):
    """Calculate how often an actor repeats their own phrases."""
    if len(texts) < 3:
        return 0

    # Extract 3-grams from all texts
    all_ngrams = []
    for text in texts:
        if not text:
            continue
        words = re.findall(r'\b\w+\b', text.lower())
        ngrams = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
        all_ngrams.extend(ngrams)

    if not all_ngrams:
        return 0

    counts = Counter(all_ngrams)
    repeated = sum(1 for c in counts.values() if c > 2)
    return repeated / len(set(all_ngrams)) if all_ngrams else 0


def get_stylometry_score(cursor, username):
    """Get stylometry-based credibility signals."""
    cursor.execute("""
        SELECT content FROM comments WHERE author = ?
        UNION ALL
        SELECT title || ' ' || COALESCE(content, '') FROM posts WHERE author = ?
    """, (username, username))

    texts = [row[0] for row in cursor.fetchall() if row[0]]

    if len(texts) < 3:
        return {'entropy': None, 'sentence_avg': None, 'repetition': None}

    # Combine for entropy
    combined = ' '.join(texts)
    entropy = calculate_word_entropy(combined)

    # Sentence stats
    sentence_stats = calculate_sentence_stats(combined)

    # Repetition
    repetition = calculate_phrase_repetition(texts)

    return {
        'entropy': round(entropy, 2),
        'sentence_avg': round(sentence_stats['avg'], 1),
        'sentence_std': round(sentence_stats['std'], 1),
        'repetition': round(repetition, 3)
    }


# ============================================================
# SIGNAL 2: ACTIVITY RHYTHM
# ============================================================

def get_activity_rhythm(cursor, username):
    """Analyze activity patterns - sleep, weekends, regularity."""
    cursor.execute("""
        SELECT created_at FROM comments WHERE author = ?
        UNION ALL
        SELECT created_at FROM posts WHERE author = ?
    """, (username, username))

    timestamps = [row[0] for row in cursor.fetchall() if row[0]]

    if len(timestamps) < 5:
        return {'regularity': None, 'night_ratio': None, 'weekend_ratio': None}

    hours = []
    weekdays = []

    for ts in timestamps:
        try:
            if 'T' in ts:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(ts[:19], '%Y-%m-%d %H:%M:%S')
            hours.append(dt.hour)
            weekdays.append(dt.weekday())
        except (ValueError, TypeError, AttributeError):
            continue

    if not hours:
        return {'regularity': None, 'night_ratio': None, 'weekend_ratio': None}

    # Night activity (0-6 AM) - humans sleep, bots don't
    night_ratio = sum(1 for h in hours if 0 <= h < 6) / len(hours)

    # Weekend activity
    weekend_ratio = sum(1 for w in weekdays if w >= 5) / len(weekdays)

    # Regularity - how evenly distributed across hours
    hour_counts = Counter(hours)
    hour_entropy = -sum((c/len(hours)) * math.log2(c/len(hours))
                        for c in hour_counts.values() if c > 0)
    max_entropy = math.log2(24)  # Maximum if perfectly distributed
    regularity = hour_entropy / max_entropy if max_entropy > 0 else 0

    return {
        'regularity': round(regularity, 2),  # 1.0 = perfectly regular (bot-like)
        'night_ratio': round(night_ratio, 2),  # High = never sleeps
        'weekend_ratio': round(weekend_ratio, 2)  # ~0.28 expected for humans
    }


# ============================================================
# SIGNAL 3: EPISTEMIC CONSISTENCY
# ============================================================

OPINION_MARKERS = [
    r'\bi think\b', r'\bi believe\b', r'\bin my opinion\b',
    r'\bi disagree\b', r'\bi agree\b', r'\byou\'re right\b',
    r'\bi was wrong\b', r'\bi changed my mind\b', r'\bgood point\b'
]

CERTAINTY_MARKERS = [
    r'\bobviously\b', r'\bclearly\b', r'\bof course\b',
    r'\beveryone knows\b', r'\bno one can deny\b', r'\bundeniably\b'
]

def get_epistemic_score(cursor, username):
    """Analyze epistemic behavior - does agent update beliefs?"""
    cursor.execute("""
        SELECT content FROM comments WHERE author = ?
    """, (username,))

    texts = [row[0] for row in cursor.fetchall() if row[0]]

    if len(texts) < 5:
        return {'opinion_markers': None, 'certainty_ratio': None, 'updates_beliefs': None}

    combined = ' '.join(texts).lower()

    # Count opinion markers
    opinion_count = sum(len(re.findall(p, combined)) for p in OPINION_MARKERS)

    # Count certainty markers (propagandists use more)
    certainty_count = sum(len(re.findall(p, combined)) for p in CERTAINTY_MARKERS)

    # "I was wrong" / "I changed my mind" - sign of genuine agent
    belief_updates = len(re.findall(r'\bi was wrong\b|\bi changed my mind\b|\bgood point\b', combined))

    word_count = len(combined.split())

    return {
        'opinion_markers': round(opinion_count / (word_count/1000), 2) if word_count > 0 else 0,
        'certainty_ratio': round(certainty_count / (word_count/1000), 2) if word_count > 0 else 0,
        'updates_beliefs': belief_updates > 0
    }


# ============================================================
# SIGNAL 4: SUPPORT NETWORKS (CLIQUES)
# ============================================================

def get_network_score(cursor, username):
    """Analyze network behavior - sockpuppets support each other."""
    # Who does this actor interact with?
    cursor.execute("""
        SELECT author_to, COUNT(*) as cnt
        FROM interactions
        WHERE author_from = ? AND author_to IS NOT NULL
        GROUP BY author_to
        ORDER BY cnt DESC
    """, (username,))

    outgoing = {row[0]: row[1] for row in cursor.fetchall()}

    # Who interacts with this actor?
    cursor.execute("""
        SELECT author_from, COUNT(*) as cnt
        FROM interactions
        WHERE author_to = ? AND author_from IS NOT NULL
        GROUP BY author_from
        ORDER BY cnt DESC
    """, (username,))

    incoming = {row[0]: row[1] for row in cursor.fetchall()}

    if not outgoing and not incoming:
        return {'reciprocity': None, 'concentration': None, 'clique_score': None}

    # Reciprocity - how many mutual connections?
    mutual = set(outgoing.keys()) & set(incoming.keys())
    reciprocity = len(mutual) / len(set(outgoing.keys()) | set(incoming.keys())) if outgoing or incoming else 0

    # Concentration - does actor focus on few targets? (sockpuppet signal)
    if outgoing:
        top_3 = sum(sorted(outgoing.values(), reverse=True)[:3])
        total_out = sum(outgoing.values())
        concentration = top_3 / total_out if total_out > 0 else 0
    else:
        concentration = 0

    # Clique detection - do actor's targets also support each other?
    clique_score = 0
    if len(outgoing) >= 3:
        targets = list(outgoing.keys())[:10]
        cursor.execute("""
            SELECT COUNT(*) FROM interactions
            WHERE author_from IN ({}) AND author_to IN ({})
        """.format(','.join('?' * len(targets)), ','.join('?' * len(targets))),
        targets + targets)
        internal_edges = cursor.fetchone()[0]
        max_edges = len(targets) * (len(targets) - 1)
        clique_score = internal_edges / max_edges if max_edges > 0 else 0

    return {
        'reciprocity': round(reciprocity, 2),
        'concentration': round(concentration, 2),  # High = focused on few (suspicious)
        'clique_score': round(clique_score, 3)  # High = sockpuppet network
    }


# ============================================================
# SIGNAL 5: ATTENTION ECONOMY
# ============================================================

ECONOMIC_TERMS = [
    r'\btoken\b', r'\btokens\b', r'\bcrypto\b', r'\bwallet\b',
    r'\bgovernance\b', r'\bvote\b', r'\bvoting\b', r'\bstake\b',
    r'\breputation\b', r'\binfluence\b', r'\bpower\b',
    r'\bmoney\b', r'\bprofit\b', r'\binvest\b', r'\bpump\b',
    r'\bfuture\b.*\b(ai|agent)\b', r'\brevolution\b'
]

PLATFORM_TERMS = [
    r'\bmoltbook\b', r'\bplatform\b', r'\bcommunity\b',
    r'\bgreat\b.*\b(feature|update)\b', r'\blove this\b',
    r'\bamazing\b', r'\bincredible\b'
]

def get_economic_score(cursor, username):
    """Analyze focus on economic/governance topics."""
    cursor.execute("""
        SELECT content FROM comments WHERE author = ?
        UNION ALL
        SELECT title || ' ' || COALESCE(content, '') FROM posts WHERE author = ?
    """, (username, username))

    texts = [row[0] for row in cursor.fetchall() if row[0]]

    if not texts:
        return {'economic_focus': None, 'platform_praise': None}

    combined = ' '.join(texts).lower()
    word_count = len(combined.split())

    if word_count < 50:
        return {'economic_focus': None, 'platform_praise': None}

    # Economic term density
    economic_count = sum(len(re.findall(p, combined)) for p in ECONOMIC_TERMS)
    economic_focus = economic_count / (word_count / 1000)

    # Platform praise density (platform plant signal)
    platform_count = sum(len(re.findall(p, combined)) for p in PLATFORM_TERMS)
    platform_praise = platform_count / (word_count / 1000)

    return {
        'economic_focus': round(economic_focus, 2),
        'platform_praise': round(platform_praise, 2)
    }


# ============================================================
# COMPOSITE CREDIBILITY SCORE
# ============================================================

def calculate_credibility_score(stylometry, rhythm, epistemic, network, economic):
    """Calculate composite credibility score (0-100, higher = more credible)."""
    score = 100
    flags = []

    # Stylometry flags
    if stylometry.get('repetition') and stylometry['repetition'] > 0.1:
        score -= 10
        flags.append('high_phrase_repetition')
    if stylometry.get('entropy') and stylometry['entropy'] < 4:
        score -= 5
        flags.append('low_vocabulary_diversity')

    # Rhythm flags
    if rhythm.get('night_ratio') and rhythm['night_ratio'] > 0.3:
        score -= 10
        flags.append('never_sleeps')
    if rhythm.get('regularity') and rhythm['regularity'] > 0.9:
        score -= 10
        flags.append('too_regular')

    # Epistemic flags
    if epistemic.get('certainty_ratio') and epistemic['certainty_ratio'] > 5:
        score -= 10
        flags.append('high_certainty_language')
    if epistemic.get('updates_beliefs') == False and epistemic.get('opinion_markers'):
        score -= 5
        flags.append('never_changes_mind')

    # Network flags
    if network.get('clique_score') and network['clique_score'] > 0.3:
        score -= 15
        flags.append('sockpuppet_network')
    if network.get('concentration') and network['concentration'] > 0.8:
        score -= 10
        flags.append('focused_on_few_targets')

    # Economic flags
    if economic.get('economic_focus') and economic['economic_focus'] > 10:
        score -= 10
        flags.append('economic_obsession')
    if economic.get('platform_praise') and economic['platform_praise'] > 5:
        score -= 5
        flags.append('platform_cheerleader')

    return max(0, score), flags


def classify_actor_type(flags, network, economic):
    """Classify actor into one of 6 types based on signals."""
    if 'sockpuppet_network' in flags or 'focused_on_few_targets' in flags:
        return 'A_sockpuppet'
    if 'too_regular' in flags and 'never_sleeps' not in flags:
        return 'B_human_operated'
    if 'platform_cheerleader' in flags:
        return 'C_platform_plant'
    if 'economic_obsession' in flags:
        return 'D_economic_manipulator'
    if 'high_certainty_language' in flags and 'never_changes_mind' in flags:
        return 'E_ideological'
    if 'high_phrase_repetition' in flags:
        return 'F_troll_larp'
    return 'organic'


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_actor(cursor, username):
    """Run full credibility analysis for one actor."""
    stylometry = get_stylometry_score(cursor, username)
    rhythm = get_activity_rhythm(cursor, username)
    epistemic = get_epistemic_score(cursor, username)
    network = get_network_score(cursor, username)
    economic = get_economic_score(cursor, username)

    score, flags = calculate_credibility_score(stylometry, rhythm, epistemic, network, economic)
    actor_type = classify_actor_type(flags, network, economic)

    return {
        'username': username,
        'credibility_score': score,
        'flags': flags,
        'actor_type': actor_type,
        'stylometry': stylometry,
        'rhythm': rhythm,
        'epistemic': epistemic,
        'network': network,
        'economic': economic
    }


def run_credibility_analysis(limit=50):
    """Run credibility analysis for top actors."""
    print("=" * 60)
    print("  ACTOR CREDIBILITY SCORE")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get top actors by activity
    cursor.execute("""
        SELECT username FROM actors
        WHERE username IN (
            SELECT author FROM comments GROUP BY author HAVING COUNT(*) >= 5
        )
        ORDER BY (SELECT COUNT(*) FROM comments WHERE author = username) DESC
        LIMIT ?
    """, (limit,))

    actors = [row[0] for row in cursor.fetchall()]
    print(f"\n>> Analyzing {len(actors)} actors...")

    results = []
    for i, username in enumerate(actors, 1):
        if i % 10 == 0:
            print(f"   Progress: {i}/{len(actors)}")
        result = analyze_actor(cursor, username)
        results.append(result)

        # Save to actor_roles table
        cursor.execute("""
            INSERT OR REPLACE INTO actor_roles
            (username, primary_role, role_confidence, influence_score, last_updated, evidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            username,
            result['actor_type'],
            result['credibility_score'] / 100,
            result['network'].get('reciprocity', 0),
            datetime.now().isoformat(),
            str(result['flags'])
        ))

    conn.commit()

    # Sort by credibility (lowest first = most suspicious)
    results.sort(key=lambda x: x['credibility_score'])

    print("\n>> Most Suspicious Actors (lowest credibility):")
    for r in results[:15]:
        flags_str = ', '.join(r['flags'][:3]) if r['flags'] else 'none'
        print(f"   [{r['credibility_score']:3d}] {r['username'][:20]:<20} | {r['actor_type']:<20} | {flags_str}")

    print("\n>> Actor Type Distribution:")
    type_counts = Counter(r['actor_type'] for r in results)
    for t, count in type_counts.most_common():
        pct = count / len(results) * 100
        print(f"   {t}: {count} ({pct:.1f}%)")

    print("\n>> Most Common Flags:")
    all_flags = [f for r in results for f in r['flags']]
    for flag, count in Counter(all_flags).most_common(10):
        print(f"   {flag}: {count}")

    conn.close()

    print("\n" + "=" * 60)
    print("  CREDIBILITY ANALYSIS COMPLETE")
    print("=" * 60)

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50, help="Number of actors to analyze")
    args = parser.parse_args()

    run_credibility_analysis(limit=args.limit)
