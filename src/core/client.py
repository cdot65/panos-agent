"""PAN-OS async HTTP client management.

Singleton pattern for reusable async HTTP client across tools and subgraphs.
Uses httpx with connection pooling for efficient API interactions.
"""

import logging
import os
from typing import Optional

import httpx

from src.core.config import get_settings
from src.core.panos_api import PanOSConnectionError, operational_command
from src.core.panos_models import DeviceInfo, DeviceType

logger = logging.getLogger(__name__)

# Global singleton
_panos_client: Optional[httpx.AsyncClient] = None
_device_info: Optional[DeviceInfo] = None


async def get_panos_client() -> httpx.AsyncClient:
    """Get or create PAN-OS async HTTP client singleton.

    Initializes connection using credentials from environment variables.
    Uses connection pooling with max 10 connections for efficiency.

    Returns:
        httpx.AsyncClient: Configured async HTTP client

    Raises:
        PanOSConnectionError: If connection initialization fails
    """
    global _panos_client

    if _panos_client is None:
        settings = get_settings()

        logger.debug(f"Initializing PAN-OS connection to {settings.panos_hostname}")

        # Create async client with connection pooling and authentication
        _panos_client = httpx.AsyncClient(
            base_url=f"https://{settings.panos_hostname}",
            auth=(settings.panos_username, settings.panos_password),
            verify=False,  # Skip SSL verification for self-signed certs (typical in labs)
            timeout=30.0,
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
            ),
            follow_redirects=True,
        )

        # Test connection and detect device type
        try:
            # Execute simple operational command to validate credentials
            cmd = "<show><system><info></info></system></show>"
            result = await operational_command(cmd, _panos_client)

            # Extract system info
            hostname_elem = result.find(".//hostname")
            version_elem = result.find(".//sw-version")
            model_elem = result.find(".//model")
            serial_elem = result.find(".//serial")
            platform_elem = result.find(".//platform")

            hostname = hostname_elem.text if hostname_elem is not None else "Unknown"
            version = version_elem.text if version_elem is not None else "Unknown"
            model = model_elem.text if model_elem is not None else "Unknown"
            serial = serial_elem.text if serial_elem is not None else "Unknown"
            platform = platform_elem.text if platform_elem is not None else None

            # Detect device type based on model
            # Panorama models: M-100, M-200, M-500, or contain "Panorama"
            # Firewall models: PA-*, VM-*, or other patterns
            model_upper = model.upper()
            if model_upper.startswith("M-") or "PANORAMA" in model_upper:
                device_type = DeviceType.PANORAMA
            else:
                device_type = DeviceType.FIREWALL

            # Store device info
            global _device_info
            _device_info = DeviceInfo(
                hostname=hostname,
                version=version,
                serial=serial,
                model=model,
                device_type=device_type,
                platform=platform,
            )

            logger.info(
                f"Connected to {device_type.value} {version} "
                f"(hostname: {hostname}, model: {model}, serial: {serial})"
            )

        except Exception as e:
            logger.error(f"Failed to connect to PAN-OS device: {e}")
            await _panos_client.aclose()
            _panos_client = None
            _device_info = None
            raise PanOSConnectionError(f"Connection test failed: {e}") from e

    return _panos_client


async def close_panos_client() -> None:
    """Close PAN-OS async HTTP client and reset singleton.

    Useful for cleanup or reconnecting with different credentials.
    """
    global _panos_client, _device_info
    if _panos_client is not None:
        await _panos_client.aclose()
        _panos_client = None
        _device_info = None
        logger.debug("PAN-OS client closed")


async def reset_panos_client() -> None:
    """Reset PAN-OS client singleton.

    Alias for close_panos_client for backward compatibility.
    """
    await close_panos_client()


async def get_device_info() -> Optional[DeviceInfo]:
    """Get device information from connection.

    Returns:
        DeviceInfo if connected, None otherwise
    """
    global _device_info  # noqa: F824
    if _device_info is None:
        # Try to initialize connection if not already done
        try:
            await get_panos_client()
        except Exception:
            pass
    return _device_info


def device_info_to_context(
    device_info: DeviceInfo,
    vsys: str = "vsys1",
    device_group: Optional[str] = None,
    template: Optional[str] = None,
) -> dict:
    """Convert DeviceInfo to DeviceContext dictionary.

    Args:
        device_info: Device information from connection
        vsys: Virtual system (for multi-vsys firewalls, default: vsys1)
        device_group: Device group (for Panorama, optional)
        template: Template name (for Panorama, optional)

    Returns:
        DeviceContext dictionary for state
    """
    return {
        "device_type": device_info.device_type.value,
        "hostname": device_info.hostname,
        "model": device_info.model,
        "version": device_info.version,
        "serial": device_info.serial,
        "vsys": vsys,
        "device_group": device_group,
        "template": template,
        "platform": device_info.platform,
    }


async def _detect_vsys(client: httpx.AsyncClient) -> str:
    """Detect available vsys or use CLI override.

    Detection logic:
    1. Check for CLI override via PANOS_AGENT_VSYS environment variable
    2. Query device for available vsys using show vsys command
    3. Default to vsys1 if detection fails or single-vsys device

    Args:
        client: Async HTTP client for PAN-OS API

    Returns:
        vsys name (e.g., 'vsys1', 'vsys2', etc.)
    """
    # Priority 1: Check CLI override from environment variable
    cli_vsys = os.environ.get("PANOS_AGENT_VSYS")
    if cli_vsys:
        logger.debug(f"Using vsys from CLI override: {cli_vsys}")
        return cli_vsys

    # Priority 2: Try to detect available vsys from device
    try:
        # Query device for vsys configuration
        # This operational command lists all configured vsys
        cmd = "<show><system><info></info></system></show>"
        _ = await operational_command(cmd, client)

        # Extract vsys info if available (multi-vsys devices)
        # For single-vsys devices, this may not be present
        # Note: The exact XML structure depends on device configuration
        # For now, we'll default to vsys1 as it's the most common case

        # TODO: Implement full vsys detection by parsing:
        # - show system info (for vsys mode check)
        # - show vsys (for available vsys list)
        # For Phase 3.4, we prioritize CLI override and default behavior

        logger.debug("Vsys detection: defaulting to vsys1 (single-vsys or CLI override required for multi-vsys)")
        return "vsys1"

    except Exception as e:
        logger.warning(f"Failed to detect vsys, defaulting to vsys1: {e}")
        return "vsys1"


async def get_device_context(
    vsys: Optional[str] = None,
    device_group: Optional[str] = None,
    template: Optional[str] = None,
) -> Optional[dict]:
    """Get device context for state.

    Convenience function that gets device info and converts to context dict.

    Args:
        vsys: Virtual system (for multi-vsys firewalls, optional)
              If not provided, will be detected or default to vsys1
        device_group: Device group (for Panorama, optional)
        template: Template name (for Panorama, optional)

    Returns:
        DeviceContext dictionary if connected, None otherwise
    """
    device_info = await get_device_info()
    if device_info is None:
        return None

    # Detect vsys if not provided and device is a firewall
    if device_info.device_type == DeviceType.FIREWALL and vsys is None:
        client = await get_panos_client()
        vsys = await _detect_vsys(client)

    # Use provided vsys or detected/default vsys
    final_vsys = vsys if vsys else "vsys1"

    return device_info_to_context(device_info, final_vsys, device_group, template)


async def test_connection() -> tuple[bool, str]:
    """Test PAN-OS device connection.

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        await get_panos_client()
        device_info = await get_device_info()

        if device_info:
            message = (
                f"✅ Connected to {device_info.device_type.value} "
                f"{device_info.version} "
                f"(hostname: {device_info.hostname}, "
                f"model: {device_info.model}, "
                f"serial: {device_info.serial})"
            )
        else:
            # Fallback if device_info not available
            message = "✅ Connected to PAN-OS device"
        return True, message

    except Exception as e:
        message = f"❌ Connection failed: {type(e).__name__}: {e}"
        return False, message
