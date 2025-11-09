"""Shared fixtures for integration tests.

Provides compiled graph fixtures and mock httpx client with respx.
"""

import os
import uuid
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
import pytest_asyncio
import respx
from httpx import Response


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Auto-mock environment variables for all integration tests.

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
def mock_panos_client():
    """Mock httpx AsyncClient for PAN-OS API integration tests.

    Returns:
        AsyncMock of httpx.AsyncClient with common responses
    """
    client = AsyncMock(spec=httpx.AsyncClient)

    # Mock successful API response
    success_response = Response(
        200,
        content=b'<response status="success" code="20"><msg>command succeeded</msg></response>',
    )

    # Default mock responses
    client.get = AsyncMock(return_value=success_response)
    client.post = AsyncMock(return_value=success_response)
    client.aclose = AsyncMock()

    return client


@pytest.fixture
def respx_mock():
    """Respx mock for HTTP requests.

    Yields:
        respx.MockRouter for mocking httpx requests
    """
    with respx.mock:
        # Mock PAN-OS API endpoints
        respx.route(host="192.168.1.1").mock(
            return_value=Response(
                200,
                content=b'<response status="success" code="20"><msg>command succeeded</msg></response>',
            )
        )
        yield respx


@pytest_asyncio.fixture
async def autonomous_graph(mock_panos_client):
    """Create autonomous graph with mocked httpx client and async checkpointer.

    Returns:
        Compiled autonomous StateGraph with async checkpointer
    """
    # Patch get_panos_client to return the mock client (using AsyncMock)
    mock_get_client = AsyncMock(return_value=mock_panos_client)

    with patch("src.core.client.get_panos_client", mock_get_client):
        from src.autonomous_graph import create_autonomous_graph
        from src.core.checkpoint_manager import get_async_checkpointer

        checkpointer = await get_async_checkpointer()
        graph = create_autonomous_graph(checkpointer=checkpointer)
        try:
            yield graph
        finally:
            # Clean up async checkpointer connection
            if hasattr(checkpointer, "conn") and checkpointer.conn:
                await checkpointer.conn.close()


@pytest_asyncio.fixture
async def deterministic_graph(mock_panos_client):
    """Create deterministic graph with mocked httpx client and async checkpointer.

    Returns:
        Compiled deterministic StateGraph with async checkpointer
    """
    # Patch get_panos_client to return the mock client (using AsyncMock)
    mock_get_client = AsyncMock(return_value=mock_panos_client)

    with patch("src.core.client.get_panos_client", mock_get_client):
        from src.core.checkpoint_manager import get_async_checkpointer
        from src.deterministic_graph import create_deterministic_graph

        checkpointer = await get_async_checkpointer()
        graph = create_deterministic_graph(checkpointer=checkpointer)
        try:
            yield graph
        finally:
            # Clean up async checkpointer connection
            if hasattr(checkpointer, "conn") and checkpointer.conn:
                await checkpointer.conn.close()


@pytest.fixture
def test_thread_id():
    """Generate unique thread ID for test isolation.

    Returns:
        UUID string for thread ID
    """
    return f"test-{uuid.uuid4()}"


@pytest.fixture
def sample_workflow():
    """Sample workflow definition for deterministic tests.

    Returns:
        Dict with workflow steps
    """
    return {
        "name": "test_workflow",
        "description": "Test workflow for integration tests",
        "steps": [
            {
                "name": "Create test address",
                "type": "tool_call",
                "tool": "crud_operation",
                "params": {
                    "operation": "create",
                    "object_type": "address",
                    "name": "test-server",
                    "data": {
                        "name": "test-server",
                        "value": "10.1.1.1",
                        "type": "ip-netmask",
                        "description": "Test address",
                    },
                },
            },
            {
                "name": "Verify address exists",
                "type": "tool_call",
                "tool": "crud_operation",
                "params": {
                    "operation": "read",
                    "object_type": "address",
                    "name": "test-server",
                },
            },
        ],
    }


@pytest.fixture
def mock_api_responses():
    """Mock XML responses for common PAN-OS API operations.

    Returns:
        Dict of operation -> mock XML response
    """
    return {
        "success": b'<response status="success" code="20"><msg>command succeeded</msg></response>',
        "get_config": b"""<response status="success" code="19">
            <result>
                <entry name="test-address">
                    <ip-netmask>10.0.0.1</ip-netmask>
                    <description>Test address</description>
                </entry>
            </result>
        </response>""",
        "commit": b"""<response status="success" code="19">
            <result>
                <msg>
                    <line>Commit job enqueued with jobid 123</line>
                </msg>
                <job>123</job>
            </result>
        </response>""",
        "job_status": b"""<response status="success">
            <result>
                <job>
                    <id>123</id>
                    <status>FIN</status>
                    <result>OK</result>
                </job>
            </result>
        </response>""",
        "error": b'<response status="error" code="403"><msg>Not Authenticated</msg></response>',
    }
