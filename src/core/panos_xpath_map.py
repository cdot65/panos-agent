"""PAN-OS XML XPath mapping and validation.

Provides XPath mappings for all PAN-OS configuration objects and operations.
Based on PAN-OS XML API structure and actual running configuration examples.
Supports both Firewall and Panorama configurations with context-aware XPath generation.
"""

from typing import Any, Dict, Optional


class PanOSXPathMap:
    """XPath mapping for PAN-OS configuration objects.

    Supports both Firewall and Panorama deployments:
    - Firewall: /config/devices/.../vsys/entry[@name='vsys1']/{object_type}
    - Panorama Shared: /config/shared/{object_type}
    - Panorama Device-Group: /config/devices/.../device-group/entry[@name='{dg}']/{object_type}
    - Panorama Template: /config/devices/.../template/entry[@name='{tpl}']/config/{object_type}
    - Panorama Template-Stack: /config/devices/.../template-stack/entry[@name='{stack}']/{object_type}
    """

    # Base configuration paths
    BASE_DEVICES = "/config/devices/entry[@name='localhost.localdomain']"
    BASE_FIREWALL_VSYS = f"{BASE_DEVICES}/vsys/entry[@name='{{vsys}}']"
    BASE_PANORAMA_SHARED = "/config/shared"
    BASE_PANORAMA_DEVICE_GROUP = f"{BASE_DEVICES}/device-group/entry[@name='{{device_group}}']"
    BASE_PANORAMA_TEMPLATE = f"{BASE_DEVICES}/template/entry[@name='{{template}}']/config"
    BASE_PANORAMA_TEMPLATE_STACK = (
        f"{BASE_DEVICES}/template-stack/entry[@name='{{template_stack}}']"
    )

    # Object type to XPath suffix mapping (relative path after base)
    OBJECT_PATHS: Dict[str, str] = {
        # Address objects
        "address": "address/entry[@name='{name}']",
        "address_list": "address",
        # Address groups
        "address_group": "address-group/entry[@name='{name}']",
        "address_group_list": "address-group",
        # Service objects
        "service": "service/entry[@name='{name}']",
        "service_list": "service",
        # Service groups
        "service_group": "service-group/entry[@name='{name}']",
        "service_group_list": "service-group",
        # Security policies
        "security_policy": "rulebase/security/rules/entry[@name='{name}']",
        "security_policy_list": "rulebase/security/rules",
        # NAT policies
        "nat_policy": "rulebase/nat/rules/entry[@name='{name}']",
        "nat_policy_list": "rulebase/nat/rules",
        # Panorama-specific objects
        "device_group": "device-group/entry[@name='{name}']",
        "device_group_list": "device-group",
        "template": "template/entry[@name='{name}']",
        "template_list": "template",
        "template_stack": "template-stack/entry[@name='{name}']",
        "template_stack_list": "template-stack",
    }

    # Legacy XPATHS for backward compatibility (firewall-only)
    BASE_CONFIG = BASE_FIREWALL_VSYS.format(vsys="vsys1")
    XPATHS: Dict[str, str] = {
        # Address objects: /config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address
        "address": f"{BASE_CONFIG}/address/entry[@name='{{name}}']",
        "address_list": f"{BASE_CONFIG}/address",
        # Address groups: /config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address-group
        "address_group": f"{BASE_CONFIG}/address-group/entry[@name='{{name}}']",
        "address_group_list": f"{BASE_CONFIG}/address-group",
        # Service objects: /config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/service
        "service": f"{BASE_CONFIG}/service/entry[@name='{{name}}']",
        "service_list": f"{BASE_CONFIG}/service",
        # Service groups: /config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/service-group
        "service_group": f"{BASE_CONFIG}/service-group/entry[@name='{{name}}']",
        "service_group_list": f"{BASE_CONFIG}/service-group",
        # Security policies: /config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/rulebase/security/rules
        "security_policy": f"{BASE_CONFIG}/rulebase/security/rules/entry[@name='{{name}}']",
        "security_policy_list": f"{BASE_CONFIG}/rulebase/security/rules",
        # NAT policies: /config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/rulebase/nat/rules
        "nat_policy": f"{BASE_CONFIG}/rulebase/nat/rules/entry[@name='{{name}}']",
        "nat_policy_list": f"{BASE_CONFIG}/rulebase/nat/rules",
    }

    # XML element structure for each object type
    XML_STRUCTURES: Dict[str, Dict[str, str]] = {
        "address": {
            "root": "entry",
            "name_attr": "name",
            "fields": {
                "ip-netmask": "ip-netmask",  # <ip-netmask>10.0.0.0/24</ip-netmask>
                "ip-range": "ip-range",  # <ip-range>10.0.0.1-10.0.0.100</ip-range>
                "fqdn": "fqdn",  # <fqdn>example.com</fqdn>
                "description": "description",  # <description>...</description>
                "tag": "tag/member",  # <tag><member>tag1</member></tag>
            },
        },
        "address_group": {
            "root": "entry",
            "name_attr": "name",
            "fields": {
                "static": "static/member",  # <static><member>addr1</member></static>
                "dynamic": "dynamic/filter",  # <dynamic><filter>...</filter></dynamic>
                "description": "description",
                "tag": "tag/member",
            },
        },
        "service": {
            "root": "entry",
            "name_attr": "name",
            "fields": {
                "protocol": "protocol",  # <protocol><tcp>...</tcp></protocol>
                "tcp_port": "protocol/tcp/port",
                "udp_port": "protocol/udp/port",
                "description": "description",
                "tag": "tag/member",
            },
        },
        "service_group": {
            "root": "entry",
            "name_attr": "name",
            "fields": {
                "members": "members/member",  # <members><member>svc1</member></members>
                "tag": "tag/member",
            },
        },
        "security_policy": {
            "root": "entry",
            "name_attr": "name",
            "fields": {
                "from": "from/member",  # <from><member>trust</member></from>
                "to": "to/member",
                "source": "source/member",
                "destination": "destination/member",
                "service": "service/member",
                "application": "application/member",
                "action": "action",  # <action>allow</action>
                "description": "description",
                "tag": "tag/member",
                "log-end": "log-end",  # <log-end>yes</log-end>
                "disabled": "disabled",
            },
        },
        "nat_policy": {
            "root": "entry",
            "name_attr": "name",
            "fields": {
                "from": "from/member",
                "to": "to/member",
                "source": "source/member",
                "destination": "destination/member",
                "service": "service",
                "nat-type": "nat-type",
                "source-translation": "source-translation",
                "destination-translation": "destination-translation",
                "description": "description",
                "tag": "tag/member",
                "disabled": "disabled",
            },
        },
        # Panorama-specific objects
        "device_group": {
            "root": "entry",
            "name_attr": "name",
            "fields": {
                "description": "description",
                "devices": "devices/entry",  # <devices><entry name="device-serial"/></devices>
                "reference-templates": "reference-templates/member",
            },
        },
        "template": {
            "root": "entry",
            "name_attr": "name",
            "fields": {
                "description": "description",
                "config": "config",  # Contains device/network configuration
                "settings": "settings",
                "devices": "devices/entry",
            },
        },
        "template_stack": {
            "root": "entry",
            "name_attr": "name",
            "fields": {
                "description": "description",
                "templates": "templates/member",  # <templates><member>template1</member></templates>
                "devices": "devices/entry",
            },
        },
    }

    @classmethod
    def build_xpath(
        cls,
        object_type: str,
        name: Optional[str] = None,
        device_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build context-aware XPath for an object type.

        Auto-detects Panorama vs Firewall from device_context and selects appropriate base path.
        Context selection priority for Panorama: Template > Device-Group > Shared

        Args:
            object_type: Type of object (address, service, security_policy, etc.)
            name: Optional name of specific object
            device_context: Optional device context dictionary with:
                - device_type: "FIREWALL" or "PANORAMA"
                - vsys: Virtual system (default: "vsys1" for firewall)
                - device_group: Device group name (for Panorama)
                - template: Template name (for Panorama)
                - template_stack: Template stack name (for Panorama)

        Returns:
            Full XPath string

        Examples:
            # Firewall
            >>> build_xpath("address", "web-server", {"device_type": "FIREWALL"})
            "/config/devices/.../vsys/entry[@name='vsys1']/address/entry[@name='web-server']"

            # Panorama Shared
            >>> build_xpath("address", "web-server", {"device_type": "PANORAMA"})
            "/config/shared/address/entry[@name='web-server']"

            # Panorama Device-Group
            >>> build_xpath("address", "web-server", {"device_type": "PANORAMA", "device_group": "prod"})
            "/config/devices/.../device-group/entry[@name='prod']/address/entry[@name='web-server']"

            # Panorama Template
            >>> build_xpath("address", "web-server", {"device_type": "PANORAMA", "template": "dmz-template"})
            "/config/devices/.../template/entry[@name='dmz-template']/config/address/entry[@name='web-server']"
        """
        # Get object path suffix
        object_path = cls._get_object_path(object_type, name)

        # Check if this is a Panorama management object (device_group, template, template_stack)
        # These live at /config/devices/.../[object_type] and don't respect context hierarchy
        is_panorama_mgmt_object = object_type in [
            "device_group",
            "device_group_list",
            "template",
            "template_list",
            "template_stack",
            "template_stack_list",
        ]

        if is_panorama_mgmt_object:
            # Management objects always live at BASE_DEVICES level
            return f"{cls.BASE_DEVICES}/{object_path}"

        # Determine base path from context for regular objects
        if device_context and device_context.get("device_type") == "PANORAMA":
            base_path = cls._get_panorama_base_path(device_context)
        else:
            base_path = cls._get_firewall_base_path(device_context)

        return f"{base_path}/{object_path}"

    @classmethod
    def _get_object_path(cls, object_type: str, name: Optional[str] = None) -> str:
        """Get object-specific path suffix.

        Args:
            object_type: Type of object
            name: Optional name of specific object

        Returns:
            Relative path (e.g., "address/entry[@name='web-server']")
        """
        # Handle list vs single object
        if object_type.endswith("_list"):
            base_type = object_type[:-5]  # Remove "_list"
            path = cls.OBJECT_PATHS.get(object_type) or cls.OBJECT_PATHS.get(f"{base_type}_list")
        else:
            path = cls.OBJECT_PATHS.get(object_type)
            if not path and name is None:
                # Try looking for list version
                path = cls.OBJECT_PATHS.get(f"{object_type}_list")

        if not path:
            raise ValueError(f"Unknown object type: {object_type}")

        # Format with name if provided
        if name and "{name}" in path:
            path = path.format(name=name)

        return path

    @classmethod
    def _get_firewall_base_path(cls, device_context: Optional[Dict[str, Any]] = None) -> str:
        """Get base path for firewall configuration.

        Args:
            device_context: Optional context with vsys

        Returns:
            Base path for firewall (e.g., "/config/devices/.../vsys/entry[@name='vsys1']")
        """
        vsys = "vsys1"  # Default
        if device_context and device_context.get("vsys"):
            vsys = device_context["vsys"]

        return cls.BASE_FIREWALL_VSYS.format(vsys=vsys)

    @classmethod
    def _get_panorama_base_path(cls, device_context: Dict[str, Any]) -> str:
        """Get base path for Panorama configuration.

        Context selection priority: Template > Device-Group > Shared

        Args:
            device_context: Context with optional template, device_group, template_stack

        Returns:
            Base path for Panorama configuration
        """
        # Priority 1: Template (network/device settings)
        if device_context.get("template"):
            return cls.BASE_PANORAMA_TEMPLATE.format(template=device_context["template"])

        # Priority 2: Template Stack (alternative to template)
        if device_context.get("template_stack"):
            return cls.BASE_PANORAMA_TEMPLATE_STACK.format(
                template_stack=device_context["template_stack"]
            )

        # Priority 3: Device Group (security policies, objects)
        if device_context.get("device_group"):
            return cls.BASE_PANORAMA_DEVICE_GROUP.format(
                device_group=device_context["device_group"]
            )

        # Default: Shared (available to all)
        return cls.BASE_PANORAMA_SHARED

    @classmethod
    def get_xpath(cls, object_type: str, name: Optional[str] = None) -> str:
        """Get XPath for an object type (legacy method for backward compatibility).

        Args:
            object_type: Type of object (address, service, etc.)
            name: Optional name of specific object

        Returns:
            XPath string

        Examples:
            >>> PanOSXPathMap.get_xpath("address", "web-server")
            "/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address/entry[@name='web-server']"

            >>> PanOSXPathMap.get_xpath("address_list")
            "/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address"
        """
        # Handle list vs single object
        if object_type.endswith("_list"):
            # Remove _list suffix and look up list xpath
            base_type = object_type[:-5]  # Remove "_list"
            xpath = cls.XPATHS.get(object_type) or cls.XPATHS.get(f"{base_type}_list")
        else:
            # Regular object lookup
            xpath = cls.XPATHS.get(object_type)
            if not xpath and name is None:
                # Try looking for list version
                xpath = cls.XPATHS.get(f"{object_type}_list")

        if not xpath:
            raise ValueError(f"Unknown object type: {object_type}")

        if name and "{name}" in xpath:
            xpath = xpath.format(name=name)

        return xpath

    @classmethod
    def get_structure(cls, object_type: str) -> Dict[str, str]:
        """Get XML structure definition for an object type.

        Args:
            object_type: Type of object

        Returns:
            Dictionary with structure metadata
        """
        return cls.XML_STRUCTURES.get(object_type, {})

    @classmethod
    def validate_object_name(cls, name: str) -> tuple[bool, Optional[str]]:
        """Validate object name according to PAN-OS rules.

        PAN-OS object name rules:
        - Maximum 63 characters
        - Alphanumeric, hyphen, underscore, period, space
        - Cannot start with space or underscore
        - No consecutive spaces

        Args:
            name: Object name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name:
            return False, "Name cannot be empty"

        if len(name) > 63:
            return False, f"Name exceeds maximum length of 63 characters (got {len(name)})"

        if name[0] in (" ", "_"):
            return False, "Name cannot start with space or underscore"

        if "  " in name:
            return False, "Name cannot contain consecutive spaces"

        # Check for valid characters
        import re

        if not re.match(r"^[a-zA-Z0-9\-_. ]+$", name):
            return (
                False,
                "Name can only contain alphanumeric characters, hyphen, underscore, period, and space",
            )

        return True, None

    @classmethod
    def get_api_xpath(cls, object_type: str, name: Optional[str] = None) -> str:
        """Get XPath formatted for API requests.

        For API requests, we use a shorter xpath without the full device path
        for certain operations.

        Args:
            object_type: Type of object
            name: Optional name of specific object

        Returns:
            API-formatted XPath string
        """
        xpath = cls.get_xpath(object_type, name)
        # Remove /config prefix for certain API operations
        # This can be customized based on specific API requirements
        return xpath


# Object-specific validation rules
VALIDATION_RULES = {
    "address": {
        "required_fields": ["name", "value"],
        "valid_types": ["ip-netmask", "ip-range", "fqdn"],
        "field_validators": {
            "ip-netmask": lambda v: _validate_ip_netmask(v),
            "ip-range": lambda v: _validate_ip_range(v),
            "fqdn": lambda v: _validate_fqdn(v),
        },
    },
    "service": {
        "required_fields": ["name", "protocol"],
        "valid_protocols": ["tcp", "udp"],
        "field_validators": {
            "tcp_port": lambda v: _validate_port(v),
            "udp_port": lambda v: _validate_port(v),
        },
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
        "valid_actions": ["allow", "deny", "drop", "reset-client", "reset-server", "reset-both"],
    },
    "nat_policy": {
        "required_fields": ["name", "from", "to", "source", "destination", "service"],
        "valid_nat_types": ["ipv4", "nat64", "nptv6"],
    },
}


# Helper validation functions
def _validate_ip_netmask(value: str) -> tuple[bool, Optional[str]]:
    """Validate IP address with netmask."""
    import re

    # Regex for IP/CIDR (e.g., 10.0.0.0/24)
    match = re.match(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(/(\d{1,2}))?$", value)
    if match:
        # Validate octets are 0-255
        octets = [int(match.group(i)) for i in range(1, 5)]
        if all(0 <= octet <= 255 for octet in octets):
            # Validate CIDR if present
            if match.group(6):
                cidr = int(match.group(6))
                if 0 <= cidr <= 32:
                    return True, None
            else:
                return True, None
    return False, f"Invalid IP/netmask format: {value}"


def _validate_ip_range(value: str) -> tuple[bool, Optional[str]]:
    """Validate IP address range."""
    import re

    # Regex for IP range (e.g., 10.0.0.1-10.0.0.100)
    match = re.match(
        r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})-(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$",
        value,
    )
    if match:
        # Validate all octets are 0-255
        octets = [int(match.group(i)) for i in range(1, 9)]
        if all(0 <= octet <= 255 for octet in octets):
            return True, None
    return False, f"Invalid IP range format: {value}"


def _validate_fqdn(value: str) -> tuple[bool, Optional[str]]:
    """Validate FQDN."""
    import re

    # Check if it looks like an IP address (reject it)
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", value):
        return False, f"IP addresses are not valid FQDNs: {value}"
    # FQDN validation (must have at least one dot, proper domain format)
    if re.match(
        r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)+$",
        value,
    ):
        return True, None
    return False, f"Invalid FQDN format: {value}"


def _validate_port(value: str) -> tuple[bool, Optional[str]]:
    """Validate port number or range."""
    import re

    # Port can be single (80), range (8080-8090), or comma-separated (80,443)
    if re.match(r"^\d{1,5}(-\d{1,5})?(,\d{1,5}(-\d{1,5})?)*$", value):
        # Check port numbers are valid (1-65535)
        ports = re.findall(r"\d+", value)
        if all(1 <= int(p) <= 65535 for p in ports):
            return True, None
        return False, "Port numbers must be between 1 and 65535"
    return False, f"Invalid port format: {value}"


def validate_object_data(object_type: str, data: dict) -> tuple[bool, Optional[str]]:
    """Validate object data against PAN-OS rules.

    Args:
        object_type: Type of object
        data: Object data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    rules = VALIDATION_RULES.get(object_type)
    if not rules:
        # No specific validation rules, accept as-is
        return True, None

    # Check required fields
    required = rules.get("required_fields", [])
    for field in required:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"

    # Validate field-specific rules
    validators = rules.get("field_validators", {})
    for field, validator in validators.items():
        if field in data:
            is_valid, error = validator(data[field])
            if not is_valid:
                return False, error

    # Check valid values for enum fields
    if "valid_types" in rules and "type" in data:
        if data["type"] not in rules["valid_types"]:
            return False, f"Invalid type: {data['type']}. Must be one of {rules['valid_types']}"

    if "valid_protocols" in rules and "protocol" in data:
        if data["protocol"] not in rules["valid_protocols"]:
            return (
                False,
                f"Invalid protocol: {data['protocol']}. Must be one of {rules['valid_protocols']}",
            )

    if "valid_actions" in rules and "action" in data:
        if data["action"] not in rules["valid_actions"]:
            return (
                False,
                f"Invalid action: {data['action']}. Must be one of {rules['valid_actions']}",
            )

    return True, None
