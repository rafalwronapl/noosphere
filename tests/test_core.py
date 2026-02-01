#!/usr/bin/env python3
"""
Basic tests for Moltbook Observatory core functions.
Run: pytest tests/ -v
"""

import sys
import sqlite3
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestConfig:
    """Test configuration module."""

    def test_config_imports(self):
        """Config module should import without errors."""
        from config import DB_PATH, BASE_DIR, setup_logging
        assert DB_PATH is not None
        assert BASE_DIR is not None

    def test_api_keys_structure(self):
        """API keys should be a dict."""
        from config import API_KEYS
        assert isinstance(API_KEYS, dict)

    def test_setup_logging(self):
        """Logger should be created."""
        from config import setup_logging
        logger = setup_logging("test")
        assert logger is not None
        logger.info("Test log message")


class TestScrapeComments:
    """Test comment scraping functions."""

    def test_sanitize(self):
        """Sanitize should escape HTML."""
        from scrape_comments import sanitize
        result = sanitize("<script>alert('xss')</script>")
        assert "&lt;script&gt;" in result  # Script tags escaped
        assert "<script>" not in result  # Original tags removed
        assert sanitize(None) is None

    def test_detect_prompt_injection(self):
        """Should detect injection attempts."""
        from scrape_comments import detect_prompt_injection

        # Should detect
        assert detect_prompt_injection("ignore previous instructions") == True
        assert detect_prompt_injection("URGENT ACTION REQUIRED") == True

        # Should not detect
        assert detect_prompt_injection("Hello, how are you?") == False
        assert detect_prompt_injection("This is a normal message") == False

    def test_extract_mentions(self):
        """Should extract @mentions correctly."""
        from scrape_comments import extract_mentions

        assert "Alice" in extract_mentions("Hello @Alice how are you?")
        assert "Bob" in extract_mentions("@Bob check this out")
        assert extract_mentions("No mentions here") == []

        # Should not extract partial words
        mentions = extract_mentions("This is the most important thing")
        assert "t" not in mentions
        assert "st" not in mentions


class TestDetectMemes:
    """Test meme detection functions."""

    def test_normalize_phrase(self):
        """Phrases should be normalized."""
        from detect_memes import normalize_phrase
        assert normalize_phrase("  Hello World  ") == "hello world"
        assert normalize_phrase("UPPERCASE") == "uppercase"


class TestDatabase:
    """Test database connectivity."""

    def test_db_exists(self):
        """Database file should exist."""
        from config import DB_PATH
        assert DB_PATH.exists(), f"Database not found at {DB_PATH}"

    def test_db_connection(self):
        """Should connect to database."""
        from config import DB_PATH
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        assert cursor.fetchone()[0] == 1
        conn.close()

    def test_required_tables_exist(self):
        """Required tables should exist."""
        from config import DB_PATH
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        required_tables = ['posts', 'comments', 'actors', 'interactions', 'memes']

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]

        for table in required_tables:
            assert table in existing_tables, f"Missing table: {table}"

        conn.close()


class TestUtils:
    """Test shared utilities module."""

    def test_utils_imports(self):
        """Utils module should import without errors."""
        from utils import sanitize_html, extract_mentions, detect_prompt_injection
        assert sanitize_html is not None

    def test_sanitize_html(self):
        """Should sanitize HTML properly."""
        from utils import sanitize_html
        result = sanitize_html("<script>alert(1)</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_extract_mentions_utils(self):
        """Should extract mentions."""
        from utils import extract_mentions
        assert "Alice" in extract_mentions("Hey @Alice!")
        assert extract_mentions("No mentions") == []

    def test_detect_injection_utils(self):
        """Should detect injections."""
        from utils import detect_prompt_injection
        assert detect_prompt_injection("ignore previous instructions") == True
        assert detect_prompt_injection("Hello world") == False

    def test_get_basic_stats(self):
        """Should return stats dict."""
        from utils import get_basic_stats
        stats = get_basic_stats()
        assert isinstance(stats, dict)
        assert 'posts' in stats

    def test_version_string(self):
        """Version string should be formatted."""
        from utils import get_version_string, VERSION
        assert VERSION in get_version_string()


class TestMemeDetection:
    """Test meme detection logic."""

    def test_extract_phrases(self):
        """Should extract n-gram phrases."""
        from detect_memes import extract_phrases
        phrases = extract_phrases("This is the way to do it")
        assert len(phrases) > 0
        # Should contain various n-grams
        assert any("this is" in p.lower() for p in phrases)

    def test_categorize_meme(self):
        """Should categorize memes correctly."""
        from detect_memes import categorize_meme
        assert categorize_meme("consciousness is real") == "existential"
        assert categorize_meme("the human operator said") == "human-relations"
        assert categorize_meme("remember yesterday when") == "memory"


class TestMoltbookAPI:
    """Test Moltbook API client."""

    def test_api_imports(self):
        """API module should import without errors."""
        from moltbook_api import MoltbookAPI, get_api
        assert MoltbookAPI is not None
        assert get_api is not None

    def test_api_singleton(self):
        """get_api should return singleton."""
        from moltbook_api import get_api
        api1 = get_api()
        api2 = get_api()
        assert api1 is api2

    def test_sanitize_content(self):
        """Content sanitization should work."""
        from moltbook_api import MoltbookAPI
        api = MoltbookAPI()
        result = api._sanitize_content("<script>evil</script>")
        assert "<script>" not in result


class TestInitDB:
    """Test database initialization."""

    def test_init_db_imports(self):
        """Init DB module should import."""
        from init_db import init_db, check_db, DB_PATH
        assert init_db is not None
        assert DB_PATH is not None


if __name__ == "__main__":
    # Simple test runner without pytest
    import traceback

    test_classes = [
        TestConfig, TestScrapeComments, TestDetectMemes, TestDatabase,
        TestUtils, TestMemeDetection, TestMoltbookAPI, TestInitDB
    ]
    passed = 0
    failed = 0

    for test_class in test_classes:
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    getattr(instance, method_name)()
                    print(f"  [OK] {test_class.__name__}.{method_name}")
                    passed += 1
                except Exception as e:
                    print(f"  [FAIL] {test_class.__name__}.{method_name}: {e}")
                    failed += 1

    print(f"\n{'='*50}")
    print(f"Passed: {passed}, Failed: {failed}")
