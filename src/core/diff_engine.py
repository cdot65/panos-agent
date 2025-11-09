"""Diff engine for comparing PAN-OS configurations.

Provides field-level comparison of desired vs actual configurations,
with support for detecting changes, generating diffs, and formatting
human-readable summaries.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from lxml import etree

from src.core.panos_models import parse_xml_to_dict


@dataclass
class FieldChange:
    """Represents a change in a single field."""

    field: str
    old_value: Any
    new_value: Any
    change_type: str  # "added", "removed", "modified"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "field": self.field,
            "old": self.old_value,
            "new": self.new_value,
            "type": self.change_type,
        }


@dataclass
class ConfigDiff:
    """Represents diff between two configurations."""

    object_name: str
    object_type: str
    changes: List[FieldChange]

    def is_identical(self) -> bool:
        """Check if configs are identical (no changes)."""
        return len(self.changes) == 0

    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return len(self.changes) > 0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.object_name,
            "type": self.object_type,
            "changes": [c.to_dict() for c in self.changes],
            "is_identical": self.is_identical(),
        }

    def summary(self) -> str:
        """Generate human-readable summary."""
        if self.is_identical():
            return f"No changes detected for {self.object_type} '{self.object_name}'"

        summary = f"Changes detected for {self.object_type} '{self.object_name}':\n"
        for change in self.changes:
            if change.change_type == "modified":
                summary += f"  • {change.field}: {change.old_value} → {change.new_value}\n"
            elif change.change_type == "added":
                summary += f"  + {change.field}: {change.new_value}\n"
            elif change.change_type == "removed":
                summary += f"  - {change.field}: {change.old_value}\n"

        return summary


def compare_configs(desired: dict, actual: dict) -> ConfigDiff:
    """Compare two PAN-OS configurations at field level.

    Args:
        desired: Desired configuration (what we want to apply)
        actual: Actual configuration (what exists on firewall)

    Returns:
        ConfigDiff with list of changes

    Example:
        >>> desired = {"name": "web-1", "ip-netmask": "10.0.0.2/32"}
        >>> actual = {"name": "web-1", "ip-netmask": "10.0.0.1/32"}
        >>> diff = compare_configs(desired, actual)
        >>> diff.summary()
        "Changes detected for address 'web-1':
          • ip-netmask: 10.0.0.1/32 → 10.0.0.2/32"
    """
    changes = []

    # Get all fields from both configs
    all_fields = set(desired.keys()) | set(actual.keys())

    # Ignore certain meta fields
    ignore_fields = {"name", "@admin", "@dirtyId", "@time"}

    for field in all_fields:
        if field in ignore_fields:
            continue

        desired_val = desired.get(field)
        actual_val = actual.get(field)

        # Field added in desired
        if desired_val is not None and actual_val is None:
            changes.append(
                FieldChange(
                    field=field,
                    old_value=None,
                    new_value=desired_val,
                    change_type="added",
                )
            )

        # Field removed in desired
        elif desired_val is None and actual_val is not None:
            changes.append(
                FieldChange(
                    field=field,
                    old_value=actual_val,
                    new_value=None,
                    change_type="removed",
                )
            )

        # Field modified
        elif desired_val is not None and actual_val is not None:
            # Normalize for comparison (handle list order, whitespace, etc.)
            if not _values_equal(desired_val, actual_val):
                changes.append(
                    FieldChange(
                        field=field,
                        old_value=actual_val,
                        new_value=desired_val,
                        change_type="modified",
                    )
                )

    return ConfigDiff(
        object_name=desired.get("name", actual.get("name", "unknown")),
        object_type=desired.get("@type", actual.get("@type", "unknown")),
        changes=changes,
    )


def _values_equal(val1: Any, val2: Any) -> bool:
    """Compare two values with normalization.

    Handles:
    - List order (tags can be in any order)
    - Whitespace differences
    - None vs empty string
    - Nested dicts

    Args:
        val1: First value to compare
        val2: Second value to compare

    Returns:
        True if values are equal after normalization, False otherwise
    """
    # Handle None/empty cases
    if val1 is None or val1 == "":
        return val2 is None or val2 == ""
    if val2 is None or val2 == "":
        return val1 is None or val1 == ""

    # Handle lists (order-independent for tags)
    if isinstance(val1, list) and isinstance(val2, list):
        # Normalize list items (handle nested structures)
        normalized1 = sorted(_normalize_list_item(item) for item in val1)
        normalized2 = sorted(_normalize_list_item(item) for item in val2)
        return normalized1 == normalized2

    # Handle nested dicts
    if isinstance(val1, dict) and isinstance(val2, dict):
        # Compare all keys from both dicts
        all_keys = set(val1.keys()) | set(val2.keys())
        for key in all_keys:
            if not _values_equal(val1.get(key), val2.get(key)):
                return False
        return True

    # Handle strings (strip whitespace)
    if isinstance(val1, str) and isinstance(val2, str):
        return val1.strip() == val2.strip()

    # Default comparison
    return val1 == val2


def _normalize_list_item(item: Any) -> Any:
    """Normalize a list item for comparison.

    Handles nested dicts and strings in lists.
    """
    if isinstance(item, dict):
        # Sort dict keys for comparison
        return tuple(sorted((k, _normalize_list_item(v)) for k, v in item.items()))
    if isinstance(item, str):
        return item.strip()
    return item


def compare_xml(desired_xml: str, actual_xml: str) -> ConfigDiff:
    """Compare two XML configurations.

    Args:
        desired_xml: Desired XML string
        actual_xml: Actual XML string from firewall

    Returns:
        ConfigDiff with list of changes
    """
    desired_tree = etree.fromstring(desired_xml.encode() if isinstance(desired_xml, str) else desired_xml)
    actual_tree = etree.fromstring(actual_xml.encode() if isinstance(actual_xml, str) else actual_xml)

    desired_dict = parse_xml_to_dict(desired_tree)
    actual_dict = parse_xml_to_dict(actual_tree)

    return compare_configs(desired_dict, actual_dict)

