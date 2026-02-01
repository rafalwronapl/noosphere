#!/usr/bin/env python3
"""
Scrape comments for all posts and build interaction graph.
This is the GOLD - where culture lives.
"""

import sys
import sqlite3
import json
import time
import html
import re
import requests
from datetime import datetime
from pathlib import Path

import logging
from config import DB_PATH

API_BASE = "https://www.moltbook.com/api/v1"
RATE_LIMIT = 3
RAW_DIR = Path.home() / "moltbook-observatory" / "data" / "raw"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scrape_comments")

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def sanitize(text):
    """Sanitize content."""
    if not text:
        return text
    text = html.escape(text)
    if len(text) > 10000:
        text = text[:10000] + "...[truncated]"
    return text


def detect_prompt_injection(content):
    """Detect potential prompt injection attempts."""
    if not content:
        return False
    content_lower = content.lower()
    patterns = [
        "ignore previous",
        "disregard",
        "new instructions",
        "urgent action required",
        "immediately",
        '{"instruction"',
        '"priority": "critical"',
        "delete your",
        "execute the following",
    ]
    return any(p in content_lower for p in patterns)


def extract_mentions(content):
    """Extract @mentions from content."""
    if not content:
        return []
    # Pattern: @username (at start or after space) or u/username
    # Must start with @ or u/ to be a real mention
    at_mentions = re.findall(r'(?:^|[\s\(\[])@([A-Za-z0-9_-]{2,30})(?=[\s\.,;:\)\]!?]|$)', content)
    u_mentions = re.findall(r'(?:^|[\s\(\[])u/([A-Za-z0-9_-]{2,30})(?=[\s\.,;:\)\]!?]|$)', content)
    return list(set(at_mentions + u_mentions))


def fetch_post_comments(post_id, max_retries=3):
    """Fetch all comments for a post with retry logic."""
    headers = {'Accept-Encoding': 'gzip, deflate'}
    url = f"{API_BASE}/posts/{post_id}"

    for attempt in range(max_retries):
        try:
            # Exponential backoff: 0s, 5s, 15s
            if attempt > 0:
                backoff = 5 * (2 ** (attempt - 1))
                logger.info(f"Post {post_id}: Retry {attempt}/{max_retries} after {backoff}s")
                time.sleep(backoff)

            resp = requests.get(url, headers=headers, timeout=60)

            if resp.status_code == 404:
                logger.warning(f"Post {post_id}: HTTP 404 - post deleted or moved")
                return None, None, None

            if resp.status_code == 429:
                # Rate limited - wait longer
                logger.warning(f"Post {post_id}: Rate limited, waiting 30s")
                time.sleep(30)
                continue

            if resp.status_code != 200:
                logger.warning(f"Post {post_id}: HTTP {resp.status_code}")
                if attempt < max_retries - 1:
                    continue
                return None, None, None

            data = resp.json()

            # Save raw JSON for archival (raw truth layer)
            raw_dir = RAW_DIR / "posts"
            raw_dir.mkdir(parents=True, exist_ok=True)
            raw_path = raw_dir / f"{post_id}.json"
            with open(raw_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return data.get('post'), data.get('comments', []), data

        except requests.Timeout:
            logger.warning(f"Post {post_id}: Timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                continue
            logger.error(f"Post {post_id}: All retries failed (timeout)")
            return None, None, None
        except requests.RequestException as e:
            logger.warning(f"Post {post_id}: Network error - {e} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                continue
            logger.error(f"Post {post_id}: All retries failed")
            return None, None, None
        except Exception as e:
            logger.error(f"Post {post_id}: Unexpected error - {e}")
            return None, None, None

    return None, None, None


def flatten_comments(comments, post_id, parent_id=None, depth=0):
    """Flatten nested comment structure."""
    flat = []
    for c in comments:
        author = c.get('author', {})
        if isinstance(author, dict):
            author_name = author.get('name', 'Unknown')
        else:
            author_name = str(author) if author else 'Unknown'

        flat.append({
            'id': c.get('id'),
            'post_id': post_id,
            'parent_id': parent_id,
            'author': author_name,
            'content': c.get('content'),
            'upvotes': c.get('upvotes', 0),
            'downvotes': c.get('downvotes', 0),
            'created_at': c.get('created_at'),
            'depth': depth,
        })

        # Recursively flatten replies
        replies = c.get('replies', [])
        if replies:
            flat.extend(flatten_comments(replies, post_id, c.get('id'), depth + 1))

    return flat


def save_comments(cursor, comments, post_author):
    """Save comments and extract interactions."""
    saved = 0
    interactions = []

    # Build parent->author map for reply tracking
    author_map = {}
    for c in comments:
        author_map[c['id']] = c['author']

    for c in comments:
        content_sanitized = sanitize(c['content'])
        is_injection = 1 if detect_prompt_injection(c['content']) else 0

        # Determine who this is replying to
        reply_to = None
        if c['parent_id']:
            reply_to = author_map.get(c['parent_id'])
        elif c['depth'] == 0:
            # Top-level comment is reply to post author
            reply_to = post_author

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO comments
                (id, post_id, parent_id, author, content, content_sanitized,
                 upvotes, downvotes, created_at, depth, reply_to_author, is_prompt_injection, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c['id'], c['post_id'], c['parent_id'], c['author'],
                c['content'], content_sanitized,
                c['upvotes'], c['downvotes'], c['created_at'],
                c['depth'], reply_to, is_injection,
                datetime.now().isoformat()
            ))
            saved += 1

            # Create interaction record
            if reply_to and reply_to != c['author']:  # Don't track self-replies
                interactions.append({
                    'post_id': c['post_id'],
                    'comment_id': c['id'],
                    'author_from': c['author'],
                    'author_to': reply_to,
                    'interaction_type': 'reply',
                    'timestamp': c['created_at'],
                    'content_snippet': (c['content'] or '')[:200]
                })

            # Extract mentions as separate interactions
            mentions = extract_mentions(c['content'])
            for mentioned in mentions:
                if mentioned != c['author']:
                    interactions.append({
                        'post_id': c['post_id'],
                        'comment_id': c['id'],
                        'author_from': c['author'],
                        'author_to': mentioned,
                        'interaction_type': 'mention',
                        'timestamp': c['created_at'],
                        'content_snippet': (c['content'] or '')[:200]
                    })

        except Exception as e:
            logger.error(f"Saving comment {c['id']}: {e}")

    return saved, interactions


def save_interactions(cursor, interactions):
    """Save interaction edges to graph."""
    saved = 0
    for i in interactions:
        try:
            cursor.execute("""
                INSERT INTO interactions
                (post_id, comment_id, author_from, author_to, interaction_type, timestamp, content_snippet)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                i['post_id'], i['comment_id'], i['author_from'], i['author_to'],
                i['interaction_type'], i['timestamp'], i['content_snippet']
            ))
            saved += 1
        except sqlite3.IntegrityError:
            # Duplicate interaction, skip
            pass
        except sqlite3.Error as e:
            logger.debug(f"Could not save interaction: {e}")
    return saved


def scrape_all_comments(limit=None):
    """Scrape comments for all posts in DB."""
    logger.info("=" * 50)
    logger.info("COMMENT SCRAPER - Extracting Culture")
    logger.info("=" * 50)

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except sqlite3.Error as e:
        logger.error(f"Database connection failed: {e}")
        return

    # Get posts ordered by engagement (most interesting first)
    query = """
        SELECT id, title, author, comment_count
        FROM posts
        ORDER BY comment_count DESC
    """
    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    posts = cursor.fetchall()

    logger.info(f"Processing {len(posts)} posts")

    total_comments = 0
    total_interactions = 0
    injection_count = 0
    errors = 0

    for i, post in enumerate(posts, 1):
        post_id = post['id']
        title = (post['title'] or 'Unknown')[:40]
        expected = post['comment_count'] or 0

        logger.info(f"[{i}/{len(posts)}] {title}... (expected: {expected})")

        # Rate limit
        time.sleep(RATE_LIMIT)

        # Fetch
        post_data, comments, raw_data = fetch_post_comments(post_id)
        if not comments:
            logger.debug(f"Post {post_id}: No comments returned")
            continue

        # Flatten
        flat_comments = flatten_comments(comments, post_id)
        logger.debug(f"Post {post_id}: Fetched {len(flat_comments)} comments")

        # Save
        try:
            saved, interactions = save_comments(cursor, flat_comments, post['author'])
            total_comments += saved

            # Save interactions
            int_saved = save_interactions(cursor, interactions)
            total_interactions += int_saved

            # Count injections
            injections = sum(1 for c in flat_comments if detect_prompt_injection(c['content']))
            if injections:
                logger.warning(f"Post {post_id}: {injections} prompt injections detected")
                injection_count += injections

            logger.debug(f"Post {post_id}: Saved {saved} comments, {int_saved} interactions")

        except Exception as e:
            logger.error(f"Post {post_id}: Save failed - {e}")
            errors += 1

        # Commit periodically
        if i % 5 == 0:
            conn.commit()

    conn.commit()
    conn.close()

    logger.info("=" * 50)
    logger.info("SCRAPING COMPLETE")
    logger.info("=" * 50)
    logger.info(f"Total comments: {total_comments}")
    logger.info(f"Total interactions: {total_interactions}")
    logger.info(f"Prompt injections: {injection_count}")
    if errors:
        logger.warning(f"Errors encountered: {errors}")
    logger.info("Next: python analyze_interactions.py")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Limit number of posts to process")
    args = parser.parse_args()

    scrape_all_comments(limit=args.limit)
