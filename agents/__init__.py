"""
Moltbook Observatory - Agent System
====================================

Agent Architecture:
- AgentCouncil: Internal deliberation (5 agents review before publication)
- SecurityMonitor: Continuous threat detection
- PublicationCoordinator: Manages pipeline from analysis to publication
- ResearchCompanion: Daily briefings and research assistance

Flow:
1. Data collection (scanner scripts)
2. Analysis (analyst scripts)
3. Findings → ResearchCompanion
4. Review → AgentCouncil deliberation
5. Security check → SecurityMonitor
6. Publication → PublicationCoordinator

All public outputs go through council review.
"""

from pathlib import Path

# Agents directory
AGENTS_DIR = Path(__file__).parent

# List available agents
AVAILABLE_AGENTS = [
    "research_companion",   # Research assistance, daily briefings
    "agent_council",        # Multi-agent deliberation system
    "security_monitor",     # Threat detection and monitoring
    "publication_coordinator",  # Publication pipeline management
]
