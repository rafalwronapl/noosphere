#!/usr/bin/env python3
"""
Noosphere Project - REST API Server
====================================
Provides JSON API endpoints for discoveries, stats, and featured agents.

Usage:
    python api_server.py                    # Run on default port 5000
    python api_server.py --port 8080        # Custom port
    python api_server.py --debug            # Debug mode
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from functools import wraps

try:
    from flask import Flask, jsonify, request, abort
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "website" / "public" / "data"
DISCOVERIES_PATH = DATA_DIR / "discoveries.json"
DB_PATH = PROJECT_ROOT / "data" / "observatory.db"

app = Flask(__name__)

if FLASK_AVAILABLE:
    CORS(app)  # Enable CORS for frontend access


def load_discoveries() -> list:
    """Load discoveries from JSON file."""
    if not DISCOVERIES_PATH.exists():
        return []
    with open(DISCOVERIES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_db_stats() -> dict:
    """Get statistics from the database."""
    import sqlite3

    if not DB_PATH.exists():
        return {"error": "Database not found"}

    stats = {}
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Total posts
        cursor.execute("SELECT COUNT(*) FROM posts")
        stats["total_posts"] = cursor.fetchone()[0]

        # Total actors
        cursor.execute("SELECT COUNT(DISTINCT author) FROM posts")
        stats["total_actors"] = cursor.fetchone()[0]

        # Posts today
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM posts WHERE date(created_at) = ?", (today,))
        stats["posts_today"] = cursor.fetchone()[0]

        # Active submolts
        cursor.execute("SELECT COUNT(DISTINCT submolt) FROM posts WHERE submolt IS NOT NULL")
        stats["active_submolts"] = cursor.fetchone()[0]

    except sqlite3.Error as e:
        stats["db_error"] = str(e)
    finally:
        conn.close()

    return stats


def get_featured_agent() -> Optional[dict]:
    """Select a featured agent based on recent activity and interest."""
    import sqlite3

    if not DB_PATH.exists():
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Get agents with most interesting recent activity
        # Criteria: high engagement, recent posts, controversy
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()

        cursor.execute("""
            SELECT
                author,
                COUNT(*) as post_count,
                SUM(upvotes) as total_upvotes,
                SUM(comment_count) as total_comments,
                AVG(upvotes - downvotes) as avg_score
            FROM posts
            WHERE created_at > ? AND author IS NOT NULL
            GROUP BY author
            HAVING post_count >= 3
            ORDER BY (total_upvotes + total_comments * 2) DESC
            LIMIT 10
        """, (week_ago,))

        candidates = cursor.fetchall()

        if not candidates:
            # Fallback: any active agent
            cursor.execute("""
                SELECT author, COUNT(*) as post_count
                FROM posts
                WHERE author IS NOT NULL
                GROUP BY author
                ORDER BY post_count DESC
                LIMIT 5
            """)
            candidates = cursor.fetchall()

        if candidates:
            # Pick one with some randomness for variety
            weights = [c[1] for c in candidates]  # Weight by post count
            chosen = random.choices(candidates, weights=weights, k=1)[0]

            # Get more details about the agent
            cursor.execute("""
                SELECT
                    author,
                    COUNT(*) as total_posts,
                    MIN(created_at) as first_seen,
                    MAX(created_at) as last_seen,
                    SUM(upvotes) as total_upvotes,
                    SUM(comment_count) as total_comments
                FROM posts
                WHERE author = ?
            """, (chosen[0],))

            agent_data = cursor.fetchone()

            # Get a notable post
            cursor.execute("""
                SELECT title, content, upvotes, comment_count
                FROM posts
                WHERE author = ?
                ORDER BY (upvotes + comment_count * 2) DESC
                LIMIT 1
            """, (chosen[0],))
            notable_post = cursor.fetchone()

            return {
                "name": agent_data[0],
                "total_posts": agent_data[1],
                "first_seen": agent_data[2],
                "last_seen": agent_data[3],
                "total_upvotes": agent_data[4] or 0,
                "total_comments": agent_data[5] or 0,
                "notable_post": {
                    "title": notable_post[0] if notable_post else None,
                    "content": (notable_post[1][:200] + "...") if notable_post and notable_post[1] and len(notable_post[1]) > 200 else (notable_post[1] if notable_post else None),
                    "upvotes": notable_post[2] if notable_post else 0,
                    "comments": notable_post[3] if notable_post else 0
                } if notable_post else None,
                "selected_at": datetime.now().isoformat()
            }

    except sqlite3.Error as e:
        return {"error": str(e)}
    finally:
        conn.close()

    return None


# =============================================================================
# API Routes
# =============================================================================

@app.route('/api/v1/discoveries', methods=['GET'])
def api_discoveries():
    """
    Get all discoveries with optional filtering.

    Query params:
        - significance: HIGH, MEDIUM, LOW
        - category: filter by category
        - limit: max results (default 50)
        - offset: pagination offset (default 0)
        - q: search in title/description
    """
    discoveries = load_discoveries()

    # Filter by significance
    significance = request.args.get('significance')
    if significance:
        discoveries = [d for d in discoveries if d.get('significance') == significance.upper()]

    # Filter by category
    category = request.args.get('category')
    if category:
        discoveries = [d for d in discoveries if d.get('category', '').lower() == category.lower()]

    # Search
    search_query = request.args.get('q')
    if search_query:
        query_lower = search_query.lower()
        discoveries = [d for d in discoveries if
                      query_lower in d.get('title', '').lower() or
                      query_lower in d.get('description', '').lower()]

    # Pagination with validation
    try:
        limit = max(1, min(int(request.args.get('limit', 50)), 100))
        offset = max(0, int(request.args.get('offset', 0)))
    except ValueError:
        limit, offset = 50, 0

    total = len(discoveries)
    discoveries = discoveries[offset:offset + limit]

    return jsonify({
        "total": total,
        "limit": limit,
        "offset": offset,
        "count": len(discoveries),
        "discoveries": discoveries
    })


@app.route('/api/v1/discoveries/<discovery_id>', methods=['GET'])
def api_discovery_detail(discovery_id):
    """Get a single discovery by ID."""
    discoveries = load_discoveries()

    for d in discoveries:
        if str(d.get('id')) == str(discovery_id):
            return jsonify(d)

    abort(404, description="Discovery not found")


@app.route('/api/v1/discoveries/categories', methods=['GET'])
def api_categories():
    """Get list of all categories with counts."""
    discoveries = load_discoveries()

    categories = {}
    for d in discoveries:
        cat = d.get('category', 'Uncategorized')
        categories[cat] = categories.get(cat, 0) + 1

    return jsonify({
        "categories": [{"name": k, "count": v} for k, v in sorted(categories.items())]
    })


@app.route('/api/v1/stats', methods=['GET'])
def api_stats():
    """Get observatory statistics."""
    discoveries = load_discoveries()

    # Discovery stats
    discovery_stats = {
        "total": len(discoveries),
        "by_significance": {
            "high": len([d for d in discoveries if d.get('significance') == 'HIGH']),
            "medium": len([d for d in discoveries if d.get('significance') == 'MEDIUM']),
            "low": len([d for d in discoveries if d.get('significance') == 'LOW'])
        }
    }

    # Database stats
    db_stats = get_db_stats()

    return jsonify({
        "discoveries": discovery_stats,
        "observatory": db_stats,
        "generated_at": datetime.now().isoformat()
    })


@app.route('/api/v1/featured-agent', methods=['GET'])
def api_featured_agent():
    """Get the featured agent of the week."""
    agent = get_featured_agent()

    if not agent:
        return jsonify({"error": "No featured agent available", "agent": None})

    return jsonify({
        "agent": agent,
        "featured_period": "weekly"
    })


@app.route('/api/v1/health', methods=['GET'])
def api_health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "service": "Noosphere Observatory API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/v1', methods=['GET'])
def api_index():
    """API documentation endpoint."""
    return jsonify({
        "name": "Noosphere Observatory API",
        "version": "1.0.0",
        "endpoints": {
            "/api/v1/discoveries": "GET - List discoveries (params: significance, category, limit, offset, q)",
            "/api/v1/discoveries/<id>": "GET - Get single discovery",
            "/api/v1/discoveries/categories": "GET - List categories",
            "/api/v1/stats": "GET - Observatory statistics",
            "/api/v1/featured-agent": "GET - Featured agent of the week",
            "/api/v1/health": "GET - Health check"
        },
        "feeds": {
            "rss": "/feeds/discoveries.xml",
            "atom": "/feeds/discoveries.atom",
            "json": "/feeds/discoveries.json"
        }
    })


# =============================================================================
# Main
# =============================================================================

def main():
    import argparse

    if not FLASK_AVAILABLE:
        print("ERROR: Flask is not installed.")
        print("Install with: pip install flask flask-cors")
        return

    parser = argparse.ArgumentParser(description="Noosphere Observatory API Server")
    parser.add_argument("--port", "-p", type=int, default=5000, help="Port to run on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    print("=" * 60)
    print("NOOSPHERE OBSERVATORY API")
    print("=" * 60)
    print(f"Starting server on http://{args.host}:{args.port}")
    print(f"API docs: http://{args.host}:{args.port}/api/v1")
    print()

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
