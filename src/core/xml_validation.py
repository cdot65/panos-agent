"""Pre-submission XML validation for PAN-OS objects.

This module provides validation for PAN-OS configuration objects before they are
sent to the firewall. It catches common errors early to provide clear feedback.
"""

import ipaddress
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from lxml import etree


@dataclass
class ValidationResult:
    """Result of a validation operation.

    Attributes:
        is_valid: Whether the validation passed
        errors: List of error messages
        warnings: List of warning messages
    """

    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add an error message and mark validation as failed."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def merge(self, other: "ValidationResult") -> None:
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False


# Field Validators
def validate_ip_cidr(value: str) -> Tuple[bool, Optional[str]]:
    """Validate IP address with CIDR notation.

    Args:
        value: String like "10.0.0.0/24" or "192.168.1.1/32"

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        ipaddress.ip_network(value, strict=False)
        return True, None
    except ValueError as e:
        return False, f"Invalid IP CIDR format: {value} ({e})"


def validate_ip_range(value: str) -> Tuple[bool, Optional[str]]:
    """Validate IP address range.

    Args:
        value: String like "10.0.0.1-10.0.0.100"

    Returns:
        Tuple of (is_valid, error_message)
    """
    if "-" not in value:
        return False, f"IP range must contain '-': {value}"

    parts = value.split("-")
    if len(parts) != 2:
        return False, f"IP range must have exactly two IPs: {value}"

    try:
        start = ipaddress.ip_address(parts[0].strip())
        end = ipaddress.ip_address(parts[1].strip())
        if start >= end:
            return False, f"Start IP must be less than end IP: {value}"
        return True, None
    except ValueError as e:
        return False, f"Invalid IP in range: {value} ({e})"


def validate_fqdn(value: str) -> Tuple[bool, Optional[str]]:
    """Validate Fully Qualified Domain Name.

    Args:
        value: Domain name like "example.com"

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Basic FQDN regex - allows wildcards for PAN-OS
    # Domain labels can't start or end with hyphen
    fqdn_pattern = r"^(\*\.)?([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$"
    if not re.match(fqdn_pattern, value):
        return False, f"Invalid FQDN format: {value}"
    return True, None


def validate_port_range(value: str) -> Tuple[bool, Optional[str]]:
    """Validate port or port range.

    Args:
        value: Port like "80" or range like "8080-8090"

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Handle comma-separated ports FIRST (before checking for dash)
    if "," in value:
        ports = value.split(",")
        for port_str in ports:
            port_str = port_str.strip()
            # Recursive call for each port/range
            is_valid, error = validate_port_range(port_str)
            if not is_valid:
                return False, error
        return True, None

    # Handle port range (dash but no comma)
    if "-" in value:
        parts = value.split("-")
        if len(parts) != 2:
            return False, f"Port range must have exactly two ports: {value}"
        try:
            start = int(parts[0].strip())
            end = int(parts[1].strip())
            if not (1 <= start <= 65535) or not (1 <= end <= 65535):
                return False, f"Ports must be 1-65535: {value}"
            if start >= end:
                return False, f"Start port must be less than end port: {value}"
            return True, None
        except ValueError:
            return False, f"Invalid port numbers in range: {value}"

    # Handle single port (no dash, no comma)
    try:
        port = int(value)
        if 1 <= port <= 65535:
            return True, None
        return False, f"Port must be 1-65535: {value}"
    except ValueError:
        return False, f"Invalid port number: {value}"


def validate_protocol(value: str) -> Tuple[bool, Optional[str]]:
    """Validate protocol value.

    Args:
        value: Protocol like "tcp", "udp"

    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_protocols = ["tcp", "udp", "icmp"]
    if value.lower() in valid_protocols:
        return True, None
    return False, f"Protocol must be one of {valid_protocols}: {value}"


def validate_action(value: str) -> Tuple[bool, Optional[str]]:
    """Validate security policy action.

    Args:
        value: Action like "allow", "deny", "drop", "reset-client", "reset-server", "reset-both"

    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_actions = ["allow", "deny", "drop", "reset-client", "reset-server", "reset-both"]
    if value.lower() in valid_actions:
        return True, None
    return False, f"Action must be one of {valid_actions}: {value}"


def validate_yes_no(value: str) -> Tuple[bool, Optional[str]]:
    """Validate yes/no field.

    Args:
        value: "yes" or "no"

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value.lower() in ["yes", "no"]:
        return True, None
    return False, f"Value must be 'yes' or 'no': {value}"


# Validation Rules Definition
VALIDATION_RULES: Dict[str, Dict[str, Any]] = {
    "address": {
        "required_fields": ["name"],
        "required_one_of": [["ip-netmask", "ip-range", "fqdn", "ip_netmask", "ip_range"]],
        "field_types": {
            "name": str,
            "description": str,
            "tag": list,
        },
        "validators": {
            "ip-netmask": validate_ip_cidr,
            "ip_netmask": validate_ip_cidr,
            "ip-range": validate_ip_range,
            "ip_range": validate_ip_range,
            "fqdn": validate_fqdn,
        },
    },
    "address_group": {
        "required_fields": ["name"],
        "required_one_of": [["static", "dynamic"]],
        "field_types": {
            "name": str,
            "description": str,
            "static": list,
            "dynamic": (str, dict),
            "tag": list,
        },
        "validators": {},
    },
    "service": {
        "required_fields": ["name", "protocol"],
        "field_types": {
            "name": str,
            "description": str,
            "protocol": (str, dict),
            "tag": list,
        },
        "validators": {
            "tcp_port": validate_port_range,
            "udp_port": validate_port_range,
        },
    },
    "service_group": {
        "required_fields": ["name", "members"],
        "field_types": {
            "name": str,
            "members": list,
            "tag": list,
        },
        "validators": {},
    },
    "security_policy": {
        "required_fields": [
            "name",
            "from",
            "to",
            "source",
            "destination",
            "service",
            "application",
            "action",
        ],
        "field_types": {
            "name": str,
            "from": list,
            "to": list,
            "source": list,
            "destination": list,
            "service": list,
            "application": list,
            "action": str,
            "description": str,
            "tag": list,
            "log-end": str,
            "log_end": str,
            "disabled": str,
        },
        "validators": {
            "action": validate_action,
            "log-end": validate_yes_no,
            "log_end": validate_yes_no,
            "disabled": validate_yes_no,
        },
    },
    "nat_policy": {
        "required_fields": ["name", "from", "to", "source", "destination"],
        "field_types": {
            "name": str,
            "from": list,
            "to": list,
            "source": list,
            "destination": list,
            "service": str,
            "nat-type": str,
            "nat_type": str,
            "description": str,
            "tag": list,
            "disabled": str,
        },
        "validators": {
            "disabled": validate_yes_no,
        },
    },
}


def validate_object_structure(object_type: str, data: dict) -> ValidationResult:
    """Validate object structure before building XML.

    This performs pre-submission validation to catch errors before sending
    configuration to the firewall.

    Args:
        object_type: Type of object (address, service, security_policy, etc.)
        data: Dictionary containing object configuration

    Returns:
        ValidationResult with validation status and any errors/warnings

    Example:
        >>> result = validate_object_structure("address", {
        ...     "name": "web-server",
        ...     "ip-netmask": "10.0.0.1/32"
        ... })
        >>> assert result.is_valid
    """
    result = ValidationResult()

    # Normalize object type (replace hyphens with underscores)
    normalized_type = object_type.replace("-", "_")

    # Check if we have validation rules for this type
    if normalized_type not in VALIDATION_RULES:
        result.add_warning(f"No validation rules defined for object type: {object_type}")
        return result

    rules = VALIDATION_RULES[normalized_type]

    # Validate required fields
    required_fields = rules.get("required_fields", [])
    for required_field in required_fields:
        # Handle both hyphen and underscore versions
        field_underscore = required_field.replace("-", "_")
        field_hyphen = required_field.replace("_", "-")
        if required_field not in data and field_underscore not in data and field_hyphen not in data:
            result.add_error(f"Missing required field: {required_field}")

    # Validate "required one of" groups
    required_one_of = rules.get("required_one_of", [])
    for field_group in required_one_of:
        found = False
        for required_field in field_group:
            if required_field in data and data[required_field]:
                found = True
                break
        if not found:
            result.add_error(f"Must specify one of: {', '.join(field_group)}")

    # Validate field types
    field_types = rules.get("field_types", {})
    for field_name, expected_type in field_types.items():
        # Check both hyphen and underscore versions
        field_underscore = field_name.replace("-", "_")
        field_hyphen = field_name.replace("_", "-")

        value = data.get(field_name) or data.get(field_underscore) or data.get(field_hyphen)
        if value is not None:
            # Handle tuple of types
            if isinstance(expected_type, tuple):
                if not isinstance(value, expected_type):
                    type_names = " or ".join(t.__name__ for t in expected_type)
                    result.add_error(
                        f"Field '{field_name}' must be {type_names}, got {type(value).__name__}"
                    )
            else:
                if not isinstance(value, expected_type):
                    result.add_error(
                        f"Field '{field_name}' must be {expected_type.__name__}, got {type(value).__name__}"
                    )

    # Run field-specific validators
    validators = rules.get("validators", {})
    for field_name, validator_func in validators.items():
        # Check both hyphen and underscore versions
        field_underscore = field_name.replace("-", "_")
        field_hyphen = field_name.replace("_", "-")

        value = data.get(field_name) or data.get(field_underscore) or data.get(field_hyphen)
        if value is not None:
            # For protocol with dict (service objects), validate nested structure
            if field_name in ["protocol"] and isinstance(value, dict):
                for proto_key, proto_value in value.items():
                    if proto_key in ["tcp", "udp"]:
                        # Validate ports within protocol dict
                        if isinstance(proto_value, dict) and "port" in proto_value:
                            is_valid, error = validate_port_range(str(proto_value["port"]))
                            if not is_valid:
                                result.add_error(error)
            elif isinstance(value, str):
                is_valid, error = validator_func(value)
                if not is_valid:
                    result.add_error(error)

    # Additional validation: check for empty name
    if "name" in data and not data["name"]:
        result.add_error("Object name cannot be empty")

    # Additional validation: check list fields are not empty
    for field_name, value in data.items():
        if isinstance(value, list) and len(value) == 0:
            result.add_warning(f"Field '{field_name}' is an empty list")

    return result


def validate_xml_string(xml_str: str, object_type: Optional[str] = None) -> ValidationResult:
    """Validate XML string before submission to PAN-OS.

    This checks that the XML is well-formed and matches expected structure.

    Args:
        xml_str: XML string to validate
        object_type: Optional object type for structure validation

    Returns:
        ValidationResult with validation status and any errors/warnings

    Example:
        >>> xml = '<entry name="test"><ip-netmask>10.0.0.1/32</ip-netmask></entry>'
        >>> result = validate_xml_string(xml, "address")
        >>> assert result.is_valid
    """
    result = ValidationResult()

    # Check for empty XML
    if not xml_str or not xml_str.strip():
        result.add_error("XML string is empty")
        return result

    # Try to parse XML
    try:
        root = etree.fromstring(xml_str.encode())
    except etree.XMLSyntaxError as e:
        result.add_error(f"Malformed XML: {e}")
        return result

    # Validate root element is 'entry' for most objects
    if root.tag != "entry" and root.tag != "member":
        result.add_warning(f"Unexpected root element: {root.tag}")

    # Validate entry has name attribute for entry-type objects
    if root.tag == "entry":
        if "name" not in root.attrib:
            result.add_error("Entry element missing 'name' attribute")
        elif not root.attrib["name"]:
            result.add_error("Entry 'name' attribute is empty")

    # Check for empty required elements
    for elem in root.iter():
        if elem.text is None and len(elem) == 0:
            # Element has no text and no children - might be invalid
            if elem.tag not in [
                "tag",
                "static",
                "members",
                "from",
                "to",
                "source",
                "destination",
                "service",
                "application",
            ]:
                result.add_warning(f"Element '{elem.tag}' is empty")

    # Object-type specific validation
    if object_type:
        normalized_type = object_type.replace("-", "_")
        if normalized_type == "address":
            # Must have one of: ip-netmask, ip-range, fqdn
            has_type = False
            for type_elem in ["ip-netmask", "ip-range", "fqdn"]:
                if root.find(type_elem) is not None:
                    has_type = True
                    break
            if not has_type:
                result.add_error("Address must have one of: ip-netmask, ip-range, or fqdn")

        elif normalized_type == "service":
            # Must have protocol element
            if root.find("protocol") is None:
                result.add_error("Service must have protocol element")

        elif normalized_type in ["security_policy", "nat_policy"]:
            # Must have required policy fields
            required = ["from", "to", "source", "destination"]
            for req_field in required:
                if root.find(req_field) is None:
                    result.add_error(f"Policy must have '{req_field}' element")

    return result


def extract_object_type_from_xpath(xpath: str) -> Optional[str]:
    """Extract object type from XPath string.

    Args:
        xpath: XPath string like "/config/.../address/entry[@name='test']"

    Returns:
        Object type string or None if not found

    Example:
        >>> extract_object_type_from_xpath("/config/devices/.../address/entry[@name='test']")
        'address'
    """
    # Check for 'rules' in XPath first (security/nat policies)
    if (
        "/rulebase/security/rules" in xpath
        or "/pre-rulebase/security/rules" in xpath
        or "/post-rulebase/security/rules" in xpath
    ):
        return "security_policy"
    if (
        "/rulebase/nat/rules" in xpath
        or "/pre-rulebase/nat/rules" in xpath
        or "/post-rulebase/nat/rules" in xpath
    ):
        return "nat_policy"

    # Common object types in XPaths
    object_types = [
        "address",
        "address-group",
        "service",
        "service-group",
    ]

    for obj_type in object_types:
        if f"/{obj_type}/" in xpath or xpath.endswith(f"/{obj_type}"):
            return obj_type.replace("-", "_")

    return None
