# AI Orchestrator 实现详情（Implementation Details）

本文档整合自 `ai-orchestrator/docs/` 目录下的实现文档，提供 AI Orchestrator 的架构设计和实现细节。

---

## 架构概述

AI Orchestrator 采用 **Planning + Multi-step Execution** 模式，基于 LangGraph 状态机实现。

### 核心能力状态

| # | 能力 | 状态 | 核心价值 | 实现方案 |
|---|------|------|----------|----------|
| 1 | 统一 Tool 抽象层 | ✅ 完成 | 代码复用，易于扩展 | Tool Registry |
| 2 | Planning 能力 | ✅ 完成 | 复杂任务分解，多步骤规划 | Planner Node |
| 3 | 多轮循环执行 | ✅ 完成 | ReAct 模式，动态调整 | Executor + Analyzer 循环 |
| 4 | 网页抓取增强 | ✅ 完成 | 竞品分析，数据采集 | Web Scraper Tool |
| 5 | 长期记忆 | 📋 计划中 | 用户画像，个性化服务 | Mem0 SDK |
| 6 | MCP Hub | 📋 计划中 | 外部工具集成，生态扩展 | MCP Client Hub |

---

## LangGraph 状态机

```
[START]
   │
   ▼
router ──────┬──────► planner ──► executor ◄───┐
             │              │          │        │
             │              │          ▼        │ (continue)
             │              │      analyzer ────┤
             │              │          │        │
             │              └──────────┘        │
             │             (replan)             │
             │                                  │
             └──► respond ──► persist ──► [END]
```

---

## 执行流程

### 简单任务流程

```
用户: "看看我上周的广告数据"

[router] → 识别意图: analyze_report
    ↓
[planner] → 生成计划: 1 步骤 (get_ad_performance)
           → 自动确认 (简单任务)
    ↓
[executor] → 执行 get_ad_performance
    ↓
[analyzer] → 决策: respond (执行完成)
    ↓
[respond] → 生成响应
    ↓
[persist] → 保存对话
```

### 复杂任务流程

```
用户: "分析表现差的广告，然后帮我生成替代素材"

[router] → 识别意图: multi_step
    ↓
[planner] → 生成计划: 2 步骤
           → 1. get_ad_performance (获取数据)
           → 2. generate_creative (依赖步骤 1)
           → 计划已确认 (成本 < 10 credits)
    ↓
[executor] → 执行步骤 1: get_ad_performance
    ↓
[analyzer] → 决策: continue (还有步骤)
    ↓
[executor] → 执行步骤 2: generate_creative
           → 参数解析: $step_1.data → 使用步骤 1 的结果
    ↓
[analyzer] → 决策: respond (执行完成)
    ↓
[respond] → 生成响应 (包含执行摘要)
    ↓
[persist] → 保存对话
```

### 高成本任务需确认

```
用户: "帮我批量生成 20 张素材"

[router] → 识别意图: generate_creative
    ↓
[planner] → 生成计划: 1 步骤
           → 预估成本: 10 credits (> 阈值)
           → 需要用户确认
    ↓
[respond] → 展示计划，等待确认
    ↓
[END] → 暂停，等待用户输入

用户: "确认"

[planner] → 标记 plan_confirmed = True
    ↓
[executor] → 执行生成任务
    ↓
...
```

---

## 目录结构

```
ai-orchestrator/
├── app/
│   ├── api/                          # API 端点
│   │   ├── chat.py                   # 聊天流式接口
│   │   └── health.py
│   │
│   ├── core/                         # 核心配置
│   │   ├── config.py                 # 配置管理
│   │   ├── graph.py                  # LangGraph 构建
│   │   ├── state.py                  # AgentState 定义
│   │   ├── models.py                 # 核心数据模型
│   │   └── routing.py                # 路由逻辑
│   │
│   ├── nodes/                        # LangGraph 节点
│   │   ├── router.py                 # 意图路由
│   │   ├── planner.py                # 任务规划
│   │   ├── executor.py               # 统一执行器
│   │   ├── analyzer.py               # 结果分析
│   │   ├── respond.py                # 响应生成
│   │   └── persist.py                # 对话持久化
│   │
│   ├── tools/                        # 统一工具层
│   │   ├── base.py                   # 工具基类定义
│   │   ├── registry.py               # 工具注册中心
│   │   ├── setup.py                  # 工具注册启动
│   │   ├── creative/                 # 素材相关工具
│   │   ├── reporting/                # 报表相关工具
│   │   ├── campaign/                 # 广告投放工具
│   │   ├── market/                   # 市场洞察工具
│   │   └── web/                      # 网页抓取工具
│   │
│   ├── modules/                      # 功能模块实现
│   │   ├── ad_creative/              # 素材生成模块
│   │   ├── ad_performance/           # 报表分析模块
│   │   ├── campaign_automation/      # 广告投放模块
│   │   ├── landing_page/             # 落地页模块
│   │   └── market_insights/          # 市场洞察模块
│   │
│   ├── services/                     # 外部服务客户端
│   │   ├── gemini_client.py          # Gemini API
│   │   ├── credit_client.py          # Credit 管理 (HTTP API)
│   │   ├── gcs_client.py             # Google Cloud Storage
│   │   └── mcp_client.py             # 后端 MCP 调用
│   │
│   └── main.py                       # FastAPI 入口
│
└── tests/
```

---

## 核心数据结构

### AgentState

```python
class AgentState(TypedDict, total=False):
    # === 消息 ===
    messages: Annotated[list[BaseMessage], operator.add]
    user_id: str
    session_id: str

    # === 意图识别 ===
    current_intent: str | None
    extracted_params: dict[str, Any] | None

    # === 执行计划 ===
    execution_plan: dict[str, Any] | None  # ExecutionPlan
    current_step_index: int
    step_results: list[dict[str, Any]]     # List[StepResult]
    plan_confirmed: bool
    execution_complete: bool

    # === 分析决策 ===
    analyzer_decision: str | None  # "continue" | "respond" | "replan"
    replan_suggestion: str | None

    # === Credit 管理 ===
    credit_checked: bool
    credit_sufficient: bool
    estimated_cost: float | None

    # === 错误处理 ===
    error: ErrorInfo | None
    retry_count: int

    # === 上下文 ===
    memory_context: dict[str, Any] | None
    context_references: dict[str, Any] | None
```

### ExecutionPlan

```python
class ExecutionStep(BaseModel):
    """执行步骤"""
    step_id: int                       # 步骤 ID (1-indexed)
    action: str                        # 动作描述
    tool: str                          # 工具名称
    tool_params: dict[str, Any]        # 工具参数
    depends_on: list[int] = []         # 依赖的步骤 ID
    reason: str                        # 执行原因
    estimated_cost: float = 0          # 预估 credit

class ExecutionPlan(BaseModel):
    """执行计划"""
    goal: str                          # 用户目标
    complexity: Literal["simple", "moderate", "complex"]
    steps: list[ExecutionStep]
    estimated_total_credits: float
    requires_confirmation: bool
```

---

## 工具层

### Tool 基类

```python
class BaseTool(ABC, Generic[InputT, OutputT]):
    """工具基类"""
    definition: ToolDefinition

    @abstractmethod
    async def execute(self, params: InputT, context: ToolContext) -> ToolResult:
        """执行工具"""
        pass

    def validate_params(self, params: dict) -> InputT:
        """参数验证"""
        pass

    def estimate_cost(self, params: InputT) -> float:
        """估算成本"""
        return self.definition.credit_cost
```

### 参数引用语法

执行器支持在工具参数中引用前序步骤的结果：

```python
# 引用语法
"$step_1"                # 整个步骤 1 的结果
"$step_1.data"           # 步骤 1 结果的 data 字段
"$step_1.data.records"   # 嵌套字段访问
"$step_1.data.0.name"    # 数组索引访问
```

---

## 路由逻辑

```python
# Router → Planner/Respond
def route_after_router(state):
    if state.get("error"):
        return "respond"
    if state.get("current_intent") in ["clarification_needed", "general_query"]:
        return "respond"
    return "planner"

# Planner → Executor/Wait/Respond
def route_after_planner(state):
    if state.get("error"):
        return "respond"
    if not state.get("plan_confirmed"):
        return "__end__"  # 等待用户确认
    return "executor"

# Executor → Analyzer/Respond
def route_after_executor(state):
    if state.get("error", {}).get("type") == "CRITICAL":
        return "respond"
    return "analyzer"

# Analyzer → Executor/Planner/Respond (循环)
def route_after_analyzer(state):
    decision = state.get("analyzer_decision", "respond")
    if state.get("execution_complete") or decision == "respond":
        return "respond"
    if decision == "continue":
        return "executor"
    if decision == "replan":
        return "planner"
    return "respond"
```

---

## 配置参数

### 计划确认阈值

```python
CONFIRMATION_CREDIT_THRESHOLD = 10.0  # 预估成本超过 10 credits 需要确认
```

### 复杂度判断

- **simple**: 单一明确任务，1-2 步骤
- **moderate**: 需要分析或组合，2-4 步骤
- **complex**: 复杂多步骤，4+ 步骤

---

## 错误处理

### 重试策略

- 指数退避：1s, 2s, 4s
- 最大重试次数：3 次
- 超时时间：30 秒

### 错误类型

- `TRANSIENT`: 临时错误，可重试
- `CRITICAL`: 严重错误，立即停止
- `VALIDATION`: 验证错误，需要用户修正输入

---

## 模块集成状态

| 模块 | 状态 | 关键功能 |
|------|------|----------|
| Ad Creative | ✅ 完成 | 素材生成、保存、GCS 存储 |
| Ad Performance | ✅ 完成 | 报表获取、AI 分析 |
| Campaign Automation | ✅ 完成 | 广告创建、预算优化 |
| Landing Page | ✅ 完成 | 页面生成、托管、导出 |
| Market Insights | ⏳ 部分完成 | 竞品分析、趋势获取 |

---

## 未来扩展

### 1. 长期记忆 (Mem0)

- Memory Recall Node: 在 router 之前召回相关记忆
- Memory Save Node: 在 persist 之后保存重要信息
- 用户画像: 投放偏好、历史表现等

### 2. MCP Hub

- 动态发现和连接外部 MCP Server
- 工具自动注册到 Tool Registry
- 支持 stdio/SSE/HTTP 传输

---

**文档版本**：v1.0
**最后更新**：2024-12-01
**来源文档**：
- `ai-orchestrator/docs/ARCHITECTURE.md`
- `ai-orchestrator/docs/TASK_*_SUMMARY.md`
- `ai-orchestrator/docs/INTEGRATION_SUMMARY.md`
