"""NAT policy tools for PAN-OS.

Basic CRUD operations for NAT policy rule management.
Uses CRUD subgraph for async operations.
"""

import asyncio
import uuid
from typing import Optional

from langchain_core.tools import tool
from src.core.subgraphs.crud import create_crud_subgraph


@tool
def nat_policy_list() -> str:
    """List all NAT policy rules on PAN-OS firewall.

    Returns:
        List of NAT policy rules or error message

    Example:
        nat_policy_list()
    """
    crud_graph = create_crud_subgraph()

    try:
        result = asyncio.run(
            crud_graph.ainvoke(
                {
                    "operation_type": "list",
                    "object_type": "nat_policy",
                    "object_name": None,
                    "data": None,
                },
                config={"configurable": {"thread_id": str(uuid.uuid4())}},
            )
        )
        return result["message"]
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


@tool
def nat_policy_read(name: str) -> str:
    """Read an existing NAT policy rule from PAN-OS firewall.

    Args:
        name: Name of the NAT policy rule to retrieve

    Returns:
        NAT policy rule details or error message

    Example:
        nat_policy_read(name="outbound-nat")
    """
    crud_graph = create_crud_subgraph()

    try:
        result = asyncio.run(
            crud_graph.ainvoke(
                {
                    "operation_type": "read",
                    "object_type": "nat_policy",
                    "object_name": name,
                    "data": None,
                },
                config={"configurable": {"thread_id": str(uuid.uuid4())}},
            )
        )
        return result["message"]
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


@tool
def nat_policy_create_source(
    name: str,
    fromzone: list[str],
    tozone: list[str],
    source: list[str],
    destination: list[str],
    service: str = "any",
    source_translation_type: str = "dynamic-ip-and-port",
    source_translation_address_type: str = "interface-address",
    source_translation_interface: Optional[str] = None,
    description: Optional[str] = None,
    tag: Optional[list[str]] = None,
) -> str:
    """Create a source NAT policy rule on PAN-OS firewall.

    Args:
        name: Name of the NAT policy rule
        fromzone: List of source zones
        tozone: List of destination zones
        source: List of source addresses
        destination: List of destination addresses
        service: Service (default: "any")
        source_translation_type: Type of source NAT (default: "dynamic-ip-and-port")
        source_translation_address_type: Address type for translation (default: "interface-address")
        source_translation_interface: Interface for translation (optional)
        description: Optional description
        tag: Optional list of tags

    Returns:
        Success/failure message

    Example:
        nat_policy_create_source(
            name="outbound-nat",
            fromzone=["trust"],
            tozone=["untrust"],
            source=["10.1.1.0/24"],
            destination=["any"],
            source_translation_interface="ethernet1/1",
            description="Outbound NAT for internal network"
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
        "source_translation_type": source_translation_type,
        "source_translation_address_type": source_translation_address_type,
    }

    if source_translation_interface:
        data["source_translation_interface"] = source_translation_interface
    if description:
        data["description"] = description
    if tag:
        data["tag"] = tag

    try:
        result = asyncio.run(
            crud_graph.ainvoke(
                {
                    "operation_type": "create",
                    "object_type": "nat_policy",
                    "data": data,
                    "object_name": name,
                },
                config={"configurable": {"thread_id": str(uuid.uuid4())}},
            )
        )
        return result["message"]
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


@tool
def nat_policy_delete(name: str) -> str:
    """Delete a NAT policy rule from PAN-OS firewall.

    Args:
        name: Name of the NAT policy rule to delete

    Returns:
        Success/failure message

    Example:
        nat_policy_delete(name="old-nat-rule")
    """
    crud_graph = create_crud_subgraph()

    try:
        result = asyncio.run(
            crud_graph.ainvoke(
                {
                    "operation_type": "delete",
                    "object_type": "nat_policy",
                    "object_name": name,
                    "data": None,
                },
                config={"configurable": {"thread_id": str(uuid.uuid4())}},
            )
        )
        return result["message"]
    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


# Export all tools
NAT_POLICY_TOOLS = [
    nat_policy_list,
    nat_policy_read,
    nat_policy_create_source,
    nat_policy_delete,
]
