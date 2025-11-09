# PAN-OS XML API Reference

> Guide to working with PAN-OS XML API using httpx and lxml

**Version**: 1.0  
**Last Updated**: 2025-01-09

---

## Table of Contents

1. [Overview](#overview)
2. [API Client Architecture](#api-client-architecture)
3. [Making API Requests](#making-api-requests)
4. [XML Generation](#xml-generation)
5. [XPath Mapping](#xpath-mapping)
6. [Error Handling](#error-handling)
7. [Testing with respx](#testing-with-respx)
8. [Common Patterns](#common-patterns)

---

## Overview

### Why httpx + lxml?

The agent uses a direct XML API integration instead of SDK wrappers for:

- **Full async support**: Non-blocking I/O with `httpx.AsyncClient`
- **Performance**: Faster XML parsing with lxml's C implementation
- **Control**: Direct control over XML generation and parsing
- **Flexibility**: Easy to add custom validation and transformations
- **Testing**: Better mocking with `respx` for integration tests

### API Endpoint

```
https://{firewall-ip}/api/
```

### Authentication

API key-based authentication via query parameter:

```python
params = {
    "type": "op",  # or "config"
    "cmd": "<xml-command>",
    "key": api_key,
    "xpath": "/config/...",  # for config operations
}
```

---

## API Client Architecture

### Core Components

```
src/core/
├── client.py              # Async client management
├── panos_api.py          # XML API functions
├── panos_models.py       # Pydantic response models
├── panos_xpath_map.py    # XPath mappings and validation
└── exceptions.py         # Custom exception types
```

### Client Management

**Singleton Pattern with Context Manager:**

```python
# src/core/client.py
async def get_panos_client() -> httpx.AsyncClient:
    """Get or create singleton httpx client."""
    global _client_instance
    
    if _client_instance is None:
        settings = get_settings()
        _client_instance = httpx.AsyncClient(
            base_url=f"https://{settings.panos_hostname}",
            verify=False,  # Self-signed certs
            timeout=30.0,
        )
    
    return _client_instance
```

**Usage in Functions:**

```python
async def get_config(xpath: str) -> str:
    """Get configuration via XML API."""
    client = await get_panos_client()
    settings = get_settings()
    
    params = {
        "type": "config",
        "action": "get",
        "xpath": xpath,
        "key": settings.panos_api_key,
    }
    
    response = await client.get("/api/", params=params)
    return response.text
```

---

## Making API Requests

### 1. Configuration Operations

#### Get Configuration

```python
from lxml import etree
from src.core.panos_api import get_config

async def get_address_object(name: str) -> dict:
    """Get address object by name."""
    xpath = f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address/entry[@name='{name}']"
    
    xml_response = await get_config(xpath)
    root = etree.fromstring(xml_response.encode())
    
    # Parse XML to dict
    entry = root.find(".//entry")
    if entry is not None:
        return {
            "name": entry.get("name"),
            "ip_netmask": entry.findtext("ip-netmask"),
            "description": entry.findtext("description"),
        }
    return None
```

#### Set Configuration

```python
from src.core.panos_api import set_config, build_object_xml

async def create_address_object(data: dict) -> None:
    """Create address object."""
    # Build XML from data
    xml_element = build_object_xml("address", data)
    
    xpath = "/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address"
    
    await set_config(xpath, xml_element)
```

#### Edit Configuration

```python
from src.core.panos_api import edit_config

async def update_address_object(name: str, data: dict) -> None:
    """Update existing address object."""
    xml_element = build_object_xml("address", data)
    
    xpath = f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address/entry[@name='{name}']"
    
    await edit_config(xpath, xml_element)
```

#### Delete Configuration

```python
from src.core.panos_api import delete_config

async def delete_address_object(name: str) -> None:
    """Delete address object."""
    xpath = f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address/entry[@name='{name}']"
    
    await delete_config(xpath)
```

### 2. Operational Commands

#### System Info

```python
async def get_system_info() -> dict:
    """Get firewall system information."""
    client = await get_panos_client()
    settings = get_settings()
    
    params = {
        "type": "op",
        "cmd": "<show><system><info></info></system></show>",
        "key": settings.panos_api_key,
    }
    
    response = await client.get("/api/", params=params)
    root = etree.fromstring(response.content)
    
    return {
        "hostname": root.findtext(".//hostname"),
        "sw_version": root.findtext(".//sw-version"),
        "model": root.findtext(".//model"),
    }
```

### 3. Commit Operations

```python
from src.core.panos_api import commit, get_job_status

async def commit_config() -> str:
    """Commit configuration and return job ID."""
    job_id = await commit()
    
    # Poll until complete
    while True:
        status = await get_job_status(job_id)
        if status.status in ["FIN", "FAIL"]:
            break
        await asyncio.sleep(2)
    
    return status.result
```

---

## XML Generation

### Using Structure Definitions

```python
from src.core.panos_api import build_object_xml

# Address object
xml = build_object_xml("address", {
    "name": "web-server",
    "ip-netmask": "10.0.0.1",
    "description": "Production web server",
    "tag": ["Web", "Production"]
})

# Output:
# <entry name="web-server">
#   <ip-netmask>10.0.0.1</ip-netmask>
#   <description>Production web server</description>
#   <tag>
#     <member>Web</member>
#     <member>Production</member>
#   </tag>
# </entry>
```

### Manual XML Construction

```python
from lxml import etree

def build_security_rule_xml(data: dict) -> str:
    """Build security rule XML."""
    entry = etree.Element("entry", attrib={"name": data["name"]})
    
    # From zones
    from_zone = etree.SubElement(entry, "from")
    for zone in data["from"]:
        member = etree.SubElement(from_zone, "member")
        member.text = zone
    
    # To zones
    to_zone = etree.SubElement(entry, "to")
    for zone in data["to"]:
        member = etree.SubElement(to_zone, "member")
        member.text = zone
    
    # Action
    action = etree.SubElement(entry, "action")
    action.text = data["action"]
    
    return etree.tostring(entry, encoding="unicode", pretty_print=True)
```

---

## XPath Mapping

### Using PanOSXPathMap

```python
from src.core.panos_xpath_map import PanOSXPathMap

# Get XPath for object type
xpath = PanOSXPathMap.get_xpath("address", name="web-server")
# Returns: "/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address/entry[@name='web-server']"

# Get list XPath
list_xpath = PanOSXPathMap.get_xpath("address_list")
# Returns: "/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address"

# Get structure definition
structure = PanOSXPathMap.get_structure("address")
# Returns field definitions and validation rules
```

### Validation

```python
from src.core.panos_xpath_map import PanOSXPathMap, validate_object_data

# Validate object name
is_valid, error = PanOSXPathMap.validate_object_name("web-server")
if not is_valid:
    raise ValueError(f"Invalid name: {error}")

# Validate object data
is_valid, error = validate_object_data("address", {
    "name": "web-server",
    "value": "10.0.0.1",
    "type": "ip-netmask",
})
if not is_valid:
    raise ValueError(f"Invalid data: {error}")
```

---

## Error Handling

### Custom Exceptions

```python
# src/core/panos_api.py

class PanOSAPIError(Exception):
    """Base exception for PAN-OS API errors."""
    pass

class PanOSConnectionError(PanOSAPIError):
    """Connection-related errors (retryable)."""
    pass

class PanOSValidationError(PanOSAPIError):
    """Validation errors (non-retryable)."""
    pass
```

### Parsing API Errors

```python
from lxml import etree
from src.core.panos_api import PanOSAPIError

async def make_api_request(params: dict):
    """Make API request with error handling."""
    client = await get_panos_client()
    response = await client.get("/api/", params=params)
    
    # Parse response
    root = etree.fromstring(response.content)
    status = root.get("status")
    
    if status == "error":
        code = root.get("code")
        message = root.findtext(".//msg/line")
        raise PanOSAPIError(f"API Error {code}: {message}")
    
    return root
```

### Retry Logic

```python
from src.core.retry_helper import with_retry_async

@with_retry_async(max_retries=3, base_delay=1.0)
async def get_config_with_retry(xpath: str) -> str:
    """Get config with automatic retry on transient errors."""
    return await get_config(xpath)
```

---

## Testing with respx

### Mocking HTTP Requests

```python
import pytest
import respx
from httpx import Response

@pytest.fixture
def mock_panos_api():
    """Mock PAN-OS API responses."""
    with respx.mock:
        # Mock successful get
        respx.get(
            url__regex=r".*/api/.*action=get.*"
        ).mock(
            return_value=Response(
                200,
                content=b'<response status="success"><result><entry name="test"/></result></response>'
            )
        )
        
        # Mock successful set
        respx.get(
            url__regex=r".*/api/.*action=set.*"
        ).mock(
            return_value=Response(
                200,
                content=b'<response status="success"><msg>command succeeded</msg></response>'
            )
        )
        
        yield

@pytest.mark.asyncio
async def test_create_address(mock_panos_api):
    """Test address creation with mocked API."""
    from src.core.panos_api import set_config
    
    await set_config("/config/path", "<entry name='test'/>")
    # Request is mocked, no real API call
```

### Async Client Fixture

```python
@pytest.fixture
async def mock_panos_client():
    """Mock httpx AsyncClient."""
    client = AsyncMock(spec=httpx.AsyncClient)
    
    success_response = Response(
        200,
        content=b'<response status="success"/>',
    )
    
    client.get = AsyncMock(return_value=success_response)
    client.post = AsyncMock(return_value=success_response)
    
    return client
```

---

## Common Patterns

### 1. List All Objects

```python
async def list_address_objects() -> list[dict]:
    """List all address objects."""
    xpath = PanOSXPathMap.get_xpath("address_list")
    xml_response = await get_config(xpath)
    
    root = etree.fromstring(xml_response.encode())
    addresses = []
    
    for entry in root.findall(".//entry"):
        addresses.append({
            "name": entry.get("name"),
            "ip_netmask": entry.findtext("ip-netmask"),
            "fqdn": entry.findtext("fqdn"),
            "description": entry.findtext("description"),
        })
    
    return addresses
```

### 2. Check Object Exists

```python
async def address_exists(name: str) -> bool:
    """Check if address object exists."""
    try:
        xpath = PanOSXPathMap.get_xpath("address", name=name)
        xml_response = await get_config(xpath)
        root = etree.fromstring(xml_response.encode())
        return root.find(".//entry") is not None
    except PanOSAPIError:
        return False
```

### 3. Bulk Operations

```python
async def create_multiple_addresses(addresses: list[dict]) -> list[str]:
    """Create multiple address objects."""
    results = []
    
    for addr_data in addresses:
        try:
            xml = build_object_xml("address", addr_data)
            xpath = PanOSXPathMap.get_xpath("address_list")
            await set_config(xpath, xml)
            results.append(f"✅ Created {addr_data['name']}")
        except PanOSAPIError as e:
            results.append(f"❌ Failed {addr_data['name']}: {e}")
    
    return results
```

### 4. Transactional Updates

```python
async def atomic_update(updates: list[dict]) -> None:
    """Perform atomic configuration update."""
    # Make all changes
    for update in updates:
        await apply_update(update)
    
    # Commit only if all succeed
    try:
        job_id = await commit()
        status = await poll_job(job_id)
        if status != "OK":
            raise PanOSAPIError(f"Commit failed: {status}")
    except Exception as e:
        # Changes will be discarded on next reboot
        # or can be explicitly reverted
        raise
```

---

## Best Practices

### 1. Connection Pooling

```python
# Use singleton client for connection pooling
client = await get_panos_client()  # Reuses connection

# Don't create new clients per request
# BAD: client = httpx.AsyncClient(...)  
```

### 2. Error Context

```python
try:
    await set_config(xpath, xml)
except PanOSAPIError as e:
    # Add context to errors
    raise PanOSAPIError(f"Failed to create {obj_name}: {e}") from e
```

### 3. XML Validation

```python
# Validate before API call
is_valid, error = validate_object_data(obj_type, data)
if not is_valid:
    raise PanOSValidationError(f"Invalid data: {error}")

# Then make API call
await set_config(xpath, xml)
```

### 4. Async Context

```python
# Keep async chain intact
async def high_level_function():
    result = await low_level_api_call()
    return result

# Only use asyncio.run() at entry points (tools)
def tool_function():
    return asyncio.run(high_level_function())
```

---

## Resources

- [PAN-OS XML API Guide](https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api)
- [httpx Documentation](https://www.python-httpx.org/)
- [lxml Documentation](https://lxml.de/)
- [respx Documentation](https://lundberg.github.io/respx/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)

---

**Questions?** See [ARCHITECTURE.md](./ARCHITECTURE.md) or [SETUP.md](./SETUP.md)
