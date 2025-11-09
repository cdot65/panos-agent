"""Template Stack tools for Panorama.

Tools for creating, reading, updating, deleting, and listing template stacks.
Template stacks group multiple templates for flexible inheritance hierarchy.
"""

import uuid
from typing import Optional

from langchain_core.tools import tool

from src.core.client import get_device_context
from src.core.subgraphs.crud import create_crud_subgraph


@tool
async def template_stack_create(
    name: str,
    templates: list[str],
    description: Optional[str] = None,
    mode: str = "skip_if_exists",
) -> str:
    """Create a new template stack on Panorama (idempotent).

    Template stacks combine multiple templates into an ordered inheritance hierarchy.
    Settings are inherited from templates in order (first template = highest priority).

    Args:
        name: Name of the template stack
        templates: Ordered list of template names (first = highest priority)
        description: Optional description
        mode: Error handling mode - "skip_if_exists" (skip if exists, default) or "strict" (fail if exists)

    Returns:
        Success/failure message

    Example:
        template_stack_create(name="prod-stack", templates=["prod-specific", "base-template"])
        template_stack_create(name="branch-stack", templates=["branch-template"], description="Branch offices")
    """
    crud_graph = create_crud_subgraph()

    data = {
        "name": name,
        "templates": templates,
    }

    if description:
        data["description"] = description

    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: template_stack operations require a Panorama device"

        result = await crud_graph.ainvoke(
            {
                "operation_type": "create",
                "object_type": "template_stack",
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
async def template_stack_read(name: str) -> str:
    """Read an existing template stack from Panorama.

    Args:
        name: Name of the template stack to retrieve

    Returns:
        Template stack details or error message

    Example:
        template_stack_read(name="prod-stack")
    """
    crud_graph = create_crud_subgraph()

    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: template_stack operations require a Panorama device"

        result = await crud_graph.ainvoke(
            {
                "operation_type": "read",
                "object_type": "template_stack",
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
async def template_stack_update(
    name: str,
    templates: Optional[list[str]] = None,
    description: Optional[str] = None,
) -> str:
    """Update an existing template stack on Panorama.

    Args:
        name: Name of the template stack to update
        templates: New ordered list of template names (optional)
        description: New description (optional)

    Returns:
        Success/failure message

    Example:
        template_stack_update(name="prod-stack", templates=["prod-v2", "base-template"])
        template_stack_update(name="prod-stack", description="Updated production stack")
    """
    crud_graph = create_crud_subgraph()

    data = {}
    if templates is not None:
        data["templates"] = templates
    if description:
        data["description"] = description

    if not data:
        return "❌ Error: No fields provided for update"

    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: template_stack operations require a Panorama device"

        result = await crud_graph.ainvoke(
            {
                "operation_type": "update",
                "object_type": "template_stack",
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
async def template_stack_delete(name: str, mode: str = "strict") -> str:
    """Delete a template stack from Panorama.

    CAUTION: Deleting a template stack removes the stack configuration.
    Devices using this stack will lose their template-based settings.

    Args:
        name: Name of the template stack to delete
        mode: Error handling mode - "strict" (fail if missing) or "skip_if_missing" (skip if missing)

    Returns:
        Success/failure message

    Example:
        template_stack_delete(name="old-stack")
    """
    crud_graph = create_crud_subgraph()

    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: template_stack operations require a Panorama device"

        result = await crud_graph.ainvoke(
            {
                "operation_type": "delete",
                "object_type": "template_stack",
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
async def template_stack_list() -> str:
    """List all template stacks on Panorama.

    Returns:
        List of template stacks or error message

    Example:
        template_stack_list()
    """
    crud_graph = create_crud_subgraph()

    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: template_stack operations require a Panorama device"

        result = await crud_graph.ainvoke(
            {
                "operation_type": "list",
                "object_type": "template_stack",
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
TEMPLATE_STACK_TOOLS = [
    template_stack_create,
    template_stack_read,
    template_stack_update,
    template_stack_delete,
    template_stack_list,
]
