# LangGraph Studio - Quick Start

The fastest way to start using your PAN-OS agent interactively.

## 5-Minute Setup

### Step 1: Verify Installation

```bash
# Check langgraph CLI is installed
langgraph --version
# Expected: LangGraph CLI, version 0.4.7
```

✅ Already installed in this project!

### Step 2: Start Studio

```bash
# From project root directory
langgraph dev
```

**Expected Output:**

```
Starting LangGraph server...
- API server: http://localhost:2024
- Studio UI: http://localhost:8000
Ready!
```

### Step 3: Open Studio

Open your browser to: **<http://localhost:8000>**

### Step 4: Select Graph

In the Studio UI:

1. Click "Select Graph" dropdown (top-left)
2. Choose **"autonomous"** (for natural language commands)
3. Click "New Thread" to start a conversation

### Step 5: Start Chatting

Type in the chat box and press Enter:

```
You: Show network interfaces

🤖 Agent responds with interface list...

You: Now show the routing table

🤖 Agent responds with routing table...
  (remembers previous context automatically)

You: Create address object 'web-server' with IP 10.1.1.100

🤖 Agent executes create operation...
```

---

## What You Get

### Interactive Chat

- Type natural language commands
- Agent maintains conversation context
- No need to repeat information

### Visual Tool Execution

- See which tools the agent calls
- View input parameters
- Inspect tool outputs
- Understand agent reasoning

### Time-Travel Debugging

- Rewind to any point in conversation
- Fork from checkpoints to try alternatives
- Compare different approaches

### Graph Visualization

- See agent flow as interactive diagram
- Watch execution traverse nodes
- Understand state transitions

---

## Example Session

### Scenario: Troubleshooting Firewall

```
1. Start Studio:
   $ langgraph dev
   → Open http://localhost:8000

2. Select Graph:
   → autonomous

3. Begin Troubleshooting:

You: Show system resources
→ Agent calls show_system_resources()
→ Shows CPU: 25%, Memory: 45%, Disk: 60%

You: Any high CPU processes?
→ Agent uses context, provides relevant info

You: Show active sessions
→ Agent calls show_sessions()
→ Displays session table

You: Show sessions from 10.1.1.5
→ Agent filters sessions by source IP
→ Returns filtered results

You: Are there any threats from that IP?
→ Agent calls query_threat_logs()
→ Searches for threats from 10.1.1.5
```

**Conversation Context:** Agent remembers the IP address from your previous question and automatically applies filters!

---

## Common Tasks

### Task 1: Check Firewall Health

```
You: Show me system health status

Agent:
- Calls show_system_resources()
- Calls show_interfaces()
- Provides summary with warnings if needed
```

### Task 2: Create Objects

```
You: Create address object 'db-server' with IP 10.2.1.50

Agent:
- Calls address_create tool
- Validates input
- Creates object
- Confirms success
```

### Task 3: Query Logs

```
You: Show high severity threats from last hour

Agent:
- Calls query_threat_logs(severity="high")
- Parses results
- Formats with severity indicators 🔴🟠
```

### Task 4: Multi-Step Operations

```
You: Create address group 'web-servers' with members server1, server2, server3

Agent:
- Calls address_group_create
- Adds all three members
- Confirms group created
```

---

## Tips

### 1. Use Natural Language

You don't need exact syntax:

✅ **Good:**

- "Show interfaces"
- "What's the CPU usage?"
- "Create address object web at 10.1.1.1"

❌ **Not Needed:**

- `show_interfaces()`
- `address_create(name="web", ip="10.1.1.1")`

### 2. Let Agent Maintain Context

Continue conversations naturally:

```
You: Show routing table
Agent: [Displays routes]

You: What about interfaces?  ← Agent knows "about" refers to firewall
Agent: [Shows interfaces]

You: Any errors?  ← Agent understands "errors" means on those interfaces
Agent: [Checks and responds]
```

### 3. Use Time-Travel for Experimentation

Made a mistake? **Rewind and try again:**

1. Click "Checkpoints" panel (right side)
2. Select checkpoint before your action
3. Click "Fork from here"
4. Try alternative approach

### 4. Monitor Tool Calls

Watch the "Tools" panel to:

- Verify agent selects correct tools
- Check parameters are accurate
- Learn how agent interprets your requests

---

## Switching Graphs

### Autonomous Graph (Default)

**Best for:**

- Natural language commands
- Interactive troubleshooting
- Ad-hoc operations
- Exploratory tasks

**Example:**

```
You: Show me everything about interface ethernet1/1
```

### Deterministic Graph

**Best for:**

- Predefined workflows
- Repeatable operations
- Multi-step procedures
- Ansible-like automation

**To use:**

1. Select "deterministic" from graph dropdown
2. Provide workflow name:

   ```
   You: workflow: simple_address
   ```

---

## Stopping Studio

Press `Ctrl+C` in the terminal where `langgraph dev` is running.

Your conversation threads are automatically saved to:

```
data/checkpoints.db
```

You can resume them later by restarting Studio!

---

## Next Steps

### Learn More

- **Full Studio Guide:** [LANGGRAPH_STUDIO.md](LANGGRAPH_STUDIO.md)
- **Testing Examples:** [TESTING_EXAMPLES.md](TESTING_EXAMPLES.md)
- **Panorama Guide:** [docs/PANORAMA.md](docs/PANORAMA.md)
- **Multi-Vsys Guide:** [docs/MULTI_VSYS_SUPPORT.md](docs/MULTI_VSYS_SUPPORT.md)

### Try Advanced Features

- Time-travel debugging
- Parallel graph execution (multiple browser tabs)
- Custom model selection (edit .env)

### Production Use

- Switch to CLI for automation: `panos-agent run -p "..."`
- Deploy to LangSmith Cloud: `langgraph deploy`

---

## Troubleshooting

**Studio won't start?**

```bash
# Check if port is in use
lsof -i :2024

# Try different port
langgraph dev --port 3000
```

**Can't see graphs?**

```bash
# Verify langgraph.json exists
cat langgraph.json

# Check .env file is present
ls -la .env
```

**Need help?**
See [LANGGRAPH_STUDIO.md](LANGGRAPH_STUDIO.md) troubleshooting section.

---

**Ready to go! Start your agent with:** `langgraph dev` 🚀
