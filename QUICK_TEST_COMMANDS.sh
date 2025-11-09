#!/bin/bash
# Quick Test Commands - Copy & Paste These

echo "=== PAN-OS Agent Quick Tests ==="
echo ""

echo "1. Test Connection"
echo "uv run panos-agent test-connection"
echo ""

echo "2. List Workflows"
echo "uv run panos-agent list-workflows"
echo ""

echo "3. Autonomous Mode - List Objects (Safe)"
echo "uv run panos-agent run -p \"List all address objects\" --model haiku"
echo ""

echo "4. Autonomous Mode - Get Specific Object"
echo "uv run panos-agent run -p \"Get details for address object named demo-server\" --model haiku"
echo ""

echo "5. Deterministic Mode - Simple Workflow"
echo "uv run panos-agent run -p \"simple_address\" -m deterministic --model haiku"
echo ""

echo "6. Autonomous Mode - Complex Query"
echo "uv run panos-agent run -p \"Show me all service objects and their port numbers\" --model sonnet"
echo ""

echo "7. Test with Different Models"
echo "# Fast: uv run panos-agent run -p \"List objects\" --model haiku"
echo "# Smart: uv run panos-agent run -p \"List objects\" --model sonnet"
echo "# Best: uv run panos-agent run -p \"List objects\" --model opus"
echo ""

echo "8. Checkpoint Management"
echo "uv run panos-agent checkpoints list"
echo ""

echo "9. No-Stream Mode (for scripting)"
echo "uv run panos-agent run -p \"List address objects\" --model haiku --no-stream"
echo ""

echo "10. Conversation Context"
echo "uv run panos-agent run -p \"Create address test-A at 10.1.1.1\" -t test-001 --model haiku"
echo "uv run panos-agent run -p \"Now create test-B at 10.1.1.2\" -t test-001 --model haiku"
