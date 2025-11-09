"""Tests for diff engine functionality."""

import pytest
from lxml import etree

from src.core.diff_engine import (
    ConfigDiff,
    FieldChange,
    compare_configs,
    compare_xml,
    _values_equal,
)


class TestFieldChange:
    """Tests for FieldChange dataclass."""

    def test_field_change_creation(self):
        """Test creating a FieldChange instance."""
        change = FieldChange(
            field="ip-netmask",
            old_value="10.0.0.1/32",
            new_value="10.0.0.2/32",
            change_type="modified",
        )
        assert change.field == "ip-netmask"
        assert change.old_value == "10.0.0.1/32"
        assert change.new_value == "10.0.0.2/32"
        assert change.change_type == "modified"

    def test_field_change_to_dict(self):
        """Test converting FieldChange to dictionary."""
        change = FieldChange(
            field="description",
            old_value="Old desc",
            new_value="New desc",
            change_type="modified",
        )
        result = change.to_dict()
        assert result == {
            "field": "description",
            "old": "Old desc",
            "new": "New desc",
            "type": "modified",
        }

    def test_modified_change(self):
        """Test modified change type."""
        change = FieldChange(
            field="ip-netmask", old_value="10.0.0.1/32", new_value="10.0.0.2/32", change_type="modified"
        )
        assert change.change_type == "modified"

    def test_added_change(self):
        """Test added change type."""
        change = FieldChange(
            field="description", old_value=None, new_value="New description", change_type="added"
        )
        assert change.change_type == "added"
        assert change.old_value is None

    def test_removed_change(self):
        """Test removed change type."""
        change = FieldChange(
            field="description", old_value="Old description", new_value=None, change_type="removed"
        )
        assert change.change_type == "removed"
        assert change.new_value is None


class TestConfigDiff:
    """Tests for ConfigDiff dataclass."""

    def test_identical_configs(self):
        """Test ConfigDiff with no changes."""
        diff = ConfigDiff(object_name="test", object_type="address", changes=[])
        assert diff.is_identical() is True
        assert diff.has_changes() is False

    def test_single_field_change(self):
        """Test ConfigDiff with single field change."""
        change = FieldChange(
            field="ip-netmask", old_value="10.0.0.1/32", new_value="10.0.0.2/32", change_type="modified"
        )
        diff = ConfigDiff(object_name="test", object_type="address", changes=[change])
        assert diff.is_identical() is False
        assert diff.has_changes() is True
        assert len(diff.changes) == 1

    def test_multiple_field_changes(self):
        """Test ConfigDiff with multiple field changes."""
        changes = [
            FieldChange(field="ip-netmask", old_value="10.0.0.1/32", new_value="10.0.0.2/32", change_type="modified"),
            FieldChange(field="description", old_value="Old", new_value="New", change_type="modified"),
        ]
        diff = ConfigDiff(object_name="test", object_type="address", changes=changes)
        assert diff.has_changes() is True
        assert len(diff.changes) == 2

    def test_diff_summary(self):
        """Test generating human-readable summary."""
        changes = [
            FieldChange(field="ip-netmask", old_value="10.0.0.1/32", new_value="10.0.0.2/32", change_type="modified"),
            FieldChange(field="description", old_value=None, new_value="New desc", change_type="added"),
        ]
        diff = ConfigDiff(object_name="web-server", object_type="address", changes=changes)
        summary = diff.summary()
        assert "web-server" in summary
        assert "ip-netmask" in summary
        assert "10.0.0.1/32 → 10.0.0.2/32" in summary
        assert "description" in summary
        assert "New desc" in summary

    def test_diff_to_dict(self):
        """Test converting ConfigDiff to dictionary."""
        change = FieldChange(
            field="ip-netmask", old_value="10.0.0.1/32", new_value="10.0.0.2/32", change_type="modified"
        )
        diff = ConfigDiff(object_name="test", object_type="address", changes=[change])
        result = diff.to_dict()
        assert result["name"] == "test"
        assert result["type"] == "address"
        assert result["is_identical"] is False
        assert len(result["changes"]) == 1


class TestCompareConfigs:
    """Tests for compare_configs function."""

    def test_identical_address_objects(self):
        """Test comparing identical address objects."""
        desired = {"name": "web-1", "ip-netmask": "10.0.0.1/32", "description": "Web server"}
        actual = {"name": "web-1", "ip-netmask": "10.0.0.1/32", "description": "Web server"}
        diff = compare_configs(desired, actual)
        assert diff.is_identical() is True
        assert len(diff.changes) == 0

    def test_ip_address_change(self):
        """Test detecting IP address change."""
        desired = {"name": "web-1", "ip-netmask": "10.0.0.2/32"}
        actual = {"name": "web-1", "ip-netmask": "10.0.0.1/32"}
        diff = compare_configs(desired, actual)
        assert diff.is_identical() is False
        assert len(diff.changes) == 1
        assert diff.changes[0].field == "ip-netmask"
        assert diff.changes[0].old_value == "10.0.0.1/32"
        assert diff.changes[0].new_value == "10.0.0.2/32"
        assert diff.changes[0].change_type == "modified"

    def test_description_change(self):
        """Test detecting description change."""
        desired = {"name": "web-1", "description": "New description"}
        actual = {"name": "web-1", "description": "Old description"}
        diff = compare_configs(desired, actual)
        assert diff.is_identical() is False
        assert len(diff.changes) == 1
        assert diff.changes[0].field == "description"
        assert diff.changes[0].change_type == "modified"

    def test_tag_addition(self):
        """Test detecting tag addition."""
        desired = {"name": "web-1", "tag": {"member": ["Production", "Web"]}}
        actual = {"name": "web-1", "tag": {"member": ["Production"]}}
        diff = compare_configs(desired, actual)
        assert diff.is_identical() is False
        # Tag changes are detected as modified (not added) since tag field exists
        assert len(diff.changes) >= 1

    def test_tag_removal(self):
        """Test detecting tag removal."""
        desired = {"name": "web-1", "tag": {"member": ["Production"]}}
        actual = {"name": "web-1", "tag": {"member": ["Production", "Web"]}}
        diff = compare_configs(desired, actual)
        assert diff.is_identical() is False
        assert len(diff.changes) >= 1

    def test_tag_order_ignored(self):
        """Test that tag order doesn't matter (tags in different order = same)."""
        desired = {"name": "web-1", "tag": {"member": ["Production", "Web", "DMZ"]}}
        actual = {"name": "web-1", "tag": {"member": ["DMZ", "Web", "Production"]}}
        diff = compare_configs(desired, actual)
        assert diff.is_identical() is True

    def test_field_added(self):
        """Test detecting field addition."""
        desired = {"name": "web-1", "ip-netmask": "10.0.0.1/32", "description": "New field"}
        actual = {"name": "web-1", "ip-netmask": "10.0.0.1/32"}
        diff = compare_configs(desired, actual)
        assert diff.is_identical() is False
        assert len(diff.changes) == 1
        assert diff.changes[0].field == "description"
        assert diff.changes[0].change_type == "added"
        assert diff.changes[0].old_value is None

    def test_field_removed(self):
        """Test detecting field removal."""
        desired = {"name": "web-1", "ip-netmask": "10.0.0.1/32"}
        actual = {"name": "web-1", "ip-netmask": "10.0.0.1/32", "description": "Old field"}
        diff = compare_configs(desired, actual)
        assert diff.is_identical() is False
        assert len(diff.changes) == 1
        assert diff.changes[0].field == "description"
        assert diff.changes[0].change_type == "removed"
        assert diff.changes[0].new_value is None

    def test_multiple_changes(self):
        """Test detecting multiple field changes."""
        desired = {"name": "web-1", "ip-netmask": "10.0.0.2/32", "description": "New desc"}
        actual = {"name": "web-1", "ip-netmask": "10.0.0.1/32", "description": "Old desc"}
        diff = compare_configs(desired, actual)
        assert diff.is_identical() is False
        assert len(diff.changes) == 2
        change_fields = {c.field for c in diff.changes}
        assert "ip-netmask" in change_fields
        assert "description" in change_fields

    def test_nested_dict_comparison(self):
        """Test comparing nested dictionaries."""
        desired = {"name": "web-1", "tag": {"member": ["Production"], "color": "blue"}}
        actual = {"name": "web-1", "tag": {"member": ["Production"], "color": "red"}}
        diff = compare_configs(desired, actual)
        assert diff.is_identical() is False
        # Nested dict changes are detected
        assert len(diff.changes) >= 1

    def test_list_comparison(self):
        """Test comparing lists (order-independent)."""
        desired = {"name": "web-1", "tags": ["Production", "Web"]}
        actual = {"name": "web-1", "tags": ["Web", "Production"]}
        diff = compare_configs(desired, actual)
        assert diff.is_identical() is True

    def test_whitespace_normalization(self):
        """Test that whitespace differences are ignored."""
        desired = {"name": "web-1", "description": "Web server"}
        actual = {"name": "web-1", "description": "  Web server  "}
        diff = compare_configs(desired, actual)
        assert diff.is_identical() is True

    def test_none_vs_empty_string(self):
        """Test that None and empty string are treated as equal."""
        desired = {"name": "web-1", "description": ""}
        actual = {"name": "web-1", "description": None}
        diff = compare_configs(desired, actual)
        assert diff.is_identical() is True

    def test_address_group_static_members(self):
        """Test comparing address group static members."""
        desired = {"name": "web-group", "static": {"member": ["web-1", "web-2"]}}
        actual = {"name": "web-group", "static": {"member": ["web-2", "web-1"]}}
        diff = compare_configs(desired, actual)
        assert diff.is_identical() is True

    def test_service_object_comparison(self):
        """Test comparing service objects."""
        desired = {"name": "http", "protocol": {"tcp": {"port": "80"}}}
        actual = {"name": "http", "protocol": {"tcp": {"port": "80"}}}
        diff = compare_configs(desired, actual)
        assert diff.is_identical() is True

    def test_service_object_port_change(self):
        """Test detecting service port change."""
        desired = {"name": "http", "protocol": {"tcp": {"port": "8080"}}}
        actual = {"name": "http", "protocol": {"tcp": {"port": "80"}}}
        diff = compare_configs(desired, actual)
        assert diff.is_identical() is False
        assert len(diff.changes) >= 1


class TestCompareXML:
    """Tests for compare_xml function."""

    def test_xml_string_comparison(self):
        """Test comparing XML strings."""
        desired_xml = '<entry name="web-1"><ip-netmask>10.0.0.1/32</ip-netmask></entry>'
        actual_xml = '<entry name="web-1"><ip-netmask>10.0.0.1/32</ip-netmask></entry>'
        diff = compare_xml(desired_xml, actual_xml)
        assert diff.is_identical() is True

    def test_xml_string_with_changes(self):
        """Test comparing XML strings with changes."""
        desired_xml = '<entry name="web-1"><ip-netmask>10.0.0.2/32</ip-netmask></entry>'
        actual_xml = '<entry name="web-1"><ip-netmask>10.0.0.1/32</ip-netmask></entry>'
        diff = compare_xml(desired_xml, actual_xml)
        assert diff.is_identical() is False
        assert len(diff.changes) >= 1


class TestValuesEqual:
    """Tests for _values_equal helper function."""

    def test_string_equality(self):
        """Test string comparison."""
        assert _values_equal("test", "test") is True
        assert _values_equal("test", "different") is False

    def test_list_equality_order_independent(self):
        """Test that list order doesn't matter."""
        assert _values_equal(["a", "b", "c"], ["c", "b", "a"]) is True
        assert _values_equal(["a", "b"], ["a", "b", "c"]) is False

    def test_dict_equality(self):
        """Test dictionary comparison."""
        assert _values_equal({"a": 1, "b": 2}, {"b": 2, "a": 1}) is True
        assert _values_equal({"a": 1}, {"a": 2}) is False

    def test_none_vs_empty(self):
        """Test None vs empty string handling."""
        assert _values_equal(None, "") is True
        assert _values_equal("", None) is True
        assert _values_equal(None, None) is True
        assert _values_equal("", "") is True

    def test_whitespace_handling(self):
        """Test whitespace normalization."""
        assert _values_equal("  test  ", "test") is True
        assert _values_equal("test\n", "test") is True

    def test_nested_dict_comparison(self):
        """Test nested dictionary comparison."""
        dict1 = {"tag": {"member": ["a", "b"]}}
        dict2 = {"tag": {"member": ["b", "a"]}}
        assert _values_equal(dict1, dict2) is True

    def test_list_with_dicts(self):
        """Test list containing dictionaries."""
        list1 = [{"name": "a"}, {"name": "b"}]
        list2 = [{"name": "b"}, {"name": "a"}]
        assert _values_equal(list1, list2) is True

