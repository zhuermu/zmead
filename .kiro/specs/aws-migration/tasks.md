# AWS Integration Implementation Plan

## Overview

This implementation plan converts the AWS integration design into actionable coding tasks. The plan focuses on adding AWS services support while maintaining existing Google services, implementing multi-provider AI model selection, and migrating to Strands Agents framework.

## Implementation Tasks

- [x] 1. Set up AWS infrastructure and dependencies
  - Install and configure AWS SDK dependencies (boto3, botocore)
  - Set up AWS credentials and configuration management
  - Create AWS service client factories with proper error handling
  - _Requirements: 5.1, 5.2, 5.3, 6.1, 6.2_

- [ ]* 1.1 Write property test for AWS authentication
  - **Property 13: AWS Service Authentication**
  - **Validates: Requirements 5.1, 5.2, 5.3**

- [x] 2. Implement S3 storage backend
  - Create S3Storage class implementing the same interface as GCSStorage
  - Implement presigned URL generation for S3 uploads and downloads
  - Add CloudFront CDN URL generation and configuration
  - Update storage factory to support both GCS and S3 backends
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ]* 2.1 Write property test for S3 storage round trip
  - **Property 1: S3 Storage Round Trip**
  - **Validates: Requirements 1.1, 1.2**

- [ ]* 2.2 Write property test for presigned URL validity
  - **Property 2: Presigned URL Validity**
  - **Validates: Requirements 1.3**

- [ ]* 2.3 Write property test for CDN URL format
  - **Property 3: CDN URL Format**
  - **Validates: Requirements 1.4**

- [ ]* 2.4 Write property test for storage interface compatibility
  - **Property 4: Storage Interface Compatibility**
  - **Validates: Requirements 1.5**

- [x] 3. Create multi-provider AI model architecture
  - Design and implement ModelProvider abstract base class
  - Create GeminiProvider class wrapping existing Gemini functionality
  - Implement BedrockProvider class for AWS Bedrock models
  - Create SageMakerProvider class for custom model endpoints
  - Add model provider factory with configuration-based selection
  - _Requirements: 2.1, 2.2, 2.3, 2.5_

- [ ]* 3.1 Write property test for multi-provider model integration
  - **Property 5: Multi-Provider Model Integration**
  - **Validates: Requirements 2.1, 2.2, 2.3**

- [ ]* 3.2 Write property test for model selection flexibility
  - **Property 7: Model Selection Flexibility**
  - **Validates: Requirements 2.5**

- [x] 4. Implement AWS Bedrock integration
  - Create BedrockClient class using Strands Agents BedrockModel
  - Implement support for Claude 4.5 Sonnet, Qwen3, and Nova 2 Lite models
  - Add proper error handling and retry logic for Bedrock API calls
  - Implement streaming and non-streaming response handling
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ]* 4.1 Write property test for model error handling
  - **Property 6: Model Error Handling**
  - **Validates: Requirements 2.4**

- [ ]* 4.2 Write property test for AWS error handling
  - **Property 14: AWS Error Handling**
  - **Validates: Requirements 5.4, 7.2**

- [x] 5. Deploy custom models on AWS SageMaker
  - Create SageMaker endpoints for Qwen-Image model deployment
  - Create SageMaker endpoints for Wan2.2 video model deployment
  - Implement SageMakerClient for custom model inference
  - Add proper timeout and retry logic for SageMaker endpoints
  - _Requirements: 3.1, 3.2, 3.4, 3.5_

- [ ]* 5.1 Write property test for custom model generation
  - **Property 8: Custom Model Generation**
  - **Validates: Requirements 3.1, 3.2**

- [ ]* 5.2 Write property test for custom model reliability
  - **Property 9: Custom Model Reliability**
  - **Validates: Requirements 3.4, 3.5**

- [x] 6. Migrate to Strands Agents framework
  - Replace LangGraph ReActAgent with Strands Agent implementation
  - Implement "Agents as Tools" pattern for capability modules
  - Create specialized tool agents for each domain (ad creative, market insights, etc.)
  - Update conversation state management using Strands Agent patterns
  - Migrate tool execution to use Strands Agent mechanisms
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ]* 6.1 Write property test for Strands agent execution
  - **Property 10: Strands Agent Execution**
  - **Validates: Requirements 4.1, 4.2**

- [ ]* 6.2 Write property test for agent tool execution
  - **Property 11: Agent Tool Execution**
  - **Validates: Requirements 4.3, 4.4**

- [ ]* 6.3 Write property test for agent configuration compliance
  - **Property 12: Agent Configuration Compliance**
  - **Validates: Requirements 4.5**

- [x] 7. Update backend configuration and dependencies
  - Update pyproject.toml and requirements.txt with AWS dependencies
  - Remove Google Cloud dependencies where replaced by AWS
  - Add Strands Agents dependencies and remove LangGraph
  - Update environment configuration for AWS services
  - Create configuration validation for AWS settings
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.3_

- [ ]* 7.1 Write property test for AWS configuration validation
  - **Property 15: AWS Configuration Validation**
  - **Validates: Requirements 5.5, 7.3, 7.4, 7.5**

- [x] 8. Implement user model selection interface
  - Add model preference fields to user profile database schema
  - Create API endpoints for getting and updating user model preferences
  - Implement frontend UI for model selection (dropdown/radio buttons)
  - Add model provider routing based on user preferences
  - Update conversation flow to use selected model provider
  - _Requirements: 2.5, 7.4_

- [x] 9. Update MCP tools and service integration
  - Update existing MCP tools to work with multi-provider architecture
  - Ensure credit deduction works with all model providers
  - Update conversation persistence to handle multiple model types
  - Test MCP tool compatibility with Strands Agents framework
  - _Requirements: 4.3, 7.4_

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Update deployment configuration
  - Update Docker configurations for AWS SDK dependencies
  - Add AWS credentials management to deployment scripts
  - Update docker-compose.yml with new environment variables
  - Create deployment guides for AWS service setup
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 12. Create integration and end-to-end tests
  - Create integration tests for S3 storage operations
  - Create integration tests for Bedrock model inference
  - Create integration tests for SageMaker custom model calls
  - Create end-to-end tests for complete user workflows with model selection
  - Add performance tests for AWS service response times
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 13. Update documentation and examples
  - Update README files with AWS setup instructions
  - Create example .env files with AWS configuration
  - Update API documentation for model selection endpoints
  - Create troubleshooting guide for AWS integration issues
  - Document model provider capabilities and limitations
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 14. Final checkpoint - Complete system validation
  - Ensure all tests pass, ask the user if questions arise.
  - Verify all AWS services are properly integrated
  - Validate user model selection works end-to-end
  - Confirm Strands Agents framework is fully operational