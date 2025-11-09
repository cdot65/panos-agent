"""Integration tests for runtime context across the full stack."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from src.core.config import AgentContext
from src.autonomous_graph import create_autonomous_graph


class TestRuntimeContextIntegration:
    """Integration tests for runtime context flowing through the graph."""

    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.autonomous_graph.get_settings")
    @patch("src.autonomous_graph.get_firewall_operation_summary")
    def test_graph_with_haiku_model(
        self, mock_get_summary, mock_settings, mock_chat_anthropic
    ):
        """Test full graph execution with Haiku model via runtime context."""
        # Setup mocks
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.panos_hostname = "192.168.1.1"
        mock_get_summary.return_value = {}

        mock_llm = Mock()
        # Return AIMessage without tool calls (ends graph)
        mock_response = AIMessage(content="List complete")
        mock_llm.invoke.return_value = mock_response
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Create graph
        graph = create_autonomous_graph()

        # Execute graph with Haiku model context
        result = graph.invoke(
            {"messages": [HumanMessage(content="List address objects")]},
            config={
                "configurable": {
                    "thread_id": "test-haiku-1",
                    "model_name": "claude-haiku-4-5",
                    "temperature": 0.0,
                }
            },
        )

        # Verify graph completed
        assert "messages" in result
        assert len(result["messages"]) > 0

        # Verify Haiku model was used
        assert mock_chat_anthropic.called
        call_kwargs = mock_chat_anthropic.call_args[1]
        assert call_kwargs["model"] == "claude-haiku-4-5"

    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.autonomous_graph.get_settings")
    @patch("src.autonomous_graph.get_firewall_operation_summary")
    def test_graph_with_opus_model(
        self, mock_get_summary, mock_settings, mock_chat_anthropic
    ):
        """Test full graph execution with Opus model via runtime context."""
        # Setup mocks
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.panos_hostname = "192.168.1.1"
        mock_get_summary.return_value = {}

        mock_llm = Mock()
        mock_response = AIMessage(content="Analysis complete")
        mock_llm.invoke.return_value = mock_response
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Create graph
        graph = create_autonomous_graph()

        # Execute graph with Opus model context
        result = graph.invoke(
            {"messages": [HumanMessage(content="Analyze security policies")]},
            config={
                "configurable": {
                    "thread_id": "test-opus-1",
                    "model_name": "claude-3-opus-20240229",
                    "temperature": 0.0,
                    "max_tokens": 8192,
                }
            },
        )

        # Verify graph completed
        assert "messages" in result
        assert len(result["messages"]) > 0

        # Verify Opus model was used
        assert mock_chat_anthropic.called
        call_kwargs = mock_chat_anthropic.call_args[1]
        assert call_kwargs["model"] == "claude-3-opus-20240229"
        assert call_kwargs["max_tokens"] == 8192

    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.autonomous_graph.get_settings")
    @patch("src.autonomous_graph.get_firewall_operation_summary")
    def test_graph_with_custom_temperature(
        self, mock_get_summary, mock_settings, mock_chat_anthropic
    ):
        """Test graph execution with custom temperature setting."""
        # Setup mocks
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.panos_hostname = "192.168.1.1"
        mock_get_summary.return_value = {}

        mock_llm = Mock()
        mock_response = AIMessage(content="Creative response")
        mock_llm.invoke.return_value = mock_response
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Create graph
        graph = create_autonomous_graph()

        # Execute graph with higher temperature
        result = graph.invoke(
            {"messages": [HumanMessage(content="Suggest creative names")]},
            config={
                "configurable": {
                    "thread_id": "test-temp-1",
                    "model_name": "claude-3-5-sonnet-20241022",
                    "temperature": 0.7,
                }
            },
        )

        # Verify temperature was applied
        assert mock_chat_anthropic.called
        call_kwargs = mock_chat_anthropic.call_args[1]
        assert call_kwargs["temperature"] == 0.7

    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.autonomous_graph.get_settings")
    @patch("src.autonomous_graph.get_firewall_operation_summary")
    def test_graph_context_persists_across_steps(
        self, mock_get_summary, mock_settings, mock_chat_anthropic
    ):
        """Test that runtime context persists across multiple graph steps."""
        # Setup mocks
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.panos_hostname = "192.168.1.1"
        mock_get_summary.return_value = {}

        mock_llm = Mock()
        # First call: return tool call
        # Second call: return final response
        mock_llm.invoke.side_effect = [
            AIMessage(
                content="",
                tool_calls=[{"name": "address_list", "args": {}, "id": "call_1"}],
            ),
            AIMessage(content="Operation complete"),
        ]
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Mock tool execution
        from src.tools.address_objects import address_list

        with patch("src.autonomous_graph.ALL_TOOLS", [address_list]):
            with patch.object(address_list, "invoke", return_value="[]"):
                # Create graph
                graph = create_autonomous_graph()

                # Execute graph - will make two agent calls (tool call + final)
                result = graph.invoke(
                    {"messages": [HumanMessage(content="List addresses")]},
                    config={
                        "configurable": {
                            "thread_id": "test-persist-1",
                            "model_name": "claude-haiku-4-5",
                            "temperature": 0.0,
                        }
                    },
                )

                # Verify graph completed successfully
                assert "messages" in result

                # Verify Haiku model was used in BOTH calls
                assert mock_chat_anthropic.call_count >= 2
                for call in mock_chat_anthropic.call_args_list:
                    assert call[1]["model"] == "claude-haiku-4-5"
                    assert call[1]["temperature"] == 0.0


class TestRuntimeContextDefaults:
    """Tests for default runtime context values."""

    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.autonomous_graph.get_settings")
    @patch("src.autonomous_graph.get_firewall_operation_summary")
    def test_graph_with_default_context(
        self, mock_get_summary, mock_settings, mock_chat_anthropic
    ):
        """Test graph execution without explicit runtime context (uses defaults)."""
        # Setup mocks
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.panos_hostname = "192.168.1.1"
        mock_get_summary.return_value = {}

        mock_llm = Mock()
        mock_response = AIMessage(content="Done")
        mock_llm.invoke.return_value = mock_response
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Create graph
        graph = create_autonomous_graph()

        # Execute graph without model/temperature in config
        # Should use AgentContext defaults
        result = graph.invoke(
            {"messages": [HumanMessage(content="test")]},
            config={"configurable": {"thread_id": "test-default-1"}},
        )

        # Verify defaults were used
        assert mock_chat_anthropic.called
        call_kwargs = mock_chat_anthropic.call_args[1]
        # Should use AgentContext defaults
        assert call_kwargs["model"] == "claude-3-5-sonnet-20241022"  # default
        assert call_kwargs["temperature"] == 0.0  # default


class TestRuntimeContextErrorHandling:
    """Tests for error handling with runtime context."""

    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.autonomous_graph.get_settings")
    @patch("src.autonomous_graph.get_firewall_operation_summary")
    def test_graph_handles_llm_error_with_runtime_context(
        self, mock_get_summary, mock_settings, mock_chat_anthropic
    ):
        """Test that graph handles LLM errors gracefully with runtime context."""
        # Setup mocks
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.panos_hostname = "192.168.1.1"
        mock_get_summary.return_value = {}

        mock_llm = Mock()
        # Simulate LLM error
        mock_llm.invoke.side_effect = Exception("LLM API error")
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Create graph
        graph = create_autonomous_graph()

        # Execute should raise exception
        with pytest.raises(Exception, match="LLM API error"):
            graph.invoke(
                {"messages": [HumanMessage(content="test")]},
                config={
                    "configurable": {
                        "thread_id": "test-error-1",
                        "model_name": "claude-haiku-4-5",
                        "temperature": 0.0,
                    }
                },
            )


class TestRuntimeContextModelComparison:
    """Tests comparing different models via runtime context."""

    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.autonomous_graph.get_settings")
    @patch("src.autonomous_graph.get_firewall_operation_summary")
    def test_haiku_vs_sonnet_model_selection(
        self, mock_get_summary, mock_settings, mock_chat_anthropic
    ):
        """Test that different model selections result in different LLM calls."""
        # Setup mocks
        mock_settings.return_value.anthropic_api_key = "test-key"
        mock_settings.return_value.panos_hostname = "192.168.1.1"
        mock_get_summary.return_value = {}

        mock_llm = Mock()
        mock_response = AIMessage(content="Done")
        mock_llm.invoke.return_value = mock_response
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Create graph
        graph = create_autonomous_graph()

        # Execute with Haiku
        graph.invoke(
            {"messages": [HumanMessage(content="test")]},
            config={
                "configurable": {
                    "thread_id": "test-haiku-2",
                    "model_name": "claude-haiku-4-5",
                }
            },
        )
        haiku_call_kwargs = mock_chat_anthropic.call_args[1]

        # Reset mock
        mock_chat_anthropic.reset_mock()

        # Execute with Sonnet
        graph.invoke(
            {"messages": [HumanMessage(content="test")]},
            config={
                "configurable": {
                    "thread_id": "test-sonnet-2",
                    "model_name": "claude-3-5-sonnet-20241022",
                }
            },
        )
        sonnet_call_kwargs = mock_chat_anthropic.call_args[1]

        # Verify different models were used
        assert haiku_call_kwargs["model"] == "claude-haiku-4-5"
        assert sonnet_call_kwargs["model"] == "claude-3-5-sonnet-20241022"
        assert haiku_call_kwargs["model"] != sonnet_call_kwargs["model"]

