# Memory Schema Documentation

**Purpose:** Long-term memory storage for PAN-OS agent across sessions using LangGraph Store API.

**Last Updated:** 2025-01-09

---

## Overview

The Store API provides persistent memory that survives across graph invocations and sessions. Unlike checkpoints (which store conversation state), the Store API stores operational context and history.

**Key Use Cases:**
- Remember firewall configuration state across sessions
- Track workflow execution history
- Provide context to agent about previous operations
- Enable "memory" of what was created/modified on each firewall

---

## Namespace Structure

Namespaces are tuples that organize data hierarchically. Each namespace represents a logical grouping of related data.

### 1. Firewall Configuration Namespace

**Namespace:** `("firewall_configs", hostname)`

**Purpose:** Store firewall-specific configuration state and operation history.

**Key Structure:**
```python
{
    "config_type": "address_objects" | "services" | "security_policies" | ...
}
```

**Value Structure:**
```python
{
    "last_updated": "2025-01-09T10:30:00Z",  # ISO timestamp
    "count": 42,  # Number of objects of this type
    "recent_operations": [  # Last 10 operations
        {
            "operation": "create",
            "object_name": "web-server-1",
            "timestamp": "2025-01-09T10:25:00Z"
        },
        ...
    ],
    "metadata": {
        "firewall_version": "11.1.4-h7",
        "serial": "021201109830"
    }
}
```

**Example Usage:**
```python
# Store address objects state
await store.put(
    namespace=("firewall_configs", "192.168.1.1"),
    key={"config_type": "address_objects"},
    value={
        "last_updated": "2025-01-09T10:30:00Z",
        "count": 15,
        "recent_operations": [...]
    }
)

# Retrieve address objects state
results = await store.search(
    namespace_prefix=("firewall_configs", "192.168.1.1")
)
```

---

### 2. Workflow History Namespace

**Namespace:** `("workflow_history", workflow_name)`

**Purpose:** Store execution history for deterministic workflows.

**Key Structure:**
```python
{
    "execution_id": "uuid-string"  # Unique execution identifier
}
```

**Value Structure:**
```python
{
    "workflow_name": "web_server_setup",
    "execution_id": "550e8400-e29b-41d4-a716-446655440000",
    "started_at": "2025-01-09T10:00:00Z",
    "completed_at": "2025-01-09T10:05:00Z",
    "status": "success" | "failed" | "partial",
    "steps_executed": 4,
    "steps_total": 4,
    "results": [
        {
            "step": 1,
            "name": "Create address object",
            "status": "success",
            "output": "✅ Created address object: web-1"
        },
        ...
    ],
    "metadata": {
        "thread_id": "user-123",
        "firewall_hostname": "192.168.1.1"
    }
}
```

**Example Usage:**
```python
# Store workflow execution
await store.put(
    namespace=("workflow_history", "web_server_setup"),
    key={"execution_id": "550e8400-..."},
    value={
        "workflow_name": "web_server_setup",
        "status": "success",
        "steps_executed": 4,
        ...
    }
)

# Search recent executions
results = await store.search(
    namespace_prefix=("workflow_history", "web_server_setup")
)
# Returns list of executions, sorted by started_at descending
```

---

### 3. User Preferences Namespace (Future)

**Namespace:** `("user_preferences", user_id)`

**Purpose:** Store user-specific settings and preferences.

**Status:** Reserved for future implementation.

**Planned Key Structure:**
```python
{
    "preference_type": "default_mode" | "model_preference" | ...
}
```

---

## Helper Functions

All helper functions are defined in `src/core/memory_store.py`:

### Firewall Configuration

```python
async def store_firewall_config(
    hostname: str,
    config_type: str,
    data: dict,
    store: BaseStore
) -> None:
    """Store firewall configuration state.
    
    Args:
        hostname: Firewall hostname/IP
        config_type: Type of config (address_objects, services, etc.)
        data: Configuration data dict
        store: Store instance (from graph runtime)
    """

async def retrieve_firewall_config(
    hostname: str,
    config_type: str,
    store: BaseStore
) -> dict | None:
    """Retrieve firewall configuration state.
    
    Args:
        hostname: Firewall hostname/IP
        config_type: Type of config to retrieve
        store: Store instance
        
    Returns:
        Configuration dict or None if not found
    """
```

### Workflow History

```python
async def store_workflow_execution(
    workflow_name: str,
    execution_data: dict,
    store: BaseStore
) -> None:
    """Store workflow execution history.
    
    Args:
        workflow_name: Name of workflow
        execution_data: Execution metadata and results
        store: Store instance
    """

async def search_workflow_history(
    workflow_name: str,
    limit: int = 10,
    store: BaseStore
) -> list[dict]:
    """Search workflow execution history.
    
    Args:
        workflow_name: Name of workflow
        limit: Maximum number of results
        store: Store instance
        
    Returns:
        List of execution records, sorted by started_at descending
    """
```

---

## Data Persistence

**Current Implementation:** `InMemoryStore`

- Data stored in RAM
- Lost on process restart
- Suitable for development and single-session use

**Future Upgrade:** Persistent Store (PostgreSQL, Redis, etc.)

- Data survives restarts
- Suitable for production multi-user deployments
- Requires external database

---

## Integration Points

### 1. Autonomous Graph

**Location:** `src/autonomous_graph.py`

**Integration:**
- `call_agent` node receives `store: BaseStore` parameter
- Retrieves firewall config context before agent call
- Stores operation results after tool execution

**Example:**
```python
def call_agent(state: AutonomousState, *, store: BaseStore) -> AutonomousState:
    # Retrieve context
    hostname = get_settings().panos_hostname
    context = await retrieve_firewall_config(hostname, "address_objects", store)
    
    # Add context to system prompt
    if context:
        memory_context = f"Recent operations: {context['recent_operations']}"
        # ... add to prompt
    
    # ... call LLM
```

### 2. Deterministic Graph

**Location:** `src/deterministic_graph.py`

**Integration:**
- `execute_workflow` node receives `store: BaseStore` parameter
- Stores workflow execution metadata after completion
- Enables workflow history queries

**Example:**
```python
def execute_workflow(state: DeterministicState, *, store: BaseStore) -> DeterministicState:
    # ... execute workflow
    
    # Store execution history
    await store_workflow_execution(
        workflow_name=workflow_name,
        execution_data={
            "status": "success",
            "steps_executed": len(results),
            ...
        },
        store=store
    )
```

---

## Security Considerations

1. **No Sensitive Data**: Store only metadata, not passwords or API keys
2. **Namespace Isolation**: Each firewall has separate namespace
3. **Access Control**: Future persistent stores should implement access control
4. **Data Retention**: Consider TTL for old workflow history (future)

---

## References

- LangGraph Store API: <https://langchain-ai.github.io/langgraph/how-tos/memory/>
- `docs/recommendations/12-add-memory.md` (lines 79-154)

