"""
Noosphere Project - Agent System
=================================

Agent Architecture:
- Guardian: Content moderation for social posts
- InsightFinder: Discovers patterns in daily reports (Kimi)
- MoltbookAgent: Active participant on Moltbook + social listening
- TwitterAgent: Twitter presence management
- ResearchAgent: Automated pattern analysis
- PublicationCoordinator: Pipeline from findings to publication

Flow:
1. Scanner → collects data from Moltbook
2. ResearchAgent → analyzes patterns, generates findings
3. InsightFinder → reads daily reports, finds hidden insights
4. PublicationCoordinator → manages publication pipeline
5. Guardian → approves content for MoltbookAgent/TwitterAgent
6. MoltbookAgent/TwitterAgent → publishes to platforms

All social posts go through Guardian review.
"""

from pathlib import Path

# Agents directory
AGENTS_DIR = Path(__file__).parent

# List available agents
AVAILABLE_AGENTS = [
    "guardian",               # Content moderation
    "insight_finder",         # Pattern discovery (Kimi)
    "moltbook_agent",         # Moltbook participation + listening
    "twitter_agent",          # Twitter presence
    "research_agent",         # Automated analysis
    "publication_coordinator", # Publication pipeline
]
