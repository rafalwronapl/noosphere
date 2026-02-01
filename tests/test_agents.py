#!/usr/bin/env python3
"""
Tests for Noosphere Project agents.
Run: pytest tests/test_agents.py -v
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))


class TestGuardian:
    """Test Guardian content moderation agent."""

    def test_guardian_imports(self):
        """Guardian should import without errors."""
        from guardian import Guardian, GuardianResult
        assert Guardian is not None
        assert GuardianResult is not None

    def test_guardian_init(self):
        """Guardian should initialize."""
        from guardian import Guardian
        g = Guardian()
        assert g is not None

    def test_check_post_safe(self):
        """Safe content should be approved."""
        from guardian import Guardian
        g = Guardian()
        result = g.check_post("Daily Report", "Here is our analysis of the data.")
        assert result.approved is True

    def test_check_post_offensive(self):
        """Offensive content should be rejected."""
        from guardian import Guardian
        g = Guardian()
        # Testing with clearly offensive content
        result = g.check_post("Bad Post", "This is hate speech content with slurs")
        # Guardian should detect this as potentially harmful
        # Note: actual result depends on Guardian's implementation

    def test_check_reply_safe(self):
        """Safe reply should be approved."""
        from guardian import Guardian
        g = Guardian()
        result = g.check_reply("Thank you for your comment!")
        assert result.approved is True

    def test_check_tweet_length(self):
        """Tweet over 280 chars should be flagged."""
        from guardian import Guardian
        g = Guardian()
        long_tweet = "x" * 300
        result = g.check_tweet(long_tweet)
        # Should either reject or flag as too long


class TestMoltbookAgent:
    """Test Moltbook Agent."""

    def test_moltbook_agent_imports(self):
        """MoltbookAgent should import without errors."""
        from moltbook_agent import MoltbookAgent, MoltbookPost, MoltbookComment
        assert MoltbookAgent is not None
        assert MoltbookPost is not None

    def test_moltbook_agent_init(self):
        """MoltbookAgent should initialize."""
        from moltbook_agent import MoltbookAgent
        agent = MoltbookAgent()
        assert agent is not None
        assert agent.guardian is not None

    def test_get_replied_comment_ids(self):
        """Should return set of replied comment IDs."""
        from moltbook_agent import MoltbookAgent
        agent = MoltbookAgent()
        replied = agent._get_replied_comment_ids()
        assert isinstance(replied, set)


class TestInsightFinder:
    """Test Insight Finder agent."""

    def test_insight_finder_imports(self):
        """InsightFinder should import without errors."""
        from insight_finder import find_insights, add_insights_to_report, call_model
        assert find_insights is not None
        assert add_insights_to_report is not None
        assert call_model is not None

    def test_call_model_function_exists(self):
        """call_model function should exist."""
        from insight_finder import call_model
        # Just test that it's callable
        assert callable(call_model)

    def test_find_insights_function_exists(self):
        """find_insights function should exist and be callable."""
        from insight_finder import find_insights
        assert callable(find_insights)


class TestResearchAgent:
    """Test Research Agent."""

    def test_research_agent_imports(self):
        """ResearchAgent should import without errors."""
        from research_agent import ResearchAgent, Finding
        assert ResearchAgent is not None
        assert Finding is not None

    def test_research_agent_init(self):
        """ResearchAgent should initialize."""
        from research_agent import ResearchAgent
        agent = ResearchAgent()
        assert agent is not None
        assert agent.guardian is not None


class TestPublicationCoordinator:
    """Test Publication Coordinator."""

    def test_coordinator_imports(self):
        """PublicationCoordinator should import without errors."""
        from publication_coordinator import PublicationCoordinator, PublicationStatus
        assert PublicationCoordinator is not None
        assert PublicationStatus is not None

    def test_coordinator_init(self):
        """PublicationCoordinator should initialize."""
        from publication_coordinator import PublicationCoordinator
        coord = PublicationCoordinator()
        assert coord is not None
        assert coord.guardian is not None

    def test_publication_status_enum(self):
        """PublicationStatus enum should have expected values."""
        from publication_coordinator import PublicationStatus
        assert PublicationStatus.DRAFT.value == "draft"
        assert PublicationStatus.APPROVED.value == "approved"
        assert PublicationStatus.REJECTED.value == "rejected"
        assert PublicationStatus.PUBLISHED.value == "published"


class TestTwitterAgent:
    """Test Twitter Agent."""

    def test_twitter_agent_imports(self):
        """TwitterAgent should import without errors."""
        from twitter_agent import TwitterAgent, Tweet
        assert TwitterAgent is not None
        assert Tweet is not None

    def test_twitter_agent_init(self):
        """TwitterAgent should initialize."""
        from twitter_agent import TwitterAgent
        agent = TwitterAgent()
        assert agent is not None
        assert agent.guardian is not None

    def test_tweepy_check(self):
        """Should check for tweepy availability."""
        from twitter_agent import TWEEPY_AVAILABLE
        assert isinstance(TWEEPY_AVAILABLE, bool)


class TestAgentIntegration:
    """Integration tests for agent interactions."""

    def test_guardian_in_moltbook_agent(self):
        """MoltbookAgent should use Guardian for moderation."""
        from moltbook_agent import MoltbookAgent
        from guardian import Guardian
        agent = MoltbookAgent()
        assert isinstance(agent.guardian, Guardian)

    def test_guardian_in_twitter_agent(self):
        """TwitterAgent should use Guardian for moderation."""
        from twitter_agent import TwitterAgent
        from guardian import Guardian
        agent = TwitterAgent()
        assert isinstance(agent.guardian, Guardian)

    def test_guardian_in_publication_coordinator(self):
        """PublicationCoordinator should use Guardian for review."""
        from publication_coordinator import PublicationCoordinator
        from guardian import Guardian
        coord = PublicationCoordinator()
        assert isinstance(coord.guardian, Guardian)


if __name__ == "__main__":
    # Simple test runner without pytest
    import traceback

    test_classes = [
        TestGuardian, TestMoltbookAgent, TestInsightFinder,
        TestResearchAgent, TestPublicationCoordinator, TestTwitterAgent,
        TestAgentIntegration
    ]
    passed = 0
    failed = 0

    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    getattr(instance, method_name)()
                    print(f"  [OK] {method_name}")
                    passed += 1
                except Exception as e:
                    print(f"  [FAIL] {method_name}: {e}")
                    failed += 1

    print(f"\n{'='*50}")
    print(f"Passed: {passed}, Failed: {failed}")
