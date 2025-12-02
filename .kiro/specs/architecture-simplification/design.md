# 设计文档 - AAE 架构全面简化

## 概述（Overview）

本设计文档描述如何全面简化 AAE 系统架构，包括：
1. 前端移除 AI agent 框架，使用 SSE 通信
2. AI Orchestrator 完成 v3 迁移，删除 v2 架构
3. 简化 capability 模块内部结构（保持 5 个独立模块）

简化后的系统将：
- 减少代码量 30%+
- 减少文件数量 50%+
- 提升启动速度 50%+
- 降低维护成本
- 保持 5 个独立能力模块
- 保持所有核心功能

---

## 架构设计（Architecture）

### Sub-Agent 设计理念

**核心原则**：5 个模块都是**智能体（AI Agent）**，不是普通服务

每个 Sub-Agent 的特征：
1. **有明确的技能定位**：专注于特定领域的智能决策
2. **通过 MCP Tools 完成任务**：调用 Backend 提供的工具
3. **由用户意图驱动**：根据对话内容主动调用工具
4. **不是定时任务**：所有操作都是响应用户请求

### 5 个 Sub-Agent 的职责定位

| Sub-Agent | 技能定位 | MCP Tools | 示例对话 |
|-----------|---------|-----------|----------|
| **Ad Creative** | 创意生成专家 | `generate_image`, `analyze_creative`, `upload_creative` | "帮我生成素材" |
| **Market Insights** | 市场分析专家 | `analyze_competitor`, `get_trends`, `generate_strategy` | "分析竞品" |
| **Ad Performance** | 性能分析专家 | `fetch_ad_data`, `analyze_performance`, `detect_anomaly` | "我的广告表现如何？" |
| **Landing Page** | 落地页生成专家 | `generate_page`, `translate_page`, `create_ab_test` | "生成落地页" |
| **Campaign Automation** | 投放优化专家 | `create_campaign`, `optimize_budget`, `apply_rules` | "创建广告" |

**关键理解**：
- ✅ Ad Performance Agent 根据用户询问"我的广告表现如何？"时，**主动调用** `fetch_ad_data` tool 抓取最新数据
- ✅ 不是后台定时任务抓取，而是 Agent 按需抓取
- ✅ Landing Page 的多语言和 A/B 测试是**页面本身的功能**，由 Agent 生成支持这些功能的页面

### 简化后的整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                            │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   Chat Interface                          │  │
│  │                                                           │  │
│  │  用户输入 → HTTP POST → 获取 session_id                   │  │
│  │           ↓                                               │  │
│  │  EventSource(SSE) ← 流式响应 ← AI Orchestrator           │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP + SSE
                              │
┌─────────────────────────────▼─────────────────────────────────────┐
│                        Backend (FastAPI)                          │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  POST /api/v1/chat          (接收消息，返回 session_id) │    │
│  │  GET  /api/v1/chat/stream   (SSE 流式响应)              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   MCP Server                             │    │
│  │  - creative_intelligence_tools                           │    │
│  │  - ad_performance_tools                                  │    │
│  │  - campaign_automation_tools                             │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                            │ MCP Protocol
                            │
┌───────────────────────────▼───────────────────────────────────────┐
│                    AI Orchestrator (v3 Only)                      │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              LangGraph (2 节点)                          │    │
│  │                                                          │    │
│  │    [START] → orchestrator → persist → [END]             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         5 个 Sub-Agents (智能体)                         │    │
│  │         每个 Agent 通过 MCP Tools 完成任务               │    │
│  │                                                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │    │
│  │  │ Ad Creative  │  │ Market       │  │ Ad           │  │    │
│  │  │ Agent        │  │ Insights     │  │ Performance  │  │    │
│  │  │              │  │ Agent        │  │ Agent        │  │    │
│  │  │ AI 能力:     │  │              │  │              │  │    │
│  │  │ - 生成图片   │  │ AI 能力:     │  │ AI 能力:     │  │    │
│  │  │   (Gemini)   │  │ - 分析竞品   │  │ - AI 分析    │  │    │
│  │  │ - 分析素材   │  │   (Gemini)   │  │   (Gemini)   │  │    │
│  │  │   (Gemini)   │  │ - 生成策略   │  │ - 异常检测   │  │    │
│  │  │              │  │   (Gemini)   │  │   (Gemini)   │  │    │
│  │  │ MCP Tools:   │  │              │  │              │  │    │
│  │  │ - save_      │  │ MCP Tools:   │  │ MCP Tools:   │  │    │
│  │  │   creative   │  │ - fetch_     │  │ - fetch_ad_  │  │    │
│  │  │ - get_       │  │   competitor │  │   data       │  │    │
│  │  │   creative   │  │   _data      │  │ - get_       │  │    │
│  │  └──────────────┘  │ - save_      │  │   historical │  │    │
│  │                     │   analysis   │  │   _data      │  │    │
│  │                     └──────────────┘  └──────────────┘  │    │
│  │                                                          │    │
│  │  ┌──────────────┐  ┌──────────────┐                    │    │
│  │  │ Landing Page │  │ Campaign     │                    │    │
│  │  │ Agent        │  │ Automation   │                    │    │
│  │  │              │  │ Agent        │                    │    │
│  │  │ AI 能力:     │  │              │                    │    │
│  │  │ - 生成内容   │  │ AI 能力:     │                    │    │
│  │  │   (Gemini)   │  │ - 优化参数   │                    │    │
│  │  │ - 翻译文案   │  │   (Gemini)   │                    │    │
│  │  │   (Gemini)   │  │ - 生成文案   │                    │    │
│  │  │              │  │   (Gemini)   │                    │    │
│  │  │ MCP Tools:   │  │              │                    │    │
│  │  │ - save_page  │  │ MCP Tools:   │                    │    │
│  │  │ - upload_    │  │ - create_    │                    │    │
│  │  │   to_s3      │  │   campaign   │                    │    │
│  │  │ - create_ab_ │  │ - get_       │                    │    │
│  │  │   test       │  │   campaign   │                    │    │
│  │  └──────────────┘  │ - pause_     │                    │    │
│  │                     │   campaign   │                    │    │
│  │                     └──────────────┘                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              │ 调用 MCP Tools                    │
│                              ↓                                   │
└───────────────────────────────────────────────────────────────────┘
                              │
                              │ MCP Protocol
                              ↓
                    Backend MCP Server
                    (提供所有 Tools)
```

---

## 组件设计（Component Design）

### 1. 前端 SSE 通信实现

#### 1.1 Chat Hook (useChat.ts)

```typescript
// frontend/src/hooks/useChat.ts

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  metadata?: any;
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const sendMessage = async (content: string) => {
    setIsLoading(true);
    setError(null);

    // 1. 添加用户消息到 UI
    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content,
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      // 2. 发送消息到后端
      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          session_id: getSessionId(),
        }),
      });

      const { session_id } = await response.json();

      // 3. 建立 SSE 连接接收流式响应
      const eventSource = new EventSource(
        `/api/v1/chat/stream?session_id=${session_id}`
      );
      eventSourceRef.current = eventSource;

      let assistantMessage: Message = {
        id: generateId(),
        role: 'assistant',
        content: '',
      };

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'content') {
          // 流式更新内容
          assistantMessage.content += data.content;
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];
            if (lastMessage?.role === 'assistant') {
              newMessages[newMessages.length - 1] = { ...assistantMessage };
            } else {
              newMessages.push({ ...assistantMessage });
            }
            return newMessages;
          });
        } else if (data.type === 'metadata') {
          // 更新元数据（嵌入式组件）
          assistantMessage.metadata = data.metadata;
        } else if (data.type === 'done') {
          // 完成
          eventSource.close();
          setIsLoading(false);
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        eventSource.close();
        setError('连接失败，请重试');
        setIsLoading(false);
      };

    } catch (err) {
      setError('发送失败，请重试');
      setIsLoading(false);
    }
  };

  const cleanup = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
  };

  useEffect(() => {
    return cleanup;
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
  };
}
```

#### 1.2 后端 SSE 端点

```python
# backend/app/api/v1/chat.py

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

@router.post("/chat")
async def create_chat_session(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """接收用户消息，创建会话，返回 session_id。"""
    session_id = generate_session_id()
    
    # 存储消息到 Redis
    await redis_client.lpush(
        f"chat:session:{session_id}:messages",
        json.dumps({
            "role": "user",
            "content": request.message,
            "timestamp": datetime.utcnow().isoformat(),
        })
    )
    
    # 异步调用 AI Orchestrator
    asyncio.create_task(
        process_chat_message(
            session_id=session_id,
            user_id=current_user.id,
            message=request.message,
        )
    )
    
    return {"session_id": session_id}


@router.get("/chat/stream")
async def stream_chat_response(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """SSE 端点，流式返回 AI 响应。"""
    
    async def event_generator():
        # 订阅 Redis channel
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"chat:session:{session_id}:stream")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    
                    if data["type"] == "content":
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "content",
                                "content": data["content"],
                            })
                        }
                    elif data["type"] == "metadata":
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "metadata",
                                "metadata": data["metadata"],
                            })
                        }
                    elif data["type"] == "done":
                        yield {
                            "event": "message",
                            "data": json.dumps({"type": "done"})
                        }
                        break
        finally:
            await pubsub.unsubscribe(f"chat:session:{session_id}:stream")
    
    return EventSourceResponse(event_generator())
```

---

### 2. AI Orchestrator v3 架构

#### 2.1 简化的 LangGraph

```python
# ai-orchestrator/app/core/graph.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

def build_agent_graph():
    """构建简化的 v3 Agent Graph。
    
    只有 2 个节点：
    - orchestrator: 处理意图识别和 Agent 调用
    - persist: 持久化对话历史
    """
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("persist", persist_node)
    
    # 简单的线性流程
    workflow.set_entry_point("orchestrator")
    workflow.add_edge("orchestrator", "persist")
    workflow.add_edge("persist", END)
    
    return workflow.compile(checkpointer=MemorySaver())
```

#### 2.2 Orchestrator 节点

```python
# ai-orchestrator/app/core/orchestrator.py

async def orchestrator_node(state: AgentState):
    """协调器节点：使用 Gemini Function Calling。"""
    
    # 1. 获取所有可用的 Agent tools
    tools = [
        creative_intelligence_agent.to_tool(),
        ad_performance_agent.to_tool(),
        campaign_automation_agent.to_tool(),
    ]
    
    # 2. 调用 Gemini with function calling
    response = await gemini_client.chat_with_tools(
        messages=state["messages"],
        tools=tools,
    )
    
    # 3. 执行 function calls
    tool_results = []
    if response.function_calls:
        for call in response.function_calls:
            agent = get_agent(call.name)
            result = await agent.execute(
                action=call.args.get("action"),
                params=call.args,
                context=AgentContext(
                    user_id=state["user_id"],
                    session_id=state["session_id"],
                ),
            )
            tool_results.append(result)
    
    # 4. 更新状态
    return {
        "messages": state["messages"] + [response.message],
        "completed_results": tool_results,
    }
```

---

### 3. 模块内部简化设计

#### 3.1 Ad Creative Module（简化内部结构）

**简化前**：
```
ai-orchestrator/app/modules/ad_creative/
├── capability.py
├── models.py
├── generators/              # 子目录
│   ├── image_generator.py
│   └── variant_generator.py
├── analyzers/               # 子目录
│   ├── competitor_analyzer.py
│   └── scoring_engine.py
├── managers/                # 子目录
│   ├── creative_manager.py
│   └── upload_manager.py
├── extractors/              # 子目录
│   ├── amazon_extractor.py
│   └── shopify_extractor.py
└── utils/
    ├── cache_manager.py
    ├── retry.py
    └── validators.py
```

**简化后**：
```
ai-orchestrator/app/modules/ad_creative/
├── capability.py          # Agent 入口
├── service.py             # 所有业务逻辑（合并所有子目录）
├── models.py              # 数据模型
└── utils.py               # 通用工具（合并 utils/）
```

**service.py 内容**：

```python
# ai-orchestrator/app/modules/ad_creative/service.py

class AdCreativeService:
    """广告素材服务：生成图片/视频、分析、评分。"""
    
    def __init__(self):
        self.gemini_client = get_gemini_client()
        self.mcp_client = get_mcp_client()
    
    # === 素材生成（AI 能力） ===
    
    async def generate_image(
        self,
        product_info: dict,
        style: str,
        aspect_ratio: str,
    ) -> CreativeResult:
        """生成广告图片（AI 能力）。"""
        # 1. [AI] 优化 prompt
        optimized_prompt = await self.gemini_client.optimize_prompt(
            product_info=product_info,
            style=style,
            media_type="image",
        )
        
        # 2. [AI] 调用 Gemini Imagen 生成图片
        image_url = await self.gemini_client.generate_image(
            prompt=optimized_prompt,
            aspect_ratio=aspect_ratio,
        )
        
        # 3. [MCP Tool] 保存到素材库
        creative_id = await self.mcp_client.call_tool(
            "save_creative",
            {
                "url": image_url,
                "type": "image",
                "metadata": product_info,
            }
        )
        
        return CreativeResult(
            creative_id=creative_id,
            url=image_url,
        )
    
    async def generate_video(
        self,
        product_info: dict,
        style: str,
        duration: int,
    ) -> CreativeResult:
        """生成广告视频（AI 能力）。"""
        # 1. [AI] 优化 prompt
        optimized_prompt = await self.gemini_client.optimize_prompt(
            product_info=product_info,
            style=style,
            media_type="video",
        )
        
        # 2. [AI] 调用 Gemini Veo 生成视频
        video_url = await self.gemini_client.generate_video(
            prompt=optimized_prompt,
            duration=duration,
        )
        
        # 3. [MCP Tool] 保存到素材库
        creative_id = await self.mcp_client.call_tool(
            "save_creative",
            {
                "url": video_url,
                "type": "video",
                "metadata": product_info,
            }
        )
        
        return CreativeResult(
            creative_id=creative_id,
            url=video_url,
        )
    
    async def generate_variants(
        self,
        creative_id: str,
        count: int,
    ) -> list[CreativeResult]:
        """生成素材变体（AI 能力）。"""
        # 1. [MCP Tool] 获取原始素材
        original = await self.mcp_client.call_tool(
            "get_creative",
            {"creative_id": creative_id}
        )
        
        # 2. [AI] 生成变体
        variants = []
        for i in range(count):
            variant_url = await self.gemini_client.generate_variant(
                original_url=original["url"],
                variation_type=f"variant_{i}",
            )
            
            # 3. [MCP Tool] 保存变体
            variant_id = await self.mcp_client.call_tool(
                "save_creative",
                {
                    "url": variant_url,
                    "type": original["type"],
                    "parent_id": creative_id,
                }
            )
            variants.append(CreativeResult(creative_id=variant_id, url=variant_url))
        
        return variants
    
    # === 素材分析（原 analyzers/） ===
    
    async def analyze_creative(
        self,
        creative_id: str,
    ) -> AnalysisResult:
        """分析素材质量。"""
        # 原 analyzers/scoring_engine.py 的逻辑
        creative = await self.mcp_client.call_tool(
            "get_creative",
            {"creative_id": creative_id}
        )
        
        analysis = await self.gemini_client.analyze_image(
            image_url=creative["url"],
            criteria=["clarity", "appeal", "brand_consistency"],
        )
        
        return AnalysisResult(
            score=analysis["score"],
            suggestions=analysis["suggestions"],
        )
    
    async def analyze_competitor_creative(
        self,
        competitor_url: str,
    ) -> CompetitorAnalysis:
        """分析竞品素材。"""
        # 原 analyzers/competitor_analyzer.py 的逻辑
        pass
    
    # === 素材管理（原 managers/） ===
    
    async def upload_creative(
        self,
        file: bytes,
        metadata: dict,
    ) -> CreativeResult:
        """上传素材。"""
        # 原 managers/upload_manager.py 的逻辑
        pass
    
    async def manage_creative(
        self,
        creative_id: str,
        action: str,
    ):
        """管理素材（更新、删除等）。"""
        # 原 managers/creative_manager.py 的逻辑
        pass
    
    # === 产品信息提取（原 extractors/） ===
    
    async def _extract_product_info(self, url: str) -> dict:
        """提取产品信息。"""
        # 原 extractors/ 的逻辑
        if "amazon.com" in url:
            return await self._extract_from_amazon(url)
        elif "shopify" in url:
            return await self._extract_from_shopify(url)
        else:
            return await self._extract_generic(url)
    
    async def _extract_from_amazon(self, url: str) -> dict:
        """从 Amazon 提取。"""
        # 原 extractors/amazon_extractor.py 的逻辑
        pass
    
    async def _extract_from_shopify(self, url: str) -> dict:
        """从 Shopify 提取。"""
        # 原 extractors/shopify_extractor.py 的逻辑
        pass
```

**优势**：
- ✅ 所有素材相关功能集中在一个文件
- ✅ 减少文件跳转，更容易理解
- ✅ 保持功能完整性
- ✅ 更容易维护

---

#### 3.2 其他 4 个模块（同样简化）

所有模块都采用相同的简化策略：

**Market Insights Module**：
```
ai-orchestrator/app/modules/market_insights/
├── capability.py
├── service.py             # 合并 analyzers/, fetchers/, trackers/
├── models.py
└── utils.py
```

**Ad Performance Module**：
```
ai-orchestrator/app/modules/ad_performance/
├── capability.py
├── service.py             # 合并 fetchers/, analyzers/, exporters/
├── models.py
└── utils.py
```

**Landing Page Module**：
```
ai-orchestrator/app/modules/landing_page/
├── capability.py
├── service.py             # 合并 generators/, managers/, optimizers/, tracking/
├── models.py
└── utils.py
```

**Campaign Automation Module**：
```
ai-orchestrator/app/modules/campaign_automation/
├── capability.py
├── service.py             # 合并 managers/, optimizers/, engines/
├── models.py
├── adapters/              # ✅ 保留（平台适配器）
│   ├── meta_adapter.py
│   ├── tiktok_adapter.py
│   └── google_adapter.py
└── utils.py
```

**简化示例（Ad Performance）**：

```python
# ai-orchestrator/app/modules/ad_performance/service.py

class AdPerformanceService:
    """广告性能分析服务。"""
    
    # === 数据抓取（原 fetchers/） ===
    
    async def fetch_meta_data(self, ad_account_id: str, date_range: tuple):
        """抓取 Meta 广告数据。"""
        # 原 fetchers/meta_fetcher.py 的逻辑
        pass
    
    async def fetch_tiktok_data(self, ad_account_id: str, date_range: tuple):
        """抓取 TikTok 广告数据。"""
        # 原 fetchers/tiktok_fetcher.py 的逻辑
        pass
    
    # === 数据分析（原 analyzers/） ===
    
    async def analyze_performance(self, data: dict) -> AnalysisResult:
        """分析广告性能。"""
        # 原 analyzers/performance_analyzer.py 的逻辑
        pass
    
    async def detect_anomaly(self, data: dict) -> list[Anomaly]:
        """检测异常。"""
        # 原 analyzers/anomaly_detector.py 的逻辑
        pass
    
    async def generate_recommendations(self, analysis: AnalysisResult):
        """生成优化建议。"""
        # 原 analyzers/recommendation_engine.py 的逻辑
        pass
    
    # === 报表生成（原 exporters/） ===
    
    async def generate_csv_report(self, data: dict) -> str:
        """生成 CSV 报表。"""
        # 原 exporters/csv_exporter.py 的逻辑
        pass
    
    async def generate_pdf_report(self, data: dict) -> str:
        """生成 PDF 报表。"""
        # 原 exporters/pdf_exporter.py 的逻辑
        pass
```

---

## 数据模型（Data Models）

### 简化的 AgentState

```python
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    """简化的 Agent 状态。"""
    
    # 对话消息
    messages: Annotated[list[BaseMessage], operator.add]
    
    # 用户信息
    user_id: str
    session_id: str
    
    # 执行结果
    completed_results: list[dict]
    
    # 错误信息
    error: dict | None
```

**删除的字段**（v2 专用）：
- ❌ `current_intent`
- ❌ `pending_actions`
- ❌ `requires_confirmation`
- ❌ `credit_checked`

---

## 文件结构变更

### 前端删除

```
frontend/
├── src/
│   ├── app/api/chat/route.ts         ❌ 删除
│   ├── hooks/
│   │   └── useWebSocket.ts           ❌ 删除
│   └── lib/
│       └── websocket-client.ts       ❌ 删除
└── package.json                       # 移除 'ai' 依赖
```

### 前端新增

```
frontend/
├── src/
│   ├── hooks/
│   │   └── useChat.ts                ✅ 新增（SSE 版本）
│   └── lib/
│       └── sse-client.ts             ✅ 新增（可选）
```

### AI Orchestrator 删除

```
ai-orchestrator/app/
├── core/
│   └── routing.py                    ❌ 删除
├── nodes/                            ❌ 删除整个目录
│   ├── router.py
│   ├── planner.py
│   ├── executor.py
│   ├── analyzer.py
│   ├── respond.py
│   └── ...
├── modules/
│   ├── ad_creative/                  ✅ 保留（简化内部）
│   │   ├── generators/               ❌ 删除（合并到 service.py）
│   │   ├── analyzers/                ❌ 删除（合并到 service.py）
│   │   ├── managers/                 ❌ 删除（合并到 service.py）
│   │   ├── extractors/               ❌ 删除（合并到 service.py）
│   │   └── utils/                    ❌ 删除（合并到 utils.py）
│   ├── market_insights/              ✅ 保留（简化内部）
│   │   ├── analyzers/                ❌ 删除（合并到 service.py）
│   │   ├── fetchers/                 ❌ 删除（合并到 service.py）
│   │   ├── trackers/                 ❌ 删除（合并到 service.py）
│   │   └── utils/                    ❌ 删除（合并到 utils.py）
│   ├── ad_performance/               ✅ 保留（简化内部）
│   │   ├── fetchers/                 ❌ 删除（合并到 service.py）
│   │   ├── analyzers/                ❌ 删除（合并到 service.py）
│   │   ├── exporters/                ❌ 删除（合并到 service.py）
│   │   └── utils/                    ❌ 删除（合并到 utils.py）
│   ├── landing_page/                 ✅ 保留（简化内部）
│   │   ├── generators/               ❌ 删除（合并到 service.py）
│   │   ├── managers/                 ❌ 删除（合并到 service.py）
│   │   ├── optimizers/               ❌ 删除（合并到 service.py）
│   │   ├── tracking/                 ❌ 删除（合并到 service.py）
│   │   ├── extractors/               ❌ 删除（合并到 service.py）
│   │   └── utils/                    ❌ 删除（合并到 utils.py）
│   └── campaign_automation/          ✅ 保留（简化内部）
│       ├── managers/                 ❌ 删除（合并到 service.py）
│       ├── optimizers/               ❌ 删除（合并到 service.py）
│       ├── engines/                  ❌ 删除（合并到 service.py）
│       ├── clients/                  ❌ 删除（合并到 service.py）
│       ├── adapters/                 ✅ 保留（平台适配器）
│       └── utils/                    ❌ 删除（合并到 utils.py）
```

### AI Orchestrator 新增

```
ai-orchestrator/app/
├── modules/
│   └── creative_intelligence/        ✅ 新增（合并模块）
│       ├── capability.py
│       ├── service.py
│       ├── models.py
│       └── utils.py
```

---

---

## 实施步骤（Implementation Steps）

### Phase 1: 前端 SSE 迁移

**目标**：移除 Vercel AI SDK，使用原生 SSE

1. 创建新的 `useChat.ts` hook（使用 EventSource）
2. 更新 ChatWindow 组件使用新 hook
3. 删除 `ai` 包依赖
4. 删除 `frontend/src/app/api/chat/route.ts`
5. 删除 WebSocket 相关代码
6. 测试聊天功能

**验收**：
- ✅ 聊天功能正常
- ✅ 流式响应正常
- ✅ 嵌入式组件渲染正常
- ✅ 前端包大小减少

---

### Phase 2: AIhestrator v3 迁移

**目标**：删除 v2 架构，只保留 v3

1. 验证 v3 功能完整性
2. 重命名 `app/core/graph_v3.py` → `app/core/gra
3. 删除 `app/core/routing.py`
4. 删除 `app/nodes/` 目录（除 persist.py）
5. 移动 `app/nodes/persist.py` → `app/core/persist.py`
6. 更新 `app/main.py` 只初始化 v3
7. 删除 v2 相关测试
8. 运行所有测试

**验收**：
- ✅ 所有测试通过
- ✅ 启动时间减少 50%+
- ✅ Chat API 正常工作

---

### Phase 3: 简化 Ad Creative Module

**目标**：合并内部子目录到 service.py
`service.py`
2. 将 `generators/` 的逻辑合并到 service.py
3. 将 `analyzers/` 的逻辑合并到 service.py
4. 将 `managers/` 的逻辑合并到 service.py
5. 将 `extractors/` 的逻辑合并到 service.py
6. 合并 `utils/` 到 `utils.py`
7. 更新 `capability.py` 使用新 service
8. 删除旧的子目录
9. 更新测试
10. 运行测试验证

**验收**：
- ✅ 所有功能正常
- ✅ 测试通过
- ✅ 文件数量减少 70%+

---

### Phase 4: 简化 Market Insights Module

**目标**：合并内部子目录到 service.py

1. 创建新的 `service.py`
2. 将 `analyzers/` 的逻辑合并到 service.py
3. 将 `fetchers/` 的逻辑合并到 service.py
4. 将 `trackers/` 的逻辑合并到 service.py
5. 合并 `utils/` 到 `utils.py`
6. 更新 `capability.py`
7. 删除旧的子目录
8. 更新测试
9. 运行测试验证

**验收**：
- ✅ 所有功能正常
- ✅ 测试通过

---

### Phase 5:ormance Module

**目标**：合并内部子目录到 service.py

1. 创建新的 `service.py`
2. 将 `fetchers/` 的逻辑合并到 service.py
3. 将 `analyzers/` 的逻辑合并到 service.py
4. 将 `exporters/` 的逻辑合并到 service.py
5. 合并 `utils/` 到 `utils.py`
6. 更新 `capability.py`
7. 删除旧的子目录
8. 更新测试
9. 运行测试验证

**验收**：
- ✅ 所有功能正常
- ✅ 测试通过

---

### Phase 6: 简化 Landing Page Module

**目标**：合并内部子目录到 service.py

1. 创建新的 `service.py`
2. 将 `generators/` 的逻辑合并到 service.py
3. 将 `managers/` 的逻辑合并到 service.py
4. 将 `optimizers/` 的逻辑合并到 service.py
5. 将 `tracking/` 的逻辑合并到 service.py6. 将 `extractors/` 的逻辑合并到 service.py
7. 合并 `utils/` 到 `utils.py`
8. 更新 `capability.py`
9. 删除旧的子目录
10. 更新测试
11. 运行测试验证

**验收**：
- ✅ 所有功能正常
- ✅ 测试通过

---

### Phase 7: 简化 Campaign Automation Module

**目标**：合并内部子目录到 service.py（保留 adapters/）

1. 创建新的 `service.py`
2. 将 `managers/` 的逻辑合并到 service.py
3. 将 `optimizers/` 的逻辑合并到 service.py
4. 将 `engines/` 的逻辑合并到 service.py
5. 将 `clients/` 的逻辑合并到 service.py
6. 合并 `utils/` 到 `utils.py`
7. **保留** `adap` 目录
8. 更新 `capability.py`
9. 删除旧的子目录（除 adapters/）
10. 更新测试
11. 运行测试验证

**验收**：
- ✅ 所有功能正常
- ✅ 测试通过
- ✅ adapters/ 保留

---

### Phase 8: 更新文档

**目标**：文档反映简化后的架构

1. 更新 `.kiro/specs/ARCHITECTURE.md`
2. 更新 `ai-orchestrator/README.md`
3. 更新 `frontend/README.md`
4. 删除过时的架构图
5. 创建迁移指南
6. 更新 API 文档

**验收**：
- ✅ 所有文档更新
- ✅ 架构图正确

---

### Phase 9: 最终验证

**目标**：确保整个系统正常工作

1. 运行所有测试（前端 + 后端 + AI Orchestrator）
2. 手动测试完整用户流程
3. 性能测试（启动时间、响应速度）
4. 代码审查
5. 部署到测试环境
6. 用户验收测试
- ✅ 所有测试通过
- ✅ 用户流程正常
- ✅ 性能指标达标
- ✅ 代码质量良好

---

## 风险与缓解（Risks and Mitigation）

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| SSE 实现不稳定 | 高 | 低 | 充分测试，参考成熟实现 |
| 模块简化导致功能丢失 | 高 | 中 | 仔细审查，保留所有核心功能 |
| v2 删除导致回滚困难 | 中 | 低 | 使用 Git 分支，分阶段迁移 |
| 测试失败 | 中 | 中 | 更新测试用例，保持覆盖率 |
| 性能下降 | 中 | 低 | 性能测试，优化瓶颈 |

---

## 成功指标（Success Metrics）

### 代码简化

- ✅ 总代码行数减少 30%+
- ✅ 文件数量减少 50%+
- ✅ 每个模块只有 4-5 个文件

### 性能提升

- ✅ AI Orchestrator 启动时间减少 50%+
- ✅ 前端包大小减少 20%+
- ✅ 响应速度保持或提升

### 可维护性

- ✅ 新开50%
- ✅ Bug 修复时间减少 30%
- ✅ 代码审查时间减少 40%

### 架构清晰度

- ✅ 5 个独立模块，职责清晰
- ✅ 每个模块结构一致
- ✅ 代码路径简单，易于理解


## Sub-Agent 工作流程示例

### 示例 1：Ad Performance Agent 按需抓取数据

```
用户: "我的广告表现如何？"

1. Main Orchestrator (Gemini)
   → 识别意图：查询广告性能
   → 调用 ad_performance_agent

2. Ad Performance Agent (Sub-Agent)
   → 理解任务：需要获取最新数据并分析
   
   → [MCP Tool] 调用 fetch_ad_data(platform="meta", date_range="last_7_days")
   → Backend 从 Meta API 抓取数据，返回原始数据
   
   → [AI 能力] Agent 使用 Gemini 分析数据
   → Gemini 理解数据模式、识别异常、生成洞察
   
   → [AI 能力] Agent 使用 Gemini 生成建议
   → Gemini 生成优化建议（暂停低效 Adset、增加预算等）

3. 返回用户
   → "📊 近 7 天表现：花费 $87.50，ROAS 2.8
      ⚠️ Adset X 表现较差（ROAS 1.8），建议暂停
      💡 Adset Y 表现优秀（ROAS 4.2），建议增加预算"
```

**关键点**：
- ✅ **MCP Tool** 只负责抓取数据（确定性操作）
- ✅ **AI 能力** 负责分析和生成建议（智能决策）
- ✅ Agent 根据用户意图决定调用哪些 Tools

### 示例 2：Ad Creative Agent 生成图片素材

```
用户: "帮我生成一个现代风格的广告图片"

1. Main Orchestrator (Gemini Function Calling)
   → 识别意图：生成素材
   → 调用 ad_creative_agent

2. Ad Creative Agent (Sub-Agent)
   → 理解任务：生成现代风格图片
   
   → [AI 能力] Agent 使用 Gemini 理解"现代风格"
   → 分析用户意图，提取关键词
   → 决定最佳的 Imagen 参数（风格、色调、构图）
   
   → [AI 能力] Agent 优化 prompt
   → 使用 Gemini 重写 prompt，提升生成质量
   → 例如："A modern, minimalist product photo with clean lines..."
   
   → [AI 能力] 调用 Gemini Imagen 生成图片
   → 使用优化后的 prompt 和参数
   → 生成高质量图片，返回 URL
   
   → [MCP Tool] 调用 save_creative(image_url, metadata)
   → Backend 下载图片，上传到 S3
   → Backend 保存素材元数据到数据库
   → 返回 creative_id

3. 返回用户
   → "✅ 素材已生成！
      [显示图片预览]
      已保存到素材库，ID: creative-123"
```

### 示例 2.5：Ad Creative Agent 生成视频素材

```
用户: "帮我生成一个 15 秒的产品展示视频"

1. Main Orchestrator
   → 调用 ad_creative_agent

2. Ad Creative Agent
   → 理解任务：生成产品展示视频
   
   → [AI 能力] Agent 使用 Gemini 理解需求
   → 分析"产品展示"的含义
   → 决定视频脚本和镜头设计
   
   → [AI 能力] Agent 生成视频脚本
   → 使用 Gemini 生成分镜脚本
   → 优化视频 prompt
   
   → [AI 能力] 调用 Gemini Veo 生成视频
   → 使用优化后的 prompt
   → 生成 15 秒视频，返回 URL
   
   → [MCP Tool] 调用 save_creative(video_url, metadata)
   → Backend 下载视频，上传到 S3
   → Backend 保存到数据库

3. 返回用户
   → "✅ 视频已生成！
      [显示视频预览]
      时长：15 秒
      已保存到素材库，ID: creative-456"
```

**关键点**：
- ✅ **AI 能力**：理解意图、生成脚本、生成视频（Gemini Veo）
- ✅ **MCP Tool**：只负责保存数据
- ✅ Agent 负责所有智能决策

### 示例 3：Landing Page Agent 生成多语言页面

```
用户: "帮我生成一个落地页，要支持中英文"

1. Main Orchestrator
   → 调用 landing_page_agent

2. Landing Page Agent
   → 理解任务：生成支持多语言的落地页
   
   → [MCP Tool] 调用 get_product_info(product_id)
   → Backend 返回产品信息
   
   → [AI 能力] Agent 使用 Gemini 生成页面内容
   → 生成中文版本的 HTML/CSS
   → 生成英文版本的 HTML/CSS
   → 生成语言切换 JavaScript 代码
   
   → [MCP Tool] 调用 save_landing_page(html, metadata)
   → Backend 保存到数据库
   
   → [MCP Tool] 调用 upload_to_s3(html)
   → Backend 上传到 S3，返回 URL

3. 返回用户
   → "✅ 落地页已生成：https://example.com/page-123
      支持中文和英文切换（右上角语言按钮）"
```

**关键点**：
- ✅ **AI 能力**：生成页面内容、翻译、设计布局（Gemini）
- ✅ **MCP Tool**：获取产品信息、保存页面、上传文件
- ✅ 多语言是页面本身的功能，由 Agent 生成

### 示例 4：Campaign Automation Agent 创建广告

```
用户: "用这个素材创建广告，预算 $100，目标是转化"

1. Main Orchestrator
   → 调用 campaign_automation_agent

2. Campaign Automation Agent
   → 理解任务：创建广告
   
   → [MCP Tool] 调用 get_creative(creative_id)
   → Backend 返回素材信息
   
   → [AI 能力] Agent 使用 Gemini 优化广告参数
   → 分析"目标是转化"，决定使用 CONVERSIONS 目标
   → 根据预算建议最佳的出价策略
   → 生成广告文案和标题
   
   → [MCP Tool] 调用 create_campaign(campaign_data)
   → Backend 调用 Meta API 创建广告
   → 返回 campaign_id

3. 返回用户
   → "✅ 广告已创建！
      Campaign ID: 123456789
      目标：转化
      出价策略：最低成本
      预计 CPA：$15-20"
```

**关键点**：
- ✅ **AI 能力**：理解目标、优化参数、生成文案（Gemini）
- ✅ **MCP Tool**：获取素材、创建广告（确定性操作）
- ✅ Agent 负责智能决策，Tool 负责执行

---

## Sub-Agent 与 MCP Tools 的关系

### 架构层次

```
用户对话
    ↓
Main Orchestrator (Gemini Function Calling)
    ↓
Sub-Agent (智能决策层)
    ↓
MCP Tools (执行层)
    ↓
Backend Services (数据层)
    ↓
Database / External APIs
```

### 每个 Sub-Agent 的能力划分

**关键原则**：
- ✅ **AI 能力**：Agent 直接调用大模型（Gemini）完成
- ✅ **MCP Tools**：只用于与后台数据交互（读取/保存数据）

#### Ad Creative Agent

**AI 能力**（调用 Gemini）：
- `generate_image()` - 生成图片（Gemini Imagen）
- `generate_video()` - 生成视频（Gemini Veo）
- `analyze_creative()` - 分析素材质量（Gemini Vision）
- `score_creative()` - 评分素材（Gemini 分析）
- `extract_product_info()` - 理解产品信息（Gemini 理解网页）

**MCP Tools**（与后台交互）：
- `save_creative` - 保存素材到素材库
- `get_creative` - 从素材库获取素材
- `list_creatives` - 列出用户的素材

#### Market Insights Agent

**AI 能力**（调用 Gemini）：
- `analyze_competitor()` - 分析竞品（Gemini 分析网页）
- `analyze_trends()` - 分析趋势（Gemini 理解数据）
- `generate_strategy()` - 生成策略（Gemini 生成建议）
- `analyze_audience()` - 分析受众（Gemini 分析）

**MCP Tools**（与后台交互）：
- `fetch_competitor_data` - 获取竞品数据
- `fetch_market_data` - 获取市场数据
- `save_analysis` - 保存分析结果

#### Ad Performance Agent

**AI 能力**（调用 Gemini）：
- `analyze_performance()` - AI 分析性能（Gemini 分析数据）
- `detect_anomaly()` - 检测异常（Gemini 识别异常模式）
- `generate_recommendations()` - 生成建议（Gemini 生成优化建议）
- `explain_metrics()` - 解释指标（Gemini 自然语言解释）

**MCP Tools**（与后台交互）：
- `fetch_ad_data` - 抓取广告数据（从 Meta/TikTok API）
- `get_historical_data` - 获取历史数据
- `save_report` - 保存报表

#### Landing Page Agent

**AI 能力**（调用 Gemini）：
- `generate_page_content()` - 生成页面内容（Gemini 生成 HTML/CSS）
- `optimize_copy()` - 优化文案（Gemini 改写）
- `translate_content()` - 翻译内容（Gemini 翻译）
- `design_layout()` - 设计布局（Gemini 生成设计）

**MCP Tools**（与后台交互）：
- `save_landing_page` - 保存落地页到数据库
- `get_landing_page` - 获取落地页
- `upload_to_s3` - 上传文件到 S3
- `create_ab_test_record` - 创建 A/B 测试记录

#### Campaign Automation Agent

**AI 能力**（调用 Gemini）：
- `optimize_budget()` - AI 预算优化建议（Gemini 分析数据）
- `suggest_targeting()` - 建议受众定向（Gemini 分析）
- `recommend_bid_strategy()` - 建议出价策略（Gemini 建议）

**MCP Tools**（与后台交互）：
- `create_campaign` - 创建广告（调用 Meta/TikTok API）
- `update_campaign` - 更新广告
- `get_campaign` - 获取广告信息
- `pause_campaign` - 暂停广告
- `apply_rules` - 应用自动化规则

### Sub-Agent 的智能决策能力

每个 Sub-Agent 的核心是**使用大模型进行智能决策**：

```python
# ai-orchestrator/app/modules/ad_creative/capability.py

class AdCreativeAgent(BaseAgent):
    """广告素材生成 Agent。"""
    
    def __init__(self):
        self.gemini_client = get_gemini_client()  # 大模型客户端
        self.mcp_client = get_mcp_client()        # MCP 工具客户端
    
    async def execute(self, action: str, params: dict, context: AgentContext):
        """执行任务。"""
        
        if action == "generate_image":
            # 1. [AI 能力] 理解用户意图
            intent = await self.gemini_client.understand_intent(
                user_input=params.get("description"),
                context="ad_creative_generation",
            )
            
            # 2. [AI 能力] 优化 prompt 和参数
            optimized_prompt = await self.gemini_client.optimize_prompt(
                product_info=params.get("product_info"),
                style=params.get("style"),
                target_audience=params.get("audience"),
            )
            
            # 3. [AI 能力] 调用 Gemini Imagen 生成图片
            image_url = await self.gemini_client.generate_image(
                prompt=optimized_prompt,
                aspect_ratio=params.get("aspect_ratio", "1:1"),
                style_preset=intent.style_preset,
            )
            
            # 4. [MCP Tool] 保存到素材库
            creative_id = await self.mcp_client.call_tool(
                "save_creative",
                {
                    "url": image_url,
                    "type": "image",
                    "metadata": {
                        "prompt": optimized_prompt,
                        "style": params.get("style"),
                    },
                    "user_id": context.user_id,
                }
            )
            
            return AgentResult(
                success=True,
                data={"creative_id": creative_id, "url": image_url},
                message=f"✅ 素材已生成并保存到素材库！",
            )
```

**关键架构原则**：
- ✅ **Agent 的核心价值**���使用大模型进行智能决策
- ✅ **MCP Tools 的作用**：与后台数据交互（CRUD 操作）
- ✅ **不要过度使用 MCP Tools**：AI 能做的事情让 AI 做
- ✅ **MCP Tools 只做确定性操作**：读取数据、保存数据、调用外部 API

---

## 定时任务 vs Agent 调用

### 两种调用方式对比

| 场景 | 调用方式 | 原因 |
|------|---------|------|
| 用户问"我的广告表现如何？" | ✅ Agent 调用 `fetch_ad_data` | 按需抓取，实时响应 |
| 每天自动生成报表 | ⚠️ Backend Celery 任务 | 定时任务，无需对话 |
| 用户问"帮我生成素材" | ✅ Agent 调用 `generate_image` | 需要理解产品信息 |
| 每小时检查 Token 过期 | ⚠️ Backend Celery 任务 | 系统维护，无需对话 |

### 建议的混合架构

**Agent 调用**（对话驱动）：
- 用户主动查询性能
- 用户要求生成素材/落地页
- 用户要求创建/优化广告
- 用户要求分析竞品

**Backend 定时任务**（系统维护）：
- 每天自动生成报表（可选）
- Token 过期检查
- 数据备份
- 系统健康检查

**推荐**：
- ✅ 优先使用 Agent 调用（更灵活）
- ✅ 定时任务只用于系统维护
- ✅ 如果用户想要"每天自动报表"，可以通过 Agent 设置规则，然后由 Backend 执行

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 聊天功能完整性
*For any* 有效的用户消息，简化后的前端系统 SHALL 能够发送消息并接收 AI 流式响应，保持与简化前相同的功能
**Validates: Requirements 1.6**

### Property 2: 模块功能保持不变
*For any* 有效的模块功能调用，简化后的系统 SHALL 返回与简化前相同格式和内容的结果
**Validates: Requirements 3.5**

---

## 测试策略（Testing Strategy）

### Unit Testing

使用 pytest 进行单元测试：

**前端测试**（可选）：
- SSE 连接建立和断开
- 消息发送和接收
- 错误处理

**AI Orchestrator 测试**：
- Orchestrator 节点逻辑
- Sub-Agent 执行逻辑
- MCP Tool 调用
- 错误处理

**模块测试**：
- 每个模块的 service.py 方法
- 数据模型验证
- 工具函数

### Property-Based Testing

使用 Hypothesis 进行属性测试：

**Property 1 测试**：
```python
# tests/test_chat_functionality_property.py

from hypothesis import given, strategies as st

@given(
    message=st.text(min_size=1, max_size=1000),
    user_id=st.uuids(),
    session_id=st.uuids(),
)
@pytest.mark.asyncio
async def test_chat_functionality_preserved(message, user_id, session_id):
    """测试聊天功能完整性。
    
    Feature: architecture-simplification, Property 1
    """
    # 发送消息
    response = await send_message(message, user_id, session_id)
    
    # 验证响应格式
    assert "session_id" in response
    assert response["session_id"] == session_id
    
    # 验证 SSE 流
    events = []
    async for event in receive_sse_stream(session_id):
        events.append(event)
    
    # 验证至少收到响应
    assert len(events) > 0
    assert any(e["type"] == "content" for e in events)
    assert any(e["type"] == "done" for e in events)
```

**Property 2 测试**：
```python
# tests/test_module_functionality_property.py

@given(
    action=st.sampled_from(["generate_image", "analyze_creative", "score_creative"]),
    params=st.fixed_dictionaries({
        "product_url": st.just("https://example.com/product"),
        "style": st.sampled_from(["modern", "minimal", "bold"]),
    }),
)
@pytest.mark.asyncio
async def test_module_functionality_preserved(action, params):
    """测试模块功能保持不变。
    
    Feature: architecture-simplification, Property 2
    """
    # 调用简化后的模块
    result = await ad_creative_agent.execute(action, params, context)
    
    # 验证结果格式
    assert result.success is not None
    assert "data" in result or "error" in result
    
    # 验证核心功能
    if result.success:
        assert result.data is not None
```

### Integration Testing

**端到端测试**：
- 完整的用户对话流程
- 跨模块协作（如：生成素材 → 创建广告）
- SSE 流式响应
- 错误处理和恢复

**性能测试**：
- 启动时间测量
- 响应延迟测量
- 并发请求测试
- 内存使用测量

---


## AI 能力 vs MCP Tools 对比

### 设计原则

| 类型 | 职责 | 实现方式 | 示例 |
|------|------|---------|------|
| **AI 能力** | 智能决策、内容生成、数据分析 | 调用 Gemini API | 生成图片、分析性能、优化参数 |
| **MCP Tools** | 数据交互、确定性操作 | 调用 Backend API | 保存素材、获取数据、创建广告 |

### 各模块的能力划分

#### Ad Creative Agent

| 功能 | 类型 | 实现 | 说明 |
|------|------|------|------|
| 生成图片 | AI 能力 | Gemini Imagen | Agent 优化 prompt 后调用 |
| 生成视频 | AI 能力 | Gemini Veo | Agent 优化 prompt 后调用 |
| 生成变体 | AI 能力 | Gemini Imagen/Veo | 基于原素材生成变体 |
| 分析素材质量 | AI 能力 | Gemini Vision | 分析清晰度、吸引力等 |
| 评分素材 | AI 能力 | Gemini 分析 | 给出 0-100 分数 |
| 提取产品信息 | AI 能力 | Gemini 理解网页 | 从 URL 提取产品信息 |
| 优化 prompt | AI 能力 | Gemini 重写 | 优化生成效果 |
| **保存素材** | **MCP Tool** | **Backend API** | 保存到素材库 |
| **获取素材** | **MCP Tool** | **Backend API** | 从素材库读取 |
| **列出素材** | **MCP Tool** | **Backend API** | 列出用户素材 |

#### Market Insights Agent

| 功能 | 类型 | 实现 |
|------|------|------|
| 分析竞品 | AI 能力 | Gemini 分析网页 |
| 分析趋势 | AI 能力 | Gemini 分析数据 |
| 生成策略 | AI 能力 | Gemini 生成建议 |
| 分析受众 | AI 能力 | Gemini 分析 |
| **获取竞品数据** | **MCP Tool** | **Backend 爬虫** |
| **获取市场数据** | **MCP Tool** | **Backend API** |
| **保存分析结果** | **MCP Tool** | **Backend API** |

#### Ad Performance Agent

| 功能 | 类型 | 实现 |
|------|------|------|
| 分析性能 | AI 能力 | Gemini 分析数据 |
| 检测异常 | AI 能力 | Gemini 识别模式 |
| 生成建议 | AI 能力 | Gemini 生成建议 |
| 解释指标 | AI 能力 | Gemini 自然语言 |
| **抓取广告数据** | **MCP Tool** | **Backend 调用平台 API** |
| **获取历史数据** | **MCP Tool** | **Backend 数据库** |
| **保存报表** | **MCP Tool** | **Backend API** |

#### Landing Page Agent

| 功能 | 类型 | 实现 |
|------|------|------|
| 生成页面内容 | AI 能力 | Gemini 生成 HTML/CSS |
| 优化文案 | AI 能力 | Gemini 改写 |
| 翻译内容 | AI 能力 | Gemini 翻译 |
| 设计布局 | AI 能力 | Gemini 生成设计 |
| **获取产品信息** | **MCP Tool** | **Backend API** |
| **保存落地页** | **MCP Tool** | **Backend API** |
| **上传到 S3** | **MCP Tool** | **Backend S3** |
| **创建 A/B 测试记录** | **MCP Tool** | **Backend API** |

#### Campaign Automation Agent

| 功能 | 类型 | 实现 |
|------|------|------|
| 优化预算建议 | AI 能力 | Gemini 分析数据 |
| 建议受众定向 | AI 能力 | Gemini 分析 |
| 建议出价策略 | AI 能力 | Gemini 建议 |
| 生成广告文案 | AI 能力 | Gemini 生成 |
| **创建广告** | **MCP Tool** | **Backend 调用平台 API** |
| **更新广告** | **MCP Tool** | **Backend 调用平台 API** |
| **获取广告信息** | **MCP Tool** | **Backend API** |
| **暂停广告** | **MCP Tool** | **Backend 调用平台 API** |
| **应用规则** | **MCP Tool** | **Backend 规则引擎** |

### 关键洞察

**什么时候使用 AI 能力？**
- ✅ 需要理解自然语言
- ✅ 需要生成内容（文本、图片、视频）
- ✅ 需要分析和洞察
- ✅ 需要优化和建议
- ✅ 需要智能决策

**什么时候使用 MCP Tools？**
- ✅ 需要读取系统数据
- ✅ 需要保存数据到数据库
- ✅ 需要调用外部 API（Meta/TikTok）
- ✅ 需要上传文件到 S3
- ✅ 需要执行确定性操作

**错误的设计**：
- ❌ 把 AI 能力包装成 MCP Tool（如 `analyze_performance` tool）
- ❌ 让 Backend 做 AI 分析（Backend 应该只做数据操作）
- ❌ Agent 只是简单的 API 包装器

**正确的设计**：
- ✅ Agent 直接调用 Gemini 进行 AI 操作
- ✅ MCP Tools 只负责数据交互
- ✅ Agent 是真正的智能体，有决策能力

---
