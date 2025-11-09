# Panorama Usage Guide

## Overview

Panorama is Palo Alto Networks' centralized management platform for PAN-OS firewalls. The PAN-OS Agent provides comprehensive Panorama support with automatic device detection and context-aware operations.

### What is Panorama?

Panorama enables centralized management of multiple firewalls through:
- **Device Groups**: Organize firewalls and define policies hierarchically
- **Templates**: Standardize network configuration across devices
- **Shared Objects**: Create reusable address/service objects
- **Centralized Logging**: Aggregate logs from all managed firewalls

### When to Use Panorama vs Firewall

| Use Case | Firewall | Panorama |
|----------|----------|----------|
| Single firewall management | ✅ Ideal | ⚠️ Overkill |
| Multi-firewall deployment | ⚠️ Manual replication | ✅ Ideal |
| Standardized network config | ⚠️ Manual templates | ✅ Built-in templates |
| Centralized policies | ❌ Not possible | ✅ Device groups |
| Shared objects | ❌ Per-firewall only | ✅ Shared context |

### Agent Capabilities

The agent automatically detects Panorama and provides:
- ✅ **19 Panorama-specific tools** (device groups, templates, operations)
- ✅ **Automatic context selection** (shared, device-group, template, template-stack)
- ✅ **Approval gates** for critical operations (commit-all, push-to-devices)
- ✅ **Hierarchical device groups** with parent-child relationships
- ✅ **Template stacks** for layered configuration

## Device Groups

Device groups organize firewalls for centralized policy management. They support hierarchical inheritance where child groups inherit settings from parents.

### Creating Device Groups

```bash
# Create a root device group
panos-agent run -p "Create device group 'All-Branches' with description 'All branch office firewalls'"

# Create a child device group (inherits from parent)
panos-agent run -p "Create device group 'West-Coast' with parent 'All-Branches'"

# Create multiple levels of hierarchy
panos-agent run -p "Create device group 'San-Francisco' with parent 'West-Coast'"
```

### Device Group Operations

```bash
# List all device groups
panos-agent run -p "List all device groups"

# Read device group details
panos-agent run -p "Show details for device group 'All-Branches'"

# Update device group
panos-agent run -p "Update device group 'West-Coast' to add description 'Western US branches'"

# Delete device group (must be empty)
panos-agent run -p "Delete device group 'Test-Group'"
```

### Device Group Policies

Policies defined in device groups apply to all managed firewalls in that group:

```bash
# Create security policy in device group
panos-agent run -p "Create security rule 'Allow-Web' in device group 'All-Branches' allowing HTTP and HTTPS from Trust to Untrust"

# List policies in device group
panos-agent run -p "List security policies in device group 'West-Coast'"

# Update policy in device group
panos-agent run -p "Update security rule 'Allow-Web' in device group 'All-Branches' to add application 'ssl'"
```

### Best Practices for Device Groups

1. **Use Hierarchical Structure**: Organize by geography, function, or environment
   - Example: `All-Branches` → `West-Coast` → `San-Francisco`
   - Shared policies in parent, specific policies in children

2. **Keep Groups Small**: Easier management and targeted pushes
   - Group by logical boundaries (office, region, function)
   - Avoid mixing unrelated firewalls

3. **Use Descriptive Names**: Clear naming prevents confusion
   - Good: `Retail-Stores-Northeast`, `DMZ-Servers-Production`
   - Bad: `Group1`, `Test`, `New`

4. **Document Inheritance**: Track which settings come from parents
   - Use descriptions to note parent group
   - Review inheritance before making changes

## Templates

Templates manage network configuration that's identical across multiple firewalls (interfaces, zones, routing, etc.). Unlike device groups (for policies), templates handle device-level settings.

### Creating Templates

```bash
# Create a basic template
panos-agent run -p "Create template 'Branch-Network' with description 'Standard branch office network config'"

# Create template with specific settings
panos-agent run -p "Create template 'DMZ-Config' for DMZ interface configuration"
```

### Template Operations

```bash
# List all templates
panos-agent run -p "List all templates"

# Read template details
panos-agent run -p "Show details for template 'Branch-Network'"

# Update template
panos-agent run -p "Update template 'Branch-Network' to add description 'Updated for MPLS'"

# Delete template (must not be in use)
panos-agent run -p "Delete template 'Test-Template'"
```

### Template Stacks

Template stacks layer multiple templates for complex configurations. They apply in order from top to bottom.

```bash
# Create a template stack
panos-agent run -p "Create template stack 'Branch-Complete' with templates 'Base-Config' and 'Branch-Network'"

# List template stacks
panos-agent run -p "List all template stacks"

# Read template stack details
panos-agent run -p "Show details for template stack 'Branch-Complete'"

# Update template stack (add template)
panos-agent run -p "Update template stack 'Branch-Complete' to add template 'Security-Baseline'"

# Delete template stack
panos-agent run -p "Delete template stack 'Test-Stack'"
```

### Template vs Template Stack

| Feature | Template | Template Stack |
|---------|----------|----------------|
| Purpose | Single config set | Multiple layered configs |
| Complexity | Simple | Complex (layered) |
| Ordering | N/A | Top to bottom |
| Use Case | Standard config | Multi-tier config |

### Best Practices for Templates

1. **Standardize Network Config**: Use templates for identical network settings
   - Interfaces (ethernet1/1-8 for branch offices)
   - Zones (Trust, Untrust, DMZ standard names)
   - Routing (default routes, OSPF/BGP settings)

2. **Layer with Template Stacks**: Build complex configs from simple templates
   - Base template: Common settings for all firewalls
   - Network template: Site-specific networking
   - Security template: Security profiles and settings

3. **Separate Concerns**: One template per logical function
   - Good: `Base-Interfaces`, `OSPF-Routing`, `Management-Settings`
   - Bad: `Everything-Config` (monolithic)

4. **Version Your Templates**: Use descriptive names with versions
   - Example: `Branch-Network-v2`, `DMZ-Config-2024`

## Configuration Contexts

Panorama uses four configuration contexts with different scopes and priorities.

### Context Priority (Highest to Lowest)

1. **Template** - Device settings (interfaces, zones, routing)
2. **Template-Stack** - Layered device settings
3. **Device-Group** - Policies and device-group objects
4. **Shared** - Objects available to all device groups

### Shared Context

Objects available to all device groups. Use for common infrastructure (DNS servers, public IPs, etc.).

```bash
# Create shared address object
panos-agent run -p "Create shared address object 'Public-DNS' with IP 8.8.8.8"

# Create shared service object
panos-agent run -p "Create shared service 'Custom-HTTPS' TCP port 8443"

# List shared address objects
panos-agent run -p "List shared address objects"
```

**When to use Shared:**
- Common external services (DNS, NTP, public IPs)
- Corporate infrastructure (HQ networks, data centers)
- Third-party services (cloud providers, partners)

### Device-Group Context

Policies and objects specific to a device group. Most common context for security policies.

```bash
# Create address in device group
panos-agent run -p "Create address object 'Branch-Server' at 10.1.1.100 in device group 'All-Branches'"

# Create security policy in device group
panos-agent run -p "Create security rule 'Allow-Internal' in device group 'All-Branches' from Trust to Untrust"

# List objects in device group
panos-agent run -p "List address objects in device group 'West-Coast'"
```

**When to use Device-Group:**
- Security policies (most policies go here)
- Group-specific objects (branch servers, regional resources)
- Application overrides for specific groups

### Template Context

Network configuration at the device level (interfaces, zones, routing).

```bash
# Configure interface in template
panos-agent run -p "Create interface ethernet1/1 in template 'Branch-Network' with IP 10.1.1.1/24"

# Configure zone in template
panos-agent run -p "Create zone 'Branch-LAN' in template 'Branch-Network'"

# List template settings
panos-agent run -p "Show configuration for template 'Branch-Network'"
```

**When to use Template:**
- Interface configuration (IP addresses, VLANs)
- Zone definitions
- Routing configuration (static routes, OSPF/BGP)
- VPN configuration

### Template-Stack Context

Layered templates for complex configurations. Lower priority than single template.

```bash
# Create template stack
panos-agent run -p "Create template stack 'Branch-Full' with templates 'Base-Config', 'Branch-Network', 'Security-Baseline'"

# List template stack settings
panos-agent run -p "Show configuration for template stack 'Branch-Full'"
```

**When to use Template-Stack:**
- Multi-tier configurations (base + network + security)
- Standard config + site-specific overrides
- Reusable template combinations

## Workflows

### Workflow 1: New Branch Office Setup

Complete workflow for deploying a new branch office with Panorama.

**Step 1: Create Device Group**

```bash
panos-agent run -p "Create device group 'Branch-NewYork' with parent 'All-Branches' and description 'New York branch office'"
```

**Step 2: Create Template for Network Configuration**

```bash
panos-agent run -p "Create template 'Branch-NewYork-Network' with description 'Network config for NY branch'"
```

**Step 3: Create Shared Objects (if needed)**

```bash
# Create shared address for corporate DNS
panos-agent run -p "Create shared address object 'Corp-DNS' with IP 10.0.0.53"

# Create shared service for custom application
panos-agent run -p "Create shared service 'Custom-App' TCP port 8080"
```

**Step 4: Create Device-Group Specific Objects**

```bash
# Create address for branch server
panos-agent run -p "Create address object 'NY-Server' at 10.100.1.10 in device group 'Branch-NewYork'"

# Create address for branch subnet
panos-agent run -p "Create address object 'NY-LAN' at 10.100.1.0/24 in device group 'Branch-NewYork'"
```

**Step 5: Create Security Policies**

```bash
# Allow internal traffic
panos-agent run -p "Create security rule 'NY-Allow-Internal' in device group 'Branch-NewYork' from Trust to Untrust allowing any"

# Allow web traffic
panos-agent run -p "Create security rule 'NY-Allow-Web' in device group 'Branch-NewYork' from Trust to Untrust allowing web-browsing and ssl"
```

**Step 6: Commit to Panorama**

```bash
panos-agent run -p "Commit changes to Panorama with description 'New York branch initial configuration'"
```

**Step 7: Push to Devices (Requires Approval)**

```bash
panos-agent run -p "Push device group 'Branch-NewYork' configuration to all managed devices"
# Agent will prompt for approval before executing
```

### Workflow 2: Shared Object Management

Manage shared objects available to all device groups.

**Step 1: Create Shared Address Objects**

```bash
# Public DNS servers
panos-agent run -p "Create shared address object 'Google-DNS-1' with IP 8.8.8.8"
panos-agent run -p "Create shared address object 'Google-DNS-2' with IP 8.8.4.4"

# Corporate infrastructure
panos-agent run -p "Create shared address object 'HQ-Network' at 10.0.0.0/16"
panos-agent run -p "Create shared address object 'DataCenter-1' at 172.16.0.0/16"
```

**Step 2: Create Shared Address Group**

```bash
panos-agent run -p "Create shared address group 'Public-DNS-Servers' with members 'Google-DNS-1' and 'Google-DNS-2'"
```

**Step 3: Create Shared Service Objects**

```bash
# Custom services
panos-agent run -p "Create shared service 'Custom-HTTPS' TCP port 8443"
panos-agent run -p "Create shared service 'Custom-SSH' TCP port 2222"
```

**Step 4: Reference in Device-Group Policy**

```bash
panos-agent run -p "Create security rule 'Allow-DNS' in device group 'All-Branches' allowing service 'dns' to destination group 'Public-DNS-Servers'"
```

**Step 5: Commit and Push**

```bash
# Commit to Panorama
panos-agent run -p "Commit changes to Panorama with description 'Added shared DNS objects'"

# Push to all device groups
panos-agent run -p "Push all device groups to managed devices"
```

### Workflow 3: Template-Based Network Configuration

Use templates to standardize network configuration across multiple firewalls.

**Step 1: Create Base Template**

```bash
panos-agent run -p "Create template 'Base-Config' with description 'Base configuration for all firewalls'"
```

**Step 2: Create Network Template**

```bash
panos-agent run -p "Create template 'Standard-Network' with description 'Standard branch network configuration'"
```

**Step 3: Create Security Template**

```bash
panos-agent run -p "Create template 'Security-Baseline' with description 'Security profiles and settings'"
```

**Step 4: Create Template Stack**

```bash
panos-agent run -p "Create template stack 'Branch-Standard' with templates 'Base-Config', 'Standard-Network', 'Security-Baseline'"
```

**Step 5: Assign to Device Group**

```bash
# Note: Assignment typically done via Panorama UI or API
# Agent can create device group with template reference
panos-agent run -p "Create device group 'New-Branches' with reference templates 'Branch-Standard'"
```

**Step 6: Commit and Push**

```bash
# Commit to Panorama
panos-agent run -p "Commit changes to Panorama with description 'Added template stack for new branches'"

# Push to devices
panos-agent run -p "Push device group 'New-Branches' to managed devices"
```

## Commit Operations

Panorama has two types of commit operations:

### 1. Local Commit (Panorama Only)

Commits changes to Panorama configuration without pushing to firewalls.

```bash
# Standard local commit
panos-agent run -p "Commit changes to Panorama"

# Commit with description
panos-agent run -p "Commit changes to Panorama with description 'Added new security rules'"

# Validate before commit (dry-run)
panos-agent run -p "Validate Panorama configuration without committing"
```

**When to use:**
- After creating/updating device groups, templates, or shared objects
- Before pushing to devices (commit local first)
- Testing configuration changes

### 2. Commit-All / Push to Devices

Pushes committed Panorama configuration to managed firewalls. **Requires approval.**

```bash
# Push specific device group
panos-agent run -p "Push device group 'Branch-Offices' to managed devices"

# Push multiple device groups
panos-agent run -p "Push device groups 'East-Coast' and 'West-Coast' to devices"

# Push all device groups
panos-agent run -p "Push all device groups to managed devices"
```

**Approval Prompt:**

```
⚠️  CRITICAL OPERATION: Panorama Commit-All
Target: device groups: Branch-Offices
Description: Deploy new security rules

This will push configuration to all firewalls in the specified device groups.
Affected firewalls: fw1, fw2, fw3

Type 'approve' to continue or anything else to cancel:
```

**When to use:**
- After local commit and validation
- Deploying new policies to firewalls
- Pushing template changes to devices
- **Always review changes before approval**

## Approval Gates

Critical Panorama operations require explicit approval to prevent accidental changes to production firewalls.

### Operations Requiring Approval

1. **Panorama Commit-All** (`panorama_commit_all`)
2. **Push to Devices** (`panorama_push_to_devices`)

### Approval Process

1. **Agent Presents Operation Details**:
   - Operation type (commit-all, push)
   - Target device groups or firewalls
   - Description of changes
   - Estimated impact

2. **User Reviews**:
   - Check target devices
   - Verify changes are correct
   - Confirm no unintended impact

3. **User Approves or Cancels**:
   - Type `approve` to proceed
   - Any other input cancels the operation

### Example Approval Flow

```bash
$ panos-agent run -p "Push device group 'Production' to managed devices"

⚠️  CRITICAL OPERATION: Push to Devices
Target: device group 'Production'
Affected devices: prod-fw1, prod-fw2, prod-fw3
Description: Deploy security policy updates

This will push configuration changes to production firewalls.
Changes may affect active traffic.

Type 'approve' to continue or anything else to cancel: approve

✅ Approved. Pushing configuration to devices...
🔄 Push job started (job ID: 12345)
⏳ Waiting for push to complete...
✅ Push completed successfully on all devices
```

### Bypassing Approval (Not Recommended)

For automation scenarios, you can bypass approval with environment variable:

```bash
# NOT RECOMMENDED for production
export PANOS_AGENT_AUTO_APPROVE=true
panos-agent run -p "Push device group 'Test' to devices"
```

**⚠️ Warning**: Auto-approval bypasses safety checks. Use only in:
- Dedicated test environments
- CI/CD pipelines with extensive validation
- Non-production scenarios

## Best Practices

### Organization Structure

1. **Use Geographic Hierarchy**:
   ```
   All-Locations
   ├── North-America
   │   ├── East-Coast
   │   └── West-Coast
   └── Europe
       ├── UK
       └── Germany
   ```

2. **Or Functional Hierarchy**:
   ```
   All-Firewalls
   ├── Branch-Offices
   ├── Data-Centers
   └── DMZ-Servers
   ```

### Object Management

1. **Shared Objects for Common Resources**:
   - Public DNS servers (8.8.8.8, 1.1.1.1)
   - Corporate infrastructure (HQ networks, VPN endpoints)
   - Third-party services (cloud providers, SaaS)

2. **Device-Group Objects for Specific Resources**:
   - Branch-specific servers
   - Regional applications
   - Group-specific policies

3. **Use Descriptive Names**:
   - Good: `Corp-DNS-Primary`, `Branch-NY-Server-1`, `DMZ-Web-Pool`
   - Bad: `Server1`, `Test`, `New-Address`

### Template Strategy

1. **Create Layered Templates**:
   - **Base**: Common settings (NTP, DNS, logging)
   - **Network**: Interface configuration
   - **Security**: Security profiles, anti-virus, anti-spyware

2. **Use Template Stacks for Flexibility**:
   - Standard stack for most deployments
   - Custom stacks for special cases
   - Test stack for validation

3. **Version Your Templates**:
   - Use version suffixes: `Branch-Network-v2`
   - Keep old versions for rollback
   - Document changes in descriptions

### Commit Strategy

1. **Always Commit Local First**:
   ```bash
   # 1. Make changes
   panos-agent run -p "Create address object 'New-Server' at 10.1.1.100"
   
   # 2. Commit to Panorama
   panos-agent run -p "Commit changes to Panorama with description 'Added new server'"
   
   # 3. Push to devices (after validation)
   panos-agent run -p "Push device group 'Production' to devices"
   ```

2. **Use Descriptive Commit Messages**:
   - Good: "Added security rules for new branch office NY"
   - Bad: "Changes", "Update", "Test"

3. **Push to Small Groups First**:
   - Test on dev/staging device group
   - Push to pilot production group
   - Push to remaining production groups

4. **Schedule Maintenance Windows**:
   - Push during low-traffic periods
   - Notify stakeholders before pushing
   - Have rollback plan ready

### Change Management

1. **Validate Before Pushing**:
   ```bash
   # Validate configuration
   panos-agent run -p "Validate Panorama configuration"
   
   # Review pending changes
   panos-agent run -p "Show pending changes in Panorama"
   ```

2. **Use Approval Gates**:
   - Never bypass approval in production
   - Review all details before approving
   - Document approval in change tickets

3. **Test in Non-Production First**:
   - Create test device group
   - Deploy changes to test first
   - Validate functionality before production

4. **Monitor After Push**:
   - Check firewall logs for errors
   - Verify traffic is flowing correctly
   - Monitor for unexpected blocks

### Backup and Recovery

1. **Export Configuration Before Major Changes**:
   ```bash
   # Backup Panorama config (via Panorama UI or API)
   # Agent support for export/import coming in future phase
   ```

2. **Document Configuration Changes**:
   - Keep change log of device group updates
   - Track template versions
   - Document shared object additions

3. **Test Rollback Procedures**:
   - Know how to revert commits
   - Practice in test environment
   - Keep previous configuration backups

## Troubleshooting

### Common Issues

**Issue: "Device type is not PANORAMA"**

```bash
❌ Error: panorama_commit_all requires a Panorama device
```

**Solution**: Verify you're connected to Panorama, not a firewall:

```bash
panos-agent test-connection
# Should show: ✅ Connected to Panorama 11.0.0 (serial: 123456789)
```

**Issue: "Device group not found"**

```bash
❌ Error: Device group 'Branch-Offices' not found
```

**Solution**: List existing device groups:

```bash
panos-agent run -p "List all device groups"
```

**Issue: "Template stack contains non-existent templates"**

```bash
❌ Error: Template 'NonExistent-Template' not found
```

**Solution**: List available templates first:

```bash
panos-agent run -p "List all templates"
```

**Issue: "Push operation timed out"**

```bash
⚠️ Warning: Push job 12345 still in progress after 180s
```

**Solution**: Check job status in Panorama UI or increase timeout.

### Debug Tips

1. **Check Device Context**:
   ```bash
   # Verify device type and context
   panos-agent test-connection
   ```

2. **List Existing Resources**:
   ```bash
   # List device groups
   panos-agent run -p "List all device groups"
   
   # List templates
   panos-agent run -p "List all templates"
   
   # List shared objects
   panos-agent run -p "List shared address objects"
   ```

3. **Validate Configuration**:
   ```bash
   # Validate before commit
   panos-agent run -p "Validate Panorama configuration"
   ```

4. **Check Logs**:
   ```bash
   # Enable debug logging
   export LOG_LEVEL=DEBUG
   panos-agent run -p "Your command here"
   ```

## Additional Resources

- **PAN-OS Agent Documentation**:
  - [README.md](../README.md) - Overview and quickstart
  - [ARCHITECTURE.md](ARCHITECTURE.md) - Technical architecture
  - [MULTI_VSYS_SUPPORT.md](MULTI_VSYS_SUPPORT.md) - Multi-vsys firewall support

- **Palo Alto Networks Documentation**:
  - [Panorama Administrator's Guide](https://docs.paloaltonetworks.com/panorama)
  - [PAN-OS XML API Reference](https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api)
  - [Device Group Best Practices](https://docs.paloaltonetworks.com/panorama/11-0/panorama-admin/manage-firewalls/manage-device-groups)

## Version

- **Phase**: 3.6 (Documentation & Testing)
- **Date**: 2025-11-09
- **Status**: Complete

