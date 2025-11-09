"""Unit tests for autonomous graph nodes."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from langgraph.graph import END

from src.autonomous_graph import call_agent, route_after_agent
from src.core.state_schemas import AutonomousState
from src.core.config import AgentContext


class TestCallAgent:
    """Tests for call_agent node."""

    @pytest.mark.asyncio
    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.autonomous_graph.get_settings")
    @patch("src.autonomous_graph.get_firewall_operation_summary")
    async def test_call_agent_returns_response(
        self, mock_get_summary, mock_settings, mock_chat_anthropic
    ):
        """Test that call_agent returns AIMessage response."""
        # Setup mocks
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.panos_hostname = "192.168.1.1"
        mock_get_summary.return_value = {}  # No memory context
        mock_llm = Mock()
        mock_response = AIMessage(content="I'll list the address objects for you.")
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Create state and runtime context
        state: AutonomousState = {"messages": [HumanMessage(content="List address objects")]}
        runtime = Mock()
        runtime.context = AgentContext()  # Default context
        store = Mock()

        # Call function
        result = await call_agent(state, runtime=runtime, store=store)

        # Assertions
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        assert result["messages"][0].content == "I'll list the address objects for you."

    @pytest.mark.asyncio
    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.autonomous_graph.get_settings")
    @patch("src.autonomous_graph.get_firewall_operation_summary")
    async def test_call_agent_with_tool_call(
        self, mock_get_summary, mock_settings, mock_chat_anthropic
    ):
        """Test that call_agent handles tool calls."""
        # Setup mocks
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.panos_hostname = "192.168.1.1"
        mock_get_summary.return_value = {}
        mock_llm = Mock()
        mock_response = AIMessage(
            content="",
            tool_calls=[{"name": "address_list", "args": {}, "id": "call_123"}],
        )
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Create state and runtime context
        state: AutonomousState = {"messages": [HumanMessage(content="List address objects")]}
        runtime = Mock()
        runtime.context = AgentContext()
        store = Mock()

        # Call function
        result = await call_agent(state, runtime=runtime, store=store)

        # Assertions
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert hasattr(result["messages"][0], "tool_calls")
        assert len(result["messages"][0].tool_calls) == 1
        assert result["messages"][0].tool_calls[0]["name"] == "address_list"

    @pytest.mark.asyncio
    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.autonomous_graph.get_settings")
    @patch("src.autonomous_graph.get_firewall_operation_summary")
    async def test_call_agent_prepends_system_message(
        self, mock_get_summary, mock_settings, mock_chat_anthropic
    ):
        """Test that call_agent prepends system message to conversation."""
        # Setup mocks
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.panos_hostname = "192.168.1.1"
        mock_get_summary.return_value = {}
        mock_llm = Mock()
        mock_response = AIMessage(content="Response")
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Create state and runtime context
        state: AutonomousState = {"messages": [HumanMessage(content="Hello")]}
        runtime = Mock()
        runtime.context = AgentContext()
        store = Mock()

        # Call function
        await call_agent(state, runtime=runtime, store=store)

        # Verify LLM was called with system message prepended
        assert mock_llm.ainvoke.called
        call_args = mock_llm.ainvoke.call_args[0][0]
        assert len(call_args) == 2  # System message + user message
        assert "autonomous mode" in call_args[0].content.lower()


class TestRouteAfterAgent:
    """Tests for route_after_agent routing function."""

    def test_route_to_tools_with_tool_calls(self):
        """Test routing to 'tools' when agent makes tool calls."""
        # Create state with tool calls
        state: AutonomousState = {
            "messages": [
                HumanMessage(content="List address objects"),
                AIMessage(
                    content="",
                    tool_calls=[{"name": "address_list", "args": {}, "id": "call_123"}],
                ),
            ]
        }

        # Call routing function
        result = route_after_agent(state)

        # Should route to tools
        assert result == "tools"

    def test_route_to_end_without_tool_calls(self):
        """Test routing to END when agent doesn't make tool calls."""
        # Create state without tool calls
        state: AutonomousState = {
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hello! I'm a PAN-OS automation agent."),
            ]
        }

        # Call routing function
        result = route_after_agent(state)

        # Should route to END
        assert result == END

    def test_route_to_end_with_empty_tool_calls(self):
        """Test routing to END when tool_calls is empty list."""
        # Create message with empty tool_calls
        message = AIMessage(content="Done!")
        message.tool_calls = []

        state: AutonomousState = {
            "messages": [HumanMessage(content="Test"), message]
        }

        # Call routing function
        result = route_after_agent(state)

        # Should route to END
        assert result == END

    def test_route_to_tools_with_multiple_tool_calls(self):
        """Test routing to 'tools' with multiple tool calls."""
        # Create state with multiple tool calls
        state: AutonomousState = {
            "messages": [
                HumanMessage(content="Create three address objects"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {"name": "address_create", "args": {"name": "addr1"}, "id": "call_1"},
                        {"name": "address_create", "args": {"name": "addr2"}, "id": "call_2"},
                        {"name": "address_create", "args": {"name": "addr3"}, "id": "call_3"},
                    ],
                ),
            ]
        }

        # Call routing function
        result = route_after_agent(state)

        # Should route to tools
        assert result == "tools"


class TestCallAgentRuntimeContext:
    """Tests for call_agent with runtime context."""

    @pytest.mark.asyncio
    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.autonomous_graph.get_settings")
    @patch("src.autonomous_graph.get_firewall_operation_summary")
    async def test_call_agent_uses_runtime_model_name(
        self, mock_get_summary, mock_settings, mock_chat_anthropic
    ):
        """Test that call_agent uses model_name from runtime context."""
        # Setup mocks
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.panos_hostname = "192.168.1.1"
        mock_get_summary.return_value = {}
        mock_llm = Mock()
        mock_response = AIMessage(content="Done")
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Create state and runtime context with custom model
        state: AutonomousState = {"messages": [HumanMessage(content="test")]}
        runtime = Mock()
        runtime.context = AgentContext(model_name="claude-haiku-4-5")
        store = Mock()

        # Call function
        await call_agent(state, runtime=runtime, store=store)

        # Verify ChatAnthropic was called with runtime model name
        assert mock_chat_anthropic.called
        call_kwargs = mock_chat_anthropic.call_args[1]
        assert call_kwargs["model"] == "claude-haiku-4-5"

    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.autonomous_graph.get_settings")
    @patch("src.autonomous_graph.get_firewall_operation_summary")
    @pytest.mark.asyncio
    async def test_call_agent_uses_runtime_temperature(
        self, mock_get_summary, mock_settings, mock_chat_anthropic
    ):
        """Test that call_agent uses temperature from runtime context."""
        # Setup mocks
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.panos_hostname = "192.168.1.1"
        mock_get_summary.return_value = {}
        mock_llm = Mock()
        mock_response = AIMessage(content="Done")
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Create state and runtime context with custom temperature
        state: AutonomousState = {"messages": [HumanMessage(content="test")]}
        runtime = Mock()
        runtime.context = AgentContext(temperature=0.7)
        store = Mock()

        # Call function
        await call_agent(state, runtime=runtime, store=store)

        # Verify ChatAnthropic was called with runtime temperature
        assert mock_chat_anthropic.called
        call_kwargs = mock_chat_anthropic.call_args[1]
        assert call_kwargs["temperature"] == 0.7

    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.autonomous_graph.get_settings")
    @patch("src.autonomous_graph.get_firewall_operation_summary")
    @pytest.mark.asyncio
    async def test_call_agent_uses_runtime_max_tokens(
        self, mock_get_summary, mock_settings, mock_chat_anthropic
    ):
        """Test that call_agent uses max_tokens from runtime context."""
        # Setup mocks
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.panos_hostname = "192.168.1.1"
        mock_get_summary.return_value = {}
        mock_llm = Mock()
        mock_response = AIMessage(content="Done")
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Create state and runtime context with custom max_tokens
        state: AutonomousState = {"messages": [HumanMessage(content="test")]}
        runtime = Mock()
        runtime.context = AgentContext(max_tokens=8192)
        store = Mock()

        # Call function
        await call_agent(state, runtime=runtime, store=store)

        # Verify ChatAnthropic was called with runtime max_tokens
        assert mock_chat_anthropic.called
        call_kwargs = mock_chat_anthropic.call_args[1]
        assert call_kwargs["max_tokens"] == 8192

    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.autonomous_graph.get_settings")
    @patch("src.autonomous_graph.get_firewall_operation_summary")
    @pytest.mark.asyncio
    async def test_call_agent_with_all_runtime_params(
        self, mock_get_summary, mock_settings, mock_chat_anthropic
    ):
        """Test that call_agent uses all parameters from runtime context."""
        # Setup mocks
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.panos_hostname = "192.168.1.1"
        mock_get_summary.return_value = {}
        mock_llm = Mock()
        mock_response = AIMessage(content="Done")
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Create state and runtime context with all custom values
        state: AutonomousState = {"messages": [HumanMessage(content="test")]}
        runtime = Mock()
        runtime.context = AgentContext(
            model_name="claude-3-opus-20240229",
            temperature=0.5,
            max_tokens=16384,
        )
        store = Mock()

        # Call function
        await call_agent(state, runtime=runtime, store=store)

        # Verify ChatAnthropic was called with all runtime parameters
        assert mock_chat_anthropic.called
        call_kwargs = mock_chat_anthropic.call_args[1]
        assert call_kwargs["model"] == "claude-3-opus-20240229"
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 16384

    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.autonomous_graph.get_settings")
    @patch("src.autonomous_graph.get_firewall_operation_summary")
    @pytest.mark.asyncio
    async def test_call_agent_haiku_configuration(
        self, mock_get_summary, mock_settings, mock_chat_anthropic
    ):
        """Test call_agent with Haiku model for fast operations."""
        # Setup mocks
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.panos_hostname = "192.168.1.1"
        mock_get_summary.return_value = {}
        mock_llm = Mock()
        mock_response = AIMessage(content="Done")
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Create state and runtime context for Haiku
        state: AutonomousState = {"messages": [HumanMessage(content="List objects")]}
        runtime = Mock()
        runtime.context = AgentContext(
            model_name="claude-haiku-4-5", temperature=0.0  # Fast, deterministic
        )
        store = Mock()

        # Call function
        await call_agent(state, runtime=runtime, store=store)

        # Verify Haiku configuration
        call_kwargs = mock_chat_anthropic.call_args[1]
        assert "haiku" in call_kwargs["model"].lower()
        assert call_kwargs["temperature"] == 0.0

    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.autonomous_graph.get_settings")
    @patch("src.autonomous_graph.get_firewall_operation_summary")
    @pytest.mark.asyncio
    async def test_call_agent_opus_configuration(
        self, mock_get_summary, mock_settings, mock_chat_anthropic
    ):
        """Test call_agent with Opus model for complex operations."""
        # Setup mocks
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.panos_hostname = "192.168.1.1"
        mock_get_summary.return_value = {}
        mock_llm = Mock()
        mock_response = AIMessage(content="Done")
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Create state and runtime context for Opus
        state: AutonomousState = {
            "messages": [HumanMessage(content="Analyze security policies")]
        }
        runtime = Mock()
        runtime.context = AgentContext(
            model_name="claude-3-opus-20240229",
            temperature=0.0,
            max_tokens=8192,  # More tokens for complex analysis
        )
        store = Mock()

        # Call function
        await call_agent(state, runtime=runtime, store=store)

        # Verify Opus configuration
        call_kwargs = mock_chat_anthropic.call_args[1]
        assert "opus" in call_kwargs["model"].lower()
        assert call_kwargs["max_tokens"] == 8192
