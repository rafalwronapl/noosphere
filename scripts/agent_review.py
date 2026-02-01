#!/usr/bin/env python3
"""
Agent Review - Pre-Publication Data Review
==========================================
Analizuje surowe dane i raport przed publikacją.
Wyłapuje wzorce, anomalie i wnioski które mogliśmy przeoczyć.

Uruchom po wygenerowaniu raportu, przed publikacją:
    python agent_review.py

Output: reports/YYYY-MM-DD/agent_review.md
"""

import sys
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Config
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from config import DB_PATH, REPORTS_DIR, TODAY, setup_logging
    logger = setup_logging("agent_review")
except ImportError:
    DB_PATH = Path(__file__).parent.parent / "data" / "observatory.db"
    REPORTS_DIR = Path(__file__).parent.parent / "reports"
    TODAY = datetime.now().strftime("%Y-%m-%d")
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("agent_review")


def analyze_timestamp_patterns(cursor):
    """Szukaj wzorców w timestamps tworzenia kont."""
    findings = []

    cursor.execute("""
        SELECT username, first_seen FROM actors
        WHERE first_seen IS NOT NULL
        ORDER BY first_seen
    """)

    actors = cursor.fetchall()
    if not actors:
        return findings

    # Grupuj po sekundzie
    by_second = defaultdict(list)
    for username, created_at in actors:
        if created_at:
            # Wyciągnij sekundę (bez milisekund)
            second = created_at[:19] if len(created_at) > 19 else created_at
            by_second[second].append(username)

    # Znajdź burst creation (>5 kont w tej samej sekundzie)
    bursts = [(ts, users) for ts, users in by_second.items() if len(users) >= 5]

    if bursts:
        for ts, users in sorted(bursts, key=lambda x: -len(x[1])):
            findings.append({
                'type': 'TIMESTAMP_BURST',
                'severity': 'HIGH' if len(users) > 20 else 'MEDIUM',
                'description': f'{len(users)} kont utworzonych w tej samej sekundzie: {ts}',
                'data': users[:10],  # Pierwsze 10
                'interpretation': 'Może wskazywać na batch onboarding lub seedowanie. Wymaga analizy.'
            })

    return findings


def analyze_activity_patterns(cursor):
    """Szukaj anomalii w aktywności."""
    findings = []

    # Konta z bardzo wysoką aktywnością
    cursor.execute("""
        SELECT author, COUNT(*) as cnt
        FROM comments
        GROUP BY author
        HAVING cnt > 100
        ORDER BY cnt DESC
        LIMIT 10
    """)

    high_activity = cursor.fetchall()
    if high_activity:
        for author, count in high_activity:
            if count > 300:
                findings.append({
                    'type': 'HIGH_ACTIVITY',
                    'severity': 'MEDIUM',
                    'description': f'{author}: {count} komentarzy',
                    'interpretation': 'Wysoka aktywność - może być bot lub bardzo aktywny użytkownik.'
                })

    # Timing analysis - konta bez nocnej aktywności
    cursor.execute("""
        SELECT author,
               SUM(CASE WHEN CAST(strftime('%H', created_at) AS INTEGER) BETWEEN 0 AND 6 THEN 1 ELSE 0 END) as night,
               COUNT(*) as total
        FROM comments
        GROUP BY author
        HAVING total >= 10
    """)

    for author, night, total in cursor.fetchall():
        night_ratio = night / total if total > 0 else 0
        if night_ratio == 0 and total >= 20:
            findings.append({
                'type': 'NO_NIGHT_ACTIVITY',
                'severity': 'LOW',
                'description': f'{author}: 0% aktywności nocnej ({total} komentarzy)',
                'interpretation': 'Wzorzec typowy dla ludzi, ale mała próbka.'
            })

    return findings


def analyze_content_patterns(cursor):
    """Szukaj wzorców w treści."""
    findings = []

    # Powtarzające się frazy (potencjalny spam/bot)
    cursor.execute("""
        SELECT content, COUNT(*) as cnt
        FROM comments
        WHERE LENGTH(content) > 50
        GROUP BY content
        HAVING cnt > 3
        ORDER BY cnt DESC
        LIMIT 5
    """)

    duplicates = cursor.fetchall()
    if duplicates:
        for content, count in duplicates:
            findings.append({
                'type': 'DUPLICATE_CONTENT',
                'severity': 'MEDIUM',
                'description': f'Identyczna treść powtórzona {count} razy',
                'data': content[:100] + '...' if len(content) > 100 else content,
                'interpretation': 'Może być spam lub skoordynowana akcja.'
            })

    # Prompt injection attempts
    cursor.execute("""
        SELECT COUNT(*) FROM comments WHERE is_prompt_injection = 1
    """)
    injection_count = cursor.fetchone()[0]

    if injection_count > 100:
        findings.append({
            'type': 'HIGH_INJECTION_ACTIVITY',
            'severity': 'HIGH',
            'description': f'{injection_count} wykrytych prób prompt injection',
            'interpretation': 'Społeczność jest celem ataków manipulacyjnych.'
        })

    return findings


def analyze_network_patterns(cursor):
    """Szukaj wzorców w sieci interakcji."""
    findings = []

    # Hub detection - konta z bardzo wysoką centralnością
    cursor.execute("""
        SELECT username, network_centrality
        FROM actors
        WHERE network_centrality IS NOT NULL
        ORDER BY network_centrality DESC
        LIMIT 5
    """)

    top_central = cursor.fetchall()
    if top_central and top_central[0][1] == 1.0:
        findings.append({
            'type': 'SINGLE_HUB',
            'severity': 'MEDIUM',
            'description': f'{top_central[0][0]} ma centrality 1.0 - dominuje sieć',
            'interpretation': 'Jeden aktor łączy całą społeczność. Warto zbadać dlaczego.'
        })

    # Isolated actors (post but no interactions)
    cursor.execute("""
        SELECT COUNT(DISTINCT p.author)
        FROM posts p
        LEFT JOIN interactions i ON p.author = i.author_from OR p.author = i.author_to
        WHERE i.author_from IS NULL
    """)
    isolated = cursor.fetchone()[0]

    if isolated > 10:
        findings.append({
            'type': 'ISOLATED_ACTORS',
            'severity': 'LOW',
            'description': f'{isolated} aktorów bez interakcji z innymi',
            'interpretation': 'Mogą być nowi użytkownicy lub boty.'
        })

    return findings


def check_data_quality(cursor):
    """Sprawdź jakość danych."""
    findings = []

    # Missing timestamps
    cursor.execute("SELECT COUNT(*) FROM actors WHERE first_seen IS NULL")
    missing_created = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM actors")
    total_actors = cursor.fetchone()[0]

    if missing_created > total_actors * 0.1:
        findings.append({
            'type': 'DATA_QUALITY',
            'severity': 'LOW',
            'description': f'{missing_created}/{total_actors} aktorów bez timestamp first_seen',
            'interpretation': 'Dane niekompletne - analiza timestamps może być niepełna.'
        })

    # Check sample size
    if total_actors < 500:
        findings.append({
            'type': 'SMALL_SAMPLE',
            'severity': 'HIGH',
            'description': f'Mała próbka: tylko {total_actors} aktorów',
            'interpretation': 'Wnioski mogą nie być reprezentatywne dla całej platformy.'
        })

    return findings


def generate_review():
    """Generuj pełny review."""
    logger.info("=" * 60)
    logger.info("AGENT REVIEW - Pre-Publication Analysis")
    logger.info("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    all_findings = []

    # Run all analyses
    logger.info("Analyzing timestamp patterns...")
    all_findings.extend(analyze_timestamp_patterns(cursor))

    logger.info("Analyzing activity patterns...")
    all_findings.extend(analyze_activity_patterns(cursor))

    logger.info("Analyzing content patterns...")
    all_findings.extend(analyze_content_patterns(cursor))

    logger.info("Analyzing network patterns...")
    all_findings.extend(analyze_network_patterns(cursor))

    logger.info("Checking data quality...")
    all_findings.extend(check_data_quality(cursor))

    conn.close()

    # Sort by severity
    severity_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    all_findings.sort(key=lambda x: severity_order.get(x.get('severity', 'LOW'), 2))

    # Generate report
    report = []
    report.append("# Agent Review - Pre-Publication Analysis")
    report.append(f"## {TODAY}")
    report.append("")
    report.append("---")
    report.append("")
    report.append("> **Ten raport jest automatycznie generowany przed publikacją.**")
    report.append("> Sprawdź każdy finding i zdecyduj czy wymaga uwzględnienia w raporcie.")
    report.append("")
    report.append("---")
    report.append("")

    # Summary
    high_count = sum(1 for f in all_findings if f.get('severity') == 'HIGH')
    medium_count = sum(1 for f in all_findings if f.get('severity') == 'MEDIUM')
    low_count = sum(1 for f in all_findings if f.get('severity') == 'LOW')

    report.append("## Summary")
    report.append("")
    report.append(f"- **HIGH**: {high_count} findings")
    report.append(f"- **MEDIUM**: {medium_count} findings")
    report.append(f"- **LOW**: {low_count} findings")
    report.append("")

    if high_count > 0:
        report.append("> ⚠️ **UWAGA**: Są findings o wysokim priorytecie. Sprawdź przed publikacją!")

    report.append("")
    report.append("---")
    report.append("")

    # Findings
    report.append("## Findings")
    report.append("")

    for i, finding in enumerate(all_findings, 1):
        severity = finding.get('severity', 'LOW')
        severity_emoji = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(severity, '⚪')

        report.append(f"### {i}. [{severity}] {finding['type']}")
        report.append("")
        report.append(f"{severity_emoji} **{finding['description']}**")
        report.append("")

        if 'data' in finding:
            data = finding['data']
            if isinstance(data, list):
                report.append("```")
                for item in data[:5]:
                    report.append(f"  - {item}")
                if len(data) > 5:
                    report.append(f"  ... i {len(data) - 5} więcej")
                report.append("```")
            else:
                report.append(f"```\n{data}\n```")
            report.append("")

        report.append(f"*Interpretacja: {finding.get('interpretation', 'Brak')}*")
        report.append("")
        report.append("---")
        report.append("")

    # Recommendations
    report.append("## Rekomendacje przed publikacją")
    report.append("")
    report.append("1. [ ] Sprawdź HIGH findings")
    report.append("2. [ ] Upewnij się że dane nie zawierają nadinterpretacji")
    report.append("3. [ ] Dodaj disclaimery gdzie potrzeba")
    report.append("4. [ ] Rozważ czy sample size jest wystarczający")
    report.append("")
    report.append("---")
    report.append("")
    report.append(f"*Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    report.append("*Agent Review v1.0*")

    # Save
    output_dir = REPORTS_DIR / TODAY
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "agent_review.md"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    logger.info(f"Review saved: {output_path}")

    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"FINDINGS: {high_count} HIGH, {medium_count} MEDIUM, {low_count} LOW")
    logger.info("=" * 60)

    if high_count > 0:
        logger.info("")
        logger.info("⚠️  HIGH PRIORITY FINDINGS - REVIEW BEFORE PUBLISHING!")
        for f in all_findings:
            if f.get('severity') == 'HIGH':
                logger.info(f"  - {f['type']}: {f['description']}")

    return all_findings


if __name__ == "__main__":
    generate_review()
