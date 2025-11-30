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

- [x] 0. Prerequisites - Complete Missing Web Platform Features
- [x] 0.1 Create conversation data models in Web Platform
  - Create `backend/app/models/conversation.py` with Conversation model
  - Create `backend/app/models/message.py` with Message model
  - Add relationships: User → Conversations → Messages
  - Create Alembic migration for new tables
  - _Requirements: 需求 5.1 (conversation persistence)_

- [x] 0.2 Implement conversation MCP tools in Web Platform
  - Create `backend/app/mcp/tools/conversation.py`
  - Implement `save_conversation` tool (stores messages to database)
  - Implement `get_conversation_history` tool (retrieves conversation by session_id)
  - Register tools in MCP registry
  - _Requirements: 需求 5.1, 1.5_

- [x] 0.3 Generate service token for AI Orchestrator
  - Add `WEB_PLATFORM_SERVICE_TOKEN` to backend/.env
  - Document token generation process in README
  - Update WebSocket handler to validate service token
  - _Requirements: Security, service-to-service auth_

- [x] 1. Project Setup and Infrastructure
- [x] 1.1 Create project structure
  - Create `ai-orchestrator/` directory at repository root
  - Create `ai-orchestrator/pyproject.toml` with project metadata
  - Configure dependencies: FastAPI>=0.115.0, LangGraph>=0.2.0, langchain-google-genai>=2.0.0, httpx>=0.27.0, redis>=5.0.0, pydantic>=2.9.0, structlog>=24.0.0
  - Create directory structure: `app/`, `app/core/`, `app/nodes/`, `app/services/`, `app/prompts/`, `app/api/`, `tests/`
  - Create `ai-orchestrator/requirements.txt` from pyproject.toml
  - _Requirements: Infrastructure setup_

- [x] 1.2 Configure development environment
  - Create `ai-orchestrator/.env.example` with all required variables
  - Create `ai-orchestrator/.gitignore` for Python (venv/, __pycache__/, .env, *.pyc)
  - Create `ai-orchestrator/README.md` with project overview
  - Add development setup instructions
  - _Requirements: Infrastructure setup_

- [x] 1.3 Implement configuration management
  - Create `ai-orchestrator/app/core/config.py` with Pydantic Settings
  - Define settings: GEMINI_API_KEY, WEB_PLATFORM_URL, WEB_PLATFORM_SERVICE_TOKEN, REDIS_URL
  - Add computed fields for derived values
  - Add validation for required settings (raise error if missing)
  - Support loading from .env file
  - _Requirements: Infrastructure setup_

- [x] 1.4 Set up logging infrastructure
  - Create `ai-orchestrator/app/core/logging.py`
  - Configure structlog with JSON formatter for production
  - Configure human-readable formatter for development
  - Set up log levels from environment variables (default: INFO)
  - Add request ID to all logs for tracing
  - _Requirements: 需求 12, 15_

- [x] 1.5 Set up Redis client
  - Create `ai-orchestrator/app/core/redis_client.py`
  - Implement connection pooling with redis-py
  - Add `get_redis()` async function for dependency injection
  - Add health check method: `ping()`
  - Handle connection failures gracefully with retries
  - Add connection timeout configuration
  - _Requirements: State persistence_

- [x] 2. MCP Client Implementation
- [x] 2.1 Create MCP client base class
  - Implement `ai-orchestrator/app/services/mcp_client.py`
  - Add HTTP client using httpx with connection pooling
  - Implement exponential backoff retry logic (1s, 2s, 4s, max 3 retries)
  - Add request/response logging with structlog
  - Add timeout handling (default 30s)
  - _Requirements: 需求 11.1, 11.4_

- [x] 2.2 Implement MCP tool call methods
  - Add `call_tool(tool_name, parameters)` method
  - Format requests according to Web Platform's `/api/v1/mcp/execute` endpoint
  - Add service token authentication in Authorization header
  - Parse MCPResponse and extract data or error
  - Create custom exceptions: `MCPConnectionError`, `MCPToolError`, `InsufficientCreditsError`
  - Map MCP error codes to user-friendly messages
  - _Requirements: 需求 11.2, 11.3, 12.1_

- [x] 2.3 Implement credit management wrappers
  - Add `check_credit(user_id, estimated_credits, operation_type)` wrapper
  - Add `deduct_credit(user_id, credits, operation_type, operation_id)` wrapper
  - Add `refund_credit(user_id, credits, operation_id)` wrapper
  - Handle insufficient credit errors (code 6011) with clear user messages
  - Add logging for all credit operations
  - _Requirements: Credit integration, 需求 6-10_

- [x] 2.4 Implement conversation persistence wrappers
  - Add `save_conversation(user_id, session_id, messages)` wrapper
  - Add `get_conversation_history(user_id, session_id, limit)` wrapper
  - Handle persistence failures gracefully (log error but don't fail request)
  - Add retry logic for transient failures
  - _Requirements: 需求 5.1, 1.5_

- [x] 2.5 Create Gemini client wrapper
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

- [x] 3. LangGraph State Machine
- [x] 3.1 Define agent state schema
  - Create `ai-orchestrator/app/core/state.py` with `AgentState` TypedDict
  - Define fields: messages (with operator.add), user_id, session_id, current_intent
  - Add fields: extracted_params, pending_actions, completed_results
  - Add fields: requires_confirmation, user_confirmed, error, retry_count
  - Add comprehensive docstrings for each field
  - _Requirements: 需求 4, 5_

- [x] 3.2 Create prompt templates
  - Create `ai-orchestrator/app/prompts/` directory
  - Create `intent_recognition.py` with detailed intent recognition prompt
  - Include examples for each intent type (creative, reporting, market, landing, campaign)
  - Create `response_generation.py` with response formatting prompt
  - Add system prompts for friendly, helpful tone
  - _Requirements: 需求 2, 14.3_

- [x] 3.3 Implement intent recognition node
  - Create `ai-orchestrator/app/nodes/router.py` with `router_node` function
  - Define `IntentSchema` Pydantic model with structured output
  - Use Gemini 2.5 Pro with `with_structured_output(IntentSchema)`
  - Extract intent, confidence, parameters, actions, estimated_cost
  - Handle low confidence scores (< 0.6) by asking clarifying questions
  - Log all intent recognition results
  - _Requirements: 需求 2.1-2.5, 14.1_

- [x] 3.4 Implement stub functional module nodes
  - Create `ai-orchestrator/app/nodes/creative_stub.py`
  - Create `ai-orchestrator/app/nodes/reporting_stub.py`
  - Create `ai-orchestrator/app/nodes/market_intel_stub.py`
  - Create `ai-orchestrator/app/nodes/landing_page_stub.py`
  - Create `ai-orchestrator/app/nodes/ad_engine_stub.py`
  - Each stub: estimate cost → check credit via MCP → mock execution (2s delay) → deduct credit
  - Return mock data with clear "mock" flag
  - Handle credit check failures gracefully
  - _Requirements: 需求 6-10_

- [x] 3.5 Implement response generator node
  - Create `ai-orchestrator/app/nodes/respond.py` with `respond_node` function
  - Use Gemini 2.5 Flash for fast response generation
  - Handle error responses with user-friendly messages
  - Handle insufficient credit responses with recharge link
  - Format responses with Markdown (bold, lists, emojis)
  - Include next step suggestions
  - _Requirements: 需求 1.2, 14.3_

- [x] 3.6 Implement conversation persistence node
  - Create `ai-orchestrator/app/nodes/persist.py` with `persist_conversation_node`
  - Call MCP `save_conversation` tool after response generation
  - Format messages for storage (role, content, timestamp)
  - Handle persistence failures gracefully (log but don't fail)
  - Add retry logic for transient failures
  - _Requirements: 需求 5.1_

- [x] 3.7 Implement human confirmation node
  - Create `ai-orchestrator/app/nodes/confirmation.py` with `human_confirmation_node`
  - Detect high-risk operations: pause_all, delete_campaign, budget_change > 50%
  - Generate confirmation message with operation details and impact
  - Set requires_confirmation flag and return END
  - Support resume after user confirms/cancels via state update
  - _Requirements: 需求 14.5_

- [x] 3.8 Implement conditional routing logic
  - Create `ai-orchestrator/app/core/routing.py` with routing functions
  - Implement `route_by_intent(state)` → returns node name based on intent
  - Implement `should_confirm(state)` → returns "confirm" or "execute"
  - Implement `after_module(state)` → routes to next module or respond
  - Add logging for all routing decisions
  - _Requirements: 需求 3.2, 14.5_

- [x] 3.9 Implement context manager
  - Create `ai-orchestrator/app/core/context.py` with context utilities
  - Implement `extract_references(message)` → finds "previous", "that", "it"
  - Implement `resolve_reference(reference, history)` → finds referenced entity
  - Implement `compress_history(messages, max_rounds)` → summarizes old messages
  - Handle context window limits (compress after 100 rounds)
  - _Requirements: 需求 5.2, 5.3, 5.4_

- [x] 3.10 Build and compile LangGraph
  - Create `ai-orchestrator/app/core/graph.py` with `build_agent_graph()` function
  - Add all nodes: router, 5 stubs, respond, persist, confirmation
  - Set entry point to router
  - Add conditional edges: router → modules, modules → confirmation check → respond
  - Add edge: respond → persist → END
  - Use MemorySaver checkpointer for state persistence
  - Compile and return graph
  - _Requirements: 需求 4_

- [x] 4. FastAPI Application
- [x] 4.1 Create FastAPI application
  - Create `ai-orchestrator/app/main.py` with FastAPI app instance
  - Configure CORS to allow web-platform origin
  - Add startup event: initialize MCP client, test connection, compile LangGraph
  - Add shutdown event: cleanup connections
  - Add middleware for request logging
  - _Requirements: Infrastructure_

- [x] 4.2 Implement service authentication
  - Create `ai-orchestrator/app/core/auth.py` with `validate_service_token()` dependency
  - Extract Bearer token from Authorization header
  - Compare with WEB_PLATFORM_SERVICE_TOKEN from settings
  - Raise HTTPException(401) for invalid/missing tokens
  - Log authentication attempts
  - _Requirements: Security_

- [x] 4.3 Implement HTTP streaming endpoint
  - Create `ai-orchestrator/app/api/chat.py` with `/chat` POST endpoint
  - Define `ChatRequest` schema: messages, user_id, session_id
  - Validate service token using dependency
  - Build initial AgentState from request
  - Execute LangGraph with config (thread_id = session_id)
  - Return StreamingResponse with text/event-stream content type
  - _Requirements: 需求 1.2, 13.3_

- [x] 4.4 Implement streaming response generator
  - Create async generator `stream_graph_events(agent, state, config)`
  - Use `agent.astream_events(state, config, version="v2")`
  - Stream LLM tokens: `data: {"type": "token", "content": "..."}\n\n`
  - Stream tool calls: `data: {"type": "tool_start", "tool": "..."}\n\n`
  - Stream tool results: `data: {"type": "tool_complete", "tool": "...", "result": {...}}\n\n`
  - Send final message: `data: {"type": "done"}\n\n`
  - Handle errors in stream gracefully
  - _Requirements: 需求 13.1, 13.3_

- [x] 4.5 Implement health check endpoint
  - Create `/health` GET endpoint
  - Check Redis connection with ping
  - Check MCP connection by calling a lightweight tool
  - Check Gemini API with test request
  - Return JSON: {status: "healthy"/"degraded", checks: {...}, timestamp}
  - Add /ready endpoint for Kubernetes readiness probe
  - _Requirements: Monitoring_

- [x] 4.6 Implement error handling middleware
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

- [x] 5. Error Handling and Retry Logic
- [x] 5.1 Implement error handler class
  - Create `ai-orchestrator/app/core/errors.py` with custom exception classes
  - Define: MCPConnectionError, MCPToolError, InsufficientCreditsError, AIModelError
  - Create `ErrorHandler` class with `handle_error(exception, context)` method
  - Map exceptions to error codes from INTERFACES.md
  - Generate user-friendly error messages (avoid technical jargon)
  - Include retry information and suggested actions
  - _Requirements: 需求 12.1, 12.2_

- [x] 5.2 Implement retry with exponential backoff
  - Create `ai-orchestrator/app/core/retry.py` with `retry_with_backoff()` decorator
  - Support configurable max retries (default 3)
  - Implement exponential backoff: 1s, 2s, 4s
  - Add jitter to prevent thundering herd
  - Log each retry attempt with attempt number and wait time
  - Raise original exception after max retries
  - _Requirements: 需求 11.4_

- [x] 5.3 Implement error recovery in nodes
  - Wrap all node logic in try-except blocks
  - Return error state dict instead of raising exceptions
  - Preserve partial results on failure (e.g., if 2/3 tasks complete)
  - Add error field to state with code, message, details
  - Log errors with full context (node name, state, exception)
  - _Requirements: 需求 12.4_

- [-] 6. Testing and Validation
- [x] 6.1 Write property test for intent recognition
  - **Feature: ai-orchestrator, Property 1: Intent Recognition Accuracy**
  - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
  - Create `ai-orchestrator/tests/test_intent_recognition_property.py`
  - Use Hypothesis to generate random user messages for each intent category
  - Test that router_node correctly identifies intent for generated messages
  - Verify accuracy > 80% across 100+ generated samples
  - Test edge cases: ambiguous messages, multi-intent messages
  - _Requirements: Correctness Properties_

- [x] 6.2 Write property test for multi-step execution
  - **Feature: ai-orchestrator, Property 2: Multi-step Execution Order**
  - **Validates: Requirements 3.3**
  - Create `ai-orchestrator/tests/test_execution_order_property.py`
  - Generate random multi-step tasks with dependencies
  - Verify creative generation always happens before campaign creation
  - Verify landing page creation before campaign creation
  - Test that dependencies are respected in execution order
  - _Requirements: Correctness Properties_

- [x] 6.3 Write property test for context resolution
  - **Feature: ai-orchestrator, Property 3: Context Reference Resolution**
  - **Validates: Requirements 5.2, 5.3**
  - Create `ai-orchestrator/tests/test_context_resolution_property.py`
  - Generate random conversation histories with entities
  - Generate random reference messages ("use the previous X", "add $Y more")
  - Verify context manager correctly resolves references
  - Test with various reference types and conversation lengths
  - _Requirements: Correctness Properties_

- [ ] 6.4 Write property test for retry mechanism
  - **Feature: ai-orchestrator, Property 4: MCP Retry Mechanism**
  - **Validates: Requirements 11.4**
  - Create `ai-orchestrator/tests/test_retry_property.py`
  - Simulate MCP failures with mock client
  - Verify exactly 3 retry attempts before giving up
  - Verify exponential backoff timing (1s, 2s, 4s)
  - Test with different failure scenarios (timeout, connection error, 500)
  - _Requirements: Correctness Properties_

- [ ] 6.5 Write property test for operation idempotence
  - **Feature: ai-orchestrator, Property 5: Operation Idempotence**
  - **Validates: Requirements 12.5**
  - Create `ai-orchestrator/tests/test_idempotence_property.py`
  - Generate random operations and execute twice
  - Verify retry produces same result as single execution
  - Test credit deduction idempotence with operation_id
  - Verify no duplicate side effects
  - _Requirements: Correctness Properties_

- [ ] 6.6 Write property test for confirmation mechanism
  - **Feature: ai-orchestrator, Property 6: Confirmation for High-Risk Operations**
  - **Validates: Requirements 14.5.1, 14.5.2, 14.5.3**
  - Create `ai-orchestrator/tests/test_confirmation_property.py`
  - Generate random high-risk operations (pause_all, delete, large budget)
  - Verify confirmation node is triggered
  - Verify low-risk operations skip confirmation
  - Test confirmation flow with user approval/rejection
  - _Requirements: Correctness Properties_

- [ ] 6.7 Write unit tests for all nodes
  - Create `ai-orchestrator/tests/test_nodes.py`
  - Test router_node with various user messages
  - Test each stub module with sufficient/insufficient credits
  - Test respond_node with success/error/partial results
  - Test persist_conversation_node with success/failure
  - Test confirmation_node with high-risk operations
  - Use pytest fixtures for common test data
  - _Requirements: Testing_

- [ ] 6.8 Create mock MCP client for testing
  - Create `ai-orchestrator/tests/mocks/mock_mcp_client.py`
  - Implement MockMCPClient class with call_tool method
  - Return realistic mock data for all MCP tools
  - Support failure simulation via configuration
  - Track call history for assertions
  - Add helper methods for common test scenarios
  - _Requirements: Testing_

- [x] 7. Integration and Deployment
- [x] 7.1 Create Docker configuration
  - Create `ai-orchestrator/Dockerfile` with Python 3.12-slim base image
  - Install dependencies from pyproject.toml
  - Set up non-root user for security
  - Configure health check: `curl -f http://localhost:8001/health`
  - Set working directory and expose port 8001
  - _Requirements: Deployment_

- [x] 7.2 Update docker-compose.yml
  - Add `ai-orchestrator` service to root docker-compose.yml
  - Configure environment variables: GEMINI_API_KEY, WEB_PLATFORM_URL, REDIS_URL
  - Set up network connections to backend (web-platform) and redis
  - Add depends_on: redis, backend
  - Add health check with 30s interval
  - Map port 8001:8001
  - _Requirements: Deployment_

- [x] 7.3 Create environment configuration
  - Create `ai-orchestrator/.env.example` with all required variables
  - Document each variable with description and example value
  - Add validation in config.py for missing required variables
  - Create `ai-orchestrator/README.md` with setup instructions
  - _Requirements: Configuration_

- [x] 7.4 Write deployment documentation
  - Update `ai-orchestrator/README.md` with:
    - Project overview and architecture
    - Setup steps (local development)
    - API endpoints documentation
    - Environment variables reference
    - Troubleshooting guide (common errors)
    - Development workflow
  - _Requirements: Documentation_

- [x] 8. Checkpoint - Verify Phase 1 Complete
- [x] 8.1 End-to-end testing
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

- [x] 8.2 Verify acceptance criteria
  - ✅ Users can send messages and receive mock responses (需求 1.1, 1.2)
  - ✅ Intent recognition accuracy > 80% - test with 20+ samples (需求 2.1-2.5)
  - ✅ HTTP streaming latency < 2 seconds (需求 13.1)
  - ✅ Credit check and deduct correctly called (需求 6-10)
  - ✅ Conversation history persisted to Web Platform (需求 5.1)
  - ✅ All error codes match INTERFACES.md (需求 12.1)
  - ✅ Service authentication works (Security)
  - ✅ Retry logic works for MCP failures (需求 11.4)

- [x] 8.3 Code review and cleanup
  - Review all code for consistency with design.md
  - Ensure proper error handling in all nodes
  - Verify logging is comprehensive (all operations logged)
  - Check type annotations (run mypy)
  - Run linters: `ruff check .` and `ruff format .`
  - Remove debug print statements
  - Update README with any learnings


## Phase 2: Ad Creative Implementation (Week 4)

- [x] 9. Replace Creative Stub with Real Implementation

- [x] 9.1 Integrate Gemini Imagen 3
  - Replace `creative_stub_node` with real implementation
  - Call Gemini Imagen 3 API for image generation
  - Handle generation failures and retries
  - _Requirements: 需求 6.1_

- [x] 9.2 Implement creative analysis
  - Add Gemini 2.5 Flash for image analysis
  - Implement quality scoring
  - Return structured analysis results
  - _Requirements: 需求 6.2, 6.3_

- [x] 9.3 Implement S3 upload via MCP
  - Call MCP `get_upload_url` tool
  - Upload generated images to S3
  - Call MCP `create_creative` to store metadata
  - Handle upload failures
  - _Requirements: 需求 6.4_

- [x] 9.4 Implement credit refund on failure
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

- [x] 10. Checkpoint - Verify Phase 2 Complete

- [x] 10.1 Test real creative generation
  - Generate actual images with Gemini Imagen 3
  - Verify images uploaded to S3
  - Verify metadata stored in database
  - Verify credit correctly deducted

- [x] 10.2 Verify error handling
  - Test generation failures
  - Verify credit refund on failure
  - Test S3 upload failures
  - Verify user-friendly error messages

---

## Phase 3: Ad Performance Module

- [x] 11. Ad Performance Module - 报表和分析功能

- [x] 11.1 Replace reporting stub with real implementation
  - Create `ai-orchestrator/app/nodes/reporting_node.py` replacing `reporting_stub.py`
  - Implement `reporting_node` function with real MCP tool calls
  - Add action handlers: get_reports, analyze_performance, detect_anomaly
  - Estimate credit cost based on data volume and analysis complexity
  - Check credit via MCP before execution
  - Deduct credit after successful execution
  - Handle errors gracefully with user-friendly messages
  - _Requirements: 需求 8.1, 8.2, 8.3_

- [x] 11.2 Implement data fetching from ad platforms
  - Call MCP `get_reports` tool to fetch ad performance data
  - Support date range parameters (today, last_7_days, last_30_days, custom)
  - Support platform filter (meta, tiktok, all)
  - Support metrics filter (impressions, clicks, spend, conversions, roas, cpa)
  - Parse and normalize data from different ad platforms
  - Handle API rate limits and pagination
  - Cache frequently requested data (5 min TTL)
  - _Requirements: 需求 8.1_

- [x] 11.3 Implement AI-powered analysis
  - Use Gemini 2.5 Pro for performance analysis
  - Create analysis prompt template in `app/prompts/performance_analysis.py`
  - Generate insights: top performers, underperformers, trends
  - Compare metrics against industry benchmarks
  - Generate actionable recommendations (increase budget, pause ad, etc.)
  - Format response with charts data for frontend rendering
  - _Requirements: 需求 8.2, 8.4_

- [x] 11.4 Implement anomaly detection
  - Call MCP `detect_anomaly` tool or implement locally
  - Detect sudden changes: CTR drop > 20%, CPA spike > 30%, spend anomalies
  - Use statistical methods (z-score, moving average deviation)
  - Generate alerts with severity levels (info, warning, critical)
  - Suggest root causes and remediation actions
  - _Requirements: 需求 8.3_

- [x] 11.5 Handle insufficient data scenarios
  - Detect when data is insufficient for analysis (< 7 days, < 1000 impressions)
  - Return helpful message explaining minimum data requirements
  - Suggest waiting period or alternative actions
  - _Requirements: 需求 8.5_

- [ ]* 11.6 Write integration tests for Ad Performance
  - Test get_reports with various date ranges and filters
  - Test analyze_performance with mock data
  - Test anomaly detection with known anomalies
  - Test insufficient data handling
  - Test credit check and deduction flow
  - _Requirements: Testing_

- [x] 11.7 Checkpoint - Verify Ad Performance Module
  - Test "查看报表" intent recognition and routing
  - Verify data fetching from MCP works correctly
  - Verify AI analysis generates meaningful insights
  - Verify anomaly detection catches test anomalies
  - Verify credit correctly deducted
  - Verify error handling for API failures

---

## Phase 4: Market Intelligence Module

- [ ] 12. Market Intelligence Module - 市场洞察能力

- [ ] 12.1 Replace market intel stub with real implementation
  - Create `ai-orchestrator/app/nodes/market_intel_node.py` replacing `market_intel_stub.py`
  - Implement `market_intel_node` function with real MCP tool calls
  - Add action handlers: analyze_competitor, get_trends, generate_strategy
  - Estimate credit cost based on analysis depth
  - Check credit via MCP before execution
  - Deduct credit after successful execution
  - _Requirements: 需求 7.1, 7.2, 7.3_

- [ ] 12.2 Implement competitor analysis
  - Call MCP `analyze_competitor` tool with competitor URL or name
  - Fetch competitor ad data (if available via ad library APIs)
  - Use Gemini 2.5 Pro to analyze competitor creative styles
  - Compare metrics: estimated spend, ad frequency, creative themes
  - Generate competitive positioning insights
  - Return structured data with visualizations
  - _Requirements: 需求 7.1_

- [ ] 12.3 Implement trend analysis
  - Call MCP `get_trends` tool for market trends
  - Analyze industry trends from available data sources
  - Use Gemini to identify emerging patterns
  - Generate trend reports with confidence scores
  - Suggest timing for campaigns based on trends
  - _Requirements: 需求 7.2_

- [ ] 12.4 Implement strategy generation
  - Call MCP `generate_strategy` tool or implement with Gemini
  - Create strategy prompt template in `app/prompts/strategy_generation.py`
  - Input: product info, target audience, budget, goals
  - Output: recommended platforms, audience targeting, creative direction, budget allocation
  - Generate multiple strategy options with pros/cons
  - _Requirements: 需求 7.3_

- [ ] 12.5 Return structured analysis data
  - Define response schema for market intelligence results
  - Include charts data for frontend visualization
  - Add confidence scores for AI-generated insights
  - Include data sources and timestamps
  - _Requirements: 需求 7.4_

- [ ] 12.6 Handle analysis failures
  - Detect when external data sources are unavailable
  - Provide partial results when possible
  - Return clear error messages with suggested alternatives
  - _Requirements: 需求 7.5_

- [ ]* 12.7 Write integration tests for Market Intelligence
  - Test competitor analysis with mock competitor data
  - Test trend analysis with historical data
  - Test strategy generation with various inputs
  - Test error handling for data source failures
  - Test credit check and deduction flow
  - _Requirements: Testing_

- [ ] 12.8 Checkpoint - Verify Market Intelligence Module
  - Test "分析竞品" intent recognition and routing
  - Verify competitor analysis generates insights
  - Verify trend analysis identifies patterns
  - Verify strategy generation provides actionable recommendations
  - Verify credit correctly deducted
  - Verify error handling for external API failures

---

## Phase 5: Landing Page Module

- [ ] 13. Landing Page Module - 落地页生成功能

- [ ] 13.1 Replace landing page stub with real implementation
  - Create `ai-orchestrator/app/nodes/landing_page_node.py` replacing `landing_page_stub.py`
  - Implement `landing_page_node` function with real MCP tool calls
  - Add action handlers: create_landing_page, translate_page, ab_test
  - Estimate credit cost based on page complexity and features
  - Check credit via MCP before execution
  - Deduct credit after successful execution
  - _Requirements: 需求 9.1, 9.2, 9.3_

- [ ] 13.2 Implement page generation
  - Call MCP `create_landing_page` tool with page parameters
  - Input: product info, template style, sections (hero, features, testimonials, CTA)
  - Use Gemini to generate copy and layout suggestions
  - Generate HTML/CSS or use template system
  - Upload assets to S3 via MCP
  - Return preview URL and edit link
  - _Requirements: 需求 9.1_

- [ ] 13.3 Implement multi-language support
  - Call MCP `translate_page` tool with target languages
  - Use Gemini for high-quality translation
  - Preserve formatting and layout across languages
  - Support common languages: EN, ZH, ES, FR, DE, JA, KO
  - Generate language-specific URLs
  - _Requirements: 需求 9.2_

- [ ] 13.4 Implement A/B testing setup
  - Call MCP `ab_test` tool to create test variants
  - Support testing: headlines, CTAs, images, layouts
  - Configure traffic split (50/50, 70/30, etc.)
  - Set up tracking for conversion metrics
  - Return test configuration and monitoring dashboard link
  - _Requirements: 需求 9.3_

- [ ] 13.5 Return landing page URL
  - Generate unique URL for each landing page
  - Support custom domain mapping (if configured)
  - Return both preview and published URLs
  - Include QR code for mobile testing
  - _Requirements: 需求 9.4_

- [ ] 13.6 Handle generation failures
  - Detect template rendering errors
  - Handle asset upload failures with retry
  - Provide partial results when possible
  - Return clear error messages with troubleshooting steps
  - Refund credit on complete failure
  - _Requirements: 需求 9.5_

- [ ]* 13.7 Write integration tests for Landing Page
  - Test page generation with various templates
  - Test multi-language translation
  - Test A/B test setup
  - Test asset upload to S3
  - Test error handling and credit refund
  - _Requirements: Testing_

- [ ] 13.8 Checkpoint - Verify Landing Page Module
  - Test "创建落地页" intent recognition and routing
  - Verify page generation creates valid HTML
  - Verify translation produces correct multi-language pages
  - Verify A/B test setup configures variants correctly
  - Verify URLs are accessible
  - Verify credit correctly deducted
  - Verify error handling and refund on failure

---

## Phase 6: Campaign Automation Module

- [ ] 14. Campaign Automation Module - 广告创建和管理功能

- [ ] 14.1 Replace ad engine stub with real implementation
  - Create `ai-orchestrator/app/nodes/ad_engine_node.py` replacing `ad_engine_stub.py`
  - Implement `ad_engine_node` function with real MCP tool calls
  - Add action handlers: create_campaign, optimize_budget, apply_rules, pause_campaign, update_budget
  - Estimate credit cost based on operation type
  - Check credit via MCP before execution
  - Deduct credit after successful execution
  - _Requirements: 需求 10.1, 10.2, 10.3_

- [ ] 14.2 Implement campaign creation
  - Call MCP `create_campaign` tool with campaign parameters
  - Input: creative_ids, budget, target_roas/cpa, audience, platforms
  - Validate all required parameters before API call
  - Support multi-platform campaigns (Meta, TikTok)
  - Handle platform-specific requirements and formats
  - Return Campaign ID and status
  - _Requirements: 需求 10.1, 需求 14.1-14.5_

- [ ] 14.3 Implement budget optimization
  - Call MCP `optimize_budget` tool with optimization parameters
  - Analyze current performance data
  - Use AI to recommend budget reallocation
  - Support strategies: maximize_roas, minimize_cpa, maximize_reach
  - Apply changes with user confirmation (high-risk check)
  - Return optimization results and projected impact
  - _Requirements: 需求 10.2, 需求 14.2_

- [ ] 14.4 Implement rule engine
  - Call MCP `apply_rules` tool with rule definitions
  - Support rule types: auto_pause (CPA > threshold), auto_scale (ROAS > target), alerts
  - Validate rule syntax and parameters
  - Schedule rule execution (hourly, daily)
  - Return rule status and execution history
  - _Requirements: 需求 10.3_

- [ ] 14.5 Implement campaign management operations
  - Implement pause_campaign: pause single or multiple campaigns
  - Implement update_budget: modify daily/lifetime budget
  - Implement update_targeting: modify audience settings
  - All high-risk operations require confirmation (需求 14.5)
  - Log all operations for audit trail
  - _Requirements: 需求 14.2, 14.4, 14.5_

- [ ] 14.6 Return Campaign ID and status
  - Return structured response with campaign details
  - Include platform-specific IDs (Meta Campaign ID, TikTok Campaign ID)
  - Include status (pending_review, active, paused, rejected)
  - Include estimated delivery and reach
  - _Requirements: 需求 10.4_

- [ ] 14.7 Handle creation failures
  - Detect platform API errors (validation, policy, rate limit)
  - Parse error messages and provide user-friendly explanations
  - Suggest fixes for common issues (budget too low, targeting too narrow)
  - Refund credit on complete failure
  - _Requirements: 需求 10.5_

- [ ]* 14.8 Write integration tests for Campaign Automation
  - Test campaign creation with various parameters
  - Test budget optimization recommendations
  - Test rule engine with different rule types
  - Test campaign management operations
  - Test high-risk operation confirmation flow
  - Test error handling and credit refund
  - _Requirements: Testing_

- [ ] 14.9 Checkpoint - Verify Campaign Automation Module
  - Test "创建广告" intent recognition and routing
  - Verify campaign creation returns valid Campaign ID
  - Verify budget optimization generates recommendations
  - Verify rule engine applies rules correctly
  - Verify high-risk operations require confirmation
  - Verify credit correctly deducted
  - Verify error handling and refund on failure

---

## Phase 7: Final Integration and Verification

- [ ] 15. Final Integration

- [ ] 15.1 Multi-module workflow testing
  - Test complex workflows: "生成素材并创建广告"
  - Verify creative → campaign flow works end-to-end
  - Test "分析表现并优化预算" workflow
  - Verify reporting → campaign automation flow
  - Test context passing between modules
  - _Requirements: 需求 3.1-3.5, 需求 4.1-4.5_

- [ ] 15.2 Conversation context integration
  - Test "用刚才的素材创建广告" context resolution
  - Test "给表现最好的广告加 20% 预算" context + action
  - Verify context persists across module calls
  - Test context compression for long conversations
  - _Requirements: 需求 5.2, 5.3, 需求 14.2_

- [ ] 15.3 Error recovery testing
  - Test partial failure scenarios (2/3 modules succeed)
  - Verify partial results are returned
  - Test retry from failure point
  - Verify credit refund on partial failure
  - _Requirements: 需求 12.4, 12.5_

- [ ] 15.4 Performance optimization
  - Measure end-to-end latency for each module
  - Optimize slow paths (caching, parallel execution)
  - Verify streaming response < 2 seconds
  - Test concurrent request handling
  - _Requirements: 需求 13.1-13.5_

- [ ] 15.5 Final acceptance testing
  - ✅ All 5 functional modules working (需求 6-10)
  - ✅ Intent recognition accuracy > 90% (需求 2.1-2.5)
  - ✅ Multi-step workflows complete successfully (需求 3, 4)
  - ✅ Context resolution works correctly (需求 5)
  - ✅ Error handling graceful and user-friendly (需求 12)
  - ✅ Performance meets requirements (需求 13)
  - ✅ High-risk operations require confirmation (需求 14.5)
  - ✅ All error codes match INTERFACES.md

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
