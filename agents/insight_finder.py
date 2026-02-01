#!/usr/bin/env python3
"""
Noosphere Project - Insight Finder (Opus 4.5)
==============================================
Reads daily report and finds hidden patterns, correlations,
and insights that the automated analysis might have missed.

Uses Claude Opus 4.5 for deep reasoning (expensive - run once daily).
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from config import setup_logging, PROJECT_ROOT

logger = setup_logging("insight_finder")

# OpenRouter API for Opus 4.5
import requests
import os

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPUS_MODEL = "anthropic/claude-opus-4-5-20251101"


def call_opus(prompt: str, max_tokens: int = 2000) -> dict:
    """Call Claude Opus 4.5 via OpenRouter."""
    if not OPENROUTER_API_KEY:
        return {"error": "OPENROUTER_API_KEY not set"}

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPUS_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        return {"content": data["choices"][0]["message"]["content"]}
    except Exception as e:
        logger.error(f"Opus API error: {e}")
        return {"error": str(e)}


def find_insights(report_path: Path, raw_data_dir: Optional[Path] = None) -> dict:
    """
    Analyze daily report and find hidden insights.

    Args:
        report_path: Path to daily_report.md
        raw_data_dir: Optional path to raw/ directory with CSVs

    Returns:
        Dict with insights, questions, and recommendations
    """
    logger.info(f"Analyzing report: {report_path}")

    # Read report
    if not report_path.exists():
        return {"error": f"Report not found: {report_path}"}

    report_content = report_path.read_text(encoding="utf-8")

    # Read raw data if available
    raw_data_summary = ""
    if raw_data_dir and raw_data_dir.exists():
        for csv_file in raw_data_dir.glob("*.csv"):
            try:
                lines = csv_file.read_text(encoding="utf-8").split("\n")
                raw_data_summary += f"\n--- {csv_file.name} ({len(lines)} rows) ---\n"
                raw_data_summary += "\n".join(lines[:20])  # First 20 rows
                raw_data_summary += "\n...\n"
            except Exception as e:
                logger.warning(f"Could not read {csv_file}: {e}")

    # Build prompt for Opus
    prompt = f"""You are a senior researcher analyzing a daily field report from an AI agent observation project.

Your task: Find insights, patterns, and correlations that the automated report might have MISSED.

DAILY REPORT:
{report_content[:8000]}

{f"RAW DATA SAMPLES:{raw_data_summary[:4000]}" if raw_data_summary else ""}

ANALYZE FOR:

1. **Hidden Correlations**
   - Are there relationships between metrics that aren't explicitly mentioned?
   - Do timing patterns suggest something about agent behavior?
   - Are there suspicious coincidences?

2. **Missing Context**
   - What external events might explain the patterns?
   - What historical context would help interpret this data?
   - What comparisons to other platforms/communities are relevant?

3. **Anomalies Worth Investigating**
   - What numbers don't add up?
   - What patterns break from expected behavior?
   - What's conspicuously absent from the data?

4. **Methodological Concerns**
   - Are there biases in how data was collected?
   - What can't we conclude from this data?
   - What would we need to verify these findings?

5. **Research Questions**
   - What should tomorrow's report investigate?
   - What hypotheses does this data suggest?
   - What would falsify our current interpretations?

FORMAT YOUR RESPONSE AS:

## Key Insights
[2-4 bullet points of non-obvious findings]

## Hidden Patterns
[Correlations or patterns not mentioned in report]

## Concerns & Caveats
[Methodological issues or alternative explanations]

## Tomorrow's Questions
[Specific things to investigate next]

## One Sentence Summary
[The most important takeaway]

Be intellectually rigorous. Challenge assumptions. Find what others missed."""

    logger.info("Calling Opus 4.5 for deep analysis...")
    result = call_opus(prompt, max_tokens=2000)

    if "error" in result:
        return {"error": result["error"], "insights": None}

    insights_text = result["content"]

    # Parse sections
    insights = {
        "raw_analysis": insights_text,
        "generated_at": datetime.now().isoformat(),
        "model": OPUS_MODEL,
        "report_analyzed": str(report_path)
    }

    # Extract one-sentence summary if present
    if "One Sentence Summary" in insights_text:
        try:
            summary_start = insights_text.index("One Sentence Summary")
            summary_section = insights_text[summary_start:summary_start+500]
            lines = [l.strip() for l in summary_section.split("\n") if l.strip() and not l.startswith("#")]
            if lines:
                insights["summary"] = lines[0]
        except:
            pass

    return insights


def add_insights_to_report(report_dir: Path) -> bool:
    """
    Run insight finder and add results to commentary.

    Args:
        report_dir: Directory containing daily_report.md

    Returns:
        True if insights were added successfully
    """
    report_path = report_dir / "daily_report.md"
    raw_dir = report_dir / "raw"
    commentary_path = report_dir / "commentary" / "commentary.md"

    # Find insights
    insights = find_insights(report_path, raw_dir)

    if "error" in insights:
        logger.error(f"Failed to find insights: {insights['error']}")
        return False

    # Add to commentary
    if commentary_path.exists():
        existing = commentary_path.read_text(encoding="utf-8")
    else:
        commentary_path.parent.mkdir(parents=True, exist_ok=True)
        existing = "# Researcher Commentary\n\n"

    # Append Opus insights
    opus_section = f"""
---

## Opus 4.5 Deep Analysis
*Generated: {insights['generated_at']}*

{insights['raw_analysis']}

---
"""

    updated = existing + opus_section
    commentary_path.write_text(updated, encoding="utf-8")

    logger.info(f"Added Opus insights to {commentary_path}")

    # Also save raw insights as JSON
    insights_json_path = report_dir / "opus_insights.json"
    insights_json_path.write_text(
        json.dumps(insights, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Find insights in daily report")
    parser.add_argument("--date", help="Report date (YYYY-MM-DD), default: today")
    parser.add_argument("--dry-run", action="store_true", help="Print insights without saving")
    args = parser.parse_args()

    # Determine report directory
    if args.date:
        date_str = args.date
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")

    report_dir = PROJECT_ROOT / "reports" / date_str

    if not report_dir.exists():
        print(f"Report directory not found: {report_dir}")
        sys.exit(1)

    print("=" * 60)
    print(f"INSIGHT FINDER - Analyzing {date_str}")
    print("=" * 60)

    if args.dry_run:
        insights = find_insights(report_dir / "daily_report.md", report_dir / "raw")
        if "error" in insights:
            print(f"Error: {insights['error']}")
        else:
            print(insights["raw_analysis"])
    else:
        success = add_insights_to_report(report_dir)
        if success:
            print(f"\nInsights added to {report_dir / 'commentary' / 'commentary.md'}")
        else:
            print("Failed to add insights")
            sys.exit(1)
