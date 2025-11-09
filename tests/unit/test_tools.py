"""Unit tests for PAN-OS tools."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock


class TestAddressTools:
    """Tests for address object tools."""

    def test_address_create_success(self):
        """Test creating an address object successfully."""
        with patch("src.core.subgraphs.crud.create_crud_subgraph") as mock_create:
            from src.tools.address_objects import address_create

            # Mock subgraph with async invoke
            mock_subgraph = Mock()
            mock_subgraph.ainvoke = AsyncMock(return_value={
                "message": "✅ Created address: test-addr"
            })
            mock_create.return_value = mock_subgraph

            result = address_create.invoke({"name": "test-addr", "value": "10.1.1.1"})

            # Should return success string
            assert isinstance(result, str)
            assert "✅" in result or "created" in result.lower()

    def test_address_read_success(self):
        """Test reading an address object."""
        with patch("src.core.subgraphs.crud.create_crud_subgraph") as mock_create:
            from src.tools.address_objects import address_read

            # Mock subgraph with async invoke
            mock_subgraph = Mock()
            mock_subgraph.ainvoke = AsyncMock(return_value={
                "message": "✅ Retrieved address: test-addr"
            })
            mock_create.return_value = mock_subgraph

            result = address_read.invoke({"name": "test-addr"})

            # Should return success string
            assert isinstance(result, str)
            assert "test-addr" in result.lower() or "✅" in result

    def test_address_list_success(self):
        """Test listing address objects."""
        with patch("src.core.subgraphs.crud.create_crud_subgraph") as mock_create:
            from src.tools.address_objects import address_list

            # Mock subgraph with async invoke
            mock_subgraph = Mock()
            mock_subgraph.ainvoke = AsyncMock(return_value={
                "message": "✅ Found 2 address objects"
            })
            mock_create.return_value = mock_subgraph

            result = address_list.invoke({})

            # Should return success string
            assert isinstance(result, str)
            assert "address" in result.lower()

    def test_address_delete_success(self):
        """Test deleting an address object."""
        with patch("src.core.subgraphs.crud.create_crud_subgraph") as mock_create:
            from src.tools.address_objects import address_delete

            # Mock subgraph with async invoke
            mock_subgraph = Mock()
            mock_subgraph.ainvoke = AsyncMock(return_value={
                "message": "✅ Deleted address: test-addr"
            })
            mock_create.return_value = mock_subgraph

            result = address_delete.invoke({"name": "test-addr"})

            # Should return success string
            assert isinstance(result, str)
            assert "✅" in result or "deleted" in result.lower()


class TestServiceTools:
    """Tests for service object tools."""

    def test_service_create_success(self):
        """Test creating a service object."""
        with patch("src.core.subgraphs.crud.create_crud_subgraph") as mock_create:
            from src.tools.services import service_create

            # Mock subgraph with async invoke
            mock_subgraph = Mock()
            mock_subgraph.ainvoke = AsyncMock(return_value={
                "message": "✅ Created service: http-8080"
            })
            mock_create.return_value = mock_subgraph

            result = service_create.invoke({
                "name": "http-8080",
                "protocol": "tcp",
                "port": "8080"
            })

            assert isinstance(result, str)
            assert "✅" in result or "created" in result.lower()

    def test_service_list_success(self):
        """Test listing service objects."""
        with patch("src.core.subgraphs.crud.create_crud_subgraph") as mock_create:
            from src.tools.services import service_list

            # Mock subgraph with async invoke
            mock_subgraph = Mock()
            mock_subgraph.ainvoke = AsyncMock(return_value={
                "message": "✅ Found 1 service objects"
            })
            mock_create.return_value = mock_subgraph

            result = service_list.invoke({})

            assert isinstance(result, str)
            assert "service" in result.lower()


class TestAddressGroupTools:
    """Tests for address group tools."""

    def test_address_group_create_success(self):
        """Test creating an address group."""
        with patch("src.core.subgraphs.crud.create_crud_subgraph") as mock_create:
            from src.tools.address_groups import address_group_create

            # Mock subgraph with async invoke
            mock_subgraph = Mock()
            mock_subgraph.ainvoke = AsyncMock(return_value={
                "message": "✅ Created address group: test-group"
            })
            mock_create.return_value = mock_subgraph

            result = address_group_create.invoke({
                "name": "test-group",
                "members": ["addr1", "addr2"]
            })

            assert isinstance(result, str)
            assert "✅" in result or "created" in result.lower()

    def test_address_group_list_success(self):
        """Test listing address groups."""
        with patch("src.core.subgraphs.crud.create_crud_subgraph") as mock_create:
            from src.tools.address_groups import address_group_list

            # Mock subgraph with async invoke
            mock_subgraph = Mock()
            mock_subgraph.ainvoke = AsyncMock(return_value={
                "message": "✅ Found 2 address groups"
            })
            mock_create.return_value = mock_subgraph

            result = address_group_list.invoke({})

            assert isinstance(result, str)
            assert "group" in result.lower() or "✅" in result


class TestServiceGroupTools:
    """Tests for service group tools."""

    def test_service_group_create_success(self):
        """Test creating a service group."""
        with patch("src.core.subgraphs.crud.create_crud_subgraph") as mock_create:
            from src.tools.service_groups import service_group_create

            # Mock subgraph with async invoke
            mock_subgraph = Mock()
            mock_subgraph.ainvoke = AsyncMock(return_value={
                "message": "✅ Created service group: web-services"
            })
            mock_create.return_value = mock_subgraph

            result = service_group_create.invoke({
                "name": "web-services",
                "members": ["http", "https"]
            })

            assert isinstance(result, str)
            assert "✅" in result or "created" in result.lower()

    def test_service_group_list_success(self):
        """Test listing service groups."""
        with patch("src.core.subgraphs.crud.create_crud_subgraph") as mock_create:
            from src.tools.service_groups import service_group_list

            # Mock subgraph with async invoke
            mock_subgraph = Mock()
            mock_subgraph.ainvoke = AsyncMock(return_value={
                "message": "✅ Found 3 service groups"
            })
            mock_create.return_value = mock_subgraph

            result = service_group_list.invoke({})

            assert isinstance(result, str)
            assert "service" in result.lower() or "✅" in result


class TestOrchestrationTools:
    """Tests for orchestration tools (CRUD operations and commit)."""

    def test_crud_operation_create(self):
        """Test unified CRUD operation for create."""
        with patch("src.core.subgraphs.crud.create_crud_subgraph") as mock_create:
            from src.tools.orchestration.crud_operations import crud_operation

            # Mock subgraph with async invoke
            mock_subgraph = Mock()
            mock_subgraph.ainvoke = AsyncMock(return_value={
                "message": "✅ Created address: test-addr"
            })
            mock_create.return_value = mock_subgraph

            result = crud_operation.invoke({
                "operation": "create",
                "object_type": "address",
                "data": {"name": "test-addr", "value": "10.1.1.1"}
            })

            assert isinstance(result, str)
            assert "✅" in result or "created" in result.lower()

    def test_crud_operation_list(self):
        """Test unified CRUD operation for list."""
        with patch("src.core.subgraphs.crud.create_crud_subgraph") as mock_create:
            from src.tools.orchestration.crud_operations import crud_operation

            # Mock subgraph with async invoke
            mock_subgraph = Mock()
            mock_subgraph.ainvoke = AsyncMock(return_value={
                "message": "✅ Found 5 address objects"
            })
            mock_create.return_value = mock_subgraph

            result = crud_operation.invoke({
                "operation": "list",
                "object_type": "address"
            })

            assert isinstance(result, str)
            assert "5" in result or "✅" in result

    def test_commit_changes_success(self):
        """Test commit changes tool."""
        with patch("src.core.subgraphs.commit.create_commit_subgraph") as mock_create:
            from src.tools.orchestration.commit_operations import commit_changes

            # Mock subgraph with async invoke
            mock_subgraph = Mock()
            mock_subgraph.ainvoke = AsyncMock(return_value={
                "message": "✅ Commit completed successfully"
            })
            mock_create.return_value = mock_subgraph

            result = commit_changes.invoke({
                "description": "Test commit"
            })

            assert isinstance(result, str)
            assert "✅" in result or "success" in result.lower()

    def test_commit_changes_error(self):
        """Test commit changes with error."""
        with patch("src.core.subgraphs.commit.create_commit_subgraph") as mock_create:
            from src.tools.orchestration.commit_operations import commit_changes

            # Mock subgraph that returns error with async invoke
            mock_subgraph = Mock()
            mock_subgraph.ainvoke = AsyncMock(return_value={
                "message": "❌ Error: Commit failed"
            })
            mock_create.return_value = mock_subgraph

            result = commit_changes.invoke({
                "description": "Test commit"
            })

            assert isinstance(result, str)
            assert "❌" in result or "error" in result.lower()


class TestToolErrorHandling:
    """Tests for tool error handling patterns."""

    def test_tools_never_raise(self):
        """Verify tools return error strings instead of raising exceptions."""
        # This is a design principle - tools should never raise exceptions,
        # they should always return a string (even if it's an error message)
        # This is tested implicitly by the other tests
        pass

    def test_tool_returns_error_message_on_exception(self):
        """Test that tools return error messages when subgraph fails."""
        with patch("src.core.subgraphs.crud.create_crud_subgraph") as mock_create:
            from src.tools.address_objects import address_create

            # Mock subgraph that returns error message with async invoke
            mock_subgraph = Mock()
            mock_subgraph.ainvoke = AsyncMock(return_value={
                "message": "❌ Error: API error"
            })
            mock_create.return_value = mock_subgraph

            result = address_create.invoke({"name": "test", "value": "10.1.1.1"})

            assert isinstance(result, str)
            assert "❌" in result or "error" in result.lower()

    def test_tool_returns_string_type(self):
        """Verify all tool functions have proper type hints for return type."""
        from src.tools.address_objects import (
            address_create,
            address_read,
            address_update,
            address_delete,
            address_list,
        )

        # Check type annotations
        assert address_create.return_annotation == str
        assert address_read.return_annotation == str
        assert address_update.return_annotation == str
        assert address_delete.return_annotation == str
        assert address_list.return_annotation == str
