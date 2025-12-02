#!/bin/bash

# E2E Test Setup Script
# This script prepares the environment for running E2E tests

set -e

echo "🚀 Setting up E2E test environment..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if services are running
check_service() {
    local url=$1
    local name=$2
    
    echo -n "Checking $name... "
    if curl -s -f -o /dev/null "$url"; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

# Wait for service to be ready
wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "Waiting for $name to be ready... "
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f -o /dev/null "$url"; then
            echo -e "${GREEN}✓${NC}"
            return 0
        fi
        
        attempt=$((attempt + 1))
        sleep 2
    done
    
    echo -e "${RED}✗ Timeout${NC}"
    return 1
}

# Check Node.js
echo -n "Checking Node.js... "
if command -v node &> /dev/null; then
    NODE_VERSION=$(node -v)
    echo -e "${GREEN}✓ $NODE_VERSION${NC}"
else
    echo -e "${RED}✗ Node.js not found${NC}"
    exit 1
fi

# Check npm
echo -n "Checking npm... "
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm -v)
    echo -e "${GREEN}✓ $NPM_VERSION${NC}"
else
    echo -e "${RED}✗ npm not found${NC}"
    exit 1
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
npm install

# Install Playwright browsers
echo ""
echo "🌐 Installing Playwright browsers..."
npm run install

# Check if services are running
echo ""
echo "🔍 Checking services..."

FRONTEND_URL="${BASE_URL:-http://localhost:3000}"
BACKEND_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
AI_ORCHESTRATOR_URL="${AI_ORCHESTRATOR_URL:-http://localhost:8001}"

SERVICES_OK=true

if ! check_service "$FRONTEND_URL" "Frontend"; then
    SERVICES_OK=false
    echo -e "${YELLOW}  Frontend not running. Start with: cd frontend && npm run dev${NC}"
fi

if ! check_service "$BACKEND_URL/health" "Backend"; then
    SERVICES_OK=false
    echo -e "${YELLOW}  Backend not running. Start with: cd backend && uvicorn app.main:app --reload${NC}"
fi

if ! check_service "$AI_ORCHESTRATOR_URL/health" "AI Orchestrator"; then
    SERVICES_OK=false
    echo -e "${YELLOW}  AI Orchestrator not running. Start with: cd ai-orchestrator && uvicorn app.main:app --reload --port 8001${NC}"
fi

# Check database
echo -n "Checking MySQL... "
if command -v mysql &> /dev/null; then
    if mysql -h localhost -u root -e "SELECT 1" &> /dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠ Cannot connect${NC}"
        SERVICES_OK=false
    fi
else
    echo -e "${YELLOW}⚠ mysql command not found${NC}"
fi

# Check Redis
echo -n "Checking Redis... "
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠ Cannot connect${NC}"
        SERVICES_OK=false
    fi
else
    echo -e "${YELLOW}⚠ redis-cli command not found${NC}"
fi

echo ""

if [ "$SERVICES_OK" = false ]; then
    echo -e "${YELLOW}⚠ Some services are not running. Tests may fail.${NC}"
    echo ""
    echo "To start all services with Docker:"
    echo "  docker-compose up -d"
    echo ""
    echo "Or start services individually:"
    echo "  Terminal 1: cd frontend && npm run dev"
    echo "  Terminal 2: cd backend && uvicorn app.main:app --reload"
    echo "  Terminal 3: cd ai-orchestrator && uvicorn app.main:app --reload --port 8001"
    echo ""
    
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create test data (optional)
echo ""
echo "📊 Test data setup..."
echo -e "${YELLOW}Note: Ensure dev user and test data exist in the database${NC}"
echo ""

# Summary
echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "Run tests with:"
echo "  npm test                    # Run all tests"
echo "  npm run test:headed         # Run with browser visible"
echo "  npm run test:debug          # Run with debugger"
echo "  npm run test:ui             # Run with UI mode"
echo ""
echo "Run specific test categories:"
echo "  npm run test:creative       # Creative generation tests"
echo "  npm run test:campaign       # Campaign management tests"
echo "  npm run test:performance    # Performance analytics tests"
echo ""
