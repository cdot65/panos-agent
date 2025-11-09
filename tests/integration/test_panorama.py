"""Integration tests for Panorama functionality."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import Response

from src.core.client import get_device_context
from src.core.panos_xpath_map import PanOSXPathMap
from src.tools.device_groups import device_group_create, device_group_list
from src.tools.templates import template_create, template_list
from src.tools.template_stacks import template_stack_create, template_stack_list
from src.tools.panorama_operations import panorama_commit_all, panorama_push_to_devices


class TestPanoramaDetection:
    """Test Panorama device detection."""

    @pytest.mark.asyncio
    async def test_panorama_device_detection(self):
        """Test that Panorama is detected correctly."""
        # Mock system info response with model="Panorama"
        system_info_xml = b"""<response status="success">
            <result>
                <system>
                    <hostname>panorama1</hostname>
                    <model>Panorama</model>
                    <serial>123456789</serial>
                    <sw-version>11.0.0</sw-version>
                </system>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.get.return_value = Response(200, content=system_info_xml)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            context = await get_device_context()
            
            assert context["device_type"] == "PANORAMA"
            assert context["model"] == "Panorama"
            assert context["hostname"] == "panorama1"
            assert context["serial"] == "123456789"

    @pytest.mark.asyncio
    async def test_firewall_device_detection(self):
        """Test that firewall is detected correctly."""
        # Mock system info response with model="PA-220"
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
            
            assert context["device_type"] == "FIREWALL"
            assert context["model"] == "PA-220"
            assert context["hostname"] == "fw1"
            assert context["serial"] == "987654321"


class TestPanoramaXPaths:
    """Test Panorama XPath generation."""

    def test_shared_context_xpath(self):
        """Test XPath for shared context."""
        context = {"device_type": "PANORAMA"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/config/shared/address" in xpath
        assert "entry[@name='test-addr']" in xpath

    def test_device_group_context_xpath(self):
        """Test XPath for device-group context."""
        context = {"device_type": "PANORAMA", "device_group": "Branch"}
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/device-group/entry[@name='Branch']" in xpath
        assert "/address/entry[@name='test-addr']" in xpath

    def test_template_context_xpath(self):
        """Test XPath for template context (highest priority)."""
        context = {
            "device_type": "PANORAMA",
            "device_group": "Branch",  # Should be ignored
            "template": "Branch-Template"
        }
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        # Template has highest priority
        assert "/template/entry[@name='Branch-Template']" in xpath
        # Should NOT contain device-group
        assert "device-group" not in xpath

    def test_template_stack_context_xpath(self):
        """Test XPath for template-stack context."""
        context = {
            "device_type": "PANORAMA",
            "template_stack": "Branch-Stack"
        }
        xpath = PanOSXPathMap.build_xpath("address", "test-addr", context)
        
        assert "/template-stack/entry[@name='Branch-Stack']" in xpath
        assert "/address/entry[@name='test-addr']" in xpath


class TestPanoramaDeviceGroups:
    """Test device group operations."""

    @pytest.mark.asyncio
    async def test_device_group_creation(self):
        """Test device group creation."""
        # Mock successful API response
        success_response = Response(
            200,
            content=b'<response status="success" code="20"><msg>command succeeded</msg></response>'
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = success_response
        mock_client.post.return_value = success_response

        # Mock device context as Panorama
        panorama_context = {
            "device_type": "PANORAMA",
            "hostname": "panorama1",
            "model": "Panorama",
            "version": "11.0.0",
            "serial": "123456789"
        }

        with patch("src.core.client.get_panos_client", return_value=mock_client), \
             patch("src.core.client.get_device_context", return_value=panorama_context):
            
            result = await device_group_create.ainvoke({
                "name": "Test-Group",
                "description": "Test device group"
            })
            
            assert "success" in result.lower() or "created" in result.lower()

    @pytest.mark.asyncio
    async def test_device_group_list(self):
        """Test listing device groups."""
        # Mock list response
        list_response = Response(
            200,
            content=b"""<response status="success">
                <result>
                    <entry name="All-Branches">
                        <description>All branch offices</description>
                    </entry>
                    <entry name="Production">
                        <description>Production firewalls</description>
                    </entry>
                </result>
            </response>"""
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = list_response

        # Mock device context as Panorama
        panorama_context = {
            "device_type": "PANORAMA",
            "hostname": "panorama1",
            "model": "Panorama",
            "version": "11.0.0",
            "serial": "123456789"
        }

        with patch("src.core.client.get_panos_client", return_value=mock_client), \
             patch("src.core.client.get_device_context", return_value=panorama_context):
            
            result = await device_group_list.ainvoke({})
            
            assert "All-Branches" in result
            assert "Production" in result


class TestPanoramaTemplates:
    """Test template operations."""

    @pytest.mark.asyncio
    async def test_template_creation(self):
        """Test template creation."""
        # Mock successful API response
        success_response = Response(
            200,
            content=b'<response status="success" code="20"><msg>command succeeded</msg></response>'
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = success_response
        mock_client.post.return_value = success_response

        # Mock device context as Panorama
        panorama_context = {
            "device_type": "PANORAMA",
            "hostname": "panorama1",
            "model": "Panorama",
            "version": "11.0.0",
            "serial": "123456789"
        }

        with patch("src.core.client.get_panos_client", return_value=mock_client), \
             patch("src.core.client.get_device_context", return_value=panorama_context):
            
            result = await template_create.ainvoke({
                "name": "Test-Template",
                "description": "Test template"
            })
            
            assert "success" in result.lower() or "created" in result.lower()

    @pytest.mark.asyncio
    async def test_template_list(self):
        """Test listing templates."""
        # Mock list response
        list_response = Response(
            200,
            content=b"""<response status="success">
                <result>
                    <entry name="Branch-Network">
                        <description>Branch network config</description>
                    </entry>
                    <entry name="Base-Config">
                        <description>Base configuration</description>
                    </entry>
                </result>
            </response>"""
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = list_response

        # Mock device context as Panorama
        panorama_context = {
            "device_type": "PANORAMA",
            "hostname": "panorama1",
            "model": "Panorama",
            "version": "11.0.0",
            "serial": "123456789"
        }

        with patch("src.core.client.get_panos_client", return_value=mock_client), \
             patch("src.core.client.get_device_context", return_value=panorama_context):
            
            result = await template_list.ainvoke({})
            
            assert "Branch-Network" in result
            assert "Base-Config" in result


class TestPanoramaTemplateStacks:
    """Test template stack operations."""

    @pytest.mark.asyncio
    async def test_template_stack_creation(self):
        """Test template stack creation."""
        # Mock successful API response
        success_response = Response(
            200,
            content=b'<response status="success" code="20"><msg>command succeeded</msg></response>'
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = success_response
        mock_client.post.return_value = success_response

        # Mock device context as Panorama
        panorama_context = {
            "device_type": "PANORAMA",
            "hostname": "panorama1",
            "model": "Panorama",
            "version": "11.0.0",
            "serial": "123456789"
        }

        with patch("src.core.client.get_panos_client", return_value=mock_client), \
             patch("src.core.client.get_device_context", return_value=panorama_context):
            
            result = await template_stack_create.ainvoke({
                "name": "Test-Stack",
                "templates": ["Base-Config", "Branch-Network"],
                "description": "Test stack"
            })
            
            assert "success" in result.lower() or "created" in result.lower()

    @pytest.mark.asyncio
    async def test_template_stack_list(self):
        """Test listing template stacks."""
        # Mock list response
        list_response = Response(
            200,
            content=b"""<response status="success">
                <result>
                    <entry name="Branch-Complete">
                        <description>Complete branch stack</description>
                        <templates>
                            <member>Base-Config</member>
                            <member>Branch-Network</member>
                        </templates>
                    </entry>
                </result>
            </response>"""
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = list_response

        # Mock device context as Panorama
        panorama_context = {
            "device_type": "PANORAMA",
            "hostname": "panorama1",
            "model": "Panorama",
            "version": "11.0.0",
            "serial": "123456789"
        }

        with patch("src.core.client.get_panos_client", return_value=mock_client), \
             patch("src.core.client.get_device_context", return_value=panorama_context):
            
            result = await template_stack_list.ainvoke({})
            
            assert "Branch-Complete" in result


class TestPanoramaOperations:
    """Test Panorama-specific operations."""

    @pytest.mark.asyncio
    async def test_panorama_commit_validation(self):
        """Test that panorama operations require Panorama device."""
        # Mock device context as firewall (not Panorama)
        firewall_context = {
            "device_type": "FIREWALL",
            "hostname": "fw1",
            "model": "PA-220",
            "version": "11.1.4",
            "serial": "987654321"
        }

        mock_client = AsyncMock()

        with patch("src.core.client.get_panos_client", return_value=mock_client), \
             patch("src.core.client.get_device_context", return_value=firewall_context):
            
            result = await panorama_commit_all.ainvoke({
                "device_groups": ["Test"]
            })
            
            # Should fail because device is not Panorama
            assert "error" in result.lower() or "panorama" in result.lower()

    @pytest.mark.asyncio
    async def test_panorama_push_validation(self):
        """Test that push operations require Panorama device."""
        # Mock device context as firewall (not Panorama)
        firewall_context = {
            "device_type": "FIREWALL",
            "hostname": "fw1",
            "model": "PA-220",
            "version": "11.1.4",
            "serial": "987654321"
        }

        mock_client = AsyncMock()

        with patch("src.core.client.get_panos_client", return_value=mock_client), \
             patch("src.core.client.get_device_context", return_value=firewall_context):
            
            result = await panorama_push_to_devices.ainvoke({
                "device_groups": ["Test"]
            })
            
            # Should fail because device is not Panorama
            assert "error" in result.lower() or "panorama" in result.lower()

