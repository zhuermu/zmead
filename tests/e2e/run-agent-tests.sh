#!/bin/bash

# Agent Capability E2E Test Runner
# This script runs the Playwright tests for AI agent capabilities

set -e

echo "🤖 AAE Agent Capability Tests"
echo "=============================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if services are running
echo "📋 Checking prerequisites..."

check_service() {
    local url=$1
    local name=$2
    
    if curl -s -f -o /dev/null "$url"; then
        echo -e "${GREEN}✓${NC} $name is running"
        return 0
    else
        echo -e "${RED}✗${NC} $name is not accessible at $url"
        return 1
    fi
}

# Check all services
SERVICES_OK=true

if ! check_service "http://localhost:3000" "Frontend"; then
    SERVICES_OK=false
fi

if ! check_service "http://localhost:8000/health" "Backend"; then
    SERVICES_OK=false
fi

if ! check_service "http://localhost:8001/health" "AI Orchestrator"; then
    SERVICES_OK=false
fi

if [ "$SERVICES_OK" = false ]; then
    echo ""
    echo -e "${RED}❌ Some services are not running!${NC}"
    echo ""
    echo "Please start all services before running tests:"
    echo "  Frontend:        cd frontend && npm run dev"
    echo "  Backend:         cd backend && uvicorn app.main:app --reload --port 8000"
    echo "  AI Orchestrator: cd ai-orchestrator && uvicorn app.main:app --reload --port 8001"
    echo ""
    exit 1
fi

echo ""
echo -e "${GREEN}✓ All services are running${NC}"
echo ""

# Create screenshot directory
mkdir -p .playwright-mcp

# Parse command line arguments
TEST_FILE=""
HEADED=false
DEBUG=false
UI=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --headed)
            HEADED=true
            shift
            ;;
        --debug)
            DEBUG=true
            shift
            ;;
        --ui)
            UI=true
            shift
            ;;
        --file)
            TEST_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Build test command
TEST_CMD="npx playwright test"

if [ -n "$TEST_FILE" ]; then
    TEST_CMD="$TEST_CMD $TEST_FILE"
fi

if [ "$HEADED" = true ]; then
    TEST_CMD="$TEST_CMD --headed"
fi

if [ "$DEBUG" = true ]; then
    TEST_CMD="$TEST_CMD --debug"
fi

if [ "$UI" = true ]; then
    TEST_CMD="$TEST_CMD --ui"
fi

# Run tests
echo "🧪 Running tests..."
echo "Command: $TEST_CMD"
echo ""

if $TEST_CMD; then
    echo ""
    echo -e "${GREEN}✅ Tests passed!${NC}"
    echo ""
    echo "📸 Screenshots saved to: .playwright-mcp/"
    echo "📊 View report: npx playwright show-report"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Tests failed!${NC}"
    echo ""
    echo "📸 Screenshots saved to: .playwright-mcp/"
    echo "📊 View report: npx playwright show-report"
    echo "🔍 Debug: npx playwright test --debug"
    exit 1
fi
