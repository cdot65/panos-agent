# Router Test Prompts

Quick reference for testing intelligent routing functionality.

## Quick Test Commands

### ✅ Should Route to **DETERMINISTIC** (Workflow)

```bash
# Web Server Setup
panos-agent run -p "Set up web server"
panos-agent run -p "Configure HTTP and HTTPS services"

# Network Segmentation
panos-agent run -p "Set up network segmentation"
panos-agent run -p "Create DMZ and internal networks"

# Simple Address
panos-agent run -p "Create address for 10.1.1.50 named web-server"
panos-agent run -p "Add an address object for database server"

# Security Workflows
panos-agent run -p "Create complete security rule setup"
panos-agent run -p "Deploy complete security policy with commit"
```

### 🔍 Should Route to **AUTONOMOUS** (Exploratory)

```bash
# Forced Autonomous (Keywords: show me, find, investigate, analyze, explore)
panos-agent run -p "Show me all address objects"
panos-agent run -p "Find policies using web-servers group"
panos-agent run -p "Investigate firewall configuration"
panos-agent run -p "Analyze current security rules"
panos-agent run -p "Explore the configuration"

# Ad-hoc Operations (No Workflow Match)
panos-agent run -p "Delete all unused address objects"
panos-agent run -p "List NAT policies in DMZ zone"
panos-agent run -p "Check if address 10.1.1.50 exists"
panos-agent run -p "Rename object old-server to new-server"
```

### ⚠️ Edge Cases (Likely Autonomous - Low Confidence)

```bash
# Vague requests
panos-agent run -p "Help me with firewall setup"
panos-agent run -p "Fix my firewall"

# Ambiguous (multiple possible workflows)
panos-agent run -p "Create network infrastructure"
panos-agent run -p "Set up servers"

# Missing parameters
panos-agent run -p "Create an address"
panos-agent run -p "Set up something for security"
```

## Observing Router Decisions

### Check Routing in Logs

With `--log-level INFO`, you'll see:

```
INFO Routing decision: deterministic (confidence: 0.85, workflow: web_server_setup)
INFO Routing to deterministic workflow execution
```

Or:

```
INFO Routing decision: autonomous (confidence: 0.45, workflow: None)
INFO Routing to autonomous ReAct execution
```

### Streaming Mode (Default)

Router shows routing decisions in real-time:

```bash
panos-agent run -p "Set up web server"
# Output:
# 🔀 Routing to deterministic mode...
# 📋 Executing workflow: web_server_setup...
```

```bash
panos-agent run -p "Show me address objects"
# Output:
# 🔀 Routing to autonomous mode...
# 🤖 Executing in autonomous mode...
```

## Testing Workflow Discovery

The autonomous agent can discover workflows:

```bash
# List all workflows
panos-agent run -p "What workflows are available?"

# Search by intent
panos-agent run -p "What workflows help with web servers?"

# Get workflow details
panos-agent run -p "Tell me about the network segmentation workflow"
```

## Testing Parameter Extraction

Router extracts parameters from natural language:

```bash
# Should extract: name="db-server", value="192.168.1.100"
panos-agent run -p "Create address for 192.168.1.100 named db-server"

# Should extract: server_ip, http_port
panos-agent run -p "Set up web server at 10.50.1.25 with HTTP on 8080"

# Should extract: dmz_subnet, internal_subnet
panos-agent run -p "Create DMZ subnet 172.16.0.0/24 and internal 10.10.0.0/16"
```

## Testing in LangGraph Studio

1. Open LangGraph Studio: `langgraph dev`
2. Select "router" graph
3. Test prompts in the UI
4. View routing decisions in graph visualization:
   - `classify_request` node shows routing decision
   - Conditional edge shows which execution path taken

## Routing Logic Reference

### Forced Routing Keywords

**Autonomous** (confidence → 0.5):
- explore, investigate, analyze, troubleshoot, debug
- find, show me, what, how many, which

**Deterministic** (confidence × 1.2):
- workflow, standard, procedure, checklist, run, execute

### Confidence Thresholds

- **≥ 0.80**: Route to deterministic workflow
- **< 0.80**: Route to autonomous mode
- **Ambiguous** (multiple high-confidence matches): Autonomous

### Confidence Factors

```python
confidence = (
    intent_clarity * 0.3        # Is intent clear?
    + workflow_match * 0.4      # Does workflow match?
    + param_completeness * 0.2  # Can extract params?
    + complexity_factor * 0.1   # Complexity (lower = higher confidence)
)
```

## Expected Results Table

| Prompt | Expected Route | Confidence | Workflow |
|--------|---------------|------------|----------|
| "Set up web server" | Deterministic | ~0.85 | web_server_setup |
| "Show me policies" | Autonomous | ~0.50 | None |
| "Create address for 10.1.1.50" | Deterministic | ~0.80 | simple_address |
| "Investigate config" | Autonomous | ~0.50 | None |
| "Deploy security policy" | Deterministic | ~0.82 | complete_security_workflow |
| "Find unused objects" | Autonomous | ~0.45 | None |
| "Help me" | Autonomous | ~0.30 | None |

## Automated Test Script

Run comprehensive test suite:

```bash
./scripts/test_router.sh
```

This will test:
- ✅ 5 deterministic routing cases
- ✅ 6 autonomous routing cases
- ✅ 2 edge cases
- ✅ 3 parameter extraction cases
- ✅ 2 workflow discovery cases

**Total**: 18 test scenarios

## Troubleshooting

### Router Always Goes to Autonomous

Check:
1. Workflow metadata properly loaded (`WORKFLOWS` dict)
2. LLM API key configured (`ANTHROPIC_API_KEY`)
3. Intent classifier working (check logs)

### Router Never Goes to Deterministic

Check:
1. Confidence threshold (src/core/intent_classifier.py:20)
2. Workflow matching logic (semantic similarity)
3. Forced routing keywords not triggering autonomous

### Router Errors

```bash
# Check router logs
panos-agent run -p "test" --log-level DEBUG

# Verify router graph compiles
python -c "from src.router_graph import create_router_graph; create_router_graph({})"
```
