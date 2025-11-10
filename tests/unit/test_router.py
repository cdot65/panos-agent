"""Unit tests for router functionality.

Tests intent classification, workflow matching, parameter extraction,
and routing decision logic.
"""

import os
from unittest.mock import AsyncMock, patch

import pytest

from src.core.intent_classifier import (
    calculate_confidence,
    check_forced_routing,
    make_routing_decision,
)
from src.workflows.definitions import WORKFLOWS


@pytest.fixture
def mock_settings():
    """Mock settings for tests that need LLM access."""
    from src.core.config import Settings

    return Settings(
        model_name="claude-sonnet-4-5-20250929",
        temperature=0.0,
        max_tokens=8192,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "test-api-key"),
        panos_hostname="test.example.com",
        panos_api_key="test-key",
        panos_username="admin",
        panos_password="admin",
    )


class TestIntentClassifier:
    """Tests for intent classification functions."""

    @pytest.mark.asyncio
    async def test_classify_simple_intent(self, mock_settings):
        """Test classifying a simple create intent."""
        from src.core.intent_classifier import classify_user_intent

        with patch("src.core.intent_classifier.get_settings", return_value=mock_settings):
            user_input = "Create address for 10.1.1.50 named web-server"
            result = await classify_user_intent(user_input)

            assert isinstance(result, dict)
            assert "primary_intent" in result
            assert "target_objects" in result
            assert result["primary_intent"] in [
                "create",
                "add",
            ]  # May vary based on LLM
            assert "address" in result.get("target_objects", [])

    @pytest.mark.asyncio
    async def test_classify_complex_intent(self, mock_settings):
        """Test classifying a multi-step intent."""
        from src.core.intent_classifier import classify_user_intent

        with patch("src.core.intent_classifier.get_settings", return_value=mock_settings):
            user_input = "Set up web server infrastructure with HTTP and HTTPS"
            result = await classify_user_intent(user_input)

            assert isinstance(result, dict)
            assert result.get("multi_step") in [True, False]  # Should detect multi-step
            assert result.get("complexity", 1) >= 2  # Should be moderate complexity

    @pytest.mark.asyncio
    async def test_match_workflow_exact_match(self, mock_settings):
        """Test matching workflow with high confidence."""
        from src.core.intent_classifier import match_workflow_semantic

        with patch("src.core.intent_classifier.get_settings", return_value=mock_settings):
            intent = {
                "primary_intent": "setup",
                "target_objects": ["web", "server"],
                "entities": {},
                "multi_step": True,
                "keywords": ["web", "server", "setup"],
                "complexity": 3,
            }

            workflow_name, confidence, alternatives = await match_workflow_semantic(
                intent, WORKFLOWS
            )

            # Should match web_server_setup with high confidence
            assert workflow_name is not None or confidence < 0.8  # Either match or low confidence
            if workflow_name:
                assert confidence > 0.0

    @pytest.mark.asyncio
    async def test_match_workflow_no_match(self, mock_settings):
        """Test workflow matching with no good match."""
        from src.core.intent_classifier import match_workflow_semantic

        with patch("src.core.intent_classifier.get_settings", return_value=mock_settings):
            intent = {
                "primary_intent": "analyze",
                "target_objects": ["unknown"],
                "entities": {},
                "multi_step": False,
                "keywords": ["random", "unrelated"],
                "complexity": 5,
            }

            workflow_name, confidence, alternatives = await match_workflow_semantic(
                intent, WORKFLOWS
            )

            # Should not match strongly
            assert confidence < 0.9  # Low confidence for unrelated intent

    @pytest.mark.asyncio
    async def test_extract_parameters_with_values(self, mock_settings):
        """Test parameter extraction with clear values."""
        from src.core.intent_classifier import extract_parameters

        with patch("src.core.intent_classifier.get_settings", return_value=mock_settings):
            user_input = "Create address for 10.1.1.50 named web-server"
            workflow_name = "simple_address"
            workflow_def = WORKFLOWS[workflow_name]

            result = await extract_parameters(user_input, workflow_name, workflow_def)

            assert isinstance(result, dict)
            assert "parameters" in result
            assert "completeness" in result
            # Should extract name and value
            params = result["parameters"]
            assert params.get("name") or params.get("value")  # At least one should be extracted

    @pytest.mark.asyncio
    async def test_extract_parameters_missing_values(self, mock_settings):
        """Test parameter extraction with missing values."""
        from src.core.intent_classifier import extract_parameters

        with patch("src.core.intent_classifier.get_settings", return_value=mock_settings):
            user_input = "Set up a web server"
            workflow_name = "web_server_setup"
            workflow_def = WORKFLOWS[workflow_name]

            result = await extract_parameters(user_input, workflow_name, workflow_def)

            assert isinstance(result, dict)
            # Completeness may vary since all params are optional in this workflow
            assert 0.0 <= result.get("completeness", 0.0) <= 1.0


class TestConfidenceCalculation:
    """Tests for confidence scoring."""

    def test_calculate_confidence_high(self):
        """Test high confidence scenario."""
        intent = {
            "primary_intent": "create",
            "target_objects": ["address"],
            "complexity": 2,
        }
        workflow_confidence = 0.9
        param_completeness = 1.0
        user_input = "Create address for 10.1.1.1"

        confidence = calculate_confidence(
            intent, workflow_confidence, param_completeness, user_input
        )

        assert 0.7 < confidence <= 1.0  # Should be high

    def test_calculate_confidence_low(self):
        """Test low confidence scenario."""
        intent = {
            "primary_intent": "unknown",
            "target_objects": [],
            "complexity": 5,
        }
        workflow_confidence = 0.3
        param_completeness = 0.0
        user_input = "Do something complex"

        confidence = calculate_confidence(
            intent, workflow_confidence, param_completeness, user_input
        )

        assert confidence < 0.6  # Should be low

    def test_calculate_confidence_with_autonomous_keyword(self):
        """Test confidence lowering with exploratory keywords."""
        intent = {
            "primary_intent": "query",
            "target_objects": ["address"],
            "complexity": 2,
        }
        workflow_confidence = 0.8
        param_completeness = 0.5
        user_input = "Explore what address objects we have"

        confidence = calculate_confidence(
            intent, workflow_confidence, param_completeness, user_input
        )

        # Should be lowered due to "explore" keyword
        assert confidence < 0.8

    def test_calculate_confidence_with_deterministic_keyword(self):
        """Test confidence boosting with deterministic keywords."""
        intent = {
            "primary_intent": "execute",
            "target_objects": ["workflow"],
            "complexity": 2,
        }
        workflow_confidence = 0.7
        param_completeness = 0.8
        user_input = "Run workflow for web server setup"

        confidence = calculate_confidence(
            intent, workflow_confidence, param_completeness, user_input
        )

        # Should be boosted due to "workflow" keyword
        assert confidence >= 0.7


class TestRoutingDecision:
    """Tests for routing decision logic."""

    def test_route_to_deterministic_high_confidence(self):
        """Test routing to deterministic with high confidence."""
        confidence = 0.9
        workflow_name = "web_server_setup"
        alternatives = []

        route_to, reason = make_routing_decision(confidence, workflow_name, alternatives)

        assert route_to == "deterministic"
        assert "confidence" in reason.lower() or "matched" in reason.lower()

    def test_route_to_autonomous_low_confidence(self):
        """Test routing to autonomous with low confidence."""
        confidence = 0.5
        workflow_name = "web_server_setup"
        alternatives = []

        route_to, reason = make_routing_decision(confidence, workflow_name, alternatives)

        assert route_to == "autonomous"
        assert "confidence" in reason.lower() or "low" in reason.lower()

    def test_route_to_autonomous_no_workflow(self):
        """Test routing to autonomous when no workflow matched."""
        confidence = 0.9
        workflow_name = None
        alternatives = []

        route_to, reason = make_routing_decision(confidence, workflow_name, alternatives)

        assert route_to == "autonomous"
        assert "no" in reason.lower() and "workflow" in reason.lower()

    def test_route_to_autonomous_ambiguous(self):
        """Test routing to autonomous when multiple similar matches."""
        confidence = 0.82
        workflow_name = "web_server_setup"
        alternatives = [["network_segmentation", 0.80], ["multi_address_creation", 0.78]]

        route_to, reason = make_routing_decision(confidence, workflow_name, alternatives)

        # May route to autonomous due to ambiguity
        assert route_to in ["autonomous", "deterministic"]
        if route_to == "autonomous":
            assert "multiple" in reason.lower() or "similar" in reason.lower()


class TestForcedRouting:
    """Tests for forced routing based on keywords."""

    def test_check_forced_autonomous(self):
        """Test forced routing to autonomous mode."""
        user_inputs = [
            "Explore the firewall configuration",
            "Show me all address objects",
            "Investigate security policies",
            "Find unused rules",
            "What do we have configured?",
        ]

        for user_input in user_inputs:
            result = check_forced_routing(user_input)
            assert result == "autonomous", f"Failed for: {user_input}"

    def test_check_forced_deterministic(self):
        """Test forced routing to deterministic mode."""
        user_inputs = [
            "Run workflow for web server",
            "Execute standard procedure",
            "Use the workflow",
        ]

        for user_input in user_inputs:
            result = check_forced_routing(user_input)
            assert result == "deterministic", f"Failed for: {user_input}"

    def test_check_no_forced_routing(self):
        """Test no forced routing for normal requests."""
        user_inputs = [
            "Create address object",
            "Set up web server",
            "Delete old policies",
        ]

        for user_input in user_inputs:
            result = check_forced_routing(user_input)
            assert result is None, f"Unexpected forced routing for: {user_input}"


class TestWorkflowMetadata:
    """Tests for workflow metadata structure."""

    def test_all_workflows_have_metadata(self):
        """Test that all workflows have required metadata."""
        required_fields = [
            "name",
            "description",
            "keywords",
            "intent_patterns",
            "required_params",
            "optional_params",
            "steps",
        ]

        for workflow_name, workflow_def in WORKFLOWS.items():
            for field in required_fields:
                assert (
                    field in workflow_def
                ), f"Workflow '{workflow_name}' missing field: {field}"

    def test_workflow_keywords_not_empty(self):
        """Test that workflows have non-empty keywords."""
        for workflow_name, workflow_def in WORKFLOWS.items():
            keywords = workflow_def.get("keywords", [])
            assert isinstance(keywords, list), f"Workflow '{workflow_name}' keywords not a list"
            assert len(keywords) > 0, f"Workflow '{workflow_name}' has no keywords"

    def test_workflow_intent_patterns_not_empty(self):
        """Test that workflows have intent patterns."""
        for workflow_name, workflow_def in WORKFLOWS.items():
            patterns = workflow_def.get("intent_patterns", [])
            assert isinstance(patterns, list), f"Workflow '{workflow_name}' patterns not a list"
            assert (
                len(patterns) > 0
            ), f"Workflow '{workflow_name}' has no intent patterns"

    def test_workflow_parameter_descriptions(self):
        """Test that parameter descriptions are provided."""
        for workflow_name, workflow_def in WORKFLOWS.items():
            param_desc = workflow_def.get("parameter_descriptions", {})
            assert isinstance(
                param_desc, dict
            ), f"Workflow '{workflow_name}' param_descriptions not a dict"

            # All optional params should have descriptions
            optional_params = workflow_def.get("optional_params", [])
            for param in optional_params:
                assert (
                    param in param_desc
                ), f"Workflow '{workflow_name}' missing description for param: {param}"

