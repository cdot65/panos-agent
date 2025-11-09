"""PAN-OS async HTTP client management.

Singleton pattern for reusable async HTTP client across tools and subgraphs.
Uses httpx with connection pooling for efficient API interactions.
"""

import logging
from typing import Optional

import httpx

from src.core.config import get_settings
from src.core.panos_api import PanOSConnectionError, operational_command

logger = logging.getLogger(__name__)

# Global singleton
_panos_client: Optional[httpx.AsyncClient] = None


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

        logger.info(f"Initializing PAN-OS connection to {settings.panos_hostname}")

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

        # Test connection
        try:
            # Execute simple operational command to validate credentials
            cmd = "<show><system><info></info></system></show>"
            result = await operational_command(cmd, _panos_client)

            # Extract system info
            hostname_elem = result.find(".//hostname")
            version_elem = result.find(".//sw-version")

            hostname = hostname_elem.text if hostname_elem is not None else "Unknown"
            version = version_elem.text if version_elem is not None else "Unknown"

            logger.info(f"Connected to PAN-OS {version} (hostname: {hostname})")

        except Exception as e:
            logger.error(f"Failed to connect to PAN-OS firewall: {e}")
            await _panos_client.aclose()
            _panos_client = None
            raise PanOSConnectionError(f"Connection test failed: {e}") from e

    return _panos_client


async def close_panos_client() -> None:
    """Close PAN-OS async HTTP client and reset singleton.

    Useful for cleanup or reconnecting with different credentials.
    """
    global _panos_client
    if _panos_client is not None:
        await _panos_client.aclose()
        _panos_client = None
        logger.info("PAN-OS client closed")


async def reset_panos_client() -> None:
    """Reset PAN-OS client singleton.

    Alias for close_panos_client for backward compatibility.
    """
    await close_panos_client()


async def test_connection() -> tuple[bool, str]:
    """Test PAN-OS firewall connection.

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        client = await get_panos_client()

        # Get system info
        cmd = "<show><system><info></info></system></show>"
        result = await operational_command(cmd, client)

        hostname_elem = result.find(".//hostname")
        version_elem = result.find(".//sw-version")
        serial_elem = result.find(".//serial")

        hostname = hostname_elem.text if hostname_elem is not None else "Unknown"
        version = version_elem.text if version_elem is not None else "Unknown"
        serial = serial_elem.text if serial_elem is not None else "Unknown"

        message = f"✅ Connected to PAN-OS {version} (hostname: {hostname}, serial: {serial})"
        return True, message

    except Exception as e:
        message = f"❌ Connection failed: {type(e).__name__}: {e}"
        return False, message
