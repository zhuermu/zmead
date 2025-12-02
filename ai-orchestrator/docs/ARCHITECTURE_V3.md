# AI Orchestrator Architecture v3.0

## 概述

v3.0 架构采用 **Agents-as-Tools** 模式，利用 Gemini 3 Pro 的原生能力简化整体流程：

- **原生图片生成**：直接使用 Gemini 的 `responseModalities=["TEXT", "IMAGE"]`
- **原生视频生成**：使用 Veo 3.1 API
- **Function Calling**：将 Sub-Agents 暴露为可调用函数
- **简化的 Graph**：从多节点流程简化为单一 Orchestrator 节点

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    Gemini 3 Pro (主 Agent)                       │
│                                                                  │
│  原生能力：                                                       │
│  ├── 对话理解与推理                                               │
│  ├── 图片生成 (gemini-2.5-flash-image / gemini-3-pro-image)      │
│  ├── 视频生成 (Veo 3.1)                                          │
│  └── 复杂推理 (thinking_level=high)                              │
│                                                                  │
│  Function Calling (Sub-Agents)：                                 │
│  ├── creative_agent()      - 素材生成、保存                       │
│  ├── performance_agent()   - 报表、分析、建议                     │
│  ├── market_agent()        - 竞品分析、市场趋势                   │
│  ├── landing_page_agent()  - 落地页生成                          │
│  └── campaign_agent()      - 广告投放自动化                       │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    Backend (MCP Protocol)
```

## 核心组件

### 1. Gemini 3 Client (`app/services/gemini3_client.py`)

统一的 Gemini 3 客户端，支持：

```python
from app.services.gemini3_client import get_gemini3_client

client = get_gemini3_client()

# 文本对话
response = await client.chat(messages=[...])

# 原生图片生成
image_bytes = await client.generate_image(
    prompt="专业广告图片",
    aspect_ratio=AspectRatio.SQUARE,
    image_size=ImageSize.SIZE_2K,
)

# 视频生成
result = await client.generate_video(
    prompt="产品展示视频",
    duration=4,
)

# Function Calling
result = await client.chat_with_tools(
    messages=[...],
    tools=[creative_agent_tool, performance_agent_tool, ...],
    tool_handlers={...},
)
```

**模型配置**：

| 用途 | 模型名 | 说明 |
|-----|-------|------|
| 对话/推理 | `gemini-3-pro-preview` | 支持 function calling 和 thinking mode |
| 图片生成 | `gemini-2.5-flash-image` | 快速图片生成 |
| 高质量图片 | `gemini-3-pro-image-preview` | 4K 分辨率 |
| 视频生成 | `veo-3.1-generate-preview` | 4-8 秒视频 |
| 快速视频 | `veo-3.1-fast-generate-preview` | 快速生成 |

### 2. Sub-Agents (`app/agents/`)

每个 Agent 继承 `BaseAgent`，实现 `execute` 方法：

```python
class CreativeAgent(BaseAgent):
    name = "creative_agent"
    description = "生成广告素材..."

    async def execute(
        self,
        action: str,
        params: dict,
        context: AgentContext,
    ) -> AgentResult:
        if action == "generate_image":
            return await self._generate_image(params, context)
        elif action == "generate_video":
            return await self._generate_video(params, context)
        ...
```

**可用 Agents**：

| Agent | 功能 |
|-------|------|
| `creative_agent` | 图片/视频生成、素材保存 |
| `performance_agent` | 报表、分析、异常检测、优化建议 |
| `market_agent` | 竞品分析、市场趋势、策略生成 |
| `landing_page_agent` | 落地页生成、翻译、A/B 测试 |
| `campaign_agent` | 创建广告、预算调整、暂停/恢复 |

### 3. Orchestrator (`app/core/orchestrator.py`)

主协调器，接收用户消息并调用 Sub-Agents：

```python
from app.core.orchestrator import get_orchestrator

orchestrator = get_orchestrator()

# 处理消息
result = await orchestrator.process_message(
    user_id="user123",
    session_id="session456",
    message="帮我生成 4 张广告图片",
)

# 流式响应
async for event in orchestrator.stream_message(...):
    print(event)
```

### 4. LangGraph v3 (`app/core/graph_v3.py`)

简化的状态图：

```
[START] → orchestrator → persist → [END]
```

所有复杂逻辑都在 `orchestrator` 节点内通过 Gemini function calling 处理。

## API 端点

### v3 Chat API

```
POST /api/v1/chat/v3
```

请求：
```json
{
  "content": "帮我生成 4 张广告图片",
  "user_id": "user123",
  "session_id": "session456",
  "history": []
}
```

响应：
```json
{
  "response": "已生成 4 张素材...",
  "success": true,
  "session_id": "session456"
}
```

### 流式响应

```
POST /api/v1/chat/v3/stream
```

返回 Server-Sent Events：
```
data: {"type": "text", "content": "正在生成..."}
data: {"type": "tool_call", "tool": "creative_agent", "args": {...}}
data: {"type": "tool_result", "result": {...}}
data: {"type": "done"}
```

### 列出 Agents

```
GET /api/v1/chat/v3/agents
```

## 与 v2 架构对比

| 方面 | v2 (旧) | v3 (新) |
|-----|---------|---------|
| Graph 节点 | 6 个 (router→planner→executor→analyzer→respond→persist) | 2 个 (orchestrator→persist) |
| 图片生成 | 通过 ImagenClient Tool | Gemini 原生能力 |
| 路由逻辑 | LLM 意图识别 + 条件路由 | Gemini function calling |
| 复杂度 | 高 | 低 |
| 扩展性 | 需要修改 Graph | 添加新 Agent 即可 |

## 配置

`.env` 文件：
```bash
# 主模型
GEMINI_MODEL_CHAT=gemini-3-pro-preview

# 图片生成
GEMINI_MODEL_IMAGEN=gemini-2.5-flash-image
GEMINI_MODEL_IMAGEN_PRO=gemini-3-pro-image-preview

# 视频生成
GEMINI_MODEL_VEO=veo-3.1-generate-preview
GEMINI_MODEL_VEO_FAST=veo-3.1-fast-generate-preview
```

## 添加新 Agent

1. 创建 Agent 类：
```python
# app/agents/my_agent.py
class MyAgent(BaseAgent):
    name = "my_agent"
    description = "..."

    async def execute(self, action, params, context):
        ...
```

2. 在 `app/agents/setup.py` 中注册：
```python
from app.agents.my_agent import get_my_agent

def register_all_agents():
    registry.register(get_my_agent())
```

3. Agent 会自动作为 Tool 暴露给 Gemini function calling。

## 参考文档

- [Gemini 3 API](https://ai.google.dev/gemini-api/docs/gemini-3)
- [Image Generation](https://ai.google.dev/gemini-api/docs/image-generation)
- [Video Generation](https://ai.google.dev/gemini-api/docs/video)
- [Function Calling](https://ai.google.dev/gemini-api/docs/function-calling)
