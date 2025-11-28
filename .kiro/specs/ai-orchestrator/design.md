# AI Orchestrator 设计文档

## 概述（Overview）

AI Orchestrator 是 AAE 系统的核心智能助手，提供统一的对话入口。用户通过自然语言与系统交互，Orchestrator 负责理解意图、协调功能模块、管理对话上下文，并返回统一的响应。

本设计基于 LangGraph 框架实现，采用状态机模式管理对话流程，通过 MCP 协议与 Web Platform 通信，支持流式响应和人工介入。

---

## 架构设计（Architecture）

### 系统分层

```
┌─────────────────────────────────────────────────────────┐
│                   AI Orchestrator                       │
│                                                         │
│  ┌───────────────────────────────────────────────┐    │
│  │         FastAPI Application Layer             │    │
│  │  - WebSocket Handler                          │    │
│  │  - HTTP Streaming Handler                     │    │
│  │  - Health Check Endpoints                     │    │
│  └───────────────────────────────────────────────┘    │
│                        │                               │
│  ┌───────────────────────────────────────────────┐    │
│  │         LangGraph Agent Layer                 │    │
│  │  - State Machine (StateGraph)                 │    │
│  │  - Router Node (Intent Recognition)           │    │
│  │  - Functional Module Nodes                    │    │
│  │  - Confirmation Node (Human-in-the-loop)      │    │
│  │  - Response Generator Node                    │    │
│  └───────────────────────────────────────────────┘    │
│                        │                               │
│  ┌───────────────────────────────────────────────┐    │
│  │         Integration Layer                     │    │
│  │  - MCP Client (Web Platform)                  │    │
│  │  - LLM Client (Gemini)                        │    │
│  │  - Redis Client (State Persistence)           │    │
│  └───────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### 核心组件

1. **FastAPI Application**: 处理 WebSocket 和 HTTP 请求
2. **LangGraph State Machine**: 管理对话流程和状态转换
3. **Intent Router**: 识别用户意图并路由到相应模块
4. **Functional Modules**: 5 个能力模块（初期为 stub）
5. **MCP Client**: 与 Web Platform 通信
6. **State Persistence**: Redis 存储对话状态和检查点

---

## 组件与接口（Components and Interfaces）

### 1. FastAPI Application

#### HTTP Streaming Handler (Primary Interface)

```python
@app.post("/chat")
async def chat_stream(
    request: ChatRequest,
    authorization: str = Header(...)
) -> StreamingResponse:
    """
    HTTP streaming endpoint compatible with Vercel AI SDK.
    Used by web-platform's /api/v1/chat and /ws/chat endpoints.
    
    Web-platform forwards requests here via HTTP POST, not WebSocket.
    """
    # 1. Validate service token
    if not await validate_service_token(authorization):
        raise HTTPException(status_code=401, detail="Invalid service token")
    
    # 2. Execute LangGraph
    # 3. Stream response in SSE format (text/event-stream)
    
async def validate_service_token(authorization: str) -> bool:
    """Validate Bearer token from web-platform."""
    if not authorization or not authorization.startswith("Bearer "):
        return False
    
    token = authorization[7:]
    expected_token = settings.web_platform_service_token
    
    return token == expected_token
```

**重要**: AI Orchestrator 不直接处理 WebSocket 连接。Web Platform 的 WebSocket handler 会将消息转发到这个 HTTP endpoint。

### 2. LangGraph State Machine

#### State Definition

```python
from typing import TypedDict, List, Optional, Annotated
from langgraph.graph import StateGraph
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    """AI Orchestrator state definition."""
    
    # Conversation messages (auto-append with operator.add)
    messages: Annotated[List[BaseMessage], operator.add]
    
    # User and session info
    user_id: str
    session_id: str
    
    # Intent recognition result
    current_intent: Optional[str]
    extracted_params: Optional[dict]
    
    # Pending actions to execute
    pending_actions: List[dict]
    
    # Completed results from modules
    completed_results: List[dict]
    
    # Confirmation state
    requires_confirmation: bool
    user_confirmed: Optional[bool]
    
    # Credit check
    credit_checked: bool
    credit_sufficient: bool
    estimated_cost: Optional[int]
    
    # Error handling
    error: Optional[dict]
    retry_count: int
```

#### Graph Structure

```python
def build_agent_graph() -> StateGraph:
    """Build the AI Orchestrator state graph."""
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("credit_check", credit_check_node)
    workflow.add_node("creative_stub", creative_stub_node)
    workflow.add_node("reporting_stub", reporting_stub_node)
    workflow.add_node("market_intel_stub", market_intel_stub_node)
    workflow.add_node("landing_page_stub", landing_page_stub_node)
    workflow.add_node("ad_engine_stub", ad_engine_stub_node)
    workflow.add_node("human_confirmation", human_confirmation_node)
    workflow.add_node("respond", respond_node)
    workflow.add_node("error_handler", error_handler_node)
    
    # Set entry point
    workflow.set_entry_point("router")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "credit_check": "credit_check",
            "error": "error_handler",
        }
    )
    
    workflow.add_conditional_edges(
        "credit_check",
        check_credit_result,
        {
            "sufficient": route_to_module,
            "insufficient": "respond",
        }
    )
    
    # Module nodes → confirmation check
    for module in ["creative_stub", "reporting_stub", "market_intel_stub",
                   "landing_page_stub", "ad_engine_stub"]:
        workflow.add_conditional_edges(
            module,
            should_confirm,
            {
                "confirm": "human_confirmation",
                "execute": "respond",
            }
        )
    
    # Confirmation → END (wait for user input)
    workflow.add_edge("human_confirmation", END)
    
    # Response → END
    workflow.add_edge("respond", END)
    workflow.add_edge("error_handler", END)
    
    # Compile with checkpointer
    from langgraph.checkpoint.memory import MemorySaver
    memory = MemorySaver()
    
    return workflow.compile(checkpointer=memory)
```

### 3. Intent Router Node

```python
async def router_node(state: AgentState) -> AgentState:
    """
    Recognize user intent and extract parameters.
    Uses Gemini 2.5 Pro with structured output.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", INTENT_RECOGNITION_PROMPT),
        ("human", "{input}")
    ])
    
    # Use structured output for reliable parsing
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0.1
    )
    
    structured_llm = llm.with_structured_output(IntentSchema)
    
    last_message = state["messages"][-1].content
    result = await structured_llm.ainvoke(
        prompt.format(input=last_message)
    )
    
    return {
        "current_intent": result.intent,
        "extracted_params": result.parameters,
        "pending_actions": result.actions,
        "estimated_cost": result.estimated_cost,
    }
```

### 4. Functional Module with Credit Check

**重要设计变更**: Credit check 不是独立节点，而是在每个功能模块内部执行。

```python
async def creative_stub_node(state: AgentState) -> AgentState:
    """
    Ad Creative stub with credit check.
    Phase 1: Returns mock data
    Phase 2: Will be replaced with real implementation
    """
    
    action = state["pending_actions"][0]
    
    # Step 1: Estimate cost
    estimated_cost = estimate_creative_cost(action["params"])
    
    # Step 2: Check credit
    try:
        credit_check = await mcp_client.call_tool(
            "check_credit",
            {
                "user_id": state["user_id"],
                "estimated_credits": estimated_cost,
                "operation_type": "generate_creative",
            }
        )
        
        if not credit_check["allowed"]:
            return {
                "error": {
                    "code": "6011",
                    "type": "INSUFFICIENT_CREDITS",
                    "message": "Credit 余额不足",
                    "details": {
                        "required": estimated_cost,
                        "available": credit_check["current_balance"],
                    }
                }
            }
    
    except Exception as e:
        logger.error(f"Credit check failed: {e}")
        return {
            "error": {
                "code": "6012",
                "message": "Credit check failed",
            }
        }
    
    # Step 3: Execute operation (mock in Phase 1)
    await asyncio.sleep(2)  # Simulate processing
    
    mock_result = {
        "status": "success",
        "creative_ids": ["mock_creative_1", "mock_creative_2"],
        "message": "✅ 已生成 10 张素材（模拟数据）",
        "mock": True,
        "cost": estimated_cost,
    }
    
    # Step 4: Deduct credit (even for mock data, to test the flow)
    try:
        await mcp_client.call_tool(
            "deduct_credit",
            {
                "user_id": state["user_id"],
                "credits": estimated_cost,
                "operation_type": "generate_creative",
                "operation_id": f"mock_{uuid.uuid4()}",
            }
        )
    except Exception as e:
        logger.error(f"Credit deduction failed: {e}")
        # Continue anyway in Phase 1
    
    return {
        "completed_results": [mock_result]
    }

def estimate_creative_cost(params: dict) -> int:
    """Estimate credit cost for creative generation."""
    count = params.get("count", 10)
    # Assume 0.5 credits per image
    return int(count * 0.5)
```

### 5. Other Stub Module Nodes

```python
async def reporting_stub_node(state: AgentState) -> AgentState:
    """Ad Performance stub with credit check."""
    # Similar structure to creative_stub_node
    # 1. Estimate cost
    # 2. Check credit
    # 3. Execute (mock)
    # 4. Deduct credit
    pass

async def market_intel_stub_node(state: AgentState) -> AgentState:
    """Market Insights stub with credit check."""
    pass

async def landing_page_stub_node(state: AgentState) -> AgentState:
    """Landing Page stub with credit check."""
    pass

async def ad_engine_stub_node(state: AgentState) -> AgentState:
    """Campaign Automation stub with credit check."""
    pass
```

**Phase 1 重点**: 所有 stub 模块都应该：
- ✅ 调用 MCP check_credit 和 deduct_credit
- ✅ 返回符合格式的 mock 数据
- ✅ 测试完整的错误处理流程
- ✅ 记录结构化日志

### 6. Conversation Persistence Node

```python
async def persist_conversation_node(state: AgentState) -> AgentState:
    """
    Persist conversation to Web Platform via MCP.
    Called after generating response.
    """
    
    try:
        await mcp_client.call_tool(
            "save_conversation",
            {
                "user_id": state["user_id"],
                "session_id": state["session_id"],
                "messages": [
                    {
                        "role": msg.type,
                        "content": msg.content,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                    for msg in state["messages"]
                ],
            }
        )
    except Exception as e:
        logger.error(f"Failed to persist conversation: {e}")
        # Don't fail the request if persistence fails
    
    return state
```

### 7. Response Generator Node

```python
async def respond_node(state: AgentState) -> AgentState:
    """
    Generate final response based on execution results.
    """
    
    # Check for errors
    if state.get("error"):
        return generate_error_response(state)
    
    # Check for insufficient credits
    if not state.get("credit_sufficient"):
        return generate_insufficient_credit_response(state)
    
    # Generate success response
    prompt = ChatPromptTemplate.from_messages([
        ("system", RESPONSE_GENERATION_PROMPT),
        ("human", "Results: {results}\n\nGenerate user-friendly response.")
    ])
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    
    response = await llm.ainvoke(
        prompt.format(
            results=json.dumps(state["completed_results"], ensure_ascii=False)
        )
    )
    
    return {
        "messages": [AIMessage(content=response.content)]
    }
```

---

## 前置条件（Prerequisites）

在开始 AI Orchestrator 开发前，Web Platform 必须完成：

1. ✅ **MCP Server 实现**: 所有 MCP 工具已实现并可调用
2. ✅ **Service Token 生成**: 生成 service-to-service 认证 token
3. ✅ **Conversation 数据模型**: 数据库中有 conversations 和 messages 表
4. ✅ **Credit 系统**: check_credit 和 deduct_credit 工具可用
5. ✅ **WebSocket 转发**: backend/app/api/v1/websocket.py 已实现消息转发

**验证方式**:
```bash
# 测试 MCP Server 可用性
curl -X POST http://localhost:8000/api/v1/mcp/tools/check_credit \
  -H "Authorization: Bearer ${SERVICE_TOKEN}" \
  -d '{"user_id": "test", "estimated_credits": 10}'
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

### Acceptence Criteria Testing Prework

#### 2.1 WHEN 用户说"生成素材" THEN AI Orchestrator SHALL 识别为 Ad Creative
Thoughts: 这是测试意图识别的准确性。我们可以生成随机的用户消息（包含"生成素材"的各种表达方式），然后验证识别结果是否正确。
Testable: yes - property

#### 2.2 WHEN 用户说"查看报表" THEN AI Orchestrator SHALL 识别为 Ad Performance
Thoughts: 同样是意图识别测试，可以用不同的表达方式测试。
Testable: yes - property

#### 3.3 WHEN 执行多个任务 THEN AI Orchestrator SHALL 按顺序调用功能模块
Thoughts: 这是测试多步骤任务的执行顺序。我们可以生成随机的多步骤任务，验证执行顺序是否符合依赖关系。
Testable: yes - property

#### 5.2 WHEN 用户说"用刚才的素材" THEN AI Orchestrator SHALL 从上下文中找到素材
Thoughts: 这是测试上下文引用解析。我们可以生成随机的对话历史，然后测试引用是否正确解析。
Testable: yes - property

#### 11.4 WHEN MCP 调用失败 THEN AI Orchestrator SHALL 重试 3 次
Thoughts: 这是测试重试机制。我们可以模拟 MCP 失败，验证重试次数。
Testable: yes - property

#### 12.5 WHEN 用户重试 THEN AI Orchestrator SHALL 从失败点继续
Thoughts: 这是测试幂等性和断点续传。重试应该产生相同的结果。
Testable: yes - property

#### 13.1 WHEN 用户发送消息 THEN AI Orchestrator SHALL 在 2 秒内开始响应
Thoughts: 这是性能测试，不是功能正确性测试。
Testable: no

#### 14.5.4 WHEN 用户确认操作 THEN AI Orchestrator SHALL 执行并记录日志
Thoughts: 这是测试确认机制。我们可以生成随机的高风险操作，验证是否要求确认。
Testable: yes - property

### Property Reflection

审查所有可测试的属性，消除冗余：
- Property 1 和 2 都是意图识别，可以合并为一个通用属性
- Property 4 (重试机制) 和 Property 5 (幂等性) 是相关的，但测试不同方面，保留两个

### Correctness Properties

#### Property 1: Intent Recognition Accuracy
*For any* user message requesting a specific operation (creative generation, report analysis, campaign creation, etc.), the router SHALL correctly identify the corresponding intent
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

#### Property 2: Multi-step Execution Order
*For any* multi-step task with dependencies, the orchestrator SHALL execute steps in dependency order (e.g., generate creative before create campaign)
**Validates: Requirements 3.3**

#### Property 3: Context Reference Resolution
*For any* user message containing context references (e.g., "use the previous creative"), the system SHALL correctly resolve the reference from conversation history
**Validates: Requirements 5.2, 5.3**

#### Property 4: MCP Retry Mechanism
*For any* MCP tool call that fails with a retryable error, the system SHALL retry exactly 3 times before reporting failure
**Validates: Requirements 11.4**

#### Property 5: Operation Idempotence
*For any* failed operation that is retried, the retry SHALL produce the same result as if executed once successfully
**Validates: Requirements 12.5**

#### Property 6: Confirmation for High-Risk Operations
*For any* high-risk operation (pause all, delete campaign, large budget change), the system SHALL require user confirmation before execution
**Validates: Requirements 14.5.1, 14.5.2, 14.5.3**

---

## 数据模型（Data Models）

### Intent Schema

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class IntentSchema(BaseModel):
    """Structured output for intent recognition."""
    
    intent: str = Field(
        description="Primary intent: generate_creative, analyze_report, "
                   "create_campaign, market_analysis, create_landing_page, "
                   "multi_step, general_query"
    )
    
    confidence: float = Field(
        description="Confidence score 0-1",
        ge=0.0,
        le=1.0
    )
    
    parameters: dict = Field(
        description="Extracted parameters from user message",
        default_factory=dict
    )
    
    actions: List[dict] = Field(
        description="List of actions to execute",
        default_factory=list
    )
    
    estimated_cost: Optional[int] = Field(
        description="Estimated credit cost",
        default=None
    )
    
    requires_confirmation: bool = Field(
        description="Whether this operation requires user confirmation",
        default=False
    )
```

### MCP Request/Response Models

```python
class MCPToolRequest(BaseModel):
    """MCP tool call request."""
    tool_name: str
    parameters: dict
    user_id: str
    session_id: str

class MCPToolResponse(BaseModel):
    """MCP tool call response."""
    status: str
    data: Optional[dict] = None
    error: Optional[dict] = None
```

---

## 错误处理（Error Handling）

### Error Handling Strategy

```python
class ErrorHandler:
    """Centralized error handling."""
    
    @staticmethod
    async def handle_error(
        error: Exception,
        state: AgentState,
        context: str
    ) -> AgentState:
        """Handle errors and return appropriate state update."""
        
        if isinstance(error, MCPConnectionError):
            return {
                "error": {
                    "code": "3000",
                    "type": "MCP_CONNECTION_FAILED",
                    "message": "无法连接到数据服务，请稍后重试",
                    "retryable": True,
                }
            }
        
        elif isinstance(error, InsufficientCreditsError):
            return {
                "error": {
                    "code": "6011",
                    "type": "INSUFFICIENT_CREDITS",
                    "message": "Credit 余额不足，请充值后继续使用",
                    "action_url": "/billing/recharge",
                }
            }
        
        elif isinstance(error, AIModelTimeoutError):
            return {
                "error": {
                    "code": "4001",
                    "type": "AI_MODEL_FAILED",
                    "message": "AI 服务暂时不可用，请稍后重试",
                    "retryable": True,
                }
            }
        
        else:
            logger.error(f"Unexpected error in {context}: {error}", exc_info=True)
            return {
                "error": {
                    "code": "1000",
                    "type": "UNKNOWN_ERROR",
                    "message": "系统错误，请联系客服",
                }
            }
```

### Retry Strategy

```python
async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    backoff_factor: float = 2.0
) -> Any:
    """Exponential backoff retry."""
    
    for attempt in range(max_retries):
        try:
            return await func()
        except RetryableError as e:
            if attempt == max_retries - 1:
                raise
            
            wait_time = backoff_factor ** attempt
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {wait_time}s")
            await asyncio.sleep(wait_time)
```

---

## 测试策略（Testing Strategy）

### Unit Tests

```python
# tests/test_intent_router.py
async def test_intent_recognition_generate_creative():
    """Test intent recognition for creative generation."""
    state = {
        "messages": [HumanMessage(content="帮我生成 10 张广告图片")],
        "user_id": "test_user",
        "session_id": "test_session",
    }
    
    result = await router_node(state)
    
    assert result["current_intent"] == "generate_creative"
    assert result["extracted_params"]["count"] == 10
    assert result["estimated_cost"] > 0

# tests/test_credit_check.py
async def test_credit_check_sufficient():
    """Test credit check with sufficient balance."""
    state = {
        "user_id": "test_user",
        "estimated_cost": 10,
        "current_intent": "generate_creative",
    }
    
    with patch_mcp_client({"allowed": True}):
        result = await credit_check_node(state)
    
    assert result["credit_sufficient"] is True
```

### Integration Tests

```python
# tests/test_integration.py
async def test_end_to_end_creative_generation():
    """Test complete flow from user message to response."""
    
    # Mock MCP client
    with patch_mcp_client():
        # Execute graph
        config = {"configurable": {"thread_id": "test_session"}}
        
        initial_state = {
            "messages": [HumanMessage(content="生成素材")],
            "user_id": "test_user",
            "session_id": "test_session",
        }
        
        result = await agent.ainvoke(initial_state, config)
        
        # Verify response
        assert len(result["messages"]) > 1
        assert "素材" in result["messages"][-1].content
```

### Mock MCP Client

```python
class MockMCPClient:
    """Mock MCP client for testing."""
    
    async def call_tool(self, tool_name: str, params: dict) -> dict:
        """Return mock data based on tool name."""
        
        if tool_name == "check_credit":
            return {"allowed": True, "current_balance": 1000}
        
        elif tool_name == "create_creative":
            return {
                "creative_id": "mock_123",
                "url": "https://mock.com/creative.jpg",
            }
        
        # ... other tools
```

---

## 部署架构（Deployment Architecture）

### Docker Compose Setup

```yaml
# docker-compose.yml
services:
  ai-orchestrator:
    build: ./ai-orchestrator
    ports:
      - "8001:8001"
    environment:
      - WEB_PLATFORM_URL=http://web-platform:8000
      - REDIS_URL=redis://redis:6379/3
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      - redis
      - web-platform
    
  web-platform:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - AI_ORCHESTRATOR_URL=http://ai-orchestrator:8001
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Environment Variables

```bash
# .env
GEMINI_API_KEY=your_api_key
WEB_PLATFORM_URL=http://localhost:8000
WEB_PLATFORM_MCP_TOKEN=service_token_here
REDIS_URL=redis://localhost:6379/3
LOG_LEVEL=INFO
```

---

## 性能优化（Performance Optimization）

### 1. Streaming Response

```python
async def stream_graph_execution(
    agent: CompiledGraph,
    initial_state: dict,
    config: dict
) -> AsyncGenerator[str, None]:
    """Stream graph execution events."""
    
    async for event in agent.astream_events(
        initial_state,
        config,
        version="v2"
    ):
        if event["event"] == "on_chat_model_stream":
            # Stream LLM tokens
            content = event["data"]["chunk"].content
            if content:
                yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
        
        elif event["event"] == "on_tool_end":
            # Notify tool completion
            yield f"data: {json.dumps({'type': 'tool_complete', 'tool': event['name']})}\n\n"
```

### 2. Caching Strategy

```python
from functools import lru_cache
from aiocache import cached

@cached(ttl=300)  # 5 minutes
async def get_user_context(user_id: str) -> dict:
    """Cache user context to reduce MCP calls."""
    return await mcp_client.call_tool("get_user_info", {"user_id": user_id})
```

### 3. Parallel Execution

```python
async def execute_independent_actions(actions: List[dict]) -> List[dict]:
    """Execute independent actions in parallel."""
    
    tasks = [
        execute_action(action)
        for action in actions
        if not action.get("depends_on")
    ]
    
    return await asyncio.gather(*tasks)
```

---

## 监控与日志（Monitoring and Logging）

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

async def log_operation(
    operation: str,
    user_id: str,
    session_id: str,
    **kwargs
):
    """Log operation with structured data."""
    
    logger.info(
        operation,
        user_id=user_id,
        session_id=session_id,
        **kwargs
    )
```

### Metrics Collection

```python
from prometheus_client import Counter, Histogram

# Define metrics
intent_recognition_counter = Counter(
    "intent_recognition_total",
    "Total intent recognitions",
    ["intent", "status"]
)

llm_latency_histogram = Histogram(
    "llm_call_duration_seconds",
    "LLM call duration"
)

# Use in code
with llm_latency_histogram.time():
    response = await llm.ainvoke(prompt)

intent_recognition_counter.labels(
    intent=result["intent"],
    status="success"
).inc()
```

### Health Check

```python
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    
    checks = {
        "redis": await check_redis_connection(),
        "mcp": await check_mcp_connection(),
        "llm": await check_llm_availability(),
    }
    
    all_healthy = all(checks.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.now(UTC).isoformat(),
    }
```

---

## 安全考虑（Security Considerations）

### 1. Service-to-Service Authentication

```python
async def validate_service_token(token: str) -> bool:
    """Validate service token from web-platform."""
    
    try:
        payload = jwt.decode(
            token,
            settings.service_secret_key,
            algorithms=["HS256"]
        )
        
        return payload.get("service") == "web-platform"
    
    except jwt.InvalidTokenError:
        return False
```

### 2. Input Validation

```python
from pydantic import BaseModel, validator

class ChatRequest(BaseModel):
    """Validated chat request."""
    
    messages: List[dict]
    user_id: str
    session_id: str
    
    @validator("messages")
    def validate_messages(cls, v):
        if len(v) > 100:
            raise ValueError("Too many messages")
        return v
    
    @validator("user_id")
    def validate_user_id(cls, v):
        if not v or len(v) > 50:
            raise ValueError("Invalid user_id")
        return v
```

### 3. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/chat")
@limiter.limit("10/minute")
async def chat_endpoint(request: Request):
    """Rate-limited chat endpoint."""
    pass
```

---

## 开发阶段（Development Phases）

### Phase 1: 核心框架（Week 3）

**目标**: 建立基础架构，所有功能模块返回 mock 数据

**核心任务**:
- FastAPI application setup
- LangGraph state machine implementation
- Intent router with Gemini integration
- 5 个 stub functional modules (with credit check)
- MCP client implementation
- HTTP streaming (SSE format)
- Service-to-service authentication
- Conversation persistence via MCP
- Structured logging and error handling

**验收标准**:
- ✅ 用户可以通过 web-platform 发送消息并收到 mock 响应
- ✅ 意图识别准确率 > 80% (测试 20+ 样本)
- ✅ HTTP streaming 延迟 < 2 秒
- ✅ Credit check 和 deduct 正确调用
- ✅ 对话历史正确持久化到 Web Platform
- ✅ 所有错误码符合 INTERFACES.md 定义

### Phase 2: Ad Creative 实现（Week 4）

**目标**: 实现真实的素材生成功能

- Replace creative_stub with real implementation
- Integrate Gemini Imagen 3
- Credit check and deduction
- File upload to S3 via MCP
- Error handling and retry

**验收标准**:
- 可以生成真实的广告图片
- Credit 正确扣减
- 生成失败时正确退款

### Phase 3-6: 其他功能模块

逐步实现其他 4 个功能模块，每个模块 1 周时间。

---

## 配置管理（Configuration Management）

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """AI Orchestrator settings."""
    
    # Application
    app_name: str = "AI Orchestrator"
    environment: str = "development"
    
    # Web Platform
    web_platform_url: str = "http://localhost:8000"
    web_platform_mcp_token: str
    
    # Redis
    redis_url: str = "redis://localhost:6379/3"
    
    # Gemini
    gemini_api_key: str
    gemini_model_chat: str = "gemini-2.5-pro"
    gemini_model_fast: str = "gemini-2.5-flash"
    
    # Performance
    max_concurrent_requests: int = 100
    request_timeout: int = 60
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
```

---

## 设计决策总结（Design Decisions Summary）

### 关键决策

1. **HTTP Streaming vs WebSocket**: 
   - 选择 HTTP streaming (SSE)
   - 原因：Web Platform 已经处理 WebSocket，AI Orchestrator 只需提供 HTTP endpoint
   - 好处：简化架构，减少连接管理复杂度

2. **Credit Check 位置**:
   - 在每个功能模块内部检查
   - 原因：不同操作成本不同，模块最清楚自己的成本
   - 好处：更灵活，支持动态定价

3. **Stub 模块策略**:
   - Phase 1 所有模块都是 stub，但调用真实的 MCP 工具
   - 原因：测试完整的集成流程
   - 好处：发现集成问题，验证接口设计

4. **LangGraph Checkpointer**:
   - 使用 MemorySaver (内存)
   - 原因：Phase 1 简化实现，对话历史通过 MCP 持久化
   - 未来：可以切换到 Redis checkpointer

5. **错误处理策略**:
   - 统一的 ErrorHandler 类
   - 映射到 INTERFACES.md 定义的错误码
   - 指数退避重试
   - 原因：保持与 Web Platform 的错误处理一致性

---

## 接下来的步骤

1. **Review this design**: 请确认设计是否满足需求
2. **Create tasks.md**: 将设计分解为具体的实现任务
3. **Setup project structure**: 创建项目目录和基础文件
4. **Implement Phase 1**: 开始核心框架开发

---

## 已知限制与未来改进（Known Limitations & Future Improvements）

### Phase 1 限制

1. **No Real AI Capabilities**: 所有功能模块返回 mock 数据
2. **Simple Intent Recognition**: 基于 Gemini 的简单 prompt，未来可以 fine-tune
3. **Memory-based Checkpointer**: 重启后丢失状态，未来切换到 Redis
4. **No Rate Limiting**: Phase 1 不实现，依赖 Web Platform 的 rate limiting
5. **No Observability**: 基础日志，未来添加 Prometheus metrics

### 未来改进

1. **Fine-tuned Intent Model**: 收集数据后 fine-tune 意图识别模型
2. **Redis Checkpointer**: 支持分布式部署和状态持久化
3. **Advanced Orchestration**: 支持更复杂的多步骤任务编排
4. **Personalization**: 基于用户历史行为个性化响应
5. **Multi-language Support**: 支持多语言对话
