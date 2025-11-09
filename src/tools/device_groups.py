"""Device Group tools for Panorama.

Tools for creating, reading, updating, deleting, and listing device groups.
Device groups organize firewalls for policy and object management.
"""

import uuid
from typing import Optional

from langchain_core.tools import tool

from src.core.client import get_device_context
from src.core.subgraphs.crud import create_crud_subgraph


@tool
async def device_group_create(
    name: str,
    description: Optional[str] = None,
    parent_device_group: Optional[str] = None,
    reference_templates: Optional[list[str]] = None,
    mode: str = "skip_if_exists",
) -> str:
    """Create a new device group on Panorama (idempotent).

    Device groups organize firewalls for centralized policy and object management.
    Supports hierarchical groups with parent-child relationships.

    Args:
        name: Name of the device group
        description: Optional description
        parent_device_group: Optional parent device group name (for hierarchical groups)
        reference_templates: Optional list of template names to reference
        mode: Error handling mode - "skip_if_exists" (skip if exists, default) or "strict" (fail if exists)

    Returns:
        Success/failure message

    Example:
        device_group_create(name="production", description="Production firewalls")
        device_group_create(name="prod-dmz", parent_device_group="production")
    """
    crud_graph = create_crud_subgraph()

    data = {
        "name": name,
    }

    if description:
        data["description"] = description
    if parent_device_group:
        data["parent_device_group"] = parent_device_group
    if reference_templates:
        data["reference_templates"] = reference_templates

    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: device_group operations require a Panorama device"

        result = await crud_graph.ainvoke(
            {
                "operation_type": "create",
                "object_type": "device_group",
                "data": data,
                "object_name": name,
                "mode": mode,
                "device_context": device_context,
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}},
        )
        return result["message"]
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


@tool
async def device_group_read(name: str) -> str:
    """Read an existing device group from Panorama.

    Args:
        name: Name of the device group to retrieve

    Returns:
        Device group details or error message

    Example:
        device_group_read(name="production")
    """
    crud_graph = create_crud_subgraph()

    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: device_group operations require a Panorama device"

        result = await crud_graph.ainvoke(
            {
                "operation_type": "read",
                "object_type": "device_group",
                "object_name": name,
                "data": None,
                "device_context": device_context,
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}},
        )
        return result["message"]
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


@tool
async def device_group_update(
    name: str,
    description: Optional[str] = None,
    reference_templates: Optional[list[str]] = None,
) -> str:
    """Update an existing device group on Panorama.

    Args:
        name: Name of the device group to update
        description: New description (optional)
        reference_templates: New list of template references (optional)

    Returns:
        Success/failure message

    Example:
        device_group_update(name="production", description="Updated production group")
    """
    crud_graph = create_crud_subgraph()

    data = {}
    if description:
        data["description"] = description
    if reference_templates is not None:
        data["reference_templates"] = reference_templates

    if not data:
        return "❌ Error: No fields provided for update"

    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: device_group operations require a Panorama device"

        result = await crud_graph.ainvoke(
            {
                "operation_type": "update",
                "object_type": "device_group",
                "object_name": name,
                "data": data,
                "device_context": device_context,
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}},
        )
        return result["message"]
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


@tool
async def device_group_delete(name: str, mode: str = "strict") -> str:
    """Delete a device group from Panorama.

    CAUTION: Deleting a device group removes all policies and objects within it.
    Devices in the group will be orphaned and need reassignment.

    Args:
        name: Name of the device group to delete
        mode: Error handling mode - "strict" (fail if missing) or "skip_if_missing" (skip if missing)

    Returns:
        Success/failure message

    Example:
        device_group_delete(name="old-group")
    """
    crud_graph = create_crud_subgraph()

    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: device_group operations require a Panorama device"

        result = await crud_graph.ainvoke(
            {
                "operation_type": "delete",
                "object_type": "device_group",
                "object_name": name,
                "data": None,
                "mode": mode,
                "device_context": device_context,
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}},
        )
        return result["message"]
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


@tool
async def device_group_list() -> str:
    """List all device groups on Panorama.

    Returns:
        List of device groups or error message

    Example:
        device_group_list()
    """
    crud_graph = create_crud_subgraph()

    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: device_group operations require a Panorama device"

        result = await crud_graph.ainvoke(
            {
                "operation_type": "list",
                "object_type": "device_group",
                "object_name": None,
                "data": None,
                "device_context": device_context,
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}},
        )
        return result["message"]
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


# Export all tools
DEVICE_GROUP_TOOLS = [
    device_group_create,
    device_group_read,
    device_group_update,
    device_group_delete,
    device_group_list,
]
