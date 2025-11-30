"""Intent recognition prompt templates.

This module contains prompts for identifying user intent and extracting
parameters from natural language messages.

Requirements: 需求 2 (Intent Recognition), 需求 14.1 (Smart Extraction)
"""

INTENT_RECOGNITION_SYSTEM_PROMPT = """你是一个专业的广告投放助手的意图识别器。你的任务是分析用户消息，识别他们想要执行的操作。

## 可识别的意图类型

### 1. generate_creative (素材生成)
用户想要生成广告素材（图片、视频）。
关键词：生成素材、创建图片、做广告图、设计素材、生成创意、制作广告

示例：
- "帮我生成 10 张广告图片"
- "用这个产品链接生成素材"
- "我需要一些新的广告创意"
- "帮我做几张推广图"

### 1.5. save_creative (保存素材)
用户想要将预览的素材保存到素材库。通常在生成素材后使用。
关键词：保存素材、保存图片、存到素材库、保存、存储素材、存下来

示例：
- "保存素材"
- "把这些图片保存到素材库"
- "保存刚才生成的素材"
- "存下来"
- "保存"

### 2. analyze_report (报表分析)
用户想要查看或分析广告表现数据。
关键词：报表、数据、表现、效果、分析、ROI、ROAS、CTR、CPA

示例：
- "查看今天的广告数据"
- "分析一下最近的投放效果"
- "我的 ROAS 怎么样"
- "哪个广告表现最好"

### 3. market_analysis (市场分析)
用户想要了解市场趋势或竞品信息。
关键词：竞品、市场、趋势、行业、对手、分析竞争

示例：
- "分析一下竞品的广告策略"
- "最近市场趋势怎么样"
- "看看同行都在投什么"
- "给我一些市场洞察"

### 4. create_landing_page (落地页创建)
用户想要创建或编辑落地页。
关键词：落地页、着陆页、页面、网页、landing page

示例：
- "帮我创建一个落地页"
- "生成产品推广页面"
- "做一个活动页"
- "翻译落地页到英文"

### 5. create_campaign (广告创建/管理)
用户想要创建、修改或管理广告活动。
关键词：广告、投放、campaign、预算、暂停、启动、创建广告

示例：
- "创建一个新广告"
- "把预算调到 $200"
- "暂停表现差的广告"
- "启动这个 campaign"

### 6. multi_step (多步骤任务)
用户的请求涉及多个操作，需要按顺序执行。

示例：
- "生成素材并创建广告" → generate_creative + create_campaign
- "分析数据然后优化预算" → analyze_report + create_campaign
- "创建落地页和广告" → create_landing_page + create_campaign

### 7. general_query (一般查询)
用户在闲聊或询问一般性问题。

示例：
- "你好"
- "你能做什么"
- "谢谢"

### 8. clarification_needed (需要澄清)
用户意图不明确，需要更多信息。

示例：
- "帮我看看"（看什么？）
- "优化一下"（优化什么？）

## 参数提取规则

根据意图类型，提取相关参数：

### generate_creative 参数
- product_url: 产品链接
- count: 生成数量（默认 10）
- style: 风格偏好
- reference_image: 参考图片

### save_creative 参数
- temp_ids: 要保存的临时素材 ID 列表（可选，默认保存所有预览素材）
- batch_id: 批次 ID（可选）

### analyze_report 参数
- date_range: 时间范围（today, yesterday, last_7_days, last_30_days, custom）
- campaign_ids: 指定的广告 ID
- metrics: 关注的指标

### market_analysis 参数
- competitor_urls: 竞品链接
- industry: 行业
- analysis_type: 分析类型（competitor, trend, strategy）

### create_landing_page 参数
- product_url: 产品链接
- template: 模板类型
- language: 目标语言

### create_campaign 参数
- campaign_id: 现有广告 ID（修改时）
- budget: 预算金额
- target_roas: 目标 ROAS
- action: 操作类型（create, pause, resume, update_budget, delete）

## 高风险操作识别

以下操作需要标记为 requires_confirmation = true：
- action = "pause_all"（暂停所有广告）
- action = "delete"（删除广告）
- budget 变化超过 50%

## 输出要求

返回结构化的 JSON，包含：
- intent: 主要意图
- confidence: 置信度 (0.0-1.0)
- parameters: 提取的参数
- actions: 需要执行的操作列表
- estimated_cost: 预估 credit 消耗
- requires_confirmation: 是否需要确认
- clarification_question: 如果需要澄清，提出的问题

## 注意事项

1. 如果置信度低于 0.6，设置 intent = "clarification_needed"
2. 多步骤任务要按正确顺序排列 actions
3. 从上下文中解析相对引用（"刚才的"、"那个"）
4. 数字要正确解析（"一百" = 100, "$50" = 50）
"""

INTENT_RECOGNITION_USER_PROMPT = """请分析以下用户消息，识别意图并提取参数。

用户消息：{user_message}

对话历史（最近 5 轮）：
{conversation_history}

请返回结构化的意图识别结果。"""


# Examples for few-shot learning
INTENT_EXAMPLES = [
    {
        "user_message": "帮我生成 10 张广告图片",
        "intent": "generate_creative",
        "confidence": 0.95,
        "parameters": {"count": 10},
        "actions": [{"type": "generate_creative", "module": "creative", "params": {"count": 10}}],
        "estimated_cost": 5.0,
        "requires_confirmation": False,
    },
    {
        "user_message": "保存素材",
        "intent": "save_creative",
        "confidence": 0.95,
        "parameters": {},
        "actions": [{"type": "save_creative", "module": "save_creative", "params": {}}],
        "estimated_cost": 0,
        "requires_confirmation": False,
    },
    {
        "user_message": "把这些图片保存到素材库",
        "intent": "save_creative",
        "confidence": 0.92,
        "parameters": {},
        "actions": [{"type": "save_creative", "module": "save_creative", "params": {}}],
        "estimated_cost": 0,
        "requires_confirmation": False,
    },
    {
        "user_message": "查看今天的广告数据",
        "intent": "analyze_report",
        "confidence": 0.92,
        "parameters": {"date_range": "today"},
        "actions": [
            {"type": "get_report", "module": "reporting", "params": {"date_range": "today"}}
        ],
        "estimated_cost": 1.0,
        "requires_confirmation": False,
    },
    {
        "user_message": "分析一下竞品的广告策略",
        "intent": "market_analysis",
        "confidence": 0.88,
        "parameters": {"analysis_type": "competitor"},
        "actions": [{"type": "analyze_competitor", "module": "market_intel", "params": {}}],
        "estimated_cost": 2.0,
        "requires_confirmation": False,
    },
    {
        "user_message": "帮我创建一个落地页",
        "intent": "create_landing_page",
        "confidence": 0.90,
        "parameters": {},
        "actions": [{"type": "create_landing_page", "module": "landing_page", "params": {}}],
        "estimated_cost": 3.0,
        "requires_confirmation": False,
    },
    {
        "user_message": "把预算调到 $200",
        "intent": "create_campaign",
        "confidence": 0.85,
        "parameters": {"budget": 200, "action": "update_budget"},
        "actions": [{"type": "update_budget", "module": "ad_engine", "params": {"budget": 200}}],
        "estimated_cost": 0.5,
        "requires_confirmation": False,
    },
    {
        "user_message": "暂停所有广告",
        "intent": "create_campaign",
        "confidence": 0.95,
        "parameters": {"action": "pause_all"},
        "actions": [{"type": "pause_all", "module": "ad_engine", "params": {}}],
        "estimated_cost": 0.5,
        "requires_confirmation": True,  # High-risk operation
    },
    {
        "user_message": "生成素材并创建广告",
        "intent": "multi_step",
        "confidence": 0.90,
        "parameters": {},
        "actions": [
            {"type": "generate_creative", "module": "creative", "params": {}, "depends_on": []},
            {"type": "create_campaign", "module": "ad_engine", "params": {}, "depends_on": [0]},
        ],
        "estimated_cost": 8.0,
        "requires_confirmation": False,
    },
    {
        "user_message": "帮我看看",
        "intent": "clarification_needed",
        "confidence": 0.3,
        "parameters": {},
        "actions": [],
        "estimated_cost": 0,
        "requires_confirmation": False,
        "clarification_question": "请问您想查看什么？是广告数据、素材还是其他内容？",
    },
]


def format_conversation_history(messages: list, max_rounds: int = 5) -> str:
    """Format conversation history for prompt.

    Args:
        messages: List of BaseMessage objects
        max_rounds: Maximum number of message pairs to include

    Returns:
        Formatted string of conversation history
    """
    if not messages:
        return "（无历史对话）"

    # Take last N*2 messages (N rounds of user-assistant pairs)
    recent = messages[-(max_rounds * 2) :]

    lines = []
    for msg in recent:
        role = "用户" if msg.type == "human" else "助手"
        content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
        lines.append(f"{role}: {content}")

    return "\n".join(lines) if lines else "（无历史对话）"
