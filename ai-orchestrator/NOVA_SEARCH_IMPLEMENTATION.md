# Amazon Nova Search 实现总结

## 实现位置
`ai-orchestrator/app/tools/strands_builtin_tools.py` - `NovaSearchTool` 类 (第483-659行)

## 实现原理

使用 **Amazon Bedrock Converse API** + **Nova Grounding** 系统工具实现网络搜索功能。

### 核心代码

```python
response = await asyncio.to_thread(
    client.converse,
    modelId="us.amazon.nova-lite-v1:0",
    messages=[
        {
            "role": "user",
            "content": [{"text": search_prompt}],
        }
    ],
    toolConfig={
        "tools": [
            {
                "systemTool": {
                    "name": "nova_grounding",
                }
            }
        ]
    },
    inferenceConfig={
        "temperature": 0.2,
        "maxTokens": 2048,
    },
)
```

## 关键特性

### 优势
1. **AWS 原生集成**：与 Bedrock 服务无缝集成，使用相同的 AWS 凭证
2. **统一计费**：与其他 Bedrock 服务统一计费，无需额外 API Key
3. **快速响应**：使用 Nova Lite 模型，响应速度快（~5-6秒）
4. **企业级安全**：符合 AWS 企业级安全和合规标准

### 局限性
1. **无结构化 Citations**：
   - Nova Grounding **不返回结构化的来源引用**（citations）
   - 返回的响应结构中没有 `citations` 字段
   - `sources_count` 始终为 0

2. **内联引用**：
   - 来源信息可能内联在生成的文本中
   - 无法自动提取为结构化的 URL 列表

## 响应结构

```json
{
  "ResponseMetadata": {...},
  "output": {
    "message": {
      "role": "assistant",
      "content": [
        {
          "text": "搜索结果摘要...（可能包含内联引用）"
        }
      ]
    }
  },
  "stopReason": "end_turn",
  "usage": {...},
  "metrics": {...}
}
```

**注意**：响应中不包含 `citations`、`retrievedReferences` 等结构化来源信息。

## 与 Google Search 对比

| 特性 | Google Search (Gemini) | Nova Search (Bedrock) |
|------|------------------------|------------------------|
| API | Gemini API | Bedrock Converse API |
| 模型 | gemini-2.5-flash | us.amazon.nova-lite-v1:0 |
| 结构化 Citations | ✅ 是 | ❌ 否 |
| 内联引用 | ✅ 是 | ✅ 是（推测） |
| 响应速度 | ~3-4秒 | ~5-6秒 |
| 来源提取 | 自动提取 | 无法提取 |
| AWS 集成 | 需要 Gemini API Key | AWS 原生 |

## 使用示例

**输入：**
```json
{
  "query": "猫粮品牌市场趋势",
  "language": "zh"
}
```

**输出：**
```json
{
  "success": true,
  "query": "猫粮品牌市场趋势",
  "summary": "根据市场调查，全球猫粮市场...（709字符）",
  "sources": [],  // 始终为空
  "sources_count": 0,
  "message": "搜索完成: 猫粮品牌市场趋势"
}
```

## 调试历程

### 问题 1: ValidationException 错误
**错误信息**：
```
Invalid Input: The input does not adhere to the expected standards.
```

**原因**：
使用了不正确的 `additionalModelRequestFields` 参数：
```python
# ❌ 错误的做法
additionalModelRequestFields={
    "inferenceConfig": {
        "grounding": {
            "includeSources": True,
        }
    }
}
```

**解决方案**：
移除 `additionalModelRequestFields`，使用默认配置。

### 问题 2: 无法获取 Citations
**尝试的方法**：
1. ✅ 检查 `response["citations"]` - 不存在
2. ✅ 检查 `response["output"]["message"]["citations"]` - 不存在
3. ✅ 检查 `response["trace"]` - 不存在
4. ✅ 检查 content blocks 中的 `reference` 或 `citation` - 不存在

**结论**：
Nova Grounding 目前不提供结构化的 citations 数据。这是 AWS Nova 的设计特性，不是实现问题。

## 配置要求

**环境变量**：
- `AWS_ACCESS_KEY_ID` 和 `AWS_SECRET_ACCESS_KEY`（或使用 IAM Role）
- `BEDROCK_REGION`：AWS 区域（默认 `us-west-2`）

**IAM 权限**：
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

## 未来改进方向

1. **文本解析**：开发算法从生成文本中提取内联引用（如 [1], [2] 标记）
2. **Citation 支持**：等待 AWS 添加结构化 citations 支持
3. **模型升级**：测试 Nova Pro 是否提供更详细的引用信息
4. **混合策略**：对于需要结构化来源的场景，自动切换到 Google Search

## 总结

✅ **功能状态**：完全可用
- 搜索功能正常工作
- 返回高质量的搜索摘要
- 适合需要快速获取信息但不严格要求结构化引用的场景

⚠️ **已知限制**：
- 无结构化 citations
- 无法自动提取来源 URL
- 适合内容研究，不适合学术引用

📌 **建议**：
- 对于需要明确来源的场景，使用 Google Search
- 对于快速信息获取和 AWS 集成场景，使用 Nova Search
