"""Memory store module for long-term memory across sessions.

Provides helper functions for storing and retrieving firewall configuration state
and workflow execution history using LangGraph Store API.

Also provides intelligent caching layer for PAN-OS API configuration retrieval
to reduce redundant API calls through TTL-based caching with automatic invalidation.
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

from langgraph.store.base import BaseStore

logger = logging.getLogger(__name__)

# Namespace constants
NAMESPACE_FIREWALL_CONFIGS = "firewall_configs"
NAMESPACE_WORKFLOW_HISTORY = "workflow_history"
NAMESPACE_USER_PREFERENCES = "user_preferences"  # Reserved for future
NAMESPACE_CONFIG_CACHE = "config_cache"  # For API response caching


@dataclass
class CacheEntry:
    """Cached configuration entry.

    Attributes:
        xpath: XPath that was queried
        xml_data: Raw XML string from firewall
        timestamp: Unix timestamp when cached
        ttl: Time-to-live in seconds (default 60)

    Example:
        ```python
        entry = CacheEntry(
            xpath="/config/.../address/entry[@name='web-1']",
            xml_data="<entry name='web-1'>...</entry>",
            timestamp=time.time(),
            ttl=60
        )
        if entry.is_expired():
            # Refetch from firewall
        ```
    """

    xpath: str
    xml_data: str
    timestamp: float
    ttl: int = 60

    def is_expired(self) -> bool:
        """Check if cache entry has expired.

        Returns:
            True if current time exceeds timestamp + ttl
        """
        return time.time() - self.timestamp > self.ttl

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage.

        Returns:
            Dictionary representation of cache entry
        """
        return {
            "xpath": self.xpath,
            "xml_data": self.xml_data,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheEntry":
        """Create CacheEntry from dictionary.

        Args:
            data: Dictionary with cache entry fields

        Returns:
            CacheEntry instance
        """
        return cls(
            xpath=data["xpath"],
            xml_data=data["xml_data"],
            timestamp=data["timestamp"],
            ttl=data.get("ttl", 60),
        )


def _sanitize_namespace_label(label: str) -> str:
    """Sanitize namespace label to remove invalid characters.

    LangGraph Store API doesn't allow periods in namespace labels.
    Replaces dots with underscores for IP addresses and hostnames.

    Args:
        label: Original label (e.g., "192.168.1.1")

    Returns:
        Sanitized label (e.g., "192_168_1_1")
    """
    return label.replace(".", "_")


def _hash_xpath(xpath: str) -> str:
    """Generate hash key for XPath.

    Uses MD5 hash for efficient key generation while avoiding namespace key length issues.

    Args:
        xpath: XPath string to hash

    Returns:
        Hexadecimal hash string (32 characters)
    """
    return hashlib.md5(xpath.encode()).hexdigest()


# =============================================================================
# Configuration Caching Functions (Phase 3.1.3)
# =============================================================================


def cache_config(
    hostname: str,
    xpath: str,
    xml_data: str,
    store: BaseStore,
    ttl: int = 60,
) -> None:
    """Cache firewall configuration data with TTL.

    Stores raw XML response from firewall with expiration timestamp to reduce
    redundant API calls for frequently accessed configurations.

    Args:
        hostname: Firewall hostname or IP address
        xpath: XPath that was queried
        xml_data: Raw XML string response from firewall
        store: BaseStore instance from graph runtime
        ttl: Time-to-live in seconds (default 60)

    Example:
        ```python
        cache_config(
            hostname="192.168.1.1",
            xpath="/config/devices/.../address/entry[@name='web-1']",
            xml_data="<entry name='web-1'><ip-netmask>10.0.0.1</ip-netmask></entry>",
            store=store,
            ttl=60
        )
        ```

    Note:
        - Uses MD5 hash of xpath as key for efficient storage
        - Namespace: ("config_cache", "192_168_1_1")
        - Automatically expires after TTL seconds
    """
    # Sanitize hostname for namespace
    sanitized_hostname = _sanitize_namespace_label(hostname)
    namespace = (NAMESPACE_CONFIG_CACHE, sanitized_hostname)

    # Generate cache key from xpath hash
    cache_key = _hash_xpath(xpath)

    # Create cache entry
    entry = CacheEntry(
        xpath=xpath,
        xml_data=xml_data,
        timestamp=time.time(),
        ttl=ttl,
    )

    try:
        store.put(namespace, cache_key, entry.to_dict())
        logger.debug(f"Cached config for xpath hash {cache_key[:8]}... (TTL={ttl}s)")
    except Exception as e:
        logger.error(f"Failed to cache config for {hostname}: {e}")


def get_cached_config(
    hostname: str,
    xpath: str,
    store: BaseStore,
) -> Optional[str]:
    """Retrieve cached configuration if not expired.

    Checks cache for previously fetched configuration data. Returns None if
    cache miss or entry has expired (past TTL).

    Args:
        hostname: Firewall hostname or IP address
        xpath: XPath to lookup
        store: BaseStore instance from graph runtime

    Returns:
        XML string if cache hit and not expired, None otherwise

    Example:
        ```python
        xml = get_cached_config("192.168.1.1", xpath, store)
        if xml:
            # Cache HIT - use cached data (no API call needed)
            logger.debug("Using cached configuration")
        else:
            # Cache MISS - fetch from firewall
            xml = await get_config(xpath, client)
            cache_config(hostname, xpath, xml, store)
        ```

    Note:
        - Returns None if entry expired (timestamp + ttl < now)
        - Expired entries are not automatically deleted (lazy expiration)
    """
    # Sanitize hostname for namespace
    sanitized_hostname = _sanitize_namespace_label(hostname)
    namespace = (NAMESPACE_CONFIG_CACHE, sanitized_hostname)

    # Generate cache key from xpath hash
    cache_key = _hash_xpath(xpath)

    try:
        result = store.get(namespace, cache_key)
        if not result:
            logger.debug(f"Cache MISS for xpath hash {cache_key[:8]}...")
            return None

        # Extract value
        data = result.value if hasattr(result, "value") else result

        # Reconstruct cache entry
        entry = CacheEntry.from_dict(data)

        # Check expiration
        if entry.is_expired():
            logger.debug(
                f"Cache EXPIRED for xpath hash {cache_key[:8]}... "
                f"(age={time.time() - entry.timestamp:.1f}s, ttl={entry.ttl}s)"
            )
            return None

        logger.debug(
            f"Cache HIT for xpath hash {cache_key[:8]}... "
            f"(age={time.time() - entry.timestamp:.1f}s, ttl={entry.ttl}s)"
        )
        return entry.xml_data

    except Exception as e:
        logger.error(f"Failed to retrieve cached config for {hostname}: {e}")
        return None


def invalidate_cache(
    hostname: str,
    xpath: Optional[str] = None,
    store: BaseStore = None,
) -> int:
    """Invalidate cached configuration.

    Removes cached entries to ensure fresh data after mutations. Can invalidate
    a specific xpath or all cached configs for a hostname.

    Args:
        hostname: Firewall hostname or IP address
        xpath: Specific XPath to invalidate, or None for all
        store: BaseStore instance from graph runtime

    Returns:
        Number of cache entries invalidated

    Example:
        ```python
        # Invalidate specific object after update
        invalidate_cache(
            "192.168.1.1",
            "/config/.../address/entry[@name='web-1']",
            store
        )

        # Invalidate all cached configs after commit
        invalidate_cache("192.168.1.1", None, store)
        ```

    Note:
        - Called automatically after create/update/delete operations
        - Ensures consistency between cache and firewall state
        - If xpath is None, clears all cache entries for hostname
    """
    if store is None:
        logger.warning("Cannot invalidate cache: store is None")
        return 0

    # Sanitize hostname for namespace
    sanitized_hostname = _sanitize_namespace_label(hostname)
    namespace = (NAMESPACE_CONFIG_CACHE, sanitized_hostname)

    try:
        if xpath is None:
            # Invalidate all cache entries for this hostname
            # Search and delete all entries in namespace
            results = store.search(namespace, limit=1000)
            count = 0
            for result in results:
                key = result.key if hasattr(result, "key") else None
                if key:
                    store.delete(namespace, key)
                    count += 1
            logger.debug(f"Invalidated {count} cache entries for {hostname}")
            return count
        else:
            # Invalidate specific xpath
            cache_key = _hash_xpath(xpath)
            result = store.get(namespace, cache_key)
            if result:
                store.delete(namespace, cache_key)
                logger.debug(f"Invalidated cache for xpath hash {cache_key[:8]}...")
                return 1
            return 0

    except Exception as e:
        logger.error(f"Failed to invalidate cache for {hostname}: {e}")
        return 0


# =============================================================================
# Firewall Configuration Storage (Long-term memory)
# =============================================================================


def store_firewall_config(
    hostname: str,
    config_type: str,
    data: dict[str, Any],
    store: BaseStore,
) -> None:
    """Store firewall configuration state.

    Stores metadata about firewall configuration operations (counts, recent operations)
    for use as context in future agent invocations.

    Args:
        hostname: Firewall hostname or IP address
        config_type: Type of configuration (e.g., "address_objects", "services")
        data: Configuration data dictionary with:
            - last_updated: ISO timestamp string
            - count: Number of objects of this type
            - recent_operations: List of recent operations (last 10)
            - metadata: Optional metadata dict
        store: BaseStore instance from graph runtime

    Example:
        ```python
        await store_firewall_config(
            hostname="192.168.1.1",
            config_type="address_objects",
            data={
                "last_updated": "2025-01-09T10:30:00Z",
                "count": 15,
                "recent_operations": [
                    {"operation": "create", "object_name": "web-1", "timestamp": "..."}
                ]
            },
            store=store
        )
        ```
    """
    # Sanitize hostname for namespace (no periods allowed)
    sanitized_hostname = _sanitize_namespace_label(hostname)
    namespace = (NAMESPACE_FIREWALL_CONFIGS, sanitized_hostname)
    # Key must be a string, encode config_type
    key = config_type

    try:
        store.put(namespace, key, data)
        logger.debug(
            f"Stored firewall config: {hostname}/{config_type} " f"(count={data.get('count', 0)})"
        )
    except Exception as e:
        logger.error(f"Failed to store firewall config {hostname}/{config_type}: {e}")


def retrieve_firewall_config(
    hostname: str,
    config_type: str,
    store: BaseStore,
) -> dict[str, Any] | None:
    """Retrieve firewall configuration state.

    Retrieves stored configuration metadata for a specific firewall and config type.

    Args:
        hostname: Firewall hostname or IP address
        config_type: Type of configuration to retrieve
        store: BaseStore instance from graph runtime

    Returns:
        Configuration data dictionary or None if not found

    Example:
        ```python
        config = await retrieve_firewall_config(
            hostname="192.168.1.1",
            config_type="address_objects",
            store=store
        )
        if config:
            print(f"Last updated: {config['last_updated']}")
            print(f"Count: {config['count']}")
        ```
    """
    # Sanitize hostname for namespace (no periods allowed)
    sanitized_hostname = _sanitize_namespace_label(hostname)
    namespace = (NAMESPACE_FIREWALL_CONFIGS, sanitized_hostname)
    # Key must be a string
    key = config_type

    try:
        result = store.get(namespace, key)
        if result:
            logger.debug(f"Retrieved firewall config: {hostname}/{config_type}")
            return result.value if hasattr(result, "value") else result
        return None
    except Exception as e:
        logger.error(f"Failed to retrieve firewall config {hostname}/{config_type}: {e}")
        return None


def store_workflow_execution(
    workflow_name: str,
    execution_data: dict[str, Any],
    store: BaseStore,
) -> None:
    """Store workflow execution history.

    Stores metadata about a workflow execution for history tracking and analysis.

    Args:
        workflow_name: Name of the workflow that was executed
        execution_data: Execution metadata dictionary with:
            - execution_id: Unique execution identifier (UUID string)
            - started_at: ISO timestamp when execution started
            - completed_at: ISO timestamp when execution completed (optional)
            - status: Execution status ("success", "failed", "partial")
            - steps_executed: Number of steps executed
            - steps_total: Total number of steps
            - results: List of step results
            - metadata: Optional metadata dict
        store: BaseStore instance from graph runtime

    Example:
        ```python
        await store_workflow_execution(
            workflow_name="web_server_setup",
            execution_data={
                "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                "started_at": "2025-01-09T10:00:00Z",
                "completed_at": "2025-01-09T10:05:00Z",
                "status": "success",
                "steps_executed": 4,
                "steps_total": 4,
                "results": [...]
            },
            store=store
        )
        ```
    """
    namespace = (NAMESPACE_WORKFLOW_HISTORY, workflow_name)
    execution_id = execution_data.get("execution_id")
    if not execution_id:
        logger.warning(f"No execution_id in workflow execution data for {workflow_name}")
        return

    # Key must be a string
    key = execution_id

    try:
        store.put(namespace, key, execution_data)
        logger.debug(
            f"Stored workflow execution: {workflow_name} "
            f"(id={execution_id}, status={execution_data.get('status')})"
        )
    except Exception as e:
        logger.error(f"Failed to store workflow execution {workflow_name}/{execution_id}: {e}")


def search_workflow_history(
    workflow_name: str,
    store: BaseStore,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search workflow execution history.

    Retrieves recent workflow executions for a specific workflow, sorted by
    started_at timestamp (most recent first).

    Args:
        workflow_name: Name of the workflow to search
        store: BaseStore instance from graph runtime
        limit: Maximum number of results to return (default: 10)

    Returns:
        List of execution records, sorted by started_at descending

    Example:
        ```python
        history = await search_workflow_history(
            workflow_name="web_server_setup",
            store=store,
            limit=5
        )
        for execution in history:
            print(f"{execution['started_at']}: {execution['status']}")
        ```
    """
    namespace = (NAMESPACE_WORKFLOW_HISTORY, workflow_name)

    try:
        # Get more results than needed, then sort and limit
        results = store.search(namespace, limit=limit * 10)  # Get more to sort properly
        if not results:
            return []

        # Convert results to list of dicts
        executions = []
        for result in results:
            value = result.value if hasattr(result, "value") else result
            if value:
                executions.append(value)

        # Sort by started_at descending (most recent first)
        executions.sort(key=lambda x: x.get("started_at", ""), reverse=True)

        # Apply limit after sorting
        return executions[:limit]
    except Exception as e:
        logger.error(f"Failed to search workflow history for {workflow_name}: {e}")
        return []


def get_firewall_operation_summary(
    hostname: str,
    store: BaseStore,
) -> dict[str, Any]:
    """Get summary of all operations on a firewall.

    Aggregates recent operations across all config types for a firewall.

    Args:
        hostname: Firewall hostname or IP address
        store: BaseStore instance from graph runtime

    Returns:
        Dictionary with summary:
            - total_objects: Total count across all types
            - recent_operations: Combined recent operations (last 20)
            - config_types: Dict of config_type -> count

    Example:
        ```python
        summary = await get_firewall_operation_summary(
            hostname="192.168.1.1",
            store=store
        )
        print(f"Total objects: {summary['total_objects']}")
        print(f"Recent operations: {len(summary['recent_operations'])}")
        ```
    """
    # Sanitize hostname for namespace (no periods allowed)
    sanitized_hostname = _sanitize_namespace_label(hostname)
    namespace = (NAMESPACE_FIREWALL_CONFIGS, sanitized_hostname)

    try:
        results = store.search(namespace, limit=100)  # Get all config types
        if not results:
            return {
                "total_objects": 0,
                "recent_operations": [],
                "config_types": {},
            }

        total_objects = 0
        config_types = {}
        all_operations = []

        for result in results:
            value = result.value if hasattr(result, "value") else result
            key = result.key if hasattr(result, "key") else ""
            if value:
                # Key is now a string (config_type), not a dict
                config_type = key if isinstance(key, str) else "unknown"
                count = value.get("count", 0)
                total_objects += count
                config_types[config_type] = count

                # Collect recent operations
                recent_ops = value.get("recent_operations", [])
                all_operations.extend(recent_ops)

        # Sort operations by timestamp descending
        all_operations.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return {
            "total_objects": total_objects,
            "recent_operations": all_operations[:20],  # Last 20 operations
            "config_types": config_types,
        }
    except Exception as e:
        logger.error(f"Failed to get firewall operation summary for {hostname}: {e}")
        return {
            "total_objects": 0,
            "recent_operations": [],
            "config_types": {},
        }
