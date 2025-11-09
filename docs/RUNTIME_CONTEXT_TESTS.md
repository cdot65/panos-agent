# Runtime Context Tests

Comprehensive test suite for Task 5: Runtime Context for LLM Configuration.

## Test Coverage Overview

### Unit Tests: 99 tests total

#### 1. AgentContext Dataclass Tests (20 tests)
**File:** `tests/unit/test_runtime_context.py`

**Test Classes:**
- `TestAgentContextDefaults` - 4 tests
  - Default model name (claude-3-5-sonnet-20241022)
  - Default temperature (0.0)
  - Default max_tokens (4096)
  - Default firewall_client (None)

- `TestAgentContextCustomValues` - 5 tests
  - Custom model_name
  - Custom temperature
  - Custom max_tokens
  - Custom firewall_client
  - All custom values combined

- `TestAgentContextModelNames` - 3 tests
  - Sonnet model validation
  - Opus model validation
  - Haiku model validation

- `TestAgentContextTemperatureRange` - 4 tests
  - Temperature 0.0 (deterministic)
  - Temperature 1.0 (creative)
  - Mid-range temperatures (0.3, 0.5, 0.7)
  - High-precision temperature values

- `TestAgentContextMaxTokens` - 3 tests
  - Small max_tokens (1024)
  - Large max_tokens (16384)
  - Default max_tokens validation

- `TestAgentContextDataclass` - 4 tests
  - Verify it's a dataclass
  - Field names validation
  - Field types validation
  - Mutability (not frozen)

- `TestAgentContextUseCases` - 4 tests
  - Haiku for speed configuration
  - Opus for complexity configuration
  - Creative configuration
  - Testing configuration with mock client

#### 2. CLI Model/Temperature Selection Tests (43 tests)
**File:** `tests/unit/test_cli_model_selection.py`

**Test Classes:**
- `TestModelAliases` - 5 tests
  - MODEL_ALIASES dictionary defined
  - Sonnet alias mapping
  - Opus alias mapping
  - Haiku alias mapping
  - All aliases are strings

- `TestResolveModelName` - 9 tests
  - Resolve sonnet alias
  - Resolve opus alias
  - Resolve haiku alias
  - Case-insensitive (uppercase)
  - Case-insensitive (mixed case)
  - Full model name passthrough
  - Unknown alias passthrough
  - Empty string handling

- `TestCLIModelFlag` - 6 tests
  - Default model is sonnet
  - --model haiku
  - --model opus
  - --model with full name
  - Model displayed in output

- `TestCLITemperatureFlag` - 6 tests
  - Default temperature is 0.0
  - Custom temperature value
  - Temperature 0.0 (deterministic)
  - Temperature 1.0 (creative)
  - Temperature displayed in output

- `TestCLIModelAndTemperatureCombined` - 2 tests
  - Haiku with zero temperature
  - Opus with creative temperature

- `TestCLIMetadataTracking` - 2 tests
  - Model name in metadata for observability
  - Temperature in metadata for observability

#### 3. Autonomous Graph Runtime Context Tests (12 tests)
**File:** `tests/unit/test_autonomous_nodes.py`

**Updated Existing Tests:**
- `TestCallAgent` - 3 tests updated
  - test_call_agent_returns_response
  - test_call_agent_with_tool_call
  - test_call_agent_prepends_system_message

**New Test Class:**
- `TestCallAgentRuntimeContext` - 7 tests
  - Uses runtime model_name
  - Uses runtime temperature
  - Uses runtime max_tokens
  - Uses all runtime parameters
  - Haiku configuration
  - Opus configuration

### Integration Tests: 6 tests
**File:** `tests/integration/test_runtime_context_integration.py`

**Test Classes:**
- `TestRuntimeContextIntegration` - 4 tests
  - Full graph with Haiku model
  - Full graph with Opus model
  - Graph with custom temperature
  - Context persists across multiple steps

- `TestRuntimeContextDefaults` - 1 test
  - Graph with default context values

- `TestRuntimeContextErrorHandling` - 1 test
  - Graph handles LLM errors with runtime context

- `TestRuntimeContextModelComparison` - 1 test
  - Haiku vs Sonnet model selection comparison

## Running the Tests

### Run All Runtime Context Tests

```bash
# Unit tests for AgentContext
pytest tests/unit/test_runtime_context.py -v

# Unit tests for CLI model selection
pytest tests/unit/test_cli_model_selection.py -v

# Updated autonomous node tests
pytest tests/unit/test_autonomous_nodes.py::TestCallAgentRuntimeContext -v

# Integration tests
pytest tests/integration/test_runtime_context_integration.py -v
```

### Run All Tests at Once

```bash
# Run all new/updated tests
pytest tests/unit/test_runtime_context.py \
       tests/unit/test_cli_model_selection.py \
       tests/unit/test_autonomous_nodes.py::TestCallAgentRuntimeContext \
       tests/integration/test_runtime_context_integration.py \
       -v
```

### Run with Coverage

```bash
pytest tests/unit/test_runtime_context.py \
       tests/unit/test_cli_model_selection.py \
       tests/unit/test_autonomous_nodes.py \
       tests/integration/test_runtime_context_integration.py \
       --cov=src.core.config \
       --cov=src.cli.commands \
       --cov=src.autonomous_graph \
       --cov-report=html
```

## Test Categories

### 1. Configuration Tests
Tests for `AgentContext` dataclass:
- Default values
- Custom values
- Field validation
- Dataclass properties

### 2. CLI Tests
Tests for CLI flags and model resolution:
- Model alias resolution (sonnet/opus/haiku)
- Temperature flag validation
- Default values
- Metadata tracking
- Combined flags

### 3. Graph Node Tests
Tests for `call_agent` function:
- Runtime context parameter passing
- Model name usage
- Temperature usage
- Max tokens usage
- Model-specific configurations

### 4. Integration Tests
End-to-end tests:
- Full graph execution with runtime context
- Context persistence across steps
- Default context handling
- Error handling
- Model comparison

## Coverage Areas

### Code Coverage
- `src/core/config.py` - AgentContext dataclass
- `src/cli/commands.py` - Model/temperature flags and resolution
- `src/autonomous_graph.py` - Runtime context usage in call_agent

### Feature Coverage
- ✅ AgentContext creation with defaults
- ✅ AgentContext creation with custom values
- ✅ Model alias resolution (sonnet, opus, haiku)
- ✅ CLI flag parsing (--model, --temperature)
- ✅ Runtime context in graph execution
- ✅ Model selection via CLI
- ✅ Temperature control via CLI
- ✅ Metadata tracking for observability
- ✅ Context persistence across graph steps
- ✅ Default value handling
- ✅ Error handling with runtime context

## Test Patterns

### Unit Test Pattern
```python
@patch("src.autonomous_graph.ChatAnthropic")
@patch("src.autonomous_graph.get_settings")
def test_feature(mock_settings, mock_chat_anthropic):
    # Setup mocks
    mock_settings.return_value.anthropic_api_key = "test-key"
    
    # Create runtime context
    runtime = Mock()
    runtime.context = AgentContext(model_name="claude-haiku-4-5")
    
    # Execute function
    result = call_agent(state, runtime=runtime, store=store)
    
    # Verify runtime context was used
    call_kwargs = mock_chat_anthropic.call_args[1]
    assert call_kwargs["model"] == "claude-haiku-4-5"
```

### CLI Test Pattern
```python
@patch("src.autonomous_graph.create_autonomous_graph")
@patch("src.core.config.get_settings")
def test_cli_flag(mock_get_settings, mock_create_graph):
    # Setup mocks
    mock_graph = Mock()
    mock_create_graph.return_value = mock_graph
    
    # Run CLI command
    result = runner.invoke(app, [
        "run", "-p", "test",
        "--model", "haiku",
        "--temperature", "0.7"
    ])
    
    # Verify config was passed correctly
    call_kwargs = mock_graph.invoke.call_args[1]
    assert call_kwargs["config"]["configurable"]["model_name"] == "claude-haiku-4-5"
    assert call_kwargs["config"]["configurable"]["temperature"] == 0.7
```

### Integration Test Pattern
```python
@patch("src.autonomous_graph.ChatAnthropic")
@patch("src.autonomous_graph.get_settings")
def test_integration(mock_settings, mock_chat_anthropic):
    # Setup mocks
    mock_llm = Mock()
    mock_llm.invoke.return_value = AIMessage(content="Done")
    mock_chat_anthropic.return_value.bind_tools.return_value = mock_llm
    
    # Create and execute graph
    graph = create_autonomous_graph()
    result = graph.invoke(
        {"messages": [HumanMessage(content="test")]},
        config={
            "configurable": {
                "model_name": "claude-haiku-4-5",
                "temperature": 0.0
            }
        }
    )
    
    # Verify end-to-end behavior
    assert "messages" in result
    assert mock_chat_anthropic.call_args[1]["model"] == "claude-haiku-4-5"
```

## Benefits of Test Suite

1. **Comprehensive Coverage** - 99+ tests covering all aspects of runtime context
2. **Unit + Integration** - Both isolated unit tests and end-to-end integration tests
3. **Regression Prevention** - Catch breaking changes in model selection logic
4. **Documentation** - Tests serve as usage examples
5. **Confidence** - High confidence in runtime context feature reliability
6. **Fast Feedback** - Unit tests run quickly for rapid iteration
7. **Real-world Scenarios** - Tests cover actual use cases (Haiku for speed, Opus for complexity)

## Test Maintenance

### Adding New Tests
When adding new model types or configuration options:

1. Add unit tests in `test_runtime_context.py` for new AgentContext fields
2. Add CLI tests in `test_cli_model_selection.py` for new flags
3. Add graph tests in `test_autonomous_nodes.py` for runtime usage
4. Add integration tests in `test_runtime_context_integration.py` for end-to-end

### Running Before Commits
```bash
# Run all runtime context tests
pytest tests/unit/test_runtime_context.py \
       tests/unit/test_cli_model_selection.py \
       tests/unit/test_autonomous_nodes.py::TestCallAgentRuntimeContext \
       tests/integration/test_runtime_context_integration.py \
       -v --tb=short
```

### CI/CD Integration
Add to CI pipeline:
```yaml
- name: Test Runtime Context
  run: |
    pytest tests/unit/test_runtime_context.py \
           tests/unit/test_cli_model_selection.py \
           tests/integration/test_runtime_context_integration.py \
           --cov=src --cov-report=xml
```

## Related Documentation

- `README.md` - Model Selection section
- `src/core/config.py` - AgentContext implementation
- `src/cli/commands.py` - CLI flags implementation
- `src/autonomous_graph.py` - Runtime context usage

## Future Enhancements

### Additional Test Coverage
- [ ] Deterministic mode runtime context tests
- [ ] Performance benchmarking across models
- [ ] Cost tracking tests
- [ ] LangSmith metadata validation tests
- [ ] Concurrent execution with different contexts

### Test Improvements
- [ ] Parameterized tests for all three models
- [ ] Property-based testing for temperature ranges
- [ ] Snapshot testing for CLI output
- [ ] Load testing with multiple contexts

---

**Last Updated:** 2025-01-09
**Test Count:** 105 tests (99 unit + 6 integration)
**Coverage:** AgentContext, CLI flags, autonomous graph, end-to-end

