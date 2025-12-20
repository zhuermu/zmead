#!/bin/bash

# AAE Platform Deployment Script
# This script automates the deployment process

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_MODE="${1:-development}"

echo -e "${BLUE}=== AAE Platform Deployment Script ===${NC}\n"

# Function to print section headers
print_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error messages
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to print warning messages
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    print_section "Checking Prerequisites"
    
    # Check Docker
    if command -v docker &> /dev/null; then
        print_success "Docker is installed"
    else
        print_error "Docker is not installed"
        echo "Please install Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check Docker Compose
    if command -v docker-compose &> /dev/null; then
        print_success "Docker Compose is installed"
    else
        print_error "Docker Compose is not installed"
        echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Check AWS CLI (optional)
    if command -v aws &> /dev/null; then
        print_success "AWS CLI is installed"
    else
        print_warning "AWS CLI is not installed (optional but recommended)"
    fi
}

# Function to check environment files
check_environment_files() {
    print_section "Checking Environment Files"
    
    local missing_files=()
    
    if [ ! -f "$PROJECT_ROOT/backend/.env" ]; then
        missing_files+=("backend/.env")
    else
        print_success "backend/.env exists"
    fi
    
    if [ ! -f "$PROJECT_ROOT/ai-orchestrator/.env" ]; then
        missing_files+=("ai-orchestrator/.env")
    else
        print_success "ai-orchestrator/.env exists"
    fi
    
    if [ ! -f "$PROJECT_ROOT/frontend/.env.local" ]; then
        missing_files+=("frontend/.env.local")
    else
        print_success "frontend/.env.local exists"
    fi
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        print_warning "Missing environment files:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        
        read -p "Create environment files from examples? (y/n): " create_env
        if [ "$create_env" = "y" ]; then
            for file in "${missing_files[@]}"; do
                if [ -f "$PROJECT_ROOT/${file}.example" ]; then
                    cp "$PROJECT_ROOT/${file}.example" "$PROJECT_ROOT/$file"
                    print_success "Created $file from example"
                fi
            done
            
            print_warning "Please edit the environment files with your configuration"
            read -p "Press Enter to continue after editing the files..."
        else
            print_error "Cannot proceed without environment files"
            exit 1
        fi
    fi
}

# Function to validate AWS credentials
validate_aws_credentials() {
    print_section "Validating AWS Credentials"
    
    # Source backend .env file
    if [ -f "$PROJECT_ROOT/backend/.env" ]; then
        export $(grep -v '^#' "$PROJECT_ROOT/backend/.env" | xargs)
    fi
    
    if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
        print_warning "AWS credentials not found in environment"
        read -p "Run AWS credentials setup script? (y/n): " run_setup
        if [ "$run_setup" = "y" ]; then
            bash "$SCRIPT_DIR/setup-aws-credentials.sh"
        else
            print_warning "Skipping AWS credentials validation"
        fi
    else
        if command -v aws &> /dev/null; then
            if aws sts get-caller-identity &> /dev/null; then
                print_success "AWS credentials are valid"
            else
                print_error "AWS credentials are invalid"
                exit 1
            fi
        else
            print_warning "AWS CLI not installed, skipping validation"
        fi
    fi
}

# Function to build Docker images
build_images() {
    print_section "Building Docker Images"
    
    cd "$PROJECT_ROOT"
    
    if [ "$DEPLOYMENT_MODE" = "production" ]; then
        docker-compose -f docker-compose.prod.yml build --no-cache
    else
        docker-compose build
    fi
    
    print_success "Docker images built successfully"
}

# Function to start services
start_services() {
    print_section "Starting Services"
    
    cd "$PROJECT_ROOT"
    
    if [ "$DEPLOYMENT_MODE" = "production" ]; then
        docker-compose -f docker-compose.prod.yml up -d
    else
        docker-compose up -d
    fi
    
    print_success "Services started successfully"
}

# Function to wait for services to be healthy
wait_for_services() {
    print_section "Waiting for Services to be Healthy"
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        attempt=$((attempt + 1))
        
        # Check backend health
        if curl -f http://localhost:8000/health &> /dev/null; then
            print_success "Backend is healthy"
            break
        else
            echo -n "."
            sleep 2
        fi
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "Backend failed to become healthy"
        echo "Check logs with: docker-compose logs backend"
        exit 1
    fi
    
    # Check AI orchestrator health
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        attempt=$((attempt + 1))
        
        if curl -f http://localhost:8001/health &> /dev/null; then
            print_success "AI Orchestrator is healthy"
            break
        else
            echo -n "."
            sleep 2
        fi
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "AI Orchestrator failed to become healthy"
        echo "Check logs with: docker-compose logs ai-orchestrator"
        exit 1
    fi
}

# Function to display service status
display_status() {
    print_section "Service Status"
    
    cd "$PROJECT_ROOT"
    
    if [ "$DEPLOYMENT_MODE" = "production" ]; then
        docker-compose -f docker-compose.prod.yml ps
    else
        docker-compose ps
    fi
}

# Function to display access information
display_access_info() {
    print_section "Access Information"
    
    echo -e "\n${GREEN}Deployment completed successfully!${NC}\n"
    echo "Services are now running:"
    echo ""
    echo "  Frontend:        http://localhost:3000"
    echo "  Backend API:     http://localhost:8000"
    echo "  API Docs:        http://localhost:8000/docs"
    echo "  AI Orchestrator: http://localhost:8001"
    echo ""
    echo "Useful commands:"
    echo "  View logs:       docker-compose logs -f"
    echo "  Stop services:   docker-compose down"
    echo "  Restart:         docker-compose restart"
    echo ""
    
    if [ "$DEPLOYMENT_MODE" = "production" ]; then
        echo "Production mode: Using docker-compose.prod.yml"
        echo "Remember to configure SSL certificates and domain settings"
    fi
}

# Function to show deployment mode selection
select_deployment_mode() {
    if [ -z "$1" ]; then
        echo -e "${YELLOW}Select deployment mode:${NC}"
        echo "1. Development (default)"
        echo "2. Production"
        echo ""
        read -p "Enter your choice (1-2): " mode_choice
        
        case $mode_choice in
            2)
                DEPLOYMENT_MODE="production"
                ;;
            *)
                DEPLOYMENT_MODE="development"
                ;;
        esac
    fi
    
    echo -e "\n${BLUE}Deployment mode: $DEPLOYMENT_MODE${NC}"
}

# Main execution
main() {
    select_deployment_mode "$1"
    check_prerequisites
    check_environment_files
    validate_aws_credentials
    
    read -p "Proceed with deployment? (y/n): " proceed
    if [ "$proceed" != "y" ]; then
        echo "Deployment cancelled"
        exit 0
    fi
    
    build_images
    start_services
    wait_for_services
    display_status
    display_access_info
}

# Run main function
main "$@"
