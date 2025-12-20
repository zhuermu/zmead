#!/bin/bash

# AWS Credentials Setup Script for AAE Platform
# This script helps configure AWS credentials for local development and deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== AAE Platform - AWS Credentials Setup ===${NC}\n"

# Function to check if AWS CLI is installed
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}Error: AWS CLI is not installed${NC}"
        echo "Please install AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        exit 1
    fi
    echo -e "${GREEN}✓ AWS CLI is installed${NC}"
}

# Function to prompt for AWS credentials
prompt_credentials() {
    echo -e "\n${YELLOW}Please enter your AWS credentials:${NC}"
    
    read -p "AWS Region (default: us-west-2): " AWS_REGION
    AWS_REGION=${AWS_REGION:-us-west-2}
    
    read -p "AWS Access Key ID: " AWS_ACCESS_KEY_ID
    read -sp "AWS Secret Access Key: " AWS_SECRET_ACCESS_KEY
    echo
    
    read -p "AWS Session Token (optional, press Enter to skip): " AWS_SESSION_TOKEN
}

# Function to validate credentials
validate_credentials() {
    echo -e "\n${YELLOW}Validating AWS credentials...${NC}"
    
    export AWS_ACCESS_KEY_ID
    export AWS_SECRET_ACCESS_KEY
    export AWS_DEFAULT_REGION=$AWS_REGION
    
    if [ -n "$AWS_SESSION_TOKEN" ]; then
        export AWS_SESSION_TOKEN
    fi
    
    if aws sts get-caller-identity &> /dev/null; then
        echo -e "${GREEN}✓ AWS credentials are valid${NC}"
        aws sts get-caller-identity
        return 0
    else
        echo -e "${RED}✗ AWS credentials are invalid${NC}"
        return 1
    fi
}

# Function to check S3 buckets
check_s3_buckets() {
    echo -e "\n${YELLOW}Checking S3 buckets...${NC}"
    
    BUCKETS=("aae-creatives" "aae-landing-pages" "aae-exports" "aae-user-uploads")
    
    for bucket in "${BUCKETS[@]}"; do
        if aws s3 ls "s3://$bucket" &> /dev/null; then
            echo -e "${GREEN}✓ Bucket $bucket exists${NC}"
        else
            echo -e "${YELLOW}⚠ Bucket $bucket does not exist${NC}"
            read -p "Create bucket $bucket? (y/n): " create_bucket
            if [ "$create_bucket" = "y" ]; then
                aws s3 mb "s3://$bucket" --region "$AWS_REGION"
                echo -e "${GREEN}✓ Created bucket $bucket${NC}"
            fi
        fi
    done
}

# Function to check Bedrock access
check_bedrock_access() {
    echo -e "\n${YELLOW}Checking AWS Bedrock access...${NC}"
    
    MODELS=(
        "anthropic.claude-sonnet-4-20250514-v1:0"
        "qwen.qwen3-235b-a22b-2507-v1:0"
        "us.amazon.nova-lite-v1:0"
    )
    
    for model in "${MODELS[@]}"; do
        if aws bedrock list-foundation-models --region "$AWS_REGION" --query "modelSummaries[?modelId=='$model'].modelId" --output text 2>/dev/null | grep -q "$model"; then
            echo -e "${GREEN}✓ Model $model is accessible${NC}"
        else
            echo -e "${YELLOW}⚠ Model $model may not be accessible${NC}"
            echo "  Please request access in AWS Console → Bedrock → Model access"
        fi
    done
}

# Function to update environment files
update_env_files() {
    echo -e "\n${YELLOW}Updating environment files...${NC}"
    
    # Backend .env
    if [ -f "backend/.env" ]; then
        echo -e "${YELLOW}Updating backend/.env${NC}"
        sed -i.bak "s|^AWS_REGION=.*|AWS_REGION=$AWS_REGION|" backend/.env
        sed -i.bak "s|^AWS_ACCESS_KEY_ID=.*|AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID|" backend/.env
        sed -i.bak "s|^AWS_SECRET_ACCESS_KEY=.*|AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY|" backend/.env
        if [ -n "$AWS_SESSION_TOKEN" ]; then
            sed -i.bak "s|^AWS_SESSION_TOKEN=.*|AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN|" backend/.env
        fi
        echo -e "${GREEN}✓ Updated backend/.env${NC}"
    else
        echo -e "${YELLOW}⚠ backend/.env not found, creating from example${NC}"
        cp backend/.env.example backend/.env
        echo "AWS_REGION=$AWS_REGION" >> backend/.env
        echo "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID" >> backend/.env
        echo "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" >> backend/.env
        if [ -n "$AWS_SESSION_TOKEN" ]; then
            echo "AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN" >> backend/.env
        fi
        echo -e "${GREEN}✓ Created backend/.env${NC}"
    fi
    
    # AI Orchestrator .env
    if [ -f "ai-orchestrator/.env" ]; then
        echo -e "${YELLOW}Updating ai-orchestrator/.env${NC}"
        sed -i.bak "s|^AWS_REGION=.*|AWS_REGION=$AWS_REGION|" ai-orchestrator/.env
        sed -i.bak "s|^AWS_ACCESS_KEY_ID=.*|AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID|" ai-orchestrator/.env
        sed -i.bak "s|^AWS_SECRET_ACCESS_KEY=.*|AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY|" ai-orchestrator/.env
        if [ -n "$AWS_SESSION_TOKEN" ]; then
            sed -i.bak "s|^AWS_SESSION_TOKEN=.*|AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN|" ai-orchestrator/.env
        fi
        echo -e "${GREEN}✓ Updated ai-orchestrator/.env${NC}"
    else
        echo -e "${YELLOW}⚠ ai-orchestrator/.env not found${NC}"
    fi
    
    # Clean up backup files
    rm -f backend/.env.bak ai-orchestrator/.env.bak
}

# Function to create AWS credentials file
create_aws_credentials_file() {
    echo -e "\n${YELLOW}Creating AWS credentials file...${NC}"
    
    mkdir -p ~/.aws
    
    cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = $AWS_ACCESS_KEY_ID
aws_secret_access_key = $AWS_SECRET_ACCESS_KEY
EOF

    if [ -n "$AWS_SESSION_TOKEN" ]; then
        echo "aws_session_token = $AWS_SESSION_TOKEN" >> ~/.aws/credentials
    fi
    
    cat > ~/.aws/config << EOF
[default]
region = $AWS_REGION
output = json
EOF
    
    chmod 600 ~/.aws/credentials
    chmod 600 ~/.aws/config
    
    echo -e "${GREEN}✓ Created AWS credentials file at ~/.aws/credentials${NC}"
}

# Function to test AWS services
test_aws_services() {
    echo -e "\n${YELLOW}Testing AWS services...${NC}"
    
    # Test S3
    if aws s3 ls &> /dev/null; then
        echo -e "${GREEN}✓ S3 access is working${NC}"
    else
        echo -e "${RED}✗ S3 access failed${NC}"
    fi
    
    # Test Bedrock
    if aws bedrock list-foundation-models --region "$AWS_REGION" &> /dev/null; then
        echo -e "${GREEN}✓ Bedrock access is working${NC}"
    else
        echo -e "${RED}✗ Bedrock access failed${NC}"
    fi
    
    # Test SageMaker
    if aws sagemaker list-endpoints --region "$AWS_REGION" &> /dev/null; then
        echo -e "${GREEN}✓ SageMaker access is working${NC}"
    else
        echo -e "${RED}✗ SageMaker access failed${NC}"
    fi
}

# Main execution
main() {
    check_aws_cli
    
    echo -e "\n${YELLOW}Choose an option:${NC}"
    echo "1. Configure new AWS credentials"
    echo "2. Use existing AWS credentials from ~/.aws/credentials"
    echo "3. Exit"
    
    read -p "Enter your choice (1-3): " choice
    
    case $choice in
        1)
            prompt_credentials
            if validate_credentials; then
                create_aws_credentials_file
                update_env_files
                check_s3_buckets
                check_bedrock_access
                test_aws_services
                
                echo -e "\n${GREEN}=== Setup Complete ===${NC}"
                echo -e "AWS credentials have been configured successfully!"
                echo -e "\nNext steps:"
                echo -e "1. Review and update other environment variables in backend/.env and ai-orchestrator/.env"
                echo -e "2. Run 'docker-compose up -d' to start the services"
                echo -e "3. Check the deployment guide: AWS_DEPLOYMENT_GUIDE.md"
            else
                echo -e "\n${RED}Setup failed. Please check your credentials and try again.${NC}"
                exit 1
            fi
            ;;
        2)
            if [ -f ~/.aws/credentials ]; then
                echo -e "${GREEN}Using existing AWS credentials${NC}"
                AWS_REGION=$(aws configure get region)
                AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
                AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)
                AWS_SESSION_TOKEN=$(aws configure get aws_session_token)
                
                if validate_credentials; then
                    update_env_files
                    check_s3_buckets
                    check_bedrock_access
                    test_aws_services
                    
                    echo -e "\n${GREEN}=== Setup Complete ===${NC}"
                else
                    echo -e "\n${RED}Existing credentials are invalid. Please run option 1 to configure new credentials.${NC}"
                    exit 1
                fi
            else
                echo -e "${RED}No existing AWS credentials found at ~/.aws/credentials${NC}"
                echo "Please run option 1 to configure new credentials."
                exit 1
            fi
            ;;
        3)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            exit 1
            ;;
    esac
}

# Run main function
main
