# Implementation Plan - AI Orchestrator

## Overview

This implementation plan breaks down the AI Orchestrator development into incremental, testable tasks. Phase 1 focuses on building the core framework with stub modules that return mock data but exercise the full integration flow.

**Current Status**: Web Platform has implemented:
- ✅ MCP Server with tool registry
- ✅ Credit management tools (check_credit, deduct_credit, refund_credit)
- ✅ WebSocket handler with AI Orchestrator forwarding
- ✅ Service-to-service authentication configured
- ❌ Conversation persistence (models and MCP tools not yet implemented)
- ❌ AI Orchestrator service (not yet created)

**Task Summary**:
- Prerequisites: Complete missing Web Platform features (3 tasks)
- Project setup and infrastructure (5 tasks)
- MCP client implementation (6 tasks)
- LangGraph state machine (10 tasks)
- FastAPI application (7 tasks)
- Error handling (3 tasks)
- Testing (8 optional tasks)
- Integration and deployment (4 tasks)
- Checkpoint verification (3 tasks)

---

- [ ] 0. Prerequisites - Complete Missing Web Platform Features
- [ ] 0.1 Create conversation data models in Web Platform
  - Create `backend/app/models/conversation.py` with Conversation model
  - Create `backend/app/models/message.py` with Message model
  - Add relationships: User → Conversations → Messages
  - Create Alembic migration for new tables
  - _Requirements: 需求 5.1 (conversation persistence)_

- [ ] 0.2 Implement conversation MCP tools in Web Platform
  - Create `backend/app/mcp/tools/conversation.py`
  - Implement `save_conversation` tool (stores messages to database)
  - Implement `get_conversation_history` tool (retrieves conversation by session_id)
  - Register tools in MCP registry
  - _Requirements: 需求 5.1, 1.5_

- [ ] 0.3 Generate service token for AI Orchestrator
  - Add `WEB_PLATFORM_SERVICE_TOKEN` to backend/.env
  - Document token generation process in README
  - Update WebSocket handler to validate service token
  - _Requirements: Security, service-to-service auth_

- [ ] 1. Project Setup and Infrastructure
- [ ] 1.1 Create project structure
  - Create `ai-orchestrator/` directory at repository root
  - Create `ai-orchestrator/pyproject.toml` with project metadata
  - Configure dependencies: FastAPI>=0.115.0, LangGraph>=0.2.0, langchain-google-genai>=2.0.0, httpx>=0.27.0, redis>=5.0.0, pydantic>=2.9.0, structlog>=24.0.0
  - Create directory structure: `app/`, `app/core/`, `app/nodes/`, `app/services/`, `app/prompts/`, `app/api/`, `tests/`
  - Create `ai-orchestrator/requirements.txt` from pyproject.toml
  - _Requirements: Infrastructure setup_

- [ ] 1.2 Configure development environment
  - Create `ai-orchestrator/.env.example` with all required variables
  - Create `ai-orchestrator/.gitignore` for Python (venv/, __pycache__/, .env, *.pyc)
  - Create `ai-orchestrator/README.md` with project overview
  - Add development setup instructions
  - _Requirements: Infrastructure setup_

- [ ] 1.3 Implement configuration management
  - Create `ai-orchestrator/app/core/config.py` with Pydantic Settings
  - Define settings: GEMINI_API_KEY, WEB_PLATFORM_URL, WEB_PLATFORM_SERVICE_TOKEN, REDIS_URL
  - Add computed fields for derived values
  - Add validation for required settings (raise error if missing)
  - Support loading from .env file
  - _Requirements: Infrastructure setup_

- [ ] 1.4 Set up logging infrastructure
  - Create `ai-orchestrator/app/core/logging.py`
  - Configure structlog with JSON formatter for production
  - Configure human-readable formatter for development
  - Set up log levels from environment variables (default: INFO)
  - Add request ID to all logs for tracing
  - _Requirements: 需求 12, 15_

- [ ] 1.5 Set up Redis client
  - Create `ai-orchestrator/app/core/redis_client.py`
  - Implement connection pooling with redis-py
  - Add `get_redis()` async function for dependency injection
  - Add health check method: `ping()`
  - Handle connection failures gracefully with retries
  - Add connection timeout configuration
  - _Requirements: State persistence_

- [ ] 2. MCP Client Implementation
- [ ] 2.1 Create MCP client base class
  - Implement `ai-orchestrator/app/services/mcp_client.py`
  - Add HTTP client using httpx with connection pooling
  - Implement exponential backoff retry logic (1s, 2s, 4s, max 3 retries)
  - Add request/response logging with structlog
  - Add timeout handling (default 30s)
  - _Requirements: 需求 11.1, 11.4_

- [ ] 2.2 Implement MCP tool call methods
  - Add `call_tool(tool_name, parameters)` method
  - Format requests according to Web Platform's `/api/v1/mcp/execute` endpoint
  - Add service token authentication in Authorization header
  - Parse MCPResponse and extract data or error
  - Create custom exceptions: `MCPConnectionError`, `MCPToolError`, `InsufficientCreditsError`
  - Map MCP error codes to user-friendly messages
  - _Requirements: 需求 11.2, 11.3, 12.1_

- [ ] 2.3 Implement credit management wrappers
  - Add `check_credit(user_id, estimated_credits, operation_type)` wrapper
  - Add `deduct_credit(user_id, credits, operation_type, operation_id)` wrapper
  - Add `refund_credit(user_id, credits, operation_id)` wrapper
  - Handle insufficient credit errors (code 6011) with clear user messages
  - Add logging for all credit operations
  - _Requirements: Credit integration, 需求 6-10_

- [ ] 2.4 Implement conversation persistence wrappers
  - Add `save_conversation(user_id, session_id, messages)` wrapper
  - Add `get_conversation_history(user_id, session_id, limit)` wrapper
  - Handle persistence failures gracefully (log error but don't fail request)
  - Add retry logic for transient failures
  - _Requirements: 需求 5.1, 1.5_

- [ ] 2.5 Create Gemini client wrapper
  - Implement `ai-orchestrator/app/services/gemini_client.py`
  - Use `langchain-google-genai` package for Gemini integration
  - Add method for chat completion (Gemini 2.5 Pro)
  - Add method for structured output with Pydantic schemas
  - Add method for fast completion (Gemini 2.5 Flash)
  - Handle API errors, rate limiting, and quota exceeded
  - Add retry logic with exponential backoff
  - _Requirements: 需求 2, 14.3_

- [ ]* 2.6 Write unit tests for MCP client
  - Test connection retry logic with mock failures
  - Test error handling and exception mapping
  - Test timeout behavior
  - Mock MCP server responses using pytest fixtures
  - Test credit check/deduct/refund flows
  - _Requirements: Testing_

- [ ] 3. LangGraph State Machine
- [ ] 3.1 Define agent state schema
  - Create `ai-orchestrator/app/core/state.py` with `AgentState` TypedDict
  - Define fields: messages (with operator.add), user_id, session_id, current_intent
  - Add fields: extracted_params, pending_actions, completed_results
  - Add fields: requires_confirmation, user_confirmed, error, retry_count
  - Add comprehensive docstrings for each field
  - _Requirements: 需求 4, 5_

- [ ] 3.2 Create prompt templates
  - Create `ai-orchestrator/app/prompts/` directory
  - Create `intent_recognition.py` with detailed intent recognition prompt
  - Include examples for each intent type (creative, reporting, market, landing, campaign)
  - Create `response_generation.py` with response formatting prompt
  - Add system prompts for friendly, helpful tone
  - _Requirements: 需求 2, 14.3_

- [ ] 3.3 Implement intent recognition node
  - Create `ai-orchestrator/app/nodes/router.py` with `router_node` function
  - Define `IntentSchema` Pydantic model with structured output
  - Use Gemini 2.5 Pro with `with_structured_output(IntentSchema)`
  - Extract intent, confidence, parameters, actions, estimated_cost
  - Handle low confidence scores (< 0.6) by asking clarifying questions
  - Log all intent recognition results
  - _Requirements: 需求 2.1-2.5, 14.1_

- [ ] 3.4 Implement stub functional module nodes
  - Create `ai-orchestrator/app/nodes/creative_stub.py`
  - Create `ai-orchestrator/app/nodes/reporting_stub.py`
  - Create `ai-orchestrator/app/nodes/market_intel_stub.py`
  - Create `ai-orchestrator/app/nodes/landing_page_stub.py`
  - Create `ai-orchestrator/app/nodes/ad_engine_stub.py`
  - Each stub: estimate cost → check credit via MCP → mock execution (2s delay) → deduct credit
  - Return mock data with clear "mock" flag
  - Handle credit check failures gracefully
  - _Requirements: 需求 6-10_

- [ ] 3.5 Implement response generator node
  - Create `ai-orchestrator/app/nodes/respond.py` with `respond_node` function
  - Use Gemini 2.5 Flash for fast response generation
  - Handle error responses with user-friendly messages
  - Handle insufficient credit responses with recharge link
  - Format responses with Markdown (bold, lists, emojis)
  - Include next step suggestions
  - _Requirements: 需求 1.2, 14.3_

- [ ] 3.6 Implement conversation persistence node
  - Create `ai-orchestrator/app/nodes/persist.py` with `persist_conversation_node`
  - Call MCP `save_conversation` tool after response generation
  - Format messages for storage (role, content, timestamp)
  - Handle persistence failures gracefully (log but don't fail)
  - Add retry logic for transient failures
  - _Requirements: 需求 5.1_

- [ ] 3.7 Implement human confirmation node
  - Create `ai-orchestrator/app/nodes/confirmation.py` with `human_confirmation_node`
  - Detect high-risk operations: pause_all, delete_campaign, budget_change > 50%
  - Generate confirmation message with operation details and impact
  - Set requires_confirmation flag and return END
  - Support resume after user confirms/cancels via state update
  - _Requirements: 需求 14.5_

- [ ] 3.8 Implement conditional routing logic
  - Create `ai-orchestrator/app/core/routing.py` with routing functions
  - Implement `route_by_intent(state)` → returns node name based on intent
  - Implement `should_confirm(state)` → returns "confirm" or "execute"
  - Implement `after_module(state)` → routes to next module or respond
  - Add logging for all routing decisions
  - _Requirements: 需求 3.2, 14.5_

- [ ] 3.9 Implement context manager
  - Create `ai-orchestrator/app/core/context.py` with context utilities
  - Implement `extract_references(message)` → finds "previous", "that", "it"
  - Implement `resolve_reference(reference, history)` → finds referenced entity
  - Implement `compress_history(messages, max_rounds)` → summarizes old messages
  - Handle context window limits (compress after 100 rounds)
  - _Requirements: 需求 5.2, 5.3, 5.4_

- [ ] 3.10 Build and compile LangGraph
  - Create `ai-orchestrator/app/core/graph.py` with `build_agent_graph()` function
  - Add all nodes: router, 5 stubs, respond, persist, confirmation
  - Set entry point to router
  - Add conditional edges: router → modules, modules → confirmation check → respond
  - Add edge: respond → persist → END
  - Use MemorySaver checkpointer for state persistence
  - Compile and return graph
  - _Requirements: 需求 4_

- [ ] 4. FastAPI Application
- [ ] 4.1 Create FastAPI application
  - Create `ai-orchestrator/app/main.py` with FastAPI app instance
  - Configure CORS to allow web-platform origin
  - Add startup event: initialize MCP client, test connection, compile LangGraph
  - Add shutdown event: cleanup connections
  - Add middleware for request logging
  - _Requirements: Infrastructure_

- [ ] 4.2 Implement service authentication
  - Create `ai-orchestrator/app/core/auth.py` with `validate_service_token()` dependency
  - Extract Bearer token from Authorization header
  - Compare with WEB_PLATFORM_SERVICE_TOKEN from settings
  - Raise HTTPException(401) for invalid/missing tokens
  - Log authentication attempts
  - _Requirements: Security_

- [ ] 4.3 Implement HTTP streaming endpoint
  - Create `ai-orchestrator/app/api/chat.py` with `/chat` POST endpoint
  - Define `ChatRequest` schema: messages, user_id, session_id
  - Validate service token using dependency
  - Build initial AgentState from request
  - Execute LangGraph with config (thread_id = session_id)
  - Return StreamingResponse with text/event-stream content type
  - _Requirements: 需求 1.2, 13.3_

- [ ] 4.4 Implement streaming response generator
  - Create async generator `stream_graph_events(agent, state, config)`
  - Use `agent.astream_events(state, config, version="v2")`
  - Stream LLM tokens: `data: {"type": "token", "content": "..."}\n\n`
  - Stream tool calls: `data: {"type": "tool_start", "tool": "..."}\n\n`
  - Stream tool results: `data: {"type": "tool_complete", "tool": "...", "result": {...}}\n\n`
  - Send final message: `data: {"type": "done"}\n\n`
  - Handle errors in stream gracefully
  - _Requirements: 需求 13.1, 13.3_

- [ ] 4.5 Implement health check endpoint
  - Create `/health` GET endpoint
  - Check Redis connection with ping
  - Check MCP connection by calling a lightweight tool
  - Check Gemini API with test request
  - Return JSON: {status: "healthy"/"degraded", checks: {...}, timestamp}
  - Add /ready endpoint for Kubernetes readiness probe
  - _Requirements: Monitoring_

- [ ] 4.6 Implement error handling middleware
  - Create global exception handler for common exceptions
  - Map MCPConnectionError → 503 Service Unavailable
  - Map InsufficientCreditsError → 402 Payment Required
  - Map ValidationError → 400 Bad Request
  - Return consistent error format: {error: {code, message, details}}
  - Log all errors with full context (user_id, session_id, traceback)
  - _Requirements: 需求 12.1_

- [ ]* 4.7 Write integration tests for chat endpoint
  - Test successful message flow with mock MCP client
  - Test streaming response format (SSE)
  - Test authentication failures (missing/invalid token)
  - Test error handling (MCP failure, Gemini failure)
  - Test timeout handling
  - Use pytest-asyncio and httpx.AsyncClient
  - _Requirements: Testing_

- [ ] 5. Error Handling and Retry Logic
- [ ] 5.1 Implement error handler class
  - Create `ai-orchestrator/app/core/errors.py` with custom exception classes
  - Define: MCPConnectionError, MCPToolError, InsufficientCreditsError, AIModelError
  - Create `ErrorHandler` class with `handle_error(exception, context)` method
  - Map exceptions to error codes from INTERFACES.md
  - Generate user-friendly error messages (avoid technical jargon)
  - Include retry information and suggested actions
  - _Requirements: 需求 12.1, 12.2_

- [ ] 5.2 Implement retry with exponential backoff
  - Create `ai-orchestrator/app/core/retry.py` with `retry_with_backoff()` decorator
  - Support configurable max retries (default 3)
  - Implement exponential backoff: 1s, 2s, 4s
  - Add jitter to prevent thundering herd
  - Log each retry attempt with attempt number and wait time
  - Raise original exception after max retries
  - _Requirements: 需求 11.4_

- [ ] 5.3 Implement error recovery in nodes
  - Wrap all node logic in try-except blocks
  - Return error state dict instead of raising exceptions
  - Preserve partial results on failure (e.g., if 2/3 tasks complete)
  - Add error field to state with code, message, details
  - Log errors with full context (node name, state, exception)
  - _Requirements: 需求 12.4_

- [ ]* 6. Testing and Validation
- [ ]* 6.1 Write property test for intent recognition
  - **Feature: ai-orchestrator, Property 1: Intent Recognition Accuracy**
  - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
  - Create `ai-orchestrator/tests/test_intent_recognition_property.py`
  - Use Hypothesis to generate random user messages for each intent category
  - Test that router_node correctly identifies intent for generated messages
  - Verify accuracy > 80% across 100+ generated samples
  - Test edge cases: ambiguous messages, multi-intent messages
  - _Requirements: Correctness Properties_

- [ ]* 6.2 Write property test for multi-step execution
  - **Feature: ai-orchestrator, Property 2: Multi-step Execution Order**
  - **Validates: Requirements 3.3**
  - Create `ai-orchestrator/tests/test_execution_order_property.py`
  - Generate random multi-step tasks with dependencies
  - Verify creative generation always happens before campaign creation
  - Verify landing page creation before campaign creation
  - Test that dependencies are respected in execution order
  - _Requirements: Correctness Properties_

- [ ]* 6.3 Write property test for context resolution
  - **Feature: ai-orchestrator, Property 3: Context Reference Resolution**
  - **Validates: Requirements 5.2, 5.3**
  - Create `ai-orchestrator/tests/test_context_resolution_property.py`
  - Generate random conversation histories with entities
  - Generate random reference messages ("use the previous X", "add $Y more")
  - Verify context manager correctly resolves references
  - Test with various reference types and conversation lengths
  - _Requirements: Correctness Properties_

- [ ]* 6.4 Write property test for retry mechanism
  - **Feature: ai-orchestrator, Property 4: MCP Retry Mechanism**
  - **Validates: Requirements 11.4**
  - Create `ai-orchestrator/tests/test_retry_property.py`
  - Simulate MCP failures with mock client
  - Verify exactly 3 retry attempts before giving up
  - Verify exponential backoff timing (1s, 2s, 4s)
  - Test with different failure scenarios (timeout, connection error, 500)
  - _Requirements: Correctness Properties_

- [ ]* 6.5 Write property test for operation idempotence
  - **Feature: ai-orchestrator, Property 5: Operation Idempotence**
  - **Validates: Requirements 12.5**
  - Create `ai-orchestrator/tests/test_idempotence_property.py`
  - Generate random operations and execute twice
  - Verify retry produces same result as single execution
  - Test credit deduction idempotence with operation_id
  - Verify no duplicate side effects
  - _Requirements: Correctness Properties_

- [ ]* 6.6 Write property test for confirmation mechanism
  - **Feature: ai-orchestrator, Property 6: Confirmation for High-Risk Operations**
  - **Validates: Requirements 14.5.1, 14.5.2, 14.5.3**
  - Create `ai-orchestrator/tests/test_confirmation_property.py`
  - Generate random high-risk operations (pause_all, delete, large budget)
  - Verify confirmation node is triggered
  - Verify low-risk operations skip confirmation
  - Test confirmation flow with user approval/rejection
  - _Requirements: Correctness Properties_

- [ ]* 6.7 Write unit tests for all nodes
  - Create `ai-orchestrator/tests/test_nodes.py`
  - Test router_node with various user messages
  - Test each stub module with sufficient/insufficient credits
  - Test respond_node with success/error/partial results
  - Test persist_conversation_node with success/failure
  - Test confirmation_node with high-risk operations
  - Use pytest fixtures for common test data
  - _Requirements: Testing_

- [ ]* 6.8 Create mock MCP client for testing
  - Create `ai-orchestrator/tests/mocks/mock_mcp_client.py`
  - Implement MockMCPClient class with call_tool method
  - Return realistic mock data for all MCP tools
  - Support failure simulation via configuration
  - Track call history for assertions
  - Add helper methods for common test scenarios
  - _Requirements: Testing_

- [ ] 7. Integration and Deployment
- [ ] 7.1 Create Docker configuration
  - Create `ai-orchestrator/Dockerfile` with Python 3.12-slim base image
  - Install dependencies from pyproject.toml
  - Set up non-root user for security
  - Configure health check: `curl -f http://localhost:8001/health`
  - Set working directory and expose port 8001
  - _Requirements: Deployment_

- [ ] 7.2 Update docker-compose.yml
  - Add `ai-orchestrator` service to root docker-compose.yml
  - Configure environment variables: GEMINI_API_KEY, WEB_PLATFORM_URL, REDIS_URL
  - Set up network connections to backend (web-platform) and redis
  - Add depends_on: redis, backend
  - Add health check with 30s interval
  - Map port 8001:8001
  - _Requirements: Deployment_

- [ ] 7.3 Create environment configuration
  - Create `ai-orchestrator/.env.example` with all required variables
  - Document each variable with description and example value
  - Add validation in config.py for missing required variables
  - Create `ai-orchestrator/README.md` with setup instructions
  - _Requirements: Configuration_

- [ ] 7.4 Write deployment documentation
  - Update `ai-orchestrator/README.md` with:
    - Project overview and architecture
    - Setup steps (local development)
    - API endpoints documentation
    - Environment variables reference
    - Troubleshooting guide (common errors)
    - Development workflow
  - _Requirements: Documentation_

- [ ] 8. Checkpoint - Verify Phase 1 Complete
- [ ] 8.1 End-to-end testing
  - Start all services: `docker-compose up -d`
  - Verify all services healthy: `docker-compose ps`
  - Open frontend at http://localhost:3000
  - Login and open chat window
  - Send test message: "帮我生成 10 张广告图片"
  - Verify streaming response received
  - Check AI Orchestrator logs: `docker-compose logs ai-orchestrator`
  - Verify credit check called in logs
  - Verify credit deduction called in logs
  - Verify conversation saved to database
  - Test error handling: disconnect MCP and verify error message

- [ ] 8.2 Verify acceptance criteria
  - ✅ Users can send messages and receive mock responses (需求 1.1, 1.2)
  - ✅ Intent recognition accuracy > 80% - test with 20+ samples (需求 2.1-2.5)
  - ✅ HTTP streaming latency < 2 seconds (需求 13.1)
  - ✅ Credit check and deduct correctly called (需求 6-10)
  - ✅ Conversation history persisted to Web Platform (需求 5.1)
  - ✅ All error codes match INTERFACES.md (需求 12.1)
  - ✅ Service authentication works (Security)
  - ✅ Retry logic works for MCP failures (需求 11.4)

- [ ] 8.3 Code review and cleanup
  - Review all code for consistency with design.md
  - Ensure proper error handling in all nodes
  - Verify logging is comprehensive (all operations logged)
  - Check type annotations (run mypy)
  - Run linters: `ruff check .` and `ruff format .`
  - Remove debug print statements
  - Update README with any learnings

---

## Phase 2: Ad Creative Implementation (Week 4)

### 9. Replace Creative Stub with Real Implementation

- [ ] 9.1 Integrate Gemini Imagen 3
  - Replace `creative_stub_node` with real implementation
  - Call Gemini Imagen 3 API for image generation
  - Handle generation failures and retries
  - _Requirements: 需求 6.1_

- [ ] 9.2 Implement creative analysis
  - Add Gemini 2.5 Flash for image analysis
  - Implement quality scoring
  - Return structured analysis results
  - _Requirements: 需求 6.2, 6.3_

- [ ] 9.3 Implement S3 upload via MCP
  - Call MCP `get_upload_url` tool
  - Upload generated images to S3
  - Call MCP `create_creative` to store metadata
  - Handle upload failures
  - _Requirements: 需求 6.4_

- [ ] 9.4 Implement credit refund on failure
  - Detect generation failures
  - Call MCP `refund_credit` tool
  - Log refund transactions
  - _Requirements: Credit integration_

- [ ]* 9.5 Write integration tests for creative generation
  - Test end-to-end creative generation
  - Test credit deduction and refund
  - Test S3 upload flow
  - Test error handling
  - _Requirements: Testing_

### 10. Checkpoint - Verify Phase 2 Complete

- [ ] 10.1 Test real creative generation
  - Generate actual images with Gemini Imagen 3
  - Verify images uploaded to S3
  - Verify metadata stored in database
  - Verify credit correctly deducted

- [ ] 10.2 Verify error handling
  - Test generation failures
  - Verify credit refund on failure
  - Test S3 upload failures
  - Verify user-friendly error messages

---

## Phase 3-6: Other Functional Modules (Weeks 5-8)

### 11. Ad Performance Module (Week 5)

- [ ] 11.1 Replace reporting stub with real implementation
- [ ] 11.2 Implement data fetching from ad platforms
- [ ] 11.3 Implement AI-powered analysis
- [ ] 11.4 Implement anomaly detection
- [ ]* 11.5 Write integration tests

### 12. Market Intelligence Module (Week 6)

- [ ] 12.1 Replace market intel stub with real implementation
- [ ] 12.2 Implement competitor analysis
- [ ] 12.3 Implement trend analysis
- [ ] 12.4 Implement strategy generation
- [ ]* 12.5 Write integration tests

### 13. Landing Page Module (Week 7)

- [ ] 13.1 Replace landing page stub with real implementation
- [ ] 13.2 Implement page generation
- [ ] 13.3 Implement multi-language support
- [ ] 13.4 Implement A/B testing setup
- [ ]* 13.5 Write integration tests

### 14. Campaign Automation Module (Week 8)

- [ ] 14.1 Replace ad engine stub with real implementation
- [ ] 14.2 Implement campaign creation
- [ ] 14.3 Implement budget optimization
- [ ] 14.4 Implement rule engine
- [ ]* 14.5 Write integration tests

---

## Notes

- **Optional Tasks**: Tasks marked with `*` are optional testing tasks (can be skipped for faster MVP)
- **Property Tests**: Each property test should run 100+ iterations using Hypothesis
- **Error Handling**: All MCP tool calls must have proper error handling and retry logic
- **Logging**: All nodes must log structured data (JSON) for debugging and monitoring
- **Phase 1 Critical**: Do not proceed to Phase 2 until all Phase 1 non-optional tasks are complete
- **Prerequisites First**: Complete tasks 0.1-0.3 in Web Platform before starting AI Orchestrator development
- **Testing Strategy**: Write implementation first, then tests. Property tests validate correctness properties from design.md
- **Code Quality**: Run `ruff check .` and `mypy .` before marking tasks complete
