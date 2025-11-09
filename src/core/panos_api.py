"""Async XML API layer for PAN-OS interactions.

This module provides functional async operations for interacting with the PAN-OS XML API
using httpx for HTTP operations and lxml for XML parsing/generation.
"""

import logging
from typing import Optional

import httpx
from lxml import etree

from src.core.panos_models import APIResponse, JobStatus, JobStatusResponse

logger = logging.getLogger(__name__)


# Custom exceptions
class PanOSAPIError(Exception):
    """PAN-OS API error."""

    def __init__(self, message: str, code: Optional[str] = None, response: Optional[str] = None):
        super().__init__(message)
        self.code = code
        self.response = response


class PanOSConnectionError(Exception):
    """PAN-OS connection error."""

    pass


class PanOSValidationError(Exception):
    """PAN-OS XML validation error."""

    pass


def build_xpath(
    object_type: str,
    name: Optional[str] = None,
    location: str = "vsys1",
    rule_base: Optional[str] = None,
) -> str:
    """Build XPath for PAN-OS configuration objects.

    Args:
        object_type: Type of object (address, service, security-policy, etc.)
        name: Optional specific object name
        location: Virtual system location (default: vsys1)
        rule_base: For policies, the rulebase type (security, nat, etc.)

    Returns:
        XPath string
    """
    base_paths = {
        "address": f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{location}']/address",
        "address-group": f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{location}']/address-group",
        "service": f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{location}']/service",
        "service-group": f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{location}']/service-group",
        "tag": f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{location}']/tag",
    }

    # Policy rules have different paths
    if object_type in ["security-policy", "nat-policy"]:
        policy_type = "security" if object_type == "security-policy" else "nat"
        base = f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{location}']/rulebase/{policy_type}/rules"
        if name:
            return f"{base}/entry[@name='{name}']"
        return base

    if object_type in base_paths:
        base = base_paths[object_type]
        if name:
            return f"{base}/entry[@name='{name}']"
        return base

    raise ValueError(f"Unknown object_type: {object_type}")


def build_xml_element(
    tag: str, attributes: Optional[dict[str, str]] = None, children: Optional[list] = None
) -> etree._Element:
    """Build an XML element with attributes and children.

    Args:
        tag: XML tag name
        attributes: Optional dictionary of attributes
        children: Optional list of child elements or (tag, text) tuples

    Returns:
        lxml Element
    """
    element = etree.Element(tag, attrib=attributes or {})

    if children:
        for child in children:
            if isinstance(child, etree._Element):
                element.append(child)
            elif isinstance(child, tuple) and len(child) == 2:
                # (tag, text) tuple
                sub_elem = etree.SubElement(element, child[0])
                sub_elem.text = child[1]
            else:
                raise ValueError(f"Invalid child type: {type(child)}")

    return element


def build_object_xml(object_type: str, data: dict) -> str:
    """Build XML for PAN-OS object using validated structure definitions.

    Args:
        object_type: Type of object (address, service, etc.)
        data: Object data dictionary

    Returns:
        XML string ready for API submission

    Example:
        >>> xml = build_object_xml("address", {
        ...     "name": "web-server",
        ...     "ip-netmask": "10.0.0.1",
        ...     "description": "Web server",
        ...     "tag": ["Web", "Production"]
        ... })
    """
    from src.core.panos_xpath_map import PanOSXPathMap

    # Get structure definition
    normalized_type = object_type.replace("-", "_")
    structure = PanOSXPathMap.get_structure(normalized_type)

    if not structure:
        raise PanOSValidationError(f"No structure definition for {object_type}")

    # Create root entry element with name attribute
    name = data.get("name", "")
    entry = etree.Element("entry", attrib={"name": name})

    # Build XML based on structure and data
    for key, value in data.items():
        if key == "name":
            continue  # Already set as attribute

        # Normalize field names (replace underscores with hyphens for XML)
        xml_key = key.replace("_", "-")

        if value is None:
            continue

        # Handle list values (members)
        if isinstance(value, list):
            # Create container and member elements
            if "member" in str(structure.get("fields", {}).get(key, "")):
                # Determine container tag (e.g., "tag", "static", "from")
                container_tag = xml_key
                container = etree.SubElement(entry, container_tag)
                for item in value:
                    member = etree.SubElement(container, "member")
                    member.text = str(item)
            else:
                # Multiple instances of same tag
                for item in value:
                    elem = etree.SubElement(entry, xml_key)
                    elem.text = str(item)

        # Handle dict values (nested structures)
        elif isinstance(value, dict):
            parent = etree.SubElement(entry, xml_key)
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, list):
                    for item in sub_value:
                        member = etree.SubElement(parent, "member")
                        member.text = str(item)
                else:
                    sub_elem = etree.SubElement(parent, sub_key.replace("_", "-"))
                    sub_elem.text = str(sub_value)

        # Handle simple values
        else:
            elem = etree.SubElement(entry, xml_key)
            elem.text = str(value)

    # Convert to string
    xml_str = etree.tostring(entry, encoding="unicode", pretty_print=True)
    return xml_str


async def api_request(
    method: str,
    params: dict[str, str],
    client: httpx.AsyncClient,
    xml_data: Optional[str] = None,
) -> APIResponse:
    """Execute PAN-OS API request.

    Args:
        method: HTTP method (GET or POST)
        params: Query parameters (including type, action, xpath, etc.)
        client: httpx AsyncClient instance
        xml_data: Optional XML data for element parameter

    Returns:
        APIResponse with parsed response

    Raises:
        PanOSConnectionError: If connection fails
        PanOSAPIError: If API returns error
    """
    try:
        logger.debug(f"API request: method={method}, params={params}")

        if method.upper() == "GET":
            response = await client.get("/api/", params=params)
        elif method.upper() == "POST":
            if xml_data:
                params["element"] = xml_data
            response = await client.post("/api/", params=params)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()

        # Parse XML response
        root = etree.fromstring(response.content)
        status = root.get("status", "")
        code = root.get("code", "")

        logger.debug(f"API response: status={status}, code={code}")

        # Check for errors
        if status != "success":
            msg_elem = root.find(".//msg")
            message = msg_elem.text if msg_elem is not None else "Unknown error"
            raise PanOSAPIError(message, code=code, response=response.text)

        # Extract message if present
        msg_elem = root.find(".//msg")
        message = msg_elem.text if msg_elem is not None else None

        return APIResponse(status=status, code=code, message=message, xml_element=root)

    except httpx.HTTPError as e:
        logger.error(f"HTTP error: {e}")
        raise PanOSConnectionError(f"Connection failed: {e}") from e
    except etree.XMLSyntaxError as e:
        logger.error(f"XML parsing error: {e}")
        raise PanOSAPIError(f"Invalid XML response: {e}") from e


async def get_config(xpath: str, client: httpx.AsyncClient) -> etree._Element:
    """Get configuration at specified XPath.

    Args:
        xpath: XPath to configuration element
        client: httpx AsyncClient instance

    Returns:
        lxml Element with configuration

    Raises:
        PanOSAPIError: If configuration retrieval fails
    """
    params = {"type": "config", "action": "get", "xpath": xpath}

    response = await api_request("GET", params, client)

    # Extract result element
    result = response.xml_element.find(".//result")
    if result is None:
        raise PanOSAPIError("No result in response")

    return result


async def set_config(xpath: str, element: etree._Element, client: httpx.AsyncClient) -> APIResponse:
    """Set configuration at specified XPath (create new).

    Args:
        xpath: XPath to configuration location
        element: XML element to create
        client: httpx AsyncClient instance

    Returns:
        APIResponse

    Raises:
        PanOSAPIError: If set operation fails
    """
    xml_str = etree.tostring(element, encoding="unicode")
    params = {"type": "config", "action": "set", "xpath": xpath}

    logger.debug(f"Setting config at {xpath}")
    return await api_request("POST", params, client, xml_data=xml_str)


async def edit_config(
    xpath: str, element: etree._Element, client: httpx.AsyncClient
) -> APIResponse:
    """Edit configuration at specified XPath (update existing).

    Args:
        xpath: XPath to configuration element
        element: XML element to update
        client: httpx AsyncClient instance

    Returns:
        APIResponse

    Raises:
        PanOSAPIError: If edit operation fails
    """
    xml_str = etree.tostring(element, encoding="unicode")
    params = {"type": "config", "action": "edit", "xpath": xpath}

    logger.debug(f"Editing config at {xpath}")
    return await api_request("POST", params, client, xml_data=xml_str)


async def delete_config(xpath: str, client: httpx.AsyncClient) -> APIResponse:
    """Delete configuration at specified XPath.

    Args:
        xpath: XPath to configuration element
        client: httpx AsyncClient instance

    Returns:
        APIResponse

    Raises:
        PanOSAPIError: If delete operation fails
    """
    params = {"type": "config", "action": "delete", "xpath": xpath}

    logger.debug(f"Deleting config at {xpath}")
    return await api_request("GET", params, client)


async def commit(
    description: Optional[str], client: httpx.AsyncClient, partial: bool = False
) -> str:
    """Commit configuration changes.

    Args:
        description: Optional commit description
        client: httpx AsyncClient instance
        partial: Whether to do a partial commit (admin-only changes)

    Returns:
        Job ID for tracking commit status

    Raises:
        PanOSAPIError: If commit initiation fails
    """
    # Build commit command XML
    cmd = "<commit>"
    if description:
        cmd += f"<description>{description}</description>"
    if partial:
        cmd += "<partial><admin><member>admin</member></admin></partial>"
    cmd += "</commit>"

    params = {"type": "commit", "cmd": cmd}

    logger.info(f"Initiating commit: {description or 'No description'}")
    response = await api_request("GET", params, client)

    # Extract job ID
    job_elem = response.xml_element.find(".//job")
    if job_elem is None:
        raise PanOSAPIError("No job ID in commit response")

    job_id = job_elem.text
    logger.info(f"Commit job started: {job_id}")
    return job_id


async def get_job_status(job_id: str, client: httpx.AsyncClient) -> JobStatusResponse:
    """Get status of a commit job.

    Args:
        job_id: Job ID from commit operation
        client: httpx AsyncClient instance

    Returns:
        JobStatusResponse with current status

    Raises:
        PanOSAPIError: If status check fails
    """
    cmd = f"<show><jobs><id>{job_id}</id></jobs></show>"
    params = {"type": "op", "cmd": cmd}

    response = await api_request("GET", params, client)

    # Parse job status
    job_elem = response.xml_element.find(".//job")
    if job_elem is None:
        raise PanOSAPIError(f"No job info for job ID: {job_id}")

    status_elem = job_elem.find("status")
    progress_elem = job_elem.find("progress")
    result_elem = job_elem.find("result")
    details_elem = job_elem.find("details")

    status_str = status_elem.text if status_elem is not None else "PEND"
    progress = int(progress_elem.text) if progress_elem is not None else 0
    result = result_elem.text if result_elem is not None else None
    details = None

    # Extract details for failed jobs
    if status_str == "FAIL" and details_elem is not None:
        # Get all line elements
        lines = details_elem.findall(".//line")
        if lines:
            details = "\n".join(line.text for line in lines if line.text)

    return JobStatusResponse(
        job_id=job_id,
        status=JobStatus(status_str),
        progress=progress,
        result=result,
        details=details,
    )


async def validate_config(client: httpx.AsyncClient) -> APIResponse:
    """Validate current configuration.

    Args:
        client: httpx AsyncClient instance

    Returns:
        APIResponse with validation result

    Raises:
        PanOSAPIError: If validation fails
    """
    cmd = "<validate><full></full></validate>"
    params = {"type": "op", "cmd": cmd}

    logger.info("Validating configuration")
    return await api_request("GET", params, client)


async def operational_command(cmd: str, client: httpx.AsyncClient) -> etree._Element:
    """Execute operational command.

    Args:
        cmd: Operational command XML
        client: httpx AsyncClient instance

    Returns:
        lxml Element with command output

    Raises:
        PanOSAPIError: If command execution fails
    """
    params = {"type": "op", "cmd": cmd}

    logger.debug(f"Executing op command: {cmd}")
    response = await api_request("GET", params, client)

    # Return full response element for parsing by caller
    return response.xml_element
