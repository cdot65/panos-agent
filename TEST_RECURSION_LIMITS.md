# Testing Recursion Limit Handling

This guide provides test commands and scenarios to verify the recursion limit handling implementation.

## Quick Tests

### 1. Test Default Recursion Limits

**Test autonomous mode default (25 steps):**
```bash
# Should work normally - most queries complete in <10 steps
uv run panos-agent run -p "List all address objects" -m autonomous --model haiku
```

**Test deterministic mode default (50 steps):**
```bash
# Run a workflow - should complete normally
uv run panos-agent run -p "simple_address" -m deterministic --model haiku
```

### 2. Test Custom Recursion Limit

**Set a very low limit to trigger graceful stopping:**
```bash
# Set limit to 10 steps - should stop gracefully before completion
uv run panos-agent run -p "web_server_setup" -m deterministic --recursion-limit 10 --model haiku
```

**Expected behavior:**
- Workflow should stop gracefully around step 8 (80% of 10)
- You should see a warning message about approaching recursion limit
- Partial results should be returned
- No crash or error

### 3. Test Progress Logging

**Run with verbose logging to see progress:**
```bash
# Enable debug logging to see progress messages
uv run panos-agent run -p "network_segmentation" -m deterministic --recursion-limit 20 --log-level DEBUG --model haiku
```

**Expected output:**
- Progress logged every 5 steps: `Workflow progress: 5/20 steps`
- Milestone at 50%: `Workflow at 50% of recursion limit (10/20)`
- Milestone at 80%: `Workflow at 80% of recursion limit (16/20) - approaching maximum`
- Warning when stopping: `Approaching recursion limit (16/20) - stopping workflow gracefully`

### 4. Test Graceful Degradation

**Create a test workflow that would exceed the limit:**
```bash
# Use a long workflow with a low limit
uv run panos-agent run -p "complete_security_workflow" -m deterministic --recursion-limit 15 --model haiku
```

**Expected behavior:**
- Workflow stops at ~12 steps (80% of 15)
- Message: `⚠️ Workflow partially completed: reached 12/15 steps`
- All completed steps are included in the result summary
- Final decision shows "partial" status

### 5. Test CLI Flag

**Verify the flag is accepted:**
```bash
# Check help text includes recursion-limit
uv run panos-agent run --help | grep recursion
```

**Test with different values:**
```bash
# Very low limit
uv run panos-agent run -p "simple_address" -m deterministic --recursion-limit 5 --model haiku

# High limit (should complete normally)
uv run panos-agent run -p "simple_address" -m deterministic --recursion-limit 100 --model haiku
```

## Advanced Testing

### Test with Long Workflow

To properly test recursion limits, you could create a workflow with 30+ steps. For now, test with existing workflows using low limits:

```bash
# Test with lowest practical limit
uv run panos-agent run -p "web_server_setup" -m deterministic --recursion-limit 8 --model haiku
```

### Monitor Logs

**Watch for specific log messages:**
```bash
# Run with DEBUG logging and grep for recursion messages
uv run panos-agent run -p "network_segmentation" -m deterministic --recursion-limit 20 --log-level DEBUG --model haiku 2>&1 | grep -i "recursion\|progress\|limit"
```

**Expected log messages:**
- `Workflow progress: 5/20 steps`
- `Workflow progress: 10/20 steps`
- `Workflow progress: 15/20 steps`
- `Workflow at 50% of recursion limit (10/20)`
- `Workflow at 80% of recursion limit (16/20) - approaching maximum`
- `Approaching recursion limit (16/20) - stopping workflow gracefully`

### Test Partial Results

**Verify partial results are returned:**
```bash
# Run workflow that will be cut short
uv run panos-agent run -p "multi_address_creation" -m deterministic --recursion-limit 12 --model haiku
```

**Check output for:**
- Summary shows completed steps (e.g., "Steps: 9/5")
- Final decision shows "partial"
- Reason mentions recursion limit
- All completed step outputs are present

## Verification Checklist

- [ ] Default limits work (25 autonomous, 50 deterministic)
- [ ] Custom `--recursion-limit` flag is accepted
- [ ] Workflows stop gracefully at 80% threshold
- [ ] Progress logging appears every 5 steps
- [ ] Milestone logging at 50% and 80%
- [ ] Partial completion message is clear
- [ ] No crashes or errors when limit is reached
- [ ] Completed steps are included in results
- [ ] Final decision shows "partial" status

## Troubleshooting

**If recursion limit doesn't trigger:**
- Check that workflows have enough steps (each workflow step = ~4 graph steps)
- Try a lower limit (e.g., `--recursion-limit 5`)
- Enable DEBUG logging to see step counts

**If you see errors:**
- Verify LangGraph version supports recursion_limit in config
- Check that config is being passed correctly to nodes
- Review logs for any configuration errors

## Example Test Session

```bash
# 1. Test normal operation
uv run panos-agent run -p "simple_address" -m deterministic --model haiku

# 2. Test with low limit (should stop gracefully)
uv run panos-agent run -p "web_server_setup" -m deterministic --recursion-limit 10 --model haiku

# 3. Test progress logging
uv run panos-agent run -p "network_segmentation" -m deterministic --recursion-limit 20 --log-level DEBUG --model haiku

# 4. Verify partial results
uv run panos-agent run -p "multi_address_creation" -m deterministic --recursion-limit 12 --model haiku
```

## Expected Output Examples

**Normal completion:**
```
📊 Workflow 'web_server_setup' Execution Summary

Steps: 5/5
✅ Successful: 5
```

**Partial completion (recursion limit):**
```
📊 Workflow 'web_server_setup' Execution Summary

Steps: 4/5
✅ Successful: 4

Final Decision: partial
Reason: Approaching recursion limit (16/20)
⚠️ Workflow partially completed: reached 16/20 steps. Workflow stopped gracefully to prevent recursion limit error.
```

