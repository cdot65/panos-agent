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
    vsys: Optional[str] = "vsys1",
    device_group: Optional[str] = None,
    template: Optional[str] = None,
) -> dict:
    """Convert DeviceInfo to DeviceContext dictionary.

    Args:
        device_info: Device information from connection
        vsys: Virtual system (for multi-vsys firewalls, default: vsys1, None for Panorama)
        device_group: Device group (for Panorama, optional)
        template: Template name (for Panorama, optional)

    Returns:
        DeviceContext dictionary for state
    """
    context = {
        "device_type": device_info.device_type.value,
        "hostname": device_info.hostname,
        "model": device_info.model,
        "version": device_info.version,
        "serial": device_info.serial,
        "device_group": device_group,
        "template": template,
        "platform": device_info.platform,
    }
    # Only add vsys for firewalls
    if device_info.device_type == DeviceType.FIREWALL:
        context["vsys"] = vsys or "vsys1"
    return context


async def _detect_vsys(client: httpx.AsyncClient) -> str:
    """Detect available vsys or use CLI override.

    Checks environment variable PANOS_AGENT_VSYS first, then queries device
    for available vsys. Defaults to vsys1 if detection fails.

    Args:
        client: PAN-OS HTTP client

    Returns:
        Vsys name (e.g., 'vsys1', 'vsys2')
    """
    # Check CLI override first
    cli_vsys = os.environ.get("PANOS_AGENT_VSYS")
    if cli_vsys:
        logger.debug(f"Using CLI-specified vsys: {cli_vsys}")
        return cli_vsys

    # Query device for available vsys
    try:
        # Query vsys configuration: <show><config><vsys></vsys></config></show>
        cmd = "<show><config><vsys></vsys></config></show>"
        result = await operational_command(cmd, client)

        # Parse vsys entries from response
        vsys_entries = result.findall(".//vsys/entry")
        if vsys_entries:
            # Get first vsys name (typically vsys1)
            first_vsys = vsys_entries[0].get("name")
            if first_vsys:
                logger.debug(f"Detected vsys: {first_vsys}")
                return first_vsys

        # Fallback: try to get vsys from system info
        cmd = "<show><system><info></info></system></show>"
        result = await operational_command(cmd, client)
        # System info doesn't directly show vsys, so default to vsys1
        logger.debug("Could not detect vsys from device, defaulting to vsys1")
        return "vsys1"

    except Exception as e:
        logger.warning(f"Failed to detect vsys: {e}, defaulting to vsys1")
        return "vsys1"


async def get_device_context(
    vsys: Optional[str] = None,
    device_group: Optional[str] = None,
    template: Optional[str] = None,
) -> Optional[dict]:
    """Get device context for state.

    Convenience function that gets device info and converts to context dict.
    For firewalls, detects vsys from device or uses CLI override.

    Args:
        vsys: Virtual system (for multi-vsys firewalls, optional - will be detected)
        device_group: Device group (for Panorama, optional)
        template: Template name (for Panorama, optional)

    Returns:
        DeviceContext dictionary if connected, None otherwise
    """
    device_info = await get_device_info()
    if device_info is None:
        return None

    # For firewalls, detect vsys if not provided
    if device_info.device_type == DeviceType.FIREWALL:
        if vsys is None:
            # Check CLI override or detect from device
            client = await get_panos_client()
            vsys = await _detect_vsys(client)
        # Ensure vsys is set (fallback to vsys1)
        if not vsys:
            vsys = "vsys1"
    else:
        # Panorama doesn't use vsys
        vsys = None

    return device_info_to_context(device_info, vsys, device_group, template)


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
