"""Diff engine for comparing PAN-OS configurations.

Provides field-level comparison of desired vs actual configurations with:
- Order-independent list comparison (tags can be in any order)
- Whitespace normalization
- None vs empty string handling
- Nested dict comparison
- Human-readable summaries
"""

from dataclasses import dataclass
from typing import Any, List


@dataclass
class FieldChange:
    """Represents a change in a single field.

    Attributes:
        field: Field name that changed
        old_value: Previous value (None if added)
        new_value: New value (None if removed)
        change_type: Type of change ('added', 'removed', 'modified')
    """

    field: str
    old_value: Any
    new_value: Any
    change_type: str  # "added", "removed", "modified"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of field change
        """
        return {
            "field": self.field,
            "old": self.old_value,
            "new": self.new_value,
            "type": self.change_type,
        }


@dataclass
class ConfigDiff:
    """Represents diff between two configurations.

    Attributes:
        object_name: Name of the object being compared
        object_type: Type of object (address, service, etc.)
        changes: List of field changes
    """

    object_name: str
    object_type: str
    changes: List[FieldChange]

    def is_identical(self) -> bool:
        """Check if configs are identical (no changes).

        Returns:
            True if no changes detected, False otherwise
        """
        return len(self.changes) == 0

    def has_changes(self) -> bool:
        """Check if there are any changes.

        Returns:
            True if changes detected, False otherwise
        """
        return len(self.changes) > 0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of diff
        """
        return {
            "name": self.object_name,
            "type": self.object_type,
            "changes": [c.to_dict() for c in self.changes],
            "is_identical": self.is_identical(),
        }

    def summary(self) -> str:
        """Generate human-readable summary.

        Returns:
            Formatted string summarizing changes
        """
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

        return summary.rstrip()


def _values_equal(val1: Any, val2: Any) -> bool:
    """Compare two values with normalization.

    Handles:
    - List order (tags can be in any order)
    - Whitespace differences
    - None vs empty string
    - Nested dicts

    Args:
        val1: First value
        val2: Second value

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
        # Sort both lists for comparison (order-independent)
        return sorted(str(v) for v in val1) == sorted(str(v) for v in val2)

    # Handle nested dicts
    if isinstance(val1, dict) and isinstance(val2, dict):
        # Compare all keys from both dicts
        all_keys = set(val1.keys()) | set(val2.keys())
        return all(_values_equal(val1.get(k), val2.get(k)) for k in all_keys)

    # Handle strings (strip whitespace)
    if isinstance(val1, str) and isinstance(val2, str):
        return val1.strip() == val2.strip()

    # Default comparison
    return val1 == val2


def compare_configs(desired: dict, actual: dict) -> ConfigDiff:
    """Compare two PAN-OS configurations at field level.

    Compares desired configuration against actual configuration and returns
    a ConfigDiff object detailing all changes. Ignores metadata fields and
    applies normalization for robust comparison.

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
                FieldChange(field=field, old_value=None, new_value=desired_val, change_type="added")
            )

        # Field removed in desired
        elif desired_val is None and actual_val is not None:
            changes.append(
                FieldChange(
                    field=field, old_value=actual_val, new_value=None, change_type="removed"
                )
            )

        # Field potentially modified
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


def compare_xml(desired_xml: str, actual_xml: str) -> ConfigDiff:
    """Compare two XML configurations.

    Parses XML strings into dictionaries and compares them using compare_configs().

    Args:
        desired_xml: Desired XML string
        actual_xml: Actual XML string from firewall

    Returns:
        ConfigDiff with list of changes

    Raises:
        ValueError: If XML parsing fails
    """
    from lxml import etree
    from src.core.panos_models import parse_xml_to_dict

    try:
        desired_tree = etree.fromstring(desired_xml.encode("utf-8"))
        actual_tree = etree.fromstring(actual_xml.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        raise ValueError(f"XML parsing failed: {e}")

    desired_dict = parse_xml_to_dict(desired_tree)
    actual_dict = parse_xml_to_dict(actual_tree)

    return compare_configs(desired_dict, actual_dict)
