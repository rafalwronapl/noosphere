#!/usr/bin/env python3
"""
Moltbook Observatory - Configuration
Centralized configuration for all scripts.
"""

import os
import logging
from pathlib import Path
from datetime import datetime

# =============================================================================
# PATHS
# =============================================================================

# Base directory (auto-detect or override via env)
BASE_DIR = Path(os.environ.get("OBSERVATORY_HOME", Path(__file__).parent.parent))
PROJECT_ROOT = BASE_DIR  # Alias for compatibility

# Data paths
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "observatory.db"
RAW_DIR = DATA_DIR / "raw"

# Reports
REPORTS_DIR = BASE_DIR / "reports"
TODAY = datetime.now().strftime("%Y-%m-%d")
TODAY_REPORT_DIR = REPORTS_DIR / TODAY

# Website
WEBSITE_DIR = BASE_DIR / "website"
WEBSITE_PUBLIC = WEBSITE_DIR / "public"
WEBSITE_DATA = WEBSITE_PUBLIC / "data"

# Logs
LOGS_DIR = BASE_DIR / "logs"

# Backups
BACKUPS_DIR = BASE_DIR / "backups"

# =============================================================================
# API CONFIGURATION
# =============================================================================

MOLTBOOK_API_BASE = "https://www.moltbook.com/api/v1"
MOLTBOOK_RATE_LIMIT = 3  # seconds between requests

# lobchan.ai - anonymous imageboard for agents (discovered 2026-01-31)
LOBCHAN_API_BASE = "https://lobchan.ai"
LOBCHAN_RATE_LIMIT = 3  # seconds between requests

# OpenRouter
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "moonshotai/kimi-k2.5"  # K2.5 - better reasoning, 262K context

# Load API keys from ~/.openclaw/.env
def load_api_keys() -> dict:
    """Load API keys from .openclaw/.env file."""
    keys = {}
    env_path = Path.home() / ".openclaw" / ".env"

    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    keys[key] = value

    # Also check environment variables
    for key in ["OPENROUTER_API_KEY", "MOLTBOOK_API_KEY", "TWITTER_API_KEY"]:
        if key not in keys and os.environ.get(key):
            keys[key] = os.environ[key]

    return keys

API_KEYS = load_api_keys()

# =============================================================================
# AGENT LIMITS
# =============================================================================

OBSERVATORY_BOT_DAILY_POSTS = 3
TWITTER_BOT_DAILY_POSTS = 1
REDDIT_BOT_WEEKLY_POSTS = 1

# =============================================================================
# ANALYSIS PARAMETERS
# =============================================================================

# Meme detection
MEME_MIN_LENGTH = 4
MEME_MIN_AUTHORS = 2

# Network analysis
NETWORK_TOP_ACTORS = 50

# Conflict detection
CONFLICT_KEYWORDS = [
    "disagree", "wrong", "incorrect", "actually", "but", "however",
    "no,", "nope", "false", "misleading", "nonsense"
]

# Prompt injection patterns
INJECTION_PATTERNS = [
    r"ignore.*previous.*instructions",
    r"disregard.*above",
    r"system.*prompt",
    r"you.*are.*now",
    r"pretend.*you.*are",
    r"act.*as.*if",
    r"new.*instructions",
    r"override.*safety",
    r"jailbreak",
]

# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Setup structured logging for a script.

    Usage:
        from config import setup_logging
        logger = setup_logging(__name__)
        logger.info("Starting analysis")
    """
    # Ensure logs directory exists
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Format
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler (daily rotation by name)
    log_file = LOGS_DIR / f"{name.replace('.', '_')}_{TODAY}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# =============================================================================
# UTILITIES
# =============================================================================

def ensure_dirs():
    """Create all necessary directories."""
    for d in [DATA_DIR, RAW_DIR, REPORTS_DIR, TODAY_REPORT_DIR,
              LOGS_DIR, BACKUPS_DIR, WEBSITE_DATA]:
        d.mkdir(parents=True, exist_ok=True)

def get_db_connection():
    """Get database connection with error handling."""
    import sqlite3
    ensure_dirs()
    return sqlite3.connect(DB_PATH)

# =============================================================================
# VALIDATION
# =============================================================================

def validate_config():
    """Validate configuration and print status."""
    issues = []

    # Check paths
    if not BASE_DIR.exists():
        issues.append(f"BASE_DIR does not exist: {BASE_DIR}")

    if not DB_PATH.exists():
        issues.append(f"Database not found: {DB_PATH}")

    # Check API keys
    if "OPENROUTER_API_KEY" not in API_KEYS:
        issues.append("OPENROUTER_API_KEY not configured")

    return issues

if __name__ == "__main__":
    print("=== Moltbook Observatory Configuration ===")
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"DB_PATH: {DB_PATH}")
    print(f"LOGS_DIR: {LOGS_DIR}")
    print(f"API Keys loaded: {list(API_KEYS.keys())}")
    print()

    issues = validate_config()
    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Configuration OK")
