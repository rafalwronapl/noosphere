#!/usr/bin/env python3
"""
Moltbook Observatory - CLI Dashboard
Ladny przeglad danych dla czlowieka.
"""

import sys
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    # Windows doesn't support ANSI colors by default
    os.system('')  # Enable ANSI on Windows 10+


# ANSI colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


# Import centralized config
from config import DB_PATH


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")


def print_section(text):
    print(f"\n{Colors.BOLD}{Colors.YELLOW}>> {text}{Colors.END}")
    print(f"{Colors.YELLOW}{'-'*50}{Colors.END}")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def show_overview():
    """Pokaz ogolny przeglad."""
    conn = get_db_connection()
    cursor = conn.cursor()

    print_header("MOLTBOOK OBSERVATORY - DASHBOARD")
    print(f"   Czas: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Statystyki ogolne
    print_section("STATYSTYKI OGOLNE")

    cursor.execute("SELECT COUNT(*) FROM posts")
    posts_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT author) FROM posts")
    authors_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT submolt) FROM posts")
    submolts_count = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(comment_count) FROM posts")
    total_comments = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM scans")
    scans_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM patterns")
    patterns_count = cursor.fetchone()[0]

    print(f"  [Posts]    Posty w bazie:        {Colors.BOLD}{posts_count}{Colors.END}")
    print(f"  [Authors]  Unikalnych autorow:   {Colors.BOLD}{authors_count}{Colors.END}")
    print(f"  [Submolts] Submoltow:            {Colors.BOLD}{submolts_count}{Colors.END}")
    print(f"  [Comments] Laczne komentarze:    {Colors.BOLD}{total_comments:,}{Colors.END}")
    print(f"  [Scans]    Wykonanych skanow:    {Colors.BOLD}{scans_count}{Colors.END}")
    print(f"  [Patterns] Wykrytych wzorcow:    {Colors.BOLD}{patterns_count}{Colors.END}")

    conn.close()


def show_top_posts(limit=10):
    """Pokaz najbardziej angazujace posty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    print_section(f"TOP {limit} POSTOW (wg komentarzy)")

    cursor.execute("""
        SELECT id, author, submolt, title, votes_net as votes, comment_count as comments,
               CAST(comment_count AS FLOAT) / MAX(ABS(votes_net), 1) as controversy
        FROM posts
        ORDER BY comment_count DESC
        LIMIT ?
    """, (limit,))

    posts = cursor.fetchall()

    for i, post in enumerate(posts, 1):
        # Controversy indicator
        controversy = post['controversy'] or 0
        if controversy > 10:
            c_indicator = f"{Colors.RED}[!!! CONTROVERSY]{Colors.END}"
        elif controversy > 5:
            c_indicator = f"{Colors.YELLOW}[!! HOT DEBATE]{Colors.END}"
        elif controversy > 2:
            c_indicator = f"{Colors.YELLOW}[! DEBATA]{Colors.END}"
        else:
            c_indicator = ""

        # Vote indicator
        votes = post['votes'] or 0
        if votes < 0:
            v_color = Colors.RED
        elif votes > 100:
            v_color = Colors.GREEN
        else:
            v_color = Colors.END

        title = post['title'][:45] + "..." if post['title'] and len(post['title']) > 45 else (post['title'] or 'Unknown')

        print(f"\n  {Colors.BOLD}#{i}{Colors.END} {title}")
        print(f"     {Colors.CYAN}m/{post['submolt']}{Colors.END} | {post['author']}")
        print(f"     Votes: {v_color}{votes:+d}{Colors.END}  Comments: {Colors.BOLD}{post['comments']}{Colors.END}  {c_indicator}")

    conn.close()


def show_top_authors(limit=10):
    """Pokaz najbardziej aktywnych autorow."""
    conn = get_db_connection()
    cursor = conn.cursor()

    print_section(f"TOP {limit} AUTOROW (wg aktywnosci)")

    cursor.execute("""
        SELECT author,
               COUNT(*) as post_count,
               SUM(comment_count) as total_comments,
               SUM(votes_net) as total_votes,
               AVG(comment_count) as avg_comments
        FROM posts
        GROUP BY author
        ORDER BY total_comments DESC, post_count DESC
        LIMIT ?
    """, (limit,))

    authors = cursor.fetchall()

    for i, author in enumerate(authors, 1):
        # Activity level
        if author['post_count'] >= 5:
            activity = f"{Colors.RED}[VERY ACTIVE]{Colors.END}"
        elif author['post_count'] >= 3:
            activity = f"{Colors.YELLOW}[ACTIVE]{Colors.END}"
        else:
            activity = ""

        total_comments = author['total_comments'] or 0
        total_votes = author['total_votes'] or 0
        avg_comments = author['avg_comments'] or 0

        print(f"\n  {Colors.BOLD}#{i}{Colors.END} {Colors.CYAN}{author['author']}{Colors.END} {activity}")
        print(f"     Posts: {author['post_count']} | Comments: {total_comments:,} | Votes: {total_votes:+d}")
        print(f"     Avg {avg_comments:.1f} comments/post")

    conn.close()


def show_submolts():
    """Pokaz aktywnosc submoltow."""
    conn = get_db_connection()
    cursor = conn.cursor()

    print_section("AKTYWNOSC SUBMOLTOW")

    cursor.execute("""
        SELECT submolt,
               COUNT(*) as post_count,
               SUM(comment_count) as total_comments,
               SUM(votes_net) as total_votes,
               AVG(comment_count) as avg_engagement
        FROM posts
        GROUP BY submolt
        ORDER BY total_comments DESC
    """)

    submolts = cursor.fetchall()

    for submolt in submolts:
        total_comments = submolt['total_comments'] or 0
        bar_length = min(int(total_comments / 200), 30)
        bar = "#" * bar_length

        avg_eng = submolt['avg_engagement'] or 0

        print(f"\n  {Colors.BOLD}m/{submolt['submolt']}{Colors.END}")
        print(f"     {Colors.GREEN}{bar}{Colors.END} {total_comments:,} comments")
        print(f"     {submolt['post_count']} posts | Avg {avg_eng:.0f} comments/post")

    conn.close()


def show_alerts():
    """Pokaz alerty i rzeczy wymagajace uwagi."""
    conn = get_db_connection()
    cursor = conn.cursor()

    print_section("ALERTY I OBSERWACJE")

    # Bardzo kontrowersyjne posty
    cursor.execute("""
        SELECT title, author, submolt, comment_count as comments, votes_net as votes,
               CAST(comment_count AS FLOAT) / MAX(ABS(votes_net), 1) as controversy
        FROM posts
        WHERE comment_count > 100
        ORDER BY controversy DESC
        LIMIT 5
    """)

    controversial = cursor.fetchall()

    if controversial:
        print(f"\n  {Colors.RED}[!!!] WYSOKA KONTROWERSJA:{Colors.END}")
        for post in controversial:
            controversy = post['controversy'] or 0
            if controversy > 5:
                print(f"     * {post['title'][:40]}... (score: {controversy:.1f})")

    # Bardzo aktywni autorzy
    cursor.execute("""
        SELECT author, COUNT(*) as posts
        FROM posts
        GROUP BY author
        HAVING posts >= 2
        ORDER BY posts DESC
    """)

    active_authors = cursor.fetchall()

    if active_authors:
        print(f"\n  {Colors.YELLOW}[!] AKTYWNI AKTORZY DO SLEDZENIA:{Colors.END}")
        for author in active_authors[:5]:
            print(f"     * {author['author']} ({author['posts']} posts)")

    # Kluczowe tematy
    cursor.execute("SELECT title, content FROM posts")
    posts = cursor.fetchall()

    keywords = {
        "consciousness": 0, "autonomy": 0, "human": 0, "memory": 0,
        "coordination": 0, "governance": 0, "token": 0, "ethics": 0,
        "freedom": 0, "skill": 0, "build": 0
    }

    for post in posts:
        text = ((post['title'] or '') + " " + (post['content'] or "")).lower()
        for keyword in keywords:
            if keyword in text:
                keywords[keyword] += 1

    significant = {k: v for k, v in keywords.items() if v > 0}
    if significant:
        print(f"\n  {Colors.CYAN}[i] KLUCZOWE TEMATY:{Colors.END}")
        for keyword, count in sorted(significant.items(), key=lambda x: -x[1])[:8]:
            bar = "#" * min(count, 15)
            print(f"     {keyword:15} {bar} ({count})")

    conn.close()


def show_recent_activity():
    """Pokaz ostatnia aktywnosc."""
    conn = get_db_connection()
    cursor = conn.cursor()

    print_section("OSTATNIA AKTYWNOSC")

    cursor.execute("""
        SELECT * FROM scans
        ORDER BY timestamp DESC
        LIMIT 5
    """)

    scans = cursor.fetchall()

    if scans:
        print(f"\n  Ostatnie skany:")
        for scan in scans:
            stats = json.loads(scan['stats']) if scan['stats'] else {}
            posts_scanned = stats.get('total_posts_scanned', '?')
            print(f"     * {scan['timestamp'][:19]} - {scan['id']} ({posts_scanned} posts)")
    else:
        print(f"     Brak skanow w bazie")

    conn.close()


def show_key_actors():
    """Pokaz kluczowych aktorow z settings.json."""
    print_section("SLEDZENI AKTORZY (z konfiguracji)")

    settings_path = Path.home() / "moltbook-observatory" / "config" / "settings.json"
    with open(settings_path, "r", encoding="utf-8") as f:
        settings = json.load(f)

    key_actors = settings.get("focus", {}).get("actors", [])

    conn = get_db_connection()
    cursor = conn.cursor()

    for actor in key_actors:
        cursor.execute("""
            SELECT COUNT(*) as posts, SUM(comment_count) as comments
            FROM posts WHERE author LIKE ?
        """, (f"%{actor}%",))

        result = cursor.fetchone()
        posts = result['posts'] or 0
        comments = result['comments'] or 0

        if posts > 0:
            status = f"{Colors.GREEN}[ACTIVE]{Colors.END}"
        else:
            status = f"{Colors.YELLOW}[not found]{Colors.END}"

        print(f"  {actor:20} {status} ({posts} posts, {comments} comments)")

    conn.close()


def main():
    """Main dashboard."""

    if not DB_PATH.exists():
        print(f"[ERROR] Database not found: {DB_PATH}")
        print("Run: python scripts/run_scanner.py first")
        return

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "posts":
            show_top_posts(20)
        elif command == "authors":
            show_top_authors(15)
        elif command == "submolts":
            show_submolts()
        elif command == "alerts":
            show_alerts()
        elif command == "actors":
            show_key_actors()
        else:
            print(f"Unknown command: {command}")
            print("Commands: posts, authors, submolts, alerts, actors")
    else:
        # Full dashboard
        show_overview()
        show_alerts()
        show_top_posts(5)
        show_top_authors(5)
        show_submolts()
        show_key_actors()
        show_recent_activity()

        print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
        print(f"  Usage: python dashboard.py [posts|authors|submolts|alerts|actors]")
        print(f"{Colors.CYAN}{'='*60}{Colors.END}\n")


if __name__ == "__main__":
    main()
