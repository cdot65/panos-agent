"""Tests for diff_engine.py - Configuration comparison and diff detection.

Comprehensive test suite covering:
- FieldChange creation and serialization
- ConfigDiff functionality
- compare_configs() with various scenarios
- compare_xml() for XML string comparison
- _values_equal() normalization logic
"""

import pytest

from src.core.diff_engine import (
    FieldChange,
    ConfigDiff,
    compare_configs,
    compare_xml,
    _values_equal,
)


class TestFieldChange:
    """Tests for FieldChange dataclass."""

    def test_field_change_creation(self):
        """Test creating a FieldChange."""
        change = FieldChange(
            field="ip-netmask",
            old_value="10.0.0.1/32",
            new_value="10.0.0.2/32",
            change_type="modified"
        )
        assert change.field == "ip-netmask"
        assert change.old_value == "10.0.0.1/32"
        assert change.new_value == "10.0.0.2/32"
        assert change.change_type == "modified"

    def test_field_change_to_dict(self):
        """Test converting FieldChange to dict."""
        change = FieldChange(
            field="description",
            old_value="Old desc",
            new_value="New desc",
            change_type="modified"
        )
        result = change.to_dict()
        assert result == {
            "field": "description",
            "old": "Old desc",
            "new": "New desc",
            "type": "modified",
        }

    def test_modified_change(self):
        """Test modified field change."""
        change = FieldChange(
            field="ip-netmask",
            old_value="10.0.0.1/32",
            new_value="10.0.0.2/32",
            change_type="modified"
        )
        assert change.change_type == "modified"
        assert change.old_value is not None
        assert change.new_value is not None

    def test_added_change(self):
        """Test added field change."""
        change = FieldChange(
            field="description",
            old_value=None,
            new_value="New description",
            change_type="added"
        )
        assert change.change_type == "added"
        assert change.old_value is None
        assert change.new_value == "New description"

    def test_removed_change(self):
        """Test removed field change."""
        change = FieldChange(
            field="tag",
            old_value=["Production"],
            new_value=None,
            change_type="removed"
        )
        assert change.change_type == "removed"
        assert change.old_value == ["Production"]
        assert change.new_value is None


class TestConfigDiff:
    """Tests for ConfigDiff dataclass."""

    def test_identical_configs(self):
        """Test ConfigDiff with no changes."""
        diff = ConfigDiff(
            object_name="web-1",
            object_type="address",
            changes=[]
        )
        assert diff.is_identical()
        assert not diff.has_changes()
        assert "No changes detected" in diff.summary()

    def test_single_field_change(self):
        """Test ConfigDiff with one field changed."""
        changes = [
            FieldChange("ip-netmask", "10.0.0.1/32", "10.0.0.2/32", "modified")
        ]
        diff = ConfigDiff(
            object_name="web-1",
            object_type="address",
            changes=changes
        )
        assert not diff.is_identical()
        assert diff.has_changes()
        assert "Changes detected" in diff.summary()
        assert "ip-netmask" in diff.summary()

    def test_multiple_field_changes(self):
        """Test ConfigDiff with multiple field changes."""
        changes = [
            FieldChange("ip-netmask", "10.0.0.1/32", "10.0.0.2/32", "modified"),
            FieldChange("description", "Old", "New", "modified"),
        ]
        diff = ConfigDiff(
            object_name="web-1",
            object_type="address",
            changes=changes
        )
        assert len(diff.changes) == 2
        summary = diff.summary()
        assert "ip-netmask" in summary
        assert "description" in summary

    def test_diff_summary_added_field(self):
        """Test summary format for added field."""
        changes = [
            FieldChange("description", None, "New description", "added")
        ]
        diff = ConfigDiff("web-1", "address", changes)
        summary = diff.summary()
        assert "+ description" in summary
        assert "New description" in summary

    def test_diff_summary_removed_field(self):
        """Test summary format for removed field."""
        changes = [
            FieldChange("description", "Old description", None, "removed")
        ]
        diff = ConfigDiff("web-1", "address", changes)
        summary = diff.summary()
        assert "- description" in summary
        assert "Old description" in summary

    def test_diff_to_dict(self):
        """Test converting ConfigDiff to dict."""
        changes = [
            FieldChange("ip-netmask", "10.0.0.1/32", "10.0.0.2/32", "modified")
        ]
        diff = ConfigDiff("web-1", "address", changes)
        result = diff.to_dict()
        assert result["name"] == "web-1"
        assert result["type"] == "address"
        assert result["is_identical"] is False
        assert len(result["changes"]) == 1


class TestCompareConfigs:
    """Tests for compare_configs() function."""

    def test_identical_address_objects(self):
        """Test comparing identical address objects."""
        config1 = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
            "description": "Web server",
        }
        config2 = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
            "description": "Web server",
        }
        diff = compare_configs(config1, config2)
        assert diff.is_identical()
        assert len(diff.changes) == 0

    def test_ip_address_change(self):
        """Test detecting IP address change."""
        desired = {
            "name": "web-1",
            "ip-netmask": "10.0.0.2/32",
        }
        actual = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
        }
        diff = compare_configs(desired, actual)
        assert diff.has_changes()
        assert len(diff.changes) == 1
        assert diff.changes[0].field == "ip-netmask"
        assert diff.changes[0].change_type == "modified"
        assert diff.changes[0].old_value == "10.0.0.1/32"
        assert diff.changes[0].new_value == "10.0.0.2/32"

    def test_description_change(self):
        """Test detecting description change."""
        desired = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
            "description": "Updated description",
        }
        actual = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
            "description": "Old description",
        }
        diff = compare_configs(desired, actual)
        assert diff.has_changes()
        assert len(diff.changes) == 1
        assert diff.changes[0].field == "description"

    def test_tag_addition(self):
        """Test detecting tag addition."""
        desired = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
            "tag": {"member": ["Production", "Web"]},
        }
        actual = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
        }
        diff = compare_configs(desired, actual)
        assert diff.has_changes()
        assert len(diff.changes) == 1
        assert diff.changes[0].field == "tag"
        assert diff.changes[0].change_type == "added"

    def test_tag_removal(self):
        """Test detecting tag removal."""
        desired = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
        }
        actual = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
            "tag": {"member": ["Production"]},
        }
        diff = compare_configs(desired, actual)
        assert diff.has_changes()
        assert len(diff.changes) == 1
        assert diff.changes[0].field == "tag"
        assert diff.changes[0].change_type == "removed"

    def test_tag_order_ignored(self):
        """Test that tag order doesn't matter."""
        desired = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
            "tag": {"member": ["Web", "Production"]},
        }
        actual = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
            "tag": {"member": ["Production", "Web"]},
        }
        diff = compare_configs(desired, actual)
        # Tags should be considered equal despite different order
        assert diff.is_identical()

    def test_field_added(self):
        """Test detecting newly added field."""
        desired = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
            "description": "New field",
        }
        actual = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
        }
        diff = compare_configs(desired, actual)
        assert diff.has_changes()
        assert any(c.change_type == "added" for c in diff.changes)

    def test_field_removed(self):
        """Test detecting removed field."""
        desired = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
        }
        actual = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
            "description": "Old field",
        }
        diff = compare_configs(desired, actual)
        assert diff.has_changes()
        assert any(c.change_type == "removed" for c in diff.changes)

    def test_multiple_changes(self):
        """Test detecting multiple changes."""
        desired = {
            "name": "web-1",
            "ip-netmask": "10.0.0.2/32",
            "description": "New description",
            "tag": {"member": ["Production"]},
        }
        actual = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
            "description": "Old description",
        }
        diff = compare_configs(desired, actual)
        assert diff.has_changes()
        # Should detect: IP change, description change, tag addition
        assert len(diff.changes) >= 2

    def test_nested_dict_comparison(self):
        """Test comparing nested dictionaries."""
        desired = {
            "name": "svc-1",
            "protocol": {"tcp": {"port": "8080"}},
        }
        actual = {
            "name": "svc-1",
            "protocol": {"tcp": {"port": "8080"}},
        }
        diff = compare_configs(desired, actual)
        assert diff.is_identical()

    def test_nested_dict_changes(self):
        """Test detecting changes in nested dicts."""
        desired = {
            "name": "svc-1",
            "protocol": {"tcp": {"port": "8080"}},
        }
        actual = {
            "name": "svc-1",
            "protocol": {"tcp": {"port": "80"}},
        }
        diff = compare_configs(desired, actual)
        assert diff.has_changes()

    def test_whitespace_normalization(self):
        """Test that whitespace differences are normalized."""
        desired = {
            "name": "web-1",
            "description": "Test description",
        }
        actual = {
            "name": "web-1",
            "description": "  Test description  ",
        }
        diff = compare_configs(desired, actual)
        # Whitespace should be normalized, configs considered identical
        assert diff.is_identical()

    def test_ignores_metadata_fields(self):
        """Test that metadata fields are ignored."""
        desired = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
        }
        actual = {
            "name": "web-1",
            "ip-netmask": "10.0.0.1/32",
            "@admin": "admin",
            "@dirtyId": "123",
            "@time": "2024/01/01",
        }
        diff = compare_configs(desired, actual)
        # Metadata fields should be ignored
        assert diff.is_identical()


class TestCompareXML:
    """Tests for compare_xml() function."""

    def test_xml_string_comparison(self):
        """Test comparing XML strings."""
        xml1 = '<entry name="web-1"><ip-netmask>10.0.0.1/32</ip-netmask></entry>'
        xml2 = '<entry name="web-1"><ip-netmask>10.0.0.1/32</ip-netmask></entry>'
        diff = compare_xml(xml1, xml2)
        assert diff.is_identical()

    def test_xml_with_changes(self):
        """Test detecting changes in XML."""
        xml1 = '<entry name="web-1"><ip-netmask>10.0.0.2/32</ip-netmask></entry>'
        xml2 = '<entry name="web-1"><ip-netmask>10.0.0.1/32</ip-netmask></entry>'
        diff = compare_xml(xml1, xml2)
        assert diff.has_changes()

    def test_malformed_xml_handling(self):
        """Test handling of malformed XML."""
        xml1 = '<entry name="web-1"><ip-netmask>10.0.0.1/32</ip-netmask>'  # Missing closing tag
        xml2 = '<entry name="web-1"><ip-netmask>10.0.0.1/32</ip-netmask></entry>'
        with pytest.raises(ValueError, match="XML parsing failed"):
            compare_xml(xml1, xml2)


class TestValuesEqual:
    """Tests for _values_equal() helper function."""

    def test_string_equality(self):
        """Test string comparison."""
        assert _values_equal("test", "test")
        assert not _values_equal("test1", "test2")

    def test_string_whitespace_handling(self):
        """Test that whitespace is normalized."""
        assert _values_equal("test", "  test  ")
        assert _values_equal("  test", "test  ")

    def test_list_equality_order_independent(self):
        """Test that list order doesn't matter."""
        assert _values_equal(["a", "b", "c"], ["c", "b", "a"])
        assert _values_equal(["Production", "Web"], ["Web", "Production"])

    def test_list_inequality(self):
        """Test detecting different list contents."""
        assert not _values_equal(["a", "b"], ["a", "c"])
        assert not _values_equal(["a", "b"], ["a", "b", "c"])

    def test_dict_equality(self):
        """Test nested dict comparison."""
        dict1 = {"key1": "value1", "key2": "value2"}
        dict2 = {"key1": "value1", "key2": "value2"}
        assert _values_equal(dict1, dict2)

    def test_dict_inequality(self):
        """Test detecting different dict contents."""
        dict1 = {"key1": "value1"}
        dict2 = {"key1": "value2"}
        assert not _values_equal(dict1, dict2)

    def test_none_vs_empty_string(self):
        """Test that None and empty string are considered equal."""
        assert _values_equal(None, "")
        assert _values_equal("", None)
        assert _values_equal(None, None)
        assert _values_equal("", "")

    def test_none_vs_value(self):
        """Test that None is not equal to actual values."""
        assert not _values_equal(None, "value")
        assert not _values_equal("value", None)

    def test_mixed_types(self):
        """Test comparing different types."""
        assert not _values_equal("123", 123)
        assert not _values_equal([1, 2], "1,2")


class TestIntegrationScenarios:
    """Integration tests with realistic PAN-OS configurations."""

    def test_realistic_address_object_unchanged(self):
        """Test realistic address object with no changes."""
        config = {
            "name": "corp-web-server",
            "@type": "address",
            "ip-netmask": "192.168.1.100/32",
            "description": "Corporate web server in DMZ",
            "tag": {"member": ["Production", "Web", "DMZ"]},
        }
        diff = compare_configs(config, config)
        assert diff.is_identical()

    def test_realistic_address_object_ip_change(self):
        """Test realistic address object with IP change."""
        desired = {
            "name": "corp-web-server",
            "@type": "address",
            "ip-netmask": "192.168.1.101/32",
            "description": "Corporate web server in DMZ",
            "tag": {"member": ["Production", "Web", "DMZ"]},
        }
        actual = {
            "name": "corp-web-server",
            "@type": "address",
            "ip-netmask": "192.168.1.100/32",
            "description": "Corporate web server in DMZ",
            "tag": {"member": ["Production", "Web", "DMZ"]},
        }
        diff = compare_configs(desired, actual)
        assert diff.has_changes()
        assert len(diff.changes) == 1
        assert diff.changes[0].field == "ip-netmask"
        summary = diff.summary()
        assert "192.168.1.100/32 → 192.168.1.101/32" in summary

    def test_realistic_service_object(self):
        """Test realistic service object comparison."""
        desired = {
            "name": "custom-https",
            "@type": "service",
            "protocol": {"tcp": {"port": "8443"}},
            "description": "Custom HTTPS port",
        }
        actual = {
            "name": "custom-https",
            "@type": "service",
            "protocol": {"tcp": {"port": "8443"}},
            "description": "Custom HTTPS port",
        }
        diff = compare_configs(desired, actual)
        assert diff.is_identical()

