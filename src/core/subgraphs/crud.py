"""CRUD subgraph for single PAN-OS object operations.

Workflow: validate → check_existence → create/update/delete → verify → format

Async implementation using lxml + httpx for PAN-OS XML API.
"""

import logging
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from lxml import etree

from src.core.client import get_panos_client
from src.core.panos_api import (
    PanOSAPIError,
    PanOSConnectionError,
    build_xpath,
    delete_config,
    edit_config,
    get_config,
    set_config,
)
from src.core.panos_models import parse_xml_to_dict
from src.core.retry_policies import PANOS_RETRY_POLICY
from src.core.state_schemas import CRUDState

logger = logging.getLogger(__name__)


async def validate_input(state: CRUDState) -> CRUDState:
    """Validate CRUD operation inputs with PAN-OS rules.

    Args:
        state: Current CRUD state

    Returns:
        Updated state with validation_result
    """
    from src.core.panos_xpath_map import PanOSXPathMap, validate_object_data

    logger.debug(f"Validating {state['operation_type']} for {state['object_type']}")

    # Check required fields
    if state["operation_type"] in ["create", "update"] and not state.get("data"):
        return {
            **state,
            "validation_result": "❌ Missing required 'data' field",
            "error": "Missing data for create/update operation",
        }

    if state["operation_type"] in ["read", "update", "delete"] and not state.get("object_name"):
        return {
            **state,
            "validation_result": "❌ Missing required 'object_name' field",
            "error": "Missing object_name for operation",
        }

    # Validate object type
    valid_types = [
        "address",
        "address-group",
        "service",
        "service-group",
        "security-policy",
        "nat-policy",
    ]
    if state["object_type"] not in valid_types:
        return {
            **state,
            "validation_result": f"❌ Unsupported object_type: {state['object_type']}",
            "error": f"Object type {state['object_type']} not supported",
        }

    # Validate object name with PAN-OS rules
    if state.get("object_name"):
        is_valid, error = PanOSXPathMap.validate_object_name(state["object_name"])
        if not is_valid:
            logger.warning(f"Invalid object name: {error}")
            return {
                **state,
                "validation_result": f"❌ Invalid object name: {error}",
                "error": f"Name validation failed: {error}",
            }

    # Validate object data with PAN-OS rules
    if state.get("data") and state["operation_type"] in ["create", "update"]:
        # Normalize object type (remove hyphens for validation)
        normalized_type = state["object_type"].replace("-", "_")
        is_valid, error = validate_object_data(normalized_type, state["data"])
        if not is_valid:
            logger.warning(f"Invalid object data: {error}")
            return {
                **state,
                "validation_result": f"❌ Invalid object data: {error}",
                "error": f"Data validation failed: {error}",
            }

    logger.debug("✅ Validation passed (including PAN-OS rules)")
    return {
        **state,
        "validation_result": "✅ Validation passed",
    }


async def check_existence(state: CRUDState) -> CRUDState:
    """Check if object exists on firewall.

    Args:
        state: Current CRUD state

    Returns:
        Updated state with exists flag
    """
    if state.get("error"):
        return state  # Skip if validation failed

    if state["operation_type"] == "list":
        return state  # Skip for list operations

    logger.debug(f"Checking existence of {state['object_type']}: {state['object_name']}")

    try:
        client = await get_panos_client()
        xpath = build_xpath(state["object_type"], name=state["object_name"])

        # Try to get the config
        try:
            result = await get_config(xpath, client)
            exists = result is not None and len(result) > 0
            logger.debug(f"Object exists: {exists}")
            return {**state, "exists": exists}
        except PanOSAPIError as e:
            # Object not found is not an error for existence check
            if "does not exist" in str(e).lower() or "not present" in str(e).lower():
                logger.debug("Object does not exist")
                return {**state, "exists": False}
            raise

    except PanOSConnectionError as e:
        logger.error(f"PAN-OS connectivity error checking existence: {e}")
        return {
            **state,
            "exists": False,
            "error": f"Connectivity error: {e}",
        }
    except PanOSAPIError as e:
        logger.error(f"PAN-OS API error checking existence: {e}")
        return {
            **state,
            "exists": False,
            "error": f"API error: {e}",
        }
    except Exception as e:
        logger.error(f"Unexpected error checking existence: {e}", exc_info=True)
        return {
            **state,
            "exists": False,
            "error": f"Unexpected error: {e}",
        }


def route_operation(
    state: CRUDState,
) -> Literal[
    "create_object",
    "read_object",
    "update_object",
    "delete_object",
    "list_objects",
    "format_response",
]:
    """Route to appropriate operation based on operation_type.

    Args:
        state: Current CRUD state

    Returns:
        Next node name
    """
    if state.get("error"):
        return "format_response"

    operation_map = {
        "create": "create_object",
        "read": "read_object",
        "update": "update_object",
        "delete": "delete_object",
        "list": "list_objects",
    }

    return operation_map[state["operation_type"]]


def build_object_xml(object_type: str, data: dict[str, Any]) -> etree._Element:
    """Build XML element for PAN-OS object.

    Args:
        object_type: Type of object
        data: Object data

    Returns:
        lxml Element
    """
    name = data.get("name", "")
    entry = etree.Element("entry", name=name)

    if object_type == "address":
        # Address object
        addr_type = data.get("type", "ip-netmask")
        type_elem = etree.SubElement(entry, addr_type)
        type_elem.text = data.get("value", "")

        if data.get("description"):
            desc_elem = etree.SubElement(entry, "description")
            desc_elem.text = data["description"]

        if data.get("tags"):
            tag_elem = etree.SubElement(entry, "tag")
            for tag in data["tags"]:
                member = etree.SubElement(tag_elem, "member")
                member.text = tag

    elif object_type == "address-group":
        # Address group
        if data.get("static_members"):
            static_elem = etree.SubElement(entry, "static")
            for member in data["static_members"]:
                member_elem = etree.SubElement(static_elem, "member")
                member_elem.text = member

        if data.get("dynamic_filter"):
            dynamic_elem = etree.SubElement(entry, "dynamic")
            filter_elem = etree.SubElement(dynamic_elem, "filter")
            filter_elem.text = data["dynamic_filter"]

        if data.get("description"):
            desc_elem = etree.SubElement(entry, "description")
            desc_elem.text = data["description"]

    elif object_type == "service":
        # Service object
        protocol = data.get("protocol", "tcp")
        protocol_elem = etree.SubElement(entry, "protocol")
        proto_type_elem = etree.SubElement(protocol_elem, protocol)
        port_elem = etree.SubElement(proto_type_elem, "port")
        port_elem.text = str(data.get("port", ""))

        if data.get("description"):
            desc_elem = etree.SubElement(entry, "description")
            desc_elem.text = data["description"]

    elif object_type == "service-group":
        # Service group
        members_elem = etree.SubElement(entry, "members")
        for member in data.get("members", []):
            member_elem = etree.SubElement(members_elem, "member")
            member_elem.text = member

        if data.get("description"):
            desc_elem = etree.SubElement(entry, "description")
            desc_elem.text = data["description"]

    elif object_type == "security-policy":
        # Security policy rule
        # Source zones
        if data.get("source_zones"):
            from_elem = etree.SubElement(entry, "from")
            for zone in data["source_zones"]:
                member = etree.SubElement(from_elem, "member")
                member.text = zone

        # Destination zones
        if data.get("destination_zones"):
            to_elem = etree.SubElement(entry, "to")
            for zone in data["destination_zones"]:
                member = etree.SubElement(to_elem, "member")
                member.text = zone

        # Source addresses
        if data.get("source_addresses"):
            source_elem = etree.SubElement(entry, "source")
            for addr in data["source_addresses"]:
                member = etree.SubElement(source_elem, "member")
                member.text = addr

        # Destination addresses
        if data.get("destination_addresses"):
            dest_elem = etree.SubElement(entry, "destination")
            for addr in data["destination_addresses"]:
                member = etree.SubElement(dest_elem, "member")
                member.text = addr

        # Applications
        if data.get("applications"):
            app_elem = etree.SubElement(entry, "application")
            for app in data["applications"]:
                member = etree.SubElement(app_elem, "member")
                member.text = app

        # Services
        if data.get("services"):
            svc_elem = etree.SubElement(entry, "service")
            for svc in data["services"]:
                member = etree.SubElement(svc_elem, "member")
                member.text = svc

        # Action
        action_elem = etree.SubElement(entry, "action")
        action_elem.text = data.get("action", "allow")

        # Logging
        if data.get("log_start", False):
            log_start = etree.SubElement(entry, "log-start")
            log_start.text = "yes"

        if data.get("log_end", True):
            log_end = etree.SubElement(entry, "log-end")
            log_end.text = "yes"

        if data.get("description"):
            desc_elem = etree.SubElement(entry, "description")
            desc_elem.text = data["description"]

    return entry


async def create_object(state: CRUDState) -> CRUDState:
    """Create new PAN-OS object.

    Args:
        state: Current CRUD state

    Returns:
        Updated state with operation_result
    """
    mode = state.get("mode", "skip_if_exists")  # Changed default to skip_if_exists for idempotency
    object_name = state["data"].get("name")

    # Check if already exists (idempotent behavior)
    if state.get("exists"):
        if mode == "skip_if_exists":
            logger.info(f"⏭️  Object {object_name} already exists (skipped)")
            return {
                **state,
                "operation_result": {
                    "status": "skipped",
                    "name": object_name,
                    "object_type": state["object_type"],
                    "reason": "already_exists",
                },
                "message": f"⏭️  Skipped: {state['object_type']} '{object_name}' already exists",
            }
        # Strict mode - fail if exists (only when explicitly requested)
        return {
            **state,
            "error": f"Object {object_name} already exists",
            "operation_result": {"status": "error", "message": "Object already exists"},
        }

    # Actually create the object
    logger.debug(f"Creating {state['object_type']}: {object_name}")

    try:
        client = await get_panos_client()
        xpath = build_xpath(state["object_type"])

        # Build XML element
        element = build_object_xml(state["object_type"], state["data"])

        # Create via set config
        await set_config(xpath, element, client)

        logger.info(f"Successfully created {state['object_type']}: {object_name}")

        return {
            **state,
            "operation_result": {
                "status": "success",
                "name": object_name,
                "object_type": state["object_type"],
            },
        }

    except PanOSConnectionError as e:
        logger.error(f"PAN-OS connectivity error creating object: {e}")
        return {
            **state,
            "error": f"Connectivity error: {e}",
            "operation_result": {"status": "error", "message": f"Connectivity error: {e}"},
        }
    except PanOSAPIError as e:
        logger.error(f"PAN-OS API error creating object: {e}")
        return {
            **state,
            "error": f"API error: {e}",
            "operation_result": {"status": "error", "message": f"API error: {e}"},
        }
    except Exception as e:
        logger.error(f"Unexpected error creating object: {e}", exc_info=True)
        return {
            **state,
            "error": f"Unexpected error: {e}",
            "operation_result": {"status": "error", "message": f"Unexpected error: {e}"},
        }


async def read_object(state: CRUDState) -> CRUDState:
    """Read existing PAN-OS object.

    Args:
        state: Current CRUD state

    Returns:
        Updated state with operation_result
    """
    logger.debug(f"Reading {state['object_type']}: {state['object_name']}")

    if not state.get("exists"):
        return {
            **state,
            "error": f"Object {state['object_name']} does not exist",
            "operation_result": {"status": "error", "message": "Object not found"},
        }

    try:
        client = await get_panos_client()
        xpath = build_xpath(state["object_type"], name=state["object_name"])

        # Get config
        result = await get_config(xpath, client)

        # Parse XML to dict
        obj_data = parse_xml_to_dict(result)

        return {
            **state,
            "operation_result": {
                "status": "success",
                "name": state["object_name"],
                "data": obj_data,
            },
        }

    except PanOSConnectionError as e:
        logger.error(f"PAN-OS connectivity error reading object: {e}")
        return {
            **state,
            "error": f"Connectivity error: {e}",
            "operation_result": {"status": "error", "message": f"Connectivity error: {e}"},
        }
    except PanOSAPIError as e:
        logger.error(f"PAN-OS API error reading object: {e}")
        return {
            **state,
            "error": f"API error: {e}",
            "operation_result": {"status": "error", "message": f"API error: {e}"},
        }
    except Exception as e:
        logger.error(f"Unexpected error reading object: {e}", exc_info=True)
        return {
            **state,
            "error": f"Unexpected error: {e}",
            "operation_result": {"status": "error", "message": f"Unexpected error: {e}"},
        }


async def update_object(state: CRUDState) -> CRUDState:
    """Update existing PAN-OS object.

    Args:
        state: Current CRUD state

    Returns:
        Updated state with operation_result
    """
    logger.debug(f"Updating {state['object_type']}: {state['object_name']}")

    if not state.get("exists"):
        return {
            **state,
            "error": f"Object {state['object_name']} does not exist",
            "operation_result": {"status": "error", "message": "Object not found"},
        }

    try:
        client = await get_panos_client()
        xpath = build_xpath(state["object_type"], name=state["object_name"])

        # Merge name from object_name if not in data
        update_data = {**state["data"]}
        if "name" not in update_data:
            update_data["name"] = state["object_name"]

        # Build XML element with updated data
        element = build_object_xml(state["object_type"], update_data)

        # Update via edit config
        await edit_config(xpath, element, client)

        logger.info(f"Successfully updated {state['object_type']}: {state['object_name']}")

        return {
            **state,
            "operation_result": {
                "status": "success",
                "name": state["object_name"],
                "updated_fields": list(state["data"].keys()),
            },
        }

    except PanOSConnectionError as e:
        logger.error(f"PAN-OS connectivity error updating object: {e}")
        return {
            **state,
            "error": f"Connectivity error: {e}",
            "operation_result": {"status": "error", "message": f"Connectivity error: {e}"},
        }
    except PanOSAPIError as e:
        logger.error(f"PAN-OS API error updating object: {e}")
        return {
            **state,
            "error": f"API error: {e}",
            "operation_result": {"status": "error", "message": f"API error: {e}"},
        }
    except Exception as e:
        logger.error(f"Unexpected error updating object: {e}", exc_info=True)
        return {
            **state,
            "error": f"Unexpected error: {e}",
            "operation_result": {"status": "error", "message": f"Unexpected error: {e}"},
        }


async def delete_object(state: CRUDState) -> CRUDState:
    """Delete existing PAN-OS object.

    Args:
        state: Current CRUD state

    Returns:
        Updated state with operation_result
    """
    logger.debug(f"Deleting {state['object_type']}: {state['object_name']}")

    mode = state.get("mode", "strict")
    object_name = state["object_name"]

    if not state.get("exists"):
        if mode == "skip_if_missing":
            logger.info(f"Object {object_name} does not exist (skipped)")
            return {
                **state,
                "operation_result": {
                    "status": "skipped",
                    "name": object_name,
                    "object_type": state["object_type"],
                    "reason": "not_found",
                },
            }
        # Default strict mode - fail if not found
        return {
            **state,
            "error": f"Object {object_name} does not exist",
            "operation_result": {"status": "error", "message": "Object not found"},
        }

    try:
        client = await get_panos_client()
        xpath = build_xpath(state["object_type"], name=state["object_name"])

        # Delete config
        await delete_config(xpath, client)

        logger.info(f"Successfully deleted {state['object_type']}: {state['object_name']}")

        return {
            **state,
            "operation_result": {
                "status": "success",
                "name": state["object_name"],
                "deleted": True,
            },
        }

    except PanOSConnectionError as e:
        logger.error(f"PAN-OS connectivity error deleting object: {e}")
        return {
            **state,
            "error": f"Connectivity error: {e}",
            "operation_result": {"status": "error", "message": f"Connectivity error: {e}"},
        }
    except PanOSAPIError as e:
        logger.error(f"PAN-OS API error deleting object: {e}")
        return {
            **state,
            "error": f"API error: {e}",
            "operation_result": {"status": "error", "message": f"API error: {e}"},
        }
    except Exception as e:
        logger.error(f"Unexpected error deleting object: {e}", exc_info=True)
        return {
            **state,
            "error": f"Unexpected error: {e}",
            "operation_result": {"status": "error", "message": f"Unexpected error: {e}"},
        }


async def list_objects(state: CRUDState) -> CRUDState:
    """List all objects of specified type.

    Args:
        state: Current CRUD state

    Returns:
        Updated state with operation_result
    """
    logger.debug(f"Listing all {state['object_type']} objects")

    try:
        client = await get_panos_client()
        xpath = build_xpath(state["object_type"])

        # Get all objects
        result = await get_config(xpath, client)

        # Parse entries
        object_list = []
        for entry in result.findall(".//entry"):
            name = entry.get("name", "")
            if name:
                object_list.append({"name": name})

        return {
            **state,
            "operation_result": {
                "status": "success",
                "count": len(object_list),
                "objects": object_list,
            },
        }

    except PanOSConnectionError as e:
        logger.error(f"PAN-OS connectivity error listing objects: {e}")
        return {
            **state,
            "error": f"Connectivity error: {e}",
            "operation_result": {"status": "error", "message": f"Connectivity error: {e}"},
        }
    except PanOSAPIError as e:
        logger.error(f"PAN-OS API error listing objects: {e}")
        return {
            **state,
            "error": f"API error: {e}",
            "operation_result": {"status": "error", "message": f"API error: {e}"},
        }
    except Exception as e:
        logger.error(f"Unexpected error listing objects: {e}", exc_info=True)
        return {
            **state,
            "error": f"Unexpected error: {e}",
            "operation_result": {"status": "error", "message": f"Unexpected error: {e}"},
        }


async def format_response(state: CRUDState) -> CRUDState:
    """Format final response message.

    Args:
        state: Current CRUD state

    Returns:
        Updated state with message field
    """
    if state.get("error"):
        message = f"❌ Error: {state['error']}"
    elif state.get("operation_result"):
        result = state["operation_result"]
        status = result.get("status")

        if status == "success":
            if state["operation_type"] == "create":
                message = f"✅ Created {state['object_type']}: {result.get('name')}"
            elif state["operation_type"] == "read":
                message = f"✅ Retrieved {state['object_type']}: {result.get('name')}"
            elif state["operation_type"] == "update":
                message = f"✅ Updated {state['object_type']}: {result.get('name')}"
            elif state["operation_type"] == "delete":
                message = f"✅ Deleted {state['object_type']}: {result.get('name')}"
            elif state["operation_type"] == "list":
                message = f"✅ Found {result.get('count')} {state['object_type']} objects"
        elif status == "skipped":
            reason = result.get("reason")
            if reason == "already_exists":
                message = (
                    f"⏭️  Skipped {state['object_type']}: {result.get('name')} (already exists)"
                )
            elif reason == "not_found":
                message = f"⏭️  Skipped {state['object_type']}: {result.get('name')} (not found)"
            else:
                message = f"⏭️  Skipped {state['object_type']}: {result.get('name')}"
        else:
            message = f"❌ Operation failed: {result.get('message')}"
    else:
        message = "❌ Unknown error occurred"

    return {**state, "message": message}


def create_crud_subgraph() -> StateGraph:
    """Create CRUD subgraph for single object operations.

    Returns:
        Compiled StateGraph for CRUD operations
    """
    workflow = StateGraph(CRUDState)

    # Add nodes (all async now)
    workflow.add_node("validate_input", validate_input)
    workflow.add_node("check_existence", check_existence, retry=PANOS_RETRY_POLICY)
    workflow.add_node("create_object", create_object, retry=PANOS_RETRY_POLICY)
    workflow.add_node("read_object", read_object, retry=PANOS_RETRY_POLICY)
    workflow.add_node("update_object", update_object, retry=PANOS_RETRY_POLICY)
    workflow.add_node("delete_object", delete_object, retry=PANOS_RETRY_POLICY)
    workflow.add_node("list_objects", list_objects, retry=PANOS_RETRY_POLICY)
    workflow.add_node("format_response", format_response)

    # Add edges
    workflow.add_edge(START, "validate_input")
    workflow.add_edge("validate_input", "check_existence")
    workflow.add_conditional_edges(
        "check_existence",
        route_operation,
        {
            "create_object": "create_object",
            "read_object": "read_object",
            "update_object": "update_object",
            "delete_object": "delete_object",
            "list_objects": "list_objects",
            "format_response": "format_response",
        },
    )
    workflow.add_edge("create_object", "format_response")
    workflow.add_edge("read_object", "format_response")
    workflow.add_edge("update_object", "format_response")
    workflow.add_edge("delete_object", "format_response")
    workflow.add_edge("list_objects", "format_response")
    workflow.add_edge("format_response", END)

    return workflow.compile()
