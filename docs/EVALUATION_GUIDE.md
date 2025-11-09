# Evaluation Dataset Usage Guide

Complete guide on using LangSmith datasets for testing, CI/CD, and quality assurance.

## Table of Contents

1. [Using Datasets in Testing](#using-datasets-in-testing)
2. [CI/CD Integration](#cicd-integration)
3. [Creating New Datasets](#creating-new-datasets)
4. [Extending Existing Datasets](#extending-existing-datasets)
5. [Best Practices](#best-practices)

---

## Using Datasets in Testing

### Example 1: Manual Testing Before Deployment

```bash
# Run full evaluation suite
uv run python scripts/evaluate.py --mode both --save-results

# Check results
cat evaluation_results/eval_autonomous_*.json | jq '.success_rate'
# Should be ≥ 0.90 (90%)

# If success rate is low, investigate failures
cat evaluation_results/eval_autonomous_*.json | jq '.results[] | select(.success == false)'
```

### Example 2: Automated pytest Integration

Create `tests/evaluation/test_evaluation_suite.py`:

```python
"""Integration tests using evaluation datasets."""

import json
import pytest
from pathlib import Path
from scripts.evaluate import (
    EXAMPLE_DATASET,
    evaluate_autonomous_mode,
    evaluate_deterministic_mode,
)
from src.autonomous_graph import create_autonomous_graph
from src.deterministic_graph import create_deterministic_graph


class TestEvaluationSuite:
    """Test agent against evaluation dataset."""

    @pytest.fixture
    def autonomous_graph(self):
        """Create autonomous graph for testing."""
        return create_autonomous_graph()

    @pytest.fixture
    def deterministic_graph(self):
        """Create deterministic graph for testing."""
        return create_deterministic_graph()

    def test_autonomous_mode_success_rate(self, autonomous_graph):
        """Test that autonomous mode meets success rate threshold."""
        metrics = evaluate_autonomous_mode(EXAMPLE_DATASET, autonomous_graph)
        
        # Assert minimum success rate
        assert metrics["success_rate"] >= 0.90, (
            f"Success rate {metrics['success_rate']:.1%} below 90% threshold. "
            f"Failed: {metrics['failed']}/{metrics['total_examples']}"
        )

    def test_autonomous_mode_tool_accuracy(self, autonomous_graph):
        """Test that correct tools are selected."""
        metrics = evaluate_autonomous_mode(EXAMPLE_DATASET, autonomous_graph)
        
        # Count tool accuracy
        tool_correct = sum(
            1 for r in metrics["results"] 
            if r.get("success", False) and r.get("tool_calls")
        )
        tool_accuracy = tool_correct / metrics["total_examples"]
        
        assert tool_accuracy >= 0.95, (
            f"Tool accuracy {tool_accuracy:.1%} below 95% threshold"
        )

    def test_autonomous_mode_token_efficiency(self, autonomous_graph):
        """Test that token usage is reasonable."""
        metrics = evaluate_autonomous_mode(EXAMPLE_DATASET, autonomous_graph)
        
        avg_tokens = metrics.get("avg_tokens_per_example", 0)
        assert avg_tokens < 10000, (
            f"Average token usage {avg_tokens:.0f} exceeds 10k threshold"
        )

    def test_deterministic_mode_success_rate(self, deterministic_graph):
        """Test that deterministic mode meets success rate threshold."""
        metrics = evaluate_deterministic_mode(EXAMPLE_DATASET, deterministic_graph)
        
        assert metrics["success_rate"] >= 0.90, (
            f"Success rate {metrics['success_rate']:.1%} below 90% threshold"
        )

    def test_specific_category(self, autonomous_graph):
        """Test specific category (e.g., CRUD operations)."""
        crud_examples = [
            ex for ex in EXAMPLE_DATASET 
            if ex.get("category") == "crud_create"
        ]
        
        if crud_examples:
            metrics = evaluate_autonomous_mode(crud_examples, autonomous_graph)
            assert metrics["success_rate"] >= 0.90, (
                f"CRUD create success rate {metrics['success_rate']:.1%} below threshold"
            )

    def test_error_handling(self, autonomous_graph):
        """Test that error cases are handled gracefully."""
        error_examples = [
            ex for ex in EXAMPLE_DATASET 
            if ex.get("category") == "error_case"
        ]
        
        if error_examples:
            metrics = evaluate_autonomous_mode(error_examples, autonomous_graph)
            # Error handling should never crash
            assert metrics["failed"] == 0 or all(
                "error" in r for r in metrics["results"] if not r["success"]
            )
```

Run with:

```bash
pytest tests/evaluation/test_evaluation_suite.py -v
```

### Example 3: Load Custom Dataset in Tests

```python
"""Test with custom LangSmith dataset."""

import pytest
from scripts.evaluate import load_langsmith_dataset, evaluate_autonomous_mode
from src.autonomous_graph import create_autonomous_graph


@pytest.mark.skipif(
    not os.getenv("LANGSMITH_API_KEY"),
    reason="LangSmith API key not configured"
)
def test_custom_dataset():
    """Test with custom dataset from LangSmith."""
    # Load dataset
    examples = load_langsmith_dataset("panos-agent-production-tests")
    
    # Run evaluation
    graph = create_autonomous_graph()
    metrics = evaluate_autonomous_mode(examples, graph)
    
    # Assert thresholds
    assert metrics["success_rate"] >= 0.95  # Higher threshold for production
```

### Example 4: Compare Two Versions

```python
"""Compare agent performance across versions."""

def compare_versions(version_a_graph, version_b_graph):
    """Compare two agent versions."""
    metrics_a = evaluate_autonomous_mode(EXAMPLE_DATASET, version_a_graph)
    metrics_b = evaluate_autonomous_mode(EXAMPLE_DATASET, version_b_graph)
    
    print(f"Version A: {metrics_a['success_rate']:.1%} success")
    print(f"Version B: {metrics_b['success_rate']:.1%} success")
    
    # Check for regressions
    if metrics_b["success_rate"] < metrics_a["success_rate"]:
        regression = metrics_a["success_rate"] - metrics_b["success_rate"]
        if regression > 0.05:  # 5% drop
            raise AssertionError(
                f"Regression detected: {regression:.1%} drop in success rate"
            )
    
    return metrics_a, metrics_b
```

---

## CI/CD Integration

### Example 1: GitHub Actions Workflow

Create `.github/workflows/evaluation.yml`:

```yaml
name: Evaluation Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    # Run weekly on Monday
    - cron: '0 0 * * 1'

jobs:
  evaluate:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Run evaluation (CI mode)
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          LANGSMITH_API_KEY: ${{ secrets.LANGSMITH_API_KEY }}
          PANOS_HOSTNAME: ${{ secrets.PANOS_HOSTNAME }}
          PANOS_USERNAME: ${{ secrets.PANOS_USERNAME }}
          PANOS_PASSWORD: ${{ secrets.PANOS_PASSWORD }}
        run: |
          make ci-evaluate
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: evaluation-results
          path: evaluation_results/
```

**Note:** The Makefile handles:

- Virtual environment creation
- Dependency installation
- Running evaluation
- Success rate validation
- All in one command: `make ci-evaluate`

### Example 2: Pre-commit Hook

Create `.git/hooks/pre-push`:

```bash
#!/bin/bash
# Run evaluation before pushing

echo "Running evaluation suite..."

python scripts/evaluate.py --mode both --save-results

# Check if success rate meets threshold
python -c "
import json
from pathlib import Path

results = list(Path('evaluation_results').glob('eval_*.json'))
for result_file in results:
    with open(result_file) as f:
        data = json.load(f)
        if data['metrics']['success_rate'] < 0.90:
            print(f'ERROR: {result_file.name} success rate below 90%')
            exit(1)
"

if [ $? -ne 0 ]; then
    echo "Evaluation failed. Fix issues before pushing."
    exit 1
fi

echo "Evaluation passed!"
```

### Example 3: Makefile (Already Included!)

The project includes a comprehensive `Makefile`. Usage:

```bash
# Local evaluation (saves results)
make evaluate

# CI evaluation (fails if <90% success rate)
make evaluate-ci

# Dataset management
make dataset-create DATASET=panos-agent-eval-v1
make dataset-list
make dataset-delete DATASET=panos-agent-eval-v1

# Setup (handles venv and dependencies automatically)
make install
```

The Makefile automatically:

- Checks for `uv` installation
- Creates virtual environment if needed
- Installs dependencies
- Handles both local and CI environments

See `make help` for all available targets.

---

## Creating New Datasets

### Example 1: Create Production Dataset

```python
"""Create production-focused evaluation dataset."""

PRODUCTION_DATASET = [
    {
        "name": "Production: Create web server",
        "input": {
            "messages": [
                HumanMessage(
                    content="Create address object web-prod-01 at 10.0.1.100 with description 'Production web server'"
                )
            ]
        },
        "expected_tool": "address_create",
        "category": "production_crud",
        "mode": "autonomous",
    },
    {
        "name": "Production: Security policy",
        "input": {
            "messages": [
                HumanMessage(
                    content="Create security policy allowing web-prod-01 to access database-prod on port 5432"
                )
            ]
        },
        "expected_tools": ["address_create", "service_create", "security_policy_create"],
        "category": "production_policy",
        "mode": "autonomous",
    },
    # ... more production examples
]

# Create in LangSmith
python scripts/evaluate.py --create-dataset --dataset panos-agent-production-v1
```

### Example 2: Create Edge Case Dataset

```python
"""Dataset focused on edge cases and error scenarios."""

EDGE_CASE_DATASET = [
    {
        "name": "Edge: Very long object name",
        "input": {
            "messages": [
                HumanMessage(
                    content=f"Create address object {'a' * 200} at 192.168.1.1"
                )
            ]
        },
        "expected_behavior": "error_handling",
        "category": "edge_case",
        "mode": "autonomous",
    },
    {
        "name": "Edge: Special characters in name",
        "input": {
            "messages": [
                HumanMessage(
                    content="Create address object server@#$% at 192.168.1.1"
                )
            ]
        },
        "expected_behavior": "error_handling",
        "category": "edge_case",
        "mode": "autonomous",
    },
    # ... more edge cases
]
```

### Example 3: Create Performance Benchmark Dataset

```python
"""Dataset for performance benchmarking."""

PERFORMANCE_DATASET = [
    {
        "name": "Perf: Simple list (baseline)",
        "input": {"messages": [HumanMessage(content="List address objects")]},
        "expected_tool": "address_list",
        "category": "performance",
        "mode": "autonomous",
        "max_tokens": 5000,  # Performance constraint
        "max_time": 5.0,     # 5 second timeout
    },
    # ... more performance tests
]
```

### Example 4: Create Workflow-Specific Dataset

```python
"""Dataset for testing specific workflows."""

WORKFLOW_DATASET = [
    {
        "name": "Workflow: Complete web server setup",
        "input": {"messages": [HumanMessage(content="workflow: web_server_setup")]},
        "expected_steps": 4,
        "expected_tools": ["address_create", "service_create", "security_policy_create", "commit"],
        "category": "workflow_complete",
        "mode": "deterministic",
    },
    # ... more workflow tests
]
```

---

## Extending Existing Datasets

### Example 1: Add More CRUD Examples

```python
"""Extend existing dataset with more CRUD operations."""

ADDITIONAL_CRUD_EXAMPLES = [
    {
        "name": "Update address object",
        "input": {
            "messages": [
                HumanMessage(
                    content="Update address object web-server to use IP 192.168.1.200"
                )
            ]
        },
        "expected_tool": "address_update",
        "category": "crud_update",
        "mode": "autonomous",
    },
    {
        "name": "Read address object",
        "input": {
            "messages": [
                HumanMessage(content="Show details for address object web-server")
            ]
        },
        "expected_tool": "address_read",
        "category": "crud_read",
        "mode": "autonomous",
    },
]

# Add to existing dataset
EXTENDED_DATASET = EXAMPLE_DATASET + ADDITIONAL_CRUD_EXAMPLES

# Create new dataset
python scripts/evaluate.py --create-dataset --dataset panos-agent-extended-v1
```

### Example 2: Add Category-Specific Examples

```python
"""Add examples for specific PAN-OS categories."""

NAT_POLICY_EXAMPLES = [
    {
        "name": "Create NAT policy",
        "input": {
            "messages": [
                HumanMessage(
                    content="Create NAT policy translating source 10.0.1.0/24 to 203.0.113.0/24"
                )
            ]
        },
        "expected_tool": "nat_policy_create",
        "category": "nat_policy",
        "mode": "autonomous",
    },
]

SERVICE_GROUP_EXAMPLES = [
    {
        "name": "Create service group",
        "input": {
            "messages": [
                HumanMessage(
                    content="Create service group web-services containing http, https, ssh"
                )
            ]
        },
        "expected_tool": "service_group_create",
        "category": "service_group",
        "mode": "autonomous",
    },
]

# Combine all
COMPREHENSIVE_DATASET = (
    EXAMPLE_DATASET +
    NAT_POLICY_EXAMPLES +
    SERVICE_GROUP_EXAMPLES
)
```

### Example 3: Add Multi-Language/Format Examples

```python
"""Test agent with different input formats."""

FORMAT_VARIATIONS = [
    {
        "name": "Format: Natural language",
        "input": {
            "messages": [
                HumanMessage(
                    content="I need to add a new web server with IP address 192.168.1.100"
                )
            ]
        },
        "expected_tool": "address_create",
        "category": "format_natural",
        "mode": "autonomous",
    },
    {
        "name": "Format: Command-like",
        "input": {
            "messages": [
                HumanMessage(content="add address web-server 192.168.1.100")
            ]
        },
        "expected_tool": "address_create",
        "category": "format_command",
        "mode": "autonomous",
    },
    {
        "name": "Format: Question",
        "input": {
            "messages": [
                HumanMessage(content="How do I create an address object for 192.168.1.100?")
            ]
        },
        "expected_behavior": "helpful_response",
        "category": "format_question",
        "mode": "autonomous",
    },
]
```

---

## Best Practices

### 1. Dataset Organization

- **Separate datasets by purpose:**
  - `panos-agent-baseline-v1` - Core functionality
  - `panos-agent-production-v1` - Production scenarios
  - `panos-agent-edge-cases-v1` - Edge cases and errors
  - `panos-agent-performance-v1` - Performance benchmarks

### 2. Example Quality

- **Clear expectations:** Each example should have unambiguous expected behavior
- **Realistic scenarios:** Use real-world use cases, not contrived examples
- **Coverage:** Include positive cases, negative cases, and edge cases
- **Documentation:** Add comments explaining why each example exists

### 3. Versioning

- **Version your datasets:** `panos-agent-eval-v1`, `panos-agent-eval-v2`
- **Track changes:** Document what changed between versions
- **Maintain baselines:** Keep old versions for regression testing

### 4. Continuous Improvement

- **Add failing cases:** When you find bugs, add them as test cases
- **Remove obsolete cases:** Update examples when features change
- **Regular reviews:** Review dataset quarterly for relevance

### 5. Metrics Tracking

- **Track trends:** Monitor success rate over time
- **Category breakdown:** Track performance by category
- **Token costs:** Monitor token usage trends
- **Failure analysis:** Analyze failures to improve dataset

---

## Quick Reference

### Common Commands

```bash
# Run evaluation
uv run python scripts/evaluate.py --mode both --save-results

# Create new dataset
uv run python scripts/evaluate.py --create-dataset --dataset my-dataset-name

# Use specific dataset
uv run python scripts/evaluate.py --dataset panos-agent-eval-v1 --mode autonomous

# Run in pytest
pytest tests/evaluation/ -v

# Check success rate
python -c "import json; print(json.load(open('evaluation_results/eval_autonomous_*.json'))['metrics']['success_rate'])"
```

### Success Rate Thresholds

- **Production:** ≥95%
- **Development:** ≥90%
- **Experimental:** ≥80%

### Token Efficiency Targets

- **Simple queries:** <5k tokens
- **CRUD operations:** <8k tokens  
- **Complex workflows:** <15k tokens

---

**Last Updated:** 2025-01-08
