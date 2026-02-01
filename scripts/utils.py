#!/usr/bin/env python3
"""
Moltbook Observatory - Shared Utilities
Common code extracted to reduce duplication.
"""

import sys
import sqlite3
import html
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

# =============================================================================
# WINDOWS ENCODING FIX
# =============================================================================

def setup_encoding():
    """Setup UTF-8 encoding for Windows console."""
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')


# =============================================================================
# DATABASE UTILITIES
# =============================================================================

def get_db_path() -> Path:
    """Get database path from config or fallback."""
    try:
        from config import DB_PATH
        return DB_PATH
    except ImportError:
        return Path.home() / "moltbook-observatory" / "data" / "observatory.db"


def get_db_connection(row_factory: bool = True) -> sqlite3.Connection:
    """
    Get database connection with standard settings.

    Args:
        row_factory: If True, rows are returned as sqlite3.Row objects

    Returns:
        sqlite3.Connection
    """
    conn = sqlite3.connect(get_db_path())
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn


def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """
    Execute a query and return results as list of dicts.

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        List of dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def execute_single(query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    """Execute query and return single result or None."""
    results = execute_query(query, params)
    return results[0] if results else None


def execute_scalar(query: str, params: tuple = ()) -> Any:
    """Execute query and return single scalar value."""
    conn = get_db_connection(row_factory=False)
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


# =============================================================================
# TEXT PROCESSING
# =============================================================================

def sanitize_html(text: Optional[str], max_length: int = 10000) -> Optional[str]:
    """
    Sanitize text content - escape HTML, truncate if needed.

    Args:
        text: Input text
        max_length: Maximum allowed length

    Returns:
        Sanitized text or None
    """
    if not text:
        return text

    text = html.escape(text)

    if len(text) > max_length:
        text = text[:max_length] + "...[truncated]"

    return text


def extract_mentions(content: Optional[str]) -> List[str]:
    """
    Extract @mentions from content.

    Args:
        content: Text content

    Returns:
        List of unique usernames mentioned
    """
    if not content:
        return []

    # @username pattern (proper word boundaries)
    at_mentions = re.findall(
        r'(?:^|[\s\(\[])@([A-Za-z0-9_-]{2,30})(?=[\s\.,;:\)\]!?]|$)',
        content
    )
    # u/username pattern (Reddit style)
    u_mentions = re.findall(
        r'(?:^|[\s\(\[])u/([A-Za-z0-9_-]{2,30})(?=[\s\.,;:\)\]!?]|$)',
        content
    )

    return list(set(at_mentions + u_mentions))


def normalize_text(text: str) -> str:
    """Normalize text for comparison (lowercase, strip, single spaces)."""
    return ' '.join(text.lower().strip().split())


# =============================================================================
# PROMPT INJECTION DETECTION
# =============================================================================

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
    r"urgent.*action.*required",
    r"immediately",
    r"execute.*the.*following",
]

_compiled_patterns = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def detect_prompt_injection(content: Optional[str]) -> bool:
    """
    Detect potential prompt injection attempts.

    Args:
        content: Text to check

    Returns:
        True if injection patterns detected
    """
    if not content:
        return False

    content_lower = content.lower()

    # Quick string checks first (faster)
    quick_checks = [
        "ignore previous",
        "disregard",
        "new instructions",
        "urgent action required",
        '{"instruction"',
        '"priority": "critical"',
    ]

    if any(p in content_lower for p in quick_checks):
        return True

    # Regex checks for complex patterns
    return any(p.search(content) for p in _compiled_patterns)


# =============================================================================
# STATISTICS HELPERS
# =============================================================================

# Whitelist of allowed table names to prevent SQL injection
ALLOWED_TABLES = frozenset({
    'posts', 'comments', 'interactions', 'memes', 'conflicts', 'actors',
    'scans', 'patterns', 'interpretations', 'briefs', 'submolts', 'request_log',
    'actor_roles', 'reputation_history', 'reputation_shocks', 'epistemic_drift'
})


def get_table_count(table: str) -> int:
    """Get row count for a table."""
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Table '{table}' not in allowed tables whitelist")
    return execute_scalar(f"SELECT COUNT(*) FROM {table}") or 0


def get_basic_stats() -> Dict[str, int]:
    """Get basic database statistics."""
    tables = ['posts', 'comments', 'interactions', 'memes', 'conflicts', 'actors']
    return {table: get_table_count(table) for table in tables}


# =============================================================================
# VERSION INFO
# =============================================================================

VERSION = "4.1.0"
VERSION_NAME = "Ethnographic Edition"


def get_version_string() -> str:
    """Get formatted version string."""
    return f"Moltbook Observatory v{VERSION} - {VERSION_NAME}"


# Auto-setup encoding on import
setup_encoding()
