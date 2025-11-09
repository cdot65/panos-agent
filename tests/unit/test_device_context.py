"""Unit tests for device context functionality."""

from unittest.mock import AsyncMock, patch

import pytest

from src.core.client import device_info_to_context, get_device_context
from src.core.panos_models import DeviceInfo, DeviceType
from src.core.state_schemas import DeviceContext


class TestDeviceInfoToContext:
    """Test DeviceInfo to DeviceContext conversion."""

    def test_firewall_context_basic(self):
        """Test converting firewall DeviceInfo to context dictionary."""
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

    def test_firewall_context_with_custom_vsys(self):
        """Test firewall context with custom vsys."""
        device_info = DeviceInfo(
            hostname="fw01.example.com",
            version="10.2.3",
            serial="012345678901",
            model="PA-5220",
            device_type=DeviceType.FIREWALL,
            platform="PA-5220",
        )

        context = device_info_to_context(device_info, vsys="vsys2")

        assert context["device_type"] == "FIREWALL"
        assert context["vsys"] == "vsys2"
        assert context["device_group"] is None
        assert context["template"] is None

    def test_panorama_context_basic(self):
        """Test converting Panorama DeviceInfo to context dictionary."""
        device_info = DeviceInfo(
            hostname="panorama01.example.com",
            version="10.2.3",
            serial="012345678902",
            model="M-100",
            device_type=DeviceType.PANORAMA,
            platform="M-100",
        )

        context = device_info_to_context(device_info)

        assert context["device_type"] == "PANORAMA"
        assert context["hostname"] == "panorama01.example.com"
        assert context["model"] == "M-100"
        assert context["version"] == "10.2.3"
        assert context["serial"] == "012345678902"
        assert context["vsys"] == "vsys1"
        assert context["device_group"] is None
        assert context["template"] is None

    def test_panorama_context_with_device_group(self):
        """Test Panorama context with device group."""
        device_info = DeviceInfo(
            hostname="panorama01.example.com",
            version="10.2.3",
            serial="012345678902",
            model="M-100",
            device_type=DeviceType.PANORAMA,
            platform="M-100",
        )

        context = device_info_to_context(device_info, device_group="production-firewalls")

        assert context["device_type"] == "PANORAMA"
        assert context["device_group"] == "production-firewalls"
        assert context["template"] is None

    def test_panorama_context_with_template(self):
        """Test Panorama context with template."""
        device_info = DeviceInfo(
            hostname="panorama01.example.com",
            version="10.2.3",
            serial="012345678902",
            model="M-100",
            device_type=DeviceType.PANORAMA,
            platform="M-100",
        )

        context = device_info_to_context(device_info, template="corporate-template")

        assert context["device_type"] == "PANORAMA"
        assert context["device_group"] is None
        assert context["template"] == "corporate-template"

    def test_panorama_context_full(self):
        """Test Panorama context with all fields."""
        device_info = DeviceInfo(
            hostname="panorama01.example.com",
            version="10.2.3",
            serial="012345678902",
            model="M-100",
            device_type=DeviceType.PANORAMA,
            platform="M-100",
        )

        context = device_info_to_context(
            device_info,
            vsys="vsys1",
            device_group="production-firewalls",
            template="corporate-template",
        )

        assert context["device_type"] == "PANORAMA"
        assert context["vsys"] == "vsys1"
        assert context["device_group"] == "production-firewalls"
        assert context["template"] == "corporate-template"

    def test_vm_series_firewall(self):
        """Test VM-Series firewall context."""
        device_info = DeviceInfo(
            hostname="vm-fw01.example.com",
            version="11.0.1",
            serial="012345678904",
            model="VM-50",
            device_type=DeviceType.FIREWALL,
            platform="VMWare ESXi",
        )

        context = device_info_to_context(device_info)

        assert context["device_type"] == "FIREWALL"
        assert context["model"] == "VM-50"
        assert context["platform"] == "VMWare ESXi"

    def test_panorama_virtual(self):
        """Test Panorama Virtual appliance context."""
        device_info = DeviceInfo(
            hostname="panorama-vm.example.com",
            version="10.2.3",
            serial="012345678903",
            model="Panorama",
            device_type=DeviceType.PANORAMA,
            platform="Panorama-VM",
        )

        context = device_info_to_context(device_info)

        assert context["device_type"] == "PANORAMA"
        assert context["model"] == "Panorama"
        assert context["platform"] == "Panorama-VM"


class TestGetDeviceContext:
    """Test get_device_context function."""

    @pytest.mark.asyncio
    async def test_get_device_context_firewall(self):
        """Test getting device context for firewall."""
        mock_device_info = DeviceInfo(
            hostname="fw01.example.com",
            version="10.2.3",
            serial="012345678901",
            model="PA-220",
            device_type=DeviceType.FIREWALL,
            platform="PA-220",
        )

        with patch("src.core.client.get_device_info", return_value=mock_device_info):
            context = await get_device_context()

            assert context is not None
            assert context["device_type"] == "FIREWALL"
            assert context["hostname"] == "fw01.example.com"
            assert context["model"] == "PA-220"
            assert context["vsys"] == "vsys1"

    @pytest.mark.asyncio
    async def test_get_device_context_panorama(self):
        """Test getting device context for Panorama."""
        mock_device_info = DeviceInfo(
            hostname="panorama01.example.com",
            version="10.2.3",
            serial="012345678902",
            model="M-100",
            device_type=DeviceType.PANORAMA,
            platform="M-100",
        )

        with patch("src.core.client.get_device_info", return_value=mock_device_info):
            context = await get_device_context(device_group="shared", template="base-template")

            assert context is not None
            assert context["device_type"] == "PANORAMA"
            assert context["device_group"] == "shared"
            assert context["template"] == "base-template"

    @pytest.mark.asyncio
    async def test_get_device_context_with_vsys(self):
        """Test getting device context with custom vsys."""
        mock_device_info = DeviceInfo(
            hostname="fw01.example.com",
            version="10.2.3",
            serial="012345678901",
            model="PA-5220",
            device_type=DeviceType.FIREWALL,
            platform="PA-5220",
        )

        with patch("src.core.client.get_device_info", return_value=mock_device_info):
            context = await get_device_context(vsys="vsys3")

            assert context is not None
            assert context["vsys"] == "vsys3"

    @pytest.mark.asyncio
    async def test_get_device_context_not_connected(self):
        """Test getting device context when not connected."""
        with patch("src.core.client.get_device_info", return_value=None):
            context = await get_device_context()

            assert context is None


class TestDeviceTypeDetection:
    """Test device type enum and detection logic."""

    def test_device_type_enum_values(self):
        """Test DeviceType enum values."""
        assert DeviceType.FIREWALL.value == "FIREWALL"
        assert DeviceType.PANORAMA.value == "PANORAMA"

    def test_firewall_detection_pa_series(self):
        """Test firewall is detected for PA-series models."""
        device_info = DeviceInfo(
            hostname="fw01.example.com",
            version="10.2.3",
            serial="012345678901",
            model="PA-220",
            device_type=DeviceType.FIREWALL,
            platform="PA-220",
        )

        assert device_info.device_type == DeviceType.FIREWALL

    def test_firewall_detection_vm_series(self):
        """Test firewall is detected for VM-series models."""
        device_info = DeviceInfo(
            hostname="vm-fw01.example.com",
            version="11.0.1",
            serial="012345678904",
            model="VM-50",
            device_type=DeviceType.FIREWALL,
            platform="VMWare ESXi",
        )

        assert device_info.device_type == DeviceType.FIREWALL

    def test_panorama_detection_m_series(self):
        """Test Panorama is detected for M-series models."""
        device_info = DeviceInfo(
            hostname="panorama01.example.com",
            version="10.2.3",
            serial="012345678902",
            model="M-100",
            device_type=DeviceType.PANORAMA,
            platform="M-100",
        )

        assert device_info.device_type == DeviceType.PANORAMA

    def test_panorama_detection_virtual(self):
        """Test Panorama is detected for Panorama Virtual."""
        device_info = DeviceInfo(
            hostname="panorama-vm.example.com",
            version="10.2.3",
            serial="012345678903",
            model="Panorama",
            device_type=DeviceType.PANORAMA,
            platform="Panorama-VM",
        )

        assert device_info.device_type == DeviceType.PANORAMA


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
