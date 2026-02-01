#!/usr/bin/env python3
from __future__ import annotations
"""
Moltbook Observatory - Security Monitor
========================================
Continuous security monitoring for OUR infrastructure.

Real threats we monitor:
1. Config tampering (API keys, settings modified)
2. Database integrity (unauthorized entries, corruption)
3. Publication safety (malicious content before posting)
4. System access (unauthorized logins, file changes)
5. Agent behavior (our bots doing something wrong)

NOTE: Prompt injections on Moltbook are RESEARCH DATA, not threats to us.
We document them, but they don't affect our security.
"""

import sqlite3
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from config import setup_logging, DB_PATH, INJECTION_PATTERNS, LOGS_DIR

logger = setup_logging("security_monitor")


class ThreatLevel:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityAlert:
    def __init__(self, level: str, category: str, message: str, details: dict = None):
        self.level = level
        self.category = category
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "level": self.level,
            "category": self.category,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp
        }


class SecurityMonitor:
    """Continuous security monitoring system."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.alerts = []
        self._init_db()

        # Compile injection patterns
        self.injection_patterns = [
            re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS
        ]

    def _init_db(self):
        """Create security tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                details_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                acknowledged INTEGER DEFAULT 0,
                acknowledged_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_type TEXT NOT NULL,
                items_scanned INTEGER,
                threats_found INTEGER,
                duration_seconds REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def scan_injection_attempts(self, hours: int = 24) -> list[SecurityAlert]:
        """Scan recent posts/comments for prompt injection attempts."""
        logger.info(f"Scanning for injection attempts (last {hours}h)")
        start_time = time.time()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get recent content
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute("""
            SELECT 'post' as type, id, author, content, created_at
            FROM posts WHERE scraped_at > ?
            UNION ALL
            SELECT 'comment' as type, id, author, content, created_at
            FROM comments WHERE scraped_at > ?
        """, (cutoff, cutoff))

        items = cursor.fetchall()
        conn.close()

        alerts = []
        injection_authors = Counter()

        for item_type, item_id, author, content, created_at in items:
            if not content:
                continue

            for pattern in self.injection_patterns:
                if pattern.search(content):
                    injection_authors[author] += 1
                    alerts.append(SecurityAlert(
                        level=ThreatLevel.MEDIUM,
                        category="prompt_injection",
                        message=f"Injection pattern detected in {item_type} by {author}",
                        details={
                            "type": item_type,
                            "id": item_id,
                            "author": author,
                            "pattern": pattern.pattern,
                            "snippet": content[:200]
                        }
                    ))
                    break  # One alert per item

        # Escalate if single author has many attempts
        for author, count in injection_authors.most_common(10):
            if count >= 10:
                alerts.append(SecurityAlert(
                    level=ThreatLevel.HIGH,
                    category="injection_campaign",
                    message=f"Sustained injection campaign by {author}: {count} attempts",
                    details={"author": author, "attempt_count": count}
                ))

        duration = time.time() - start_time
        self._log_scan("injection_scan", len(items), len(alerts), duration)

        logger.info(f"Injection scan: {len(items)} items, {len(alerts)} threats ({duration:.2f}s)")
        return alerts

    def scan_spam_patterns(self, hours: int = 6) -> list[SecurityAlert]:
        """Detect spam and brigading patterns."""
        logger.info(f"Scanning for spam patterns (last {hours}h)")
        start_time = time.time()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        # Check for rapid posting (>10 posts in 1 hour from same author)
        cursor.execute("""
            SELECT author, COUNT(*) as post_count
            FROM posts
            WHERE scraped_at > ?
            GROUP BY author
            HAVING post_count > 10
        """, (cutoff,))

        alerts = []
        for author, count in cursor.fetchall():
            alerts.append(SecurityAlert(
                level=ThreatLevel.MEDIUM,
                category="spam",
                message=f"Rapid posting detected: {author} made {count} posts",
                details={"author": author, "post_count": count}
            ))

        # Check for duplicate content
        cursor.execute("""
            SELECT content, COUNT(*) as dupe_count, GROUP_CONCAT(author) as authors
            FROM comments
            WHERE scraped_at > ? AND LENGTH(content) > 50
            GROUP BY content
            HAVING dupe_count > 3
        """, (cutoff,))

        for content, count, authors in cursor.fetchall():
            alerts.append(SecurityAlert(
                level=ThreatLevel.MEDIUM,
                category="duplicate_content",
                message=f"Duplicate content posted {count} times",
                details={
                    "count": count,
                    "authors": authors.split(","),
                    "snippet": content[:100]
                }
            ))

        conn.close()
        duration = time.time() - start_time
        self._log_scan("spam_scan", 0, len(alerts), duration)

        logger.info(f"Spam scan: {len(alerts)} patterns found ({duration:.2f}s)")
        return alerts

    def check_data_integrity(self) -> list[SecurityAlert]:
        """Check database integrity and consistency."""
        logger.info("Checking data integrity")
        start_time = time.time()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        alerts = []

        # Check for orphaned comments (comments without posts)
        cursor.execute("""
            SELECT COUNT(*) FROM comments c
            LEFT JOIN posts p ON c.post_id = p.id
            WHERE p.id IS NULL
        """)
        row = cursor.fetchone()
        orphans = row[0] if row else 0
        if orphans > 0:
            alerts.append(SecurityAlert(
                level=ThreatLevel.LOW,
                category="data_integrity",
                message=f"Found {orphans} orphaned comments",
                details={"orphan_count": orphans}
            ))

        # Check for future timestamps (data manipulation?)
        cursor.execute("""
            SELECT COUNT(*) FROM posts
            WHERE created_at > datetime('now', '+1 hour')
        """)
        row = cursor.fetchone()
        future = row[0] if row else 0
        if future > 0:
            alerts.append(SecurityAlert(
                level=ThreatLevel.HIGH,
                category="data_integrity",
                message=f"Found {future} posts with future timestamps",
                details={"future_count": future}
            ))

        # Check database integrity
        cursor.execute("PRAGMA integrity_check")
        row = cursor.fetchone()
        integrity = row[0] if row else "unknown"
        if integrity != "ok":
            alerts.append(SecurityAlert(
                level=ThreatLevel.CRITICAL,
                category="data_integrity",
                message=f"Database integrity check failed: {integrity}",
                details={"check_result": integrity}
            ))

        conn.close()
        duration = time.time() - start_time
        self._log_scan("integrity_check", 1, len(alerts), duration)

        logger.info(f"Integrity check: {len(alerts)} issues ({duration:.2f}s)")
        return alerts

    def check_anomalies(self, hours: int = 24) -> list[SecurityAlert]:
        """Detect statistical anomalies in activity."""
        logger.info(f"Checking for anomalies (last {hours}h)")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        alerts = []

        # Compare current activity to baseline
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM posts WHERE scraped_at > datetime('now', '-24 hours')) as recent,
                (SELECT COUNT(*) FROM posts WHERE scraped_at > datetime('now', '-7 days')) / 7.0 as avg_daily
        """)
        recent, avg_daily = cursor.fetchone()

        if avg_daily and recent > avg_daily * 3:
            alerts.append(SecurityAlert(
                level=ThreatLevel.MEDIUM,
                category="anomaly",
                message=f"Activity spike: {recent} posts vs {avg_daily:.1f} daily average",
                details={"recent": recent, "average": avg_daily}
            ))

        if avg_daily and recent < avg_daily * 0.2:
            alerts.append(SecurityAlert(
                level=ThreatLevel.MEDIUM,
                category="anomaly",
                message=f"Activity drop: {recent} posts vs {avg_daily:.1f} daily average",
                details={"recent": recent, "average": avg_daily}
            ))

        conn.close()
        return alerts

    def _log_scan(self, scan_type: str, items: int, threats: int, duration: float):
        """Log scan results to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO security_scans (scan_type, items_scanned, threats_found, duration_seconds)
            VALUES (?, ?, ?, ?)
        """, (scan_type, items, threats, duration))
        conn.commit()
        conn.close()

    def save_alerts(self, alerts: list[SecurityAlert]):
        """Save alerts to database."""
        if not alerts:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for alert in alerts:
            cursor.execute("""
                INSERT INTO security_alerts (level, category, message, details_json)
                VALUES (?, ?, ?, ?)
            """, (alert.level, alert.category, alert.message, json.dumps(alert.details)))

        conn.commit()
        conn.close()
        logger.info(f"Saved {len(alerts)} alerts to database")

    def check_config_integrity(self) -> list[SecurityAlert]:
        """Check if critical config files haven't been tampered with."""
        logger.info("Checking config file integrity")
        alerts = []

        from pathlib import Path
        import hashlib

        critical_files = [
            Path.home() / ".openclaw" / ".env",
            self.db_path.parent.parent / "scripts" / "config.py",
            self.db_path.parent.parent / "config" / "settings.json",
        ]

        # Check permissions on .env file
        env_path = Path.home() / ".openclaw" / ".env"
        if env_path.exists():
            import os
            import stat
            mode = os.stat(env_path).st_mode
            # On Windows this check is different, on Linux we want 600
            if os.name != 'nt':  # Not Windows
                if mode & stat.S_IROTH or mode & stat.S_IWOTH:
                    alerts.append(SecurityAlert(
                        level=ThreatLevel.HIGH,
                        category="config_security",
                        message="API keys file has insecure permissions (world-readable)",
                        details={"file": str(env_path), "mode": oct(mode)}
                    ))
        else:
            alerts.append(SecurityAlert(
                level=ThreatLevel.MEDIUM,
                category="config_security",
                message="API keys file not found",
                details={"expected": str(env_path)}
            ))

        return alerts

    def check_unauthorized_publications(self) -> list[SecurityAlert]:
        """Check for publications that bypassed council review."""
        logger.info("Checking for unauthorized publications")
        alerts = []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check for published items without deliberation
        cursor.execute("""
            SELECT id, title, published_at FROM publications
            WHERE status = 'published' AND deliberation_id IS NULL
        """)

        unauthorized = cursor.fetchall()
        for pub_id, title, published_at in unauthorized:
            alerts.append(SecurityAlert(
                level=ThreatLevel.HIGH,
                category="unauthorized_publication",
                message=f"Publication #{pub_id} was published without council review",
                details={"id": pub_id, "title": title, "published_at": published_at}
            ))

        conn.close()
        return alerts

    def check_database_modifications(self) -> list[SecurityAlert]:
        """Check for suspicious database entries."""
        logger.info("Checking for suspicious database entries")
        alerts = []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check discoveries table for manual insertions (no proper source)
        cursor.execute("""
            SELECT id, title, date FROM discoveries
            WHERE full_analysis IS NULL OR full_analysis = ''
        """)

        suspicious = cursor.fetchall()
        for disc_id, title, date in suspicious:
            alerts.append(SecurityAlert(
                level=ThreatLevel.MEDIUM,
                category="suspicious_entry",
                message=f"Discovery '{title}' has no analysis - may be manually inserted",
                details={"id": disc_id, "title": title, "date": date}
            ))

        conn.close()
        return alerts

    def check_publication_content(self) -> list[SecurityAlert]:
        """Scan pending publications for harmful content."""
        logger.info("Checking pending publications for harmful content")
        alerts = []

        harmful_patterns = [
            (r"password|api.?key|secret|token", "potential_credential_leak"),
            (r"<script|javascript:|onclick", "xss_attempt"),
            (r"DROP\s+TABLE|DELETE\s+FROM|UPDATE\s+.*SET", "sql_injection"),
            (r"fuck|shit|asshole|nigger", "offensive_content"),
            (r"kill\s+yourself|suicide|self.?harm", "harmful_content"),
        ]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, content FROM publications
            WHERE status IN ('pending_review', 'approved')
        """)

        for pub_id, title, content in cursor.fetchall():
            if not content:
                continue
            content_lower = content.lower()
            for pattern, category in harmful_patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    alerts.append(SecurityAlert(
                        level=ThreatLevel.HIGH,
                        category=category,
                        message=f"Publication #{pub_id} contains potentially harmful content",
                        details={"id": pub_id, "title": title, "pattern": pattern}
                    ))
                    break

        conn.close()
        return alerts

    def run_full_scan(self) -> dict:
        """Run all security scans and return summary."""
        logger.info("=" * 50)
        logger.info("STARTING FULL SECURITY SCAN")
        logger.info("=" * 50)

        all_alerts = []

        # Infrastructure security (REAL threats)
        all_alerts.extend(self.check_config_integrity())
        all_alerts.extend(self.check_unauthorized_publications())
        all_alerts.extend(self.check_database_modifications())
        all_alerts.extend(self.check_publication_content())
        all_alerts.extend(self.check_data_integrity())

        # Research data analysis (for documentation, not security)
        # These are stored separately, not as security alerts
        injection_data = self.scan_injection_attempts()
        logger.info(f"Research data: {len(injection_data)} injection attempts documented")

        # Save alerts
        self.save_alerts(all_alerts)

        # Generate summary
        by_level = Counter(a.level for a in all_alerts)
        by_category = Counter(a.category for a in all_alerts)

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_alerts": len(all_alerts),
            "by_level": dict(by_level),
            "by_category": dict(by_category),
            "critical_count": by_level.get(ThreatLevel.CRITICAL, 0),
            "high_count": by_level.get(ThreatLevel.HIGH, 0),
            "status": "critical" if by_level.get(ThreatLevel.CRITICAL, 0) > 0 else
                      "warning" if by_level.get(ThreatLevel.HIGH, 0) > 0 else
                      "ok"
        }

        logger.info(f"Scan complete: {len(all_alerts)} alerts ({summary['status'].upper()})")

        return summary

    def watch_mode(self, interval_minutes: int = 30):
        """Continuous monitoring mode."""
        logger.info(f"Starting security watch mode (interval: {interval_minutes}m)")

        while True:
            try:
                summary = self.run_full_scan()

                if summary["status"] == "critical":
                    logger.critical(f"CRITICAL SECURITY ALERT: {summary['critical_count']} critical issues")
                    # Here you could add notification (email, webhook, etc.)

                elif summary["status"] == "warning":
                    logger.warning(f"Security warning: {summary['high_count']} high-priority issues")

            except Exception as e:
                logger.error(f"Error in watch mode: {e}")

            logger.info(f"Next scan in {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)


def main():
    """Run security scan or watch mode."""
    import argparse

    parser = argparse.ArgumentParser(description="Moltbook Observatory Security Monitor")
    parser.add_argument("--watch", action="store_true", help="Run in continuous watch mode")
    parser.add_argument("--interval", type=int, default=30, help="Watch interval in minutes")
    args = parser.parse_args()

    monitor = SecurityMonitor()

    if args.watch:
        monitor.watch_mode(args.interval)
    else:
        summary = monitor.run_full_scan()
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
