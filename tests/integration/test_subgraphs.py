"""Integration tests for subgraphs (CRUD and Commit).

Tests subgraph invocation from parent graphs with async httpx/respx mocking.
"""

import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx
from httpx import Response

from src.core.subgraphs.crud import create_crud_subgraph
from src.core.subgraphs.commit import create_commit_subgraph


class TestCRUDSubgraphIntegration:
    """Test CRUD subgraph execution in graph context."""

    @pytest.mark.asyncio
    async def test_crud_create_operation(self):
        """Test CRUD subgraph create operation."""
        with respx.mock:
            # Mock connection test (system info)
            respx.get(url__regex=r".*type=op&cmd=.*show.*system.*info.*").mock(
                return_value=Response(
                    200,
                    content=b'<response status="success" code="19"><result><system><hostname>test-fw</hostname></system></result></response>',
                )
            )

            # Mock GET to check if object exists (should not exist)
            respx.get(url__regex=r".*type=config&action=get.*").mock(
                return_value=Response(
                    200,
                    content=b'<response status="success" code="19"><result/></response>',
                )
            )

            # Mock SET to create object (can be GET or POST)
            respx.get(url__regex=r".*type=config&action=set.*").mock(
                return_value=Response(
                    200,
                    content=b'<response status="success" code="20"><msg>command succeeded</msg></response>',
                )
            )
            respx.post(url__regex=r".*type=config&action=set.*").mock(
                return_value=Response(
                    200,
                    content=b'<response status="success" code="20"><msg>command succeeded</msg></response>',
                )
            )

            # Mock httpx client
            async def mock_get_client():
                return httpx.AsyncClient(base_url="https://192.168.1.1")

            with patch("src.core.client.get_panos_client", mock_get_client):
                # Create and invoke CRUD subgraph
                subgraph = create_crud_subgraph()

                result = await subgraph.ainvoke(
                    {
                        "operation_type": "create",
                        "object_type": "address",
                        "object_name": "test-server",
                        "data": {
                            "name": "test-server",
                            "value": "10.1.1.1",
                            "type": "ip-netmask",
                        },
                        "validation_result": None,
                        "exists": None,
                        "operation_result": None,
                        "message": "",
                        "error": None,
                    },
                    config={"configurable": {"thread_id": str(uuid.uuid4())}},
                )

                # Verify successful creation
                assert "message" in result
                assert "✅" in result["message"] or "success" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_crud_read_operation(self):
        """Test CRUD subgraph read operation."""
        with respx.mock:
            # Mock connection test (system info)
            respx.get(url__regex=r".*type=op&cmd=.*show.*system.*info.*").mock(
                return_value=Response(
                    200,
                    content=b'<response status="success" code="19"><result><system><hostname>test-fw</hostname></system></result></response>',
                )
            )

            # Mock GET to retrieve object (exists)
            respx.get(url__regex=r".*type=config&action=get.*").mock(
                return_value=Response(
                    200,
                    content=b'<response status="success" code="19">'
                    b'<result><address><entry name="test-server">'
                    b'<ip-netmask>10.1.1.1</ip-netmask>'
                    b'</entry></address></result>'
                    b"</response>",
                )
            )

            # Mock httpx client
            async def mock_get_client():
                return httpx.AsyncClient(base_url="https://192.168.1.1")

            with patch("src.core.client.get_panos_client", mock_get_client):
                # Create and invoke CRUD subgraph
                subgraph = create_crud_subgraph()

                result = await subgraph.ainvoke(
                    {
                        "operation_type": "read",
                        "object_type": "address",
                        "object_name": "test-server",
                        "data": None,
                        "validation_result": None,
                        "exists": None,
                        "operation_result": None,
                        "message": "",
                        "error": None,
                    },
                    config={"configurable": {"thread_id": str(uuid.uuid4())}},
                )

                # Verify successful read
                assert "message" in result
                assert "test-server" in result["message"]

    @pytest.mark.asyncio
    async def test_crud_list_operation(self):
        """Test CRUD subgraph list operation."""
        with respx.mock:
            # Mock GET to list objects
            respx.get(url__regex=r".*type=config&action=get.*").mock(
                return_value=Response(
                    200,
                    content=b'<response status="success" code="19">'
                    b"<result><address>"
                    b'<entry name="server-1"><ip-netmask>10.1.1.1</ip-netmask></entry>'
                    b'<entry name="server-2"><ip-netmask>10.1.1.2</ip-netmask></entry>'
                    b'<entry name="server-3"><ip-netmask>10.1.1.3</ip-netmask></entry>'
                    b"</address></result>"
                    b"</response>",
                )
            )

            # Mock httpx client
            async def mock_get_client():
                return httpx.AsyncClient(base_url="https://192.168.1.1")

            with patch("src.core.client.get_panos_client", mock_get_client):
                # Create and invoke CRUD subgraph
                subgraph = create_crud_subgraph()

                result = await subgraph.ainvoke(
                    {
                        "operation_type": "list",
                        "object_type": "address",
                        "object_name": None,
                        "data": None,
                        "validation_result": None,
                        "exists": None,
                        "operation_result": None,
                        "message": "",
                        "error": None,
                    },
                    config={"configurable": {"thread_id": str(uuid.uuid4())}},
                )

                # Verify successful list
                assert "message" in result
                assert "3" in result["message"] or "found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_crud_delete_operation(self):
        """Test CRUD subgraph delete operation."""
        with respx.mock:
            # Mock connection test (system info)
            respx.get(url__regex=r".*type=op&cmd=.*show.*system.*info.*").mock(
                return_value=Response(
                    200,
                    content=b'<response status="success" code="19"><result><system><hostname>test-fw</hostname></system></result></response>',
                )
            )

            # Mock GET to check if object exists
            respx.get(url__regex=r".*type=config&action=get.*").mock(
                return_value=Response(
                    200,
                    content=b'<response status="success" code="19">'
                    b'<result><address><entry name="test-server">'
                    b'<ip-netmask>10.1.1.1</ip-netmask>'
                    b"</entry></address></result>"
                    b"</response>",
                )
            )

            # Mock DELETE
            respx.get(url__regex=r".*type=config&action=delete.*").mock(
                return_value=Response(
                    200,
                    content=b'<response status="success" code="20"><msg>command succeeded</msg></response>',
                )
            )

            # Mock httpx client
            async def mock_get_client():
                return httpx.AsyncClient(base_url="https://192.168.1.1")

            with patch("src.core.client.get_panos_client", mock_get_client):
                # Create and invoke CRUD subgraph
                subgraph = create_crud_subgraph()

                result = await subgraph.ainvoke(
                    {
                        "operation_type": "delete",
                        "object_type": "address",
                        "object_name": "test-server",
                        "data": None,
                        "validation_result": None,
                        "exists": None,
                        "operation_result": None,
                        "message": "",
                        "error": None,
                    },
                    config={"configurable": {"thread_id": str(uuid.uuid4())}},
                )

                # Verify successful deletion
                assert "message" in result
                assert "✅" in result["message"] or "deleted" in result["message"].lower()


class TestCommitSubgraphIntegration:
    """Test commit subgraph execution."""

    @pytest.mark.asyncio
    async def test_commit_without_approval(self):
        """Test commit subgraph without approval gate."""
        with respx.mock:
            # Mock connection test (system info)
            respx.get(url__regex=r".*type=op&cmd=.*show.*system.*info.*").mock(
                return_value=Response(
                    200,
                    content=b'<response status="success" code="19"><result><system><hostname>test-fw</hostname></system></result></response>',
                )
            )

            # Mock commit API call - job ID should be in <job> text, not <job><id>
            respx.get(url__regex=r".*type=commit.*").mock(
                return_value=Response(
                    200,
                    content=b'<response status="success" code="19">'
                    b"<result><job>123</job></result>"
                    b"</response>",
                )
            )

            # Mock httpx client
            async def mock_get_client():
                return httpx.AsyncClient(base_url="https://192.168.1.1")

            with patch("src.core.client.get_panos_client", mock_get_client):
                # Create and invoke commit subgraph
                subgraph = create_commit_subgraph()

                result = await subgraph.ainvoke(
                    {
                        "description": "Test commit",
                        "sync": False,
                        "require_approval": False,
                        "approval_granted": None,
                        "commit_job_id": None,
                        "job_status": None,
                        "job_result": None,
                        "message": "",
                        "error": None,
                    },
                    config={"configurable": {"thread_id": str(uuid.uuid4())}},
                )

                # Verify commit executed
                assert "message" in result
                assert "commit" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_commit_sync_mode(self):
        """Test commit subgraph with job polling."""
        with respx.mock:
            # Mock connection test (system info)
            respx.get(url__regex=r".*type=op&cmd=.*show.*system.*info.*").mock(
                return_value=Response(
                    200,
                    content=b'<response status="success" code="19"><result><system><hostname>test-fw</hostname></system></result></response>',
                )
            )

            # Mock commit API call - job ID should be in <job> text, not <job><id>
            respx.get(url__regex=r".*type=commit.*").mock(
                return_value=Response(
                    200,
                    content=b'<response status="success" code="19">'
                    b"<result><job>123</job></result>"
                    b"</response>",
                )
            )

            # Mock job status polling - complete immediately
            respx.get(url__regex=r".*type=op&cmd=.*show.*jobs.*123.*").mock(
                return_value=Response(
                    200,
                    content=b'<response status="success" code="19">'
                    b"<result><job>"
                    b"<id>123</id>"
                    b"<status>FIN</status>"
                    b"<result>OK</result>"
                    b"</job></result>"
                    b"</response>",
                )
            )

            # Mock httpx client
            async def mock_get_client():
                return httpx.AsyncClient(base_url="https://192.168.1.1")

            with patch("src.core.client.get_panos_client", mock_get_client):
                with patch("src.core.subgraphs.commit.asyncio.sleep", return_value=None):
                    # Create and invoke commit subgraph
                    subgraph = create_commit_subgraph()

                    result = await subgraph.ainvoke(
                        {
                            "description": "Test commit with polling",
                            "sync": True,
                            "require_approval": False,
                            "approval_granted": None,
                            "commit_job_id": None,
                            "job_status": None,
                            "job_result": None,
                            "message": "",
                            "error": None,
                        },
                        config={"configurable": {"thread_id": str(uuid.uuid4())}},
                    )

                    # Verify commit completed
                    assert "message" in result
                    assert "success" in result["message"].lower() or "✅" in result["message"]


class TestSubgraphErrorHandling:
    """Test subgraph error handling and retry behavior."""

    @pytest.mark.asyncio
    async def test_crud_handles_connection_error(self):
        """Test CRUD subgraph handles connection errors with retry."""
        with respx.mock:
            # Mock connection timeout
            respx.get(url__regex=r".*type=config&action=get.*").mock(
                side_effect=httpx.TimeoutException("Connection timeout")
            )

            # Mock httpx client
            async def mock_get_client():
                return httpx.AsyncClient(base_url="https://192.168.1.1")

            with patch("src.core.client.get_panos_client", mock_get_client):
                # Create and invoke CRUD subgraph
                subgraph = create_crud_subgraph()

                result = await subgraph.ainvoke(
                    {
                        "operation_type": "list",
                        "object_type": "address",
                        "object_name": None,
                        "data": None,
                        "validation_result": None,
                        "exists": None,
                        "operation_result": None,
                        "message": "",
                        "error": None,
                    },
                    config={"configurable": {"thread_id": str(uuid.uuid4())}},
                )

                # Should handle error gracefully
                assert "message" in result
                # Error message should be present (retry policy will retry 3 times then fail)
                assert "❌" in result["message"] or "error" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_crud_handles_validation_error(self):
        """Test CRUD subgraph handles validation errors without retry."""
        with respx.mock:
            # Mock API error (non-retryable)
            respx.get(url__regex=r".*type=config&action=set.*").mock(
                return_value=Response(
                    400,
                    content=b'<response status="error" code="7">'
                    b"<msg><line>Invalid IP address</line></msg>"
                    b"</response>",
                )
            )

            # Mock GET for existence check
            respx.get(url__regex=r".*type=config&action=get.*").mock(
                return_value=Response(
                    200,
                    content=b'<response status="success" code="19"><result/></response>',
                )
            )

            # Mock httpx client
            async def mock_get_client():
                return httpx.AsyncClient(base_url="https://192.168.1.1")

            with patch("src.core.client.get_panos_client", mock_get_client):
                # Create and invoke CRUD subgraph
                subgraph = create_crud_subgraph()

                result = await subgraph.ainvoke(
                    {
                        "operation_type": "create",
                        "object_type": "address",
                        "object_name": "invalid-server",
                        "data": {
                            "name": "invalid-server",
                            "value": "256.1.1.1",  # Invalid IP
                            "type": "ip-netmask",
                        },
                        "validation_result": None,
                        "exists": None,
                        "operation_result": None,
                        "message": "",
                        "error": None,
                    },
                    config={"configurable": {"thread_id": str(uuid.uuid4())}},
                )

                # Should handle error without retry (validation errors are non-retryable)
                assert "message" in result
                assert "❌" in result["message"] or "error" in result["message"].lower()
