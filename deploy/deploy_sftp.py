#!/usr/bin/env python3
"""
SFTP Deployment Script for Moltbook Observatory
Usage: python deploy_sftp.py --host ftp.example.com --user myuser --password mypass --path /public_html/observatory
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Path to website build
WEBSITE_DIST = Path(__file__).parent.parent / "website" / "dist"


def deploy_sftp(host: str, user: str, password: str, remote_path: str):
    """Deploy website via SFTP using scp/sftp commands."""

    if not WEBSITE_DIST.exists():
        print(f"ERROR: Website build not found at {WEBSITE_DIST}")
        print("Run: cd website && npm run build")
        return False

    print(f"Deploying to {user}@{host}:{remote_path}")
    print(f"Source: {WEBSITE_DIST}")

    # Use scp for simplicity (available on Windows with Git)
    # -r = recursive, -o StrictHostKeyChecking=no for first connection
    try:
        # Create remote directory if needed
        cmd_mkdir = [
            "ssh", f"{user}@{host}",
            f"mkdir -p {remote_path}"
        ]

        # Upload files
        cmd_upload = [
            "scp", "-r",
            "-o", "StrictHostKeyChecking=no",
            f"{WEBSITE_DIST}/*",
            f"{user}@{host}:{remote_path}/"
        ]

        print("\nCreating remote directory...")
        # For password auth, we'd need sshpass or expect
        # This script assumes SSH key auth or manual password entry

        print("\nUploading files...")
        print(f"Command: scp -r {WEBSITE_DIST}/* {user}@{host}:{remote_path}/")
        print("\nNote: If prompted for password, enter it manually.")
        print("For automated deployment, set up SSH keys.")

        result = subprocess.run(cmd_upload, shell=True)

        if result.returncode == 0:
            print("\n✓ Deployment successful!")
            return True
        else:
            print(f"\n✗ Deployment failed (exit code {result.returncode})")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Deploy Observatory website via SFTP")
    parser.add_argument("--host", required=True, help="SFTP host (e.g., ftp.home.pl)")
    parser.add_argument("--user", required=True, help="SFTP username")
    parser.add_argument("--password", help="SFTP password (or use SSH key)")
    parser.add_argument("--path", required=True, help="Remote path (e.g., /public_html/observatory)")

    args = parser.parse_args()

    success = deploy_sftp(args.host, args.user, args.password, args.path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
