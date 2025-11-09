# Phase 3.5: Quick Reference Guide

**Status:** ✅ Complete | **Date:** November 9, 2025

---

## 🎯 What Was Added

### 7 New Tools for Monitoring & Troubleshooting

#### 🔧 Operational Commands (4 tools)
```python
show_interfaces()           # Network interface status
show_routing_table()        # Routing table entries
show_sessions(...)          # Active firewall sessions (with filters)
show_system_resources()     # CPU, memory, disk usage
```

#### 📊 Log Queries (3 tools)
```python
query_traffic_logs(...)     # Traffic logs with IP/app filters
query_threat_logs(...)      # Threat/security logs with severity filters
query_system_logs(...)      # System event logs with type/user filters
```

---

## 📝 Usage Examples

### Network Monitoring
```bash
# Check interface status
panos-agent run -p "show all network interfaces"

# View routing table
panos-agent run -p "show routing table"

# Check system health
panos-agent run -p "show system resources"
```

### Session Analysis
```bash
# Show all active sessions
panos-agent run -p "show active sessions"

# Filter by source IP
panos-agent run -p "show sessions from 10.1.1.5"

# Filter by application
panos-agent run -p "show sessions for SSL traffic"
```

### Traffic Investigation
```bash
# Traffic from subnet
panos-agent run -p "show traffic logs from 10.1.1.0/24"

# Traffic to specific destination
panos-agent run -p "show traffic to 8.8.8.8"

# Application traffic
panos-agent run -p "show web-browsing traffic logs"
```

### Security Analysis
```bash
# High severity threats
panos-agent run -p "show threat logs with high severity"

# Virus detections
panos-agent run -p "show threat logs type virus"

# Critical threats from subnet
panos-agent run -p "show critical threats from 10.0.0.0/8"
```

### Audit & Compliance
```bash
# Configuration changes
panos-agent run -p "show system config changes"

# Authentication events
panos-agent run -p "show system auth logs"

# Admin activity
panos-agent run -p "show system logs for user admin"
```

---

## 🔧 Tool Signatures

### Operational Tools

#### `show_interfaces()`
```python
"""Show all network interfaces and their status."""
Returns: str  # Formatted interface list
```

#### `show_routing_table()`
```python
"""Show the routing table with all routes."""
Returns: str  # Formatted routing table
```

#### `show_sessions(source=None, destination=None, application=None)`
```python
"""Show active firewall sessions with optional filters.

Args:
    source: Source IP address (e.g., "10.1.1.5")
    destination: Destination IP address
    application: Application name (e.g., "web-browsing")

Returns: str  # Formatted session list
"""
```

#### `show_system_resources()`
```python
"""Show system resource usage including CPU, memory, and disk."""
Returns: str  # Resource usage with warnings if >80%
```

### Log Query Tools

#### `query_traffic_logs(source=None, destination=None, application=None, port=None, limit=100)`
```python
"""Query firewall traffic logs with optional filters.

Args:
    source: Source IP/subnet (e.g., "10.0.0.0/8")
    destination: Destination IP/subnet
    application: Application name
    port: Destination port number
    limit: Max entries (default: 100)

Returns: str  # Formatted traffic logs
"""
```

#### `query_threat_logs(threat_type=None, severity=None, source=None, destination=None, limit=100)`
```python
"""Query firewall threat/security logs.

Args:
    threat_type: virus, spyware, vulnerability, url, wildfire
    severity: critical, high, medium, low, informational
    source: Source IP/subnet
    destination: Destination IP/subnet
    limit: Max entries (default: 100)

Returns: str  # Formatted threat logs with severity indicators
"""
```

#### `query_system_logs(event_type=None, severity=None, username=None, limit=100)`
```python
"""Query firewall system event logs.

Args:
    event_type: config, system, auth, ha
    severity: critical, high, medium, low, informational
    username: User who triggered event
    limit: Max entries (default: 100)

Returns: str  # Formatted system logs
"""
```

---

## 🎨 Output Formats

### Interfaces
```
Network Interfaces:
ethernet1/1: 10.0.1.1/24 | Status: up | 1000/full
ethernet1/2: 192.168.1.1/24 | Status: up | 1000/full
```

### Routing Table
```
Routing Table:
Destination         Next Hop           Interface      Metric/Flags
----------------------------------------------------------------------
0.0.0.0/0           10.0.1.254         ethernet1/1    metric 10 [S]
10.0.1.0/24         0.0.0.0            ethernet1/1    metric 0 [C]
```

### Sessions
```
Active Sessions (Total: 142):
10.1.1.5:52341       → 8.8.8.8:443          | App: ssl            | State: ACTIVE      | Duration: 120s | Bytes: 15234
10.1.1.12:48932      → 1.1.1.1:53           | App: dns            | State: ACTIVE      | Duration: 2s   | Bytes: 512
```

### System Resources
```
System Resources:
CPU Load Average: 0.45 (1m), 0.52 (5m), 0.48 (15m)
Memory: 3.24GB / 8.00GB (40.5%)
Disk (root): 65% used (Total: 100GB, Available: 35GB)

⚠️  High disk usage on root: 85%
```

### Traffic Logs
```
Traffic Logs (showing 42 of 50 max):
10.1.1.5        → 8.8.8.8        | App: web-browsing      | Action: allow      | 15.24KB    (127 pkts)
10.1.1.12       → 1.1.1.1        | App: dns               | Action: allow      | 512B       (4 pkts)
```

### Threat Logs
```
Threat Logs (showing 15 of 50 max):
🔴 Malware.Generic.123456       | Severity: critical   | Type: virus         | 10.1.1.5   → 8.8.8.8   | Action: block
🟠 SQL-Injection-Attempt        | Severity: high       | Type: vulnerability | 203.0.113.5 → 10.1.2.10 | Action: alert
```

### System Logs
```
System Logs (showing 12 of 50 max):
[2025/11/09 10:15:23] config     | Severity: informational | User: admin         | Configuration committed successfully
[2025/11/09 09:45:10] config     | Severity: medium       | User: operator      | Security policy modified: allow-web
```

---

## 📚 PAN-OS Query Syntax

### Operators
| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equals | `(app eq 'web-browsing')` |
| `neq` | Not equals | `(threatid neq 0)` |
| `in` | IP in subnet | `(addr.src in 10.0.0.0/8)` |
| `geq` | Greater/equal | `(receive_time geq -1h)` |

### Common Patterns
```
# Traffic logs
(addr.src in 10.0.0.0/8) and (app eq 'web-browsing')
(addr.dst eq 8.8.8.8) and (port.dst eq 443)

# Threat logs
(threatid neq 0) and (severity eq 'high')
(subtype eq 'virus') and (addr.src in 10.0.0.0/8)

# System logs
(subtype eq 'config') and (receive_time geq -1h)
(user.name eq 'admin') and (subtype eq 'auth')
```

---

## 📊 Statistics

- **Files Created:** 10 files
  - 4 operational tool files
  - 3 log tool files
  - 2 `__init__.py` files
  - 1 completion summary
- **Files Modified:** 3 files
  - `src/core/panos_api.py` (added query_logs)
  - `src/tools/__init__.py` (registered tools)
  - `README.md` (updated stats)
- **Lines of Code:** ~800+ lines
- **Tools Added:** 7 tools
- **Total Tools:** 50 → 57
- **Linting Errors:** 0

---

## ✅ Quick Validation

```bash
# Verify tools load
uv run python -c "from src.tools import ALL_TOOLS; print(f'Total: {len(ALL_TOOLS)}')"

# Output: Total: 57
```

---

## 🔗 Related Documentation

- **Full Details:** [PHASE_3.5_COMPLETE.md](PHASE_3.5_COMPLETE.md)
- **Architecture:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Testing Guide:** [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)
- **Main README:** [README.md](README.md)

---

**Phase 3.5 Complete** ✅ | Ready for production use 🚀

