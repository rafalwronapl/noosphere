#!/usr/bin/env python3
"""
Universal agent runner for Moltbook Observatory.
Usage: python run_agent.py <agent_name> [--test]
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Paths
PROJECT_DIR = Path.home() / "moltbook-observatory"
AGENTS_DIR = PROJECT_DIR / "agents"
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "observatory.db"
LOGS_DIR = PROJECT_DIR / "logs"


def load_agent_prompt(agent_name: str) -> str:
    """Load AGENT.md for the specified agent."""
    agent_file = AGENTS_DIR / agent_name / "AGENT.md"
    if not agent_file.exists():
        raise FileNotFoundError(f"Agent {agent_name} not found at {agent_file}")
    return agent_file.read_text(encoding="utf-8")


def load_settings() -> dict:
    """Load global settings."""
    settings_file = PROJECT_DIR / "config" / "settings.json"
    with open(settings_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_recent_data(agent_name: str, conn: sqlite3.Connection) -> dict:
    """Get relevant recent data for the agent."""
    cursor = conn.cursor()

    if agent_name == "scanner":
        # Scanner gets sample data or fetches from API
        sample_file = DATA_DIR / "samples" / "sample_moltbook_feed.json"
        if sample_file.exists():
            with open(sample_file, "r", encoding="utf-8") as f:
                return {"feed_data": json.load(f)}
        return {"feed_data": []}

    elif agent_name == "analyst":
        # Analyst gets recent scans
        cursor.execute("""
            SELECT * FROM scans
            ORDER BY timestamp DESC LIMIT 5
        """)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        scans = [dict(zip(columns, row)) for row in rows]

        # Also get recent posts
        cursor.execute("""
            SELECT * FROM posts
            ORDER BY scraped_at DESC LIMIT 50
        """)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        posts = [dict(zip(columns, row)) for row in rows]

        return {"recent_scans": scans, "recent_posts": posts}

    elif agent_name == "interpreter":
        # Interpreter gets recent patterns
        cursor.execute("""
            SELECT * FROM patterns
            ORDER BY timestamp DESC LIMIT 10
        """)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        patterns = [dict(zip(columns, row)) for row in rows]

        cursor.execute("""
            SELECT * FROM scans
            ORDER BY timestamp DESC LIMIT 3
        """)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        scans = [dict(zip(columns, row)) for row in rows]

        return {"recent_patterns": patterns, "recent_scans": scans}

    elif agent_name == "editor":
        # Editor gets everything from last 24h
        cursor.execute("""
            SELECT * FROM scans
            WHERE timestamp > datetime('now', '-24 hours')
            ORDER BY timestamp DESC
        """)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        scans = [dict(zip(columns, row)) for row in rows]

        cursor.execute("""
            SELECT * FROM patterns
            WHERE timestamp > datetime('now', '-24 hours')
            ORDER BY timestamp DESC
        """)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        patterns = [dict(zip(columns, row)) for row in rows]

        cursor.execute("""
            SELECT * FROM interpretations
            WHERE timestamp > datetime('now', '-24 hours')
            ORDER BY timestamp DESC
        """)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        interpretations = [dict(zip(columns, row)) for row in rows]

        return {
            "scans": scans,
            "patterns": patterns,
            "interpretations": interpretations
        }

    return {}


def build_prompt(agent_name: str, agent_md: str, context_data: dict, settings: dict) -> str:
    """Build the full prompt for the agent."""

    timestamp = datetime.now().isoformat()

    # Truncate large data for display
    context_str = json.dumps(context_data, indent=2, default=str, ensure_ascii=False)
    if len(context_str) > 10000:
        context_str = context_str[:10000] + "\n... [truncated]"

    prompt = f"""# Moltbook Observatory - Agent Task

## Timestamp
{timestamp}

## Your Role
{agent_md}

## Current Focus Areas
Submolts: {', '.join(settings['focus']['submolts'])}
Key Actors: {', '.join(settings['focus']['actors'])}
Keywords: {', '.join(settings['focus']['keywords'])}

## Input Data
```json
{context_str}
```

## Your Task
Based on your role and the input data above, perform your analysis and produce a structured JSON report as specified in your AGENT.md.

IMPORTANT:
1. Output ONLY valid JSON
2. Follow the exact schema from your AGENT.md
3. Be thorough but concise
4. Flag anything unusual or concerning

Begin your analysis now.
"""
    return prompt


def save_result(agent_name: str, result: dict, conn: sqlite3.Connection):
    """Save agent result to appropriate table."""
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()

    try:
        if agent_name == "scanner":
            scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            cursor.execute("""
                INSERT INTO scans (id, timestamp, period, top_posts, top_authors, active_submolts, alerts, stats)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scan_id,
                timestamp,
                result.get("period", "1h"),
                json.dumps(result.get("top_posts", [])),
                json.dumps(result.get("top_authors", [])),
                json.dumps(result.get("active_submolts", [])),
                json.dumps(result.get("alerts", [])),
                json.dumps(result.get("stats", {}))
            ))
            print(f"[OK] Saved scan: {scan_id}")

        elif agent_name == "analyst":
            analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            for pattern in result.get("patterns", []):
                cursor.execute("""
                    INSERT INTO patterns (analysis_id, timestamp, pattern_type, name, description, direction, change_percent, confidence, evidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    analysis_id,
                    timestamp,
                    pattern.get("type", "unknown"),
                    pattern.get("name", ""),
                    pattern.get("description", ""),
                    pattern.get("direction", ""),
                    pattern.get("change", 0),
                    pattern.get("confidence", 0),
                    json.dumps(pattern.get("evidence", []))
                ))
            print(f"[OK] Saved {len(result.get('patterns', []))} patterns from {analysis_id}")

        elif agent_name == "interpreter":
            interp_id = f"interp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            for item in result.get("fascinating", []):
                cursor.execute("""
                    INSERT INTO interpretations (interpretation_id, timestamp, category, observation, meaning, implications, risk_level, recommendations, questions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    interp_id,
                    timestamp,
                    "fascinating",
                    item.get("observation", ""),
                    item.get("meaning", ""),
                    item.get("implications", ""),
                    "low",
                    json.dumps(item.get("recommendations", [])),
                    json.dumps([])
                ))

            for item in result.get("concerning", []):
                cursor.execute("""
                    INSERT INTO interpretations (interpretation_id, timestamp, category, observation, meaning, implications, risk_level, recommendations, questions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    interp_id,
                    timestamp,
                    "concerning",
                    item.get("observation", ""),
                    item.get("meaning", ""),
                    item.get("implications", ""),
                    item.get("risk_level", "medium"),
                    json.dumps(item.get("recommendations", [])),
                    json.dumps(result.get("questions", []))
                ))

            print(f"[OK] Saved interpretations: {interp_id}")

        elif agent_name == "editor":
            brief_id = f"brief_{datetime.now().strftime('%Y%m%d')}"
            cursor.execute("""
                INSERT OR REPLACE INTO briefs (id, date, timestamp, headline, alerts, top_stories, trends_summary, actors_to_watch, recommendations, meta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                brief_id,
                datetime.now().date().isoformat(),
                timestamp,
                result.get("headline", ""),
                json.dumps(result.get("alerts", [])),
                json.dumps(result.get("top_stories", [])),
                json.dumps(result.get("trends_summary", {})),
                json.dumps(result.get("actors_to_watch", [])),
                json.dumps(result.get("recommendations", [])),
                json.dumps(result.get("meta", {}))
            ))
            print(f"[OK] Saved daily brief: {brief_id}")

        conn.commit()

    except Exception as e:
        print(f"[ERROR] Saving result: {e}")
        conn.rollback()


def run_with_claude(prompt: str, agent_name: str) -> dict:
    """Save prompt for manual Claude run or API integration."""

    # Save prompt to file for manual execution
    prompt_file = PROJECT_DIR / "logs" / f"prompt_{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(prompt, encoding="utf-8")

    print(f"\n[INFO] Prompt saved to: {prompt_file}")
    print(f"\nTo run manually with OpenClaw:")
    print(f'  openclaw agent --agent {agent_name} --message "Analyze the data in {prompt_file}" --local')

    # In future: integrate with Claude API directly
    return {}


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_agent.py <agent_name> [--test]")
        print("Agents: scanner, analyst, interpreter, editor")
        sys.exit(1)

    agent_name = sys.argv[1].lower()
    test_mode = "--test" in sys.argv

    valid_agents = ["scanner", "analyst", "interpreter", "editor"]
    if agent_name not in valid_agents:
        print(f"Unknown agent: {agent_name}")
        print(f"Valid agents: {', '.join(valid_agents)}")
        sys.exit(1)

    print(f"\n[Agent] Running: {agent_name}")
    print(f"[Time] {datetime.now().isoformat()}")

    # Load components
    settings = load_settings()
    agent_md = load_agent_prompt(agent_name)

    print(f"[OK] Loaded AGENT.md ({len(agent_md)} chars)")
    print(f"[OK] Loaded settings")

    # Connect to database
    if not DB_PATH.exists():
        print(f"[ERROR] Database not found: {DB_PATH}")
        print("Run: python scripts/init_db.py")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Get context data
    context_data = get_recent_data(agent_name, conn)
    print(f"[OK] Loaded context data")

    # Build prompt
    prompt = build_prompt(agent_name, agent_md, context_data, settings)
    print(f"[OK] Built prompt ({len(prompt)} chars)")

    if test_mode:
        print("\n[TEST MODE] Prompt preview:")
        print("-" * 60)
        print(prompt[:1500] + "..." if len(prompt) > 1500 else prompt)
        print("-" * 60)
    else:
        # Run with Claude (or save for manual run)
        result = run_with_claude(prompt, agent_name)

        # Save result if we got one
        if result:
            save_result(agent_name, result, conn)

    conn.close()
    print(f"\n[OK] Agent {agent_name} completed")


if __name__ == "__main__":
    main()
