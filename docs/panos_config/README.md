## PAN-OS Configuration Reference

This directory contains reference PAN-OS configuration files for development and testing.

---

## 📚 Documentation Index

- **[README.md](README.md)** (this file) - Overview and configuration setup
- **[QUICK_START.md](QUICK_START.md)** - 5-minute quick start guide ⚡
- **[XPATH_MAPPING.md](XPATH_MAPPING.md)** - Complete XPath reference
- **[SUMMARY.md](SUMMARY.md)** - Configuration analysis results
- **[INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md)** - Integration details
- **[COMPLETION_SUMMARY.md](COMPLETION_SUMMARY.md)** - Task completion status ✅

### 🚀 Quick Links

**For New Users:** Start with [QUICK_START.md](QUICK_START.md)

**For Developers:** See [INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md) and [XPATH_MAPPING.md](XPATH_MAPPING.md)

**For Project Managers:** Check [COMPLETION_SUMMARY.md](COMPLETION_SUMMARY.md)

---

### `running-config.xml`

Place your PAN-OS running configuration export here to:

1. **Validate XML structure** - Ensure our generated XML matches actual PAN-OS format
2. **Test XPath expressions** - Verify our XPath mappings work with real config
3. **Extract examples** - Get real-world examples of different object types
4. **Schema validation** - Validate our Pydantic models against actual data

### How to Export Your Running Config

#### Option 1: Via Web UI
1. Navigate to Device > Setup > Operations
2. Click "Save named configuration snapshot"
3. Or export via: Device > Setup > Operations > "Export named configuration snapshot"

#### Option 2: Via CLI
```bash
# SSH to firewall
ssh admin@<firewall-ip>

# Export running config
> configure
# show | format xml
# Or save to file
> save config to running-config.xml
```

#### Option 3: Via API
```bash
curl -k "https://<firewall>/api/?type=export&category=configuration&key=<api-key>" -o running-config.xml
```

### Using the Config for Development

Once you add `running-config.xml`, the codebase will use it for:

**1. XPath Validation** (`src/core/panos_xpath_map.py`)
```python
from src.core.panos_xpath_map import PanOSXPathMap

# Get XPath for specific object
xpath = PanOSXPathMap.get_xpath("address", "web-server")
# /config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='vsys1']/address/entry[@name='web-server']
```

**2. XML Structure Validation**
```python
from src.core.panos_xpath_map import validate_object_data

# Validate before creating
is_valid, error = validate_object_data("address", {
    "name": "web-server",
    "value": "10.1.1.100",
    "type": "ip-netmask"
})
```

**3. Test Data Generation**
The test suite can parse your actual config to generate realistic test cases.

### Config File Format

Expected structure (PAN-OS XML format):
```xml
<?xml version="1.0"?>
<config>
  <devices>
    <entry name="localhost.localdomain">
      <vsys>
        <entry name="vsys1">
          <address>
            <entry name="example-address">
              <ip-netmask>10.0.0.0/24</ip-netmask>
              <description>Example address object</description>
            </entry>
          </address>
          <service>
            <entry name="example-service">
              <protocol>
                <tcp>
                  <port>8080</port>
                </tcp>
              </protocol>
            </entry>
          </service>
          <!-- More objects... -->
        </entry>
      </vsys>
    </entry>
  </devices>
</config>
```

### Privacy Note

**Do NOT commit sensitive information!**

This directory is `.gitignore`d by default. Before adding any config:

1. **Remove sensitive data**:
   - API keys
   - Passwords
   - IP addresses (or anonymize them)
   - Organization-specific information

2. **Anonymize if needed**:
```bash
# Replace sensitive IPs
sed -i 's/192\.168\.1\./10.0.0./g' running-config.xml

# Remove API key section
# Edit and remove <mgt-config> section if present
```

3. **Use sample config**: For development, a minimal sample config works fine

### Sample Minimal Config

Create a `running-config-sample.xml` with minimal objects for testing:

```xml
<?xml version="1.0"?>
<config>
  <devices>
    <entry name="localhost.localdomain">
      <vsys>
        <entry name="vsys1">
          <address>
            <entry name="test-address">
              <ip-netmask>10.1.1.0/24</ip-netmask>
            </entry>
          </address>
          <service>
            <entry name="test-service">
              <protocol>
                <tcp>
                  <port>8080</port>
                </tcp>
              </protocol>
            </entry>
          </service>
          <address-group>
            <entry name="test-group">
              <static>
                <member>test-address</member>
              </static>
            </entry>
          </address-group>
          <rulebase>
            <security>
              <rules>
                <entry name="test-rule">
                  <from><member>any</member></from>
                  <to><member>any</member></to>
                  <source><member>any</member></source>
                  <destination><member>any</member></destination>
                  <service><member>application-default</member></service>
                  <application><member>any</member></application>
                  <action>allow</action>
                </entry>
              </rules>
            </security>
          </rulebase>
        </entry>
      </vsys>
    </entry>
  </devices>
</config>
```

This provides enough structure to validate our XPath expressions and XML generation without exposing any real firewall config.

