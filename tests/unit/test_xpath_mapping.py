"""Tests for PAN-OS XPath mapping and validation.

Tests the XPath generation, name validation, and data validation
based on actual PAN-OS 11.1.4 configuration structure.
"""

import pytest

from src.core.panos_xpath_map import (
    VALIDATION_RULES,
    PanOSXPathMap,
    _validate_fqdn,
    _validate_ip_netmask,
    _validate_ip_range,
    _validate_port,
    validate_object_data,
)


class TestXPathGeneration:
    """Test XPath expression generation."""

    def test_xpath_for_address_object(self):
        """Test XPath for specific address object."""
        xpath = PanOSXPathMap.get_xpath("address", "web-server")

        assert "localhost.localdomain" in xpath
        assert "vsys1" in xpath
        assert "address" in xpath
        assert "entry[@name='web-server']" in xpath

    def test_xpath_for_address_list(self):
        """Test XPath for listing all addresses."""
        xpath = PanOSXPathMap.get_xpath("address_list")

        assert "localhost.localdomain" in xpath
        assert "vsys1" in xpath
        assert "address" in xpath
        # List path should end with object type, not an entry filter
        assert xpath.endswith("/address")

    def test_xpath_for_service(self):
        """Test XPath for service object."""
        xpath = PanOSXPathMap.get_xpath("service", "web-http")

        assert "service" in xpath
        assert "entry[@name='web-http']" in xpath

    def test_xpath_for_security_policy(self):
        """Test XPath for security policy."""
        xpath = PanOSXPathMap.get_xpath("security_policy", "allow-web")

        assert "rulebase/security/rules" in xpath
        assert "entry[@name='allow-web']" in xpath

    def test_xpath_for_nat_policy(self):
        """Test XPath for NAT policy."""
        xpath = PanOSXPathMap.get_xpath("nat_policy", "outbound-nat")

        assert "rulebase/nat/rules" in xpath
        assert "entry[@name='outbound-nat']" in xpath

    def test_xpath_for_unknown_type(self):
        """Test error handling for unknown object type."""
        with pytest.raises(ValueError, match="Unknown object type"):
            PanOSXPathMap.get_xpath("unknown_type", "test")

    def test_all_object_types_have_xpaths(self):
        """Test that all supported object types have XPath mappings."""
        object_types = [
            "address",
            "address_group",
            "service",
            "service_group",
            "security_policy",
            "nat_policy",
        ]

        for obj_type in object_types:
            # Should not raise
            xpath = PanOSXPathMap.get_xpath(obj_type, "test")
            assert xpath
            assert isinstance(xpath, str)


class TestNameValidation:
    """Test object name validation according to PAN-OS rules."""

    def test_valid_names(self):
        """Test valid object names."""
        valid_names = [
            "web-server",
            "my_server",
            "server.test",
            "Server 1",
            "a",  # Single character
            "A" * 63,  # Max length
            "test-123",
            "web.server.1",
        ]

        for name in valid_names:
            is_valid, error = PanOSXPathMap.validate_object_name(name)
            assert is_valid, f"Name '{name}' should be valid, got error: {error}"
            assert error is None

    def test_invalid_name_empty(self):
        """Test empty name is invalid."""
        is_valid, error = PanOSXPathMap.validate_object_name("")

        assert not is_valid
        assert "empty" in error.lower()

    def test_invalid_name_too_long(self):
        """Test name exceeding 63 characters is invalid."""
        long_name = "a" * 64
        is_valid, error = PanOSXPathMap.validate_object_name(long_name)

        assert not is_valid
        assert "63" in error
        assert "64" in error

    def test_invalid_name_starts_with_underscore(self):
        """Test name starting with underscore is invalid."""
        is_valid, error = PanOSXPathMap.validate_object_name("_server")

        assert not is_valid
        assert "underscore" in error.lower()

    def test_invalid_name_starts_with_space(self):
        """Test name starting with space is invalid."""
        is_valid, error = PanOSXPathMap.validate_object_name(" server")

        assert not is_valid
        assert "space" in error.lower()

    def test_invalid_name_consecutive_spaces(self):
        """Test name with consecutive spaces is invalid."""
        is_valid, error = PanOSXPathMap.validate_object_name("web  server")

        assert not is_valid
        assert "consecutive" in error.lower()

    def test_invalid_name_special_characters(self):
        """Test name with invalid special characters."""
        invalid_names = [
            "server@test",
            "web#server",
            "test$name",
            "server%1",
            "web&server",
        ]

        for name in invalid_names:
            is_valid, error = PanOSXPathMap.validate_object_name(name)
            assert not is_valid, f"Name '{name}' should be invalid"
            assert error is not None


class TestIPValidation:
    """Test IP address validation."""

    def test_valid_ip_netmask(self):
        """Test valid IP/netmask formats."""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.0/8",
            "172.16.0.0/16",
            "192.168.1.0/24",
            "1.1.1.1",
            "255.255.255.255",
        ]

        for ip in valid_ips:
            is_valid, error = _validate_ip_netmask(ip)
            assert is_valid, f"IP '{ip}' should be valid, got error: {error}"

    def test_invalid_ip_netmask(self):
        """Test invalid IP/netmask formats."""
        invalid_ips = [
            "999.0.0.0",
            "192.168.1",
            "192.168.1.1.1",
            "not-an-ip",
            "192.168.1.1/33",  # Invalid CIDR
        ]

        for ip in invalid_ips:
            is_valid, error = _validate_ip_netmask(ip)
            assert not is_valid, f"IP '{ip}' should be invalid"

    def test_valid_ip_range(self):
        """Test valid IP range formats."""
        valid_ranges = [
            "192.168.1.1-192.168.1.100",
            "10.0.0.1-10.0.0.255",
        ]

        for ip_range in valid_ranges:
            is_valid, error = _validate_ip_range(ip_range)
            assert is_valid, f"Range '{ip_range}' should be valid, got error: {error}"

    def test_invalid_ip_range(self):
        """Test invalid IP range formats."""
        invalid_ranges = [
            "192.168.1.1",  # Not a range
            "192.168.1.1-999.0.0.0",  # Invalid end IP
            "not-a-range",
        ]

        for ip_range in invalid_ranges:
            is_valid, error = _validate_ip_range(ip_range)
            assert not is_valid, f"Range '{ip_range}' should be invalid"


class TestFQDNValidation:
    """Test FQDN validation."""

    def test_valid_fqdns(self):
        """Test valid FQDN formats."""
        valid_fqdns = [
            "example.com",
            "www.example.com",
            "mail.google.com",
            "a.b.c.d.e.f",
            "test-server.example.com",
        ]

        for fqdn in valid_fqdns:
            is_valid, error = _validate_fqdn(fqdn)
            assert is_valid, f"FQDN '{fqdn}' should be valid, got error: {error}"

    def test_invalid_fqdns(self):
        """Test invalid FQDN formats."""
        invalid_fqdns = [
            "-example.com",  # Starts with hyphen
            "example-.com",  # Ends with hyphen
            "192.168.1.1",  # IP address
            "not a domain",  # Spaces
        ]

        for fqdn in invalid_fqdns:
            is_valid, error = _validate_fqdn(fqdn)
            assert not is_valid, f"FQDN '{fqdn}' should be invalid"


class TestPortValidation:
    """Test port number validation."""

    def test_valid_ports(self):
        """Test valid port formats."""
        valid_ports = [
            "80",
            "443",
            "8080",
            "1-65535",  # Full range
            "8080-8090",  # Range
            "80,443",  # Multiple
            "80,443,8080",  # Multiple
            "8080-8090,9000-9100",  # Multiple ranges
        ]

        for port in valid_ports:
            is_valid, error = _validate_port(port)
            assert is_valid, f"Port '{port}' should be valid, got error: {error}"

    def test_invalid_ports(self):
        """Test invalid port formats."""
        invalid_ports = [
            "0",  # Too low
            "65536",  # Too high
            "999999",  # Way too high
            "not-a-port",
            "-80",  # Negative
        ]

        for port in invalid_ports:
            is_valid, error = _validate_port(port)
            assert not is_valid, f"Port '{port}' should be invalid"


class TestObjectDataValidation:
    """Test complete object data validation."""

    def test_validate_address_object_valid(self):
        """Test valid address object data."""
        data = {
            "name": "web-server",
            "value": "10.0.0.1",
            "type": "ip-netmask",
            "description": "Web server",
            "tag": ["Web", "Production"],
        }

        is_valid, error = validate_object_data("address", data)
        assert is_valid
        assert error is None

    def test_validate_address_object_missing_required(self):
        """Test address object with missing required fields."""
        data = {
            "description": "Missing name and value",
        }

        is_valid, error = validate_object_data("address", data)
        assert not is_valid
        assert "required" in error.lower()

    def test_validate_service_object_valid(self):
        """Test valid service object data."""
        data = {
            "name": "web-http",
            "protocol": "tcp",
            "tcp_port": "8080",
            "description": "HTTP service",
        }

        is_valid, error = validate_object_data("service", data)
        assert is_valid
        assert error is None

    def test_validate_service_invalid_protocol(self):
        """Test service with invalid protocol."""
        data = {
            "name": "test-service",
            "protocol": "invalid",  # Not tcp or udp
        }

        is_valid, error = validate_object_data("service", data)
        assert not is_valid
        assert "protocol" in error.lower()

    def test_validate_security_policy_valid(self):
        """Test valid security policy data."""
        data = {
            "name": "allow-web",
            "from": ["trust"],
            "to": ["untrust"],
            "source": ["any"],
            "destination": ["any"],
            "service": ["application-default"],
            "application": ["web-browsing", "ssl"],
            "action": "allow",
        }

        is_valid, error = validate_object_data("security_policy", data)
        assert is_valid
        assert error is None

    def test_validate_security_policy_invalid_action(self):
        """Test security policy with invalid action."""
        data = {
            "name": "test-rule",
            "from": ["trust"],
            "to": ["untrust"],
            "source": ["any"],
            "destination": ["any"],
            "service": ["any"],
            "application": ["any"],
            "action": "invalid-action",  # Not allow/deny/drop
        }

        is_valid, error = validate_object_data("security_policy", data)
        assert not is_valid
        assert "action" in error.lower()

    def test_validate_nat_policy_valid(self):
        """Test valid NAT policy data."""
        data = {
            "name": "outbound-nat",
            "from": ["trust"],
            "to": ["untrust"],
            "source": ["10.0.0.0/8"],
            "destination": ["any"],
            "service": "any",
        }

        is_valid, error = validate_object_data("nat_policy", data)
        assert is_valid
        assert error is None

    def test_validate_unknown_object_type(self):
        """Test validation with unknown object type."""
        data = {"name": "test"}

        # Should return True (no validation rules)
        is_valid, error = validate_object_data("unknown_type", data)
        assert is_valid


class TestStructureDefinitions:
    """Test XML structure definitions."""

    def test_get_structure_for_address(self):
        """Test getting structure definition for address."""
        structure = PanOSXPathMap.get_structure("address")

        assert structure
        assert "root" in structure
        assert "fields" in structure
        assert structure["root"] == "entry"
        assert "name_attr" in structure
        assert structure["name_attr"] == "name"

    def test_get_structure_for_service(self):
        """Test getting structure definition for service."""
        structure = PanOSXPathMap.get_structure("service")

        assert structure
        assert structure["root"] == "entry"
        assert "protocol" in structure["fields"]

    def test_get_structure_for_unknown_type(self):
        """Test getting structure for unknown type returns empty."""
        structure = PanOSXPathMap.get_structure("unknown_type")

        assert structure == {}

    def test_all_object_types_have_structures(self):
        """Test that all supported types have structure definitions."""
        object_types = [
            "address",
            "address_group",
            "service",
            "service_group",
            "security_policy",
            "nat_policy",
        ]

        for obj_type in object_types:
            structure = PanOSXPathMap.get_structure(obj_type)
            assert structure, f"No structure for {obj_type}"
            assert "root" in structure
            assert "fields" in structure


class TestValidationRules:
    """Test validation rules configuration."""

    def test_validation_rules_exist(self):
        """Test that validation rules are defined."""
        assert VALIDATION_RULES
        assert isinstance(VALIDATION_RULES, dict)

    def test_address_validation_rules(self):
        """Test address object validation rules."""
        rules = VALIDATION_RULES.get("address")

        assert rules
        assert "required_fields" in rules
        assert "name" in rules["required_fields"]
        assert "value" in rules["required_fields"]

    def test_service_validation_rules(self):
        """Test service object validation rules."""
        rules = VALIDATION_RULES.get("service")

        assert rules
        assert "required_fields" in rules
        assert "valid_protocols" in rules
        assert "tcp" in rules["valid_protocols"]
        assert "udp" in rules["valid_protocols"]

    def test_security_policy_validation_rules(self):
        """Test security policy validation rules."""
        rules = VALIDATION_RULES.get("security_policy")

        assert rules
        assert "valid_actions" in rules
        assert "allow" in rules["valid_actions"]
        assert "deny" in rules["valid_actions"]
        assert "drop" in rules["valid_actions"]


class TestAPIXPath:
    """Test API-formatted XPath generation."""

    def test_api_xpath_format(self):
        """Test that API XPath is correctly formatted."""
        xpath = PanOSXPathMap.get_api_xpath("address", "test")

        assert xpath
        # API xpath should be same as regular xpath for now
        regular_xpath = PanOSXPathMap.get_xpath("address", "test")
        assert xpath == regular_xpath

    def test_api_xpath_for_list(self):
        """Test API XPath for listing objects."""
        xpath = PanOSXPathMap.get_api_xpath("service_list")

        assert xpath
        assert "service" in xpath
        # List path should end with object type, not a specific entry filter
        assert xpath.endswith("/service")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
