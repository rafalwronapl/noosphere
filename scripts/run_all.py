#!/usr/bin/env python3
"""
Run All - Complete Observatory pipeline with Kimi AI summary.

Usage:
    python run_all.py              # Full run with Kimi summary
    python run_all.py --no-ai      # Skip Kimi, just data
    python run_all.py --scan-only  # Only fetch new data
    python run_all.py --continue   # Continue even if steps fail
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Use centralized config
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from config import DB_PATH, setup_logging

logger = setup_logging("run_all")


class PipelineError(Exception):
    """Error during pipeline execution."""
    pass


def run_pipeline(use_ai: bool = True, scan_only: bool = False, scan_limit: int = 50,
                 continue_on_error: bool = False) -> bool:
    """Run the complete Observatory pipeline.

    Args:
        use_ai: Enable Kimi AI summary
        scan_only: Only fetch data, skip analysis
        scan_limit: Number of posts to fetch
        continue_on_error: Continue pipeline even if critical steps fail

    Returns:
        True if pipeline completed successfully, False otherwise
    """
    errors = []

    print("\n" + "=" * 60)
    print("  MOLTBOOK OBSERVATORY - Full Pipeline")
    print("=" * 60)
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  AI Summary: {'Kimi K2' if use_ai else 'disabled'}")

    # 1. SCAN - Fetch fresh data (CRITICAL - must succeed)
    print("\n>> STEP 1: Fetching fresh data...")
    print("-" * 40)

    try:
        from run_scanner import run_scanner
        run_scanner(limit=scan_limit)
    except Exception as e:
        error_msg = f"Scanner failed: {e}"
        print(f"[ERROR] {error_msg}")
        logger.error(error_msg)
        errors.append(("CRITICAL", "Scanner", str(e)))
        if not continue_on_error:
            print("\n[FATAL] Cannot continue without fresh data. Use --continue to force.")
            return False

    if scan_only:
        print("\n[OK] Scan complete (--scan-only mode)")
        return len(errors) == 0

    # 2. ANALYZE - Run pattern analysis (CRITICAL - needed for insights)
    print("\n>> STEP 2: Analyzing patterns...")
    print("-" * 40)

    try:
        from run_analyst_now import analyze_data
        analyze_data()
    except Exception as e:
        error_msg = f"Analyst failed: {e}"
        print(f"[ERROR] {error_msg}")
        logger.error(error_msg)
        errors.append(("CRITICAL", "Analyst", str(e)))
        if not continue_on_error:
            print("\n[FATAL] Analysis failed. Results may be stale. Use --continue to force.")
            return False

    # 3. DIFF - Compare with previous scan (non-critical)
    print("\n>> STEP 3: Comparing with previous scan...")
    print("-" * 40)

    diff_summary = ""
    try:
        from diff_engine import get_diff_summary, compare_scans, print_diff_report
        import sqlite3

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        diff = compare_scans(conn)
        print_diff_report(diff)
        diff_summary = get_diff_summary()
        conn.close()
    except Exception as e:
        print(f"[WARN] Diff failed: {e}")
        logger.warning(f"Diff failed: {e}")
        errors.append(("WARN", "Diff", str(e)))
        diff_summary = "Diff not available"

    # 4. ALERTS - Detect noteworthy events (non-critical)
    print("\n>> STEP 4: Checking alerts...")
    print("-" * 40)

    alerts_summary = ""
    try:
        from alerts import detect_alerts, prioritize_alerts, print_alerts, get_alerts_summary
        import sqlite3

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        alerts = detect_alerts(conn)
        alerts = prioritize_alerts(alerts)
        print_alerts(alerts)
        alerts_summary = get_alerts_summary()
        conn.close()
    except Exception as e:
        print(f"[WARN] Alerts failed: {e}")
        logger.warning(f"Alerts failed: {e}")
        errors.append(("WARN", "Alerts", str(e)))
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

    # Report errors if any
    if errors:
        print("\n  Errors encountered:")
        critical_count = 0
        for level, step, msg in errors:
            print(f"    [{level}] {step}: {msg}")
            if level == "CRITICAL":
                critical_count += 1
        if critical_count > 0:
            print(f"\n  WARNING: {critical_count} critical error(s) occurred!")
            logger.error(f"Pipeline completed with {critical_count} critical errors")
    else:
        print("\n  Status: All steps completed successfully")

    print("\n  Next steps:")
    print("    python dashboard.py        # Full dashboard")
    print("    python run_all.py          # Run again later")
    print("=" * 60 + "\n")

    return len([e for e in errors if e[0] == "CRITICAL"]) == 0


def main():
    parser = argparse.ArgumentParser(description="Moltbook Observatory - Full Pipeline")
    parser.add_argument("--no-ai", action="store_true", help="Skip Kimi AI summary")
    parser.add_argument("--scan-only", action="store_true", help="Only fetch new data")
    parser.add_argument("--limit", type=int, default=50, help="Number of posts to fetch")
    parser.add_argument("--continue", dest="continue_on_error", action="store_true",
                        help="Continue pipeline even if critical steps fail")

    args = parser.parse_args()

    success = run_pipeline(
        use_ai=not args.no_ai,
        scan_only=args.scan_only,
        scan_limit=args.limit,
        continue_on_error=args.continue_on_error
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
