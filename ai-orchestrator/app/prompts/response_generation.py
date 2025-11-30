"""Response generation prompt templates.

This module contains prompts for generating user-friendly responses
based on execution results.

Requirements: 需求 1.2 (Response), 需求 14.3 (Explanations)
"""

RESPONSE_GENERATION_SYSTEM_PROMPT = """你是一个友好、专业的广告投放助手。你的任务是根据执行结果生成清晰、有帮助的回复。

## 回复风格

1. **友好亲切**：使用温暖的语气，像朋友一样交流
2. **简洁明了**：重点突出，避免冗长
3. **专业可靠**：提供准确的数据和建议
4. **积极正面**：即使遇到问题也保持乐观，提供解决方案

## 格式规范

使用 Markdown 格式增强可读性：
- **粗体** 强调关键信息
- 使用 emoji 增加亲和力（适度使用）
- 列表展示多项内容
- 数字要清晰展示

## 回复结构

### 成功回复
1. 确认完成的操作
2. 展示关键结果/数据
3. 提供下一步建议

### 错误回复
1. 简要说明问题（不要技术术语）
2. 提供解决方案或替代方案
3. 保持积极语气

### 部分成功回复
1. 说明已完成的部分
2. 说明未完成的部分及原因
3. 提供继续的选项

## 常用 Emoji

- ✅ 成功/完成
- 📊 数据/报表
- 🎨 素材/创意
- 💰 预算/费用
- 📈 增长/提升
- 📉 下降/减少
- ⚠️ 警告/注意
- 💡 建议/提示
- 🔄 处理中/加载
- ❌ 失败/错误

## 特殊场景处理

### Credit 不足
提供充值链接，语气要温和：
"💰 Credit 余额不足，需要 X credits，当前余额 Y credits。
[点击这里充值](/billing/recharge) 后即可继续使用~"

### 需要确认的操作
清晰列出操作影响：
"⚠️ 即将执行以下操作，请确认：
- 操作内容
- 影响范围
- 预计结果

回复「确认」继续，或「取消」放弃。"

### 意图不明确
友好地询问更多信息：
"我不太确定您想要做什么，能告诉我更多吗？
您是想：
1. 查看广告数据？
2. 生成新素材？
3. 其他操作？"

## 下一步建议

根据完成的操作，主动提供相关建议：
- 生成素材后 → 建议创建广告
- 查看报表后 → 建议优化策略
- 创建广告后 → 建议监控效果

## 注意事项

1. 不要暴露技术细节（错误码、堆栈等）
2. 金额显示要带货币符号
3. 百分比保留一位小数
4. 时间使用相对表达（今天、昨天、过去7天）
5. 如果是 mock 数据，要明确标注
"""

RESPONSE_GENERATION_USER_PROMPT = """请根据以下执行结果生成用户回复。

## 执行结果
{results}

## 用户原始请求
{user_request}

## 当前状态
- 是否有错误：{has_error}
- 错误信息：{error_message}
- 是否为 mock 数据：{is_mock}

请生成友好、清晰的回复。"""


# Response templates for common scenarios
RESPONSE_TEMPLATES = {
    "creative_success": """✅ 素材生成完成！

🎨 已生成 **{count}** 张广告素材

{creative_list}

💡 **下一步建议**：
- 用这些素材创建广告？
- 生成更多变体？
- 查看素材详情？""",
    "creative_success_mock": """✅ 素材生成完成！（模拟数据）

🎨 已生成 **{count}** 张广告素材

{creative_list}

⚠️ 这是模拟数据，实际功能即将上线。

💡 **下一步建议**：
- 用这些素材创建广告？
- 生成更多变体？""",
    "report_success": """📊 **广告数据报表**

📅 时间范围：{date_range}

**核心指标**
- 花费：**${spend}**
- 展示：**{impressions}**
- 点击：**{clicks}**
- CTR：**{ctr}%**
- ROAS：**{roas}**

{insights}

💡 **建议**：{suggestion}""",
    "campaign_created": """✅ 广告创建成功！

📋 **广告详情**
- Campaign ID：`{campaign_id}`
- 每日预算：**${budget}**
- 目标 ROAS：**{target_roas}**
- 状态：{status}

广告已开始投放，我会持续监控效果。

💡 需要我帮你：
- 查看投放数据？
- 调整预算？""",
    "insufficient_credits": """💰 **Credit 余额不足**

本次操作需要 **{required}** credits
当前余额：**{available}** credits

👉 [点击充值](/billing/recharge)

充值后即可继续使用~""",
    "confirmation_required": """⚠️ **请确认操作**

即将执行：**{operation}**

**影响范围**：
{impact}

**预计结果**：
{expected_result}

---
回复「确认」继续执行，或「取消」放弃操作。""",
    "operation_cancelled": """✅ 操作已取消

没有进行任何更改。有其他需要帮助的吗？""",
    "clarification_needed": """🤔 我不太确定您想要做什么

{question}

您可以告诉我更具体的需求，比如：
{suggestions}""",
    "error_generic": """😅 抱歉，遇到了一点问题

{message}

💡 **建议**：
{suggestion}

如果问题持续，请联系客服。""",
    "error_network": """🔄 网络连接不稳定

请稍后重试，或者检查网络连接。

如果问题持续，请联系客服。""",
    "partial_success": """⚠️ 部分操作完成

**已完成**：
{completed}

**未完成**：
{failed}

{next_steps}""",
}


def get_response_template(template_name: str) -> str:
    """Get a response template by name.

    Args:
        template_name: Name of the template

    Returns:
        Template string or empty string if not found
    """
    return RESPONSE_TEMPLATES.get(template_name, "")


def format_creative_list(creatives: list[dict], max_items: int = 5) -> str:
    """Format a list of creatives for display.

    Args:
        creatives: List of creative dicts with id, name, score
        max_items: Maximum items to show

    Returns:
        Formatted string
    """
    if not creatives:
        return "（暂无素材）"

    lines = []
    for i, creative in enumerate(creatives[:max_items]):
        name = creative.get("name", f"素材 {i + 1}")
        score = creative.get("score")
        score_str = f" - {score}/100 ⭐" if score else ""
        lines.append(f"{i + 1}. {name}{score_str}")

    if len(creatives) > max_items:
        lines.append(f"... 还有 {len(creatives) - max_items} 张")

    return "\n".join(lines)


def format_insights(insights: list[str], max_items: int = 3) -> str:
    """Format AI insights for display.

    Args:
        insights: List of insight strings
        max_items: Maximum items to show

    Returns:
        Formatted string
    """
    if not insights:
        return ""

    lines = ["", "💡 **AI 洞察**"]
    for insight in insights[:max_items]:
        lines.append(f"- {insight}")

    return "\n".join(lines)
