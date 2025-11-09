# Deployment Guide

Complete guide to deploying the PAN-OS Agent to LangSmith Cloud for production use.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Environment Configuration](#environment-configuration)
- [Deployment Process](#deployment-process)
- [API Usage](#api-usage)
- [Monitoring and Observability](#monitoring-and-observability)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### 1. LangSmith Account

- Sign up at [https://smith.langchain.com](https://smith.langchain.com)
- Navigate to Settings → API Keys
- Generate a new API key (starts with `lsv2_pt_`)
- Export it: `export LANGSMITH_API_KEY=lsv2_pt_...`

### 2. GitHub Repository

Your code must be in a Git repository (GitHub, GitLab, etc.):

```bash
# Initialize if not already a git repo
git init
git add .
git commit -m "Initial commit"

# Add remote and push
git remote add origin https://github.com/yourusername/panos-agent.git
git push -u origin main
```

### 3. Install LangGraph CLI

```bash
pip install langgraph-cli

# Verify installation
langgraph --version
```

### 4. Required Environment Variables

```bash
# LangSmith API access
export LANGSMITH_API_KEY=lsv2_pt_...

# PAN-OS firewall credentials
export PANOS_HOSTNAME=firewall.example.com
export PANOS_USERNAME=automation
export PANOS_PASSWORD=secure-password

# Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...
```

---

## Initial Setup

### 1. Create LangGraph Configuration

Create `langgraph.json` in your project root (should already exist):

```json
{
  "dependencies": ["."],
  "graphs": {
    "autonomous": "./src/autonomous_graph.py:create_autonomous_graph",
    "deterministic": "./src/deterministic_graph.py:create_deterministic_graph"
  },
  "env": ".env"
}
```

### 2. Prepare Environment File

Create `.env.production` with deployment-specific settings:

```bash
# Firewall connection
PANOS_HOSTNAME=production-firewall.company.com
PANOS_USERNAME=automation
PANOS_PASSWORD=<secure-password>

# LangSmith tracing (optional but recommended)
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=panos-agent-production

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-...
```

**⚠️ Security Note:** Never commit `.env.production` to version control. Add to `.gitignore`.

### 3. Validate Local Configuration

Before deploying, test locally:

```bash
# Test with LangGraph Dev Server
langgraph dev

# Open Studio at http://localhost:8000
# Test both autonomous and deterministic modes
```

---

## Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key | `sk-ant-api...` |
| `PANOS_HOSTNAME` | Firewall hostname/IP | `firewall.company.com` |
| `PANOS_USERNAME` | Firewall username | `automation` |
| `PANOS_PASSWORD` | Firewall password | `secure-password` |

### Optional Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `LANGSMITH_TRACING` | Enable tracing | `false` | `true` |
| `LANGSMITH_PROJECT` | Project name | `default` | `panos-prod` |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG` |

### Setting Variables in LangSmith

After deployment, configure via LangSmith UI:

1. Navigate to your deployment: https://smith.langchain.com/deployments/{deployment-name}
2. Click "Environment Variables"
3. Add/edit variables
4. Click "Save & Redeploy"

---

## Deployment Process

### Step 1: Pre-Deployment Checklist

```bash
# 1. Run tests
uv run pytest tests/unit -v
uv run pytest tests/integration -v  # Optional

# 2. Run linters
uv run flake8 src/
uv run black --check src/

# 3. Verify environment
echo $LANGSMITH_API_KEY  # Should output your key
echo $PANOS_HOSTNAME     # Should output firewall hostname

# 4. Test locally
langgraph dev  # Verify no errors
```

### Step 2: Deploy to LangSmith

```bash
# Deploy with a specific name
langgraph deploy --name panos-agent-prod

# Or let LangSmith auto-generate a name
langgraph deploy
```

**Expected output:**

```
🚀 Deploying panos-agent-prod...
📦 Building container...
⬆️  Uploading to LangSmith Cloud...
✅ Deployment successful!

Deployment URL: https://smith.langchain.com/deployments/panos-agent-prod
API Endpoint: https://panos-agent-prod.api.langsmith.com
```

### Step 3: Configure Environment Variables

In LangSmith UI:

1. Go to deployment settings
2. Add environment variables (see [Environment Configuration](#environment-configuration))
3. Click "Save & Redeploy"

### Step 4: Verify Deployment

```bash
# Test the deployed API
curl -X GET https://panos-agent-prod.api.langsmith.com/health \
  -H "X-API-Key: $LANGSMITH_API_KEY"

# Expected: {"status": "healthy"}
```

---

## API Usage

### REST API Endpoints

#### 1. Create Thread

```bash
curl -X POST https://panos-agent-prod.api.langsmith.com/threads \
  -H "X-API-Key: $LANGSMITH_API_KEY" \
  -H "Content-Type: application/json"
```

**Response:**

```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 2. Run Agent (Autonomous Mode)

```bash
curl -X POST https://panos-agent-prod.api.langsmith.com/threads/{thread_id}/runs \
  -H "X-API-Key: $LANGSMITH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "autonomous",
    "input": {
      "messages": [
        {
          "role": "user",
          "content": "List all address objects on the firewall"
        }
      ]
    }
  }'
```

#### 3. Stream Agent Response

```bash
curl -X POST https://panos-agent-prod.api.langsmith.com/threads/{thread_id}/runs/stream \
  -H "X-API-Key: $LANGSMITH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "autonomous",
    "input": {
      "messages": [
        {
          "role": "user",
          "content": "Create address object web-server with IP 10.0.1.100"
        }
      ]
    }
  }'
```

#### 4. Get Thread State

```bash
curl -X GET https://panos-agent-prod.api.langsmith.com/threads/{thread_id}/state \
  -H "X-API-Key: $LANGSMITH_API_KEY"
```

#### 5. Get Thread History

```bash
curl -X GET https://panos-agent-prod.api.langsmith.com/threads/{thread_id}/history \
  -H "X-API-Key: $LANGSMITH_API_KEY"
```

### Python SDK

See [`examples/api_usage.py`](../examples/api_usage.py) for complete Python examples using the LangGraph SDK.

Quick example:

```python
from langgraph_sdk import get_client

client = get_client(
    url="https://panos-agent-prod.api.langsmith.com",
    api_key=os.environ["LANGSMITH_API_KEY"]
)

# Create thread
thread = await client.threads.create()

# Run agent
response = await client.runs.create(
    thread_id=thread["thread_id"],
    assistant_id="autonomous",
    input={
        "messages": [
            {"role": "user", "content": "List address objects"}
        ]
    }
)
```

---

## Monitoring and Observability

### LangSmith Tracing

All deployed agents automatically trace to LangSmith when `LANGSMITH_TRACING=true`:

1. **View Traces**: https://smith.langchain.com/projects/{your-project}
2. **Filter by deployment**: Use deployment name as tag
3. **View execution graph**: Click on any trace to see step-by-step execution

### Key Metrics to Monitor

| Metric | Location | What to Watch |
|--------|----------|---------------|
| Response Time | LangSmith traces | P95 < 30s for autonomous, < 60s for workflows |
| Error Rate | LangSmith traces | < 5% error rate |
| Token Usage | LangSmith traces | Track costs per operation |
| Tool Success Rate | LangSmith traces | Monitor firewall API failures |

### Alerts and Notifications

Set up alerts in LangSmith:

1. Go to Project Settings → Alerts
2. Configure thresholds:
   - Error rate > 10%
   - Avg response time > 60s
   - Token usage > budget threshold

### Anonymization

Sensitive firewall data is automatically redacted in traces:

- Firewall hostnames → `<FIREWALL_HOST>`
- IP addresses → `<IP_ADDRESS>`
- Passwords → `<REDACTED>`
- API keys → `<REDACTED>`

See `src/core/anonymizers.py` for full anonymization rules.

---

## Troubleshooting

### Common Issues

#### 1. Deployment Fails - "Invalid API Key"

**Symptom:**
```
Error: Authentication failed. Invalid API key.
```

**Solution:**
```bash
# Verify API key is set
echo $LANGSMITH_API_KEY

# Re-export if needed
export LANGSMITH_API_KEY=lsv2_pt_...

# Verify it works
langgraph deploy
```

#### 2. Agent Returns "Firewall Connection Error"

**Symptom:**
```json
{
  "error": "PAN-OS connectivity error: HTTP error 403"
}
```

**Solution:**

1. Check environment variables are set in deployment
2. Verify firewall credentials are correct
3. Test firewall connectivity:

```bash
curl -k "https://$PANOS_HOSTNAME/api/?type=version&key=YOUR_API_KEY"
```

#### 3. High Latency / Slow Responses

**Symptom:** Responses taking > 60 seconds

**Possible Causes:**

- Firewall is slow to respond (check firewall load)
- Network latency between LangSmith and firewall
- Large number of concurrent requests

**Solutions:**

1. Increase timeout in deployment config
2. Add retry logic with exponential backoff (already implemented)
3. Scale deployment (contact LangSmith support)

#### 4. Memory Store Issues

**Symptom:** Agent doesn't remember previous operations

**Solution:**

Verify Store API is configured in graph creation:

```python
# In autonomous_graph.py
store = InMemoryStore()
graph = create_autonomous_graph(checkpointer=checkpointer, store=store)
```

### Debug Mode

Enable debug logging in deployment:

1. Set `LOG_LEVEL=DEBUG` in environment variables
2. Redeploy
3. Check traces in LangSmith for detailed logs

---

## Rollback Procedures

### Option 1: Redeploy Previous Version

```bash
# List deployments
langgraph deployments list

# Redeploy specific version
langgraph deploy --revision {previous-revision-hash}
```

### Option 2: Rollback via LangSmith UI

1. Go to https://smith.langchain.com/deployments/{deployment-name}
2. Click "Revisions" tab
3. Find previous working revision
4. Click "Redeploy"

### Option 3: Emergency Shutdown

```bash
# Delete deployment entirely
langgraph deployment delete panos-agent-prod

# Then redeploy from known-good commit
git checkout {good-commit-hash}
langgraph deploy --name panos-agent-prod
```

---

## Production Best Practices

### 1. Use Separate Environments

Create separate deployments for dev/staging/prod:

```bash
# Development
langgraph deploy --name panos-agent-dev

# Staging
langgraph deploy --name panos-agent-staging

# Production
langgraph deploy --name panos-agent-prod
```

### 2. Implement CI/CD

Example GitHub Actions workflow:

```yaml
name: Deploy to LangSmith

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install langgraph-cli

      - name: Deploy to LangSmith
        env:
          LANGSMITH_API_KEY: ${{ secrets.LANGSMITH_API_KEY }}
        run: langgraph deploy --name panos-agent-prod
```

### 3. Monitor Costs

Track token usage in LangSmith:

- Set budget alerts
- Monitor usage by model (Haiku vs Sonnet)
- Optimize prompts to reduce token consumption

### 4. Rate Limiting

Implement rate limiting to prevent abuse:

```python
# In your API wrapper
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=100, period=60)  # 100 calls per minute
async def call_agent(input_data):
    # Your agent invocation
    pass
```

---

## Support

- **LangSmith Docs**: https://docs.smith.langchain.com/
- **LangGraph Cloud**: https://langchain-ai.github.io/langgraph/cloud/
- **Issues**: File issues in your repository
- **LangSmith Support**: support@langchain.com

---

**Last Updated**: 2025-01-09
