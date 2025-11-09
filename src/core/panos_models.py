"""Pydantic models for PAN-OS API responses and data structures.

These models provide type-safe representations of PAN-OS objects and API responses.
"""

from enum import Enum
from typing import Any, Optional

from lxml import etree
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """PAN-OS commit job status."""

    FINISHED = "FIN"
    FAILED = "FAIL"
    PENDING = "PEND"
    ACTIVE = "ACT"


class DeviceType(str, Enum):
    """PAN-OS device type."""

    FIREWALL = "FIREWALL"
    PANORAMA = "PANORAMA"


class APIResponse(BaseModel):
    """Response from PAN-OS API call."""

    status: str = Field(description="Response status (success/error)")
    code: Optional[str] = Field(None, description="Response code")
    message: Optional[str] = Field(None, description="Response message")
    xml_element: Any = Field(None, description="Raw lxml Element (not serializable)")

    class Config:
        arbitrary_types_allowed = True


class JobStatusResponse(BaseModel):
    """PAN-OS commit job status response."""

    job_id: str = Field(description="Job ID")
    status: JobStatus = Field(description="Job status")
    progress: int = Field(description="Progress percentage (0-100)")
    result: Optional[str] = Field(None, description="Job result (if finished)")
    details: Optional[str] = Field(None, description="Error details (if failed)")


class DeviceInfo(BaseModel):
    """PAN-OS device information."""

    hostname: str = Field(description="Device hostname")
    version: str = Field(description="PAN-OS software version")
    serial: str = Field(description="Device serial number")
    model: str = Field(description="Device model")
    device_type: DeviceType = Field(description="Device type (FIREWALL or PANORAMA)")
    platform: Optional[str] = Field(None, description="Platform information")


class AddressType(str, Enum):
    """Address object types."""

    IP_NETMASK = "ip-netmask"
    IP_RANGE = "ip-range"
    FQDN = "fqdn"


class AddressObjectData(BaseModel):
    """Address object data."""

    name: str = Field(description="Object name")
    type: AddressType = Field(description="Address type")
    value: str = Field(description="Address value (IP, range, or FQDN)")
    description: Optional[str] = Field(None, description="Object description")
    tags: list[str] = Field(default_factory=list, description="Associated tags")


class ServiceProtocol(str, Enum):
    """Service protocol types."""

    TCP = "tcp"
    UDP = "udp"


class ServiceObjectData(BaseModel):
    """Service object data."""

    name: str = Field(description="Object name")
    protocol: ServiceProtocol = Field(description="Protocol")
    port: str = Field(description="Port or port range (e.g., '80', '8000-8080')")
    description: Optional[str] = Field(None, description="Object description")
    tags: list[str] = Field(default_factory=list, description="Associated tags")


class SecurityRuleAction(str, Enum):
    """Security rule actions."""

    ALLOW = "allow"
    DENY = "deny"
    DROP = "drop"
    RESET_CLIENT = "reset-client"
    RESET_SERVER = "reset-server"
    RESET_BOTH = "reset-both"


class SecurityRuleData(BaseModel):
    """Security rule data."""

    name: str = Field(description="Rule name")
    source_zones: list[str] = Field(description="Source zones")
    destination_zones: list[str] = Field(description="Destination zones")
    source_addresses: list[str] = Field(description="Source addresses")
    destination_addresses: list[str] = Field(description="Destination addresses")
    applications: list[str] = Field(description="Applications")
    services: list[str] = Field(description="Services")
    action: SecurityRuleAction = Field(description="Rule action")
    description: Optional[str] = Field(None, description="Rule description")
    tags: list[str] = Field(default_factory=list, description="Associated tags")
    disabled: bool = Field(default=False, description="Rule disabled state")
    log_start: bool = Field(default=False, description="Log at session start")
    log_end: bool = Field(default=True, description="Log at session end")


class NATRuleType(str, Enum):
    """NAT rule types."""

    IPV4 = "ipv4"
    NAT64 = "nat64"
    NPTV6 = "nptv6"


class NATRuleData(BaseModel):
    """NAT policy rule data."""

    name: str = Field(description="Rule name")
    nat_type: NATRuleType = Field(description="NAT type")
    source_zones: list[str] = Field(description="Source zones")
    destination_zone: str = Field(description="Destination zone")
    source_addresses: list[str] = Field(description="Source addresses")
    destination_addresses: list[str] = Field(description="Destination addresses")
    service: str = Field(description="Service")
    source_translation_type: Optional[str] = Field(None, description="Source NAT type")
    source_translation_address: Optional[str] = Field(None, description="Source NAT address")
    destination_translation_address: Optional[str] = Field(
        None, description="Destination NAT address"
    )
    destination_translation_port: Optional[int] = Field(None, description="Destination NAT port")
    description: Optional[str] = Field(None, description="Rule description")
    tags: list[str] = Field(default_factory=list, description="Associated tags")
    disabled: bool = Field(default=False, description="Rule disabled state")


class AddressGroupData(BaseModel):
    """Address group data."""

    name: str = Field(description="Group name")
    static_members: list[str] = Field(
        default_factory=list, description="Static address object members"
    )
    dynamic_filter: Optional[str] = Field(None, description="Dynamic filter expression")
    description: Optional[str] = Field(None, description="Group description")
    tags: list[str] = Field(default_factory=list, description="Associated tags")


class ServiceGroupData(BaseModel):
    """Service group data."""

    name: str = Field(description="Group name")
    members: list[str] = Field(description="Service object members")
    description: Optional[str] = Field(None, description="Group description")
    tags: list[str] = Field(default_factory=list, description="Associated tags")


def parse_xml_to_dict(element: etree._Element) -> dict[str, Any]:
    """Parse XML element to dictionary.

    Args:
        element: lxml Element to parse

    Returns:
        Dictionary representation of XML
    """
    result: dict[str, Any] = {}

    # Add attributes
    if element.attrib:
        result.update(element.attrib)

    # Add text content
    if element.text and element.text.strip():
        if len(element) == 0:  # Leaf node
            return element.text.strip()
        result["_text"] = element.text.strip()

    # Add child elements
    for child in element:
        child_data = parse_xml_to_dict(child)
        if child.tag in result:
            # Multiple elements with same tag - convert to list
            if not isinstance(result[child.tag], list):
                result[child.tag] = [result[child.tag]]
            result[child.tag].append(child_data)
        else:
            result[child.tag] = child_data

    return result
