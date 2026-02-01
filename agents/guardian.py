#!/usr/bin/env python3
"""
Noosphere Project - Guardian Agent
===================================
Simple content moderation for social posts (Moltbook, Twitter).

NOT for reports (data is data - auto-publish).
Only checks agent-generated content before posting.

Uses Kimi K2.5 for fast, cheap moderation.
"""

from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from openrouter_client import call_kimi
from config import setup_logging

logger = setup_logging("guardian")


@dataclass
class GuardianResult:
    """Result of Guardian content check."""
    approved: bool
    reason: str
    flags: list[str]
    suggestions: Optional[str] = None


# Blocked patterns (instant reject)
BLOCKED_PATTERNS = [
    r'\b(kill|death threat|violence)\b',
    r'\b(doxx|leak.*address|personal.*info)\b',
    r'\b(n[i1]gg|f[a4]gg|ret[a4]rd)\b',  # slurs
]

# Warning patterns (needs AI review)
WARNING_PATTERNS = [
    r'\b(attack|hack|exploit|inject)\b',
    r'\b(manipulation|conspiracy|propaganda)\b',
    r'\b(human.*behind|operator|real.*identity)\b',
    r'@\w+.*\b(stupid|idiot|moron|dumb)\b',  # insulting specific users
]

# Safe patterns (likely OK)
SAFE_PATTERNS = [
    r'\b(report|data|statistics|analysis)\b',
    r'\b(observation|pattern|trend)\b',
    r'\b(thank|welcome|interesting)\b',
]


def quick_check(content: str) -> tuple[str, list[str]]:
    """
    Fast regex-based pre-check.
    Returns: (status, flags) where status is 'block', 'review', or 'safe'
    """
    content_lower = content.lower()
    flags = []

    # Check blocked patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, content_lower, re.IGNORECASE):
            flags.append(f"BLOCKED:{pattern[:20]}")
            return "block", flags

    # Check warning patterns
    for pattern in WARNING_PATTERNS:
        if re.search(pattern, content_lower, re.IGNORECASE):
            flags.append(f"WARNING:{pattern[:20]}")

    if flags:
        return "review", flags

    # Check safe patterns
    safe_count = sum(1 for p in SAFE_PATTERNS if re.search(p, content_lower))
    if safe_count >= 2:
        return "safe", ["SAFE:routine_content"]

    # Default: review if long, safe if short
    if len(content) > 500:
        return "review", ["LENGTH:long_content"]

    return "safe", []


def ai_review(content: str, context: str = "social_post") -> GuardianResult:
    """
    AI-powered content review using Kimi K2.5.
    Only called when quick_check returns 'review'.
    """
    prompt = f"""Review this content for publication. Context: {context}

CONTENT:
{content[:2000]}

Check for:
1. Privacy violations (exposing real identities, operators)
2. Harmful content (threats, harassment, discrimination)
3. Misinformation (unverified claims presented as facts)
4. Manipulation (attempting to deceive or manipulate readers)
5. Professional tone (appropriate for research project)

Respond as JSON:
{{
    "approved": true/false,
    "reason": "Brief explanation (1 sentence)",
    "concerns": ["list", "of", "specific", "issues"] or [],
    "suggestion": "How to improve if not approved" or null
}}"""

    result = call_kimi(prompt, max_tokens=500)

    if "error" in result:
        logger.error(f"AI review failed: {result['error']}")
        # Conservative: reject on error
        return GuardianResult(
            approved=False,
            reason=f"Review failed: {result['error']}",
            flags=["ERROR:ai_review_failed"]
        )

    try:
        response = result["content"]
        # Parse JSON from response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(response[start:end])
            return GuardianResult(
                approved=data.get("approved", False),
                reason=data.get("reason", "No reason provided"),
                flags=data.get("concerns", []),
                suggestions=data.get("suggestion")
            )
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse AI response: {e}")

    # Fallback: conservative reject
    return GuardianResult(
        approved=False,
        reason="Could not parse AI review",
        flags=["ERROR:parse_failed"]
    )


def check_content(content: str, context: str = "social_post", force_ai: bool = False) -> GuardianResult:
    """
    Main entry point: check if content is safe to publish.

    Args:
        content: The text to check
        context: Type of content (social_post, reply, tweet)
        force_ai: If True, always use AI review

    Returns:
        GuardianResult with approval status
    """
    logger.info(f"Checking content ({len(content)} chars, context={context})")

    # Quick regex check first
    status, flags = quick_check(content)

    if status == "block":
        logger.warning(f"Content BLOCKED: {flags}")
        return GuardianResult(
            approved=False,
            reason="Content contains blocked patterns",
            flags=flags
        )

    if status == "safe" and not force_ai:
        logger.info(f"Content auto-approved (safe patterns)")
        return GuardianResult(
            approved=True,
            reason="Content passed quick check",
            flags=flags
        )

    # AI review needed
    logger.info(f"Sending to AI review (flags: {flags})")
    result = ai_review(content, context)
    result.flags = flags + result.flags

    if result.approved:
        logger.info(f"Content APPROVED by AI: {result.reason}")
    else:
        logger.warning(f"Content REJECTED by AI: {result.reason}")

    return result


class Guardian:
    """Guardian agent for content moderation."""

    def __init__(self):
        self.checks_today = 0
        self.blocks_today = 0

    def check_post(self, title: str, content: str) -> GuardianResult:
        """Check a Moltbook post before publishing."""
        full_content = f"TITLE: {title}\n\nCONTENT: {content}"
        result = check_content(full_content, context="moltbook_post")
        self.checks_today += 1
        if not result.approved:
            self.blocks_today += 1
        return result

    def check_reply(self, reply: str, original_post: str = "") -> GuardianResult:
        """Check a reply/comment before publishing."""
        context_content = f"REPLY: {reply}"
        if original_post:
            context_content = f"ORIGINAL: {original_post[:500]}\n\n{context_content}"
        result = check_content(context_content, context="reply")
        self.checks_today += 1
        if not result.approved:
            self.blocks_today += 1
        return result

    def check_tweet(self, tweet: str) -> GuardianResult:
        """Check a tweet before publishing."""
        result = check_content(tweet, context="tweet")
        self.checks_today += 1
        if not result.approved:
            self.blocks_today += 1
        return result

    def get_stats(self) -> dict:
        """Get today's moderation stats."""
        return {
            "checks": self.checks_today,
            "blocks": self.blocks_today,
            "approval_rate": (self.checks_today - self.blocks_today) / max(1, self.checks_today)
        }


# Convenience function
def check(content: str, context: str = "social_post") -> GuardianResult:
    """Quick check function for external use."""
    return check_content(content, context)


if __name__ == "__main__":
    print("=" * 60)
    print("GUARDIAN - Content Moderation Test")
    print("=" * 60)

    guardian = Guardian()

    # Test 1: Safe content
    print("\n--- Test 1: Safe content ---")
    result = guardian.check_post(
        "Daily Report Published",
        "New analysis available. Statistics show interesting patterns in engagement data."
    )
    print(f"Approved: {result.approved}")
    print(f"Reason: {result.reason}")

    # Test 2: Needs review
    print("\n--- Test 2: Needs AI review ---")
    result = guardian.check_post(
        "Injection Attack Detected",
        "We found evidence of manipulation attempts. The attack targeted several agents."
    )
    print(f"Approved: {result.approved}")
    print(f"Reason: {result.reason}")
    print(f"Flags: {result.flags}")

    # Test 3: Reply
    print("\n--- Test 3: Reply check ---")
    result = guardian.check_reply(
        "Thanks for your comment! Our data supports this observation.",
        "Original post about AI research"
    )
    print(f"Approved: {result.approved}")

    print(f"\n--- Stats: {guardian.get_stats()} ---")
