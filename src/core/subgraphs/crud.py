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


async def _get_existing_config(state: CRUDState) -> dict:
    """Fetch existing config from cache or firewall.

    Args:
        state: Current CRUD state

    Returns:
        Dictionary representation of existing config

    Raises:
        PanOSAPIError: If config retrieval fails
    """
    from src.core.config import get_settings
    from src.core.memory_store import get_cached_config

    settings = get_settings()
    store = state.get("store")
    object_name = state.get("object_name") or state.get("data", {}).get("name")
    device_context = state.get("device_context")

    xpath = build_xpath(state["object_type"], name=object_name, device_context=device_context)

    # Try cache first if enabled and store available
    if settings.cache_enabled and store:
        cached_xml = get_cached_config(settings.panos_hostname, xpath, store)
        if cached_xml:
            logger.debug(f"Using cached config for diff comparison: {object_name}")
            root = etree.fromstring(cached_xml)
            return parse_xml_to_dict(root)

    # Fetch from firewall
    logger.debug(f"Fetching config from firewall for diff comparison: {object_name}")
    client = await get_panos_client()
    result = await get_config(xpath, client)

    if result is None:
        return {}

    return parse_xml_to_dict(result)


def _format_skip_details(config: dict, object_type: str) -> dict:
    """Format existing config details for skip message.

    Args:
        config: Configuration dictionary
        object_type: Type of object (address, service, etc.)

    Returns:
        Dictionary of formatted details
    """
    details = {
        "name": config.get("name", "unknown"),
        "type": object_type,
    }

    # Address object details
    if "ip-netmask" in config:
        details["ip"] = config["ip-netmask"]
    elif "ip-range" in config:
        details["ip_range"] = config["ip-range"]
    elif "fqdn" in config:
        details["fqdn"] = config["fqdn"]

    # Service object details
    if "protocol" in config:
        protocol = config["protocol"]
        if isinstance(protocol, dict):
            # Extract protocol type and port
            for proto_type in ["tcp", "udp"]:
                if proto_type in protocol:
                    port_info = protocol[proto_type]
                    if isinstance(port_info, dict) and "port" in port_info:
                        details["protocol"] = f"{proto_type}/{port_info['port']}"

    # Common fields
    if "description" in config:
        details["description"] = config["description"]

    # Tags
    if "tag" in config:
        tag_data = config["tag"]
        if isinstance(tag_data, dict) and "member" in tag_data:
            members = tag_data["member"]
            if isinstance(members, list):
                details["tags"] = ", ".join(members)
            else:
                details["tags"] = members
        elif isinstance(tag_data, list):
            details["tags"] = ", ".join(tag_data)

    return details


def _format_skip_message(name: str, config: dict, object_type: str, reason: str) -> str:
    """Format user-friendly skip message with details.

    Args:
        name: Object name
        config: Configuration dictionary
        object_type: Type of object
        reason: Reason for skipping (unchanged, already_exists, etc.)

    Returns:
        Formatted skip message string
    """
    details = _format_skip_details(config, object_type)

    # Map reason to user-friendly text
    reason_text = {
        "unchanged": "Object unchanged, no update needed",
        "already_exists": "Object already exists with same configuration",
        "not_found": "Object not found",
    }.get(reason, reason)

    msg = f"⏭️  Skipped: {object_type} '{name}' already exists\n"
    msg += f"   Reason: {reason_text}\n"
    msg += "   Current config:\n"

    for key, value in details.items():
        if key in ["name", "type"]:
            continue
        msg += f"     {key}: {value}\n"

    return msg.rstrip()


def _format_diff_message(name: str, object_type: str, diff) -> str:
    """Format diff message for update approval.

    Args:
        name: Object name
        object_type: Type of object
        diff: ConfigDiff object

    Returns:
        Formatted diff message string
    """
    msg = f"\n🔍 Update Detected for {object_type} '{name}'\n\n"
    msg += "Changes:\n"

    for change in diff.changes:
        if change.change_type == "modified":
            msg += f"  • {change.field}: {change.old_value} → {change.new_value}\n"
        elif change.change_type == "added":
            msg += f"  + {change.field}: {change.new_value}\n"
        elif change.change_type == "removed":
            msg += f"  - {change.field}: {change.old_value}\n"

    return msg


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
    """Check if object exists on firewall (with caching).

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
        from src.core.config import get_settings
        from src.core.memory_store import cache_config, get_cached_config

        client = await get_panos_client()
        settings = get_settings()
        device_context = state.get("device_context")
        xpath = build_xpath(
            state["object_type"], name=state["object_name"], device_context=device_context
        )

        # Check cache first if enabled and store available
        store = state.get("store")
        if settings.cache_enabled and store:
            cached_xml = get_cached_config(settings.panos_hostname, xpath, store)

            if cached_xml:
                logger.debug(f"Cache HIT for existence check: {state['object_name']}")
                # Parse cached XML to check existence
                exists = cached_xml and len(cached_xml.strip()) > 0
                return {**state, "exists": exists}

        # Cache MISS: Fetch from firewall
        logger.debug(f"Cache MISS for existence check: {state['object_name']}")
        try:
            result = await get_config(xpath, client)
            exists = result is not None and len(result) > 0

            # Cache the result if caching enabled and store available
            if settings.cache_enabled and store and result is not None:
                xml_str = etree.tostring(result, encoding="unicode")
                cache_config(
                    settings.panos_hostname,
                    xpath,
                    xml_str,
                    store,
                    ttl=settings.cache_ttl_seconds,
                )

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
    """Create new PAN-OS object with diff detection.

    Args:
        state: Current CRUD state

    Returns:
        Updated state with operation_result
    """
    mode = state.get("mode", "skip_if_exists")  # Changed default to skip_if_exists for idempotency
    object_name = state["data"].get("name")

    # Check if already exists (idempotent behavior with diff detection)
    if state.get("exists"):
        if mode == "skip_if_exists":
            try:
                # Fetch existing config for comparison
                existing_config = await _get_existing_config(state)

                # Compare desired vs actual
                from src.core.diff_engine import compare_configs

                diff = compare_configs(state["data"], existing_config)

                if diff.is_identical():
                    # Unchanged - skip with detailed message
                    skip_message = _format_skip_message(
                        object_name, existing_config, state["object_type"], "unchanged"
                    )
                    logger.info(f"⏭️  Object {object_name} already exists and unchanged (skipped)")
                    return {
                        **state,
                        "operation_result": {
                            "status": "skipped",
                            "name": object_name,
                            "object_type": state["object_type"],
                            "reason": "unchanged",
                            "details": _format_skip_details(existing_config, state["object_type"]),
                        },
                        "message": skip_message,
                    }
                else:
                    # Changed - show diff (for now, just skip with diff info)
                    # TODO: In future phase, add approval gate here
                    diff_summary = diff.summary()
                    logger.info(
                        f"⚠️  Object {object_name} exists with different config:\n{diff_summary}"
                    )
                    return {
                        **state,
                        "operation_result": {
                            "status": "skipped",
                            "name": object_name,
                            "object_type": state["object_type"],
                            "reason": "exists_with_changes",
                            "diff": diff.to_dict(),
                        },
                        "message": f"⏭️  Skipped: {state['object_type']} '{object_name}' exists with different config\n{diff_summary}",
                    }
            except Exception as e:
                # If diff comparison fails, fall back to simple skip
                logger.warning(f"Diff comparison failed, falling back to simple skip: {e}")
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
        from src.core.config import get_settings
        from src.core.memory_store import invalidate_cache

        client = await get_panos_client()
        settings = get_settings()
        device_context = state.get("device_context")
        xpath = build_xpath(state["object_type"], device_context=device_context)

        # Build XML element
        element = build_object_xml(state["object_type"], state["data"])

        # Create via set config
        await set_config(xpath, element, client)

        logger.info(f"Successfully created {state['object_type']}: {object_name}")

        # Invalidate cache after successful create
        store = state.get("store")
        if settings.cache_enabled and store:
            # Build xpath for the specific object
            object_xpath = build_xpath(
                state["object_type"], name=object_name, device_context=device_context
            )
            invalidate_cache(settings.panos_hostname, object_xpath, store)
            logger.debug(f"Cache invalidated after create: {object_name}")

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
    """Read existing PAN-OS object (with caching).

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
        from src.core.config import get_settings
        from src.core.memory_store import cache_config, get_cached_config

        client = await get_panos_client()
        settings = get_settings()
        device_context = state.get("device_context")
        xpath = build_xpath(
            state["object_type"], name=state["object_name"], device_context=device_context
        )

        # Check cache first if enabled and store available
        store = state.get("store")
        if settings.cache_enabled and store:
            cached_xml = get_cached_config(settings.panos_hostname, xpath, store)

            if cached_xml:
                logger.debug(f"Cache HIT for read: {state['object_name']}")
                # Parse cached XML and return
                root = etree.fromstring(cached_xml)
                obj_data = parse_xml_to_dict(root)
                return {
                    **state,
                    "operation_result": {
                        "status": "success",
                        "name": state["object_name"],
                        "data": obj_data,
                    },
                }

        # Cache MISS: Fetch from firewall
        logger.debug(f"Cache MISS for read: {state['object_name']}")
        result = await get_config(xpath, client)

        # Cache the result if caching enabled and store available
        if settings.cache_enabled and store and result is not None:
            xml_str = etree.tostring(result, encoding="unicode")
            cache_config(
                settings.panos_hostname,
                xpath,
                xml_str,
                store,
                ttl=settings.cache_ttl_seconds,
            )

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
    """Update existing PAN-OS object with diff detection (invalidates cache).

    Args:
        state: Current CRUD state

    Returns:
        Updated state with operation_result
    """
    object_name = state["object_name"]
    logger.debug(f"Updating {state['object_type']}: {object_name}")

    if not state.get("exists"):
        return {
            **state,
            "error": f"Object {object_name} does not exist",
            "operation_result": {"status": "error", "message": "Object not found"},
        }

    try:
        from src.core.config import get_settings
        from src.core.memory_store import invalidate_cache

        # Merge name from object_name if not in data
        update_data = {**state["data"]}
        if "name" not in update_data:
            update_data["name"] = object_name

        # Fetch existing config and compare
        existing_config = await _get_existing_config(state)

        from src.core.diff_engine import compare_configs

        diff = compare_configs(update_data, existing_config)

        # Skip if no changes detected
        if diff.is_identical():
            logger.info(f"⏭️  No changes detected for {object_name}, skipping update")
            return {
                **state,
                "operation_result": {
                    "status": "skipped",
                    "name": object_name,
                    "object_type": state["object_type"],
                    "reason": "unchanged",
                    "message": "Configuration identical, no update needed",
                },
                "message": f"⏭️  Skipped: {state['object_type']} '{object_name}' (unchanged)",
            }

        # Changes detected - log diff and proceed with update
        logger.info(f"✏️  Changes detected for {object_name}:")
        logger.info(diff.summary())

        client = await get_panos_client()
        settings = get_settings()
        device_context = state.get("device_context")
        xpath = build_xpath(state["object_type"], name=object_name, device_context=device_context)

        # Build XML element with updated data
        element = build_object_xml(state["object_type"], update_data)

        # Update via edit config
        await edit_config(xpath, element, client)

        logger.info(f"Successfully updated {state['object_type']}: {object_name}")

        # Invalidate cache after successful update
        store = state.get("store")
        if settings.cache_enabled and store:
            invalidate_cache(settings.panos_hostname, xpath, store)
            logger.debug(f"Cache invalidated after update: {object_name}")

        return {
            **state,
            "operation_result": {
                "status": "success",
                "name": object_name,
                "updated_fields": list(state["data"].keys()),
                "diff": diff.to_dict(),
                "message": f"Successfully updated {state['object_type']} '{object_name}'",
            },
            "message": f"✅ Updated: {state['object_type']} '{object_name}'\n{diff.summary()}",
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
    """Delete existing PAN-OS object (invalidates cache).

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
        from src.core.config import get_settings
        from src.core.memory_store import invalidate_cache

        client = await get_panos_client()
        settings = get_settings()
        device_context = state.get("device_context")
        xpath = build_xpath(
            state["object_type"], name=state["object_name"], device_context=device_context
        )

        # Delete config
        await delete_config(xpath, client)

        logger.info(f"Successfully deleted {state['object_type']}: {state['object_name']}")

        # Invalidate cache after successful delete
        store = state.get("store")
        if settings.cache_enabled and store:
            invalidate_cache(settings.panos_hostname, xpath, store)
            logger.debug(f"Cache invalidated after delete: {state['object_name']}")

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
        device_context = state.get("device_context")
        xpath = build_xpath(state["object_type"], device_context=device_context)

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
    """Format final response message with enhanced skip details.

    Args:
        state: Current CRUD state

    Returns:
        Updated state with message field
    """
    # If message already set (e.g., from create/update with diff), use it
    if state.get("message") and not state.get("error"):
        return state

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
                # Check if diff available
                if result.get("diff"):
                    change_count = len(result["diff"].get("changes", []))
                    message = f"✅ Updated {state['object_type']}: {result.get('name')} ({change_count} changes)"
                else:
                    message = f"✅ Updated {state['object_type']}: {result.get('name')}"
            elif state["operation_type"] == "delete":
                message = f"✅ Deleted {state['object_type']}: {result.get('name')}"
            elif state["operation_type"] == "list":
                message = f"✅ Found {result.get('count')} {state['object_type']} objects"
        elif status == "skipped":
            reason = result.get("reason")
            if reason == "unchanged":
                message = (
                    f"⏭️  Skipped {state['object_type']}: {result.get('name')} "
                    f"(unchanged - identical configuration)"
                )
            elif reason == "already_exists":
                message = (
                    f"⏭️  Skipped {state['object_type']}: {result.get('name')} (already exists)"
                )
            elif reason == "exists_with_changes":
                message = (
                    f"⏭️  Skipped {state['object_type']}: {result.get('name')} "
                    f"(exists with different config)"
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
