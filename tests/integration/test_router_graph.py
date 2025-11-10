"""Integration tests for router graph.

Tests full routing flow from user input to execution selection.
"""

import pytest
from langchain_core.messages import HumanMessage
from langgraph.store.memory import InMemoryStore

from src.core.checkpoint_manager import get_checkpointer
from src.router_graph import create_router_graph


class TestRouterGraph:
    """Integration tests for router graph."""

    @pytest.mark.asyncio
    async def test_router_graph_initialization(self):
        """Test router graph can be created and initialized."""
        config = {
            "configurable": {
                "checkpointer": get_checkpointer(),
                "store": InMemoryStore(),
            }
        }

        graph = create_router_graph(config)
        assert graph is not None

    @pytest.mark.asyncio
    async def test_router_classify_workflow_request(self):
        """Test router classifies a workflow-matching request."""
        config = {
            "configurable": {
                "thread_id": "test-workflow-123",
                "checkpointer": get_checkpointer(),
                "store": InMemoryStore(),
            }
        }

        graph = create_router_graph(config)

        # Request that should match a workflow
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content="Set up web server infrastructure")]},
            config=config,
        )

        assert "route_to" in result
        assert result["route_to"] in ["autonomous", "deterministic"]
        assert "confidence_score" in result
        assert 0.0 <= result["confidence_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_router_classify_exploratory_request(self):
        """Test router classifies an exploratory request."""
        config = {
            "configurable": {
                "thread_id": "test-explore-456",
                "checkpointer": get_checkpointer(),
                "store": InMemoryStore(),
            }
        }

        graph = create_router_graph(config)

        # Request with exploratory keyword
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content="Show me all address objects")]},
            config=config,
        )

        assert "route_to" in result
        # Should route to autonomous due to "show me" keyword
        assert result["route_to"] == "autonomous"

    @pytest.mark.asyncio
    async def test_router_forced_deterministic(self):
        """Test router respects forced deterministic routing."""
        config = {
            "configurable": {
                "thread_id": "test-forced-789",
                "checkpointer": get_checkpointer(),
                "store": InMemoryStore(),
            }
        }

        graph = create_router_graph(config)

        # Request with deterministic keyword
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content="Run workflow web_server_setup")]},
            config=config,
        )

        assert "route_to" in result
        # Should route to deterministic due to "workflow" keyword
        assert result["route_to"] == "deterministic"

    @pytest.mark.asyncio
    async def test_router_parameter_extraction(self):
        """Test router extracts parameters from request."""
        config = {
            "configurable": {
                "thread_id": "test-params-101",
                "checkpointer": get_checkpointer(),
                "store": InMemoryStore(),
            }
        }

        graph = create_router_graph(config)

        # Request with specific parameters
        result = await graph.ainvoke(
            {
                "messages": [
                    HumanMessage(content="Create address for 10.1.1.50 named web-server")
                ]
            },
            config=config,
        )

        assert "route_to" in result
        # Should have attempted parameter extraction if workflow matched
        if result.get("matched_workflow"):
            assert "extracted_params" in result

    @pytest.mark.asyncio
    async def test_router_state_structure(self):
        """Test router returns proper state structure."""
        config = {
            "configurable": {
                "thread_id": "test-state-202",
                "checkpointer": get_checkpointer(),
                "store": InMemoryStore(),
            }
        }

        graph = create_router_graph(config)

        result = await graph.ainvoke(
            {"messages": [HumanMessage(content="Create some addresses")]},
            config=config,
        )

        # Verify required state fields
        assert "messages" in result
        assert "user_request" in result
        assert "route_to" in result
        assert "routing_reason" in result
        assert result["route_to"] in ["autonomous", "deterministic"]


class TestRouterSubgraph:
    """Tests for router subgraph components."""

    @pytest.mark.asyncio
    async def test_router_subgraph_parse_request(self):
        """Test router subgraph can parse user requests."""
        from src.core.subgraphs.router import create_router_subgraph

        router = create_router_subgraph()
        assert router is not None

        # Basic invocation test
        result = await router.ainvoke(
            {
                "messages": [HumanMessage(content="Test request")],
                "user_request": "",
                "intent_classification": None,
                "matched_workflow": None,
                "workflow_alternatives": None,
                "extracted_params": None,
                "confidence_score": None,
                "route_to": None,
                "routing_reason": None,
                "device_context": None,
            }
        )

        assert "route_to" in result
        assert result["route_to"] in ["autonomous", "deterministic"]


class TestWorkflowDiscoveryIntegration:
    """Integration tests for workflow discovery tools."""

    def test_discover_workflows_tool(self):
        """Test workflow discovery tool."""
        from src.tools.workflow_discovery import discover_workflows

        # List all workflows
        result = discover_workflows("")
        assert isinstance(result, str)
        assert "workflow" in result.lower()

    def test_discover_workflows_with_intent(self):
        """Test workflow discovery with specific intent."""
        from src.tools.workflow_discovery import discover_workflows

        result = discover_workflows("web server")
        assert isinstance(result, str)
        # Should find web_server_setup
        assert "web" in result.lower() or "no workflow" in result.lower()

    def test_get_workflow_details(self):
        """Test getting workflow details."""
        from src.tools.workflow_discovery import get_workflow_details

        result = get_workflow_details("web_server_setup")
        assert isinstance(result, str)
        assert "web" in result.lower()
        assert "step" in result.lower()

    def test_get_workflow_details_invalid(self):
        """Test getting details for non-existent workflow."""
        from src.tools.workflow_discovery import get_workflow_details

        result = get_workflow_details("nonexistent_workflow")
        assert isinstance(result, str)
        assert "not found" in result.lower()

