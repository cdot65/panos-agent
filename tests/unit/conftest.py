"""Shared fixtures for unit tests."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from unittest.mock import Mock, MagicMock


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Auto-mock environment variables for all unit tests.
    
    Sets required PAN-OS and API credentials to prevent validation errors.
    """
    monkeypatch.setenv("PANOS_HOSTNAME", "192.168.1.1")
    monkeypatch.setenv("PANOS_USERNAME", "admin")
    monkeypatch.setenv("PANOS_PASSWORD", "admin")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    
    # Clear settings cache to ensure new environment variables are picked up
    import src.core.config
    src.core.config._settings = None


@pytest.fixture
def mock_llm():
    """Mock ChatAnthropic LLM for testing (async-aware)."""
    from unittest.mock import AsyncMock
    llm = Mock()
    # Mock response without tool calls
    mock_response = AIMessage(content="Hello! I'm a PAN-OS automation agent.")
    llm.ainvoke = AsyncMock(return_value=mock_response)
    llm.invoke = Mock(return_value=mock_response)  # Keep sync for backward compat
    return llm


@pytest.fixture
def mock_llm_with_tool_call():
    """Mock LLM that returns a tool call (async-aware)."""
    from unittest.mock import AsyncMock
    llm = Mock()
    # Mock response with tool calls
    mock_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "address_list",
                "args": {},
                "id": "call_123",
            }
        ],
    )
    llm.ainvoke = AsyncMock(return_value=mock_response)
    llm.invoke = Mock(return_value=mock_response)  # Keep sync for backward compat
    return llm


@pytest.fixture
def mock_state_autonomous():
    """Sample AutonomousState fixture."""
    return {
        "messages": [HumanMessage(content="List all address objects")],
    }


@pytest.fixture
def mock_state_deterministic():
    """Sample DeterministicState fixture."""
    return {
        "messages": [HumanMessage(content="simple_address")],
        "workflow_steps": [
            {
                "name": "Create address object",
                "type": "tool_call",
                "tool": "address_create",
                "params": {
                    "name": "demo-server",
                    "value": "192.168.1.100",
                },
            }
        ],
        "current_step_index": 0,
        "step_results": [],
        "continue_workflow": True,
        "workflow_complete": False,
        "error_occurred": False,
    }


@pytest.fixture
def mock_state_crud():
    """Sample CRUDState fixture."""
    return {
        "operation_type": "create",
        "object_type": "address",
        "object_name": "test-server",
        "data": {
            "name": "test-server",
            "value": "192.168.1.100",
        },
        "validation_result": None,
        "exists": False,
        "operation_result": None,
        "message": "",
        "error": None,
    }


@pytest.fixture
def mock_state_commit():
    """Sample CommitState fixture."""
    return {
        "description": "Test commit",
        "force": False,
        "approval_required": True,
        "approved": None,
        "job_id": None,
        "commit_result": None,
        "message": "",
        "error": None,
    }


@pytest.fixture
def mock_state_workflow():
    """Sample DeterministicWorkflowState fixture."""
    return {
        "workflow_name": "test_workflow",
        "workflow_params": {},
        "steps": [
            {
                "name": "Step 1",
                "type": "tool_call",
                "tool": "address_create",
                "params": {
                    "name": "{{server_name}}",
                    "value": "{{server_ip}}",
                },
            }
        ],
        "current_step": 0,
        "step_outputs": [],
        "overall_result": None,
        "message": "",
    }


@pytest.fixture
async def mock_panos_client(monkeypatch):
    """Mock httpx AsyncClient for PAN-OS API globally."""
    from unittest.mock import AsyncMock
    import httpx
    
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    
    # Mock successful responses
    from httpx import Response
    success_response = Response(
        200,
        content=b'<response status="success" code="20"><msg>command succeeded</msg></response>',
    )
    
    mock_client.get = AsyncMock(return_value=success_response)
    mock_client.post = AsyncMock(return_value=success_response)
    
    # Mock get_panos_client function
    async def mock_get_client():
        return mock_client
    
    monkeypatch.setattr("src.core.client.get_panos_client", mock_get_client)
    return mock_client


@pytest.fixture
def mock_tool():
    """Mock tool for testing."""
    tool = Mock()
    tool.name = "test_tool"
    tool.invoke.return_value = "✅ Tool executed successfully"
    return tool


@pytest.fixture
def sample_workflow_definition():
    """Sample workflow definition for testing."""
    return {
        "name": "test_workflow",
        "description": "Test workflow for unit tests",
        "steps": [
            {
                "name": "Create address",
                "type": "tool_call",
                "tool": "address_create",
                "params": {
                    "name": "test-addr",
                    "value": "10.1.1.1",
                },
            },
            {
                "name": "Verify creation",
                "type": "tool_call",
                "tool": "address_read",
                "params": {
                    "name": "test-addr",
                },
            },
        ],
    }
