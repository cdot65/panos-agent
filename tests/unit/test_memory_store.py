"""Unit tests for memory store module.

Tests Store API helper functions for firewall config and workflow history.
"""

from datetime import datetime

import pytest
from langgraph.store.memory import InMemoryStore

from src.core.memory_store import (
    get_firewall_operation_summary,
    retrieve_firewall_config,
    search_workflow_history,
    store_firewall_config,
    store_workflow_execution,
)


class TestStoreFirewallConfig:
    """Tests for store_firewall_config function."""

    def test_store_firewall_config_success(self):
        """Test storing firewall config successfully."""
        store = InMemoryStore()
        hostname = "192.168.1.1"
        config_type = "address_objects"
        data = {
            "last_updated": "2025-01-09T10:30:00Z",
            "count": 15,
            "recent_operations": [
                {
                    "operation": "create",
                    "object_name": "web-1",
                    "timestamp": "2025-01-09T10:25:00Z",
                }
            ],
        }

        store_firewall_config(hostname, config_type, data, store)

        # Verify stored (hostname is sanitized: dots -> underscores)
        result = store.get(
            namespace=("firewall_configs", "192_168_1_1"),
            key=config_type,
        )
        assert result is not None
        assert result.value["count"] == 15
        assert len(result.value["recent_operations"]) == 1
        assert result.value["recent_operations"][0]["object_name"] == "web-1"

    def test_store_firewall_config_overwrite(self):
        """Test overwriting existing firewall config."""
        store = InMemoryStore()
        hostname = "192.168.1.1"
        config_type = "address_objects"

        # Store initial config
        initial_data = {
            "last_updated": "2025-01-09T10:00:00Z",
            "count": 10,
            "recent_operations": [],
        }
        store_firewall_config(hostname, config_type, initial_data, store)

        # Overwrite with new data
        new_data = {
            "last_updated": "2025-01-09T11:00:00Z",
            "count": 20,
            "recent_operations": [
                {
                    "operation": "create",
                    "object_name": "new-obj",
                    "timestamp": "2025-01-09T11:00:00Z",
                }
            ],
        }
        store_firewall_config(hostname, config_type, new_data, store)

        # Verify overwritten
        result = store.get(
            namespace=("firewall_configs", "192_168_1_1"),
            key=config_type,
        )
        assert result.value["count"] == 20
        assert result.value["last_updated"] == "2025-01-09T11:00:00Z"
        assert len(result.value["recent_operations"]) == 1

    def test_store_firewall_config_different_hostnames(self):
        """Test namespace isolation for different hostnames."""
        store = InMemoryStore()
        hostname1 = "192.168.1.1"
        hostname2 = "192.168.1.2"
        config_type = "address_objects"

        data1 = {"last_updated": "2025-01-09T10:00:00Z", "count": 10, "recent_operations": []}
        data2 = {"last_updated": "2025-01-09T10:00:00Z", "count": 20, "recent_operations": []}

        store_firewall_config(hostname1, config_type, data1, store)
        store_firewall_config(hostname2, config_type, data2, store)

        # Verify isolation
        result1 = store.get(
            namespace=("firewall_configs", "192_168_1_1"),
            key=config_type,
        )
        result2 = store.get(
            namespace=("firewall_configs", "192_168_1_2"),
            key=config_type,
        )

        assert result1.value["count"] == 10
        assert result2.value["count"] == 20


class TestRetrieveFirewallConfig:
    """Tests for retrieve_firewall_config function."""

    def test_retrieve_firewall_config_exists(self):
        """Test retrieving existing firewall config."""
        store = InMemoryStore()
        hostname = "192.168.1.1"
        config_type = "address_objects"
        data = {
            "last_updated": "2025-01-09T10:30:00Z",
            "count": 15,
            "recent_operations": [],
        }

        # Store first
        store_firewall_config(hostname, config_type, data, store)

        # Retrieve
        result = retrieve_firewall_config(hostname, config_type, store)

        assert result is not None
        assert result["count"] == 15
        assert result["last_updated"] == "2025-01-09T10:30:00Z"

    def test_retrieve_firewall_config_not_found(self):
        """Test retrieving non-existent firewall config."""
        store = InMemoryStore()
        hostname = "192.168.1.1"
        config_type = "address_objects"

        result = retrieve_firewall_config(hostname, config_type, store)

        assert result is None

    def test_retrieve_firewall_config_different_config_type(self):
        """Test retrieving different config type returns None."""
        store = InMemoryStore()
        hostname = "192.168.1.1"

        # Store address_objects
        store_firewall_config(
            hostname,
            "address_objects",
            {"last_updated": "2025-01-09T10:00:00Z", "count": 10, "recent_operations": []},
            store,
        )

        # Try to retrieve services (doesn't exist)
        result = retrieve_firewall_config(hostname, "services", store)

        assert result is None


class TestStoreWorkflowExecution:
    """Tests for store_workflow_execution function."""

    def test_store_workflow_execution_success(self):
        """Test storing workflow execution successfully."""
        store = InMemoryStore()
        workflow_name = "web_server_setup"
        execution_data = {
            "workflow_name": workflow_name,
            "execution_id": "550e8400-e29b-41d4-a716-446655440000",
            "started_at": "2025-01-09T10:00:00Z",
            "completed_at": "2025-01-09T10:05:00Z",
            "status": "success",
            "steps_executed": 4,
            "steps_total": 4,
            "results": [
                {"step": 1, "name": "Create address", "status": "success"},
            ],
            "metadata": {"thread_id": "test-123"},
        }

        store_workflow_execution(workflow_name, execution_data, store)

        # Verify stored
        result = store.get(
            namespace=("workflow_history", workflow_name),
            key=execution_data["execution_id"],
        )
        assert result is not None
        assert result.value["status"] == "success"
        assert result.value["steps_executed"] == 4
        assert result.value["workflow_name"] == workflow_name

    def test_store_workflow_execution_no_execution_id(self):
        """Test storing workflow execution without execution_id (should skip)."""
        store = InMemoryStore()
        workflow_name = "test_workflow"
        execution_data = {
            "workflow_name": workflow_name,
            "status": "success",
            # Missing execution_id
        }

        # Should not raise, but also not store
        store_workflow_execution(workflow_name, execution_data, store)

        # Verify nothing stored (can't search without execution_id)
        results = store.search(("workflow_history", workflow_name))
        assert len(results) == 0

    def test_store_workflow_execution_multiple_workflows(self):
        """Test storing multiple workflow executions for different workflows."""
        store = InMemoryStore()
        workflow1 = "web_server_setup"
        workflow2 = "database_setup"

        exec1 = {
            "workflow_name": workflow1,
            "execution_id": "exec-1",
            "started_at": "2025-01-09T10:00:00Z",
            "status": "success",
            "steps_executed": 2,
            "steps_total": 2,
            "results": [],
            "metadata": {},
        }
        exec2 = {
            "workflow_name": workflow2,
            "execution_id": "exec-2",
            "started_at": "2025-01-09T11:00:00Z",
            "status": "success",
            "steps_executed": 3,
            "steps_total": 3,
            "results": [],
            "metadata": {},
        }

        store_workflow_execution(workflow1, exec1, store)
        store_workflow_execution(workflow2, exec2, store)

        # Verify both stored
        result1 = store.get(
            ("workflow_history", workflow1),
            "exec-1",
        )
        result2 = store.get(
            ("workflow_history", workflow2),
            "exec-2",
        )

        assert result1.value["workflow_name"] == workflow1
        assert result2.value["workflow_name"] == workflow2


class TestSearchWorkflowHistory:
    """Tests for search_workflow_history function."""

    def test_search_workflow_history_empty(self):
        """Test searching workflow history when empty."""
        store = InMemoryStore()
        workflow_name = "test_workflow"

        results = search_workflow_history(workflow_name, store)

        assert results == []

    def test_search_workflow_history_single_execution(self):
        """Test searching workflow history with single execution."""
        store = InMemoryStore()
        workflow_name = "test_workflow"
        execution_data = {
            "workflow_name": workflow_name,
            "execution_id": "exec-1",
            "started_at": "2025-01-09T10:00:00Z",
            "status": "success",
            "steps_executed": 2,
            "steps_total": 2,
            "results": [],
            "metadata": {},
        }

        store_workflow_execution(workflow_name, execution_data, store)

        results = search_workflow_history(workflow_name, store)

        assert len(results) == 1
        assert results[0]["execution_id"] == "exec-1"
        assert results[0]["status"] == "success"

    def test_search_workflow_history_multiple_executions_sorted(self):
        """Test searching workflow history with multiple executions (sorted by started_at)."""
        store = InMemoryStore()
        workflow_name = "test_workflow"

        # Store executions in reverse chronological order
        exec1 = {
            "workflow_name": workflow_name,
            "execution_id": "exec-1",
            "started_at": "2025-01-09T10:00:00Z",  # Oldest
            "status": "success",
            "steps_executed": 1,
            "steps_total": 1,
            "results": [],
            "metadata": {},
        }
        exec2 = {
            "workflow_name": workflow_name,
            "execution_id": "exec-2",
            "started_at": "2025-01-09T11:00:00Z",  # Middle
            "status": "success",
            "steps_executed": 2,
            "steps_total": 2,
            "results": [],
            "metadata": {},
        }
        exec3 = {
            "workflow_name": workflow_name,
            "execution_id": "exec-3",
            "started_at": "2025-01-09T12:00:00Z",  # Newest
            "status": "failed",
            "steps_executed": 1,
            "steps_total": 2,
            "results": [],
            "metadata": {},
        }

        store_workflow_execution(workflow_name, exec1, store)
        store_workflow_execution(workflow_name, exec2, store)
        store_workflow_execution(workflow_name, exec3, store)

        results = search_workflow_history(workflow_name, store)

        assert len(results) == 3
        # Should be sorted descending (newest first)
        assert results[0]["execution_id"] == "exec-3"
        assert results[1]["execution_id"] == "exec-2"
        assert results[2]["execution_id"] == "exec-1"

    def test_search_workflow_history_limit(self):
        """Test searching workflow history with limit."""
        store = InMemoryStore()
        workflow_name = "test_workflow"

        # Store 5 executions
        for i in range(5):
            exec_data = {
                "workflow_name": workflow_name,
                "execution_id": f"exec-{i}",
                "started_at": f"2025-01-09T{10+i:02d}:00:00Z",
                "status": "success",
                "steps_executed": 1,
                "steps_total": 1,
                "results": [],
                "metadata": {},
            }
            store_workflow_execution(workflow_name, exec_data, store)

        # Search with limit=3
        results = search_workflow_history(workflow_name, store, limit=3)

        assert len(results) == 3
        # Should return newest 3
        assert results[0]["execution_id"] == "exec-4"
        assert results[1]["execution_id"] == "exec-3"
        assert results[2]["execution_id"] == "exec-2"

    def test_search_workflow_history_namespace_isolation(self):
        """Test that workflow history is isolated by workflow name."""
        store = InMemoryStore()
        workflow1 = "workflow_1"
        workflow2 = "workflow_2"

        exec1 = {
            "workflow_name": workflow1,
            "execution_id": "exec-1",
            "started_at": "2025-01-09T10:00:00Z",
            "status": "success",
            "steps_executed": 1,
            "steps_total": 1,
            "results": [],
            "metadata": {},
        }
        exec2 = {
            "workflow_name": workflow2,
            "execution_id": "exec-2",
            "started_at": "2025-01-09T10:00:00Z",
            "status": "success",
            "steps_executed": 1,
            "steps_total": 1,
            "results": [],
            "metadata": {},
        }

        store_workflow_execution(workflow1, exec1, store)
        store_workflow_execution(workflow2, exec2, store)

        # Search workflow1 should only return exec1
        results1 = search_workflow_history(workflow1, store)
        results2 = search_workflow_history(workflow2, store)

        assert len(results1) == 1
        assert results1[0]["execution_id"] == "exec-1"
        assert len(results2) == 1
        assert results2[0]["execution_id"] == "exec-2"


class TestGetFirewallOperationSummary:
    """Tests for get_firewall_operation_summary function."""

    def test_get_firewall_operation_summary_empty(self):
        """Test getting summary when no configs stored."""
        store = InMemoryStore()
        hostname = "192.168.1.1"

        summary = get_firewall_operation_summary(hostname, store)

        assert summary["total_objects"] == 0
        assert summary["recent_operations"] == []
        assert summary["config_types"] == {}

    def test_get_firewall_operation_summary_single_config_type(self):
        """Test getting summary with single config type."""
        store = InMemoryStore()
        hostname = "192.168.1.1"
        config_type = "address_objects"
        data = {
            "last_updated": "2025-01-09T10:00:00Z",
            "count": 15,
            "recent_operations": [
                {
                    "operation": "create",
                    "object_name": "web-1",
                    "timestamp": "2025-01-09T10:00:00Z",
                }
            ],
        }

        store_firewall_config(hostname, config_type, data, store)

        summary = get_firewall_operation_summary(hostname, store)

        assert summary["total_objects"] == 15
        assert summary["config_types"][config_type] == 15
        assert len(summary["recent_operations"]) == 1
        assert summary["recent_operations"][0]["object_name"] == "web-1"

    def test_get_firewall_operation_summary_multiple_config_types(self):
        """Test getting summary with multiple config types."""
        store = InMemoryStore()
        hostname = "192.168.1.1"

        # Store multiple config types
        store_firewall_config(
            hostname,
            "address_objects",
            {
                "last_updated": "2025-01-09T10:00:00Z",
                "count": 10,
                "recent_operations": [
                    {
                        "operation": "create",
                        "object_name": "addr-1",
                        "timestamp": "2025-01-09T10:00:00Z",
                    }
                ],
            },
            store,
        )
        store_firewall_config(
            hostname,
            "services",
            {
                "last_updated": "2025-01-09T10:00:00Z",
                "count": 5,
                "recent_operations": [
                    {
                        "operation": "create",
                        "object_name": "svc-1",
                        "timestamp": "2025-01-09T11:00:00Z",
                    }
                ],
            },
            store,
        )

        summary = get_firewall_operation_summary(hostname, store)

        assert summary["total_objects"] == 15  # 10 + 5
        assert summary["config_types"]["address_objects"] == 10
        assert summary["config_types"]["services"] == 5
        assert len(summary["recent_operations"]) == 2

    def test_get_firewall_operation_summary_sorted_operations(self):
        """Test that recent operations are sorted by timestamp descending."""
        store = InMemoryStore()
        hostname = "192.168.1.1"

        # Store operations with different timestamps
        store_firewall_config(
            hostname,
            "address_objects",
            {
                "last_updated": "2025-01-09T10:00:00Z",
                "count": 2,
                "recent_operations": [
                    {
                        "operation": "create",
                        "object_name": "old",
                        "timestamp": "2025-01-09T09:00:00Z",
                    },
                    {
                        "operation": "create",
                        "object_name": "new",
                        "timestamp": "2025-01-09T10:00:00Z",
                    },
                ],
            },
            store,
        )

        summary = get_firewall_operation_summary(hostname, store)

        # Should be sorted newest first
        assert summary["recent_operations"][0]["object_name"] == "new"
        assert summary["recent_operations"][1]["object_name"] == "old"

    def test_get_firewall_operation_summary_limit_operations(self):
        """Test that summary limits to last 20 operations."""
        store = InMemoryStore()
        hostname = "192.168.1.1"

        # Create 25 operations
        operations = []
        for i in range(25):
            operations.append(
                {
                    "operation": "create",
                    "object_name": f"obj-{i}",
                    "timestamp": f"2025-01-09T{10+i//60:02d}:{i%60:02d}:00Z",
                }
            )

        store_firewall_config(
            hostname,
            "address_objects",
            {
                "last_updated": "2025-01-09T10:00:00Z",
                "count": 25,
                "recent_operations": operations,
            },
            store,
        )

        summary = get_firewall_operation_summary(hostname, store)

        # Should limit to 20
        assert len(summary["recent_operations"]) == 20
        # Should be newest 20
        assert summary["recent_operations"][0]["object_name"] == "obj-24"

    def test_get_firewall_operation_summary_hostname_isolation(self):
        """Test that summaries are isolated by hostname."""
        store = InMemoryStore()
        hostname1 = "192.168.1.1"
        hostname2 = "192.168.1.2"

        store_firewall_config(
            hostname1,
            "address_objects",
            {"last_updated": "2025-01-09T10:00:00Z", "count": 10, "recent_operations": []},
            store,
        )
        store_firewall_config(
            hostname2,
            "address_objects",
            {"last_updated": "2025-01-09T10:00:00Z", "count": 20, "recent_operations": []},
            store,
        )

        summary1 = get_firewall_operation_summary(hostname1, store)
        summary2 = get_firewall_operation_summary(hostname2, store)

        assert summary1["total_objects"] == 10
        assert summary2["total_objects"] == 20


# =============================================================================
# Phase 3.1.3: Configuration Caching Tests
# =============================================================================


class TestCacheConfig:
    """Tests for cache_config function (basic operations)."""

    def test_cache_config_stores_entry(self):
        """Test that cache_config stores entry in cache."""
        from src.core.memory_store import cache_config, get_cached_config

        store = InMemoryStore()
        hostname = "192.168.1.1"
        xpath = "/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address/entry[@name='web-1']"
        xml_data = "<entry name='web-1'><ip-netmask>10.0.0.1</ip-netmask></entry>"

        cache_config(hostname, xpath, xml_data, store, ttl=60)

        # Retrieve from cache
        cached = get_cached_config(hostname, xpath, store)
        assert cached == xml_data

    def test_cache_config_with_custom_ttl(self):
        """Test caching with custom TTL value."""
        from src.core.memory_store import cache_config, get_cached_config

        store = InMemoryStore()
        hostname = "192.168.1.1"
        xpath = "/config/test"
        xml_data = "<test>data</test>"

        cache_config(hostname, xpath, xml_data, store, ttl=120)

        # Verify stored
        cached = get_cached_config(hostname, xpath, store)
        assert cached == xml_data

    def test_cache_config_overwrite_existing(self):
        """Test that caching same xpath overwrites previous entry."""
        from src.core.memory_store import cache_config, get_cached_config

        store = InMemoryStore()
        hostname = "192.168.1.1"
        xpath = "/config/test"
        old_xml = "<test>old</test>"
        new_xml = "<test>new</test>"

        # Cache first time
        cache_config(hostname, xpath, old_xml, store, ttl=60)
        assert get_cached_config(hostname, xpath, store) == old_xml

        # Cache again with new data
        cache_config(hostname, xpath, new_xml, store, ttl=60)
        assert get_cached_config(hostname, xpath, store) == new_xml

    def test_cache_config_multiple_hosts(self):
        """Test cache isolation across different hostnames."""
        from src.core.memory_store import cache_config, get_cached_config

        store = InMemoryStore()
        hostname1 = "192.168.1.1"
        hostname2 = "192.168.1.2"
        xpath = "/config/test"
        xml1 = "<test>host1</test>"
        xml2 = "<test>host2</test>"

        cache_config(hostname1, xpath, xml1, store, ttl=60)
        cache_config(hostname2, xpath, xml2, store, ttl=60)

        # Each host should have its own cache
        assert get_cached_config(hostname1, xpath, store) == xml1
        assert get_cached_config(hostname2, xpath, store) == xml2

    def test_cache_config_multiple_xpaths(self):
        """Test caching multiple different xpaths for same host."""
        from src.core.memory_store import cache_config, get_cached_config

        store = InMemoryStore()
        hostname = "192.168.1.1"
        xpath1 = "/config/address/entry[@name='web-1']"
        xpath2 = "/config/address/entry[@name='web-2']"
        xml1 = "<entry name='web-1'>data1</entry>"
        xml2 = "<entry name='web-2'>data2</entry>"

        cache_config(hostname, xpath1, xml1, store, ttl=60)
        cache_config(hostname, xpath2, xml2, store, ttl=60)

        # Both should be cached independently
        assert get_cached_config(hostname, xpath1, store) == xml1
        assert get_cached_config(hostname, xpath2, store) == xml2


class TestGetCachedConfig:
    """Tests for get_cached_config function (cache retrieval)."""

    def test_get_cached_config_returns_data(self):
        """Test retrieving cached configuration data."""
        from src.core.memory_store import cache_config, get_cached_config

        store = InMemoryStore()
        hostname = "192.168.1.1"
        xpath = "/config/test"
        xml_data = "<test>data</test>"

        cache_config(hostname, xpath, xml_data, store, ttl=60)
        cached = get_cached_config(hostname, xpath, store)

        assert cached == xml_data

    def test_get_cached_config_miss_returns_none(self):
        """Test that cache miss returns None."""
        from src.core.memory_store import get_cached_config

        store = InMemoryStore()
        hostname = "192.168.1.1"
        xpath = "/config/nonexistent"

        cached = get_cached_config(hostname, xpath, store)
        assert cached is None

    def test_get_cached_config_different_xpath_returns_none(self):
        """Test that querying different xpath returns None."""
        from src.core.memory_store import cache_config, get_cached_config

        store = InMemoryStore()
        hostname = "192.168.1.1"
        xpath1 = "/config/test1"
        xpath2 = "/config/test2"
        xml_data = "<test>data</test>"

        cache_config(hostname, xpath1, xml_data, store, ttl=60)

        # Query different xpath
        cached = get_cached_config(hostname, xpath2, store)
        assert cached is None


class TestCacheTTLExpiration:
    """Tests for cache TTL expiration logic."""

    def test_cache_expires_after_ttl(self):
        """Test that cache entry expires after TTL."""
        import time

        from src.core.memory_store import cache_config, get_cached_config

        store = InMemoryStore()
        hostname = "192.168.1.1"
        xpath = "/config/test"
        xml_data = "<test>data</test>"

        # Cache with 1 second TTL
        cache_config(hostname, xpath, xml_data, store, ttl=1)

        # Should be available immediately
        assert get_cached_config(hostname, xpath, store) == xml_data

        # Wait for expiration
        time.sleep(1.1)

        # Should now be expired
        cached = get_cached_config(hostname, xpath, store)
        assert cached is None

    def test_cache_valid_before_ttl(self):
        """Test that cache entry is valid before TTL expires."""
        import time

        from src.core.memory_store import cache_config, get_cached_config

        store = InMemoryStore()
        hostname = "192.168.1.1"
        xpath = "/config/test"
        xml_data = "<test>data</test>"

        # Cache with 5 second TTL
        cache_config(hostname, xpath, xml_data, store, ttl=5)

        # Wait 2 seconds (within TTL)
        time.sleep(2)

        # Should still be cached
        cached = get_cached_config(hostname, xpath, store)
        assert cached == xml_data

    def test_cache_different_ttls_per_entry(self):
        """Test that different cache entries can have different TTLs."""
        import time

        from src.core.memory_store import cache_config, get_cached_config

        store = InMemoryStore()
        hostname = "192.168.1.1"
        xpath1 = "/config/test1"
        xpath2 = "/config/test2"
        xml1 = "<test>data1</test>"
        xml2 = "<test>data2</test>"

        # Cache with different TTLs
        cache_config(hostname, xpath1, xml1, store, ttl=1)  # 1 second
        cache_config(hostname, xpath2, xml2, store, ttl=10)  # 10 seconds

        # Wait for first to expire
        time.sleep(1.1)

        # First should be expired
        assert get_cached_config(hostname, xpath1, store) is None

        # Second should still be valid
        assert get_cached_config(hostname, xpath2, store) == xml2


class TestInvalidateCache:
    """Tests for invalidate_cache function."""

    def test_invalidate_specific_xpath(self):
        """Test invalidating specific xpath entry."""
        from src.core.memory_store import cache_config, get_cached_config, invalidate_cache

        store = InMemoryStore()
        hostname = "192.168.1.1"
        xpath = "/config/test"
        xml_data = "<test>data</test>"

        # Cache data
        cache_config(hostname, xpath, xml_data, store, ttl=60)
        assert get_cached_config(hostname, xpath, store) == xml_data

        # Invalidate
        count = invalidate_cache(hostname, xpath, store)
        assert count == 1

        # Should now be None
        assert get_cached_config(hostname, xpath, store) is None

    def test_invalidate_all_for_host(self):
        """Test invalidating all cache entries for a hostname."""
        from src.core.memory_store import cache_config, get_cached_config, invalidate_cache

        store = InMemoryStore()
        hostname = "192.168.1.1"
        xpath1 = "/config/test1"
        xpath2 = "/config/test2"
        xpath3 = "/config/test3"

        # Cache multiple entries
        cache_config(hostname, xpath1, "<test1/>", store, ttl=60)
        cache_config(hostname, xpath2, "<test2/>", store, ttl=60)
        cache_config(hostname, xpath3, "<test3/>", store, ttl=60)

        # Verify all cached
        assert get_cached_config(hostname, xpath1, store) is not None
        assert get_cached_config(hostname, xpath2, store) is not None
        assert get_cached_config(hostname, xpath3, store) is not None

        # Invalidate all
        count = invalidate_cache(hostname, None, store)
        assert count == 3

        # All should be None
        assert get_cached_config(hostname, xpath1, store) is None
        assert get_cached_config(hostname, xpath2, store) is None
        assert get_cached_config(hostname, xpath3, store) is None

    def test_invalidate_returns_count(self):
        """Test that invalidate_cache returns correct count."""
        from src.core.memory_store import cache_config, invalidate_cache

        store = InMemoryStore()
        hostname = "192.168.1.1"

        # Cache 5 entries
        for i in range(5):
            xpath = f"/config/test{i}"
            cache_config(hostname, xpath, f"<test{i}/>", store, ttl=60)

        # Invalidate all
        count = invalidate_cache(hostname, None, store)
        assert count == 5

    def test_invalidate_nonexistent_entry(self):
        """Test invalidating non-existent cache entry returns 0."""
        from src.core.memory_store import invalidate_cache

        store = InMemoryStore()
        hostname = "192.168.1.1"
        xpath = "/config/nonexistent"

        # Invalidate non-existent entry
        count = invalidate_cache(hostname, xpath, store)
        assert count == 0


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_cache_entry_is_expired(self):
        """Test CacheEntry.is_expired() method."""
        import time

        from src.core.memory_store import CacheEntry

        # Create entry with 1 second TTL
        entry = CacheEntry(
            xpath="/config/test",
            xml_data="<test/>",
            timestamp=time.time(),
            ttl=1,
        )

        # Should not be expired immediately
        assert not entry.is_expired()

        # Wait for expiration
        time.sleep(1.1)

        # Should now be expired
        assert entry.is_expired()

    def test_cache_entry_to_dict(self):
        """Test CacheEntry.to_dict() serialization."""
        import time

        from src.core.memory_store import CacheEntry

        timestamp = time.time()
        entry = CacheEntry(
            xpath="/config/test",
            xml_data="<test/>",
            timestamp=timestamp,
            ttl=60,
        )

        data = entry.to_dict()
        assert data["xpath"] == "/config/test"
        assert data["xml_data"] == "<test/>"
        assert data["timestamp"] == timestamp
        assert data["ttl"] == 60

    def test_cache_entry_from_dict(self):
        """Test CacheEntry.from_dict() deserialization."""
        import time

        from src.core.memory_store import CacheEntry

        timestamp = time.time()
        data = {
            "xpath": "/config/test",
            "xml_data": "<test/>",
            "timestamp": timestamp,
            "ttl": 60,
        }

        entry = CacheEntry.from_dict(data)
        assert entry.xpath == "/config/test"
        assert entry.xml_data == "<test/>"
        assert entry.timestamp == timestamp
        assert entry.ttl == 60
