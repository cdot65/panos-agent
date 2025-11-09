"""Template tools for Panorama.

Tools for creating, reading, updating, deleting, and listing templates.
Templates define network and device settings for managed firewalls.
"""

import uuid
from typing import Optional

from langchain_core.tools import tool

from src.core.client import get_device_context
from src.core.subgraphs.crud import create_crud_subgraph


@tool
async def template_create(
    name: str,
    description: Optional[str] = None,
    mode: str = "skip_if_exists",
) -> str:
    """Create a new template on Panorama (idempotent).

    Templates define network and device settings (zones, interfaces, VLANs, etc.)
    that can be applied to managed firewalls.

    Args:
        name: Name of the template
        description: Optional description
        mode: Error handling mode - "skip_if_exists" (skip if exists, default) or "strict" (fail if exists)

    Returns:
        Success/failure message

    Example:
        template_create(name="dmz-template", description="DMZ network configuration")
        template_create(name="branch-template", description="Branch office template")
    """
    crud_graph = create_crud_subgraph()

    data = {
        "name": name,
    }

    if description:
        data["description"] = description

    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: template operations require a Panorama device"

        result = await crud_graph.ainvoke(
            {
                "operation_type": "create",
                "object_type": "template",
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
async def template_read(name: str) -> str:
    """Read an existing template from Panorama.

    Args:
        name: Name of the template to retrieve

    Returns:
        Template details or error message

    Example:
        template_read(name="dmz-template")
    """
    crud_graph = create_crud_subgraph()

    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: template operations require a Panorama device"

        result = await crud_graph.ainvoke(
            {
                "operation_type": "read",
                "object_type": "template",
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
async def template_update(
    name: str,
    description: Optional[str] = None,
) -> str:
    """Update an existing template on Panorama.

    Args:
        name: Name of the template to update
        description: New description (optional)

    Returns:
        Success/failure message

    Example:
        template_update(name="dmz-template", description="Updated DMZ configuration")
    """
    crud_graph = create_crud_subgraph()

    data = {}
    if description:
        data["description"] = description

    if not data:
        return "❌ Error: No fields provided for update"

    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: template operations require a Panorama device"

        result = await crud_graph.ainvoke(
            {
                "operation_type": "update",
                "object_type": "template",
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
async def template_delete(name: str, mode: str = "strict") -> str:
    """Delete a template from Panorama.

    CAUTION: Deleting a template removes all network/device settings within it.
    Devices using this template will lose their configuration.

    Args:
        name: Name of the template to delete
        mode: Error handling mode - "strict" (fail if missing) or "skip_if_missing" (skip if missing)

    Returns:
        Success/failure message

    Example:
        template_delete(name="old-template")
    """
    crud_graph = create_crud_subgraph()

    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: template operations require a Panorama device"

        result = await crud_graph.ainvoke(
            {
                "operation_type": "delete",
                "object_type": "template",
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
async def template_list() -> str:
    """List all templates on Panorama.

    Returns:
        List of templates or error message

    Example:
        template_list()
    """
    crud_graph = create_crud_subgraph()

    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: template operations require a Panorama device"

        result = await crud_graph.ainvoke(
            {
                "operation_type": "list",
                "object_type": "template",
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
TEMPLATE_TOOLS = [
    template_create,
    template_read,
    template_update,
    template_delete,
    template_list,
]
