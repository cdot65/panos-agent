#!/bin/bash
# Test runner for Runtime Context features
# Usage: ./scripts/test_runtime_context.sh [options]

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Runtime Context Test Suite                          ║${NC}"
echo -e "${BLUE}║       Tests for model selection & temperature control     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Default options
VERBOSE=${VERBOSE:-false}
COVERAGE=${COVERAGE:-false}
INTEGRATION=${INTEGRATION:-true}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        --unit-only)
            INTEGRATION=false
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -v, --verbose     Verbose output with test names"
            echo "  -c, --coverage    Generate coverage report"
            echo "  --unit-only       Run only unit tests (skip integration)"
            echo "  -h, --help        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                        # Run all tests"
            echo "  $0 -v                     # Run with verbose output"
            echo "  $0 -c                     # Run with coverage report"
            echo "  $0 -v -c                  # Verbose + coverage"
            echo "  $0 --unit-only            # Unit tests only"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest not found${NC}"
    echo "Install with: pip install pytest pytest-cov"
    exit 1
fi

# Build test command
PYTEST_CMD="pytest"

# Add verbose flag if requested
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
else
    PYTEST_CMD="$PYTEST_CMD -q"
fi

# Test files to run
TEST_FILES=(
    "tests/unit/test_runtime_context.py"
    "tests/unit/test_cli_model_selection.py"
    "tests/unit/test_autonomous_nodes.py::TestCallAgentRuntimeContext"
)

# Add integration tests if not unit-only
if [ "$INTEGRATION" = true ]; then
    TEST_FILES+=("tests/integration/test_runtime_context_integration.py")
fi

# Add coverage if requested
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src.core.config --cov=src.cli.commands --cov=src.autonomous_graph"
    PYTEST_CMD="$PYTEST_CMD --cov-report=term-missing --cov-report=html"
fi

# Add color output
PYTEST_CMD="$PYTEST_CMD --color=yes"

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
echo ""

if [ "$COVERAGE" = true ]; then
    echo -e "${BLUE}Coverage enabled: HTML report will be generated in htmlcov/${NC}"
    echo ""
fi

# Execute pytest
$PYTEST_CMD "${TEST_FILES[@]}"
EXIT_CODE=$?

echo ""

# Summary
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ All Runtime Context tests passed!                      ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    
    if [ "$COVERAGE" = true ]; then
        echo ""
        echo -e "${BLUE}Coverage report: htmlcov/index.html${NC}"
        echo -e "${BLUE}Open with: open htmlcov/index.html (macOS)${NC}"
    fi
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ✗ Some tests failed                                       ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
fi

exit $EXIT_CODE

