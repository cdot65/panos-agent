"""Integration tests for CRUD operations with caching (Phase 3.1.3).

Tests verify that:
- check_existence() uses cache
- read_object() uses cache
- create_object() invalidates cache
- update_object() invalidates cache
- delete_object() invalidates cache
"""

import pytest
from langgraph.store.memory import InMemoryStore
from lxml import etree
from unittest.mock import AsyncMock, patch

from src.core.subgraphs.crud import (
    check_existence,
    read_object,
    create_object,
    update_object,
    delete_object,
)
from src.core.state_schemas import CRUDState


@pytest.fixture
def mock_store():
    """Create InMemoryStore for testing."""
    return InMemoryStore()


@pytest.fixture
def base_state(mock_store):
    """Create base CRUD state with store."""
    return {
        "operation_type": "read",
        "object_type": "address",
        "object_name": "test-obj-1",
        "data": {},
        "store": mock_store,
        "device_context": {
            "device_name": "localhost.localdomain",
            "vsys": "vsys1",
        },
    }


@pytest.fixture
def mock_xml_response():
    """Create mock XML response."""
    xml = "<entry name='test-obj-1'><ip-netmask>10.0.0.1/32</ip-netmask></entry>"
    return etree.fromstring(xml)


class TestCheckExistenceWithCache:
    """Tests for check_existence() using cache."""

    @pytest.mark.asyncio
    async def test_check_existence_caches_result(self, base_state, mock_xml_response):
        """Test that check_existence() caches the API response."""
        from src.core.memory_store import get_cached_config

        with patch("src.core.subgraphs.crud.get_panos_client") as mock_client:
            with patch("src.core.subgraphs.crud.get_config") as mock_get_config:
                mock_get_config.return_value = mock_xml_response

                # First call - should hit API
                state = base_state.copy()
                result = await check_existence(state)

                assert result["exists"] is True
                assert mock_get_config.call_count == 1

                # Verify cache entry exists
                from src.core.config import get_settings
                from src.core.panos_api import build_xpath

                settings = get_settings()
                xpath = build_xpath("address", name="test-obj-1", device_context=base_state["device_context"])
                cached = get_cached_config(settings.panos_hostname, xpath, base_state["store"])
                assert cached is not None

    @pytest.mark.asyncio
    async def test_check_existence_uses_cache_on_second_call(self, base_state, mock_xml_response):
        """Test that second check_existence() call uses cache."""
        with patch("src.core.subgraphs.crud.get_panos_client") as mock_client:
            with patch("src.core.subgraphs.crud.get_config") as mock_get_config:
                mock_get_config.return_value = mock_xml_response

                # First call - should hit API
                state1 = base_state.copy()
                result1 = await check_existence(state1)
                assert result1["exists"] is True
                assert mock_get_config.call_count == 1

                # Second call - should use cache (no additional API call)
                state2 = base_state.copy()
                state2["store"] = state1["store"]  # Use same store
                result2 = await check_existence(state2)
                assert result2["exists"] is True
                assert mock_get_config.call_count == 1  # Still 1 (cache hit)

    @pytest.mark.asyncio
    async def test_check_existence_cache_disabled(self, base_state, mock_xml_response):
        """Test that check_existence() bypasses cache when disabled."""
        with patch("src.core.subgraphs.crud.get_panos_client") as mock_client:
            with patch("src.core.subgraphs.crud.get_config") as mock_get_config:
                with patch("src.core.config.get_settings") as mock_settings:
                    # Disable cache
                    mock_settings.return_value.cache_enabled = False
                    mock_settings.return_value.panos_hostname = "192.168.1.1"
                    mock_get_config.return_value = mock_xml_response

                    # First call
                    state1 = base_state.copy()
                    result1 = await check_existence(state1)
                    assert result1["exists"] is True
                    assert mock_get_config.call_count == 1

                    # Second call - should still hit API (cache disabled)
                    state2 = base_state.copy()
                    state2["store"] = state1["store"]
                    result2 = await check_existence(state2)
                    assert result2["exists"] is True
                    assert mock_get_config.call_count == 2  # Hit API again


class TestReadObjectWithCache:
    """Tests for read_object() using cache."""

    @pytest.mark.asyncio
    async def test_read_object_caches_result(self, base_state, mock_xml_response):
        """Test that read_object() caches the API response."""
        from src.core.memory_store import get_cached_config

        with patch("src.core.subgraphs.crud.get_panos_client") as mock_client:
            with patch("src.core.subgraphs.crud.get_config") as mock_get_config:
                mock_get_config.return_value = mock_xml_response

                # Set exists flag
                state = base_state.copy()
                state["exists"] = True
                result = await read_object(state)

                assert result["operation_result"]["status"] == "success"
                assert mock_get_config.call_count == 1

                # Verify cache entry exists
                from src.core.config import get_settings
                from src.core.panos_api import build_xpath

                settings = get_settings()
                xpath = build_xpath("address", name="test-obj-1", device_context=base_state["device_context"])
                cached = get_cached_config(settings.panos_hostname, xpath, base_state["store"])
                assert cached is not None

    @pytest.mark.asyncio
    async def test_read_object_uses_cache_on_second_call(self, base_state, mock_xml_response):
        """Test that second read_object() call uses cache."""
        with patch("src.core.subgraphs.crud.get_panos_client") as mock_client:
            with patch("src.core.subgraphs.crud.get_config") as mock_get_config:
                mock_get_config.return_value = mock_xml_response

                # First call - should hit API
                state1 = base_state.copy()
                state1["exists"] = True
                result1 = await read_object(state1)
                assert result1["operation_result"]["status"] == "success"
                assert mock_get_config.call_count == 1

                # Second call - should use cache
                state2 = base_state.copy()
                state2["exists"] = True
                state2["store"] = state1["store"]  # Use same store
                result2 = await read_object(state2)
                assert result2["operation_result"]["status"] == "success"
                assert mock_get_config.call_count == 1  # Still 1 (cache hit)


class TestMutationsInvalidateCache:
    """Tests that mutations (create/update/delete) invalidate cache."""

    @pytest.mark.asyncio
    async def test_create_invalidates_cache(self, base_state, mock_xml_response):
        """Test that create_object() invalidates cache."""
        from src.core.memory_store import cache_config, get_cached_config
        from src.core.config import get_settings
        from src.core.panos_api import build_xpath

        settings = get_settings()
        xpath = build_xpath("address", name="test-obj-1", device_context=base_state["device_context"])

        # Pre-populate cache
        cache_config(
            settings.panos_hostname,
            xpath,
            etree.tostring(mock_xml_response, encoding="unicode"),
            base_state["store"],
            ttl=60,
        )

        # Verify cache exists
        assert get_cached_config(settings.panos_hostname, xpath, base_state["store"]) is not None

        with patch("src.core.subgraphs.crud.get_panos_client") as mock_client:
            with patch("src.core.subgraphs.crud.set_config") as mock_set_config:
                mock_set_config.return_value = None

                # Create object
                state = base_state.copy()
                state["operation_type"] = "create"
                state["exists"] = False
                state["data"] = {
                    "name": "test-obj-1",
                    "type": "ip-netmask",
                    "value": "10.0.0.1/32",
                }
                result = await create_object(state)

                assert result["operation_result"]["status"] == "success"

                # Verify cache invalidated
                assert get_cached_config(settings.panos_hostname, xpath, base_state["store"]) is None

    @pytest.mark.asyncio
    async def test_update_invalidates_cache(self, base_state, mock_xml_response):
        """Test that update_object() invalidates cache."""
        from src.core.memory_store import cache_config, get_cached_config
        from src.core.config import get_settings
        from src.core.panos_api import build_xpath

        settings = get_settings()
        xpath = build_xpath("address", name="test-obj-1", device_context=base_state["device_context"])

        # Pre-populate cache
        cache_config(
            settings.panos_hostname,
            xpath,
            etree.tostring(mock_xml_response, encoding="unicode"),
            base_state["store"],
            ttl=60,
        )

        # Verify cache exists
        assert get_cached_config(settings.panos_hostname, xpath, base_state["store"]) is not None

        with patch("src.core.subgraphs.crud.get_panos_client") as mock_client:
            with patch("src.core.subgraphs.crud.edit_config") as mock_edit_config:
                mock_edit_config.return_value = None

                # Update object
                state = base_state.copy()
                state["operation_type"] = "update"
                state["exists"] = True
                state["data"] = {
                    "value": "10.0.0.2/32",
                }
                result = await update_object(state)

                assert result["operation_result"]["status"] == "success"

                # Verify cache invalidated
                assert get_cached_config(settings.panos_hostname, xpath, base_state["store"]) is None

    @pytest.mark.asyncio
    async def test_delete_invalidates_cache(self, base_state, mock_xml_response):
        """Test that delete_object() invalidates cache."""
        from src.core.memory_store import cache_config, get_cached_config
        from src.core.config import get_settings
        from src.core.panos_api import build_xpath

        settings = get_settings()
        xpath = build_xpath("address", name="test-obj-1", device_context=base_state["device_context"])

        # Pre-populate cache
        cache_config(
            settings.panos_hostname,
            xpath,
            etree.tostring(mock_xml_response, encoding="unicode"),
            base_state["store"],
            ttl=60,
        )

        # Verify cache exists
        assert get_cached_config(settings.panos_hostname, xpath, base_state["store"]) is not None

        with patch("src.core.subgraphs.crud.get_panos_client") as mock_client:
            with patch("src.core.subgraphs.crud.delete_config") as mock_delete_config:
                mock_delete_config.return_value = None

                # Delete object
                state = base_state.copy()
                state["operation_type"] = "delete"
                state["exists"] = True
                result = await delete_object(state)

                assert result["operation_result"]["status"] == "success"

                # Verify cache invalidated
                assert get_cached_config(settings.panos_hostname, xpath, base_state["store"]) is None


class TestCachePerformance:
    """Tests to verify cache improves performance."""

    @pytest.mark.asyncio
    async def test_multiple_reads_use_cache(self, base_state, mock_xml_response):
        """Test that multiple reads of same object use cache (reducing API calls)."""
        with patch("src.core.subgraphs.crud.get_panos_client") as mock_client:
            with patch("src.core.subgraphs.crud.get_config") as mock_get_config:
                mock_get_config.return_value = mock_xml_response

                # Read same object 5 times
                for i in range(5):
                    state = base_state.copy()
                    state["exists"] = True
                    if i > 0:
                        state["store"] = base_state["store"]  # Reuse store
                    result = await read_object(state)
                    assert result["operation_result"]["status"] == "success"

                # Should only call API once (first time)
                assert mock_get_config.call_count == 1

    @pytest.mark.asyncio
    async def test_read_after_update_fetches_fresh(self, base_state, mock_xml_response):
        """Test that read after update fetches fresh data (cache invalidated)."""
        with patch("src.core.subgraphs.crud.get_panos_client") as mock_client:
            with patch("src.core.subgraphs.crud.get_config") as mock_get_config:
                with patch("src.core.subgraphs.crud.edit_config") as mock_edit_config:
                    mock_get_config.return_value = mock_xml_response
                    mock_edit_config.return_value = None

                    # Read object (caches it)
                    state1 = base_state.copy()
                    state1["exists"] = True
                    result1 = await read_object(state1)
                    assert result1["operation_result"]["status"] == "success"
                    assert mock_get_config.call_count == 1

                    # Update object (invalidates cache)
                    state2 = base_state.copy()
                    state2["operation_type"] = "update"
                    state2["exists"] = True
                    state2["data"] = {"value": "10.0.0.2/32"}
                    state2["store"] = state1["store"]
                    result2 = await update_object(state2)
                    assert result2["operation_result"]["status"] == "success"

                    # Read again (should fetch fresh from API)
                    state3 = base_state.copy()
                    state3["exists"] = True
                    state3["store"] = state1["store"]
                    result3 = await read_object(state3)
                    assert result3["operation_result"]["status"] == "success"
                    assert mock_get_config.call_count == 2  # Called again after update

