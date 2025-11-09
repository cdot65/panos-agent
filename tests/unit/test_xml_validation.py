"""Unit tests for XML validation functionality.

This module tests the pre-submission validation of PAN-OS configuration objects.
"""

from src.core.xml_validation import (
    ValidationResult,
    extract_object_type_from_xpath,
    validate_action,
    validate_fqdn,
    validate_ip_cidr,
    validate_ip_range,
    validate_object_structure,
    validate_port_range,
    validate_protocol,
    validate_xml_string,
    validate_yes_no,
)

# ============================================================================
# Valid Objects Tests (5 tests)
# ============================================================================


def test_valid_address_object():
    """Test validation of a valid address object."""
    data = {
        "name": "web-server",
        "ip-netmask": "10.0.0.1/32",
        "description": "Web server",
        "tag": ["Production", "Web"],
    }
    result = validate_object_structure("address", data)
    assert result.is_valid
    assert len(result.errors) == 0


def test_valid_service_object():
    """Test validation of a valid service object."""
    data = {
        "name": "http-8080",
        "protocol": {"tcp": {"port": "8080"}},
        "description": "HTTP on 8080",
    }
    result = validate_object_structure("service", data)
    assert result.is_valid
    assert len(result.errors) == 0


def test_valid_security_policy():
    """Test validation of a valid security policy."""
    data = {
        "name": "allow-web",
        "from": ["trust"],
        "to": ["untrust"],
        "source": ["any"],
        "destination": ["any"],
        "service": ["application-default"],
        "application": ["web-browsing"],
        "action": "allow",
        "log-end": "yes",
    }
    result = validate_object_structure("security_policy", data)
    assert result.is_valid
    assert len(result.errors) == 0


def test_valid_address_group():
    """Test validation of a valid address group."""
    data = {
        "name": "web-servers",
        "static": ["web-1", "web-2", "web-3"],
        "description": "All web servers",
        "tag": ["Production"],
    }
    result = validate_object_structure("address_group", data)
    assert result.is_valid
    assert len(result.errors) == 0


def test_valid_service_group():
    """Test validation of a valid service group."""
    data = {
        "name": "web-services",
        "members": ["http", "https"],
        "tag": ["Web"],
    }
    result = validate_object_structure("service_group", data)
    assert result.is_valid
    assert len(result.errors) == 0


# ============================================================================
# Missing Required Fields Tests (5 tests)
# ============================================================================


def test_address_missing_name():
    """Test that missing name field is caught."""
    data = {"ip-netmask": "10.0.0.1/32"}
    result = validate_object_structure("address", data)
    assert not result.is_valid
    assert any("name" in error.lower() for error in result.errors)


def test_address_missing_type():
    """Test that address without type field is caught."""
    data = {"name": "incomplete-addr"}
    result = validate_object_structure("address", data)
    assert not result.is_valid
    assert any("one of" in error.lower() for error in result.errors)


def test_service_missing_protocol():
    """Test that service without protocol is caught."""
    data = {"name": "incomplete-service"}
    result = validate_object_structure("service", data)
    assert not result.is_valid
    assert any("protocol" in error.lower() for error in result.errors)


def test_policy_missing_zones():
    """Test that security policy without zones is caught."""
    data = {
        "name": "incomplete-policy",
        "source": ["any"],
        "destination": ["any"],
        "service": ["any"],
        "application": ["any"],
        "action": "allow",
    }
    result = validate_object_structure("security_policy", data)
    assert not result.is_valid
    # Should be missing 'from' and 'to'
    assert any("from" in error.lower() for error in result.errors)
    assert any("to" in error.lower() for error in result.errors)


def test_policy_missing_action():
    """Test that security policy without action is caught."""
    data = {
        "name": "incomplete-policy",
        "from": ["trust"],
        "to": ["untrust"],
        "source": ["any"],
        "destination": ["any"],
        "service": ["any"],
        "application": ["any"],
    }
    result = validate_object_structure("security_policy", data)
    assert not result.is_valid
    assert any("action" in error.lower() for error in result.errors)


# ============================================================================
# Invalid Field Types and Values Tests (7 tests)
# ============================================================================


def test_invalid_ip_format():
    """Test that invalid IP format is caught."""
    data = {"name": "bad-addr", "ip-netmask": "999.999.999.999"}
    result = validate_object_structure("address", data)
    assert not result.is_valid
    assert any("invalid" in error.lower() for error in result.errors)


def test_invalid_port_range():
    """Test that invalid port range is caught."""
    # Port too high
    is_valid, error = validate_port_range("99999")
    assert not is_valid
    assert "65535" in error


def test_invalid_fqdn():
    """Test that invalid FQDN is caught."""
    is_valid, error = validate_fqdn("not a valid domain")
    assert not is_valid
    assert "fqdn" in error.lower()


def test_tag_not_list():
    """Test that tag field must be a list."""
    data = {
        "name": "test-addr",
        "ip-netmask": "10.0.0.1/32",
        "tag": "Production",  # Should be a list
    }
    result = validate_object_structure("address", data)
    assert not result.is_valid
    assert any("tag" in error.lower() and "list" in error.lower() for error in result.errors)


def test_members_not_list():
    """Test that members field must be a list."""
    data = {
        "name": "test-group",
        "members": "single-service",  # Should be a list
    }
    result = validate_object_structure("service_group", data)
    assert not result.is_valid
    assert any("members" in error.lower() and "list" in error.lower() for error in result.errors)


def test_invalid_action_value():
    """Test that invalid action values are caught."""
    is_valid, error = validate_action("maybe")
    assert not is_valid
    assert "action" in error.lower()


def test_invalid_protocol_value():
    """Test that invalid protocol values are caught."""
    is_valid, error = validate_protocol("http")  # Should be tcp/udp/icmp
    assert not is_valid
    assert "protocol" in error.lower()


# ============================================================================
# XML String Validation Tests (5 tests)
# ============================================================================


def test_valid_xml_string():
    """Test validation of well-formed XML."""
    xml = '<entry name="test"><ip-netmask>10.0.0.1/32</ip-netmask></entry>'
    result = validate_xml_string(xml, "address")
    assert result.is_valid
    assert len(result.errors) == 0


def test_malformed_xml():
    """Test that malformed XML is caught."""
    xml = "<entry name='test'><ip-netmask>10.0.0.1/32"  # Missing closing tags
    result = validate_xml_string(xml)
    assert not result.is_valid
    assert any("malformed" in error.lower() for error in result.errors)


def test_missing_closing_tag():
    """Test that missing closing tag is caught."""
    xml = "<entry name='test'><ip-netmask>10.0.0.1/32</entry>"  # Missing </ip-netmask>
    result = validate_xml_string(xml)
    assert not result.is_valid
    assert any("malformed" in error.lower() or "xml" in error.lower() for error in result.errors)


def test_entry_missing_name_attribute():
    """Test that entry without name attribute is caught."""
    xml = "<entry><ip-netmask>10.0.0.1/32</ip-netmask></entry>"
    result = validate_xml_string(xml, "address")
    assert not result.is_valid
    assert any("name" in error.lower() for error in result.errors)


def test_empty_xml_string():
    """Test that empty XML string is caught."""
    result = validate_xml_string("")
    assert not result.is_valid
    assert any("empty" in error.lower() for error in result.errors)


# ============================================================================
# Error Message Tests (3 tests)
# ============================================================================


def test_clear_error_message_format():
    """Test that error messages are clear and helpful."""
    data = {"name": "test", "ip-netmask": "invalid-ip"}
    result = validate_object_structure("address", data)
    assert not result.is_valid
    assert len(result.errors) > 0
    # Error should mention what's wrong
    error_text = " ".join(result.errors)
    assert "invalid" in error_text.lower()


def test_multiple_errors_reported():
    """Test that multiple errors are all reported."""
    data = {
        # Missing name
        "ip-netmask": "999.999.999.999",  # Invalid IP
        "tag": "not-a-list",  # Wrong type
    }
    result = validate_object_structure("address", data)
    assert not result.is_valid
    # Should have multiple errors
    assert len(result.errors) >= 2


def test_warning_messages():
    """Test that warnings are generated for suspicious configurations."""
    data = {
        "name": "test-addr",
        "ip-netmask": "10.0.0.1/32",
        "tag": [],  # Empty list - should warn
    }
    result = validate_object_structure("address", data)
    # Should be valid but with warnings
    assert result.is_valid
    assert len(result.warnings) > 0


# ============================================================================
# Field Validator Tests (5 tests)
# ============================================================================


def test_validate_ip_cidr():
    """Test IP CIDR validation."""
    # Valid cases
    assert validate_ip_cidr("10.0.0.0/24")[0]
    assert validate_ip_cidr("192.168.1.1/32")[0]
    assert validate_ip_cidr("0.0.0.0/0")[0]

    # Invalid cases
    assert not validate_ip_cidr("999.999.999.999/24")[0]
    assert not validate_ip_cidr("10.0.0.0/99")[0]
    assert not validate_ip_cidr("not-an-ip")[0]


def test_validate_ip_range():
    """Test IP range validation."""
    # Valid cases
    assert validate_ip_range("10.0.0.1-10.0.0.100")[0]
    assert validate_ip_range("192.168.1.1-192.168.1.254")[0]

    # Invalid cases
    assert not validate_ip_range("10.0.0.100-10.0.0.1")[0]  # Reversed
    assert not validate_ip_range("10.0.0.1")[0]  # Missing dash
    assert not validate_ip_range("invalid-range")[0]


def test_validate_port_range():
    """Test port range validation."""
    # Valid cases
    assert validate_port_range("80")[0]
    assert validate_port_range("8080-8090")[0]
    assert validate_port_range("80,443,8080")[0]
    assert validate_port_range("80,443,8080-8090")[0]

    # Invalid cases
    assert not validate_port_range("99999")[0]  # Too high
    assert not validate_port_range("0")[0]  # Too low
    assert not validate_port_range("8090-8080")[0]  # Reversed
    assert not validate_port_range("not-a-port")[0]


def test_validate_yes_no():
    """Test yes/no field validation."""
    # Valid cases
    assert validate_yes_no("yes")[0]
    assert validate_yes_no("no")[0]
    assert validate_yes_no("YES")[0]  # Case insensitive

    # Invalid cases
    assert not validate_yes_no("true")[0]
    assert not validate_yes_no("maybe")[0]


def test_validate_fqdn():
    """Test FQDN validation."""
    # Valid cases
    assert validate_fqdn("example.com")[0]
    assert validate_fqdn("sub.example.com")[0]
    assert validate_fqdn("*.example.com")[0]  # Wildcard allowed

    # Invalid cases
    assert not validate_fqdn("not a domain")[0]
    assert not validate_fqdn("missing-tld")[0]
    assert not validate_fqdn("-.example.com")[0]


# ============================================================================
# XPath Extraction Tests (2 tests)
# ============================================================================


def test_extract_object_type_from_xpath_address():
    """Test extracting object type from address XPath."""
    xpath = "/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address/entry[@name='test']"
    obj_type = extract_object_type_from_xpath(xpath)
    assert obj_type == "address"


def test_extract_object_type_from_xpath_policy():
    """Test extracting object type from security policy XPath."""
    xpath = "/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/rulebase/security/rules/entry[@name='test']"
    obj_type = extract_object_type_from_xpath(xpath)
    assert obj_type == "security_policy"


# ============================================================================
# Integration Tests (3 tests)
# ============================================================================


def test_validation_result_merge():
    """Test merging validation results."""
    result1 = ValidationResult()
    result1.add_error("Error 1")
    result1.add_warning("Warning 1")

    result2 = ValidationResult()
    result2.add_error("Error 2")
    result2.add_warning("Warning 2")

    result1.merge(result2)

    assert not result1.is_valid
    assert len(result1.errors) == 2
    assert len(result1.warnings) == 2


def test_underscore_hyphen_field_normalization():
    """Test that both underscore and hyphen field names work."""
    # Test with hyphens
    data1 = {"name": "test", "ip-netmask": "10.0.0.1/32"}
    result1 = validate_object_structure("address", data1)
    assert result1.is_valid

    # Test with underscores
    data2 = {"name": "test", "ip_netmask": "10.0.0.1/32"}
    result2 = validate_object_structure("address", data2)
    assert result2.is_valid


def test_object_type_normalization():
    """Test that object type normalization works."""
    data = {
        "name": "test-addr",
        "ip-netmask": "10.0.0.1/32",
    }

    # Both should work
    result1 = validate_object_structure("address", data)
    result2 = validate_object_structure("address", data)

    assert result1.is_valid
    assert result2.is_valid


# ============================================================================
# NAT Policy Tests (2 tests)
# ============================================================================


def test_valid_nat_policy():
    """Test validation of a valid NAT policy."""
    data = {
        "name": "nat-outbound",
        "from": ["trust"],
        "to": ["untrust"],
        "source": ["10.0.0.0/24"],
        "destination": ["any"],
        "service": "any",
        "nat-type": "ipv4",
    }
    result = validate_object_structure("nat_policy", data)
    assert result.is_valid
    assert len(result.errors) == 0


def test_nat_policy_missing_zones():
    """Test that NAT policy without zones is caught."""
    data = {
        "name": "incomplete-nat",
        "source": ["any"],
        "destination": ["any"],
    }
    result = validate_object_structure("nat_policy", data)
    assert not result.is_valid
    assert any("from" in error.lower() for error in result.errors)
    assert any("to" in error.lower() for error in result.errors)
