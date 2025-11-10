#!/bin/bash
# Router functionality test script
# Tests intelligent routing between autonomous and deterministic modes

set -e

echo "🧪 Router Test Suite"
echo "===================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_prompt() {
    local expected_mode=$1
    local prompt=$2
    local description=$3

    echo -e "${BLUE}Test:${NC} $description"
    echo -e "Prompt: \"$prompt\""
    echo -e "Expected: ${YELLOW}$expected_mode${NC}"
    echo ""

    # Run in no-stream mode for cleaner output
    echo "$ panos-agent run -p \"$prompt\" --no-stream"
    echo "---"

    # Uncomment to actually run (requires .env setup)
    # panos-agent run -p "$prompt" --no-stream

    echo ""
    echo "---"
    echo ""
}

echo "📋 Category 1: Should Route to DETERMINISTIC"
echo "============================================"
echo ""

test_prompt "deterministic" \
    "Set up web server" \
    "Exact workflow name match"

test_prompt "deterministic" \
    "Configure HTTP and HTTPS services" \
    "Semantic match to web_server_setup"

test_prompt "deterministic" \
    "Set up network segmentation" \
    "Exact workflow match"

test_prompt "deterministic" \
    "Create address for 10.1.1.50 named web-server" \
    "Simple address with parameters"

test_prompt "deterministic" \
    "Deploy complete security policy with commit" \
    "Complete security workflow"

echo ""
echo "🔍 Category 2: Should Route to AUTONOMOUS"
echo "=========================================="
echo ""

test_prompt "autonomous" \
    "Show me all address objects" \
    "Forced autonomous (show me keyword)"

test_prompt "autonomous" \
    "Investigate firewall configuration" \
    "Forced autonomous (investigate keyword)"

test_prompt "autonomous" \
    "Find all policies using web-servers group" \
    "Forced autonomous (find keyword)"

test_prompt "autonomous" \
    "Delete all unused address objects" \
    "Ad-hoc operation (no workflow match)"

test_prompt "autonomous" \
    "List all NAT policies in DMZ zone" \
    "Specific query (no workflow match)"

test_prompt "autonomous" \
    "Explore the current configuration" \
    "Forced autonomous (explore keyword)"

echo ""
echo "⚠️  Category 3: Edge Cases / Ambiguous"
echo "======================================"
echo ""

test_prompt "autonomous" \
    "Help me with firewall setup" \
    "Vague request (low confidence)"

test_prompt "autonomous" \
    "Create network infrastructure" \
    "Ambiguous (multiple possible workflows)"

echo ""
echo "🔧 Category 4: Parameter Extraction"
echo "===================================="
echo ""

test_prompt "deterministic" \
    "Create address for 192.168.1.100 named database-server" \
    "Clear parameters for simple_address"

test_prompt "deterministic" \
    "Set up web server at 10.50.1.25 with HTTP on 8080" \
    "Parameters for web_server_setup"

test_prompt "autonomous" \
    "Create an address" \
    "Missing required parameters (fallback to autonomous)"

echo ""
echo "🛠️  Category 5: Workflow Discovery"
echo "=================================="
echo ""

test_prompt "autonomous" \
    "What workflows are available?" \
    "Discovery tool usage"

test_prompt "autonomous" \
    "What workflows can help with web servers?" \
    "Search workflows by intent"

echo ""
echo "✅ Test suite complete!"
echo ""
echo "To run with actual execution:"
echo "  1. Ensure .env is configured with PANOS credentials"
echo "  2. Uncomment the panos-agent run lines in this script"
echo "  3. Run: ./scripts/test_router.sh"
