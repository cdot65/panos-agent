#!/usr/bin/env python3
"""Analyze PAN-OS running configuration and extract examples.

This script parses a PAN-OS running-config.xml file and:
1. Extracts examples of each object type
2. Validates XPath expressions
3. Generates test data from real config
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional


def analyze_config(config_path: str) -> Dict:
    """Analyze PAN-OS configuration file.

    Args:
        config_path: Path to running-config.xml

    Returns:
        Dictionary with analysis results
    """
    tree = ET.parse(config_path)
    root = tree.getroot()

    # Get version info
    version = root.get("version", "Unknown")
    detail_version = root.get("detail-version", "Unknown")

    print(f"PAN-OS Version: {version} ({detail_version})\n")

    # Find vsys1
    vsys = root.find(".//entry[@name='vsys1']")
    if vsys is None:
        print("❌ vsys1 not found!")
        return {}

    results = {
        "version": version,
        "detail_version": detail_version,
        "objects": {},
    }

    # Analyze each object type
    object_types = [
        ("address", "Address Objects"),
        ("address-group", "Address Groups"),
        ("service", "Service Objects"),
        ("service-group", "Service Groups"),
    ]

    for xml_tag, display_name in object_types:
        element = vsys.find(xml_tag)
        if element is not None:
            entries = list(element.findall("entry"))
            count = len(entries)
            print(f"✅ {display_name}: {count} entries")

            if count > 0:
                # Get first example
                example = entries[0]
                results["objects"][xml_tag] = {
                    "count": count,
                    "example_name": example.get("name"),
                    "example_xml": ET.tostring(example, encoding="unicode"),
                }
                print(f"   Example: {example.get('name')}")

    # Analyze security rules
    sec_rules = vsys.find(".//rulebase/security/rules")
    if sec_rules is not None:
        entries = list(sec_rules.findall("entry"))
        count = len(entries)
        print(f"\n✅ Security Rules: {count} entries")

        if count > 0:
            example = entries[0]
            results["objects"]["security_rules"] = {
                "count": count,
                "example_name": example.get("name"),
                "example_xml": ET.tostring(example, encoding="unicode"),
            }
            print(f"   Example: {example.get('name')}")

    # Analyze NAT rules
    nat_rules = vsys.find(".//rulebase/nat/rules")
    if nat_rules is not None:
        entries = list(nat_rules.findall("entry"))
        count = len(entries)
        print(f"\n✅ NAT Rules: {count} entries")

        if count > 0:
            example = entries[0]
            results["objects"]["nat_rules"] = {
                "count": count,
                "example_name": example.get("name"),
                "example_xml": ET.tostring(example, encoding="unicode"),
            }
            print(f"   Example: {example.get('name')}")

    return results


def extract_examples(config_path: str, output_dir: str):
    """Extract XML examples for each object type.

    Args:
        config_path: Path to running-config.xml
        output_dir: Directory to save examples
    """
    tree = ET.parse(config_path)
    root = tree.getroot()

    vsys = root.find(".//entry[@name='vsys1']")
    if vsys is None:
        print("❌ vsys1 not found!")
        return

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n📁 Extracting examples to {output_dir}/\n")

    # Extract address object examples
    addresses = vsys.find("address")
    if addresses is not None:
        entries = list(addresses.findall("entry"))
        if entries:
            example = entries[0]
            xml_str = ET.tostring(example, encoding="unicode")
            with open(output_path / "address_example.xml", "w") as f:
                f.write(xml_str)
            print(f"✅ address_example.xml: {example.get('name')}")

    # Extract address group examples
    addr_groups = vsys.find("address-group")
    if addr_groups is not None:
        entries = list(addr_groups.findall("entry"))
        if entries:
            example = entries[0]
            xml_str = ET.tostring(example, encoding="unicode")
            with open(output_path / "address_group_example.xml", "w") as f:
                f.write(xml_str)
            print(f"✅ address_group_example.xml: {example.get('name')}")

    # Extract service examples
    services = vsys.find("service")
    if services is not None:
        entries = list(services.findall("entry"))
        if entries:
            example = entries[0]
            xml_str = ET.tostring(example, encoding="unicode")
            with open(output_path / "service_example.xml", "w") as f:
                f.write(xml_str)
            print(f"✅ service_example.xml: {example.get('name')}")

    # Extract security rule examples
    sec_rules = vsys.find(".//rulebase/security/rules")
    if sec_rules is not None:
        entries = list(sec_rules.findall("entry"))
        if entries:
            example = entries[0]
            xml_str = ET.tostring(example, encoding="unicode")
            with open(output_path / "security_rule_example.xml", "w") as f:
                f.write(xml_str)
            print(f"✅ security_rule_example.xml: {example.get('name')}")

    # Extract NAT rule examples
    nat_rules = vsys.find(".//rulebase/nat/rules")
    if nat_rules is not None:
        entries = list(nat_rules.findall("entry"))
        if entries:
            example = entries[0]
            xml_str = ET.tostring(example, encoding="unicode")
            with open(output_path / "nat_rule_example.xml", "w") as f:
                f.write(xml_str)
            print(f"✅ nat_rule_example.xml: {example.get('name')}")


def validate_xpaths(config_path: str):
    """Validate XPath expressions against actual config.

    Args:
        config_path: Path to running-config.xml
    """
    from src.core.panos_xpath_map import PanOSXPathMap

    tree = ET.parse(config_path)
    root = tree.getroot()

    print("\n🔍 Validating XPath Expressions\n")

    # Test base config path
    base_xpath = "/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']"
    vsys = root.find(".//entry[@name='vsys1']")

    if vsys is not None:
        print(f"✅ Base path works: {base_xpath}")
    else:
        print(f"❌ Base path failed: {base_xpath}")
        return

    # Test object type paths
    tests = [
        ("address", "Address Objects"),
        ("address_group", "Address Groups"),
        ("service", "Service Objects"),
        ("security_policy", "Security Policies"),
        ("nat_policy", "NAT Policies"),
    ]

    for obj_type, display_name in tests:
        try:
            xpath = PanOSXPathMap.get_xpath(obj_type + "_list")
            # Convert our xpath to work with ET (remove /config prefix)
            et_xpath = xpath.replace("/config/", ".//")
            result = root.find(et_xpath)

            if result is not None:
                entries = len(list(result.findall("entry")))
                print(f"✅ {display_name}: {entries} entries")
            else:
                print(f"❌ {display_name}: XPath returned None")
        except Exception as e:
            print(f"❌ {display_name}: {e}")


if __name__ == "__main__":
    import sys

    config_file = "docs/panos_config/running-config.xml"

    if not Path(config_file).exists():
        print(f"❌ Config file not found: {config_file}")
        print("\nPlace your running-config.xml in docs/panos_config/")
        sys.exit(1)

    print("=" * 60)
    print("PAN-OS Configuration Analyzer")
    print("=" * 60 + "\n")

    # Analyze configuration
    results = analyze_config(config_file)

    # Extract examples
    extract_examples(config_file, "docs/panos_config/examples")

    # Validate XPaths
    try:
        validate_xpaths(config_file)
    except ImportError:
        print("\n⚠️  XPath validation skipped (run from project root)")

    print("\n" + "=" * 60)
    print("Analysis complete!")
    print("=" * 60)
