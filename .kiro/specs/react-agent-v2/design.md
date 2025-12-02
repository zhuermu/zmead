# 设计文档 - AAE ReAct Agent v2（Skills 动态加载）

## 概述（Overview）

本设计文档描述如何实现 **ReAct Agent + 3 类 Tools + Skills 动态加载** 架构。新架构将：
- 支持 3 类 Tools（LangChain 内置 + Agent 自定义 + MCP Server）
- 使用 Skills 机制动态加载 Tools
- 减少 LLM context 大小 60%+
- 提升响应速度和降低成本
- 保持智能 Human-in-the-Loop

---

## 架构设计（Architecture）

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js + SSE)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP + SSE
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                             │
│  - MCP Server (提供 MCP Server Tools)                            │
│  - Business Services                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ MCP Protocol
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    AI Orchestrator                               │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              ReAct Agent (Gemini)                         │  │
│  │                                                           │  │
│  │  Step 1: Intent Recognition                               │  │
│  │  ├─ 识别用户意图                                           │  │
│  │  └─ 识别需要的 Skills                                      │  │
│  │                                                           │  │
│  │  Step 2: Skills Loading                                   │  │
│  │  ├─ 动态加载相关 Skills                                    │  │
│  │  └─ 组装 Tools 列表                                        │  │
│  │                                                           │  │
│  │  Step 3: ReAct Loop                                       │  │
│  │  ├─ Planner (制定计划)                                     │  │
│  │  ├─ Evaluator (判断是否需要人工)                           │  │
│  │  ├─ Human-in-the-Loop (可选)                              │  │
│  │  ├─ Act (执行 Tools)                                       │  │
│  │  ├─ Memory (记录结果)                                      │  │
│  │  └─ Perceive (评估是否完成)                                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │              Skills Registry                               │  │
│  │                                                            │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │
│  │  │ Creative    │  │ Performance │  │ Campaign    │       │  │
│  │  │ Skill       │  │ Skill       │  │ Skill       │       │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │  │
│  │                                                            │  │
│  │  ┌─────────────┐  ┌─────────────┐                         │  │
│  │  │ Landing     │  │ Market      │                         │  │
│  │  │ Page Skill  │  │ Skill       │                         │  │
│  │  └─────────────┘  └─────────────┘                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │              3 类 Tools                                    │  │
│  │                                                            │  │
│  │  ┌──────────────────────────────────────────────┐         │  │
│  │  │ 1. LangChain 内置 Tools                      │         │  │
│  │  │  - google_search, calculator, datetime       │         │  │
│  │  └──────────────────────────────────────────────┘         │  │
│  │                                                            │  │
│  │  ┌──────────────────────────────────────────────┐         │  │
│  │  │ 2. Agent 自定义 Tools (可调用大模型)         │         │  │
│  │  │  - generate_image_tool                       │         │  │
│  │  │  - analyze_performance_tool                  │         │  │
│  │  │  - generate_strategy_tool                    │         │  │
│  │  └──────────────────────────────────────────────┘         │  │
│  │                                                            │  │
│  │  ┌──────────────────────────────────────────────┐         │  │
│  │  │ 3. MCP Server Tools (Backend API)            │         │  │
│  │  │  - save_creative, fetch_ad_data              │         │  │
│  │  │  - create_campaign, save_landing_page        │         │  │
│  │  └──────────────────────────────────────────────┘         │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 组件设计（Component Design）

### 1. Skills Registry

```python
# ai-orchestrator/app/core/skills_registry.py

from dataclasses import dataclass
from typing import List

@dataclass
class Skill:
    """Skill 定义。"""
    
    name: str
    description: str
    keywords: list[str]  # 触发关键词
    langchain_tools: list[str]  # LangChain 工具名称
    agent_tools: list[str]      # Agent 自定义工具名称
    mcp_tools: list[str]        # MCP Server 工具名称


class SkillsRegistry:
    """Skills 注册表。"""
    
    def __init__(self):
        self.skills = self._register_skills()
    
    def _register_skills(self) -> dict[str, Skill]:
        """注册所有 Skills。"""
        
        return {
            "creative": Skill(
                name="Creative Skill",
                description="素材生成和分析能力",
                keywords=["素材", "图片", "视频", "创意", "设计", "生成"],
                langchain_tools=[],
                agent_tools=[
                    "generate_image_tool",
                    "generate_video_tool",
                    "analyze_creative_tool",
                    "extract_product_info_tool",
                ],
                mcp_tools=[
                    "save_creative",
                    "get_creative",
                    "list_creatives",
                ],
            ),
            
            "performance": Skill(
                name="Performance Skill",
                description="广告性能分析能力",
                keywords=["表现", "数据", "分析", "报表", "ROAS", "CTR", "性能"],
                langchain_tools=["calculator"],
                agent_tools=[
                    "analyze_performance_tool",
                    "detect_anomaly_tool",
                    "generate_recommendations_tool",
                ],
                mcp_tools=[
                    "fetch_ad_data",
                    "get_historical_data",
                    "save_report",
                ],
            ),
            
            "campaign": Skill(
                name="Campaign Skill",
                description="广告投放管理能力",
                keywords=["广告", "投放", "预算", "Campaign", "Adset", "创建", "暂停"],
                langchain_tools=[],
                agent_tools=[
                    "optimize_budget_tool",
                    "generate_ad_copy_tool",
                    "suggest_targeting_tool",
                ],
                mcp_tools=[
                    "create_campaign",
                    "update_campaign",
                    "pause_campaign",
                    "get_campaign",
                ],
            ),
            
            "landing_page": Skill(
                name="Landing Page Skill",
                description="落地页生成和管理能力",
                keywords=["落地页", "页面", "网站", "Landing Page"],
                langchain_tools=[],
                agent_tools=[
                    "generate_page_content_tool",
                    "translate_content_tool",
                    "optimize_copy_tool",
                ],
                mcp_tools=[
                    "save_landing_page",
                    "get_landing_page",
                    "upload_to_s3",
                    "create_ab_test_record",
                ],
            ),
            
            "market": Skill(
                name="Market Skill",
                description="市场洞察和竞品分析能力",
                keywords=["竞品", "市场", "趋势", "策略", "分析"],
                langchain_tools=["google_search"],
                agent_tools=[
                    "analyze_competitor_tool",
                    "analyze_trends_tool",
                    "generate_strategy_tool",
                ],
                mcp_tools=[
                    "fetch_competitor_data",
                    "fetch_market_data",
                    "save_analysis",
                ],
            ),
        }
    
    async def identify_skills(self, user_message: str) -> list[str]:
        """识别用户消息需要的 Skills。"""
        
        # 使用 Gemini 识别
        prompt = f"""
        用户消息：{user_message}
        
        可用的 Skills：
        {self._format_skills_for_prompt()}
        
        请识别需要哪些 Skills（返回 skill 名称列表）。
        """
        
        response = await gemini_client.chat(prompt)
        skill_names = self._parse_skill_names(response)
        
        return skill_names
    
    def get_tools_for_skills(
        self,
        skill_names: list[str],
    ) -> dict:
        """获取 Skills 对应的所有 Tools。"""
        
        tools = {
            "langchain": [],
            "agent_custom": [],
            "mcp_server": [],
        }
        
        for skill_name in skill_names:
            skill = self.skills.get(skill_name)
            if skill:
                tools["langchain"].extend(skill.langchain_tools)
                tools["agent_custom"].extend(skill.agent_tools)
                tools["mcp_server"].extend(skill.mcp_tools)
        
        # 去重
        tools["langchain"] = list(set(tools["langchain"]))
        tools["agent_custom"] = list(set(tools["agent_custom"]))
        tools["mcp_server"] = list(set(tools["mcp_server"]))
        
        return tools
```

---

### 2. Agent Custom Tools 实现

```python
# ai-orchestrator/app/tools/creative_tools.py

from langchain.tools import tool

@tool
async def generate_image_tool(
    product_info: dict,
    style: str,
    aspect_ratio: str = "1:1",
) -> str:
    """生成广告图片。
    
    这个 Tool 可以调用大模型（Gemini Imagen）。
    
    Args:
        product_info: 产品信息
        style: 风格（modern, vibrant, luxury）
        aspect_ratio: 宽高比
    
    Returns:
        图片 URL
    """
    service = get_ad_creative_service()
    image_url = await service.generate_image(product_info, style, aspect_ratio)
    return image_url


@tool
async def analyze_creative_tool(image_url: str) -> dict:
    """分析素材质量。
    
    这个 Tool 可以调用大模型（Gemini Vision）。
    
    Args:
        image_url: 素材 URL
    
    Returns:
        分析结果（score, suggestions）
    """
    service = get_ad_creative_service()
    analysis = await service.analyze_creative(image_url)
    return analysis
```

```python
# ai-orchestrator/app/tools/performance_tools.py

@tool
async def analyze_performance_tool(data: dict) -> dict:
    """AI 分析广告性能。
    
    这个 Tool 可以调用大模型（Gemini）。
    
    Args:
        data: 广告数据
    
    Returns:
        分析结果（insights, recommendations）
    """
    service = get_ad_performance_service()
    analysis = await service.analyze_performance(data)
    return analysis


@tool
async def detect_anomaly_tool(data: dict) -> list[dict]:
    """检测异常。
    
    这个 Tool 可以调用大模型（Gemini）。
    
    Args:
        data: 广告数据
    
    Returns:
        异常列表
    """
    service = get_ad_performance_service()
    anomalies = await service.detect_anomaly(data)
    return anomalies
```

---

### 3. Tools Loader

```python
# ai-orchestrator/app/core/tools_loader.py

class ToolsLoader:
    """Tools 加载器。"""
    
    def __init__(self):
        self.skills_registry = SkillsRegistry()
        self.langchain_tools_registry = {}
        self.agent_tools_registry = {}
        self.mcp_client = get_mcp_client()
    
    async def load_tools_for_message(
        self,
        user_message: str,
    ) -> list[Tool]:
        """根据用户消息动态加载 Tools。"""
        
        # 1. 识别需要的 Skills
        skill_names = await self.skills_registry.identify_skills(user_message)
        
        # 2. 获取 Skills 对应的 Tools
        tools_dict = self.skills_registry.get_tools_for_skills(skill_names)
        
        # 3. 加载 3 类 Tools
        loaded_tools = []
        
        # 3.1 加载 LangChain Tools
        for tool_name in tools_dict["langchain"]:
            tool = self._load_langchain_tool(tool_name)
            loaded_tools.append(tool)
        
        # 3.2 加载 Agent Custom Tools
        for tool_name in tools_dict["agent_custom"]:
            tool = self._load_agent_tool(tool_name)
            loaded_tools.append(tool)
        
        # 3.3 加载 MCP Server Tools
        for tool_name in tools_dict["mcp_server"]:
            tool = await self._load_mcp_tool(tool_name)
            loaded_tools.append(tool)
        
        return loaded_tools
    
    def _load_langchain_tool(self, tool_name: str) -> Tool:
        """加载 LangChain 内置工具。"""
        if tool_name == "google_search":
            from langchain.tools import GoogleSearchTool
            return GoogleSearchTool()
        elif tool_name == "calculator":
            from langchain.tools import Calculator
            return Calculator()
        # ... 其他工具
    
    def _load_agent_tool(self, tool_name: str) -> Tool:
        """加载 Agent 自定义工具。"""
        # 从注册表获取
        return self.agent_tools_registry[tool_name]
    
    async def _load_mcp_tool(self, tool_name: str) -> Tool:
        """加载 MCP Server 工具。"""
        # 从 MCP Client 获取工具定义
        tool_def = await self.mcp_client.get_tool(tool_name)
        return self._convert_mcp_to_langchain_tool(tool_def)
```

---

### 4. ReAct Agent 主循环（带 Skills 加载）

```python
# ai-orchestrator/app/core/react_agent.py

class ReActAgent:
    """ReAct Agent with Skills Dynamic Loading."""
    
    def __init__(self):
        self.gemini_client = get_gemini_client()
        self.tools_loader = ToolsLoader()
        self.evaluator = Evaluator()
        self.memory = AgentMemory()
    
    async def process_message(
        self,
        user_message: str,
        user_id: str,
        session_id: str,
    ) -> AgentResponse:
        """处理用户消息。"""
        
        # Step 1: 动态加载 Tools
        tools = await self.tools_loader.load_tools_for_message(user_message)
        
        logger.info(
            "tools_loaded",
            count=len(tools),
            tools=[t.name for t in tools],
        )
        
        # Step 2: 初始化状态
        state = AgentState(
            user_message=user_message,
            user_id=user_id,
            session_id=session_id,
            loaded_tools=tools,
            steps_completed=[],
        )
        
        # Step 3: ReAct 循环
        max_iterations = 10
        for i in range(max_iterations):
            
            # 3.1 Planner
            plan = await self._plan(state)
            
            # 3.2 Evaluator
            needs_human = await self.evaluator.needs_human_input(plan, state)
            
            if needs_human:
                return AgentResponse(
                    status="waiting_for_user",
                    message=plan.question_for_user,
                    options=plan.options,
                )
            
            # 3.3 Act
            tool_results = await self._act(plan, state)
            state.steps_completed.append({
                "plan": plan,
                "results": tool_results,
            })
            
            # 3.4 Memory
            await self.memory.save(state)
            
            # 3.5 Perceive & Evaluate
            is_complete = await self.evaluator.is_task_complete(state)
            
            if is_complete:
                final_response = await self._generate_response(state)
                return AgentResponse(
                    status="completed",
                    message=final_response,
                )
            
            # 3.6 检查是否需要加载新 Skills
            needs_new_skills = await self._check_needs_new_skills(state)
            if needs_new_skills:
                new_tools = await self.tools_loader.load_additional_tools(
                    state.current_plan.required_skills
                )
                state.loaded_tools.extend(new_tools)
        
        return AgentResponse(
            status="error",
            message="任务过于复杂，请简化后重试",
        )
```

---

## 完整对话流程示例（带 Skills 动态加载）

### 示例：复杂任务 - "帮我生成素材并创建广告"

```
用户: "帮我生成素材并创建广告，预算 $100"

Step 1: Intent Recognition & Skills Loading
  Agent: 分析用户意图
  → 需要生成素材（Creative Skill）
  → 需要创建广告（Campaign Skill）
  
  动态加载 Skills:
  ✅ Creative Skill (10 个 Tools)
  ✅ Campaign Skill (8 个 Tools)
  ❌ Performance Skill (不需要)
  ❌ Landing Page Skill (不需要)
  ❌ Market Skill (不需要)
  
  总共加载：18 个 Tools（而不是 50 个）

Step 2: ReAct Loop - Round 1
  Planner: "需要先获取产品信息"
  Evaluator: "缺少产品链接，需要用户输入"
  
  [Human-in-the-Loop]
  返回用户:
    "好的！产品链接是什么？
     [输入框]
     ❌ 取消"

用户输入: "https://example.com/product"

Step 3: ReAct Loop - Round 2
  Planner: "生成素材"
  Evaluator: "风格模糊，提供选项"
  
  [Human-in-the-Loop]
  返回用户:
    "请选择素材风格：
     1️⃣ 现代简约
     2️⃣ 活力多彩
     3️⃣ 高端奢华
     ➕ 其他
     ❌ 取消"

用户选择: "1️⃣"

Step 4: ReAct Loop - Round 3
  Planner: "执行生成"
  Evaluator: "生成素材无需确认"
  
  Act:
    - 调用 extract_product_info_tool(url)  # Agent Custom Tool
    - 调用 generate_image_tool(product_info, "modern")  # Agent Custom Tool
    - 调用 save_creative(image_url)  # MCP Server Tool
  
  Memory: 保存 creative_id
  
  Evaluator: "素材完成，但还需创建广告"

Step 5: ReAct Loop - Round 4
  Planner: "创建广告"
  Evaluator: "涉及花费，需要确认"
  
  Act (准备):
    - 调用 generate_ad_copy_tool(product_info)  # Agent Custom Tool
    - 调用 suggest_targeting_tool(product_info)  # Agent Custom Tool
  
  [Human-in-the-Loop]
  返回用户:
    "素材已生成！现在创建广告：
     
     [显示素材预览]
     
     广告设置：
     - 预算：$100/天
     - 目标：转化
     - 文案：[AI 生成的文案]
     - 受众：25-35 岁女性，兴趣：时尚
     
     确认创建吗？
     ✅ 确认
     ✏️ 修改设置
     ❌ 取消"

用户选择: "✅"

Step 6: ReAct Loop - Round 5
  Planner: "执行创建"
  
  Act:
    - 调用 create_campaign(creative_id, settings)  # MCP Server Tool
  
  Memory: 保存 campaign_id
  
  Evaluator: "任务完成"

返回用户:
  "✅ 素材和广告都已完成！
   
   素材 ID: creative-123
   Campaign ID: 123456789
   
   广告将在审核通过后开始投放"
```

**关键优势**：
- ✅ 只加载了 18 个 Tools（而不是 50 个）
- ✅ Context 大小减少 64%
- ✅ 响应速度更快
- ✅ 成本更低

---

## 3 类 Tools 对比

| 类型 | 职责 | 是否调用大模型 | 示例 | 数量 |
|------|------|---------------|------|------|
| **LangChain 内置** | 通用工具 | 部分可以 | google_search, calculator | ~5 个 |
| **Agent 自定义** | AI 能力封装 | ✅ 是 | generate_image_tool, analyze_performance_tool | ~20 个 |
| **MCP Server** | 数据交互 | ❌ 否 | save_creative, fetch_ad_data, create_campaign | ~25 个 |

### Agent Custom Tools 详细列表

#### Creative Tools

```python
- generate_image_tool(product_info, style, aspect_ratio) → image_url
  # 调用 Gemini Imagen

- generate_video_tool(product_info, style, duration) → video_url
  # 调用 Gemini Veo

- analyze_creative_tool(image_url) → {score, suggestions}
  # 调用 Gemini Vision

- extract_product_info_tool(url) → product_info
  # 调用 Gemini 理解网页
```

#### Performance Tools

```python
- analyze_performance_tool(data) → {insights, recommendations}
  # 调用 Gemini 分析数据

- detect_anomaly_tool(data) → list[anomaly]
  # 调用 Gemini 识别异常模式

- generate_recommendations_tool(analysis) → list[recommendation]
  # 调用 Gemini 生成建议
```

#### Campaign Tools

```python
- optimize_budget_tool(performance_data) → budget_recommendations
  # 调用 Gemini 优化预算

- generate_ad_copy_tool(product_info) → {headline, description}
  # 调用 Gemini 生成文案

- suggest_targeting_tool(product_info) → targeting_config
  # 调用 Gemini 建议受众
```

#### Landing Page Tools

```python
- generate_page_content_tool(product_info, template) → html_content
  # 调用 Gemini 生成页面

- translate_content_tool(content, target_language) → translated_content
  # 调用 Gemini 翻译

- optimize_copy_tool(content) → optimized_content
  # 调用 Gemini 优化文案
```

#### Market Tools

```python
- analyze_competitor_tool(competitor_url) → analysis
  # 调用 Gemini 分析竞品

- analyze_trends_tool(market_data) → trends
  # 调用 Gemini 分析趋势

- generate_strategy_tool(product_info, market_analysis) → strategy
  # 调用 Gemini 生成策略
```

---

## Context 优化效果

### 不使用 Skills 动态加载

```
所有 Tools 都加载：
- LangChain Tools: 5 个
- Agent Custom Tools: 20 个
- MCP Server Tools: 25 个
总计：50 个 Tools

LLM Context:
- Tools 描述：~10,000 tokens
- 对话历史：~2,000 tokens
- System Prompt：~1,000 tokens
总计：~13,000 tokens
```

### 使用 Skills 动态加载

```
只加载相关 Skills 的 Tools：
- Creative Skill: 10 个 Tools
- Campaign Skill: 8 个 Tools
总计：18 个 Tools

LLM Context:
- Tools 描述：~3,600 tokens (减少 64%)
- 对话历史：~2,000 tokens
- System Prompt：~1,000 tokens
总计：~6,600 tokens (减少 49%)
```

**效果**：
- ✅ Context 减少 49%
- ✅ 响应速度提升 30%+
- ✅ Token 成本降低 40%+
- ✅ 更容易达到 context 限制

---

## 数据模型（Data Models）

### Skill Definition

```python
@dataclass
class Skill:
    """Skill 定义。"""
    name: str
    description: str
    keywords: list[str]
    langchain_tools: list[str]
    agent_tools: list[str]
    mcp_tools: list[str]
```

### AgentState

```python
@dataclass
class AgentState:
    """Agent 状态。"""
    user_message: str
    user_id: str
    session_id: str
    
    # Skills 和 Tools
    loaded_skills: list[str]
    loaded_tools: list[Tool]
    
    # 执行状态
    current_plan: Plan | None
    steps_completed: list[dict]
    
    # 人工输入
    waiting_for_user: bool = False
    user_input_request: UserInputRequest | None = None
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

### Property 1: Skills 识别准确性
*For any* 用户消息，系统 SHALL 正确识别需要的 Skills，准确率 > 95%
**Validates: Requirements 2.2**

### Property 2: Tools 动态加载正确性
*For any* 识别的 Skills，系统 SHALL 加载该 Skill 的所有 Tools，不遗漏不多余
**Validates: Requirements 2.3, 2.4**

### Property 3: Context 大小优化
*For any* 用户消息，动态加载的 Tools 数量 SHALL 少于总 Tools 数量的 50%
**Validates: Requirements 2.3**

---

## 测试策略（Testing Strategy）

### Unit Testing

**Skills Registry 测试**：
- Skills 注册测试
- Skills 识别测试
- Tools 映射测试

**Tools Loader 测试**：
- 3 类 Tools 加载测试
- 动态加载测试
- Tools 去重测试

**ReAct Agent 测试**：
- 主循环测试
- Planner 测试
- Evaluator 测试

### Property-Based Testing

```python
@given(
    message=st.text(min_size=5, max_size=100),
)
@pytest.mark.asyncio
async def test_skills_identification_accuracy(message):
    """测试 Skills 识别准确性。
    
    Feature: react-agent-v2, Property 1
    """
    registry = SkillsRegistry()
    skills = await registry.identify_skills(message)
    
    # 验证识别的 Skills 是合理的
    assert len(skills) > 0
    assert all(s in registry.skills for s in skills)


@given(
    skills=st.lists(
        st.sampled_from(["creative", "performance", "campaign"]),
        min_size=1,
        max_size=3,
        unique=True,
    ),
)
def test_tools_loading_correctness(skills):
    """测试 Tools 加载正确性。
    
    Feature: react-agent-v2, Property 2
    """
    registry = SkillsRegistry()
    tools_dict = registry.get_tools_for_skills(skills)
    
    # 验证加载的 Tools 完整性
    for skill_name in skills:
        skill = registry.skills[skill_name]
        assert all(t in tools_dict["agent_custom"] for t in skill.agent_tools)
        assert all(t in tools_dict["mcp_server"] for t in skill.mcp_tools)
```

---

## 实施优先级

### Phase 1: 核心架构（高优先级）
1. 实现 Skills Registry
2. 实现 Tools Loader
3. 实现 ReAct Agent 主循环

### Phase 2: Tools 实现（高优先级）
1. 实现 Agent Custom Tools
2. 统一 MCP Server Tools
3. 集成 LangChain Tools

### Phase 3: Human-in-the-Loop（中优先级）
1. 实现 Evaluator
2. 实现确认和选项机制
3. 前端交互组件

### Phase 4: 前端 SSE（中优先级）
1. 实现 SSE 通信
2. 移除 AI SDK
3. 实现选项按钮

### Phase 5: 清理旧代码（低优先级）
1. 删除 Sub-Agents
2. 删除 v2 架构
3. 更新文档

---

## 成功指标（Success Metrics）

### Context 优化

- ✅ 平均加载 Tools 数量：15-20 个（而不是 50 个）
- ✅ Context 大小减少 50%+
- ✅ Skills 识别准确率 > 95%

### 性能提升

- ✅ 响应速度提升 30%+
- ✅ Token 使用减少 40%+
- ✅ 成本降低 40%+

### 架构简化

- ✅ 从 5 个 Sub-Agents 减少到 1 个
- ✅ 代码行数减少 50%+
- ✅ 更容易维护和扩展
