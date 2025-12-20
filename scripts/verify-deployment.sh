#!/bin/bash

# Deployment Configuration Verification Script
# This script verifies that all deployment files are properly configured

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== AAE Platform Deployment Configuration Verification ===${NC}\n"

# Function to check file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 (missing)"
        return 1
    fi
}

# Function to check directory exists
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        return 0
    else
        echo -e "${RED}✗${NC} $1/ (missing)"
        return 1
    fi
}

# Check deployment configuration files
echo -e "${BLUE}Checking deployment configuration files:${NC}"
check_file "docker-compose.yml"
check_file "docker-compose.prod.yml"
check_file ".env.production.example"

# Check Dockerfiles
echo -e "\n${BLUE}Checking Dockerfiles:${NC}"
check_file "backend/Dockerfile"
check_file "ai-orchestrator/Dockerfile"
check_file "frontend/Dockerfile"

# Check Nginx configuration
echo -e "\n${BLUE}Checking Nginx configuration:${NC}"
check_dir "nginx"
check_file "nginx/nginx.conf"

# Check deployment scripts
echo -e "\n${BLUE}Checking deployment scripts:${NC}"
check_dir "scripts"
check_file "scripts/setup-aws-credentials.sh"
check_file "scripts/deploy.sh"
check_file "scripts/verify-deployment.sh"

# Check if scripts are executable
echo -e "\n${BLUE}Checking script permissions:${NC}"
if [ -x "scripts/setup-aws-credentials.sh" ]; then
    echo -e "${GREEN}✓${NC} scripts/setup-aws-credentials.sh is executable"
else
    echo -e "${YELLOW}⚠${NC} scripts/setup-aws-credentials.sh is not executable"
    echo "  Run: chmod +x scripts/setup-aws-credentials.sh"
fi

if [ -x "scripts/deploy.sh" ]; then
    echo -e "${GREEN}✓${NC} scripts/deploy.sh is executable"
else
    echo -e "${YELLOW}⚠${NC} scripts/deploy.sh is not executable"
    echo "  Run: chmod +x scripts/deploy.sh"
fi

# Check documentation
echo -e "\n${BLUE}Checking deployment documentation:${NC}"
check_file "AWS_DEPLOYMENT_GUIDE.md"
check_file "DEPLOYMENT_README.md"
check_file "DEPLOYMENT_CHECKLIST.md"
check_file "TASK_11_DEPLOYMENT_CONFIGURATION_SUMMARY.md"

# Check environment example files
echo -e "\n${BLUE}Checking environment example files:${NC}"
check_file "backend/.env.example"
check_file "ai-orchestrator/.env"
check_file "frontend/.env.example"

# Validate docker-compose.yml syntax
echo -e "\n${BLUE}Validating Docker Compose syntax:${NC}"
if command -v docker-compose &> /dev/null; then
    if docker-compose config > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} docker-compose.yml syntax is valid"
    else
        echo -e "${RED}✗${NC} docker-compose.yml has syntax errors"
    fi
    
    if docker-compose -f docker-compose.prod.yml config > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} docker-compose.prod.yml syntax is valid"
    else
        echo -e "${RED}✗${NC} docker-compose.prod.yml has syntax errors"
    fi
else
    echo -e "${YELLOW}⚠${NC} Docker Compose not installed, skipping syntax validation"
fi

# Check for required environment variables in docker-compose files
echo -e "\n${BLUE}Checking required AWS environment variables in docker-compose.yml:${NC}"
required_vars=(
    "AWS_REGION"
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY"
    "S3_BUCKET_CREATIVES"
    "BEDROCK_DEFAULT_MODEL"
)

for var in "${required_vars[@]}"; do
    if grep -q "$var" docker-compose.yml; then
        echo -e "${GREEN}✓${NC} $var is configured"
    else
        echo -e "${RED}✗${NC} $var is missing"
    fi
done

# Summary
echo -e "\n${BLUE}=== Verification Summary ===${NC}"
echo -e "Deployment configuration files are in place."
echo -e "\nNext steps:"
echo -e "1. Review the deployment guides:"
echo -e "   - AWS_DEPLOYMENT_GUIDE.md (comprehensive AWS setup)"
echo -e "   - DEPLOYMENT_README.md (quick start)"
echo -e "   - DEPLOYMENT_CHECKLIST.md (deployment checklist)"
echo -e "2. Configure AWS credentials:"
echo -e "   ./scripts/setup-aws-credentials.sh"
echo -e "3. Deploy the platform:"
echo -e "   ./scripts/deploy.sh"
echo -e "\n${GREEN}Verification complete!${NC}"
