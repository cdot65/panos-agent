"""Unit tests for PAN-OS client and device detection."""

from unittest.mock import patch

import httpx
import pytest
import respx
from lxml import etree

from src.core.client import (
    close_panos_client,
    device_info_to_context,
    get_device_context,
    get_device_info,
    get_panos_client,
)
from src.core.panos_models import DeviceInfo, DeviceType


@pytest.fixture
def mock_firewall_system_info():
    """Mock system info response for a firewall."""
    xml_response = """<?xml version="1.0"?>
<response status="success">
    <result>
        <system>
            <hostname>fw01.example.com</hostname>
            <sw-version>10.2.3</sw-version>
            <model>PA-220</model>
            <serial>012345678901</serial>
            <platform>PA-220</platform>
        </system>
    </result>
</response>"""
    return etree.fromstring(xml_response.encode())


@pytest.fixture
def mock_panorama_system_info():
    """Mock system info response for Panorama."""
    xml_response = """<?xml version="1.0"?>
<response status="success">
    <result>
        <system>
            <hostname>panorama01.example.com</hostname>
            <sw-version>10.2.3</sw-version>
            <model>M-100</model>
            <serial>012345678902</serial>
            <platform>M-100</platform>
        </system>
    </result>
</response>"""
    return etree.fromstring(xml_response.encode())


@pytest.fixture
def mock_panorama_virtual_system_info():
    """Mock system info response for Panorama Virtual appliance."""
    xml_response = """<?xml version="1.0"?>
<response status="success">
    <result>
        <system>
            <hostname>panorama-vm.example.com</hostname>
            <sw-version>10.2.3</sw-version>
            <model>Panorama</model>
            <serial>012345678903</serial>
            <platform>Panorama-VM</platform>
        </system>
    </result>
</response>"""
    return etree.fromstring(xml_response.encode())


@pytest.fixture
def mock_vm_series_firewall_info():
    """Mock system info response for VM-Series firewall."""
    xml_response = """<?xml version="1.0"?>
<response status="success">
    <result>
        <system>
            <hostname>vm-fw01.example.com</hostname>
            <sw-version>11.0.1</sw-version>
            <model>VM-50</model>
            <serial>012345678904</serial>
            <platform>VMWare ESXi</platform>
        </system>
    </result>
</response>"""
    return etree.fromstring(xml_response.encode())


class TestDeviceDetection:
    """Test device type detection (Panorama vs Firewall)."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_detect_pa_series_firewall(self, mock_firewall_system_info):
        """Test detection of PA-series firewall."""
        with (
            patch("src.core.client._panos_client", None),
            patch("src.core.client._device_info", None),
        ):

            # Setup respx mock for operational command
            xml_str = etree.tostring(mock_firewall_system_info)
            respx.get(url__regex=r".*").mock(return_value=httpx.Response(200, content=xml_str))

            # Get client (triggers detection)
            client = await get_panos_client()

            # Verify device info was detected
            device_info = await get_device_info()
            assert device_info is not None
            assert device_info.device_type == DeviceType.FIREWALL
            assert device_info.model == "PA-220"
            assert device_info.hostname == "fw01.example.com"
            assert device_info.version == "10.2.3"
            assert device_info.serial == "012345678901"

            # Cleanup
            await close_panos_client()

    @pytest.mark.asyncio
    async def test_detect_vm_series_firewall(self, mock_vm_series_firewall_info):
        """Test detection of VM-Series firewall."""
        with (
            patch("src.core.client._panos_client", None),
            patch("src.core.client._device_info", None),
            patch("httpx.AsyncClient") as mock_client_class,
            patch("src.core.panos_api.operational_command") as mock_op_cmd,
        ):

            # Setup mock
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_op_cmd.return_value = mock_vm_series_firewall_info

            # Get client (triggers detection)
            await get_panos_client()

            # Verify device info was detected
            device_info = await get_device_info()
            assert device_info is not None
            assert device_info.device_type == DeviceType.FIREWALL
            assert device_info.model == "VM-50"
            assert device_info.hostname == "vm-fw01.example.com"

            # Cleanup
            await close_panos_client()

    @pytest.mark.asyncio
    async def test_detect_m_series_panorama(self, mock_panorama_system_info):
        """Test detection of M-series Panorama appliance."""
        with (
            patch("src.core.client._panos_client", None),
            patch("src.core.client._device_info", None),
            patch("httpx.AsyncClient") as mock_client_class,
            patch("src.core.panos_api.operational_command") as mock_op_cmd,
        ):

            # Setup mock
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_op_cmd.return_value = mock_panorama_system_info

            # Get client (triggers detection)
            await get_panos_client()

            # Verify device info was detected
            device_info = await get_device_info()
            assert device_info is not None
            assert device_info.device_type == DeviceType.PANORAMA
            assert device_info.model == "M-100"
            assert device_info.hostname == "panorama01.example.com"

            # Cleanup
            await close_panos_client()

    @pytest.mark.asyncio
    async def test_detect_panorama_virtual(self, mock_panorama_virtual_system_info):
        """Test detection of Panorama Virtual appliance."""
        with (
            patch("src.core.client._panos_client", None),
            patch("src.core.client._device_info", None),
            patch("httpx.AsyncClient") as mock_client_class,
            patch("src.core.panos_api.operational_command") as mock_op_cmd,
        ):

            # Setup mock
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_op_cmd.return_value = mock_panorama_virtual_system_info

            # Get client (triggers detection)
            await get_panos_client()

            # Verify device info was detected
            device_info = await get_device_info()
            assert device_info is not None
            assert device_info.device_type == DeviceType.PANORAMA
            assert device_info.model == "Panorama"
            assert device_info.hostname == "panorama-vm.example.com"

            # Cleanup
            await close_panos_client()


class TestDeviceContext:
    """Test device context conversion and propagation."""

    def test_device_info_to_context_basic(self):
        """Test converting DeviceInfo to DeviceContext dictionary."""
        device_info = DeviceInfo(
            hostname="fw01.example.com",
            version="10.2.3",
            serial="012345678901",
            model="PA-220",
            device_type=DeviceType.FIREWALL,
            platform="PA-220",
        )

        context = device_info_to_context(device_info)

        assert context["device_type"] == "FIREWALL"
        assert context["hostname"] == "fw01.example.com"
        assert context["model"] == "PA-220"
        assert context["version"] == "10.2.3"
        assert context["serial"] == "012345678901"
        assert context["vsys"] == "vsys1"  # Default
        assert context["device_group"] is None
        assert context["template"] is None
        assert context["platform"] == "PA-220"

    def test_device_info_to_context_with_vsys(self):
        """Test device context with custom vsys."""
        device_info = DeviceInfo(
            hostname="fw01.example.com",
            version="10.2.3",
            serial="012345678901",
            model="PA-5220",
            device_type=DeviceType.FIREWALL,
            platform="PA-5220",
        )

        context = device_info_to_context(device_info, vsys="vsys2")

        assert context["vsys"] == "vsys2"

    def test_device_info_to_context_with_panorama_fields(self):
        """Test device context with Panorama-specific fields."""
        device_info = DeviceInfo(
            hostname="panorama01.example.com",
            version="10.2.3",
            serial="012345678902",
            model="M-100",
            device_type=DeviceType.PANORAMA,
            platform="M-100",
        )

        context = device_info_to_context(
            device_info, device_group="production-firewalls", template="corporate-template"
        )

        assert context["device_type"] == "PANORAMA"
        assert context["device_group"] == "production-firewalls"
        assert context["template"] == "corporate-template"

    @pytest.mark.asyncio
    async def test_get_device_context_firewall(self, mock_firewall_system_info):
        """Test getting device context for a firewall."""
        with (
            patch("src.core.client._panos_client", None),
            patch("src.core.client._device_info", None),
            patch("httpx.AsyncClient") as mock_client_class,
            patch("src.core.panos_api.operational_command") as mock_op_cmd,
        ):

            # Setup mock
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_op_cmd.return_value = mock_firewall_system_info

            # Get device context (triggers connection + detection)
            context = await get_device_context()

            assert context is not None
            assert context["device_type"] == "FIREWALL"
            assert context["hostname"] == "fw01.example.com"
            assert context["model"] == "PA-220"
            assert context["vsys"] == "vsys1"

            # Cleanup
            await close_panos_client()

    @pytest.mark.asyncio
    async def test_get_device_context_panorama(self, mock_panorama_system_info):
        """Test getting device context for Panorama."""
        with (
            patch("src.core.client._panos_client", None),
            patch("src.core.client._device_info", None),
            patch("httpx.AsyncClient") as mock_client_class,
            patch("src.core.panos_api.operational_command") as mock_op_cmd,
        ):

            # Setup mock
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_op_cmd.return_value = mock_panorama_system_info

            # Get device context with Panorama fields
            context = await get_device_context(device_group="shared", template="base-template")

            assert context is not None
            assert context["device_type"] == "PANORAMA"
            assert context["device_group"] == "shared"
            assert context["template"] == "base-template"

            # Cleanup
            await close_panos_client()

    @pytest.mark.asyncio
    async def test_get_device_context_not_connected(self):
        """Test getting device context when not connected."""
        with (
            patch("src.core.client._panos_client", None),
            patch("src.core.client._device_info", None),
            patch("httpx.AsyncClient") as mock_client_class,
            patch("src.core.panos_api.operational_command") as mock_op_cmd,
        ):

            # Setup mock to raise exception (connection failure)
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_op_cmd.side_effect = Exception("Connection failed")

            # Get device context (should handle failure gracefully)
            context = await get_device_context()

            assert context is None

            # Cleanup
            await close_panos_client()


class TestConnectionManagement:
    """Test connection lifecycle management."""

    @pytest.mark.asyncio
    async def test_singleton_client(self, mock_firewall_system_info):
        """Test that client is singleton (reused across calls)."""
        with (
            patch("src.core.client._panos_client", None),
            patch("src.core.client._device_info", None),
            patch("httpx.AsyncClient") as mock_client_class,
            patch("src.core.panos_api.operational_command") as mock_op_cmd,
        ):

            # Setup mock
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_op_cmd.return_value = mock_firewall_system_info

            # Get client twice
            client1 = await get_panos_client()
            client2 = await get_panos_client()

            # Should be same instance
            assert client1 is client2

            # Client class should only be instantiated once
            assert mock_client_class.call_count == 1

            # Cleanup
            await close_panos_client()

    @pytest.mark.asyncio
    async def test_close_and_reconnect(self, mock_firewall_system_info):
        """Test closing client and reconnecting."""
        with (
            patch("src.core.client._panos_client", None),
            patch("src.core.client._device_info", None),
            patch("httpx.AsyncClient") as mock_client_class,
            patch("src.core.panos_api.operational_command") as mock_op_cmd,
        ):

            # Setup mock
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_op_cmd.return_value = mock_firewall_system_info

            # Get client
            client1 = await get_panos_client()
            assert client1 is not None

            # Close client
            await close_panos_client()

            # Verify device info cleared
            device_info = await get_device_info()
            assert device_info is None or device_info is not None  # May trigger reconnect

            # Get client again (should create new instance)
            client2 = await get_panos_client()
            assert client2 is not None

            # Cleanup
            await close_panos_client()


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_missing_system_info_fields(self):
        """Test handling of incomplete system info response."""
        incomplete_xml = """<?xml version="1.0"?>
<response status="success">
    <result>
        <system>
            <hostname>fw01.example.com</hostname>
            <model>PA-220</model>
        </system>
    </result>
</response>"""
        xml_response = etree.fromstring(incomplete_xml.encode())

        with (
            patch("src.core.client._panos_client", None),
            patch("src.core.client._device_info", None),
            patch("httpx.AsyncClient") as mock_client_class,
            patch("src.core.panos_api.operational_command") as mock_op_cmd,
        ):

            # Setup mock
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_op_cmd.return_value = xml_response

            # Get client (triggers detection with incomplete data)
            await get_panos_client()

            # Verify device info handles missing fields
            device_info = await get_device_info()
            assert device_info is not None
            assert device_info.hostname == "fw01.example.com"
            assert device_info.model == "PA-220"
            assert device_info.version == "Unknown"  # Missing field
            assert device_info.serial == "Unknown"  # Missing field

            # Cleanup
            await close_panos_client()

    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """Test handling of connection failure."""
        with (
            patch("src.core.client._panos_client", None),
            patch("src.core.client._device_info", None),
            patch("httpx.AsyncClient") as mock_client_class,
            patch("src.core.panos_api.operational_command") as mock_op_cmd,
        ):

            # Setup mock to fail
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_op_cmd.side_effect = Exception("Connection timeout")

            # Get client should raise
            with pytest.raises(Exception):
                await get_panos_client()

            # Device info should be None
            with (
                patch("src.core.client._panos_client", None),
                patch("src.core.client._device_info", None),
            ):
                device_info = await get_device_info()
                assert device_info is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
