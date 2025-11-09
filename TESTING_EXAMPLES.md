# Testing Examples for Phase 3.5 & 3.6 Features

## Testing Phase 3.5: Operational Commands & Logs

### 1. Show Network Interfaces

```bash
# Show all network interfaces
panos-agent run -p "Show all network interfaces"

# Or be more specific
panos-agent run -p "Display interface status and IP addresses"
```

**Expected output:** List of interfaces with IP, status (up/down), speed/duplex

---

### 2. Show Routing Table

```bash
# Show routing table
panos-agent run -p "Show the routing table"

# Or ask for specific routes
panos-agent run -p "What routes are configured for 10.0.0.0/8?"
```

**Expected output:** Routing table with destination, next-hop, interface, metric

**Note:** This tool automatically detects and handles both standard and advanced routing engines. If standard routing returns no results, it will automatically query the advanced routing engine.

---

### 3. Show Active Sessions

```bash
# Show all active sessions
panos-agent run -p "Show active firewall sessions"

# Filter by source IP
panos-agent run -p "Show sessions from source 10.1.1.5"

# Filter by application
panos-agent run -p "Show all SSL sessions"

# Filter by destination
panos-agent run -p "Show sessions to 8.8.8.8"
```

**Expected output:** Session count, source/dest IPs, application, state, duration

---

### 4. Show System Resources

```bash
# Show CPU, memory, disk usage
panos-agent run -p "Show system resource usage"

# Or be specific
panos-agent run -p "What is the current CPU and memory utilization?"
```

**Expected output:** CPU load average, memory usage, disk usage (with warnings if >80%)

---

### 5. Query Traffic Logs

```bash
# Show recent traffic logs
panos-agent run -p "Show traffic logs from the last hour"

# Filter by source subnet
panos-agent run -p "Show traffic logs from 10.1.1.0/24"

# Filter by application
panos-agent run -p "Show web-browsing traffic logs"

# Filter by destination and port
panos-agent run -p "Show traffic to 8.8.8.8 on port 443"

# Limit results
panos-agent run -p "Show the last 50 traffic log entries"
```

**Expected output:** Traffic logs with source→dest, application, action, bytes/packets

---

### 6. Query Threat Logs

```bash
# Show recent threat logs
panos-agent run -p "Show high severity threat logs"

# Filter by threat type
panos-agent run -p "Show virus threat logs"

# Filter by severity
panos-agent run -p "Show critical and high severity threats"

# Filter by source
panos-agent run -p "Show threats from 10.1.1.0/24"
```

**Expected output:** Threat logs with severity indicators (🔴🟠🟡🟢), threat name, action

---

### 7. Query System Logs

```bash
# Show recent system events
panos-agent run -p "Show system logs from the last hour"

# Filter by event type
panos-agent run -p "Show configuration change logs"

# Filter by user
panos-agent run -p "Show logs for user admin"

# Filter by severity
panos-agent run -p "Show high severity system logs"
```

**Expected output:** System events with timestamp, event type, user, description

---

## Testing Phase 3.6: Panorama Support

### 1. Automatic Device Detection

```bash
# Test connection - agent auto-detects device type
panos-agent test-connection

# Expected output shows:
# - Panorama: "Connected to Panorama X.X.X"
# - Firewall: "Connected to PAN-OS X.X.X (model: PA-XXX)"
```

---

### 2. Panorama Device Groups

```bash
# Create device group
panos-agent run -p "Create device group 'Branch-Offices'"

# Create device group with parent
panos-agent run -p "Create device group 'East-Coast' with parent 'Branch-Offices'"

# List device groups
panos-agent run -p "List all device groups"

# Read device group details
panos-agent run -p "Show me details of device group 'Branch-Offices'"
```

---

### 3. Panorama Templates

```bash
# Create template
panos-agent run -p "Create template 'Branch-Network-Config'"

# List templates
panos-agent run -p "List all templates"

# Read template details
panos-agent run -p "Show template 'Branch-Network-Config' details"
```

---

### 4. Panorama Template Stacks

```bash
# Create template stack
panos-agent run -p "Create template stack 'Branch-Stack'"

# List template stacks
panos-agent run -p "List all template stacks"
```

---

### 5. Panorama Shared Objects

```bash
# Create shared address object (available to all device groups)
panos-agent run -p "Create shared address object 'DNS-Server' with IP 8.8.8.8"

# Create shared service object
panos-agent run -p "Create shared service 'Custom-HTTPS' with TCP port 8443"

# List shared objects
panos-agent run -p "List all shared address objects"
```

---

### 6. Device Group-Specific Objects

```bash
# Create address object in device group
panos-agent run -p "Create address object 'Branch-Server' in device group 'Branch-Offices' with IP 10.10.10.5"

# Create policy in device group
panos-agent run -p "In device group 'Branch-Offices', create security policy 'Allow-DNS' allowing UDP/53 to DNS-Server"
```

---

### 7. Panorama Commit Operations

```bash
# Commit to Panorama only (local)
panos-agent run -p "Commit changes to Panorama"

# Validate before commit
panos-agent run -p "Validate my Panorama configuration changes"

# Commit and push to devices (requires HITL approval)
panos-agent run -p "Commit all changes and push to device group 'Branch-Offices'"

# Expected: You'll be prompted for approval before push
```

---

## Testing Phase 3.4: Multi-Vsys Support

### 1. Default Vsys (vsys1)

```bash
# Operations default to vsys1 if not specified
panos-agent run -p "Create address object 'Server1' with IP 10.1.1.5"

# Show interfaces in default vsys
panos-agent run -p "Show network interfaces"
```

---

### 2. Specify Vsys via CLI Flag

```bash
# Create object in vsys2
panos-agent run --vsys vsys2 -p "Create address object 'Server2' with IP 10.2.1.5"

# Create object in vsys3
panos-agent run --vsys vsys3 -p "Create address object 'Server3' with IP 10.3.1.5"

# Show routing in vsys2
panos-agent run --vsys vsys2 -p "Show routing table"

# Query logs in vsys2
panos-agent run --vsys vsys2 -p "Show traffic logs from last hour"
```

---

### 3. Specify Vsys via Environment Variable

```bash
# Set vsys for entire session
export PANOS_AGENT_VSYS=vsys2

# All operations now use vsys2
panos-agent run -p "List address objects"
panos-agent run -p "Show active sessions"

# Unset to go back to default
unset PANOS_AGENT_VSYS
```

---

### 4. Custom Vsys Names

```bash
# If you have custom vsys names like "vsys-tenant1"
panos-agent run --vsys vsys-tenant1 -p "Create address object 'Tenant1-Server' with IP 192.168.1.5"
```

---

## Combined Testing Scenarios

### Scenario 1: Multi-Vsys Monitoring

```bash
# Monitor vsys1
panos-agent run --vsys vsys1 -p "Show system resources and active sessions"

# Monitor vsys2
panos-agent run --vsys vsys2 -p "Show high severity threats and traffic logs from 10.2.0.0/16"

# Monitor vsys3
panos-agent run --vsys vsys3 -p "Show interfaces and routing table"
```

---

### Scenario 2: Panorama Branch Office Setup

```bash
# Step 1: Create device group
panos-agent run -p "Create device group 'Branch-NYC'"

# Step 2: Create shared objects
panos-agent run -p "Create shared address object 'Corporate-DNS' with IP 10.0.0.53"

# Step 3: Create device-group policy
panos-agent run -p "In device group 'Branch-NYC', create security policy allowing all traffic to Corporate-DNS"

# Step 4: Validate configuration
panos-agent run -p "Validate configuration for device group 'Branch-NYC'"

# Step 5: Commit (requires approval)
panos-agent run -p "Commit and push to device group 'Branch-NYC'"
```

---

### Scenario 3: Troubleshooting Workflow

```bash
# 1. Check system health
panos-agent run -p "Show system resources"

# 2. Check active sessions
panos-agent run -p "Show top 50 active sessions"

# 3. Check for threats
panos-agent run -p "Show critical and high severity threats from last 2 hours"

# 4. Check traffic patterns
panos-agent run -p "Show traffic logs for destination 8.8.8.8"

# 5. Check configuration changes
panos-agent run -p "Show system logs for config changes by user admin"
```

---

### Scenario 4: Multi-Tenant Firewall (Multi-Vsys)

```bash
# Tenant 1 (vsys1)
panos-agent run --vsys vsys1 -p "Create address object 'Tenant1-Web' with IP 10.1.0.100"
panos-agent run --vsys vsys1 -p "Show traffic logs from 10.1.0.0/24"

# Tenant 2 (vsys2)
panos-agent run --vsys vsys2 -p "Create address object 'Tenant2-Web' with IP 10.2.0.100"
panos-agent run --vsys vsys2 -p "Show traffic logs from 10.2.0.0/24"

# Each tenant's traffic and objects are isolated
```

---

## Quick Test Script

Create a test script to try multiple features:

```bash
#!/bin/bash
# test_new_features.sh

echo "=== Testing Operational Commands ==="
panos-agent run -p "Show system resources"
echo ""

echo "=== Testing Traffic Logs ==="
panos-agent run -p "Show traffic logs from last hour, limit 10"
echo ""

echo "=== Testing Threat Logs ==="
panos-agent run -p "Show high severity threats"
echo ""

echo "=== Testing Multi-Vsys ==="
panos-agent run --vsys vsys1 -p "Show interfaces"
panos-agent run --vsys vsys2 -p "Show routing table"
echo ""

echo "=== Testing Panorama (if connected to Panorama) ==="
panos-agent run -p "List all device groups"
panos-agent run -p "List shared address objects"
```

Save this as `test_new_features.sh`, make it executable, and run:

```bash
chmod +x test_new_features.sh
./test_new_features.sh
```

---

## Verification Checklist

After running examples, verify:

- [ ] Operational commands return formatted output (not raw XML)
- [ ] Log queries show structured logs with proper filtering
- [ ] Multi-vsys commands use correct XPath (check logs with `-v`)
- [ ] Panorama commands detect device type correctly
- [ ] Approval gates trigger for commit-all operations
- [ ] Error messages are clear and actionable
- [ ] Response times are reasonable (<5 seconds for most ops)

---

## Tips for Testing

### Use --no-stream for Cleaner Output

```bash
panos-agent run --no-stream -p "Show traffic logs"
```

This disables streaming mode and shows just the final result.

### Enable Verbose Logging

```bash
# Set log level to DEBUG to see XPath queries and API calls
export LOG_LEVEL=DEBUG
panos-agent run -p "Show interfaces"
```

### Test with Different Models

```bash
# Use faster model for simple queries
panos-agent run --model haiku -p "Show interfaces"

# Use default model for complex operations
panos-agent run --model sonnet -p "Create security policy..."
```

### Use Thread IDs for Conversation Context

```bash
# Start a conversation
panos-agent run --thread-id troubleshooting-001 -p "Show system resources"

# Continue the conversation
panos-agent run --thread-id troubleshooting-001 -p "Now show active sessions"

# Agent remembers previous context
panos-agent run --thread-id troubleshooting-001 -p "Show threats related to those sessions"
```

---

## Troubleshooting Common Issues

### Issue: "No interfaces found"

**Cause:** Operational command XML parsing issue or unsupported platform

**Solution:**

1. Check connection: `panos-agent test-connection`
2. Verify device type is detected correctly
3. Enable DEBUG logging to see raw XML response

### Issue: "No logs found"

**Cause:** No logs match filter criteria, or logging not enabled

**Solution:**

1. Broaden filter (e.g., remove severity filter)
2. Check logging is enabled on firewall
3. Try default query: `panos-agent run -p "Show traffic logs"`

### Issue: "Permission denied" on Panorama operations

**Cause:** API user lacks Panorama permissions

**Solution:**

1. Verify API user has Panorama admin role
2. Check device group permissions
3. Review firewall/Panorama admin roles

### Issue: Multi-vsys commands go to wrong vsys

**Cause:** Environment variable set incorrectly

**Solution:**

1. Check: `echo $PANOS_AGENT_VSYS`
2. Unset if needed: `unset PANOS_AGENT_VSYS`
3. Use explicit `--vsys` flag instead

---

## Next Steps

After testing these features, explore:

1. **Combine features**: Use operational commands + log queries for comprehensive troubleshooting
2. **Automate workflows**: Create deterministic workflows combining multiple operations
3. **Set up monitoring**: Use operational commands to monitor firewall health
4. **Document your environment**: Create templates for common operations in your network

For more information, see:

- [docs/PANORAMA.md](docs/PANORAMA.md) - Comprehensive Panorama usage guide
- [docs/MULTI_VSYS_SUPPORT.md](docs/MULTI_VSYS_SUPPORT.md) - Multi-vsys configuration guide
- [README.md](README.md) - Full feature documentation
