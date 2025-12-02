#!/bin/bash

# Quick Agent Test Runner
# 快速运行 Agent 能力测试

echo "🚀 Quick Agent Test"
echo "==================="
echo ""

# Check if services are running
echo "Checking services..."

if ! curl -s -f http://localhost:3000 > /dev/null; then
    echo "❌ Frontend not running on port 3000"
    echo "   Start with: cd frontend && npm run dev"
    exit 1
fi

if ! curl -s -f http://localhost:8000/health > /dev/null; then
    echo "❌ Backend not running on port 8000"
    echo "   Start with: cd backend && uvicorn app.main:app --reload --port 8000"
    exit 1
fi

if ! curl -s -f http://localhost:8001/health > /dev/null; then
    echo "❌ AI Orchestrator not running on port 8001"
    echo "   Start with: cd ai-orchestrator && uvicorn app.main:app --reload --port 8001"
    exit 1
fi

echo "✅ All services running"
echo ""

# Create screenshot directory
mkdir -p .playwright-mcp

# Run core tests (faster)
echo "Running core agent tests..."
echo ""

npx playwright test agent-core.spec.ts --headed

echo ""
echo "✅ Tests complete!"
echo "📸 Screenshots: .playwright-mcp/"
echo ""
echo "To run full test suite:"
echo "  npx playwright test agent-ui-capabilities.spec.ts"
