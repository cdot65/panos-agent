#!/usr/bin/env python3
"""Device Type Detection Validation Script

This script demonstrates the device type detection feature.
It connects to a PAN-OS device and displays device information including
whether it's a Firewall or Panorama.

Usage:
    python examples/device_detection.py

Environment Variables:
    PANOS_HOSTNAME: PAN-OS device hostname/IP
    PANOS_USERNAME: PAN-OS username
    PANOS_PASSWORD: PAN-OS password
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.client import get_device_info, get_panos_client, test_connection
from src.core.panos_models import DeviceType


async def main():
    """Main validation function."""
    print("=" * 70)
    print("PAN-OS Device Type Detection Validation")
    print("=" * 70)
    print()

    # Check environment variables
    if not os.getenv("PANOS_HOSTNAME"):
        print("❌ Error: PANOS_HOSTNAME environment variable not set")
        print("\nPlease set the following environment variables:")
        print("  export PANOS_HOSTNAME=<device-ip-or-hostname>")
        print("  export PANOS_USERNAME=<username>")
        print("  export PANOS_PASSWORD=<password>")
        sys.exit(1)

    print(f"Connecting to: {os.getenv('PANOS_HOSTNAME')}")
    print()

    # Test connection
    print("1. Testing connection...")
    success, message = await test_connection()
    if success:
        print(f"   {message}")
    else:
        print(f"   {message}")
        sys.exit(1)
    print()

    # Get device info
    print("2. Retrieving device information...")
    device_info = await get_device_info()

    if device_info:
        print(f"   ✅ Device information retrieved successfully")
        print()
        print("   Device Details:")
        print(f"   - Device Type: {device_info.device_type.value}")
        print(f"   - Hostname:    {device_info.hostname}")
        print(f"   - Model:       {device_info.model}")
        print(f"   - Serial:      {device_info.serial}")
        print(f"   - Version:     {device_info.version}")
        if device_info.platform:
            print(f"   - Platform:    {device_info.platform}")
        print()

        # Validate device type detection
        print("3. Validating device type detection...")
        model_upper = device_info.model.upper()
        expected_type = None

        if model_upper.startswith("M-") or "PANORAMA" in model_upper:
            expected_type = DeviceType.PANORAMA
        else:
            expected_type = DeviceType.FIREWALL

        if device_info.device_type == expected_type:
            print(f"   ✅ Device type correctly detected as {device_info.device_type.value}")
        else:
            print(
                f"   ⚠️  Warning: Expected {expected_type.value}, "
                f"but detected {device_info.device_type.value}"
            )
        print()

        # Display device-specific information
        print("4. Device-specific context:")
        if device_info.device_type == DeviceType.PANORAMA:
            print("   This is a Panorama device.")
            print("   - Can manage multiple firewalls")
            print("   - Uses device-groups and templates")
            print("   - XPaths will include device-group/template context")
        else:
            print("   This is a Firewall device.")
            print("   - Standalone or managed by Panorama")
            print("   - Uses vsys for virtual systems")
            print("   - XPaths will include vsys context")
        print()

        print("=" * 70)
        print("✅ Validation complete!")
        print("=" * 70)
    else:
        print("   ❌ Failed to retrieve device information")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

