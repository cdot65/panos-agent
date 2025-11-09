"""Integration tests for operational command tools."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import Response

from src.tools.operational.interfaces import show_interfaces
from src.tools.operational.routing import show_routing_table
from src.tools.operational.sessions import show_sessions
from src.tools.operational.system import show_system_resources


class TestShowInterfaces:
    """Test show_interfaces operational command."""

    @pytest.mark.asyncio
    async def test_show_interfaces_success(self):
        """Test show_interfaces returns formatted output."""
        # Mock operational command response with interface XML
        interface_response = b"""<response status="success">
            <result>
                <ifnet>
                    <entry>
                        <name>ethernet1/1</name>
                        <zone>trust</zone>
                        <fwd>vr:default</fwd>
                        <vsys>1</vsys>
                        <dyn-addr/>
                        <addr6/>
                        <tag>0</tag>
                        <ip>10.1.1.1/24</ip>
                        <id>16</id>
                        <addr>10.1.1.1/24</addr>
                    </entry>
                    <entry>
                        <name>ethernet1/2</name>
                        <zone>untrust</zone>
                        <fwd>vr:default</fwd>
                        <vsys>1</vsys>
                        <dyn-addr/>
                        <addr6/>
                        <tag>0</tag>
                        <ip>192.168.1.1/24</ip>
                        <id>17</id>
                        <addr>192.168.1.1/24</addr>
                    </entry>
                </ifnet>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.post.return_value = Response(200, content=interface_response)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_interfaces.ainvoke({})
            
            # Should include interface information
            assert "ethernet1/1" in result
            assert "ethernet1/2" in result
            assert "10.1.1.1" in result
            assert "192.168.1.1" in result

    @pytest.mark.asyncio
    async def test_show_interfaces_empty_result(self):
        """Test show_interfaces with no interfaces."""
        # Mock empty response
        empty_response = b"""<response status="success">
            <result>
                <ifnet/>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.post.return_value = Response(200, content=empty_response)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_interfaces.ainvoke({})
            
            # Should handle empty result gracefully
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_show_interfaces_error_handling(self):
        """Test show_interfaces handles errors gracefully."""
        # Mock error response
        error_response = b'<response status="error"><result><msg>Command failed</msg></result></response>'

        mock_client = AsyncMock()
        mock_client.post.return_value = Response(400, content=error_response)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_interfaces.ainvoke({})
            
            # Should return error message
            assert "error" in result.lower() or "failed" in result.lower()


class TestShowRoutingTable:
    """Test show_routing_table operational command."""

    @pytest.mark.asyncio
    async def test_show_routing_table_success(self):
        """Test show_routing_table returns formatted output."""
        # Mock routing table XML response
        routing_response = b"""<response status="success">
            <result>
                <entry>
                    <virtual-router>default</virtual-router>
                    <destination>0.0.0.0/0</destination>
                    <nexthop>192.168.1.254</nexthop>
                    <metric>10</metric>
                    <flags>A S</flags>
                    <age>123456</age>
                    <interface>ethernet1/2</interface>
                    <route-table>unicast</route-table>
                </entry>
                <entry>
                    <virtual-router>default</virtual-router>
                    <destination>10.1.1.0/24</destination>
                    <nexthop>10.1.1.1</nexthop>
                    <metric>0</metric>
                    <flags>A C</flags>
                    <age>0</age>
                    <interface>ethernet1/1</interface>
                    <route-table>unicast</route-table>
                </entry>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.post.return_value = Response(200, content=routing_response)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_routing_table.ainvoke({})
            
            # Should include routing information
            assert "0.0.0.0/0" in result
            assert "10.1.1.0/24" in result
            assert "192.168.1.254" in result
            assert "default" in result.lower()

    @pytest.mark.asyncio
    async def test_show_routing_table_empty(self):
        """Test show_routing_table with no routes."""
        # Mock empty routing table
        empty_response = b"""<response status="success">
            <result/>
        </response>"""

        mock_client = AsyncMock()
        mock_client.post.return_value = Response(200, content=empty_response)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_routing_table.ainvoke({})
            
            # Should handle empty routing table gracefully
            assert isinstance(result, str)
            assert "routing" in result.lower() or "no routes" in result.lower()

    @pytest.mark.asyncio
    async def test_show_routing_table_error_handling(self):
        """Test show_routing_table handles errors."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection failed")

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_routing_table.ainvoke({})
            
            # Should return error message
            assert "error" in result.lower()


class TestShowSessions:
    """Test show_sessions operational command."""

    @pytest.mark.asyncio
    async def test_show_sessions_no_filter(self):
        """Test show_sessions without filters."""
        # Mock sessions XML response
        sessions_response = b"""<response status="success">
            <result>
                <total>2</total>
                <entry>
                    <source>10.1.1.5</source>
                    <sport>45678</sport>
                    <dst>8.8.8.8</dst>
                    <dport>53</dport>
                    <application>dns</application>
                    <state>ACTIVE</state>
                    <duration>30</duration>
                    <bytes>512</bytes>
                </entry>
                <entry>
                    <source>10.1.1.10</source>
                    <sport>54321</sport>
                    <dst>1.1.1.1</dst>
                    <dport>443</dport>
                    <application>ssl</application>
                    <state>ACTIVE</state>
                    <duration>120</duration>
                    <bytes>4096</bytes>
                </entry>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.post.return_value = Response(200, content=sessions_response)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_sessions.ainvoke({})
            
            # Should include session information
            assert "10.1.1.5" in result
            assert "8.8.8.8" in result
            assert "dns" in result.lower() or "ssl" in result.lower()
            assert "2" in result  # Total count

    @pytest.mark.asyncio
    async def test_show_sessions_with_source_filter(self):
        """Test show_sessions with source filter."""
        # Mock filtered sessions response
        sessions_response = b"""<response status="success">
            <result>
                <total>1</total>
                <entry>
                    <source>10.1.1.5</source>
                    <sport>45678</sport>
                    <dst>8.8.8.8</dst>
                    <dport>53</dport>
                    <application>dns</application>
                    <state>ACTIVE</state>
                    <duration>30</duration>
                    <bytes>512</bytes>
                </entry>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.post.return_value = Response(200, content=sessions_response)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_sessions.ainvoke({"source": "10.1.1.5"})
            
            # Should show filtered results
            assert "10.1.1.5" in result
            assert "from 10.1.1.5" in result.lower() or "source" in result.lower()

    @pytest.mark.asyncio
    async def test_show_sessions_with_destination_filter(self):
        """Test show_sessions with destination filter."""
        sessions_response = b"""<response status="success">
            <result>
                <total>1</total>
                <entry>
                    <source>10.1.1.10</source>
                    <sport>54321</sport>
                    <dst>8.8.8.8</dst>
                    <dport>53</dport>
                    <application>dns</application>
                    <state>ACTIVE</state>
                    <duration>15</duration>
                    <bytes>256</bytes>
                </entry>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.post.return_value = Response(200, content=sessions_response)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_sessions.ainvoke({"destination": "8.8.8.8"})
            
            assert "8.8.8.8" in result

    @pytest.mark.asyncio
    async def test_show_sessions_with_application_filter(self):
        """Test show_sessions with application filter."""
        sessions_response = b"""<response status="success">
            <result>
                <total>1</total>
                <entry>
                    <source>10.1.1.20</source>
                    <sport>12345</sport>
                    <dst>1.1.1.1</dst>
                    <dport>443</dport>
                    <application>ssl</application>
                    <state>ACTIVE</state>
                    <duration>60</duration>
                    <bytes>2048</bytes>
                </entry>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.post.return_value = Response(200, content=sessions_response)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_sessions.ainvoke({"application": "ssl"})
            
            assert "ssl" in result.lower()

    @pytest.mark.asyncio
    async def test_show_sessions_empty_result(self):
        """Test show_sessions with no active sessions."""
        empty_response = b"""<response status="success">
            <result>
                <total>0</total>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.post.return_value = Response(200, content=empty_response)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_sessions.ainvoke({})
            
            # Should handle empty sessions gracefully
            assert "0" in result or "no sessions" in result.lower()

    @pytest.mark.asyncio
    async def test_show_sessions_error_handling(self):
        """Test show_sessions handles errors."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("API error")

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_sessions.ainvoke({})
            
            assert "error" in result.lower()


class TestShowSystemResources:
    """Test show_system_resources operational command."""

    @pytest.mark.asyncio
    async def test_show_system_resources_success(self):
        """Test show_system_resources returns formatted output."""
        # Mock system resources XML response
        resources_response = b"""<response status="success">
            <result>
                <system>
                    <cpu>
                        <total>25</total>
                    </cpu>
                    <memory>
                        <total>8192</total>
                        <used>4096</used>
                        <free>4096</free>
                    </memory>
                    <disk>
                        <root>
                            <total>100000</total>
                            <used>45000</used>
                            <available>55000</available>
                        </root>
                        <log>
                            <total>200000</total>
                            <used>80000</used>
                            <available>120000</available>
                        </log>
                    </disk>
                </system>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.post.return_value = Response(200, content=resources_response)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_system_resources.ainvoke({})
            
            # Should include resource information
            assert "cpu" in result.lower() or "25" in result
            assert "memory" in result.lower() or "8192" in result
            assert "disk" in result.lower()

    @pytest.mark.asyncio
    async def test_show_system_resources_high_cpu(self):
        """Test show_system_resources with high CPU usage."""
        resources_response = b"""<response status="success">
            <result>
                <system>
                    <cpu>
                        <total>95</total>
                    </cpu>
                    <memory>
                        <total>8192</total>
                        <used>2048</used>
                        <free>6144</free>
                    </memory>
                </system>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.post.return_value = Response(200, content=resources_response)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_system_resources.ainvoke({})
            
            # Should show high CPU
            assert "95" in result

    @pytest.mark.asyncio
    async def test_show_system_resources_high_memory(self):
        """Test show_system_resources with high memory usage."""
        resources_response = b"""<response status="success">
            <result>
                <system>
                    <cpu>
                        <total>15</total>
                    </cpu>
                    <memory>
                        <total>8192</total>
                        <used>7680</used>
                        <free>512</free>
                    </memory>
                </system>
            </result>
        </response>"""

        mock_client = AsyncMock()
        mock_client.post.return_value = Response(200, content=resources_response)

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_system_resources.ainvoke({})
            
            # Should show high memory usage
            assert "7680" in result or "memory" in result.lower()

    @pytest.mark.asyncio
    async def test_show_system_resources_error_handling(self):
        """Test show_system_resources handles errors."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("System error")

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_system_resources.ainvoke({})
            
            assert "error" in result.lower()


class TestOperationalToolsIntegration:
    """Integration tests for multiple operational tools."""

    @pytest.mark.asyncio
    async def test_all_operational_tools_available(self):
        """Test that all operational tools are importable and callable."""
        # All tools should be importable
        assert callable(show_interfaces)
        assert callable(show_routing_table)
        assert callable(show_sessions)
        assert callable(show_system_resources)

    @pytest.mark.asyncio
    async def test_operational_tools_with_vsys_context(self, monkeypatch):
        """Test operational tools respect vsys context."""
        monkeypatch.setenv("PANOS_AGENT_VSYS", "vsys2")

        mock_response = Response(
            200,
            content=b"""<response status="success">
                <result>
                    <ifnet>
                        <entry>
                            <name>ethernet1/1</name>
                            <vsys>2</vsys>
                            <ip>10.2.1.1/24</ip>
                        </entry>
                    </ifnet>
                </result>
            </response>"""
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            result = await show_interfaces.ainvoke({})
            
            # Should work with vsys2 context
            assert "ethernet1/1" in result

    @pytest.mark.asyncio
    async def test_operational_tools_concurrent_execution(self):
        """Test that operational tools can be called concurrently."""
        import asyncio

        mock_client = AsyncMock()
        mock_client.post.return_value = Response(
            200,
            content=b'<response status="success"><result><total>0</total></result></response>'
        )

        with patch("src.core.client.get_panos_client", return_value=mock_client):
            # Execute multiple tools concurrently
            results = await asyncio.gather(
                show_interfaces.ainvoke({}),
                show_routing_table.ainvoke({}),
                show_sessions.ainvoke({}),
                show_system_resources.ainvoke({})
            )
            
            # All should complete successfully
            assert len(results) == 4
            assert all(isinstance(r, str) for r in results)

