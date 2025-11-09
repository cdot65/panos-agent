# PAN-OS Agent Test Commands

Quick reference for testing the agent with various scenarios.

---

## Connection & Setup

### Test Firewall Connection

```bash
uv run panos-agent test-connection
```

### List Available Workflows

```bash
uv run panos-agent list-workflows
```

### Check Version

```bash
uv run panos-agent version
```

---

## Autonomous Mode (ReAct)

### Simple List Operations

```bash
# List address objects
uv run panos-agent run -p "List all address objects" --model haiku

# List service objects
uv run panos-agent run -p "Show me all service objects" --model haiku

# List security policies
uv run panos-agent run -p "What security policies are configured?" --model haiku

# List address groups
uv run panos-agent run -p "Show all address groups" --model haiku
```

### Read Specific Objects (if they exist)

```bash
# Read specific address (change name to one that exists)
uv run panos-agent run -p "Get details for address object named demo-server" --model haiku

# Read service group
uv run panos-agent run -p "Show me the members of service group web-services" --model haiku
```

### Create Operations (Test Only - Review Before Committing!)

```bash
# Create address object
uv run panos-agent run -p "Create an address object named test-server-001 with IP 10.50.50.10" --model sonnet

# Create service object
uv run panos-agent run -p "Create a service named http-8080 for TCP port 8080" --model sonnet

# Create address group
uv run panos-agent run -p "Create an address group called test-group with members test-server-001" --model sonnet
```

### Complex Multi-Step Operations

```bash
# Multi-object creation
uv run panos-agent run -p "Create three address objects: web-server-1 at 10.1.1.10, web-server-2 at 10.1.1.11, and web-server-3 at 10.1.1.12" --model sonnet

# With description
uv run panos-agent run -p "Create address object app-server at 192.168.100.50 with description 'Application server for production'" --model sonnet
```

### Model Comparison

```bash
# Fast & cheap (Haiku)
uv run panos-agent run -p "List address objects" --model haiku

# Balanced (Sonnet - default)
uv run panos-agent run -p "Create a comprehensive security policy for web traffic" --model sonnet

# Most capable (Opus)
uv run panos-agent run -p "Analyze my current security policies and recommend improvements" --model opus
```

### Temperature Control

```bash
# Deterministic (temp=0.0, default)
uv run panos-agent run -p "List objects" --temperature 0.0

# Slightly creative (temp=0.3)
uv run panos-agent run -p "Suggest meaningful names for three web server address objects" --temperature 0.3

# More creative (temp=0.7)
uv run panos-agent run -p "Generate creative but professional names for a DMZ security policy" --temperature 0.7
```

### Streaming vs No-Stream

```bash
# With streaming (default, good for interactive use)
uv run panos-agent run -p "List address objects" --model haiku

# Without streaming (good for CI/CD, scripting)
uv run panos-agent run -p "List address objects" --model haiku --no-stream
```

---

## Deterministic Mode (Workflows)

### Available Workflows

```bash
# Simple 2-step workflow
uv run panos-agent run -p "simple_address" -m deterministic --model haiku

# With approval gate (3 steps)
uv run panos-agent run -p "address_with_approval" -m deterministic --model haiku

# Web server setup (5 steps)
uv run panos-agent run -p "web_server_setup" -m deterministic --model sonnet

# Multiple objects (5 steps)
uv run panos-agent run -p "multi_address_creation" -m deterministic --model sonnet

# Network segmentation (7 steps)
uv run panos-agent run -p "network_segmentation" -m deterministic --model sonnet

# Complete security rule (8 steps)
uv run panos-agent run -p "security_rule_complete" -m deterministic --model sonnet

# End-to-end with commit (6 steps)
uv run panos-agent run -p "complete_security_workflow" -m deterministic --model sonnet
```

---

## Checkpoint Management

### List Checkpoints

```bash
uv run panos-agent checkpoints list
```

### Show Checkpoint Details

```bash
# Replace THREAD_ID with actual thread ID from list command
uv run panos-agent checkpoints show --thread-id THREAD_ID
```

### Resume from Checkpoint

```bash
# Use thread ID from previous run (shown in output)
uv run panos-agent run -p "Continue the conversation" -t THREAD_ID --model haiku
```

### View Checkpoint History

```bash
uv run panos-agent checkpoints history --thread-id THREAD_ID
```

### Delete Checkpoint

```bash
uv run panos-agent checkpoints delete --thread-id THREAD_ID
```

### Prune Old Checkpoints

```bash
# Delete checkpoints older than 7 days
uv run panos-agent checkpoints prune --days 7
```

---

## Advanced Testing Scenarios

### Test Error Handling

```bash
# Invalid object type (should error gracefully)
uv run panos-agent run -p "Create an invalid-type object" --model haiku

# Missing required parameters (should error gracefully)
uv run panos-agent run -p "Create an address object" --model haiku
```

### Test Idempotency

```bash
# Create same object twice (should handle gracefully)
uv run panos-agent run -p "Create address object test-001 at 10.1.1.1" --model haiku
uv run panos-agent run -p "Create address object test-001 at 10.1.1.1" --model haiku
```

### Test Conversation Context

```bash
# Start conversation
uv run panos-agent run -p "Create address object server-A at 10.1.1.1" -t test-session-001 --model haiku

# Continue conversation (remembers context)
uv run panos-agent run -p "Now create server-B at 10.1.1.2" -t test-session-001 --model haiku

# Reference previous work
uv run panos-agent run -p "List all the servers we just created" -t test-session-001 --model haiku
```

---

## Performance Testing

### Quick Response (Haiku)

```bash
time uv run panos-agent run -p "List address objects" --model haiku --no-stream
```

### Complex Operation (Sonnet)

```bash
time uv run panos-agent run -p "Create web-server at 10.1.1.10, then create service http-8080 on TCP port 8080" --model sonnet --no-stream
```

### Deterministic Workflow

```bash
time uv run panos-agent run -p "simple_address" -m deterministic --model haiku --no-stream
```

---

## Logging Levels

### Default (INFO)

```bash
uv run panos-agent run -p "List objects" --model haiku
```

### Debug (verbose)

```bash
uv run panos-agent run -p "List objects" --model haiku -l DEBUG
```

### Warning (quiet)

```bash
uv run panos-agent run -p "List objects" --model haiku -l WARNING
```

---

## Tips

1. **Always start with `--model haiku`** for testing - it's fast and cheap
2. **Use `--no-stream`** when scripting or timing operations
3. **Use thread IDs (`-t`)** to maintain conversation context
4. **Check `list-workflows`** before running deterministic mode
5. **Test connection first** with `test-connection`
6. **Review operations** before committing changes to firewall

---

## Safety Notes

⚠️ **These commands interact with a real firewall!**

- Test create/update/delete operations carefully
- Review changes before committing
- Use test objects (prefix with `test-` or `demo-`)
- Keep backups of firewall configurations
- Consider using a lab/test firewall first

---

**Quick Start:**

```bash
# 1. Test connection
uv run panos-agent test-connection

# 2. List objects (safe, read-only)
uv run panos-agent run -p "List all address objects" --model haiku

# 3. Try a workflow
uv run panos-agent run -p "simple_address" -m deterministic --model haiku
```
