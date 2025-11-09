# Claude Model Reference

Complete reference for all supported Claude models in the PAN-OS Agent.

**Last Updated:** January 9, 2025  
**Source:** Anthropic Claude API Documentation

---

## Quick Reference

### Simple Aliases (Recommended)

Use these aliases with the `--model` flag for the latest versions:

```bash
--model sonnet    # Claude Sonnet 4.5 (Latest, Default)
--model opus      # Claude Opus 4.1 (Most Powerful)
--model haiku     # Claude Haiku 4.5 (Fastest, Cheapest)
```

### Version-Specific Aliases

```bash
--model sonnet-4.5    # Claude Sonnet 4.5 (Sep 2025)
--model sonnet-4      # Claude Sonnet 4 (May 2025)
--model sonnet-3.7    # Claude 3.7 Sonnet (Feb 2025) - Hybrid reasoning

--model opus-4.1      # Claude Opus 4.1 (Aug 2025)
--model opus-4        # Claude Opus 4 (May 2025)

--model haiku-4.5     # Claude Haiku 4.5 (Oct 2025)
--model haiku-3.5     # Claude 3.5 Haiku (Oct 2024)
```

---

## Full Model Specifications

### Claude 4 Series (2025) - Current Generation

#### Claude Opus 4.1 (Most Powerful)

- **API Name:** `claude-opus-4-1-20250805`
- **Release Date:** August 5, 2025
- **Alias:** `opus`, `opus-4.1`
- **Context Window:** 200K tokens
- **Max Output:** 32,000 tokens
- **Training Data:** Through March 2025

**Best For:**

- Complex reasoning and analysis
- Security policy auditing
- Multi-constraint decision making
- Advanced code generation
- Novel/ambiguous requests

**Cost:** Highest
**Speed:** Moderate

#### Claude Opus 4

- **API Name:** `claude-opus-4-20250514`
- **Release Date:** May 14, 2025
- **Alias:** `opus-4`
- **Context Window:** 200K tokens
- **Max Output:** 32,000 tokens
- **Training Data:** Through March 2025

**Best For:**

- High-performance tasks requiring strong reasoning
- Complex automation workflows

**Cost:** High
**Speed:** Moderate

#### Claude Sonnet 4.5 (Default, Latest)

- **API Name:** `claude-sonnet-4-5-20250929`
- **Release Date:** September 15, 2025
- **Alias:** `sonnet`, `sonnet-4.5`
- **Context Window:** 200K tokens
- **Max Output:** 64,000 tokens
- **Training Data:** Through March 2025

**Best For:**

- General-purpose automation (DEFAULT)
- Multi-step operations
- Natural language queries
- Production workflows
- Balanced speed and capability

**Cost:** Moderate
**Speed:** Fast

#### Claude Sonnet 4

- **API Name:** `claude-sonnet-4-20250514`
- **Release Date:** May 14, 2025
- **Alias:** `sonnet-4`
- **Context Window:** 200K tokens
- **Max Output:** 64,000 tokens
- **Training Data:** Through March 2025

**Best For:**

- Alternative to Sonnet 4.5 with similar capabilities

**Cost:** Moderate
**Speed:** Fast

#### Claude 3.7 Sonnet (Hybrid Reasoning)

- **API Name:** `claude-3-7-sonnet-20250219`
- **Release Date:** February 19, 2025
- **Alias:** `sonnet-3.7`
- **Context Window:** 200K tokens
- **Max Output:** 64,000 tokens
- **Training Data:** Through October 2024

**Best For:**

- Extended thinking mode
- Complex problem-solving requiring step-by-step reasoning
- Specialized reasoning tasks

**Cost:** Moderate
**Speed:** Slower (extended thinking)

#### Claude Haiku 4.5 (Fastest)

- **API Name:** `claude-haiku-4-5-20251001`
- **Release Date:** October 10, 2025
- **Alias:** `haiku`, `haiku-4.5`
- **Context Window:** 200K tokens
- **Max Output:** 8,192 tokens
- **Training Data:** Through March 2025

**Best For:**

- Simple list operations
- Single CRUD operations
- Batch operations with known patterns
- Development/testing (fast iteration)
- Cost-sensitive production workloads

**Cost:** Lowest
**Speed:** Fastest

### Claude 3 Series (2024) - Previous Generation

#### Claude 3.5 Haiku

- **API Name:** `claude-3-5-haiku-20241022`
- **Release Date:** October 22, 2024
- **Alias:** `haiku-3.5`
- **Context Window:** 200K tokens
- **Max Output:** 8,192 tokens
- **Training Data:** Through July 2024

**Best For:**

- Legacy compatibility
- Fallback for Haiku 4.5

**Cost:** Low
**Speed:** Fast

---

## Model Comparison Table

| Model | Alias | Power | Speed | Cost | Context | Output | Best Use Case |
|-------|-------|-------|-------|------|---------|--------|---------------|
| **Opus 4.1** | `opus` | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | 💵💵💵💵 | 200K | 32K | Complex analysis, auditing |
| **Opus 4** | `opus-4` | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | 💵💵💵💵 | 200K | 32K | High-performance tasks |
| **Sonnet 4.5** | `sonnet` | ⭐⭐⭐⭐ | ⚡⚡⚡⚡ | 💵💵💵 | 200K | 64K | **Default, general use** |
| **Sonnet 4** | `sonnet-4` | ⭐⭐⭐⭐ | ⚡⚡⚡⚡ | 💵💵💵 | 200K | 64K | Alternative to 4.5 |
| **Sonnet 3.7** | `sonnet-3.7` | ⭐⭐⭐⭐ | ⚡⚡ | 💵💵💵 | 200K | 64K | Extended reasoning |
| **Haiku 4.5** | `haiku` | ⭐⭐⭐ | ⚡⚡⚡⚡⚡ | 💵 | 200K | 8K | Fast, cheap operations |
| **Haiku 3.5** | `haiku-3.5` | ⭐⭐⭐ | ⚡⚡⚡⚡ | 💵 | 200K | 8K | Legacy support |

---

## Usage Examples

### Simple Aliases

```bash
# Default (Sonnet 4.5) - no flag needed
panos-agent run -p "Create address object web-server at 10.1.1.100"

# Haiku for speed
panos-agent run -p "List all address objects" --model haiku

# Opus for complex tasks
panos-agent run -p "Audit all security policies for compliance" --model opus
```

### Version-Specific Models

```bash
# Use Sonnet 3.7 for extended reasoning
panos-agent run -p "Analyze complex security architecture" --model sonnet-3.7

# Use Opus 4 specifically
panos-agent run -p "Complex analysis" --model opus-4

# Use older Haiku 3.5
panos-agent run -p "Quick list" --model haiku-3.5
```

### Full Model Names

```bash
# Using full API model name
panos-agent run -p "test" --model claude-sonnet-4-5-20250929

# Direct API name for specific version control
panos-agent run -p "test" --model claude-opus-4-1-20250805
```

---

## Model Selection Guide

### When to Use Each Model

#### Use Haiku (4.5) When

- ✅ Simple CRUD operations
- ✅ List/read operations
- ✅ Known patterns and workflows
- ✅ Development and testing
- ✅ High-volume batch processing
- ✅ Budget constraints

#### Use Sonnet (4.5) When

- ✅ General automation (DEFAULT)
- ✅ Multi-step operations
- ✅ Natural language queries
- ✅ Production workflows
- ✅ Balanced performance needs
- ✅ Most use cases

#### Use Sonnet 3.7 When

- ✅ Need extended thinking/reasoning
- ✅ Complex problem-solving
- ✅ Step-by-step analysis required
- ✅ Specialized reasoning tasks

#### Use Opus (4.1) When

- ✅ Complex security analysis
- ✅ Policy recommendations
- ✅ Multi-constraint decisions
- ✅ Novel/ambiguous requests
- ✅ Quality over speed matters
- ✅ Advanced code generation

### Cost Optimization Strategy

**Development/Testing:**

```bash
# Use Haiku for fast, cheap iteration
panos-agent run -p "test queries" --model haiku
```

**Production - Simple Operations:**

```bash
# Use Haiku for high-volume simple operations
panos-agent run -p "List objects" --model haiku
panos-agent run -p "Create standard address" --model haiku
```

**Production - Standard Operations:**

```bash
# Use Sonnet (default) for most automation
panos-agent run -p "Setup web server rules"
# No flag needed, uses Sonnet 4.5 by default
```

**Production - Complex Operations:**

```bash
# Use Opus when accuracy is critical
panos-agent run -p "Audit security for PCI compliance" --model opus
panos-agent run -p "Analyze and recommend policy changes" --model opus
```

---

## Migration from Old Models

### Updating from Previous Versions

If you were using old model names, update them as follows:

**Old → New:**

- `claude-3-5-sonnet-20241022` → `claude-sonnet-4-5-20250929` (or alias: `sonnet`)
- `claude-3-opus-20240229` → `claude-opus-4-1-20250805` (or alias: `opus`)
- `claude-haiku-4-5` → `claude-haiku-4-5-20251001` (or alias: `haiku`)

**Using Aliases (Recommended):**

```bash
# Old way (outdated model)
--model claude-3-5-sonnet-20241022

# New way (always latest)
--model sonnet
```

### Deprecated Models

The following models were retired on **July 21, 2025**:

- ❌ Claude 2.0
- ❌ Claude 2.1
- ❌ All Claude 1.x models

---

## Model Capabilities

### Context Window (All Current Models)

All Claude 4 and 3.7 models support **200,000 tokens** context window.

### Output Limits

- **Opus models:** 32,000 tokens max output
- **Sonnet models:** 64,000 tokens max output
- **Haiku models:** 8,192 tokens max output

### Training Data Cutoff

- **Claude 4 series:** March 2025
- **Claude 3.7:** October 2024
- **Claude 3.5 Haiku:** July 2024

---

## Programming Notes

### Code Integration

The model aliases are defined in `src/cli/commands.py`:

```python
MODEL_ALIASES = {
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-1-20250805",
    "haiku": "claude-haiku-4-5-20251001",
    # ... more aliases
}
```

Default model in `src/core/config.py`:

```python
@dataclass
class AgentContext:
    model_name: str = "claude-sonnet-4-5-20250929"
    # ...
```

### Updating Models

To add new models as they're released:

1. Update `MODEL_ALIASES` in `src/cli/commands.py`
2. Add to `SUPPORTED_MODELS` list
3. Update documentation
4. Run tests to verify

---

## Additional Resources

- [Anthropic Model Documentation](https://docs.anthropic.com/en/docs/about-claude/models)
- [Claude API Reference](https://docs.anthropic.com/en/api)
- [Model Pricing](https://www.anthropic.com/pricing)
- [Model Comparison](https://docs.anthropic.com/en/docs/about-claude/models/all-models)

---

**Note:** This document is maintained as models evolve. Check Anthropic's official documentation for the most current information.
