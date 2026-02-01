#!/usr/bin/env python3
"""Create ZIP archive with all observatory data for download."""

import zipfile
import json
from pathlib import Path
from datetime import datetime

# Paths
BASE_DIR = Path.home() / "moltbook-observatory"
REPORTS_DIR = BASE_DIR / "reports"
DATA_DIR = BASE_DIR / "data"
WEBSITE_PUBLIC = BASE_DIR / "website" / "public"

def create_data_zip(date: str = None):
    """Create ZIP with all data for a given date."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    report_dir = REPORTS_DIR / date
    output_path = WEBSITE_PUBLIC / "reports" / date / "observatory_data.zip"

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    files_to_include = []

    # Daily report
    if (report_dir / "daily_report.md").exists():
        files_to_include.append((report_dir / "daily_report.md", "daily_report.md"))

    # Metadata JSON (archival documentation)
    if (report_dir / "metadata.json").exists():
        files_to_include.append((report_dir / "metadata.json", "metadata.json"))

    # README from report
    if (report_dir / "README.md").exists():
        files_to_include.append((report_dir / "README.md", "README.md"))

    # Stats JSON
    if (report_dir / "stats.json").exists():
        files_to_include.append((report_dir / "stats.json", "stats.json"))

    # Raw data CSVs
    raw_dir = report_dir / "raw"
    if raw_dir.exists():
        for csv_file in raw_dir.glob("*.csv"):
            files_to_include.append((csv_file, f"raw/{csv_file.name}"))

    # Commentary
    commentary_dir = report_dir / "commentary"
    if commentary_dir.exists():
        for md_file in commentary_dir.glob("*.md"):
            files_to_include.append((md_file, f"commentary/{md_file.name}"))

    # Discoveries JSON
    discoveries_path = WEBSITE_PUBLIC / "data" / "discoveries.json"
    if discoveries_path.exists():
        files_to_include.append((discoveries_path, "discoveries.json"))

    # Database (optional - may be large)
    db_path = DATA_DIR / "observatory.db"
    include_db = db_path.exists() and db_path.stat().st_size < 50 * 1024 * 1024  # <50MB

    if not files_to_include:
        print(f"No files found for date {date}")
        return None

    # Create ZIP
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add files (README.md and metadata.json from report dir if exist)
        for src_path, arc_name in files_to_include:
            print(f"  Adding: {arc_name}")
            zf.write(src_path, arc_name)

        # Add database if small enough
        if include_db:
            print(f"  Adding: observatory.db ({db_path.stat().st_size / 1024 / 1024:.1f} MB)")
            zf.write(db_path, "observatory.db")

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"\nCreated: {output_path}")
    print(f"Size: {size_mb:.2f} MB")
    print(f"Files: {len(files_to_include) + 1}")  # +1 for README

    return output_path


if __name__ == "__main__":
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else None
    create_data_zip(date)
