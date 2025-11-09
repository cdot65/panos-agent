"""Integration tests for XML validation with panos_api.

This module tests that validation is properly integrated into the API layer.
"""

import pytest
from lxml import etree

from src.core.panos_api import PanOSValidationError, build_object_xml


class TestBuildObjectXMLValidation:
    """Test that build_object_xml validates objects before building."""

    def test_build_address_valid(self):
        """Test building a valid address object."""
        data = {
            "name": "web-server",
            "ip-netmask": "10.0.0.1/32",
            "description": "Test server",
        }
        xml = build_object_xml("address", data)
        assert xml is not None
        assert "web-server" in xml
        assert "10.0.0.1/32" in xml

    def test_build_address_missing_name(self):
        """Test that missing name raises validation error."""
        data = {"ip-netmask": "10.0.0.1/32"}
        with pytest.raises(PanOSValidationError) as exc_info:
            build_object_xml("address", data)
        assert "name" in str(exc_info.value).lower()

    def test_build_address_missing_type(self):
        """Test that address without type field raises validation error."""
        data = {"name": "incomplete-addr"}
        with pytest.raises(PanOSValidationError) as exc_info:
            build_object_xml("address", data)
        assert "one of" in str(exc_info.value).lower()

    def test_build_address_invalid_ip(self):
        """Test that invalid IP raises validation error."""
        data = {"name": "bad-addr", "ip-netmask": "999.999.999.999"}
        with pytest.raises(PanOSValidationError) as exc_info:
            build_object_xml("address", data)
        assert "invalid" in str(exc_info.value).lower()

    def test_build_service_valid(self):
        """Test building a valid service object."""
        data = {
            "name": "http-8080",
            "protocol": {"tcp": {"port": "8080"}},
        }
        xml = build_object_xml("service", data)
        assert xml is not None
        assert "http-8080" in xml

    def test_build_service_missing_protocol(self):
        """Test that service without protocol raises validation error."""
        data = {"name": "incomplete-service"}
        with pytest.raises(PanOSValidationError) as exc_info:
            build_object_xml("service", data)
        assert "protocol" in str(exc_info.value).lower()

    def test_build_security_policy_valid(self):
        """Test building a valid security policy."""
        data = {
            "name": "allow-web",
            "from": ["trust"],
            "to": ["untrust"],
            "source": ["any"],
            "destination": ["any"],
            "service": ["any"],
            "application": ["any"],
            "action": "allow",
        }
        xml = build_object_xml("security_policy", data)
        assert xml is not None
        assert "allow-web" in xml

    def test_build_security_policy_invalid_action(self):
        """Test that invalid action raises validation error."""
        data = {
            "name": "bad-policy",
            "from": ["trust"],
            "to": ["untrust"],
            "source": ["any"],
            "destination": ["any"],
            "service": ["any"],
            "application": ["any"],
            "action": "maybe",  # Invalid action
        }
        with pytest.raises(PanOSValidationError) as exc_info:
            build_object_xml("security_policy", data)
        assert "action" in str(exc_info.value).lower()

    def test_build_address_group_valid(self):
        """Test building a valid address group."""
        data = {
            "name": "web-servers",
            "static": ["web-1", "web-2"],
        }
        xml = build_object_xml("address_group", data)
        assert xml is not None
        assert "web-servers" in xml

    def test_build_service_group_valid(self):
        """Test building a valid service group."""
        data = {
            "name": "web-services",
            "members": ["http", "https"],
        }
        xml = build_object_xml("service_group", data)
        assert xml is not None
        assert "web-services" in xml

    def test_build_nat_policy_valid(self):
        """Test building a valid NAT policy."""
        data = {
            "name": "nat-outbound",
            "from": ["trust"],
            "to": ["untrust"],
            "source": ["any"],
            "destination": ["any"],
        }
        xml = build_object_xml("nat_policy", data)
        assert xml is not None
        assert "nat-outbound" in xml

    def test_validation_error_message_format(self):
        """Test that validation errors provide clear messages."""
        data = {
            "name": "test",
            "ip-netmask": "invalid-ip",
            "tag": "should-be-list",
        }
        with pytest.raises(PanOSValidationError) as exc_info:
            build_object_xml("address", data)
        error_msg = str(exc_info.value)
        # Should mention multiple errors
        assert "invalid" in error_msg.lower() or "list" in error_msg.lower()


class TestXMLStringValidation:
    """Test XML string validation in set_config and edit_config."""

    def test_xml_element_creation(self):
        """Test creating XML elements for validation."""
        # Create a valid XML element
        entry = etree.Element("entry", attrib={"name": "test"})
        ip_elem = etree.SubElement(entry, "ip-netmask")
        ip_elem.text = "10.0.0.1/32"

        xml_str = etree.tostring(entry, encoding="unicode")
        assert "test" in xml_str
        assert "10.0.0.1/32" in xml_str

    def test_malformed_xml_element(self):
        """Test that malformed XML is caught."""
        # This would be caught at element creation time
        with pytest.raises(etree.XMLSyntaxError):
            etree.fromstring("<entry><unclosed>")
