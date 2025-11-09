# LangGraph Studio Setup Guide

LangGraph Studio provides a powerful web-based interface for interacting with your PAN-OS agent, featuring visual debugging, interactive chat, and time-travel capabilities.

## Quick Start

### 1. Prerequisites

✅ Already installed in this project:

- `langgraph` package (v1.0.2)
- `langgraph-cli` (v0.4.7)
- `langgraph.json` configuration file

### 2. Start LangGraph Studio

```bash
# From project root directory
langgraph dev

# Expected output:
# - API server starting at http://localhost:2024
# - Studio UI available at http://localhost:8000
```

### 3. Access the Studio

Open your browser to:

- **Studio UI:** <http://localhost:8000>
- **API Endpoint:** <http://localhost:2024>

---

## Features

### 🎯 Interactive Chat Interface

Chat with your PAN-OS agent in a conversational interface:

1. **Select Graph:**
   - Choose "autonomous" for natural language commands
   - Choose "deterministic" for workflow execution

2. **Start Conversation:**
   - Type your prompt in the chat box
   - Watch the agent think and execute tools in real-time
   - Agent maintains conversation context automatically

3. **View Tool Calls:**
   - See exactly which tools the agent calls
   - View input parameters and outputs
   - Understand the agent's decision-making process

### 🔍 Visual Debugging

**Graph Visualization:**

- See the agent's state machine as a flowchart
- Watch execution flow through nodes in real-time
- Understand branching logic and decision points

**State Inspection:**

- View complete conversation state at any point
- Inspect messages, tool results, and context
- Debug issues by examining state transitions

### ⏰ Time-Travel Debugging

**Checkpoint Navigation:**

- Rewind to any previous point in the conversation
- Fork conversations from historical checkpoints
- Compare different execution paths

**Use Cases:**

- "What if I had asked this differently?"
- Replay failed operations with modifications
- Test alternative approaches without starting over

---

## Example Workflows

### Workflow 1: Basic Agent Interaction

```
1. Start Studio:
   $ langgraph dev

2. Open Studio UI:
   http://localhost:8000

3. Select Graph:
   - Graph: "autonomous"

4. Start Conversation:
   You: "Show network interfaces"

   [Watch agent execute show_interfaces tool]

   Agent: [Displays interface list with IPs, status, speed]

5. Continue Conversation:
   You: "Now show the routing table"

   [Agent remembers context, executes show_routing_table]

   Agent: [Displays routing table]

6. Follow-up:
   You: "Are there any high CPU processes?"

   [Agent uses context from previous questions]
```

### Workflow 2: Debugging with Time-Travel

```
1. Start conversation with agent

2. Execute operation that needs adjustment:
   You: "Create address object 'Server1' with IP 10.1.1.1"

   [Realizes you wanted different IP]

3. Use Time-Travel:
   - Click "Checkpoints" panel
   - Select checkpoint before object creation
   - Click "Fork from here"

4. Try alternative:
   You: "Create address object 'Server1' with IP 10.2.1.1"

   [New conversation branch with correct IP]

5. Compare Results:
   - View both conversation branches side-by-side
   - See different outcomes
```

### Workflow 3: Multi-Vsys Operations

```
1. Studio automatically uses your environment variables

2. Set vsys via environment:
   # In .env file:
   PANOS_AGENT_VSYS=vsys2

3. Restart Studio:
   $ langgraph dev

4. All operations now scoped to vsys2:
   You: "List address objects"

   [Returns objects from vsys2 only]

5. Switch vsys:
   - Update .env: PANOS_AGENT_VSYS=vsys3
   - Restart: langgraph dev
   - New conversations use vsys3
```

---

## Configuration

### langgraph.json

Your project already has this configured:

```json
{
  "graphs": {
    "autonomous": {
      "path": "src/autonomous_graph.py:create_autonomous_graph",
      "description": "Autonomous ReAct agent with full tool access"
    },
    "deterministic": {
      "path": "src/deterministic_graph.py:create_deterministic_graph",
      "description": "Deterministic workflow mode (Ansible-like)"
    }
  },
  "env": ".env",
  "python_version": "3.11"
}
```

### Environment Variables

Studio automatically loads `.env` file with your credentials:

```bash
# Required
PANOS_HOSTNAME=your-firewall.example.com
PANOS_USERNAME=admin
PANOS_PASSWORD=your-password
ANTHROPIC_API_KEY=sk-ant-your-key

# Optional
PANOS_AGENT_VSYS=vsys1  # Multi-vsys support
LANGSMITH_TRACING=true  # Enable LangSmith tracing
LANGSMITH_API_KEY=...   # Your LangSmith key
```

---

## Keyboard Shortcuts

**Studio UI:**

- `Ctrl/Cmd + Enter` - Send message
- `Esc` - Clear input field
- `↑/↓` - Navigate message history
- `Ctrl/Cmd + K` - Open command palette

**Graph View:**

- `+/-` - Zoom in/out
- `Space + Drag` - Pan view
- `F` - Fit graph to screen
- Click node - View node details

---

## Comparison with CLI

| Feature | CLI (`panos-agent run`) | LangGraph Studio |
|---------|------------------------|------------------|
| **Interface** | Command line | Web browser |
| **Conversations** | Manual thread IDs | Automatic threads |
| **Context** | Explicit continuation | Automatic context |
| **Debugging** | Logs only | Visual + state inspection |
| **Time-Travel** | Manual checkpoint commands | Interactive rewind/fork |
| **Tool Visibility** | Log messages | Visual tool cards |
| **Graph Visualization** | None | Interactive flowchart |
| **Multiple Graphs** | Mode flag (`--mode`) | Dropdown selector |

---

## Advanced Features

### Custom Model Selection

Override model via environment variable:

```bash
# In .env
ANTHROPIC_MODEL=claude-opus-4-1-20250805

# Restart Studio
langgraph dev
```

Or use runtime context (requires code modification):

```python
# In autonomous_graph.py
context = {
    "model_name": "claude-haiku-4-5-20251001",  # Fast model
    "temperature": 0.0
}
```

### Parallel Graph Execution

Studio supports running multiple graphs simultaneously:

1. Open multiple browser tabs
2. Each tab can run a different graph
3. Separate thread IDs automatically managed
4. Useful for testing workflows in parallel

### Streaming Responses

Studio shows responses as they stream in:

- Watch agent thinking in real-time
- See tool execution immediately
- Faster feedback than waiting for complete response

---

## Troubleshooting

### Issue: "Port 2024 already in use"

**Cause:** Another LangGraph instance running

**Solution:**

```bash
# Find process using port 2024
lsof -i :2024

# Kill the process
kill -9 <PID>

# Or use different port
langgraph dev --port 3000
```

### Issue: "Cannot load graph"

**Cause:** Graph import error or missing dependencies

**Solution:**

```bash
# Verify graphs load correctly
python -c "from src.autonomous_graph import create_autonomous_graph"
python -c "from src.deterministic_graph import create_deterministic_graph"

# Check logs in terminal for detailed error
```

### Issue: "Environment variables not loaded"

**Cause:** `.env` file not found or incorrectly formatted

**Solution:**

```bash
# Verify .env exists
ls -la .env

# Check langgraph.json points to correct env file
cat langgraph.json | grep env

# Restart Studio after .env changes
```

### Issue: "Studio UI blank/not loading"

**Cause:** Browser cache or JavaScript error

**Solution:**

1. Hard refresh: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
2. Clear browser cache
3. Try incognito/private window
4. Check browser console for errors (F12)

---

## Tips & Best Practices

### 1. Use Descriptive Thread Names

Studio auto-generates thread IDs, but you can name them in the UI:

- Click thread name
- Enter descriptive name: "firewall-troubleshooting", "policy-updates", etc.
- Easier to find conversations later

### 2. Save Important Checkpoints

Mark key points in conversations:

- After successful operations
- Before making risky changes
- At decision points for later comparison

### 3. Monitor Tool Usage

Watch the "Tools" panel to:

- Verify agent selects correct tools
- Check tool parameters are accurate
- Identify unnecessary tool calls (optimization opportunity)

### 4. Use Studio for Development

Perfect for:

- Testing new tools
- Debugging agent behavior
- Understanding graph flow
- Experimenting with prompts

### 5. Switch to CLI for Production

CLI is better for:

- Automated workflows
- CI/CD pipelines
- Scripted operations
- Production deployments

---

## Next Steps

After mastering LangGraph Studio, explore:

1. **Deploy to LangSmith Cloud:**

   ```bash
   langgraph deploy
   ```

   - Remote access to your agent
   - Team collaboration
   - Production monitoring

2. **Agent Chat UI (Phase 4.1):**
   - More polished interface
   - Public sharing capabilities
   - Custom branding options

3. **Custom Workflows:**
   - Create deterministic workflows in Studio
   - Test with visual feedback
   - Export to workflow JSON files

---

## Resources

- **LangGraph Docs:** <https://langchain-ai.github.io/langgraph/>
- **Studio Guide:** <https://langchain-ai.github.io/langgraph/cloud/deployment/>
- **CLI Reference:** <https://langchain-ai.github.io/langgraph/cloud/reference/cli/>
- **Project README:** [README.md](README.md)
- **Testing Examples:** [TESTING_EXAMPLES.md](TESTING_EXAMPLES.md)

---

## Quick Reference

**Start Studio:**

```bash
langgraph dev
```

**Custom Port:**

```bash
langgraph dev --port 3000
```

**Verbose Logging:**

```bash
langgraph dev --verbose
```

**Stop Studio:**

- `Ctrl+C` in terminal running `langgraph dev`

**Studio URL:** <http://localhost:8000>
**API URL:** <http://localhost:2024>

---

**Happy graphing! 🎨**
