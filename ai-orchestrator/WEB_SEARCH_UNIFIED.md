# 统一 Web Search 实现总结

## 实现目标

创建统一的 `web_search` 工具，内部实现自动降级逻辑，对用户隐藏底层技术细节：
1. **优先使用** Amazon Nova Search（AWS 原生，快速）
2. **自动降级** Google Search（Gemini Grounding，作为备选）
3. **用户体验** 只显示"互联网搜索"，不显示具体提供商

## 实现架构

### 后端实现

**文件位置**: `ai-orchestrator/app/tools/strands_builtin_tools.py`

**核心类**: `WebSearchTool` (第669-772行)

```python
class WebSearchTool(AgentTool):
    """Unified web search tool with automatic fallback.

    1. First tries Amazon Nova Grounding (fast, AWS-native)
    2. Falls back to Google Search if Nova fails
    """

    def __init__(self):
        # 初始化两个搜索提供商
        self._nova_search = NovaSearchTool()
        self._google_search = GoogleSearchTool()

    async def execute(self, parameters, context):
        # 策略 1: 优先 Nova Search
        try:
            result = await self._nova_search.execute(parameters, context)
            return {**result, "provider": "nova"}
        except Exception as nova_error:
            log.warning("nova_search_failed", fallback="google_search")

            # 策略 2: 降级到 Google Search
            try:
                result = await self._google_search.execute(parameters, context)
                return {**result, "provider": "google"}
            except Exception as google_error:
                raise ToolExecutionError("Web search failed")
```

### 前端实现

**文件位置**: `frontend/src/components/chat/AgentProcessingCard.tsx`

**工具名称映射** (第22-39行):

```typescript
const getToolDisplayName = (toolName: string | undefined): string => {
  const toolNameMap: Record<string, string> = {
    'web_search': '互联网搜索',
    'google_search': '互联网搜索',
    'nova_search': '互联网搜索',
    'calculator': '计算器',
    'datetime': '日期时间',
    'generate_image_tool': '图片生成',
    'generate_video_tool': '视频生成',
    'create_campaign': '创建广告',
    'get_reports': '获取报告',
  };

  return toolNameMap[toolName] || toolName;
};
```

**应用位置**:
1. 第210行：工具执行中的副标题
2. 第302行：执行步骤标签
3. 第303行：结果步骤标签

## 执行流程

```
用户请求 "搜索2024年AI趋势"
    ↓
AI Agent 识别需要搜索
    ↓
调用 web_search 工具
    ↓
┌─────────────────────────┐
│  WebSearchTool.execute  │
└─────────────────────────┘
    ↓
尝试 Nova Search
    ├─ 成功 → 返回结果 (provider: nova)
    │
    └─ 失败 → 尝试 Google Search
              ├─ 成功 → 返回结果 (provider: google)
              └─ 失败 → 抛出错误
    ↓
前端显示 "互联网搜索"
（用户不知道使用了哪个提供商）
```

## 测试结果

### 日志验证

```log
✅ tool_registered - tool_name=web_search
✅ web_search_start - query='2024年AI行业最新趋势'
✅ trying_nova_search
✅ nova_search_start
✅ calling_bedrock_converse - model=us.amazon.nova-lite-v1:0
✅ bedrock_response_received
✅ nova_search_complete - result_length=607
✅ web_search_complete - provider=nova, success=True
✅ tool_execution_success - tool_name=web_search
```

### 用户界面

**工具调用显示**:
```
执行: 互联网搜索
结果: 互联网搜索
```

**不再显示**:
- ❌ "nova_search"
- ❌ "google_search"
- ❌ 任何技术细节

## 降级逻辑优势

### 自动容错
| 场景 | Nova 状态 | Google 状态 | 结果 |
|------|-----------|-------------|------|
| 正常 | ✅ 成功 | - | 使用 Nova ✅ |
| Nova 故障 | ❌ 失败 | ✅ 成功 | 自动切换到 Google ✅ |
| 全部故障 | ❌ 失败 | ❌ 失败 | 返回错误 ❌ |

### 性能优化
- **第一优先级**: Nova (AWS 原生，~5-6秒)
- **第二优先级**: Google (Gemini API，~3-4秒)
- **零配置**: 自动选择最佳提供商

### 用户体验
- **一致性**: 用户始终看到"互联网搜索"
- **透明度**: 不暴露技术实现细节
- **可靠性**: 双重备份确保服务可用性

## 内部监控

虽然用户看不到提供商，但系统内部完整记录：

```python
# 返回结果包含 provider 字段（仅供日志）
{
    "success": True,
    "query": "...",
    "summary": "...",
    "sources": [...],
    "provider": "nova"  # 或 "google" - 用于监控和调试
}
```

**监控指标**:
- Nova 成功率
- Google 降级频率
- 平均响应时间
- 错误类型分布

## 配置要求

### 环境变量

**Nova Search**:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `BEDROCK_REGION=us-west-2`

**Google Search**:
- `GEMINI_API_KEY`

### IAM 权限

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:Converse"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/us.amazon.nova-lite-v1:0"
    }
  ]
}
```

## 移除的工具

为了简化用户体验，以下工具已从工具列表中移除：
- ❌ `google_search` (合并到 web_search)
- ❌ `nova_search` (合并到 web_search)

**保留的工具列表**:
```python
[
    WebSearchTool(),      # 统一搜索（Nova → Google）
    CalculatorTool(),     # 计算器
    DateTimeTool(),       # 日期时间
]
```

## 未来改进

### 智能路由
根据查询类型选择最佳提供商：
- 实时新闻 → Nova (AWS最新数据)
- 技术文档 → Google (更全面的索引)
- 学术研究 → Google (citation support)

### 负载均衡
- 分配流量到不同提供商
- 避免单点故障
- 优化成本

### 缓存策略
- 相似查询缓存
- 减少API调用
- 提升响应速度

## 总结

✅ **实现完成**:
- 统一的 `web_search` 工具
- 自动 Nova → Google 降级
- 用户友好的中文名称映射
- 完整的日志和监控

✅ **用户体验**:
- 只看到"互联网搜索"
- 不关心底层技术
- 可靠的搜索服务

✅ **开发体验**:
- 清晰的降级逻辑
- 完整的错误处理
- 详细的日志记录
