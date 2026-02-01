#!/usr/bin/env python3
"""
Noosphere Project - Deployment Script
======================================
Automates the full deployment pipeline:
1. Run scanner to fetch new data
2. Generate dashboard data
3. Generate feeds
4. Commit and push changes

Usage:
    python deploy.py              # Full deploy
    python deploy.py --no-scan    # Skip scanning (just regenerate)
    python deploy.py --no-push    # Don't push to git
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def run_command(cmd: list, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"[STEP] {description}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=False,
            text=True
        )
        if result.returncode != 0:
            print(f"[WARN] {description} returned code {result.returncode}")
            return False
        return True
    except Exception as e:
        print(f"[ERROR] {description}: {e}")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Deploy Noosphere Observatory")
    parser.add_argument("--no-scan", action="store_true", help="Skip data scanning")
    parser.add_argument("--no-push", action="store_true", help="Don't push to git")
    parser.add_argument("--lobchan", action="store_true", help="Also scrape lobchan")
    args = parser.parse_args()

    print("=" * 60)
    print("NOOSPHERE OBSERVATORY - DEPLOYMENT")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    steps_run = 0
    steps_failed = 0

    # Step 1: Scan Moltbook
    if not args.no_scan:
        if run_command(
            [sys.executable, str(SCRIPTS_DIR / "run_scanner.py")],
            "Scanning Moltbook for new posts"
        ):
            steps_run += 1
        else:
            steps_failed += 1

    # Step 1b: Scan lobchan (optional)
    if args.lobchan:
        if run_command(
            [sys.executable, str(SCRIPTS_DIR / "scrape_lobchan.py"), "full"],
            "Scanning lobchan.ai"
        ):
            steps_run += 1
        else:
            steps_failed += 1

    # Step 2: Generate dashboard data
    if run_command(
        [sys.executable, str(SCRIPTS_DIR / "generate_dashboard_data.py")],
        "Generating dashboard JSON"
    ):
        steps_run += 1
    else:
        steps_failed += 1

    # Step 3: Generate feeds
    if run_command(
        [sys.executable, str(SCRIPTS_DIR / "generate_feeds.py")],
        "Generating RSS/Atom/JSON feeds"
    ):
        steps_run += 1
    else:
        steps_failed += 1

    # Step 4: Git operations
    if not args.no_push:
        # Check for changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )

        if result.stdout.strip():
            # Stage data files
            run_command(
                ["git", "add",
                 "website/public/data/",
                 "website/public/feeds/",
                 "website/public/reports/"],
                "Staging data files"
            )

            # Commit
            commit_msg = f"Auto-deploy: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            if run_command(
                ["git", "commit", "-m", commit_msg],
                "Committing changes"
            ):
                steps_run += 1

                # Push
                if run_command(["git", "push"], "Pushing to GitHub"):
                    steps_run += 1
                else:
                    steps_failed += 1
            else:
                steps_failed += 1
        else:
            print("\n[INFO] No changes to commit")

    # Summary
    print("\n" + "=" * 60)
    print("DEPLOYMENT COMPLETE")
    print("=" * 60)
    print(f"Steps completed: {steps_run}")
    print(f"Steps failed: {steps_failed}")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return 0 if steps_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
