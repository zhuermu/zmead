# 设计文档 - AI Orchestrator 架构统一

## 概述（Overview）

本设计文档描述如何将 AI Orchestrator 从双架构（v2 + v3）统一为单一的 v3 架构。v3 架构采用 **Agents-as-Tools** 模式，利用 Gemini 的 Function Calling 能力简化整体流程。

统一后的架构将：
- 删除 v2 的 6 节点复杂流程
- 保留 v3 的 2 节点简化流程
- 统一 API 端点为 `/api/v1/chat`
- 减少代码量约 40%
- 提升可维护性和扩展性

---

## 架构设计（Architecture）

### 统一后的架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI Orchestrator (v3 Only)                    │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   FastAPI Application                      │  │
│  │  - POST /api/v1/chat (streaming SSE)                      │  │
│  │  - POST /api/v1/chat/sync (non-streaming)                 │  │
│  │  - GET /health, /ready                                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │                   LangGraph (简化)                         │  │
│  │                                                            │  │
│  │    [START] → orchestrator → persist → [END]               │  │
│  │                                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │                   Orchestrator                             │  │
│  │                                                            │  │
│  │  Gemini 3 Pro + Function Calling                          │  │
│  │  ├── 意图理解                                              │  │
│  │  ├── 调用 Sub-Agents                                       │  │
│  │  └── 生成响应                                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │                   Sub-Agents (Function Tools)              │  │
│  │                                                            │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐         │  │
│  │  │ creative    │ │ performance │ │ market      │         │  │
│  │  │ _agent      │ │ _agent      │ │ _agent      │         │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘         │  │
│  │                                                            │  │
│  │  ┌─────────────┐ ┌─────────────┐                          │  │
│  │  │ landing     │ │ campaign    │                          │  │
│  │  │ _page_agent │ │ _agent      │                          │  │
│  │  └─────────────┘ └─────────────┘                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │                   Integration Layer                        │  │
│  │  - MCP Client (Web Platform)                              │  │
│  │  - Gemini Client                                          │  │
│  │  - Redis Client                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```


### v2 vs v3 对比

| 方面 | v2 (删除) | v3 (保留) |
|------|-----------|-----------|
| Graph 节点数 | 6 个 | 2 个 |
| 路由逻辑 | 复杂条件边 + 多个路由函数 | Gemini Function Calling |
| 意图识别 | 独立 router 节点 | Orchestrator 内部 |
| 任务规划 | 独立 planner 节点 | Gemini 自动处理 |
| 执行器 | 独立 executor 节点 | Sub-Agents |
| 分析器 | 独立 analyzer 节点 | Sub-Agents 内部 |
| 代码复杂度 | 高（~2000 行） | 低（~500 行） |
| 扩展方式 | 修改 Graph + 路由 | 添加新 Agent |
| 调试难度 | 高（多节点跳转） | 低（线性流程） |

---

## 组件与接口（Components and Interfaces）

### 1. 统一的 Chat API

```python
# app/api/chat.py (合并 chat.py 和 chat_v3.py)

@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    _token: str = Depends(validate_service_token),
) -> StreamingResponse:
    """统一的 Chat 端点，支持 SSE 流式响应。
    
    使用 v3 架构：orchestrator → persist
    """
    orchestrator = get_orchestrator()
    
    async def generate():
        async for event in orchestrator.stream_message(
            user_id=request.user_id,
            session_id=request.session_id,
            message=request.messages[-1].content,
            conversation_history=request.messages[:-1],
        ):
            yield format_sse_event(event)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/sync")
async def chat_sync_endpoint(
    request: ChatRequest,
    _token: str = Depends(validate_service_token),
) -> ChatResponse:
    """同步 Chat 端点，返回完整响应。"""
    orchestrator = get_orchestrator()
    result = await orchestrator.process_message(
        user_id=request.user_id,
        session_id=request.session_id,
        message=request.messages[-1].content,
        conversation_history=request.messages[:-1],
    )
    
    return ChatResponse(
        response=result["response"],
        success=result["success"],
        session_id=request.session_id,
        error=result.get("error"),
        tool_results=result.get("tool_results"),
    )
```

### 2. 简化的 LangGraph

```python
# app/core/graph.py (原 graph_v3.py)

def build_agent_graph() -> CompiledStateGraph:
    """构建简化的 Agent Graph。
    
    Graph Structure:
        [START] → orchestrator → persist → [END]
    
    所有复杂逻辑在 orchestrator 节点内通过 Gemini function calling 处理。
    """
    workflow = StateGraph(AgentState)
    
    # 只有 2 个节点
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("persist", persist_node)
    
    # 简单的线性流程
    workflow.set_entry_point("orchestrator")
    workflow.add_edge("orchestrator", "persist")
    workflow.add_edge("persist", END)
    
    return workflow.compile(checkpointer=MemorySaver())
```

### 3. Orchestrator 核心

```python
# app/core/orchestrator.py

class Orchestrator:
    """主协调器，使用 Gemini Function Calling。"""
    
    def __init__(self):
        self.gemini_client = get_gemini_client()
        self.agent_registry = get_agent_registry()
    
    async def process_message(
        self,
        user_id: str,
        session_id: str,
        message: str,
        conversation_history: list | None = None,
    ) -> dict:
        """处理用户消息。
        
        流程：
        1. 构建 tools 列表（从注册的 Agents）
        2. 调用 Gemini with function calling
        3. 执行 Agent 调用
        4. 返回结果
        """
        # 1. 构建 tools
        tools = [agent.to_tool() for agent in self.agent_registry.list_agents()]
        
        # 2. 构建消息
        messages = self._build_messages(message, conversation_history)
        
        # 3. 调用 Gemini
        response = await self.gemini_client.chat_with_tools(
            messages=messages,
            tools=tools,
        )
        
        # 4. 处理 function calls
        tool_results = []
        if response.function_calls:
            for call in response.function_calls:
                agent = self.agent_registry.get(call.name)
                result = await agent.execute(
                    action=call.args.get("action"),
                    params=call.args,
                    context=AgentContext(
                        user_id=user_id,
                        session_id=session_id,
                    ),
                )
                tool_results.append(result)
        
        # 5. 返回结果
        return {
            "response": response.text,
            "success": True,
            "tool_results": tool_results,
        }
    
    async def stream_message(self, ...):
        """流式处理消息。"""
        # Similar to process_message but yields events
        pass
```


### 4. Sub-Agent 接口

```python
# app/agents/base.py

class BaseAgent(ABC):
    """Sub-Agent 基类。"""
    
    name: str
    description: str
    
    @abstractmethod
    async def execute(
        self,
        action: str,
        params: dict,
        context: AgentContext,
    ) -> AgentResult:
        """执行 Agent 操作。
        
        Args:
            action: 操作类型（如 "generate_image", "analyze_report"）
            params: 操作参数
            context: 执行上下文（user_id, session_id 等）
        
        Returns:
            AgentResult 包含执行结果
        """
        pass
    
    def to_tool(self) -> dict:
        """转换为 Gemini Function Tool 格式。
        
        Returns:
            Tool definition for Gemini function calling
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.get_parameters_schema(),
                "required": self.get_required_parameters(),
            },
        }
    
    @abstractmethod
    def get_parameters_schema(self) -> dict:
        """返回参数 schema。"""
        pass
    
    def get_required_parameters(self) -> list[str]:
        """返回必需参数列表。"""
        return ["action"]
```

---

## 文件结构变更

### 删除的文件（v2 专用）

```
app/core/
├── graph.py              # 删除（v2 实现，保留 graph_v3.py 并重命名）
└── routing.py            # 删除（v2 路由逻辑）

app/nodes/                # 删除整个目录
├── router.py
├── planner.py
├── executor.py
├── analyzer.py
├── respond.py
├── confirmation.py
├── creative_stub.py
├── reporting_stub.py
├── market_intel_stub.py
├── landing_page_stub.py
├── ad_engine_stub.py
├── creative_node.py
├── reporting_node.py
├── market_insights_node.py
├── landing_page_node.py
├── campaign_automation_node.py
└── persist.py            # 保留但移到 app/core/

app/api/
└── chat.py               # 删除（v2 API）

app/tools/                # 删除整个目录（v3 使用 agents/）

tests/
├── test_intent_recognition_property.py  # 删除（v2 router 测试）
├── test_execution_order_property.py     # 删除（v2 planner 测试）
├── test_context_resolution_property.py  # 删除（v2 特定）
└── test_checkpoint_verification.py      # 删除（v2 特定）
```

### 重命名的文件

```
app/core/graph_v3.py  →  app/core/graph.py
app/api/chat_v3.py    →  app/api/chat.py
```

### 新增/移动的文件

```
app/core/persist.py       # 从 app/nodes/persist.py 移动
```

### 保留的文件

```
app/
├── core/
│   ├── graph.py           # 重命名自 graph_v3.py
│   ├── orchestrator.py    # 保留
│   ├── persist.py         # 从 nodes/ 移动
│   ├── state.py           # 保留
│   ├── config.py          # 保留
│   ├── errors.py          # 保留
│   ├── retry.py           # 保留
│   ├── auth.py            # 保留
│   ├── logging.py         # 保留
│   ├── redis_client.py    # 保留
│   └── context.py         # 保留
├── agents/                # 保留整个目录
│   ├── base.py
│   ├── creative.py
│   ├── performance.py
│   ├── market.py
│   ├── landing_page.py
│   ├── campaign.py
│   ├── registry.py
│   └── setup.py
├── modules/               # 保留，后续简化
├── api/
│   ├── chat.py            # 重命名自 chat_v3.py
│   ├── health.py          # 保留
│   └── campaign_automation.py  # 保留
├── services/
│   ├── mcp_client.py      # 保留
│   └── gemini_client.py   # 保留
├── prompts/               # 保留
└── main.py                # 更新
```

---

## 数据模型（Data Models）

### AgentState（简化）

```python
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    """Agent 状态定义（简化版）。"""
    
    # 对话消息历史
    messages: Annotated[list[BaseMessage], operator.add]
    
    # 用户和会话信息
    user_id: str
    session_id: str
    
    # 执行结果（可选）
    completed_results: list[dict]
    
    # 错误信息（可选）
    error: dict | None
```

**简化说明**：
- 删除 `current_intent`（Gemini 自动识别）
- 删除 `pending_actions`（Gemini 自动规划）
- 删除 `requires_confirmation`（在 Agent 内部处理）
- 删除 `credit_checked`（在 Agent 内部处理）


### ChatRequest/Response（统一格式）

```python
class MessageItem(BaseModel):
    """单条消息。"""
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    """Chat 请求模型。"""
    messages: list[MessageItem]
    user_id: str
    session_id: str

class ChatResponse(BaseModel):
    """Chat 响应模型。"""
    response: str
    success: bool
    session_id: str
    error: str | None = None
    tool_results: list[dict] | None = None
```

---

## 错误处理（Error Handling）

保持现有的错误处理策略，统一使用 `app/core/errors.py`：

```python
class AIOrchestatorError(Exception):
    """基础错误类。"""
    pass

class MCPConnectionError(AIOrchestatorError):
    """MCP 连接错误。"""
    pass

class InsufficientCreditsError(AIOrchestatorError):
    """Credit 不足错误。"""
    pass

class AgentExecutionError(AIOrchestatorError):
    """Agent 执行错误。"""
    pass
```

**错误处理流程**：
1. Agent 内部捕获错误
2. 返回 AgentResult with error
3. Orchestrator 检查 error 并生成友好消息
4. 返回给用户

---

## 测试策略（Testing Strategy）

### 删除的测试

```
tests/
├── test_intent_recognition_property.py  # v2 router 测试
├── test_execution_order_property.py     # v2 planner 测试
├── test_context_resolution_property.py  # v2 特定
├── test_checkpoint_verification.py      # v2 特定
├── test_reporting_node.py               # v2 node 测试
└── test_phase2_checkpoint.py            # v2 特定
```

### 保留/更新的测试

```
tests/
├── test_orchestrator.py                 # 新增：测试 Orchestrator
├── test_retry_property.py               # 保留：通用重试测试
├── ad_performance/                      # 保留：模块测试
├── campaign_automation/                 # 保留：模块测试
├── landing_page/                        # 保留：模块测试
├── market_insights/                     # 保留：模块测试
└── ad_creative/                         # 保留：模块测试
```

### 新增测试

```python
# tests/test_orchestrator.py

@pytest.mark.asyncio
async def test_orchestrator_simple_message():
    """测试 Orchestrator 处理简单消息。"""
    orchestrator = get_orchestrator()
    result = await orchestrator.process_message(
        user_id="test",
        session_id="test",
        message="你好",
    )
    assert result["success"]
    assert "response" in result


@pytest.mark.asyncio
async def test_orchestrator_with_agent_call():
    """测试 Orchestrator 调用 Agent。"""
    with patch_agent_registry():
        orchestrator = get_orchestrator()
        result = await orchestrator.process_message(
            user_id="test",
            session_id="test",
            message="帮我生成素材",
        )
        assert result["success"]
        assert len(result["tool_results"]) > 0
```

---

## 实施步骤（Implementation Steps）

### Phase 1: 准备与验证（不删除代码）

**目标**：确保 v3 功能完整，可以替代 v2

1. 验证 v3 API 功能正常
2. 验证 v3 与前端集成正常
3. 验证 v3 与 Web Platform MCP 通信正常
4. 运行所有测试确保通过

### Phase 2: 文件重命名

**目标**：将 v3 文件重命名为主文件

1. 重命名 `app/core/graph_v3.py` → `app/core/graph.py`
2. 重命名 `app/api/chat_v3.py` → `app/api/chat.py`
3. 移动 `app/nodes/persist.py` → `app/core/persist.py`
4. 更新所有导入语句

### Phase 3: 更新 main.py

**目标**：只初始化 v3 架构

```python
# app/main.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... 初始化 Redis, MCP Client ...
    
    # 注册 Agents
    register_all_agents()
    logger.info("agents_registered")
    
    # 编译 LangGraph（只编译 v3）
    graph = build_agent_graph()
    logger.info("langgraph_compiled")
    
    yield
    
    # ... 清理资源 ...
    reset_agent_graph()
```

### Phase 4: 删除 v2 代码

**目标**：删除所有 v2 相关文件

1. 删除 `app/nodes/` 目录（除了已移动的 persist.py）
2. 删除 `app/core/routing.py`
3. 删除 `app/tools/` 目录
4. 删除 v2 相关测试

### Phase 5: 更新文档

**目标**：文档反映统一后的架构

1. 更新 `README.md`
2. 更新 `.kiro/specs/ai-orchestrator/design.md`
3. 更新 `docs/ARCHITECTURE_V3.md` → `docs/ARCHITECTURE.md`

### Phase 6: 测试验证

**目标**：确保一切正常

1. 运行所有测试
2. 手动测试 Chat 功能
3. 验证与前端集成
4. 性能测试

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

### Acceptence Criteria Testing Prework

#### 1.1 WHEN 架构统一完成 THEN 系统 SHALL 只保留 v3 架构的 LangGraph 实现
Thoughts: 这是验证代码清理的完整性。我们可以检查文件系统，确保 v2 相关文件都已删除。
Testable: yes - example

#### 2.1 WHEN API 统一完成 THEN 系统 SHALL 将 `/api/v1/chat` 指向 v3 实现
Thoughts: 这是验证 API 端点的正确性。我们可以调用 API 并检查响应格式。
Testable: yes - example

#### 2.3 WHEN API 统一完成 THEN 系统 SHALL 保持与前端的接口兼容性
Thoughts: 这是验证接口兼容性。对于任何有效的请求，新 API 应该返回与旧 API 相同格式的响应。
Testable: yes - property

#### 3.1 WHEN 模块简化完成 THEN 每个模块 SHALL 只保留必要的文件
Thoughts: 这是验证文件结构的简化。我们可以检查每个模块的文件数量。
Testable: yes - example

#### 4.1 WHEN 启动流程更新 THEN `app/main.py` SHALL 只编译 v3 LangGraph
Thoughts: 这是验证启动流程。我们可以检查 main.py 中是否只有一个 build_agent_graph 调用。
Testable: yes - example

### Property Reflection

审查所有可测试的属性：
- 大部分是 example 测试（验证特定状态）
- Property 1 (接口兼容性) 是真正的 property，需要跨多个输入验证

### Correctness Properties

#### Property 1: API 响应格式兼容性
*For any* 有效的 ChatRequest，统一后的 `/api/v1/chat` 端点 SHALL 返回包含 `response`, `success`, `session_id` 字段的响应，格式与原 v3 端点一致
**Validates: Requirements 2.3**

---

## 数据模型（Data Models）

### AgentContext

```python
@dataclass
class AgentContext:
    """Agent 执行上下文。"""
    user_id: str
    session_id: str
    mcp_client: MCPClient | None = None
    redis_client: Redis | None = None
```

### AgentResult

```python
@dataclass
class AgentResult:
    """Agent 执行结果。"""
    success: bool
    data: dict | None = None
    error: dict | None = None
    message: str | None = None
```

---

## 错误处理（Error Handling）

### 统一的错误处理流程

```python
# app/core/errors.py

async def handle_agent_error(
    error: Exception,
    agent_name: str,
    context: AgentContext,
) -> AgentResult:
    """处理 Agent 执行错误。"""
    logger.error(
        "agent_execution_error",
        agent=agent_name,
        error=str(error),
        user_id=context.user_id,
    )
    
    if isinstance(error, MCPConnectionError):
        return AgentResult(
            success=False,
            error={
                "code": "3000",
                "message": "无法连接到数据服务，请稍后重试",
            },
        )
    
    elif isinstance(error, InsufficientCreditsError):
        return AgentResult(
            success=False,
            error={
                "code": "6011",
                "message": "Credit 余额不足，请充值",
            },
        )
    
    else:
        return AgentResult(
            success=False,
            error={
                "code": "1000",
                "message": "系统错误，请稍后重试",
            },
        )
```

---

## 性能优化（Performance Optimization）

### 1. 减少启动时间

**v2 架构**：
- 编译 2 个 LangGraph（v2 + v3）
- 注册 tools + agents
- 启动时间：~3-5 秒

**v3 架构**：
- 编译 1 个 LangGraph
- 只注册 agents
- 启动时间：~1-2 秒（减少 50%）

### 2. 简化执行路径

**v2 架构**：
```
用户消息 → router → planner → executor → analyzer → respond → persist
（6 个节点，多次 LLM 调用）
```

**v3 架构**：
```
用户消息 → orchestrator (Gemini function calling) → persist
（2 个节点，1-2 次 LLM 调用）
```

### 3. 减少代码复杂度

| 指标 | v2 | v3 | 改善 |
|------|----|----|------|
| 核心代码行数 | ~2000 | ~500 | -75% |
| Graph 节点数 | 6 | 2 | -67% |
| 条件路由函数 | 5 | 0 | -100% |
| 启动时间 | 3-5s | 1-2s | -50% |

---

## 监控与日志（Monitoring and Logging）

### 统一的日志格式

```python
# 所有日志使用 structlog

logger.info(
    "orchestrator_process_message",
    user_id=user_id,
    session_id=session_id,
    message_preview=message[:100],
)

logger.info(
    "agent_execution",
    agent=agent_name,
    action=action,
    duration_ms=duration,
)
```

### 关键指标

```python
from prometheus_client import Counter, Histogram

# 请求计数
chat_requests_total = Counter(
    "chat_requests_total",
    "Total chat requests",
    ["status"],
)

# Agent 调用计数
agent_calls_total = Counter(
    "agent_calls_total",
    "Total agent calls",
    ["agent", "status"],
)

# 响应延迟
response_latency = Histogram(
    "response_latency_seconds",
    "Response latency",
)
```

---

## 安全考虑（Security Considerations）

### Service Token 验证

```python
# app/core/auth.py

async def validate_service_token(
    authorization: str = Header(...),
) -> str:
    """验证 service token。"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization[7:]
    settings = get_settings()
    
    if token != settings.web_platform_service_token:
        raise HTTPException(status_code=401, detail="Invalid service token")
    
    return token
```

---

## 配置管理（Configuration Management）

### 简化的配置

```python
# app/core/config.py

class Settings(BaseSettings):
    """AI Orchestrator 配置。"""
    
    # Application
    app_name: str = "AI Orchestrator"
    environment: str = "development"
    
    # Web Platform
    web_platform_url: str = "http://localhost:8000"
    web_platform_service_token: str
    
    # Redis
    redis_url: str = "redis://localhost:6379/3"
    
    # Gemini
    gemini_api_key: str
    gemini_model: str = "gemini-3-pro-preview"
    
    # Performance
    max_concurrent_requests: int = 100
    request_timeout: int = 60
    
    # Logging
    log_level: str = "INFO"
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
```

---

## 部署架构（Deployment Architecture）

### Docker Compose（简化）

```yaml
services:
  ai-orchestrator:
    build: ./ai-orchestrator
    ports:
      - "8001:8001"
    environment:
      - WEB_PLATFORM_URL=http://backend:8000
      - WEB_PLATFORM_SERVICE_TOKEN=${SERVICE_TOKEN}
      - REDIS_URL=redis://redis:6379/3
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      - redis
      - backend
```

---

## 迁移检查清单（Migration Checklist）

### 代码迁移

- [ ] 重命名 `graph_v3.py` → `graph.py`
- [ ] 重命名 `chat_v3.py` → `chat.py`
- [ ] 移动 `nodes/persist.py` → `core/persist.py`
- [ ] 更新 `main.py` 导入
- [ ] 删除 `app/nodes/` 目录
- [ ] 删除 `app/core/routing.py`
- [ ] 删除 `app/tools/` 目录
- [ ] 删除旧的 `app/api/chat.py`

### 测试迁移

- [ ] 删除 v2 相关测试
- [ ] 更新集成测试指向新 API
- [ ] 添加 Orchestrator 测试
- [ ] 运行所有测试确保通过

### 文档更新

- [ ] 更新 `README.md`
- [ ] 更新 `.kiro/specs/ai-orchestrator/design.md`
- [ ] 重命名 `ARCHITECTURE_V3.md` → `ARCHITECTURE.md`
- [ ] 删除 v2 相关文档

### 验证

- [ ] 启动服务无错误
- [ ] `/health` 端点返回 healthy
- [ ] Chat API 返回正确响应
- [ ] 前端集成正常
- [ ] 所有测试通过

---

## 风险与缓解（Risks and Mitigation）

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| v3 功能不完整 | 高 | 中 | Phase 1 充分验证 |
| 前端接口不兼容 | 高 | 低 | 保持响应格式一致 |
| 测试失败 | 中 | 中 | 逐步迁移测试 |
| 文档过时 | 低 | 高 | 同步更新文档 |
| 回滚困难 | 中 | 低 | 使用 Git 分支 |

### 回滚计划

如果迁移失败，可以：
1. 回退 Git commit
2. 恢复 v2 代码
3. 切换 API 端点回 v2

---

## 已知限制与未来改进（Known Limitations & Future Improvements）

### 当前限制

1. **Gemini 3 依赖**：v3 架构依赖 Gemini 3 的 function calling，如果 API 不可用会影响功能
2. **简化的状态管理**：v3 使用更简单的状态，可能不适合极复杂的多步骤任务
3. **Function Calling 限制**：Gemini function calling 有调用次数限制

### 未来改进

1. **混合架构**：对于极复杂任务，可以在 v3 基础上添加专门的规划节点
2. **多模型支持**：支持切换到其他 LLM（Claude, GPT-4）
3. **更细粒度的监控**：添加 Agent 级别的性能监控

---

## 设计决策总结（Design Decisions Summary）

### 关键决策

1. **保留 v3，删除 v2**
   - 原因：v3 更简单，利用 Gemini 原生能力
   - 好处：减少代码量，提升可维护性

2. **统一 API 端点**
   - 原因：避免前端需要处理多个端点
   - 好处：简化集成，减少混淆

3. **保留 agents/ 目录**
   - 原因：Sub-Agents 是 v3 的核心
   - 好处：清晰的模块边界

4. **删除 nodes/ 目录**
   - 原因：v3 不需要多个 LangGraph 节点
   - 好处：减少代码复杂度

5. **保留 modules/ 目录**
   - 原因：包含业务逻辑实现
   - 好处：后续可以逐步简化

---

## 接下来的步骤

1. **Review this design**: 请确认设计是否满足需求
2. **Create tasks.md**: 将设计分解为具体的实现任务
3. **Execute migration**: 按照 Phase 1-6 执行迁移
4. **Verify and test**: 确保一切正常

