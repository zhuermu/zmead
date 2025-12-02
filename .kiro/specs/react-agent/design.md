# 设计文档 - AAE ReAct Agent 架构

## 概述（Overview）

本设计文档描述如何将 AAE 系统重构为**单一 ReAct Agent** 架构。新架构将：
- 移除 5 个 Sub-Agents，使用单一 Main Agent
- 利用 Gemini 的自主规划和编排能力
- 实现智能的 Human-in-the-Loop 机制
- 简化代码复杂度 50%+
- 提升用户体验

---

## 架构设计（Architecture）

### ReAct Agent 循环

```
┌─────────────────────────────────────────────────────────────────┐
│                    ReAct Agent (Gemini)                          │
│                                                                  │
│  用户输入                                                         │
│     ↓                                                            │
│  ┌──────────────┐                                               │
│  │   Planner    │  ← 理解任务，制定计划                          │
│  │   (Gemini)   │                                               │
│  └──────────────┘                                               │
│         │                                                        │
│         ↓ plan                                                   │
│  ┌──────────────┐                                               │
│  │ Evaluator    │  ← 判断是否需要人工确认                        │
│  │ (Guardrails) │                                               │
│  └──────────────┘                                               │
│         │                                                        │
│         ├─ 明确任务 ──→ 直接执行                                 │
│         │                                                        │
│         └─ 模糊/重要 ──→ Human-in-the-Loop                       │
│                              │                                   │
│                              ↓                                   │
│                       ┌──────────────┐                          │
│                       │ 用户确认/选择 │                          │
│                       └──────────────┘                          │
│                              │                                   │
│         ↓ act                ↓                                   │
│  ┌──────────────┐                                               │
│  │ Tools/APIs   │  ← 调用 MCP Tools                             │
│  └──────────────┘                                               │
│         │                                                        │
│         ↓ observe                                                │
│  ┌──────────────┐                                               │
│  │ Memory/State │  ← 记录执行结果                                │
│  └──────────────┘                                               │
│         │                                                        │
│         ↓ perceive                                               │
│  ┌──────────────┐                                               │
│  │  Evaluator   │  ← 评估是否完成                                │
│  └──────────────┘                                               │
│         │                                                        │
│         ├─ 未完成 ──→ 回到 Planner（继续规划）                   │
│         └─ 已完成 ──→ 返回用户                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 整体系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js + SSE)                      │
│  - 发送消息：HTTP POST                                            │
│  - 接收响应：EventSource (SSE)                                    │
│  - 渲染选项按钮（预设 + 其他 + 取消）                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP + SSE
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                             │
│  - MCP Server (提供所有 Tools)                                   │
│  - 业务逻辑服务（creative, performance, campaign 等）             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ MCP Protocol
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    AI Orchestrator                               │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Single ReAct Agent                           │  │
│  │                                                           │  │
│  │  - Planner (Gemini)                                       │  │
│  │  - Evaluator (Guardrails)                                 │  │
│  │  - Memory (Redis + LangGraph State)                       │  │
│  │  - Human-in-the-Loop Handler                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │              All MCP Tools (30-50 个)                      │  │
│  │                                                            │  │
│  │  Creative Tools:                                           │  │
│  │  - save_creative, get_creative, list_creatives            │  │
│  │                                                            │  │
│  │  Performance Tools:                                        │  │
│  │  - fetch_ad_data, get_historical_data, save_report        │  │
│  │                                                            │  │
│  │  Campaign Tools:                                           │  │
│  │  - create_campaign, update_campaign, pause_campaign       │  │
│  │                                                            │  │
│  │  Landing Page Tools:                                       │  │
│  │  - save_landing_page, get_landing_page, upload_to_s3      │  │
│  │                                                            │  │
│  │  Market Tools:                                             │  │
│  │  - fetch_competitor_data, fetch_market_data               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │              Business Logic Modules                        │  │
│  │              (不是 Agents，是实现层)                        │  │
│  │                                                            │  │
│  │  - ad_creative/service.py                                  │  │
│  │  - ad_performance/service.py                               │  │
│  │  - campaign_automation/service.py                          │  │
│  │  - landing_page/service.py                                 │  │
│  │  - market_insights/service.py                              │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 组件设计（Component Design）

### 1. ReAct Agent 核心实现

```python
# ai-orchestrator/app/core/react_agent.py

class ReActAgent:
    """单一 ReAct Agent，具备自主规划和编排能力。"""
    
    def __init__(self):
        self.gemini_client = get_gemini_client()
        self.mcp_client = get_mcp_client()
        self.memory = AgentMemory()
        self.evaluator = Evaluator()
    
    async def process_message(
        self,
        user_message: str,
        user_id: str,
        session_id: str,
    ) -> AgentResponse:
        """处理用户消息的主循环。"""
        
        # 初始化状态
        state = AgentState(
            user_message=user_message,
            user_id=user_id,
            session_id=session_id,
            steps_completed=[],
            current_plan=None,
        )
        
        # ReAct 循环
        max_iterations = 10
        for i in range(max_iterations):
            
            # 1. Planner: 制定或更新计划
            plan = await self._plan(state)
            state.current_plan = plan
            
            # 2. Evaluator: 判断是否需要人工确认
            needs_human = await self.evaluator.needs_human_input(plan, state)
            
            if needs_human:
                # 请求人工输入
                return AgentResponse(
                    status="waiting_for_user",
                    message=plan.question_for_user,
                    options=plan.options,
                    allow_custom=plan.allow_custom,
                    allow_cancel=True,
                )
            
            # 3. Act: 执行工具调用
            tool_results = await self._act(plan, state)
            state.steps_completed.append({
                "plan": plan,
                "results": tool_results,
            })
            
            # 4. Observe: 记录到 Memory
            await self.memory.save(state)
            
            # 5. Perceive & Evaluate: 判断是否完成
            is_complete = await self.evaluator.is_task_complete(state)
            
            if is_complete:
                # 生成最终响应
                final_response = await self._generate_response(state)
                return AgentResponse(
                    status="completed",
                    message=final_response,
                )
        
        # 达到最大迭代次数
        return AgentResponse(
            status="error",
            message="任务过于复杂，请简化后重试",
        )
    
    async def _plan(self, state: AgentState) -> Plan:
        """使用 Gemini 制定计划。"""
        
        # 构建 prompt
        prompt = f"""
        用户请求：{state.user_message}
        已完成步骤：{state.steps_completed}
        
        请分析：
        1. 下一步需要做什么？
        2. 需要调用哪些工具？
        3. 是否需要用户提供更多信息？
        """
        
        # 调用 Gemini
        plan = await self.gemini_client.generate_plan(
            prompt=prompt,
            available_tools=self.mcp_client.list_tools(),
        )
        
        return plan
    
    async def _act(self, plan: Plan, state: AgentState) -> list[ToolResult]:
        """执行工具调用。"""
        
        results = []
        for tool_call in plan.tool_calls:
            result = await self.mcp_client.call_tool(
                tool_name=tool_call.name,
                params=tool_call.params,
            )
            results.append(result)
        
        return results
```

---

### 2. Evaluator (Guardrails) 实现

```python
# ai-orchestrator/app/core/evaluator.py

class Evaluator:
    """评估器：判断是否需要人工介入。"""
    
    # 必须人工确认的操作
    REQUIRES_CONFIRMATION = [
        "create_campaign",      # 创建广告
        "update_budget",        # 修改预算
        "pause_campaign",       # 暂停广告
        "delete_campaign",      # 删除广告
        "recharge_credits",     # 充值
    ]
    
    # 建议人工选择的场景
    SUGGESTS_USER_CHOICE = [
        "ambiguous_style",      # 风格模糊
        "multiple_options",     # 多个可行方案
        "unclear_audience",     # 受众不明确
    ]
    
    async def needs_human_input(
        self,
        plan: Plan,
        state: AgentState,
    ) -> bool:
        """判断是否需要人工输入。"""
        
        # 1. 检查是否有需要确认的操作
        for tool_call in plan.tool_calls:
            if tool_call.name in self.REQUIRES_CONFIRMATION:
                return True
        
        # 2. 检查是否有模糊的参数
        if self._has_ambiguous_params(plan):
            return True
        
        # 3. 检查是否缺少必要信息
        if self._missing_required_info(plan, state):
            return True
        
        return False
    
    def _has_ambiguous_params(self, plan: Plan) -> bool:
        """检查是否有模糊的参数。"""
        # 例如：用户说"生成素材"但没说风格
        # 例如：用户说"创建广告"但没说预算
        pass
    
    def _missing_required_info(self, plan: Plan, state: AgentState) -> bool:
        """检查是否缺少必要信息。"""
        # 例如：创建广告需要 creative_id，但还没生成素材
        pass
    
    async def is_task_complete(self, state: AgentState) -> bool:
        """判断任务是否完成。"""
        
        # 使用 Gemini 判断
        prompt = f"""
        用户请求：{state.user_message}
        已完成步骤：{state.steps_completed}
        
        任务是否已完成？回答 yes 或 no。
        """
        
        response = await gemini_client.chat(prompt)
        return "yes" in response.lower()
```

---

### 3. Human-in-the-Loop 实现

#### 3.1 后端实现

```python
# ai-orchestrator/app/core/human_in_loop.py

class HumanInLoopHandler:
    """处理人工确认和选择。"""
    
    async def request_confirmation(
        self,
        action: str,
        details: dict,
    ) -> UserInputRequest:
        """请求用户确认。"""
        
        return UserInputRequest(
            type="confirmation",
            message=f"确认{action}？",
            details=details,
            options=[
                {"id": "confirm", "label": "✅ 确认"},
                {"id": "cancel", "label": "❌ 取消"},
            ],
        )
    
    async def request_choice(
        self,
        question: str,
        options: list[str],
        allow_custom: bool = True,
    ) -> UserInputRequest:
        """请求用户选择。"""
        
        option_list = [
            {"id": str(i), "label": opt}
            for i, opt in enumerate(options, 1)
        ]
        
        if allow_custom:
            option_list.append({
                "id": "custom",
                "label": "➕ 其他（自定义）",
                "requires_input": True,
            })
        
        option_list.append({
            "id": "cancel",
            "label": "❌ 取消",
        })
        
        return UserInputRequest(
            type="choice",
            message=question,
            options=option_list,
        )
    
    async def request_input(
        self,
        question: str,
        input_type: str = "text",
    ) -> UserInputRequest:
        """请求用户输入。"""
        
        return UserInputRequest(
            type="input",
            message=question,
            input_type=input_type,  # text, number, url, etc.
            options=[
                {"id": "cancel", "label": "❌ 取消"},
            ],
        )
```

#### 3.2 前端实现

```typescript
// frontend/src/components/chat/UserInputPrompt.tsx

interface UserInputPromptProps {
  message: string;
  options: Array<{
    id: string;
    label: string;
    requires_input?: boolean;
  }>;
  onSelect: (optionId: string, customInput?: string) => void;
}

export function UserInputPrompt({ message, options, onSelect }: UserInputPromptProps) {
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [customValue, setCustomValue] = useState('');

  const handleOptionClick = (option: any) => {
    if (option.requires_input) {
      setShowCustomInput(true);
    } else {
      onSelect(option.id);
    }
  };

  const handleCustomSubmit = () => {
    onSelect('custom', customValue);
    setShowCustomInput(false);
  };

  return (
    <div className="user-input-prompt">
      <p className="message">{message}</p>
      
      {!showCustomInput ? (
        <div className="options">
          {options.map(option => (
            <button
              key={option.id}
              onClick={() => handleOptionClick(option)}
              className={cn(
                "option-button",
                option.id === "cancel" && "cancel-button"
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      ) : (
        <div className="custom-input">
          <input
            type="text"
            value={customValue}
            onChange={(e) => setCustomValue(e.target.value)}
            placeholder="请输入..."
            autoFocus
          />
          <button onClick={handleCustomSubmit}>提交</button>
          <button onClick={() => setShowCustomInput(false)}>返回</button>
        </div>
      )}
    </div>
  );
}
```

---

## 完整对话流程示例

### 示例 1：明确任务（无需人工确认）

```
用户: "我的广告表现如何？"

Agent ReAct 循环:

Round 1:
  Planner: "用户想查询广告性能，需要：
           1. 抓取最新数据
           2. 分析性能
           3. 生成报告"
  
  Evaluator: "这是只读操作，无需人工确认"
  
  Act: 
    - 调用 fetch_ad_data(user_id, date_range="last_7_days")
    - 使用 Gemini 分析数据
    - 生成自然语言报告
  
  Memory: 保存执行结果
  
  Evaluator: "任务完成"

返回用户:
  "📊 近 7 天表现：
   - 花费：$87.50
   - ROAS：2.8
   - CTR：1.2%
   
   ⚠️ 发现问题：
   - Adset X 表现较差（ROAS 1.8）
   
   💡 建议：
   - 暂停 Adset X
   - 增加 Adset Y 预算"
```

**关键点**：
- ✅ 全程自动执行
- ✅ 无需人工介入
- ✅ 快速响应

---

### 示例 2：模糊任务（需要人工选择）

```
用户: "帮我生成素材"

Agent ReAct 循环:

Round 1:
  Planner: "用户想生成素材，但缺少信息：
           - 产品是什么？
           - 什么风格？"
  
  Evaluator: "参数模糊，需要人工输入"
  
  [Human-in-the-Loop]
  返回用户:
    "好的！我需要一些信息：
     
     产品链接是什么？
     [输入框]
     ❌ 取消"

用户输入: "https://example.com/product"

Round 2:
  Planner: "已有产品链接，但还需要风格"
  
  Evaluator: "风格模糊，提供选项"
  
  [Human-in-the-Loop]
  返回用户:
    "请选择素材风格：
     1️⃣ 现代简约
     2️⃣ 活力多彩
     3️⃣ 高端奢华
     ➕ 其他（描述你想要的风格）
     ❌ 取消"

用户选择: "1️⃣"

Round 3:
  Planner: "信息完整，开始生成"
  
  Evaluator: "生成素材无需确认"
  
  Act:
    - 使用 Gemini 提取产品信息
    - 使用 Gemini Imagen 生成图片（现代简约风格）
    - 调用 save_creative(image_url, metadata)
  
  Memory: 保存 creative_id
  
  Evaluator: "任务完成"

返回用户:
  "✅ 素材已生成！
   [显示图片预览]
   已保存到素材库，ID: creative-123"
```

**关键点**：
- ✅ Agent 智能识别缺失信息
- ✅ 分步请求用户输入
- ✅ 提供选项 + 自定义

---

### 示例 3：重要操作（需要人工确认）

```
用户: "用素材 creative-123 创建广告，预算 $100"

Agent ReAct 循环:

Round 1:
  Planner: "用户想创建广告，信息完整：
           - 素材：creative-123
           - 预算：$100
           需要：
           1. 获取素材信息
           2. 优化广告参数
           3. 创建广告"
  
  Evaluator: "创建广告涉及花费，需要确认"
  
  Act (部分):
    - 调用 get_creative(creative_123)
    - 使用 Gemini 优化广告参数
  
  [Human-in-the-Loop]
  返回用户:
    "我为你准备了广告设置：
     
     素材：[显示素材预览]
     预算：$100/天
     目标：转化
     出价策略：最低成本
     受众：25-35 岁女性，兴趣：时尚、美妆
     
     确认创建吗？
     ✅ 确认
     ✏️ 修改设置
     ❌ 取消"

用户选择: "✅"

Round 2:
  Planner: "用户已确认，执行创建"
  
  Act:
    - 调用 create_campaign(creative_id, settings)
  
  Memory: 保存 campaign_id
  
  Evaluator: "任务完成"

返回用户:
  "✅ 广告已创建！
   Campaign ID: 123456789
   预计今天开始投放
   
   我会持续监控表现，有问题及时通知你"
```

**关键点**：
- ✅ Agent 自动优化参数
- ✅ 展示完整设置供用户确认
- ✅ 确认后才执行

---

### 示例 4：复杂任务（多次人工介入）

```
用户: "帮我优化广告投放"

Agent ReAct 循环:

Round 1:
  Planner: "用户想优化广告，需要：
           1. 分析当前表现
           2. 生成优化建议
           3. 执行优化"
  
  Evaluator: "分析无需确认"
  
  Act:
    - 调用 fetch_ad_data()
    - 使用 Gemini 分析数据
  
  Memory: 保存分析结果
  
  Evaluator: "分析完成，但还需执行优化"

Round 2:
  Planner: "生成优化建议"
  
  [Human-in-the-Loop]
  返回用户:
    "📊 分析完成！发现 3 个优化机会：
     
     1️⃣ 暂停低效 Adset X（ROAS 1.8）
        预计节省：$20/天
     
     2️⃣ 增加高效 Adset Y 预算 50%
        预计增加收入：$50/天
     
     3️⃣ 调整受众定向，排除低转化人群
        预计提升 ROAS 15%
     
     请选择要执行的优化（可多选）：
     ☑️ 优化 1
     ☑️ 优化 2
     ☑️ 优化 3
     ✅ 全部执行
     ❌ 取消"

用户选择: "☑️ 1, ☑️ 2"

Round 3:
  Planner: "执行优化 1 和 2"
  
  Evaluator: "涉及修改广告，需要最终确认"
  
  [Human-in-the-Loop]
  返回用户:
    "即将执行：
     - 暂停 Adset X
     - 将 Adset Y 预算从 $50 增加到 $75
     
     确认执行吗？
     ✅ 确认
     ❌ 取消"

用户选择: "✅"

Round 4:
  Act:
    - 调用 pause_adset(adset_x_id)
    - 调用 update_budget(adset_y_id, new_budget=75)
  
  Evaluator: "任务完成"

返回用户:
  "✅ 优化已完成！
   - Adset X 已暂停
   - Adset Y 预算已增加到 $75
   
   我会继续监控效果"
```

**关键点**：
- ✅ 多次人工介入
- ✅ 每次介入都有明确目的
- ✅ 用户有完全控制权

---

## MCP Tools 设计

### Tools 分类

所有 Tools 只负责**数据交互**，不包含 AI 逻辑：

#### Creative Tools（素材相关）

```python
# backend/app/mcp/tools/creative.py

@mcp_tool
async def save_creative(
    url: str,
    type: str,  # "image" or "video"
    metadata: dict,
    user_id: str,
) -> dict:
    """保存素材到素材库。"""
    creative_id = await creative_service.create(url, type, metadata, user_id)
    return {"creative_id": creative_id}

@mcp_tool
async def get_creative(creative_id: str, user_id: str) -> dict:
    """获取素材信息。"""
    return await creative_service.get(creative_id, user_id)

@mcp_tool
async def list_creatives(user_id: str, filters: dict = None) -> list[dict]:
    """列出用户的素材。"""
    return await creative_service.list(user_id, filters)
```

#### Performance Tools（性能相关）

```python
# backend/app/mcp/tools/performance.py

@mcp_tool
async def fetch_ad_data(
    user_id: str,
    platform: str,  # "meta", "tiktok", "google"
    date_range: tuple,
) -> dict:
    """从广告平台抓取数据。"""
    # 调用平台 API
    data = await platform_service.fetch_data(platform, date_range)
    # 保存到数据库
    await report_service.save(user_id, data)
    return data

@mcp_tool
async def get_historical_data(
    user_id: str,
    date_range: tuple,
) -> dict:
    """获取历史数据。"""
    return await report_service.get_historical(user_id, date_range)

@mcp_tool
async def save_report(
    user_id: str,
    report_data: dict,
) -> dict:
    """保存报表。"""
    report_id = await report_service.save_report(user_id, report_data)
    return {"report_id": report_id}
```

#### Campaign Tools（广告投放相关）

```python
# backend/app/mcp/tools/campaign.py

@mcp_tool
async def create_campaign(
    user_id: str,
    platform: str,
    campaign_data: dict,
) -> dict:
    """创建广告系列。"""
    # 调用平台 API
    campaign_id = await campaign_service.create(platform, campaign_data)
    # 保存到数据库
    await campaign_service.save(user_id, campaign_id, campaign_data)
    return {"campaign_id": campaign_id}

@mcp_tool
async def update_budget(
    campaign_id: str,
    new_budget: float,
    user_id: str,
) -> dict:
    """更新广告预算。"""
    await campaign_service.update_budget(campaign_id, new_budget)
    return {"success": True}

@mcp_tool
async def pause_campaign(campaign_id: str, user_id: str) -> dict:
    """暂停广告。"""
    await campaign_service.pause(campaign_id)
    return {"success": True}
```

#### Landing Page Tools（落地页相关）

```python
# backend/app/mcp/tools/landing_page.py

@mcp_tool
async def save_landing_page(
    user_id: str,
    html_content: str,
    metadata: dict,
) -> dict:
    """保存落地页。"""
    page_id = await landing_page_service.create(user_id, html_content, metadata)
    return {"page_id": page_id}

@mcp_tool
async def upload_to_s3(
    file_content: bytes,
    file_name: str,
    user_id: str,
) -> dict:
    """上传文件到 S3。"""
    url = await storage_service.upload(file_content, file_name, user_id)
    return {"url": url}

@mcp_tool
async def create_ab_test_record(
    page_id: str,
    variants: list[dict],
    user_id: str,
) -> dict:
    """创建 A/B 测试记录。"""
    test_id = await ab_test_service.create(page_id, variants, user_id)
    return {"test_id": test_id}
```

#### Market Tools（市场洞察相关）

```python
# backend/app/mcp/tools/market.py

@mcp_tool
async def fetch_competitor_data(
    competitor_url: str,
    user_id: str,
) -> dict:
    """抓取竞品数据。"""
    data = await scraper_service.fetch(competitor_url)
    return data

@mcp_tool
async def fetch_market_data(
    industry: str,
    region: str,
) -> dict:
    """获取市场数据。"""
    data = await market_data_service.fetch(industry, region)
    return data

@mcp_tool
async def save_analysis(
    user_id: str,
    analysis_data: dict,
) -> dict:
    """保存分析结果。"""
    analysis_id = await analysis_service.save(user_id, analysis_data)
    return {"analysis_id": analysis_id}
```

---

## Business Logic Modules 设计

modules/ 不再是 Sub-Agents，而是**业务逻辑实现层**：

### 新的模块结构

```
ai-orchestrator/app/modules/
├── ad_creative/
│   ├── service.py          # AI 能力实现（调用 Gemini）
│   ├── models.py            # 数据模型
│   └── utils.py             # 工具函数
├── ad_performance/
│   ├── service.py
│   ├── models.py
│   └── utils.py
├── campaign_automation/
│   ├── service.py
│   ├── models.py
│   ├── adapters/            # 平台适配器
│   │   ├── meta_adapter.py
│   │   ├── tiktok_adapter.py
│   │   └── google_adapter.py
│   └── utils.py
├── landing_page/
│   ├── service.py
│   ├── models.py
│   └── utils.py
└── market_insights/
    ├── service.py
    ├── models.py
    └── utils.py
```

### Service 的新角色

**不是**：
- ❌ 不是 Sub-Agent
- ❌ 不是 MCP Tool 的包装器

**而是**：
- ✅ AI 能力的实现（调用 Gemini API）
- ✅ 业务逻辑的封装
- ✅ 被 Main Agent 或 MCP Tools 调用

### 示例：Ad Creative Service

```python
# ai-orchestrator/app/modules/ad_creative/service.py

class AdCreativeService:
    """素材生成服务（AI 能力实现）。"""
    
    def __init__(self):
        self.gemini_client = get_gemini_client()
    
    async def generate_image(
        self,
        product_info: dict,
        style: str,
        aspect_ratio: str = "1:1",
    ) -> str:
        """生成图片（AI 能力）。
        
        这个方法：
        - 被 Main Agent 直接调用
        - 不是 MCP Tool
        - 返回图片 URL
        """
        
        # 1. 优化 prompt
        prompt = await self._optimize_prompt(product_info, style)
        
        # 2. 调用 Gemini Imagen
        image_url = await self.gemini_client.generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
        )
        
        return image_url
    
    async def analyze_creative(
        self,
        image_url: str,
    ) -> dict:
        """分析素材质量（AI 能力）。"""
        
        analysis = await self.gemini_client.analyze_image(
            image_url=image_url,
            criteria=["clarity", "appeal", "brand_consistency"],
        )
        
        return {
            "score": analysis.score,
            "suggestions": analysis.suggestions,
        }
    
    async def _optimize_prompt(
        self,
        product_info: dict,
        style: str,
    ) -> str:
        """优化 prompt（AI 能力）。"""
        
        prompt = await self.gemini_client.optimize_prompt(
            product=product_info,
            style=style,
            task="ad_image_generation",
        )
        
        return prompt
```

**调用关系**：

```
Main Agent
    ↓
ad_creative_service.generate_image()  # AI 能力
    ↓
Gemini Imagen API
    ↓
返回 image_url
    ↓
Main Agent 调用 MCP Tool: save_creative(image_url)
    ↓
Backend 保存到数据库
```

---

## 数据模型（Data Models）

### AgentState

```python
from typing import TypedDict
from dataclasses import dataclass

@dataclass
class AgentState:
    """Agent 状态。"""
    
    # 用户信息
    user_message: str
    user_id: str
    session_id: str
    
    # 执行状态
    current_plan: Plan | None
    steps_completed: list[dict]
    
    # 人工输入状态
    waiting_for_user: bool = False
    user_input_request: UserInputRequest | None = None
```

### Plan

```python
@dataclass
class Plan:
    """执行计划。"""
    
    # 计划描述
    description: str
    
    # 需要调用的工具
    tool_calls: list[ToolCall]
    
    # 是否需要人工输入
    needs_human_input: bool = False
    question_for_user: str | None = None
    options: list[dict] | None = None
    allow_custom: bool = False
```

### UserInputRequest

```python
@dataclass
class UserInputRequest:
    """人工输入请求。"""
    
    type: str  # "confirmation", "choice", "input"
    message: str
    options: list[dict]
    input_type: str | None = None  # "text", "number", "url"
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

### Property 1: 明确任务自动执行
*For any* 明确且无风险的用户请求（如查询数据、分析性能），Agent SHALL 自动执行无需人工确认
**Validates: Requirements 1.1, 1.2, 1.3**

### Property 2: 重要操作必须确认
*For any* 涉及花费或重要操作的请求（如创建广告、修改预算），Agent SHALL 请求人工确认后才执行
**Validates: Requirements 2.2**

### Property 3: 模糊任务智能请求输入
*For any* 参数模糊的请求，Agent SHALL 提供选项（预设 + 其他 + 取消）让用户选择
**Validates: Requirements 2.3, 2.4, 2.5**

---

## 测试策略（Testing Strategy）

### Unit Testing

**ReAct Agent 测试**：
- Planner 逻辑测试
- Evaluator 判断逻辑测试
- Tool 调用测试
- Memory 存储测试

**Human-in-the-Loop 测试**：
- 确认请求生成测试
- 选项生成测试
- 用户输入处理测试

**Business Logic 测试**：
- 各模块 service.py 的方法测试
- Gemini API 调用测试（mock）

### Property-Based Testing

使用 Hypothesis 进行属性测试：

```python
# tests/test_react_agent_property.py

from hypothesis import given, strategies as st

@given(
    message=st.sampled_from([
        "我的广告表现如何？",
        "分析竞品",
        "生成报表",
    ]),
)
@pytest.mark.asyncio
async def test_clear_tasks_auto_execute(message):
    """测试明确任务自动执行。
    
    Feature: react-agent, Property 1
    """
    agent = ReActAgent()
    response = await agent.process_message(message, "user-123", "session-123")
    
    # 明确任务应该直接完成，不需要等待用户输入
    assert response.status == "completed"
    assert response.message is not None


@given(
    action=st.sampled_from([
        "create_campaign",
        "update_budget",
        "pause_campaign",
    ]),
)
@pytest.mark.asyncio
async def test_important_actions_require_confirmation(action):
    """测试重要操作必须确认。
    
    Feature: react-agent, Property 2
    """
    agent = ReActAgent()
    # 模拟 Agent 计划执行重要操作
    plan = Plan(
        description=f"Execute {action}",
        tool_calls=[ToolCall(name=action, params={})],
    )
    
    needs_confirmation = await agent.evaluator.needs_human_input(plan, state)
    
    # 重要操作必须请求确认
    assert needs_confirmation == True
```

### Integration Testing

**端到端测试**：
- 完整的 ReAct 循环测试
- 多轮对话测试
- Human-in-the-Loop 交互测试
- 复杂任务编排测试

---

## 实施步骤（Implementation Steps）

### Phase 1: 实现 ReAct Agent 核心

1. 创建 `ReActAgent` 类
2. 实现 Planner（使用 Gemini）
3. 实现 Evaluator（Guardrails）
4. 实现 Memory（Redis + State）
5. 实现主循环逻辑

### Phase 2: 实现 Human-in-the-Loop

1. 创建 `HumanInLoopHandler` 类
2. 实现确认请求生成
3. 实现选项请求生成
4. 实现用户输入处理
5. 集成到 ReAct 循环

### Phase 3: 统一 MCP Tools

1. 审查现有 Tools
2. 移除 AI 逻辑，只保留数据操作
3. 统一 Tool 接口
4. 添加清晰的描述和参数定义
5. 注册所有 Tools

### Phase 4: 重构 Business Logic Modules

1. 移除 capability.py（不再是 Agent）
2. 简化 service.py（只保留 AI 能力实现）
3. 删除所有子目录
4. 更新测试

### Phase 5: 前端 SSE 实现

1. 创建 useChat hook（SSE 版本）
2. 实现 UserInputPrompt 组件
3. 更新 ChatWindow
4. 删除 AI SDK 依赖

### Phase 6: 删除旧架构

1. 删除 Sub-Agent 代码
2. 删除 v2 架构代码
3. 删除 WebSocket 代码
4. 更新文档

### Phase 7: 测试和验证

1. 运行所有测试
2. 手动测试完整流程
3. 性能测试
4. 用户验收测试

---

## 架构对比

### 旧架构（Sub-Agents）

```
用户 → Main Orchestrator → Sub-Agent → MCP Tools → Backend
```

**问题**：
- ❌ 两层 Agent 调用
- ❌ 需要手动路由
- ❌ Sub-Agent 价值不大
- ❌ 复杂度高

### 新架构（ReAct Agent）

```
用户 → ReAct Agent (Gemini 自主编排) → MCP Tools → Backend
```

**优势**：
- ✅ 单层 Agent
- ✅ Gemini 自动路由
- ✅ 更简单
- ✅ 更强大

---

## 风险与缓解（Risks and Mitigation）

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| Gemini 规划能力不足 | 高 | 低 | 充分测试，优化 prompt |
| Human-in-the-Loop 过于频繁 | 中 | 中 | 优化 Evaluator 逻辑 |
| 重构导致功能丢失 | 高 | 中 | 充分测试，分阶段迁移 |
| 性能下降 | 中 | 低 | 性能测试，优化瓶颈 |

---

## 成功指标（Success Metrics）

### 架构简化

- ✅ 从 5 个 Sub-Agents 减少到 1 个
- ✅ 代码行数减少 50%+
- ✅ 文件数量减少 60%+

### 用户体验

- ✅ 明确任务自动执行率 > 80%
- ✅ 人工确认响应时间 < 5 秒
- ✅ 用户满意度提升

### 性能提升

- ✅ 启动时间减少 60%+
- ✅ 响应速度保持或提升
- ✅ 内存使用减少 40%+
