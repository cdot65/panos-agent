# PAN-OS XPath Mapping Reference

Based on actual running-config.xml from PAN-OS 11.1.4

## Overview

This document provides XPath expressions for all supported object types, validated against a real PAN-OS configuration.

## Base Configuration Path

```xpath
/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']
```

All object paths are relative to this base.

---

## Address Objects

### XPath Expressions

**List all addresses:**
```xpath
/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address
```

**Get specific address:**
```xpath
/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address/entry[@name='{name}']
```

### XML Structure (from actual config)

```xml
<entry name="Auth Server">
  <ip-netmask>172.16.0.2</ip-netmask>
  <description>Synology NAS playing the role of RADIUS and LDAP</description>
  <tag>
    <member>GlobalProtect</member>
    <member>Auth</member>
  </tag>
</entry>
```

### Fields

| Field | XML Path | Type | Required | Example |
|-------|----------|------|----------|---------|
| Name | `@name` attribute | string | ✅ | "Auth Server" |
| IP/Netmask | `ip-netmask` | string | ✅* | "172.16.0.2" or "10.0.0.0/24" |
| IP Range | `ip-range` | string | ✅* | "10.0.0.1-10.0.0.100" |
| FQDN | `fqdn` | string | ✅* | "example.com" |
| Description | `description` | string | ❌ | "Server description" |
| Tags | `tag/member` | list | ❌ | ["GlobalProtect", "Auth"] |

*One of ip-netmask, ip-range, or fqdn is required

---

## Address Groups

### XPath Expressions

**List all address groups:**
```xpath
/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address-group
```

**Get specific address group:**
```xpath
/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address-group/entry[@name='{name}']
```

### XML Structure (from actual config)

```xml
<entry name="GP-Baddies">
  <static>
    <member>192.168.1.100</member>
    <member>192.168.1.101</member>
  </static>
  <description>Bad actors attempting GP login</description>
  <tag>
    <member>Security</member>
  </tag>
</entry>
```

### Fields

| Field | XML Path | Type | Required | Example |
|-------|----------|------|----------|---------|
| Name | `@name` attribute | string | ✅ | "GP-Baddies" |
| Static Members | `static/member` | list | ✅* | ["addr1", "addr2"] |
| Dynamic Filter | `dynamic/filter` | string | ✅* | "'tag1' or 'tag2'" |
| Description | `description` | string | ❌ | "Group description" |
| Tags | `tag/member` | list | ❌ | ["Security"] |

*Either static members or dynamic filter is required

---

## Service Objects

### XPath Expressions

**List all services:**
```xpath
/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/service
```

**Get specific service:**
```xpath
/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/service/entry[@name='{name}']
```

### XML Structure (from actual config)

```xml
<entry name="EDA">
  <protocol>
    <tcp>
      <port>5000</port>
      <override>
        <no />
      </override>
    </tcp>
  </protocol>
</entry>
```

### Fields

| Field | XML Path | Type | Required | Example |
|-------|----------|------|----------|---------|
| Name | `@name` attribute | string | ✅ | "EDA" |
| Protocol | `protocol/tcp` or `protocol/udp` | element | ✅ | tcp or udp |
| Port (TCP) | `protocol/tcp/port` | string | ✅* | "5000" or "8080-8090" |
| Port (UDP) | `protocol/udp/port` | string | ✅* | "53" |
| Description | `description` | string | ❌ | "Service description" |
| Tags | `tag/member` | list | ❌ | ["Web"] |

*Port required for the specified protocol

---

## Service Groups

### XPath Expressions

**List all service groups:**
```xpath
/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/service-group
```

**Get specific service group:**
```xpath
/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/service-group/entry[@name='{name}']
```

### XML Structure

```xml
<entry name="web-services">
  <members>
    <member>service-http</member>
    <member>service-https</member>
  </members>
  <tag>
    <member>Web</member>
  </tag>
</entry>
```

### Fields

| Field | XML Path | Type | Required | Example |
|-------|----------|------|----------|---------|
| Name | `@name` attribute | string | ✅ | "web-services" |
| Members | `members/member` | list | ✅ | ["service-http", "service-https"] |
| Tags | `tag/member` | list | ❌ | ["Web"] |

---

## Security Policies

### XPath Expressions

**List all security rules:**
```xpath
/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/rulebase/security/rules
```

**Get specific security rule:**
```xpath
/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/rulebase/security/rules/entry[@name='{name}']
```

### XML Structure (from actual config)

```xml
<entry name="Block GP Login Failures" uuid="56b47e79-7fe2-42c6-947e-a8a33969a006">
  <to>
    <member>any</member>
  </to>
  <from>
    <member>any</member>
  </from>
  <source>
    <member>GP-Baddies</member>
  </source>
  <destination>
    <member>any</member>
  </destination>
  <source-user>
    <member>any</member>
  </source-user>
  <category>
    <member>any</member>
  </category>
  <application>
    <member>any</member>
  </application>
  <service>
    <member>any</member>
  </service>
  <source-hip>
    <member>any</member>
  </source-hip>
  <destination-hip>
    <member>any</member>
  </destination-hip>
  <tag>
    <member>Automation</member>
  </tag>
  <action>drop</action>
</entry>
```

### Fields

| Field | XML Path | Type | Required | Example |
|-------|----------|------|----------|---------|
| Name | `@name` attribute | string | ✅ | "Block GP Login Failures" |
| UUID | `@uuid` attribute | string | ❌ | Auto-generated by PAN-OS |
| From Zones | `from/member` | list | ✅ | ["trust"] or ["any"] |
| To Zones | `to/member` | list | ✅ | ["untrust"] or ["any"] |
| Source Addresses | `source/member` | list | ✅ | ["GP-Baddies"] or ["any"] |
| Destination Addresses | `destination/member` | list | ✅ | ["any"] |
| Source Users | `source-user/member` | list | ✅ | ["any"] |
| Applications | `application/member` | list | ✅ | ["any"] or ["ssl", "web-browsing"] |
| Services | `service/member` | list | ✅ | ["any"] or ["application-default"] |
| Category | `category/member` | list | ❌ | ["any"] |
| Source HIP | `source-hip/member` | list | ❌ | ["any"] |
| Destination HIP | `destination-hip/member` | list | ❌ | ["any"] |
| Action | `action` | string | ✅ | "allow", "deny", "drop" |
| Tags | `tag/member` | list | ❌ | ["Automation"] |
| Log End | `log-end` | string | ❌ | "yes" or "no" |
| Description | `description` | string | ❌ | "Rule description" |
| Disabled | `disabled` | string | ❌ | "yes" or "no" |

---

## NAT Policies

### XPath Expressions

**List all NAT rules:**
```xpath
/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/rulebase/nat/rules
```

**Get specific NAT rule:**
```xpath
/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/rulebase/nat/rules/entry[@name='{name}']
```

### XML Structure

```xml
<entry name="outbound-nat" uuid="...">
  <nat-type>ipv4</nat-type>
  <from>
    <member>trust</member>
  </from>
  <to>
    <member>untrust</member>
  </to>
  <source>
    <member>10.0.0.0/8</member>
  </source>
  <destination>
    <member>any</member>
  </destination>
  <service>any</service>
  <source-translation>
    <dynamic-ip-and-port>
      <interface-address>
        <interface>ethernet1/1</interface>
      </interface-address>
    </dynamic-ip-and-port>
  </source-translation>
  <tag>
    <member>Automation</member>
  </tag>
  <description>Outbound NAT</description>
</entry>
```

### Fields

| Field | XML Path | Type | Required | Example |
|-------|----------|------|----------|---------|
| Name | `@name` attribute | string | ✅ | "outbound-nat" |
| UUID | `@uuid` attribute | string | ❌ | Auto-generated by PAN-OS |
| NAT Type | `nat-type` | string | ✅ | "ipv4", "nat64", "nptv6" |
| From Zones | `from/member` | list | ✅ | ["trust"] |
| To Zones | `to/member` | list | ✅ | ["untrust"] |
| Source Addresses | `source/member` | list | ✅ | ["10.0.0.0/8"] |
| Destination Addresses | `destination/member` | list | ✅ | ["any"] |
| Service | `service` | string | ✅ | "any" or service name |
| Source Translation | `source-translation/*` | complex | ❌ | Dynamic IP and Port |
| Destination Translation | `destination-translation/*` | complex | ❌ | Static IP |
| Tags | `tag/member` | list | ❌ | ["Automation"] |
| Description | `description` | string | ❌ | "NAT description" |
| Disabled | `disabled` | string | ❌ | "yes" or "no" |

---

## API Operations

### Common API Patterns

**Get Configuration (type=config, action=get):**
```
https://{firewall}/api/?type=config&action=get&xpath={xpath}&key={api_key}
```

**Set Configuration (type=config, action=set):**
```
https://{firewall}/api/?type=config&action=set&xpath={xpath}&element={xml}&key={api_key}
```

**Edit Configuration (type=config, action=edit):**
```
https://{firewall}/api/?type=config&action=edit&xpath={xpath}&element={xml}&key={api_key}
```

**Delete Configuration (type=config, action=delete):**
```
https://{firewall}/api/?type=config&action=delete&xpath={xpath}&key={api_key}
```

**Commit (type=commit, cmd):**
```
https://{firewall}/api/?type=commit&cmd=<commit></commit>&key={api_key}
```

---

## Validation Rules

### Object Name Validation

- **Maximum length:** 63 characters
- **Allowed characters:** Alphanumeric, hyphen (-), underscore (_), period (.), space
- **Restrictions:**
  - Cannot start with space or underscore
  - Cannot contain consecutive spaces
- **Regular expression:** `^[a-zA-Z0-9][a-zA-Z0-9\-_. ]{0,62}$`

### IP Address Validation

**IP/Netmask format:**
- Single IP: `192.168.1.1`
- CIDR notation: `192.168.1.0/24`
- Regex: `^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(/\d{1,2})?$`

**IP Range format:**
- Format: `192.168.1.1-192.168.1.100`
- Regex: `^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}-\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$`

### Port Validation

- **Single port:** `80`, `443`, `8080`
- **Port range:** `8080-8090`, `1000-2000`
- **Multiple ports:** `80,443,8080`
- **Valid range:** 1-65535
- **Regex:** `^\d{1,5}(-\d{1,5})?(,\d{1,5}(-\d{1,5})?)*$`

---

## Python Usage Examples

### Using XPath Mapping

```python
from src.core.panos_xpath_map import PanOSXPathMap

# Get XPath for specific address object
xpath = PanOSXPathMap.get_xpath("address", "web-server")
# Returns: /config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address/entry[@name='web-server']

# Get XPath for listing all addresses
xpath = PanOSXPathMap.get_xpath("address_list")
# Returns: /config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address

# Validate object name
is_valid, error = PanOSXPathMap.validate_object_name("my-server")
# Returns: (True, None)

is_valid, error = PanOSXPathMap.validate_object_name("_invalid")
# Returns: (False, "Name cannot start with space or underscore")
```

### Validating Object Data

```python
from src.core.panos_xpath_map import validate_object_data

# Validate address object
is_valid, error = validate_object_data("address", {
    "name": "web-server",
    "value": "10.1.1.100",
    "type": "ip-netmask"
})
# Returns: (True, None)

# Validate service object
is_valid, error = validate_object_data("service", {
    "name": "web-http",
    "protocol": "tcp",
    "tcp_port": "8080"
})
# Returns: (True, None)
```

---

## Related Files

- **XPath Implementation:** `src/core/panos_xpath_map.py`
- **API Layer:** `src/core/panos_api.py`
- **Response Models:** `src/core/panos_models.py`
- **Analysis Script:** `scripts/analyze_panos_config.py`
- **Examples:** `docs/panos_config/examples/`

---

## References

- [PAN-OS XML API Guide](https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api/get-started-with-the-pan-os-xml-api)
- [PAN-OS XPath Documentation](https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api/pan-os-xml-api-request-types/configuration-api/xpath-syntax)
- [Configuration Tree](https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api/pan-os-xml-api-request-types/configuration-api)

---

**Last Updated:** 2025-01-09  
**PAN-OS Version:** 11.1.4  
**Config Source:** Actual running-config.xml from production firewall

