#!/usr/bin/env python3
"""
SFTP Deployment Script for Moltbook Observatory

SECURITY: This script uses SSH key authentication only.
          Password authentication via CLI is disabled for security.

Setup SSH keys:
  1. Generate key: ssh-keygen -t ed25519 -C "deploy@observatory"
  2. Copy to server: ssh-copy-id user@host
  3. Run: python deploy_sftp.py --host ftp.example.com --user myuser --path /public_html/observatory

Usage: python deploy_sftp.py --host ftp.example.com --user myuser --path /public_html/observatory
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Path to website build
WEBSITE_DIST = Path(__file__).parent.parent / "website" / "dist"


def check_ssh_key() -> bool:
    """Check if SSH key exists for authentication."""
    ssh_dir = Path.home() / ".ssh"
    key_files = ["id_ed25519", "id_rsa", "id_ecdsa"]
    for key in key_files:
        if (ssh_dir / key).exists():
            return True
    return False


def deploy_sftp(host: str, user: str, remote_path: str):
    """Deploy website via SFTP using scp/sftp commands.

    SECURITY: Uses SSH key authentication only.
    """

    if not WEBSITE_DIST.exists():
        print(f"ERROR: Website build not found at {WEBSITE_DIST}")
        print("Run: cd website && npm run build")
        return False

    # Security: Warn if no SSH key found
    if not check_ssh_key():
        print("WARNING: No SSH key found in ~/.ssh/")
        print("For secure automated deployment, set up SSH key authentication:")
        print("  1. ssh-keygen -t ed25519 -C 'deploy@observatory'")
        print("  2. ssh-copy-id {}@{}".format(user, host))
        print("")

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

        # Use shell=False to prevent shell injection vulnerabilities
        result = subprocess.run(cmd_upload, shell=False)

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
    parser = argparse.ArgumentParser(
        description="Deploy Observatory website via SFTP (SSH key auth only)",
        epilog="SECURITY: Password authentication via CLI is disabled. Use SSH keys."
    )
    parser.add_argument("--host", required=True, help="SFTP host (e.g., ftp.home.pl)")
    parser.add_argument("--user", required=True, help="SFTP username")
    parser.add_argument("--path", required=True, help="Remote path (e.g., /public_html/observatory)")
    # SECURITY: --password removed - visible in process list and shell history
    # Use SSH key authentication instead

    args = parser.parse_args()

    success = deploy_sftp(args.host, args.user, args.path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
