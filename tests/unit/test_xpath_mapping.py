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


class TestPanoramaXPathFirewall:
    """Test context-aware XPath generation for Firewall deployments."""

    def test_firewall_address_default_vsys(self):
        """Test firewall address XPath with default vsys."""
        context = {"device_type": "FIREWALL"}
        xpath = PanOSXPathMap.build_xpath("address", "web-server", context)

        assert "/config/devices/entry[@name='localhost.localdomain']" in xpath
        assert "/vsys/entry[@name='vsys1']" in xpath
        assert "/address/entry[@name='web-server']" in xpath

    def test_firewall_address_custom_vsys(self):
        """Test firewall address XPath with custom vsys."""
        context = {"device_type": "FIREWALL", "vsys": "vsys2"}
        xpath = PanOSXPathMap.build_xpath("address", "web-server", context)

        assert "/vsys/entry[@name='vsys2']" in xpath
        assert "/address/entry[@name='web-server']" in xpath

    def test_firewall_service_xpath(self):
        """Test firewall service XPath."""
        context = {"device_type": "FIREWALL"}
        xpath = PanOSXPathMap.build_xpath("service", "http-8080", context)

        assert "vsys1" in xpath
        assert "service/entry[@name='http-8080']" in xpath

    def test_firewall_security_policy_xpath(self):
        """Test firewall security policy XPath."""
        context = {"device_type": "FIREWALL"}
        xpath = PanOSXPathMap.build_xpath("security_policy", "allow-web", context)

        assert "vsys1" in xpath
        assert "rulebase/security/rules/entry[@name='allow-web']" in xpath

    def test_firewall_list_xpath(self):
        """Test firewall list XPath."""
        context = {"device_type": "FIREWALL"}
        xpath = PanOSXPathMap.build_xpath("address_list", device_context=context)

        assert "vsys1" in xpath
        assert xpath.endswith("/address")

    def test_firewall_no_context_defaults_to_firewall(self):
        """Test that no context defaults to firewall behavior."""
        xpath = PanOSXPathMap.build_xpath("address", "test")

        assert "vsys1" in xpath
        assert "/address/entry[@name='test']" in xpath


class TestPanoramaXPathShared:
    """Test Panorama Shared context XPath generation."""

    def test_panorama_shared_address(self):
        """Test Panorama shared address XPath."""
        context = {"device_type": "PANORAMA"}
        xpath = PanOSXPathMap.build_xpath("address", "web-server", context)

        assert xpath == "/config/shared/address/entry[@name='web-server']"

    def test_panorama_shared_address_group(self):
        """Test Panorama shared address-group XPath."""
        context = {"device_type": "PANORAMA"}
        xpath = PanOSXPathMap.build_xpath("address_group", "web-servers", context)

        assert xpath == "/config/shared/address-group/entry[@name='web-servers']"

    def test_panorama_shared_service(self):
        """Test Panorama shared service XPath."""
        context = {"device_type": "PANORAMA"}
        xpath = PanOSXPathMap.build_xpath("service", "http-8080", context)

        assert xpath == "/config/shared/service/entry[@name='http-8080']"

    def test_panorama_shared_service_group(self):
        """Test Panorama shared service-group XPath."""
        context = {"device_type": "PANORAMA"}
        xpath = PanOSXPathMap.build_xpath("service_group", "web-services", context)

        assert xpath == "/config/shared/service-group/entry[@name='web-services']"

    def test_panorama_shared_list(self):
        """Test Panorama shared list XPath."""
        context = {"device_type": "PANORAMA"}
        xpath = PanOSXPathMap.build_xpath("address_list", device_context=context)

        assert xpath == "/config/shared/address"


class TestPanoramaXPathDeviceGroup:
    """Test Panorama Device-Group context XPath generation."""

    def test_device_group_address(self):
        """Test device-group address XPath."""
        context = {"device_type": "PANORAMA", "device_group": "production"}
        xpath = PanOSXPathMap.build_xpath("address", "web-server", context)

        assert "/config/devices/entry[@name='localhost.localdomain']" in xpath
        assert "/device-group/entry[@name='production']" in xpath
        assert "/address/entry[@name='web-server']" in xpath

    def test_device_group_security_policy(self):
        """Test device-group security policy XPath."""
        context = {"device_type": "PANORAMA", "device_group": "dmz"}
        xpath = PanOSXPathMap.build_xpath("security_policy", "allow-web", context)

        assert "/device-group/entry[@name='dmz']" in xpath
        assert "/rulebase/security/rules/entry[@name='allow-web']" in xpath

    def test_device_group_nat_policy(self):
        """Test device-group NAT policy XPath."""
        context = {"device_type": "PANORAMA", "device_group": "production"}
        xpath = PanOSXPathMap.build_xpath("nat_policy", "outbound-nat", context)

        assert "/device-group/entry[@name='production']" in xpath
        assert "/rulebase/nat/rules/entry[@name='outbound-nat']" in xpath

    def test_device_group_service(self):
        """Test device-group service XPath."""
        context = {"device_type": "PANORAMA", "device_group": "branch"}
        xpath = PanOSXPathMap.build_xpath("service", "custom-svc", context)

        assert "/device-group/entry[@name='branch']" in xpath
        assert "/service/entry[@name='custom-svc']" in xpath

    def test_device_group_list(self):
        """Test device-group list XPath."""
        context = {"device_type": "PANORAMA", "device_group": "production"}
        xpath = PanOSXPathMap.build_xpath("service_list", device_context=context)

        assert "/device-group/entry[@name='production']" in xpath
        assert xpath.endswith("/service")


class TestPanoramaXPathTemplate:
    """Test Panorama Template context XPath generation."""

    def test_template_address(self):
        """Test template address XPath."""
        context = {"device_type": "PANORAMA", "template": "dmz-template"}
        xpath = PanOSXPathMap.build_xpath("address", "web-server", context)

        assert "/config/devices/entry[@name='localhost.localdomain']" in xpath
        assert "/template/entry[@name='dmz-template']/config" in xpath
        assert "/address/entry[@name='web-server']" in xpath

    def test_template_service(self):
        """Test template service XPath."""
        context = {"device_type": "PANORAMA", "template": "branch-template"}
        xpath = PanOSXPathMap.build_xpath("service", "custom-svc", context)

        assert "/template/entry[@name='branch-template']/config" in xpath
        assert "/service/entry[@name='custom-svc']" in xpath

    def test_template_list(self):
        """Test template list XPath."""
        context = {"device_type": "PANORAMA", "template": "dmz-template"}
        xpath = PanOSXPathMap.build_xpath("address_list", device_context=context)

        assert "/template/entry[@name='dmz-template']/config" in xpath
        assert xpath.endswith("/address")


class TestPanoramaXPathTemplateStack:
    """Test Panorama Template-Stack context XPath generation."""

    def test_template_stack_address(self):
        """Test template-stack address XPath."""
        context = {"device_type": "PANORAMA", "template_stack": "prod-stack"}
        xpath = PanOSXPathMap.build_xpath("address", "web-server", context)

        assert "/config/devices/entry[@name='localhost.localdomain']" in xpath
        assert "/template-stack/entry[@name='prod-stack']" in xpath
        assert "/address/entry[@name='web-server']" in xpath

    def test_template_stack_service(self):
        """Test template-stack service XPath."""
        context = {"device_type": "PANORAMA", "template_stack": "branch-stack"}
        xpath = PanOSXPathMap.build_xpath("service", "custom-svc", context)

        assert "/template-stack/entry[@name='branch-stack']" in xpath
        assert "/service/entry[@name='custom-svc']" in xpath


class TestPanoramaContextPriority:
    """Test context selection priority for Panorama."""

    def test_template_over_device_group(self):
        """Test that template takes priority over device-group."""
        context = {
            "device_type": "PANORAMA",
            "template": "dmz-template",
            "device_group": "production",
        }
        xpath = PanOSXPathMap.build_xpath("address", "test", context)

        # Should use template, not device-group
        assert "/template/entry[@name='dmz-template']/config" in xpath
        assert "/device-group/" not in xpath

    def test_template_stack_over_device_group(self):
        """Test that template-stack takes priority over device-group."""
        context = {
            "device_type": "PANORAMA",
            "template_stack": "prod-stack",
            "device_group": "production",
        }
        xpath = PanOSXPathMap.build_xpath("address", "test", context)

        # Should use template-stack, not device-group
        assert "/template-stack/entry[@name='prod-stack']" in xpath
        assert "/device-group/" not in xpath

    def test_template_over_template_stack(self):
        """Test that template takes priority over template-stack."""
        context = {
            "device_type": "PANORAMA",
            "template": "dmz-template",
            "template_stack": "prod-stack",
        }
        xpath = PanOSXPathMap.build_xpath("address", "test", context)

        # Should use template, not template-stack
        assert "/template/entry[@name='dmz-template']/config" in xpath
        assert "/template-stack/" not in xpath

    def test_device_group_over_shared(self):
        """Test that device-group takes priority over shared."""
        context = {
            "device_type": "PANORAMA",
            "device_group": "production",
        }
        xpath = PanOSXPathMap.build_xpath("address", "test", context)

        # Should use device-group, not shared
        assert "/device-group/entry[@name='production']" in xpath
        assert xpath != "/config/shared/address/entry[@name='test']"

    def test_shared_as_fallback(self):
        """Test that shared is used when no other context provided."""
        context = {"device_type": "PANORAMA"}
        xpath = PanOSXPathMap.build_xpath("address", "test", context)

        # Should fall back to shared
        assert xpath == "/config/shared/address/entry[@name='test']"


class TestPanoramaSpecificObjects:
    """Test Panorama-specific object XPaths (device-group, template, template-stack)."""

    def test_device_group_object_xpath(self):
        """Test device-group object XPath at Panorama root."""
        context = {"device_type": "PANORAMA"}
        xpath = PanOSXPathMap.build_xpath("device_group", "production", context)

        # Device-group objects are at panorama root level
        assert "/config/devices/entry[@name='localhost.localdomain']" in xpath
        assert "/device-group/entry[@name='production']" in xpath

    def test_device_group_list_xpath(self):
        """Test device-group list XPath."""
        context = {"device_type": "PANORAMA"}
        xpath = PanOSXPathMap.build_xpath("device_group_list", device_context=context)

        assert "/config/devices/entry[@name='localhost.localdomain']" in xpath
        assert xpath.endswith("/device-group")

    def test_template_object_xpath(self):
        """Test template object XPath at Panorama root."""
        context = {"device_type": "PANORAMA"}
        xpath = PanOSXPathMap.build_xpath("template", "dmz-template", context)

        assert "/config/devices/entry[@name='localhost.localdomain']" in xpath
        assert "/template/entry[@name='dmz-template']" in xpath

    def test_template_list_xpath(self):
        """Test template list XPath."""
        context = {"device_type": "PANORAMA"}
        xpath = PanOSXPathMap.build_xpath("template_list", device_context=context)

        assert "/config/devices/entry[@name='localhost.localdomain']" in xpath
        assert xpath.endswith("/template")

    def test_template_stack_object_xpath(self):
        """Test template-stack object XPath at Panorama root."""
        context = {"device_type": "PANORAMA"}
        xpath = PanOSXPathMap.build_xpath("template_stack", "prod-stack", context)

        assert "/config/devices/entry[@name='localhost.localdomain']" in xpath
        assert "/template-stack/entry[@name='prod-stack']" in xpath

    def test_template_stack_list_xpath(self):
        """Test template-stack list XPath."""
        context = {"device_type": "PANORAMA"}
        xpath = PanOSXPathMap.build_xpath("template_stack_list", device_context=context)

        assert "/config/devices/entry[@name='localhost.localdomain']" in xpath
        assert xpath.endswith("/template-stack")


class TestBackwardCompatibility:
    """Test backward compatibility with legacy get_xpath method."""

    def test_legacy_get_xpath_still_works(self):
        """Test that legacy get_xpath method still works."""
        xpath = PanOSXPathMap.get_xpath("address", "test")

        assert xpath
        assert "vsys1" in xpath
        assert "address/entry[@name='test']" in xpath

    def test_legacy_list_xpath_still_works(self):
        """Test that legacy list xpath still works."""
        xpath = PanOSXPathMap.get_xpath("service_list")

        assert xpath
        assert "vsys1" in xpath
        assert xpath.endswith("/service")

    def test_build_xpath_without_context_matches_legacy(self):
        """Test that build_xpath without context matches legacy behavior."""
        legacy_xpath = PanOSXPathMap.get_xpath("address", "test")
        new_xpath = PanOSXPathMap.build_xpath("address", "test")

        # Should produce same result (defaults to firewall vsys1)
        assert new_xpath == legacy_xpath


class TestXPathHelperMethods:
    """Test internal XPath helper methods."""

    def test_get_object_path_address(self):
        """Test _get_object_path for address."""
        path = PanOSXPathMap._get_object_path("address", "test")
        assert path == "address/entry[@name='test']"

    def test_get_object_path_list(self):
        """Test _get_object_path for list."""
        path = PanOSXPathMap._get_object_path("service_list")
        assert path == "service"

    def test_get_firewall_base_path_default(self):
        """Test _get_firewall_base_path with defaults."""
        base = PanOSXPathMap._get_firewall_base_path()
        assert base == "/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']"

    def test_get_firewall_base_path_custom_vsys(self):
        """Test _get_firewall_base_path with custom vsys."""
        base = PanOSXPathMap._get_firewall_base_path({"vsys": "vsys3"})
        assert base == "/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys3']"

    def test_get_panorama_base_path_shared(self):
        """Test _get_panorama_base_path defaults to shared."""
        base = PanOSXPathMap._get_panorama_base_path({})
        assert base == "/config/shared"

    def test_get_panorama_base_path_device_group(self):
        """Test _get_panorama_base_path with device-group."""
        base = PanOSXPathMap._get_panorama_base_path({"device_group": "prod"})
        assert base == "/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='prod']"

    def test_get_panorama_base_path_template(self):
        """Test _get_panorama_base_path with template."""
        base = PanOSXPathMap._get_panorama_base_path({"template": "dmz"})
        assert base == "/config/devices/entry[@name='localhost.localdomain']/template/entry[@name='dmz']/config"

    def test_get_panorama_base_path_template_stack(self):
        """Test _get_panorama_base_path with template-stack."""
        base = PanOSXPathMap._get_panorama_base_path({"template_stack": "stack1"})
        assert base == "/config/devices/entry[@name='localhost.localdomain']/template-stack/entry[@name='stack1']"


class TestMultiVsysXPath:
    """Test XPath generation for multi-vsys firewall configurations.
    
    Tests comprehensive vsys support (vsys1, vsys2, vsys3, vsys4) across all object types.
    Ensures backward compatibility when vsys not specified (defaults to vsys1).
    """

    # ============================================================================
    # Address Objects - Multi-vsys
    # ============================================================================

    def test_address_vsys1(self):
        """Address object in vsys1."""
        context = {"device_type": "FIREWALL", "vsys": "vsys1"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/config/devices/entry[@name='localhost.localdomain']" in xpath
        assert "/vsys/entry[@name='vsys1']" in xpath
        assert "/address/entry[@name='test-addr']" in xpath

    def test_address_vsys2(self):
        """Address object in vsys2."""
        context = {"device_type": "FIREWALL", "vsys": "vsys2"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/vsys/entry[@name='vsys2']" in xpath
        assert "/address/entry[@name='test-addr']" in xpath

    def test_address_vsys3(self):
        """Address object in vsys3."""
        context = {"device_type": "FIREWALL", "vsys": "vsys3"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/vsys/entry[@name='vsys3']" in xpath
        assert "/address/entry[@name='test-addr']" in xpath

    def test_address_vsys4(self):
        """Address object in vsys4."""
        context = {"device_type": "FIREWALL", "vsys": "vsys4"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/vsys/entry[@name='vsys4']" in xpath
        assert "/address/entry[@name='test-addr']" in xpath

    def test_address_list_vsys2(self):
        """Address list in vsys2."""
        context = {"device_type": "FIREWALL", "vsys": "vsys2"}
        xpath = PanOSXPathMap.build_xpath("address_list", device_context=context)
        
        assert "/vsys/entry[@name='vsys2']" in xpath
        assert xpath.endswith("/address")

    # ============================================================================
    # Service Objects - Multi-vsys
    # ============================================================================

    def test_service_vsys1(self):
        """Service object in vsys1."""
        context = {"device_type": "FIREWALL", "vsys": "vsys1"}
        xpath = PanOSXPathMap.build_xpath("service", "http-8080", context)
        
        assert "/vsys/entry[@name='vsys1']" in xpath
        assert "/service/entry[@name='http-8080']" in xpath

    def test_service_vsys2(self):
        """Service object in vsys2."""
        context = {"device_type": "FIREWALL", "vsys": "vsys2"}
        xpath = PanOSXPathMap.build_xpath("service", "http-8080", context)
        
        assert "/vsys/entry[@name='vsys2']" in xpath
        assert "/service/entry[@name='http-8080']" in xpath

    def test_service_vsys3(self):
        """Service object in vsys3."""
        context = {"device_type": "FIREWALL", "vsys": "vsys3"}
        xpath = PanOSXPathMap.build_xpath("service", "http-8080", context)
        
        assert "/vsys/entry[@name='vsys3']" in xpath
        assert "/service/entry[@name='http-8080']" in xpath

    def test_service_list_vsys3(self):
        """Service list in vsys3."""
        context = {"device_type": "FIREWALL", "vsys": "vsys3"}
        xpath = PanOSXPathMap.build_xpath("service_list", device_context=context)
        
        assert "/vsys/entry[@name='vsys3']" in xpath
        assert xpath.endswith("/service")

    # ============================================================================
    # Address Groups - Multi-vsys
    # ============================================================================

    def test_address_group_vsys1(self):
        """Address group in vsys1."""
        context = {"device_type": "FIREWALL", "vsys": "vsys1"}
        xpath = PanOSXPathMap.build_xpath("address_group", "web-servers", context)
        
        assert "/vsys/entry[@name='vsys1']" in xpath
        assert "/address-group/entry[@name='web-servers']" in xpath

    def test_address_group_vsys2(self):
        """Address group in vsys2."""
        context = {"device_type": "FIREWALL", "vsys": "vsys2"}
        xpath = PanOSXPathMap.build_xpath("address_group", "web-servers", context)
        
        assert "/vsys/entry[@name='vsys2']" in xpath
        assert "/address-group/entry[@name='web-servers']" in xpath

    def test_address_group_vsys4(self):
        """Address group in vsys4."""
        context = {"device_type": "FIREWALL", "vsys": "vsys4"}
        xpath = PanOSXPathMap.build_xpath("address_group", "web-servers", context)
        
        assert "/vsys/entry[@name='vsys4']" in xpath
        assert "/address-group/entry[@name='web-servers']" in xpath

    # ============================================================================
    # Service Groups - Multi-vsys
    # ============================================================================

    def test_service_group_vsys2(self):
        """Service group in vsys2."""
        context = {"device_type": "FIREWALL", "vsys": "vsys2"}
        xpath = PanOSXPathMap.build_xpath("service_group", "web-services", context)
        
        assert "/vsys/entry[@name='vsys2']" in xpath
        assert "/service-group/entry[@name='web-services']" in xpath

    def test_service_group_vsys3(self):
        """Service group in vsys3."""
        context = {"device_type": "FIREWALL", "vsys": "vsys3"}
        xpath = PanOSXPathMap.build_xpath("service_group", "web-services", context)
        
        assert "/vsys/entry[@name='vsys3']" in xpath
        assert "/service-group/entry[@name='web-services']" in xpath

    # ============================================================================
    # Security Rules - Multi-vsys
    # ============================================================================

    def test_security_policy_vsys1(self):
        """Security policy in vsys1."""
        context = {"device_type": "FIREWALL", "vsys": "vsys1"}
        xpath = PanOSXPathMap.build_xpath("security_policy", "allow-web", context)
        
        assert "/vsys/entry[@name='vsys1']" in xpath
        assert "/rulebase/security/rules/entry[@name='allow-web']" in xpath

    def test_security_policy_vsys2(self):
        """Security policy in vsys2."""
        context = {"device_type": "FIREWALL", "vsys": "vsys2"}
        xpath = PanOSXPathMap.build_xpath("security_policy", "allow-web", context)
        
        assert "/vsys/entry[@name='vsys2']" in xpath
        assert "/rulebase/security/rules/entry[@name='allow-web']" in xpath

    def test_security_policy_vsys3(self):
        """Security policy in vsys3."""
        context = {"device_type": "FIREWALL", "vsys": "vsys3"}
        xpath = PanOSXPathMap.build_xpath("security_policy", "allow-web", context)
        
        assert "/vsys/entry[@name='vsys3']" in xpath
        assert "/rulebase/security/rules/entry[@name='allow-web']" in xpath

    def test_security_policy_vsys4(self):
        """Security policy in vsys4."""
        context = {"device_type": "FIREWALL", "vsys": "vsys4"}
        xpath = PanOSXPathMap.build_xpath("security_policy", "allow-web", context)
        
        assert "/vsys/entry[@name='vsys4']" in xpath
        assert "/rulebase/security/rules/entry[@name='allow-web']" in xpath

    def test_security_policy_list_vsys2(self):
        """Security policy list in vsys2."""
        context = {"device_type": "FIREWALL", "vsys": "vsys2"}
        xpath = PanOSXPathMap.build_xpath("security_policy_list", device_context=context)
        
        assert "/vsys/entry[@name='vsys2']" in xpath
        assert xpath.endswith("/rulebase/security/rules")

    # ============================================================================
    # NAT Rules - Multi-vsys
    # ============================================================================

    def test_nat_policy_vsys1(self):
        """NAT policy in vsys1."""
        context = {"device_type": "FIREWALL", "vsys": "vsys1"}
        xpath = PanOSXPathMap.build_xpath("nat_policy", "outbound-nat", context)
        
        assert "/vsys/entry[@name='vsys1']" in xpath
        assert "/rulebase/nat/rules/entry[@name='outbound-nat']" in xpath

    def test_nat_policy_vsys2(self):
        """NAT policy in vsys2."""
        context = {"device_type": "FIREWALL", "vsys": "vsys2"}
        xpath = PanOSXPathMap.build_xpath("nat_policy", "outbound-nat", context)
        
        assert "/vsys/entry[@name='vsys2']" in xpath
        assert "/rulebase/nat/rules/entry[@name='outbound-nat']" in xpath

    def test_nat_policy_vsys3(self):
        """NAT policy in vsys3."""
        context = {"device_type": "FIREWALL", "vsys": "vsys3"}
        xpath = PanOSXPathMap.build_xpath("nat_policy", "outbound-nat", context)
        
        assert "/vsys/entry[@name='vsys3']" in xpath
        assert "/rulebase/nat/rules/entry[@name='outbound-nat']" in xpath

    def test_nat_policy_list_vsys4(self):
        """NAT policy list in vsys4."""
        context = {"device_type": "FIREWALL", "vsys": "vsys4"}
        xpath = PanOSXPathMap.build_xpath("nat_policy_list", device_context=context)
        
        assert "/vsys/entry[@name='vsys4']" in xpath
        assert xpath.endswith("/rulebase/nat/rules")

    # ============================================================================
    # Backward Compatibility - Default to vsys1
    # ============================================================================

    def test_default_vsys_when_not_specified(self):
        """Default to vsys1 when vsys not in context."""
        context = {"device_type": "FIREWALL"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        # Should default to vsys1
        assert "/vsys/entry[@name='vsys1']" in xpath
        assert "/address/entry[@name='test-addr']" in xpath

    def test_default_vsys_with_empty_context(self):
        """Default to vsys1 with empty context."""
        xpath = PanOSXPathMap.build_xpath("service", "test-svc")
        
        # Should default to vsys1
        assert "/vsys/entry[@name='vsys1']" in xpath
        assert "/service/entry[@name='test-svc']" in xpath

    def test_default_vsys_for_security_policy(self):
        """Default to vsys1 for security policy when vsys not specified."""
        context = {"device_type": "FIREWALL"}
        xpath = PanOSXPathMap.build_xpath("security_policy", "allow-all", context)
        
        assert "/vsys/entry[@name='vsys1']" in xpath
        assert "/rulebase/security/rules/entry[@name='allow-all']" in xpath

    def test_default_vsys_for_nat_policy(self):
        """Default to vsys1 for NAT policy when vsys not specified."""
        context = {"device_type": "FIREWALL"}
        xpath = PanOSXPathMap.build_xpath("nat_policy", "outbound", context)
        
        assert "/vsys/entry[@name='vsys1']" in xpath
        assert "/rulebase/nat/rules/entry[@name='outbound']" in xpath

    # ============================================================================
    # Panorama Ignores Vsys
    # ============================================================================

    def test_panorama_ignores_vsys_shared(self):
        """Panorama shared context ignores vsys parameter."""
        context = {"device_type": "PANORAMA", "vsys": "vsys2"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        # Should use shared path, not vsys
        assert xpath == "/config/shared/address/entry[@name='test-addr']"
        assert "/vsys/" not in xpath

    def test_panorama_ignores_vsys_device_group(self):
        """Panorama device-group context ignores vsys parameter."""
        context = {"device_type": "PANORAMA", "device_group": "production", "vsys": "vsys3"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        # Should use device-group path, not vsys
        assert "/device-group/entry[@name='production']" in xpath
        assert "/vsys/" not in xpath

    def test_panorama_ignores_vsys_template(self):
        """Panorama template context ignores vsys parameter."""
        context = {"device_type": "PANORAMA", "template": "dmz-template", "vsys": "vsys4"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        # Should use template path, not vsys
        assert "/template/entry[@name='dmz-template']/config" in xpath
        assert "/vsys/" not in xpath

    # ============================================================================
    # Invalid/Custom Vsys Names
    # ============================================================================

    def test_custom_vsys_name(self):
        """Support custom vsys names (non-standard)."""
        context = {"device_type": "FIREWALL", "vsys": "vsys-custom"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/vsys/entry[@name='vsys-custom']" in xpath
        assert "/address/entry[@name='test-addr']" in xpath

    def test_vsys_with_underscores(self):
        """Support vsys names with underscores."""
        context = {"device_type": "FIREWALL", "vsys": "vsys_tenant1"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/vsys/entry[@name='vsys_tenant1']" in xpath
        assert "/address/entry[@name='test-addr']" in xpath


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
