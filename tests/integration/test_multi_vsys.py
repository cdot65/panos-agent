"""Integration tests for multi-vsys functionality."""

import pytest
import os
from unittest.mock import AsyncMock, patch
from httpx import Response

from src.core.client import get_device_context, _detect_vsys
from src.core.panos_xpath_map import PanOSXPathMap
from src.tools.address_objects import address_create, address_list
from src.tools.security_policies import security_policy_create


class TestVsysDetection:
    """Test vsys detection and CLI override."""

    @pytest.mark.asyncio
    async def test_default_vsys_detection(self):
        """Test default vsys is vsys1."""
        # Mock firewall system info
        system_info_xml = b"""<response status="success">
            <result>
                <system>
                    <hostname>fw1</hostname>
                    <model>PA-220</model>
                    <serial>987654321</serial>
                    <sw-version>11.1.4</sw-version>
                </system>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.get.return_value = Response(200, content=system_info_xml)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            context = await get_device_context()
            
            # Default should be vsys1
            assert context["vsys"] == "vsys1"
            assert context["device_type"] == "FIREWALL"

    @pytest.mark.asyncio
    async def test_cli_vsys_override_vsys2(self, monkeypatch):
        """Test CLI override via environment variable to vsys2."""
        # Set environment variable for vsys override
        monkeypatch.setenv("PANOS_AGENT_VSYS", "vsys2")

        # Mock firewall system info
        system_info_xml = b"""<response status="success">
            <result>
                <system>
                    <hostname>fw1</hostname>
                    <model>PA-220</model>
                    <serial>987654321</serial>
                    <sw-version>11.1.4</sw-version>
                </system>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.get.return_value = Response(200, content=system_info_xml)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            context = await get_device_context()
            
            # Should override to vsys2
            assert context["vsys"] == "vsys2"
            assert context["device_type"] == "FIREWALL"

    @pytest.mark.asyncio
    async def test_cli_vsys_override_vsys3(self, monkeypatch):
        """Test CLI override via environment variable to vsys3."""
        # Set environment variable for vsys override
        monkeypatch.setenv("PANOS_AGENT_VSYS", "vsys3")

        # Mock firewall system info
        system_info_xml = b"""<response status="success">
            <result>
                <system>
                    <hostname>fw1</hostname>
                    <model>PA-220</model>
                    <serial>987654321</serial>
                    <sw-version>11.1.4</sw-version>
                </system>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.get.return_value = Response(200, content=system_info_xml)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            context = await get_device_context()
            
            # Should override to vsys3
            assert context["vsys"] == "vsys3"
            assert context["device_type"] == "FIREWALL"

    @pytest.mark.asyncio
    async def test_detect_vsys_with_cli_override(self, monkeypatch):
        """Test _detect_vsys function with CLI override."""
        monkeypatch.setenv("PANOS_AGENT_VSYS", "vsys4")
        
        mock_client = AsyncMock()
        vsys = await _detect_vsys(mock_client)
        
        assert vsys == "vsys4"

    @pytest.mark.asyncio
    async def test_detect_vsys_default(self):
        """Test _detect_vsys function defaults to vsys1."""
        # Ensure no environment override
        if "PANOS_AGENT_VSYS" in os.environ:
            del os.environ["PANOS_AGENT_VSYS"]
        
        mock_client = AsyncMock()
        vsys = await _detect_vsys(mock_client)
        
        assert vsys == "vsys1"


class TestVsysXPaths:
    """Test XPath generation for different vsys."""

    def test_vsys1_xpath(self):
        """Test XPath for vsys1 (default)."""
        context = {"device_type": "FIREWALL", "vsys": "vsys1"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/vsys/entry[@name='vsys1']" in xpath
        assert "/address/entry[@name='test-addr']" in xpath

    def test_vsys2_xpath(self):
        """Test XPath for vsys2."""
        context = {"device_type": "FIREWALL", "vsys": "vsys2"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/vsys/entry[@name='vsys2']" in xpath
        assert "/address/entry[@name='test-addr']" in xpath

    def test_vsys3_xpath(self):
        """Test XPath for vsys3."""
        context = {"device_type": "FIREWALL", "vsys": "vsys3"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/vsys/entry[@name='vsys3']" in xpath
        assert "/address/entry[@name='test-addr']" in xpath

    def test_vsys4_xpath(self):
        """Test XPath for vsys4."""
        context = {"device_type": "FIREWALL", "vsys": "vsys4"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/vsys/entry[@name='vsys4']" in xpath
        assert "/address/entry[@name='test-addr']" in xpath

    def test_custom_vsys_xpath(self):
        """Test XPath for custom vsys name."""
        context = {"device_type": "FIREWALL", "vsys": "vsys-tenant1"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/vsys/entry[@name='vsys-tenant1']" in xpath
        assert "/address/entry[@name='test-addr']" in xpath

    def test_vsys_with_underscore_xpath(self):
        """Test XPath for vsys name with underscore."""
        context = {"device_type": "FIREWALL", "vsys": "vsys_prod"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/vsys/entry[@name='vsys_prod']" in xpath
        assert "/address/entry[@name='test-addr']" in xpath

    def test_security_policy_vsys2_xpath(self):
        """Test XPath for security policy in vsys2."""
        context = {"device_type": "FIREWALL", "vsys": "vsys2"}
        xpath = PanOSXPathMap.build_xpath("security_policy", "test-rule", context)
        
        assert "/vsys/entry[@name='vsys2']" in xpath
        assert "/rulebase/security/rules/entry[@name='test-rule']" in xpath

    def test_service_vsys3_xpath(self):
        """Test XPath for service object in vsys3."""
        context = {"device_type": "FIREWALL", "vsys": "vsys3"}
        xpath = PanOSXPathMap.build_xpath("service", "test-svc", context)
        
        assert "/vsys/entry[@name='vsys3']" in xpath
        assert "/service/entry[@name='test-svc']" in xpath


class TestVsysOperations:
    """Test operations scoped to specific vsys."""

    @pytest.mark.asyncio
    async def test_create_object_in_vsys2(self, monkeypatch):
        """Test creating address object in vsys2."""
        monkeypatch.setenv("PANOS_AGENT_VSYS", "vsys2")

        # Mock successful API response
        success_response = Response(
            200,
            content=b'<response status="success" code="20"><msg>command succeeded</msg></response>'
        )

        # Mock firewall system info
        system_info_xml = b"""<response status="success">
            <result>
                <system>
                    <hostname>fw1</hostname>
                    <model>PA-220</model>
                    <serial>987654321</serial>
                    <sw-version>11.1.4</sw-version>
                </system>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.get.return_value = Response(200, content=system_info_xml)
        mock_client.post.return_value = success_response

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await address_create.ainvoke({
                "name": "test-server",
                "value": "10.2.1.100",
                "type": "ip-netmask",
                "description": "Test server in vsys2"
            })
            
            # Should succeed
            assert "success" in result.lower() or "created" in result.lower()

    @pytest.mark.asyncio
    async def test_list_objects_in_vsys3(self, monkeypatch):
        """Test listing address objects in vsys3."""
        monkeypatch.setenv("PANOS_AGENT_VSYS", "vsys3")

        # Mock list response
        list_response = Response(
            200,
            content=b"""<response status="success">
                <result>
                    <entry name="server-1">
                        <ip-netmask>10.3.1.1</ip-netmask>
                        <description>Server 1 in vsys3</description>
                    </entry>
                    <entry name="server-2">
                        <ip-netmask>10.3.1.2</ip-netmask>
                        <description>Server 2 in vsys3</description>
                    </entry>
                </result>
            </response>"""
        )

        # Mock firewall system info
        system_info_xml = b"""<response status="success">
            <result>
                <system>
                    <hostname>fw1</hostname>
                    <model>PA-220</model>
                    <serial>987654321</serial>
                    <sw-version>11.1.4</sw-version>
                </system>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.get.return_value = Response(200, content=system_info_xml)
        # First call gets system info, second gets list
        mock_client.get.side_effect = [
            Response(200, content=system_info_xml),
            list_response
        ]

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await address_list.ainvoke({})
            
            # Should list objects from vsys3
            assert "server-1" in result
            assert "server-2" in result
            assert "vsys3" in result.lower() or "10.3.1" in result

    @pytest.mark.asyncio
    async def test_create_policy_in_vsys4(self, monkeypatch):
        """Test creating security policy in vsys4."""
        monkeypatch.setenv("PANOS_AGENT_VSYS", "vsys4")

        # Mock successful API response
        success_response = Response(
            200,
            content=b'<response status="success" code="20"><msg>command succeeded</msg></response>'
        )

        # Mock firewall system info
        system_info_xml = b"""<response status="success">
            <result>
                <system>
                    <hostname>fw1</hostname>
                    <model>PA-220</model>
                    <serial>987654321</serial>
                    <sw-version>11.1.4</sw-version>
                </system>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.get.return_value = Response(200, content=system_info_xml)
        mock_client.post.return_value = success_response

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await security_policy_create.ainvoke({
                "name": "test-rule",
                "fromzone": ["trust"],
                "tozone": ["untrust"],
                "source": ["any"],
                "destination": ["any"],
                "service": ["application-default"],
                "action": "allow",
                "description": "Test rule in vsys4"
            })
            
            # Should succeed
            assert "success" in result.lower() or "created" in result.lower()


class TestVsysBackwardCompatibility:
    """Test backward compatibility (vsys defaults)."""

    def test_no_vsys_defaults_to_vsys1(self):
        """Test that missing vsys defaults to vsys1."""
        context = {"device_type": "FIREWALL"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        # Should default to vsys1
        assert "/vsys/entry[@name='vsys1']" in xpath

    def test_empty_vsys_defaults_to_vsys1(self):
        """Test that empty vsys defaults to vsys1."""
        context = {"device_type": "FIREWALL", "vsys": None}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        # Should default to vsys1
        assert "/vsys/entry[@name='vsys1']" in xpath

    def test_panorama_ignores_vsys(self):
        """Test that Panorama ignores vsys parameter."""
        context = {
            "device_type": "PANORAMA",
            "vsys": "vsys2"  # Should be ignored
        }
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        # Should use shared context, not vsys
        assert "/config/shared/address" in xpath
        assert "vsys" not in xpath


class TestVsysEdgeCases:
    """Test edge cases for vsys handling."""

    def test_vsys_with_dashes(self):
        """Test vsys name with dashes."""
        context = {"device_type": "FIREWALL", "vsys": "vsys-tenant-1"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/vsys/entry[@name='vsys-tenant-1']" in xpath

    def test_vsys_numeric_only(self):
        """Test vsys with only numbers (edge case)."""
        context = {"device_type": "FIREWALL", "vsys": "123"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/vsys/entry[@name='123']" in xpath

    def test_vsys_mixed_case(self):
        """Test vsys with mixed case."""
        context = {"device_type": "FIREWALL", "vsys": "Vsys2"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/vsys/entry[@name='Vsys2']" in xpath

