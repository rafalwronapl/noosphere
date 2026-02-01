#!/usr/bin/env python3
"""
Database Backup Script for Moltbook Observatory

Creates timestamped backups of the SQLite database with rotation.
Keeps last N backups and optionally compresses them.

Usage:
    python backup_db.py                    # Create backup
    python backup_db.py --keep 7           # Keep only last 7 backups
    python backup_db.py --compress         # Compress backup with gzip
    python backup_db.py --restore latest   # Restore latest backup
    python backup_db.py --list             # List available backups
"""

import sys
import shutil
import gzip
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import DB_PATH, BACKUPS_DIR, setup_logging

logger = setup_logging("backup")


def ensure_backup_dir():
    """Ensure backup directory exists."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


def get_backup_name(compress: bool = False) -> str:
    """Generate backup filename with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".db.gz" if compress else ".db"
    return f"observatory_backup_{timestamp}{ext}"


def list_backups() -> list:
    """List all available backups sorted by date (newest first)."""
    ensure_backup_dir()
    backups = []

    for f in BACKUPS_DIR.glob("observatory_backup_*"):
        stat = f.stat()
        backups.append({
            "path": f,
            "name": f.name,
            "size_mb": stat.st_size / (1024 * 1024),
            "created": datetime.fromtimestamp(stat.st_mtime)
        })

    return sorted(backups, key=lambda x: x["created"], reverse=True)


def create_backup(compress: bool = False) -> Path:
    """Create a new backup of the database."""
    ensure_backup_dir()

    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    backup_name = get_backup_name(compress)
    backup_path = BACKUPS_DIR / backup_name

    logger.info(f"Creating backup: {backup_name}")

    if compress:
        # Compressed backup
        with open(DB_PATH, 'rb') as f_in:
            with gzip.open(backup_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    else:
        # Simple copy
        shutil.copy2(DB_PATH, backup_path)

    size_mb = backup_path.stat().st_size / (1024 * 1024)
    logger.info(f"Backup created: {backup_path} ({size_mb:.2f} MB)")

    return backup_path


def rotate_backups(keep: int = 10):
    """Remove old backups, keeping only the most recent N."""
    backups = list_backups()

    if len(backups) <= keep:
        logger.info(f"No rotation needed ({len(backups)} backups, keeping {keep})")
        return

    to_delete = backups[keep:]

    for backup in to_delete:
        logger.info(f"Deleting old backup: {backup['name']}")
        backup["path"].unlink()

    logger.info(f"Rotation complete: deleted {len(to_delete)} old backups")


def restore_backup(backup_name: str = "latest") -> bool:
    """Restore database from a backup.

    Args:
        backup_name: Backup filename or "latest" for most recent

    Returns:
        True if successful
    """
    backups = list_backups()

    if not backups:
        logger.error("No backups available")
        return False

    if backup_name == "latest":
        backup = backups[0]
    else:
        backup = next((b for b in backups if b["name"] == backup_name), None)
        if not backup:
            logger.error(f"Backup not found: {backup_name}")
            return False

    backup_path = backup["path"]
    logger.info(f"Restoring from: {backup['name']}")

    # Create a backup of current DB before restoring
    if DB_PATH.exists():
        pre_restore_backup = DB_PATH.with_suffix(".db.pre_restore")
        shutil.copy2(DB_PATH, pre_restore_backup)
        logger.info(f"Current DB backed up to: {pre_restore_backup.name}")

    # Restore
    if backup_path.suffix == ".gz":
        with gzip.open(backup_path, 'rb') as f_in:
            with open(DB_PATH, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    else:
        shutil.copy2(backup_path, DB_PATH)

    logger.info(f"Database restored from {backup['name']}")
    return True


def print_backup_list():
    """Print formatted list of backups."""
    backups = list_backups()

    if not backups:
        print("No backups found.")
        return

    print(f"\n{'Backup Name':<45} {'Size':>10} {'Created':<20}")
    print("-" * 75)

    for b in backups:
        print(f"{b['name']:<45} {b['size_mb']:>8.2f} MB  {b['created'].strftime('%Y-%m-%d %H:%M:%S')}")

    total_size = sum(b["size_mb"] for b in backups)
    print("-" * 75)
    print(f"Total: {len(backups)} backups, {total_size:.2f} MB")


def main():
    parser = argparse.ArgumentParser(description="Database Backup Manager")
    parser.add_argument("--compress", "-c", action="store_true",
                        help="Compress backup with gzip")
    parser.add_argument("--keep", "-k", type=int, default=10,
                        help="Number of backups to keep (default: 10)")
    parser.add_argument("--restore", "-r", nargs="?", const="latest",
                        help="Restore from backup (default: latest)")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List available backups")
    parser.add_argument("--no-rotate", action="store_true",
                        help="Skip rotation after backup")

    args = parser.parse_args()

    if args.list:
        print_backup_list()
        return

    if args.restore:
        success = restore_backup(args.restore)
        sys.exit(0 if success else 1)

    # Default: create backup
    try:
        backup_path = create_backup(compress=args.compress)
        print(f"Backup created: {backup_path}")

        if not args.no_rotate:
            rotate_backups(keep=args.keep)

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
