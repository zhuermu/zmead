# 对话记忆修复总结

## 问题描述

用户反馈：AI Agent 似乎只有最近一轮的对话记忆，无法记住之前的上下文。

## 根本原因分析

通过代码审查，发现了完整的数据流问题：

### 1. 前端（✅ 正常）
- **文件**: `frontend/src/hooks/useChat.ts`
- **行数**: 336-352
- **状态**: 前端正确发送了完整的对话历史数组
```typescript
const allMessages = [
  ...messages.map(msg => ({
    role: msg.role,
    content: getMessageContentAsString(msg),
  })),
  {
    role: 'user',
    content: content.trim(),
  }
];
```

### 2. 后端接收（❌ 问题）
- **文件**: `ai-orchestrator/app/api/chat.py`
- **行数**: 206-207
- **问题**: 只提取了最后一条消息
```python
# OLD (错误)
last_message_obj = request.messages[-1]  # 只取最后一条
```

### 3. Agent 调用（❌ 问题）
- **文件**: `ai-orchestrator/app/api/chat.py`
- **行数**: 389-395
- **问题**: 没有传递对话历史参数
```python
# OLD (错误)
async for event in agent.process_message_stream(
    user_message=last_message,  # 只传递当前消息
    # 缺少 conversation_history 参数
)
```

### 4. Strands Agent 执行（❌ 问题）
- **文件**: `ai-orchestrator/app/core/strands_enhanced_agent.py`
- **行数**: 326-335, 405
- **问题**: 方法不接受对话历史，只传递单条消息给模型
```python
# OLD (错误)
async def process_message_stream(
    self,
    user_message: str,
    user_id: str,
    session_id: str,
    # 缺少 conversation_history 参数
)

async for chunk in strands_agent.stream_async(state.user_message):  # 只传单条消息
```

### 5. 工具上下文（❌ 问题）
- **文件**: `ai-orchestrator/app/core/strands_enhanced_agent.py`
- **行数**: 633
- **问题**: 工具执行时的 context 中 conversation_history 为空数组
```python
# OLD (错误)
context = {
    "conversation_history": [],  # 空数组！
}
```

## 修复方案

### 修改 1: chat.py - 构建对话历史

**文件**: `ai-orchestrator/app/api/chat.py`

**新增代码** (第 209-216 行):
```python
# Build conversation history (all messages except the last one)
# Convert ChatMessage objects to simple dict format for agent
conversation_history = []
for msg in request.messages[:-1]:  # All messages except last (current)
    conversation_history.append({
        "role": msg.role,
        "content": msg.content,
    })
```

**修改调用** (第 398-405 行):
```python
async for event in agent.process_message_stream(
    user_message=last_message,
    user_id=request.user_id,
    session_id=request.session_id,
    conversation_history=conversation_history,  # ✅ 传递完整对话历史
    attachments=attachments,
    model_preferences=request.model_preferences,
):
```

### 修改 2: strands_enhanced_agent.py - 接受对话历史参数

**文件**: `ai-orchestrator/app/core/strands_enhanced_agent.py`

**修改方法签名** (第 326-359 行):
```python
async def process_message_stream(
    self,
    user_message: str,
    user_id: str,
    session_id: str,
    conversation_id: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,  # ✅ 新增参数
    loaded_tools: list[AgentTool] | None = None,
    attachments: list[dict] | None = None,
    model_preferences: Any = None,
) -> AsyncIterator[dict[str, Any]]:
    """Process message with streaming ReAct loop.

    Args:
        user_message: Current user message
        user_id: User identifier
        session_id: Session identifier
        conversation_id: Optional conversation identifier
        conversation_history: Previous conversation messages  # ✅ 新增文档
        loaded_tools: Pre-loaded tools (optional)
        attachments: File attachments
        model_preferences: User's model preferences
    ...
    """
```

### 修改 3: 构建完整消息数组传给 Strands Agent

**文件**: `ai-orchestrator/app/core/strands_enhanced_agent.py`

**新增代码** (第 409-431 行):
```python
# Build messages for Strands Agent (conversation history + current message)
# Strands Agent supports passing conversation history as a list of messages
messages_for_agent = []

# Add conversation history (if provided)
if conversation_history:
    for msg in conversation_history:
        messages_for_agent.append({
            "role": msg["role"],
            "content": msg["content"],
        })

# Add current user message
messages_for_agent.append({
    "role": "user",
    "content": state.user_message,
})

logger.info(
    "calling_strands_agent_with_history",
    history_length=len(conversation_history) if conversation_history else 0,
    total_messages=len(messages_for_agent),
)

# Call Strands Agent with full conversation history
async for chunk in strands_agent.stream_async(messages_for_agent):  # ✅ 传递完整历史
```

### 修改 4: 工具上下文传递对话历史

**文件**: `ai-orchestrator/app/core/strands_enhanced_agent.py`

**修改 _convert_tools_to_strands 签名** (第 623-630 行):
```python
def _convert_tools_to_strands(
    self,
    agent_tools: list[AgentTool],
    user_id: str,
    session_id: str,
    model_preferences: Any = None,
    conversation_history: list[dict[str, str]] | None = None,  # ✅ 新增参数
) -> list[Any]:
```

**修改工具上下文** (第 667-672 行):
```python
context = {
    "user_id": tool_context.invocation_state.get("user_id", user_id),
    "session_id": tool_context.invocation_state.get("session_id", session_id),
    "conversation_history": conversation_history or [],  # ✅ 传递真实历史
    "model_preferences": model_preferences,
}
```

**修改调用处** (第 394-397 行):
```python
# Convert tools to Strands format (pass conversation_history for tool context)
strands_tools = self._convert_tools_to_strands(
    loaded_tools, user_id, session_id, model_preferences, conversation_history  # ✅ 传递历史
)
```

## 修复效果

修复后，完整的对话流程：

```
用户第1轮对话: "我叫小明"
AI: "你好小明"

用户第2轮对话: "我叫什么名字？"
AI: "你叫小明"  ✅ 记住了第1轮的内容
```

### 数据流

```
Frontend (useChat.ts)
    ↓ 发送完整对话历史
    messages: [
      {role: "user", content: "我叫小明"},
      {role: "assistant", content: "你好小明"},
      {role: "user", content: "我叫什么名字？"}
    ]
    ↓
Backend (chat.py)
    ↓ 提取历史 + 当前消息
    conversation_history: [
      {role: "user", content: "我叫小明"},
      {role: "assistant", content: "你好小明"}
    ]
    current_message: "我叫什么名字？"
    ↓
Agent (strands_enhanced_agent.py)
    ↓ 构建完整消息数组
    messages_for_agent: [
      {role: "user", content: "我叫小明"},
      {role: "assistant", content: "你好小明"},
      {role: "user", content: "我叫什么名字？"}
    ]
    ↓
Strands Agent
    ↓ 传递给底层模型（Bedrock/Gemini）
    Model receives full conversation history
    ↓
Model Response: "你叫小明"  ✅ 有完整上下文
```

## 测试要点

1. **多轮对话连贯性测试**:
   - 第1轮：告诉 AI 一些信息
   - 第2轮：询问第1轮提到的信息
   - 预期：AI 能够正确回忆

2. **工具调用上下文测试**:
   - 第1轮：让 AI 生成某个素材
   - 第2轮：引用第1轮的素材（"刚才那张图片"）
   - 预期：AI 知道"刚才"指的是什么

3. **长对话测试**:
   - 进行 5-10 轮对话
   - 预期：AI 能够记住所有之前的对话内容

4. **日志验证**:
   - 查看日志中的 `calling_strands_agent_with_history`
   - 确认 `history_length` 和 `total_messages` 正确

## 注意事项

1. **Token 限制**: 对话历史越长，消耗的 token 越多，需要注意模型的上下文窗口限制

2. **性能影响**: 每次请求都传递完整历史会增加请求大小，但对于正常对话（< 10 轮）影响可以接受

3. **Memory 系统**: 当前 Memory 系统（Redis）仍然在使用，用于持久化存储，但不再是唯一的记忆来源

4. **未来优化**: 可以考虑：
   - 实现对话摘要（summarization）来压缩长对话历史
   - 实现滑动窗口策略（只保留最近 N 轮对话）
   - 根据 token 预算动态调整历史长度

## 相关文件

- `frontend/src/hooks/useChat.ts` - 前端对话管理
- `ai-orchestrator/app/api/chat.py` - 后端 API 入口
- `ai-orchestrator/app/core/strands_enhanced_agent.py` - Agent 核心逻辑
- `ai-orchestrator/app/tools/base.py` - 工具基类（context 定义）

## 修复时间

2025-12-19

## 测试状态

✅ 代码修改完成
⏳ 等待实际测试验证
