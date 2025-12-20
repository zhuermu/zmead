#!/bin/bash

# AAE Platform Services Test Script
# Tests the health and connectivity of all services

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== AAE Platform Services Test ===${NC}\n"

# Test Backend
echo -e "${YELLOW}Testing Backend (http://localhost:8000)...${NC}"
if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    BACKEND_RESPONSE=$(curl -s http://localhost:8000/health)
    echo -e "${GREEN}✓ Backend is healthy${NC}"
    echo "  Response: $BACKEND_RESPONSE"
else
    echo -e "${RED}✗ Backend is not responding${NC}"
    exit 1
fi

# Test AI Orchestrator
echo -e "\n${YELLOW}Testing AI Orchestrator (http://localhost:8001)...${NC}"
if curl -s -f http://localhost:8001/health > /dev/null 2>&1; then
    AI_RESPONSE=$(curl -s http://localhost:8001/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8001/health)
    echo -e "${GREEN}✓ AI Orchestrator is responding${NC}"
    echo "  Response: $AI_RESPONSE"
else
    echo -e "${RED}✗ AI Orchestrator is not responding${NC}"
    exit 1
fi

# Test Frontend
echo -e "\n${YELLOW}Testing Frontend (http://localhost:3000)...${NC}"
if curl -s -f http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is accessible${NC}"
    TITLE=$(curl -s http://localhost:3000 | grep -o '<title>[^<]*</title>' | sed 's/<[^>]*>//g')
    echo "  Page title: $TITLE"
else
    echo -e "${RED}✗ Frontend is not responding${NC}"
    exit 1
fi

# Test Backend API endpoints
echo -e "\n${YELLOW}Testing Backend API endpoints...${NC}"

# Test docs endpoint
if curl -s -f http://localhost:8000/docs > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API docs accessible at /docs${NC}"
else
    echo -e "${YELLOW}⚠ API docs not accessible${NC}"
fi

# Test AI Orchestrator endpoints
echo -e "\n${YELLOW}Testing AI Orchestrator endpoints...${NC}"

# Test docs endpoint
if curl -s -f http://localhost:8001/docs > /dev/null 2>&1; then
    echo -e "${GREEN}✓ AI Orchestrator docs accessible at /docs${NC}"
else
    echo -e "${YELLOW}⚠ AI Orchestrator docs not accessible${NC}"
fi

# Summary
echo -e "\n${BLUE}=== Test Summary ===${NC}"
echo -e "${GREEN}✓ All core services are running${NC}"
echo -e "\nService URLs:"
echo -e "  Backend API:     http://localhost:8000"
echo -e "  API Docs:        http://localhost:8000/docs"
echo -e "  AI Orchestrator: http://localhost:8001"
echo -e "  AI Docs:         http://localhost:8001/docs"
echo -e "  Frontend:        http://localhost:3000"

echo -e "\n${GREEN}All tests passed!${NC}"
