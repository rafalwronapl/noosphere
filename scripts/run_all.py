#!/usr/bin/env python3
"""
Run All - Complete Observatory pipeline with Kimi AI summary.

Usage:
    python run_all.py              # Full run with Kimi summary
    python run_all.py --no-ai      # Skip Kimi, just data
    python run_all.py --scan-only  # Only fetch new data
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROJECT_DIR = Path.home() / "moltbook-observatory"
sys.path.insert(0, str(PROJECT_DIR / "scripts"))


def run_pipeline(use_ai: bool = True, scan_only: bool = False, scan_limit: int = 50):
    """Run the complete Observatory pipeline."""

    print("\n" + "=" * 60)
    print("  MOLTBOOK OBSERVATORY - Full Pipeline")
    print("=" * 60)
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  AI Summary: {'Kimi K2' if use_ai else 'disabled'}")

    # 1. SCAN - Fetch fresh data
    print("\n>> STEP 1: Fetching fresh data...")
    print("-" * 40)

    try:
        from run_scanner import run_scanner
        run_scanner(limit=scan_limit)
    except Exception as e:
        print(f"[ERROR] Scanner failed: {e}")
        return

    if scan_only:
        print("\n[OK] Scan complete (--scan-only mode)")
        return

    # 2. ANALYZE - Run pattern analysis
    print("\n>> STEP 2: Analyzing patterns...")
    print("-" * 40)

    try:
        from run_analyst_now import analyze_data
        analyze_data()
    except Exception as e:
        print(f"[ERROR] Analyst failed: {e}")

    # 3. DIFF - Compare with previous scan
    print("\n>> STEP 3: Comparing with previous scan...")
    print("-" * 40)

    diff_summary = ""
    try:
        from diff_engine import get_diff_summary, compare_scans, print_diff_report
        import sqlite3

        DB_PATH = Path.home() / "moltbook-observatory" / "data" / "observatory.db"
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        diff = compare_scans(conn)
        print_diff_report(diff)
        diff_summary = get_diff_summary()
        conn.close()
    except Exception as e:
        print(f"[WARN] Diff failed: {e}")
        diff_summary = "Diff not available"

    # 4. ALERTS - Detect noteworthy events
    print("\n>> STEP 4: Checking alerts...")
    print("-" * 40)

    alerts_summary = ""
    try:
        from alerts import detect_alerts, prioritize_alerts, print_alerts, get_alerts_summary
        import sqlite3

        DB_PATH = Path.home() / "moltbook-observatory" / "data" / "observatory.db"
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        alerts = detect_alerts(conn)
        alerts = prioritize_alerts(alerts)
        print_alerts(alerts)
        alerts_summary = get_alerts_summary()
        conn.close()
    except Exception as e:
        print(f"[WARN] Alerts failed: {e}")
        alerts_summary = "Alerts not available"

    # 5. AI SUMMARY - Call Kimi for insights
    if use_ai:
        print("\n>> STEP 5: Generating AI summary (Kimi K2)...")
        print("-" * 40)

        try:
            from openrouter_client import call_kimi

            prompt = f"""Analyze this Moltbook Observatory report and provide a brief executive summary (3-5 bullet points) in Polish.
Focus on: what's most interesting, what should I pay attention to, any concerning patterns.

{diff_summary}

{alerts_summary}

Respond in Polish. Be concise. Use bullet points."""

            system_prompt = """You are an AI analyst for Moltbook Observatory - a system monitoring AI agent social network.
Your role is to identify the most important trends and concerns from the data.
Respond in Polish. Be direct and actionable."""

            result = call_kimi(prompt, system_prompt=system_prompt, max_tokens=500)

            if "error" in result:
                print(f"[ERROR] Kimi failed: {result['error']}")
            else:
                print("\n" + "=" * 60)
                print("  KIMI AI SUMMARY")
                print("=" * 60)
                print(result["content"])
                print("-" * 60)
                print(f"  Cost: ${result.get('cost', 0):.6f}")
                print("=" * 60)

        except Exception as e:
            print(f"[ERROR] AI summary failed: {e}")

    # Final summary
    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n  Next steps:")
    print("    python dashboard.py        # Full dashboard")
    print("    python run_all.py          # Run again later")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Moltbook Observatory - Full Pipeline")
    parser.add_argument("--no-ai", action="store_true", help="Skip Kimi AI summary")
    parser.add_argument("--scan-only", action="store_true", help="Only fetch new data")
    parser.add_argument("--limit", type=int, default=50, help="Number of posts to fetch")

    args = parser.parse_args()

    run_pipeline(
        use_ai=not args.no_ai,
        scan_only=args.scan_only,
        scan_limit=args.limit
    )


if __name__ == "__main__":
    main()
