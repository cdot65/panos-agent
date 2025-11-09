"""Integration tests for autonomous (ReAct) graph.

Tests full graph execution from user input to final response.
"""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


class TestAutonomousGraphExecution:
    """Test autonomous graph end-to-end execution."""

    @pytest.mark.asyncio
    @patch("src.autonomous_graph.ChatAnthropic")
    async def test_simple_query_no_tools(
        self, mock_chat_anthropic, autonomous_graph, test_thread_id
    ):
        """Test simple conversational query without tool calls."""
        # Mock LLM response
        mock_llm = AsyncMock()
        mock_response = AIMessage(content="Hello! I'm doing well, thank you for asking.")
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Execute graph
        result = await autonomous_graph.ainvoke(
            {"messages": [HumanMessage(content="Hello, how are you?")]},
            config={"configurable": {"thread_id": test_thread_id}},
        )

        # Verify response structure
        assert "messages" in result
        assert len(result["messages"]) > 0

        # Last message should be AI response
        last_message = result["messages"][-1]
        assert isinstance(last_message, AIMessage)
        assert last_message.content  # Has content

        # Should not have tool calls for greeting
        assert not hasattr(last_message, "tool_calls") or not last_message.tool_calls

    @pytest.mark.asyncio
    @patch("src.autonomous_graph.ChatAnthropic")
    @patch("src.tools.address_objects.address_list")
    async def test_query_with_single_tool(
        self, mock_address_list, mock_chat_anthropic, autonomous_graph, test_thread_id
    ):
        """Test query that triggers single tool execution."""
        # Mock tool response (async)
        mock_address_list.ainvoke = AsyncMock(return_value="✅ Found 5 address objects")

        # Mock LLM responses: first call returns tool call, second returns final response
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            side_effect=[
                AIMessage(
                    content="",
                    tool_calls=[{"name": "address_list", "args": {}, "id": "call_1"}],
                ),
                AIMessage(content="I found 5 address objects on the firewall."),
            ]
        )
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Execute graph
        result = await autonomous_graph.ainvoke(
            {"messages": [HumanMessage(content="List all address objects")]},
            config={"configurable": {"thread_id": test_thread_id}},
        )

        # Verify execution
        assert "messages" in result
        messages = result["messages"]

        # Should have: HumanMessage, AIMessage(tool_calls), ToolMessage, AIMessage(final)
        assert len(messages) >= 3

        # Check for tool execution
        has_tool_message = any(isinstance(msg, ToolMessage) for msg in messages)
        assert has_tool_message, "Should have executed a tool"

        # Final message should be AI response
        last_message = messages[-1]
        assert isinstance(last_message, AIMessage)

    @pytest.mark.asyncio
    @patch("src.autonomous_graph.ChatAnthropic")
    async def test_conversation_continuity(
        self, mock_chat_anthropic, autonomous_graph, test_thread_id
    ):
        """Test that conversation history is maintained across invocations."""
        # Mock LLM responses
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            side_effect=[
                AIMessage(content="Nice to meet you, Alice!"),
                AIMessage(content="Your name is Alice."),
            ]
        )
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # First message
        result1 = await autonomous_graph.ainvoke(
            {"messages": [HumanMessage(content="My name is Alice")]},
            config={"configurable": {"thread_id": test_thread_id}},
        )

        # Second message referencing first
        result2 = await autonomous_graph.ainvoke(
            {"messages": [HumanMessage(content="What is my name?")]},
            config={"configurable": {"thread_id": test_thread_id}},
        )

        # Verify history is maintained
        assert "messages" in result2
        messages = result2["messages"]

        # Should have all messages from both invocations
        assert len(messages) >= 4  # 2 human + 2 AI minimum

        # Check that both human messages are present
        human_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
        assert len(human_messages) >= 2

    @pytest.mark.asyncio
    @patch("src.autonomous_graph.ChatAnthropic")
    async def test_fresh_thread_no_history(self, mock_chat_anthropic, autonomous_graph):
        """Test that different thread IDs create independent conversations."""
        # Mock LLM responses - need separate mocks for each invocation
        mock_llm_1 = AsyncMock()
        mock_llm_1.ainvoke = AsyncMock(return_value=AIMessage(content="Blue is a great color!"))

        mock_llm_2 = AsyncMock()
        mock_llm_2.ainvoke = AsyncMock(return_value=AIMessage(content="Hello! How can I help you?"))

        # Set up side_effect to return different mocks for each call
        mock_chat_anthropic.return_value.bind_tools.side_effect = [mock_llm_1, mock_llm_2]

        # First conversation with unique thread ID (use UUID to ensure isolation)
        thread_id_1 = f"test-thread-{uuid.uuid4()}"
        result1 = await autonomous_graph.ainvoke(
            {"messages": [HumanMessage(content="My favorite color is blue")]},
            config={"configurable": {"thread_id": thread_id_1}},
        )

        # Second conversation with different thread ID (use UUID to ensure isolation)
        thread_id_2 = f"test-thread-{uuid.uuid4()}"
        result2 = await autonomous_graph.ainvoke(
            {"messages": [HumanMessage(content="Hello")]},
            config={"configurable": {"thread_id": thread_id_2}},
        )

        # Second conversation should not have first conversation's messages
        # Filter to only messages from this thread (checkpoint isolation)
        messages = result2["messages"]
        human_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]

        # Should only have one human message (the greeting) - check content matches
        hello_messages = [msg for msg in human_messages if msg.content == "Hello"]
        assert (
            len(hello_messages) == 1
        ), f"Expected 1 'Hello' message, found {len(hello_messages)}. All human messages: {[m.content for m in human_messages]}"
        assert hello_messages[0].content == "Hello"


class TestAutonomousGraphCheckpointing:
    """Test checkpoint and resume functionality."""

    @pytest.mark.asyncio
    @patch("src.autonomous_graph.ChatAnthropic")
    async def test_checkpoint_after_execution(
        self, mock_chat_anthropic, autonomous_graph, test_thread_id
    ):
        """Test that state is checkpointed after execution."""
        # Mock LLM response
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Test response"))
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # Execute graph
        await autonomous_graph.ainvoke(
            {"messages": [HumanMessage(content="Test message")]},
            config={"configurable": {"thread_id": test_thread_id}},
        )

        # Get state to verify checkpoint exists (async checkpointer requires async get_state)
        config = {"configurable": {"thread_id": test_thread_id}}
        state = await autonomous_graph.aget_state(config)

        # Verify checkpoint was created
        assert state is not None
        assert hasattr(state, "values")
        assert "messages" in state.values

    @pytest.mark.asyncio
    @patch("src.autonomous_graph.ChatAnthropic")
    async def test_resume_from_checkpoint(
        self, mock_chat_anthropic, autonomous_graph, test_thread_id
    ):
        """Test resuming conversation from checkpoint."""
        # Mock LLM responses
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            side_effect=[
                AIMessage(content="I'll remember the number 42."),
                AIMessage(content="You told me the number 42."),
            ]
        )
        mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm

        # First execution
        result1 = await autonomous_graph.ainvoke(
            {"messages": [HumanMessage(content="Remember the number 42")]},
            config={"configurable": {"thread_id": test_thread_id}},
        )

        # Resume with same thread
        result2 = await autonomous_graph.ainvoke(
            {"messages": [HumanMessage(content="What number did I tell you?")]},
            config={"configurable": {"thread_id": test_thread_id}},
        )

        # Verify conversation continuity
        messages = result2["messages"]
        assert len(messages) >= 4  # Both exchanges

        # Should have both human messages
        human_contents = [msg.content for msg in messages if isinstance(msg, HumanMessage)]
        assert "Remember the number 42" in human_contents
        assert "What number did I tell you?" in human_contents
