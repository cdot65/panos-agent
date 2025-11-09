# Testing Guide - Runtime Context Features

Complete guide for running tests for the runtime context feature (Task 5).

---

## Quick Start

### Simple Test Run

```bash
# Run all runtime context tests
pytest tests/unit/test_runtime_context.py \
       tests/unit/test_cli_model_selection.py \
       tests/unit/test_autonomous_nodes.py::TestCallAgentRuntimeContext \
       tests/integration/test_runtime_context_integration.py
```

### Using the Test Script (Recommended)

```bash
# Run all tests with nice output
./scripts/test_runtime_context.sh

# Run with verbose output
./scripts/test_runtime_context.sh -v

# Run with coverage report
./scripts/test_runtime_context.sh -c

# Run unit tests only (faster)
./scripts/test_runtime_context.sh --unit-only

# Combine options
./scripts/test_runtime_context.sh -v -c
```

---

## Setup Requirements

### 1. Install Dependencies

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock

# Or install all dev dependencies
pip install -e ".[dev]"
```

### 2. Verify Installation

```bash
# Check pytest is available
pytest --version

# Should show: pytest 7.x.x or higher
```

---

## Test Categories

### 1. AgentContext Dataclass Tests (20 tests)

**File:** `tests/unit/test_runtime_context.py`

```bash
# Run all AgentContext tests
pytest tests/unit/test_runtime_context.py -v

# Run specific test class
pytest tests/unit/test_runtime_context.py::TestAgentContextDefaults -v

# Run single test
pytest tests/unit/test_runtime_context.py::TestAgentContextDefaults::test_default_model_name -v
```

**What's tested:**
- Default values (model, temperature, max_tokens)
- Custom values
- Model names validation
- Temperature ranges
- Dataclass properties

### 2. CLI Model Selection Tests (43 tests)

**File:** `tests/unit/test_cli_model_selection.py`

```bash
# Run all CLI tests
pytest tests/unit/test_cli_model_selection.py -v

# Run model alias tests only
pytest tests/unit/test_cli_model_selection.py::TestModelAliases -v
pytest tests/unit/test_cli_model_selection.py::TestResolveModelName -v

# Run CLI flag tests
pytest tests/unit/test_cli_model_selection.py::TestCLIModelFlag -v
pytest tests/unit/test_cli_model_selection.py::TestCLITemperatureFlag -v
```

**What's tested:**
- Model alias resolution (sonnet/opus/haiku)
- CLI flag parsing (--model, --temperature)
- Default values
- Metadata tracking
- Combined flags

### 3. Autonomous Graph Runtime Tests (10 tests)

**File:** `tests/unit/test_autonomous_nodes.py`

```bash
# Run all runtime context tests
pytest tests/unit/test_autonomous_nodes.py::TestCallAgentRuntimeContext -v

# Run specific runtime context test
pytest tests/unit/test_autonomous_nodes.py::TestCallAgentRuntimeContext::test_call_agent_uses_runtime_model_name -v
```

**What's tested:**
- Runtime context parameter passing
- Model name usage in call_agent
- Temperature usage
- Max tokens usage
- Model-specific configurations (Haiku, Opus)

### 4. Integration Tests (6 tests)

**File:** `tests/integration/test_runtime_context_integration.py`

```bash
# Run all integration tests
pytest tests/integration/test_runtime_context_integration.py -v

# Run specific test class
pytest tests/integration/test_runtime_context_integration.py::TestRuntimeContextIntegration -v
```

**What's tested:**
- End-to-end graph execution
- Context persistence across steps
- Default context handling
- Error handling
- Model comparison

---

## Common Test Commands

### Run All Runtime Context Tests

```bash
# All tests (105 total)
pytest tests/unit/test_runtime_context.py \
       tests/unit/test_cli_model_selection.py \
       tests/unit/test_autonomous_nodes.py::TestCallAgentRuntimeContext \
       tests/integration/test_runtime_context_integration.py
```

### Run Unit Tests Only (Faster)

```bash
# Unit tests only (99 tests) - faster
pytest tests/unit/test_runtime_context.py \
       tests/unit/test_cli_model_selection.py \
       tests/unit/test_autonomous_nodes.py::TestCallAgentRuntimeContext
```

### Run with Verbose Output

```bash
# See each test name and result
pytest tests/unit/test_runtime_context.py -v
```

### Run with Coverage

```bash
# Generate coverage report
pytest tests/unit/test_runtime_context.py \
       tests/unit/test_cli_model_selection.py \
       tests/integration/test_runtime_context_integration.py \
       --cov=src.core.config \
       --cov=src.cli.commands \
       --cov=src.autonomous_graph \
       --cov-report=html \
       --cov-report=term-missing

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Run Specific Test Pattern

```bash
# Run all tests matching a pattern
pytest tests/unit/test_runtime_context.py -k "model_name"

# Run tests NOT matching a pattern
pytest tests/unit/test_runtime_context.py -k "not integration"
```

### Stop on First Failure

```bash
# Exit immediately on first failure
pytest tests/unit/test_runtime_context.py -x
```

### Show Test Output

```bash
# Show print statements and logging
pytest tests/unit/test_runtime_context.py -s
```

---

## Test Script Options

The `test_runtime_context.sh` script provides convenient options:

```bash
# Show help
./scripts/test_runtime_context.sh --help

# Options:
#   -v, --verbose     Verbose output with test names
#   -c, --coverage    Generate coverage report
#   --unit-only       Run only unit tests (skip integration)
#   -h, --help        Show help message
```

**Examples:**

```bash
# Default run (quiet mode, all tests)
./scripts/test_runtime_context.sh

# Verbose output
./scripts/test_runtime_context.sh -v

# With coverage
./scripts/test_runtime_context.sh -c

# Unit tests only (faster for quick validation)
./scripts/test_runtime_context.sh --unit-only

# Verbose + coverage
./scripts/test_runtime_context.sh -v -c
```

---

## Expected Output

### Successful Run

```
╔════════════════════════════════════════════════════════════╗
║       Runtime Context Test Suite                          ║
║       Tests for model selection & temperature control     ║
╚════════════════════════════════════════════════════════════╝

Running tests...

tests/unit/test_runtime_context.py ...................... [ 19%]
tests/unit/test_cli_model_selection.py .................. [ 60%]
tests/unit/test_autonomous_nodes.py ............         [ 71%]
tests/integration/test_runtime_context_integration.py .. [100%]

105 passed in 2.34s

╔════════════════════════════════════════════════════════════╗
║  ✓ All Runtime Context tests passed!                      ║
╚════════════════════════════════════════════════════════════╝
```

### With Coverage

```
---------- coverage: platform darwin, python 3.11.13 -----------
Name                           Stmts   Miss  Cover   Missing
------------------------------------------------------------
src/cli/commands.py              250     45    82%   125-130, 245-250
src/core/config.py                45      2    96%   78-79
src/autonomous_graph.py          180     25    86%   245-250, 320-325
------------------------------------------------------------
TOTAL                            475     72    85%

Coverage report: htmlcov/index.html
```

---

## Troubleshooting

### Import Errors

```bash
# If you see "ModuleNotFoundError"
# Make sure you're in the project root
cd /Users/cdot/.cursor/worktrees/panos-agent/CXEog

# Install package in editable mode
pip install -e .
```

### Pytest Not Found

```bash
# Install pytest
pip install pytest pytest-cov

# Verify installation
pytest --version
```

### Virtual Environment Issues

```bash
# Activate virtual environment first
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Then run tests
pytest tests/unit/test_runtime_context.py
```

### Permission Denied (Test Script)

```bash
# Make script executable
chmod +x scripts/test_runtime_context.sh

# Run script
./scripts/test_runtime_context.sh
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Runtime Context

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov
      
      - name: Run runtime context tests
        run: |
          pytest tests/unit/test_runtime_context.py \
                 tests/unit/test_cli_model_selection.py \
                 tests/integration/test_runtime_context_integration.py \
                 --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

### Pre-commit Hook

```bash
# Add to .git/hooks/pre-commit
#!/bin/bash
./scripts/test_runtime_context.sh --unit-only
exit $?
```

---

## Test Development

### Running Tests During Development

```bash
# Watch mode (run tests on file changes) - requires pytest-watch
pip install pytest-watch
ptw tests/unit/test_runtime_context.py

# Run specific test while developing
pytest tests/unit/test_runtime_context.py::TestAgentContextDefaults::test_default_model_name -v -s
```

### Adding New Tests

1. Add test to appropriate file
2. Run specific test to verify
3. Run all tests to ensure no regression
4. Update test count in documentation

```bash
# Test your new test
pytest tests/unit/test_runtime_context.py::TestYourNewClass::test_your_new_test -v

# Run all tests
./scripts/test_runtime_context.sh -v
```

---

## Performance Benchmarks

### Expected Test Times

- **Unit Tests Only:** ~1-2 seconds (99 tests)
- **Integration Tests:** ~3-5 seconds (6 tests)
- **All Tests:** ~4-7 seconds (105 tests)
- **With Coverage:** ~5-8 seconds

### Slow Tests

If tests are running slowly:

```bash
# Show slowest tests
pytest tests/unit/test_runtime_context.py --durations=10

# Run in parallel (requires pytest-xdist)
pip install pytest-xdist
pytest tests/unit/test_runtime_context.py -n auto
```

---

## Additional Commands

### Run All Project Tests

```bash
# Run entire test suite
pytest

# Run with coverage for entire project
pytest --cov=src --cov-report=html
```

### Test Specific Features

```bash
# Test only model aliases
pytest tests/unit/test_cli_model_selection.py::TestModelAliases -v

# Test only temperature
pytest tests/unit/test_cli_model_selection.py::TestCLITemperatureFlag -v

# Test only Haiku configuration
pytest tests/unit/test_autonomous_nodes.py::TestCallAgentRuntimeContext::test_call_agent_haiku_configuration -v
```

---

## Quick Reference Card

```bash
# Fastest: Unit tests only
./scripts/test_runtime_context.sh --unit-only

# Standard: All tests
./scripts/test_runtime_context.sh

# Thorough: All tests with coverage
./scripts/test_runtime_context.sh -v -c

# Debug: Run specific test with output
pytest tests/unit/test_runtime_context.py::TestAgentContextDefaults::test_default_model_name -v -s

# Development: Watch mode
ptw tests/unit/test_runtime_context.py
```

---

## Summary

**Test Count:** 105 tests (99 unit + 6 integration)

**Test Files:**
- `tests/unit/test_runtime_context.py` (20 tests)
- `tests/unit/test_cli_model_selection.py` (43 tests)
- `tests/unit/test_autonomous_nodes.py` (10 new tests)
- `tests/integration/test_runtime_context_integration.py` (6 tests)

**Quick Commands:**
```bash
# Recommended: Use the test script
./scripts/test_runtime_context.sh -v

# Or direct pytest
pytest tests/unit/test_runtime_context.py \
       tests/unit/test_cli_model_selection.py \
       tests/unit/test_autonomous_nodes.py::TestCallAgentRuntimeContext \
       tests/integration/test_runtime_context_integration.py -v
```

---

**Need Help?** See test documentation in `docs/RUNTIME_CONTEXT_TESTS.md`

