# AWS Integration Design Document

## Overview

This design document outlines the integration of AWS services into the AAE (Automated Ad Engine) platform to support multi-cloud AI model providers and enhanced infrastructure. The integration encompasses four major components:

1. **Storage Migration**: Transitioning from Google Cloud Storage (GCS) to Amazon S3 with CloudFront CDN
2. **Multi-Model AI Support**: Adding AWS Bedrock models (Claude 4.5 Sonnet, Qwen3, Nova 2 Lite) alongside existing Gemini models with user-configurable selection
3. **Agent Framework Migration**: Moving from LangGraph to Strands Agents framework
4. **Custom Model Deployment**: Deploying open-source Qwen-Image and Wan2.2 models on AWS SageMaker

The integration maintains existing Gemini model support while adding AWS Bedrock options, allowing users to choose their preferred AI models through the platform interface.

## Architecture

### Current Architecture (Google-based)
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │ AI Orchestrator │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   (LangGraph)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │ Google Cloud    │    │ Google Gemini   │
                    │ Storage (GCS)   │    │ Models          │
                    └─────────────────┘    └─────────────────┘
```

### Target Architecture (Multi-Cloud)
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │ AI Orchestrator │
│ (Model Selector)│◄──►│   (FastAPI)     │◄──►│ (Strands Agent) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │ Amazon S3 +     │    │ Multi-Model     │
                    │ CloudFront CDN  │    │ AI Provider     │
                    └─────────────────┘    └─────────────────┘
                                                      │
                                          ┌───────────┼───────────┐
                                          ▼           ▼           ▼
                                   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
                                   │   Gemini    │ │AWS Bedrock  │ │AWS SageMaker│
                                   │  (Existing) │ │(Claude/Qwen)│ │(Custom Gen) │
                                   └─────────────┘ └─────────────┘ └─────────────┘
```

## Components and Interfaces

### 1. Storage Layer Migration

#### Current Implementation (GCS)
- **File**: `backend/app/core/storage.py`
- **Class**: `GCSStorage`
- **Dependencies**: `google-cloud-storage`, `google-oauth2`

#### Target Implementation (S3)
- **File**: `backend/app/core/storage.py` (updated)
- **Class**: `S3Storage`
- **Dependencies**: `boto3`, `botocore`

#### Interface Compatibility
The storage interface will maintain the same method signatures:
```python
class StorageInterface:
    def generate_presigned_upload_url(self, key: str, content_type: str, expires_in: int) -> dict
    def generate_presigned_download_url(self, key: str, expires_in: int) -> str
    def upload_file(self, key: str, data: bytes, content_type: str) -> str
    def delete_file(self, key: str) -> None
    def get_cdn_url(self, key: str) -> str
    def file_exists(self, key: str) -> bool
    def list_files(self, prefix: str, max_results: int) -> list[dict]
```

### 2. AI Model Layer Enhancement

#### Current Implementation (Gemini Only)
- **File**: `ai-orchestrator/app/services/gemini_client.py`
- **Class**: `GeminiClient`
- **Dependencies**: `google-genai`, `langchain-google-genai`

#### Enhanced Implementation (Multi-Provider)
- **File**: `ai-orchestrator/app/services/model_provider.py` (new)
- **Class**: `ModelProvider` (abstract base)
- **Implementations**: `GeminiProvider`, `BedrockProvider`, `SageMakerProvider`
- **Dependencies**: `google-genai`, `boto3`, `strands-agents`

#### Model Configuration
```python
# Conversational AI Models (User Selectable)
CONVERSATIONAL_MODELS = {
    "gemini": {
        "gemini-2.5-flash": "gemini-2.5-flash",
        "gemini-2.5-pro": "gemini-2.5-pro"
    },
    "bedrock": {
        "claude-4.5-sonnet": "anthropic.claude-sonnet-4-20250514-v1:0",
        "qwen3": "qwen.qwen3-235b-a22b-2507-v1:0",
        "nova-2-lite": "us.amazon.nova-lite-v1:0"
    }
}

# Creative Generation Models (Fixed)
GENERATION_MODELS = {
    "image": {
        "qwen-image": "sagemaker-endpoint-qwen-image"
    },
    "video": {
        "wan2.2": "sagemaker-endpoint-wan-video"
    }
}
```

#### User Model Selection Interface
```python
class UserModelPreference(BaseModel):
    """User's AI model preferences"""
    conversational_provider: Literal["gemini", "bedrock"] = "gemini"
    conversational_model: str = "gemini-2.5-flash"
    # Image and video models are fixed to Qwen-Image and Wan2.2
```

### 3. Agent Framework Migration

#### Current Implementation (LangGraph)
- **File**: `ai-orchestrator/app/core/react_agent.py`
- **Class**: `ReActAgent`
- **Dependencies**: `langgraph`, `langchain-core`

#### Target Implementation (Strands Agents)
- **File**: `ai-orchestrator/app/core/strands_agent.py`
- **Class**: `StrandsReActAgent`
- **Dependencies**: `strands-agents`

#### Agent Architecture Pattern
Following the "Agents as Tools" pattern from Strands Agents:
```python
# Orchestrator Agent with Specialized Tool Agents
@tool
def ad_creative_agent(query: str) -> str:
    """Handle ad creative generation requests"""
    
@tool  
def market_insights_agent(query: str) -> str:
    """Handle market analysis requests"""

@tool
def campaign_automation_agent(query: str) -> str:
    """Handle campaign management requests"""

# Main orchestrator
orchestrator = Agent(
    system_prompt=ORCHESTRATOR_PROMPT,
    tools=[ad_creative_agent, market_insights_agent, campaign_automation_agent]
)
```

## Data Models

### 1. AWS Configuration Models

```python
from pydantic import BaseModel, Field
from typing import Optional

class AWSConfig(BaseModel):
    """AWS service configuration"""
    region: str = Field(default="us-west-2")
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    session_token: Optional[str] = None
    
class S3Config(AWSConfig):
    """S3-specific configuration"""
    bucket_creatives: str = "aae-creatives"
    bucket_landing_pages: str = "aae-landing-pages"
    bucket_exports: str = "aae-exports"
    bucket_uploads: str = "aae-user-uploads"
    cloudfront_domain: Optional[str] = None

class BedrockConfig(AWSConfig):
    """Bedrock-specific configuration"""
    default_model: str = "anthropic.claude-sonnet-4-20250514-v1:0"
    temperature: float = 0.7
    max_tokens: int = 4096
    
class SageMakerConfig(AWSConfig):
    """SageMaker-specific configuration"""
    qwen_image_endpoint: str
    wan_video_endpoint: str
```

### 2. Migration State Models

```python
class MigrationState(BaseModel):
    """Track migration progress"""
    storage_migrated: bool = False
    ai_models_migrated: bool = False
    agent_framework_migrated: bool = False
    custom_models_deployed: bool = False
    
class ServiceHealth(BaseModel):
    """AWS service health status"""
    s3_healthy: bool = False
    bedrock_healthy: bool = False
    sagemaker_healthy: bool = False
    last_check: datetime
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After reviewing all properties identified in the prework analysis, I've identified several areas where properties can be consolidated:

- **Storage Properties (1.1-1.5)**: These can be combined into comprehensive storage operation properties
- **Model Properties (2.1-2.5)**: These can be consolidated into model integration and error handling properties  
- **Custom Model Properties (3.1, 3.2, 3.4, 3.5)**: These can be combined into custom model deployment and invocation properties
- **Agent Framework Properties (4.1-4.5)**: These can be consolidated into agent execution and configuration properties
- **AWS Integration Properties (5.1-5.5, 7.1-7.5)**: These overlap significantly and can be combined into AWS service integration properties

The consolidated properties provide comprehensive validation while eliminating redundancy.

### Storage Migration Properties

**Property 1: S3 Storage Round Trip**
*For any* file content and metadata, uploading to S3 then downloading should return identical content with correct metadata
**Validates: Requirements 1.1, 1.2**

**Property 2: Presigned URL Validity**
*For any* file key and expiration time, generated presigned URLs should be valid, accessible, and expire at the specified time
**Validates: Requirements 1.3**

**Property 3: CDN URL Format**
*For any* stored file, CDN URLs should follow CloudFront format and serve the correct content
**Validates: Requirements 1.4**

**Property 4: Storage Interface Compatibility**
*For any* storage operation, the S3 implementation should maintain the same API interface as the GCS implementation
**Validates: Requirements 1.5**

### Multi-Model AI Integration Properties

**Property 5: Multi-Provider Model Integration**
*For any* conversational AI request and user model preference, the system should successfully invoke the selected model provider (Gemini or Bedrock) and return valid responses
**Validates: Requirements 2.1, 2.2, 2.3**

**Property 6: Model Error Handling**
*For any* model error scenario, the system should implement appropriate retry logic and provide clear error messages
**Validates: Requirements 2.4**

**Property 7: Model Selection Flexibility**
*For any* user model preference (Gemini, Claude, Qwen3, Nova), the system should correctly route requests to the specified model and provider
**Validates: Requirements 2.5**

### Custom Model Deployment Properties

**Property 8: Custom Model Generation**
*For any* valid generation request, custom models (Qwen-Image, Wan2.2) should produce valid outputs of the correct type
**Validates: Requirements 3.1, 3.2**

**Property 9: Custom Model Reliability**
*For any* custom model invocation, the system should handle timeouts and failures with appropriate retry logic
**Validates: Requirements 3.4, 3.5**

### Agent Framework Migration Properties

**Property 10: Strands Agent Execution**
*For any* user message, the Strands Agent framework should process requests and maintain conversation state correctly
**Validates: Requirements 4.1, 4.2**

**Property 11: Agent Tool Execution**
*For any* tool call, the Strands Agent should execute tools correctly and handle multi-step workflows
**Validates: Requirements 4.3, 4.4**

**Property 12: Agent Configuration Compliance**
*For any* agent configuration, the system should follow Strands Agent configuration patterns and formats
**Validates: Requirements 4.5**

### AWS Integration Properties

**Property 13: AWS Service Authentication**
*For any* AWS service call, the system should authenticate successfully using proper credentials and SDK configuration
**Validates: Requirements 5.1, 5.2, 5.3, 7.1**

**Property 14: AWS Error Handling**
*For any* AWS service error, the system should provide clear error messages and implement appropriate retry logic
**Validates: Requirements 5.4, 7.2**

**Property 15: AWS Configuration Validation**
*For any* environment configuration, the system should validate AWS settings and support both development and production configurations
**Validates: Requirements 5.5, 7.3, 7.4, 7.5**

## Error Handling

### 1. Storage Error Handling
- **S3 Connection Errors**: Implement exponential backoff retry with circuit breaker
- **Presigned URL Failures**: Generate alternative URLs with different expiration times
- **CDN Cache Issues**: Implement cache invalidation and fallback to direct S3 URLs

### 2. AI Model Error Handling
- **Bedrock Rate Limiting**: Implement token bucket algorithm for request throttling
- **Model Unavailability**: Automatic fallback between Claude and Qwen models
- **Custom Model Failures**: Graceful degradation with error reporting

### 3. Agent Framework Error Handling
- **State Persistence Failures**: Implement Redis failover and local state backup
- **Tool Execution Errors**: Retry mechanism with exponential backoff
- **Conversation Context Loss**: Automatic context reconstruction from message history

## Testing Strategy

### Unit Testing Framework
- **Framework**: pytest with pytest-asyncio for async operations
- **Coverage Target**: 90% code coverage for migration components
- **Mock Strategy**: Mock AWS services using moto library for S3, Bedrock simulation

### Property-Based Testing Framework
- **Library**: Hypothesis for Python property-based testing
- **Configuration**: Minimum 100 iterations per property test
- **Generators**: Custom generators for file content, model requests, and agent configurations

### Property-Based Test Implementation

Each correctness property will be implemented as a property-based test:

```python
from hypothesis import given, strategies as st
import pytest

@pytest.mark.asyncio
@given(
    file_content=st.binary(min_size=1, max_size=10*1024*1024),
    content_type=st.sampled_from(['image/jpeg', 'image/png', 'text/plain'])
)
async def test_s3_storage_round_trip(file_content, content_type):
    """
    **Feature: aws-migration, Property 1: S3 Storage Round Trip**
    For any file content and metadata, uploading to S3 then downloading 
    should return identical content with correct metadata
    """
    # Test implementation here
    pass

@pytest.mark.asyncio  
@given(
    user_message=st.text(min_size=1, max_size=1000),
    model_choice=st.sampled_from(['claude', 'qwen'])
)
async def test_bedrock_model_integration(user_message, model_choice):
    """
    **Feature: aws-migration, Property 5: Bedrock Model Integration**
    For any conversational AI request, the system should successfully 
    invoke Bedrock models and return valid responses
    """
    # Test implementation here
    pass
```

### Integration Testing
- **End-to-End Tests**: Complete user workflows through the migrated system
- **Service Integration**: Test interactions between S3, Bedrock, and SageMaker
- **Performance Testing**: Validate response times and throughput meet requirements

### Test Environment Setup
- **AWS LocalStack**: Local AWS service emulation for development testing
- **Test Data**: Synthetic data generation for comprehensive test coverage
- **CI/CD Integration**: Automated testing in GitHub Actions with AWS credentials