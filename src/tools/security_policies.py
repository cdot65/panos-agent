"""Security policy tools for PAN-OS.

Full CRUD operations for security policy rule management.
Uses CRUD subgraph for async operations.
"""

import uuid
from typing import Optional

from langchain_core.tools import tool

from src.core.subgraphs.crud import create_crud_subgraph


@tool
async def security_policy_list() -> str:
    """List all security policy rules on PAN-OS firewall.

    Returns:
        List of security policy rules or error message

    Example:
        security_policy_list()
    """
    crud_graph = create_crud_subgraph()

    try:
        result = await crud_graph.ainvoke(
            {
                "operation_type": "list",
                "object_type": "security_policy",
                "object_name": None,
                "data": None,
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}},
        )
        return result["message"]
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


@tool
async def security_policy_read(name: str) -> str:
    """Read an existing security policy rule from PAN-OS firewall.

    Args:
        name: Name of the security policy rule to retrieve

    Returns:
        Security policy rule details or error message

    Example:
        security_policy_read(name="allow-web-traffic")
    """
    crud_graph = create_crud_subgraph()

    try:
        result = await crud_graph.ainvoke(
            {
                "operation_type": "read",
                "object_type": "security_policy",
                "object_name": name,
                "data": None,
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}},
        )
        return result["message"]
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


@tool
async def security_policy_create(
    name: str,
    fromzone: list[str],
    tozone: list[str],
    source: list[str],
    destination: list[str],
    service: list[str],
    action: str = "allow",
    description: Optional[str] = None,
    tag: Optional[list[str]] = None,
    log_end: bool = True,
) -> str:
    """Create a new security policy rule on PAN-OS firewall.

    Args:
        name: Name of the security policy rule
        fromzone: List of source zones (e.g., ["trust"])
        tozone: List of destination zones (e.g., ["untrust"])
        source: List of source addresses (e.g., ["any", "10.1.1.0/24"])
        destination: List of destination addresses (e.g., ["any"])
        service: List of services (e.g., ["application-default", "service-http"])
        action: Action to take (allow, deny, drop) - default: allow
        description: Optional description
        tag: Optional list of tags
        log_end: Log at session end (default: True)

    Returns:
        Success/failure message

    Example:
        security_policy_create(
            name="allow-web-traffic",
            fromzone=["trust"],
            tozone=["untrust"],
            source=["10.1.1.0/24"],
            destination=["any"],
            service=["service-http", "service-https"],
            action="allow",
            description="Allow web traffic from internal network"
        )
    """
    crud_graph = create_crud_subgraph()

    data = {
        "name": name,
        "fromzone": fromzone,
        "tozone": tozone,
        "source": source,
        "destination": destination,
        "service": service,
        "action": action,
        "log_end": log_end,
    }

    if description:
        data["description"] = description
    if tag:
        data["tag"] = tag

    try:
        result = await crud_graph.ainvoke(
            {
                "operation_type": "create",
                "object_type": "security_policy",
                "data": data,
                "object_name": name,
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}},
        )
        return result["message"]
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


@tool
async def security_policy_update(
    name: str,
    fromzone: Optional[list[str]] = None,
    tozone: Optional[list[str]] = None,
    source: Optional[list[str]] = None,
    destination: Optional[list[str]] = None,
    service: Optional[list[str]] = None,
    action: Optional[str] = None,
    description: Optional[str] = None,
    tag: Optional[list[str]] = None,
) -> str:
    """Update an existing security policy rule on PAN-OS firewall.

    Args:
        name: Name of the security policy rule to update
        fromzone: New source zones (optional)
        tozone: New destination zones (optional)
        source: New source addresses (optional)
        destination: New destination addresses (optional)
        service: New services (optional)
        action: New action (optional)
        description: New description (optional)
        tag: New tags (optional)

    Returns:
        Success/failure message

    Example:
        security_policy_update(
            name="allow-web-traffic",
            source=["10.1.1.0/24", "10.2.1.0/24"],
            description="Updated to include 10.2.1.0/24"
        )
    """
    crud_graph = create_crud_subgraph()

    data = {}
    if fromzone is not None:
        data["fromzone"] = fromzone
    if tozone is not None:
        data["tozone"] = tozone
    if source is not None:
        data["source"] = source
    if destination is not None:
        data["destination"] = destination
    if service is not None:
        data["service"] = service
    if action is not None:
        data["action"] = action
    if description is not None:
        data["description"] = description
    if tag is not None:
        data["tag"] = tag

    if not data:
        return "❌ Error: No fields provided for update"

    try:
        result = await crud_graph.ainvoke(
            {
                "operation_type": "update",
                "object_type": "security_policy",
                "object_name": name,
                "data": data,
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}},
        )
        return result["message"]
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


@tool
async def security_policy_delete(name: str) -> str:
    """Delete a security policy rule from PAN-OS firewall.

    Args:
        name: Name of the security policy rule to delete

    Returns:
        Success/failure message

    Example:
        security_policy_delete(name="old-rule")
    """
    crud_graph = create_crud_subgraph()

    try:
        result = await crud_graph.ainvoke(
            {
                "operation_type": "delete",
                "object_type": "security_policy",
                "object_name": name,
                "data": None,
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}},
        )
        return result["message"]
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


# Export all tools
SECURITY_POLICY_TOOLS = [
    security_policy_list,
    security_policy_read,
    security_policy_create,
    security_policy_update,
    security_policy_delete,
]
