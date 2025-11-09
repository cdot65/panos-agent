"""Pytest configuration and shared fixtures for PAN-OS agent tests."""

from unittest.mock import AsyncMock, MagicMock, Mock

import httpx
import pytest
from httpx import Response


@pytest.fixture
async def mock_httpx_client():
    """Mock httpx AsyncClient for PAN-OS API testing.
    
    Returns:
        AsyncMock of httpx.AsyncClient with successful responses
    """
    client = AsyncMock(spec=httpx.AsyncClient)
    
    # Mock successful API response
    success_response = Response(
        200,
        content=b'<response status="success" code="20"><msg>command succeeded</msg></response>',
    )
    
    client.get = AsyncMock(return_value=success_response)
    client.post = AsyncMock(return_value=success_response)
    client.aclose = AsyncMock()
    
    return client


@pytest.fixture
def mock_firewall():
    """Mock PAN-OS firewall client (legacy - for backward compatibility).
    
    Note: New tests should use mock_httpx_client instead.
    """
    fw = MagicMock()
    fw.hostname = "192.168.1.1"
    fw.version = "10.2.3"
    fw.serial = "123456789"
    fw.refreshall = Mock()
    fw.find = Mock()
    fw.findall = Mock(return_value=[])
    fw.add = Mock()
    fw.commit = Mock()
    return fw


@pytest.fixture
def mock_address_object():
    """Mock address object."""
    addr = MagicMock()
    addr.name = "test-address"
    addr.value = "10.1.1.1"
    addr.type = "ip-netmask"
    addr.description = "Test address"
    addr.tag = []
    addr.create = Mock()
    addr.apply = Mock()
    addr.delete = Mock()
    return addr


@pytest.fixture
def mock_address_group():
    """Mock address group."""
    group = MagicMock()
    group.name = "test-group"
    group.static_value = ["addr-1", "addr-2"]
    group.description = "Test group"
    group.tag = []
    group.create = Mock()
    group.apply = Mock()
    group.delete = Mock()
    return group


@pytest.fixture
def mock_service_object():
    """Mock service object."""
    svc = MagicMock()
    svc.name = "test-service"
    svc.protocol = "tcp"
    svc.destination_port = "8080"
    svc.description = "Test service"
    svc.tag = []
    svc.create = Mock()
    svc.apply = Mock()
    svc.delete = Mock()
    return svc


@pytest.fixture
def mock_security_rule():
    """Mock security policy rule."""
    rule = MagicMock()
    rule.name = "test-rule"
    rule.fromzone = ["trust"]
    rule.tozone = ["untrust"]
    rule.source = ["any"]
    rule.destination = ["any"]
    rule.service = ["application-default"]
    rule.action = "allow"
    rule.create = Mock()
    rule.apply = Mock()
    rule.delete = Mock()
    return rule


@pytest.fixture
def sample_addresses():
    """Sample address objects for batch tests."""
    return [
        {"name": "addr-1", "value": "10.1.1.1"},
        {"name": "addr-2", "value": "10.1.1.2"},
        {"name": "addr-3", "value": "10.1.1.3"},
    ]


@pytest.fixture
def mock_commit_result():
    """Mock commit job result."""
    result = MagicMock()
    result.id = 123
    result.status = "FIN"
    result.result = "OK"
    return result
