# 需求文档 - AI Orchestrator（AI 协调器）

## 简介（Introduction）

统一 AI Agent 是 AAE 系统的核心智能助手，提供**唯一的对话入口**，用户通过自然语言与系统交互。Agent 内部集成了 **5 种功能模块**（Creative、Market Intelligence、Reporting、Landing Page、Ad Engine），通过智能意图识别和协调器，自动调用相应能力完成用户任务。

## 术语表（Glossary）

- **AI Orchestrator**：统一 AI Agent，提供唯一对话入口
- **Intent Recognition**：意图识别，理解用户想要做什么
- **Functional Module**：功能模块，Agent 的功能单元
- **Orchestrator**：协调器，管理功能模块的调用和协作
- **Conversation Context**：对话上下文，记住之前的对话内容
- **MCP Client**：MCP 客户端，调用 Web Platform 提供的工具

---

## 系统架构（System Architecture）

```
┌─────────────────────────────────────────────────────────┐
│                   统一 AI Agent                         │
│                                                         │
│  ┌───────────────────────────────────────────────┐    │
│  │         对话理解与意图识别                     │    │
│  │           (Gemini 2.5 Pro)                    │    │
│  └───────────────────────────────────────────────┘    │
│                        │                               │
│                        ▼                               │
│  ┌───────────────────────────────────────────────┐    │
│  │              协调器 (Orchestrator)             │    │
│  │                                                │    │
│  │  - 选择功能模块                                │    │
│  │  - 管理执行顺序                                │    │
│  │  - 聚合结果                                    │    │
│  └───────────────────────────────────────────────┘    │
│                        │                               │
│         ┌──────────────┼──────────────┐               │
│         │              │              │               │
│    ┌────▼────┐    ┌───▼────┐    ┌───▼────┐          │
│    │Ad      │    │Market  │    │Ad       │          │
│    │Creative│    │Insights│    │Performance│       │
│    └─────────┘    └────────┘    └─────────┘          │
│                                                       │
│         │              │              │               │
│    ┌────▼────┐    ┌───▼────┐                         │
│    │Landing  │    │Campaign │                        │
│    │Page     │    │Automation│                       │
│    └─────────┘    └─────────┘                        │
│                                                        │
│  所有功能模块通过 MCP 与 Web Platform 通信             │
└─────────────────────────────────────────────────────────┘
```

---

## 需求（Requirements）

### 需求 1：统一对话入口

**用户故事**：作为一个用户，我想要通过一个对话界面完成所有操作，以便无需切换不同的工具。

#### 验收标准

1. WHEN 用户访问系统 THEN AI Orchestrator SHALL 显示统一的对话界面
2. WHEN 用户发送任何消息 THEN AI Orchestrator SHALL 理解并响应
3. WHEN 用户需要不同功能 THEN AI Orchestrator SHALL 在同一对话中完成
4. WHEN 用户切换话题 THEN AI Orchestrator SHALL 保持对话连贯性
5. WHEN 用户返回系统 THEN AI Orchestrator SHALL 恢复之前的对话

---

### 需求 2：智能意图识别

**用户故事**：作为系统，我需要准确识别用户意图，以便调用正确的功能模块。

#### 验收标准

1. WHEN 用户说"生成素材" THEN AI Orchestrator SHALL 识别为 Ad Creative
2. WHEN 用户说"查看报表" THEN AI Orchestrator SHALL 识别为 Ad Performance
3. WHEN 用户说"分析竞品" THEN AI Orchestrator SHALL 识别为 Market Insights
4. WHEN 用户说"创建落地页" THEN AI Orchestrator SHALL 识别为 Landing Page
5. WHEN 用户说"创建广告" THEN AI Orchestrator SHALL 识别为 Campaign Automation

---

### 需求 3：多意图识别

**用户故事**：作为系统，我需要识别用户的多个意图，以便协调多个功能模块。

#### 验收标准

1. WHEN 用户说"生成素材并创建广告" THEN AI Orchestrator SHALL 识别两个意图
2. WHEN 识别多个意图 THEN AI Orchestrator SHALL 确定执行顺序
3. WHEN 执行多个任务 THEN AI Orchestrator SHALL 按顺序调用功能模块
4. WHEN 前一个任务失败 THEN AI Orchestrator SHALL 停止后续任务并通知用户
5. WHEN 所有任务完成 THEN AI Orchestrator SHALL 返回聚合结果

---

### 需求 4：协调器（Orchestrator）

**用户故事**：作为系统，我需要协调器管理功能模块的调用，以便完成复杂任务。

#### 验收标准

1. WHEN 协调器接收任务 THEN AI Orchestrator SHALL 分解为子任务
2. WHEN 子任务确定 THEN AI Orchestrator SHALL 选择对应的功能模块
3. WHEN 功能模块执行 THEN AI Orchestrator SHALL 传递必要的上下文
4. WHEN 功能模块返回结果 THEN AI Orchestrator SHALL 传递给下一个模块
5. WHEN 所有模块完成 THEN AI Orchestrator SHALL 聚合结果返回用户

---

### 需求 5：对话上下文管理

**用户故事**：作为系统，我需要记住对话历史，以便理解用户的后续请求。

#### 验收标准

1. WHEN 用户发送消息 THEN AI Orchestrator SHALL 保存到对话历史
2. WHEN 用户说"用刚才的素材" THEN AI Orchestrator SHALL 从上下文中找到素材
3. WHEN 用户说"再加 $50" THEN AI Orchestrator SHALL 理解是在之前预算基础上增加
4. WHEN 对话超过 100 轮 THEN AI Orchestrator SHALL 压缩早期对话
5. WHEN 用户开始新话题 THEN AI Orchestrator SHALL 标记上下文切换

---

### 需求 6：Ad Creative（素材生成能力）

**用户故事**：作为功能模块，我需要提供素材生成功能。

#### 验收标准

1. WHEN 调用 generate_creative THEN Ad Creative SHALL 生成广告素材
2. WHEN 调用 analyze_creative THEN Ad Creative SHALL 分析素材质量
3. WHEN 调用 score_creative THEN Ad Creative SHALL 评估素材评分
4. WHEN 生成素材 THEN Ad Creative SHALL 通过 MCP 存储到 Web Platform
5. WHEN 生成失败 THEN Ad Creative SHALL 返回清晰的错误信息

---

### 需求 7：Market Insights（市场洞察能力）

**用户故事**：作为功能模块，我需要提供市场分析功能。

#### 验收标准

1. WHEN 调用 analyze_competitor THEN Market Insights SHALL 分析竞品
2. WHEN 调用 get_trends THEN Market Insights SHALL 获取市场趋势
3. WHEN 调用 generate_strategy THEN Market Insights SHALL 生成广告策略
4. WHEN 分析完成 THEN Market Insights SHALL 返回结构化数据
5. WHEN 分析失败 THEN Market Insights SHALL 返回清晰的错误信息

---

### 需求 8：Ad Performance（报表能力）

**用户故事**：作为功能模块，我需要提供报表和分析功能。

#### 验收标准

1. WHEN 调用 get_reports THEN Ad Performance SHALL 获取广告数据
2. WHEN 调用 analyze_performance THEN Ad Performance SHALL 分析广告表现
3. WHEN 调用 detect_anomaly THEN Ad Performance SHALL 检测异常
4. WHEN 分析完成 THEN Ad Performance SHALL 返回 AI 生成的建议
5. WHEN 数据不足 THEN Ad Performance SHALL 提示用户等待更多数据

---

### 需求 9：Landing Page（落地页能力）

**用户故事**：作为功能模块，我需要提供落地页生成功能。

#### 验收标准

1. WHEN 调用 create_landing_page THEN Landing Page SHALL 生成落地页
2. WHEN 调用 translate_page THEN Landing Page SHALL 翻译落地页
3. WHEN 调用 ab_test THEN Landing Page SHALL 创建 A/B 测试
4. WHEN 生成完成 THEN Landing Page SHALL 返回落地页 URL
5. WHEN 生成失败 THEN Landing Page SHALL 返回清晰的错误信息

---

### 需求 10：Campaign Automation（投放引擎能力）

**用户故事**：作为功能模块，我需要提供广告创建和管理功能。

#### 验收标准

1. WHEN 调用 create_campaign THEN Campaign Automation SHALL 创建广告
2. WHEN 调用 optimize_budget THEN Campaign Automation SHALL 优化预算
3. WHEN 调用 apply_rules THEN Campaign Automation SHALL 执行规则
4. WHEN 创建完成 THEN Campaign Automation SHALL 返回 Campaign ID
5. WHEN 创建失败 THEN Campaign Automation SHALL 返回清晰的错误信息

---

### 需求 11：MCP 通信

**用户故事**：作为系统，我需要通过 MCP 协议与 Web Platform 通信。

#### 验收标准

1. WHEN Agent 启动 THEN AI Orchestrator SHALL 连接到 Web Platform MCP Server
2. WHEN 功能模块需要数据 THEN AI Orchestrator SHALL 调用 MCP 工具
3. WHEN MCP 调用成功 THEN AI Orchestrator SHALL 返回数据给功能模块
4. WHEN MCP 调用失败 THEN AI Orchestrator SHALL 重试 3 次
5. WHEN 重试失败 THEN AI Orchestrator SHALL 通知用户并记录日志

---

### 需求 12：错误处理与恢复

**用户故事**：作为系统，我需要优雅地处理错误，以便用户体验不受影响。

#### 验收标准

1. WHEN 功能模块失败 THEN AI Orchestrator SHALL 显示友好的错误信息
2. WHEN 网络错误 THEN AI Orchestrator SHALL 提示用户稍后重试
3. WHEN AI 模型超时 THEN AI Orchestrator SHALL 切换到备选模型
4. WHEN 任务部分失败 THEN AI Orchestrator SHALL 返回已完成的部分
5. WHEN 用户重试 THEN AI Orchestrator SHALL 从失败点继续

---

### 需求 13：性能优化

**用户故事**：作为系统，我需要快速响应用户，以便提供流畅的体验。

#### 验收标准

1. WHEN 用户发送消息 THEN AI Orchestrator SHALL 在 2 秒内开始响应
2. WHEN 调用功能模块 THEN AI Orchestrator SHALL 并行执行独立任务
3. WHEN 生成长回复 THEN AI Orchestrator SHALL 流式返回（Streaming）
4. WHEN 频繁调用 THEN AI Orchestrator SHALL 缓存常用数据
5. WHEN 系统负载高 THEN AI Orchestrator SHALL 排队处理请求

---

### 需求 14：对话式广告创建

**用户故事**：作为用户，我想通过对话创建广告，以便无需学习复杂操作。

#### 验收标准

1. WHEN 用户发送"我想创建广告" THEN AI Orchestrator SHALL 启动对话式创建流程
2. WHEN 对话开始 THEN AI Orchestrator SHALL 询问广告目标（提升销量/增加流量/品牌曝光）
3. WHEN 用户回答目标 THEN AI Orchestrator SHALL 询问每日预算
4. WHEN 用户回答预算 THEN AI Orchestrator SHALL 询问目标 ROAS 或 CPA
5. WHEN 信息收集完成 THEN AI Orchestrator SHALL 调用 Campaign Automation 创建广告

---

### 需求 14.1：智能信息提取

**用户故事**：作为用户，我想系统自动提取我描述中的关键信息，以便快速完成设置。

#### 验收标准

1. WHEN 用户发送"我想推广这个产品，每天预算 $100，目标 ROAS 3.0" THEN AI Orchestrator SHALL 自动提取预算和目标
2. WHEN 信息提取完成 THEN AI Orchestrator SHALL 显示提取的信息供用户确认
3. WHEN 用户确认信息 THEN AI Orchestrator SHALL 继续询问缺失的信息
4. WHEN 用户修改信息 THEN AI Orchestrator SHALL 更新提取的数据
5. WHEN 所有信息收集完成 THEN AI Orchestrator SHALL 显示广告创建摘要

---

### 需求 14.2：对话式广告管理

**用户故事**：作为用户，我想通过对话管理现有广告，以便快速执行操作。

#### 验收标准

1. WHEN 用户发送"暂停表现最差的广告" THEN AI Orchestrator SHALL 调用 Ad Performance 识别表现最差的 Adset
2. WHEN 识别完成 THEN AI Orchestrator SHALL 显示要暂停的 Adset 列表
3. WHEN 用户确认 THEN AI Orchestrator SHALL 调用 Campaign Automation 执行暂停操作
4. WHEN 操作完成 THEN AI Orchestrator SHALL 确认操作结果
5. WHEN 用户发送"给表现最好的广告加 20% 预算" THEN AI Orchestrator SHALL 自动执行预算调整

---

### 需求 14.3：智能建议与解释

**用户故事**：作为用户，我想要系统解释为什么做出某些决策，以便理解和学习。

#### 验收标准

1. WHEN 系统做出决策 THEN AI Orchestrator SHALL 解释决策原因
2. WHEN 用户询问"为什么选择这个受众" THEN AI Orchestrator SHALL 解释受众选择逻辑
3. WHEN 用户询问"为什么这个预算" THEN AI Orchestrator SHALL 解释预算分配策略
4. WHEN 用户询问"什么是 Lookalike Audience" THEN AI Orchestrator SHALL 提供简单易懂的解释
5. WHEN 用户需要建议 THEN AI Orchestrator SHALL 主动提供优化建议

---

### 需求 14.4：快速操作指令

**用户故事**：作为用户，我想使用快捷指令快速执行常见操作。

#### 验收标准

1. WHEN 用户发送"/status" THEN AI Orchestrator SHALL 显示所有广告的状态摘要
2. WHEN 用户发送"/pause [campaign_id]" THEN AI Orchestrator SHALL 暂停指定广告
3. WHEN 用户发送"/budget [campaign_id] $200" THEN AI Orchestrator SHALL 修改预算
4. WHEN 用户发送"/report today" THEN AI Orchestrator SHALL 显示今日报表
5. WHEN 用户发送"/help" THEN AI Orchestrator SHALL 显示所有可用指令

---

### 需求 14.5：安全确认机制

**用户故事**：作为系统，我需要在执行关键操作前要求用户确认，以便避免误操作。

#### 验收标准

1. WHEN 用户要求暂停所有广告 THEN AI Orchestrator SHALL 要求确认
2. WHEN 用户要求大幅调整预算（> 50%） THEN AI Orchestrator SHALL 要求确认
3. WHEN 用户要求删除广告 THEN AI Orchestrator SHALL 要求确认
4. WHEN 用户确认操作 THEN AI Orchestrator SHALL 执行并记录日志
5. WHEN 用户取消操作 THEN AI Orchestrator SHALL 取消并保持原状态

---

### 需求 15：学习与改进

**用户故事**：作为系统，我需要从用户交互中学习，以便提供更好的服务。

#### 验收标准

1. WHEN 用户采纳建议 THEN AI Orchestrator SHALL 记录成功案例
2. WHEN 用户拒绝建议 THEN AI Orchestrator SHALL 记录拒绝原因
3. WHEN 意图识别错误 THEN AI Orchestrator SHALL 从用户纠正中学习
4. WHEN 积累足够数据 THEN AI Orchestrator SHALL 优化意图识别模型
5. WHEN 发现新模式 THEN AI Orchestrator SHALL 主动提供个性化建议

---

## 对话流程示例（Conversation Flow Examples）

### 示例 1：简单任务

```
用户: 帮我生成 10 张广告图片

AI Agent:
  [意图识别] → Ad Creative
  
  好的！请告诉我产品链接或上传参考图片
  
用户: https://myshop.com/product/headphones

AI Agent:
  [调用 Ad Creative]
  → generate_creative(product_url, count=10)
  
  正在生成素材...
  ⏳ 预计 30-45 秒
  
  ✅ 生成完成！
  📊 素材评分：
  1. 简约风格-01.jpg - 92/100 ⭐
  2. 简约风格-02.jpg - 88/100
  ...
  
  需要我帮你：
  - 生成更多变体？
  - 用这些素材创建广告？
```

### 示例 2：复杂任务（多能力协作）

```
用户: 帮我生成素材并创建广告

AI Agent:
  [意图识别] → Ad Creative + Campaign Automation
  [协调器规划] → 先生成素材，再创建广告
  
  好的！我会帮你完成：
  1. 生成广告素材
  2. 创建广告投放
  
  首先，请提供产品链接
  
用户: https://myshop.com/product/headphones

AI Agent:
  [步骤 1: Ad Creative]
  → generate_creative(product_url)
  
  ✅ 素材已生成（10 张）
  
  [步骤 2: Campaign Automation]
  现在创建广告，请告诉我：
  - 每日预算？
  - 目标 ROAS？
  
用户: 每天 $100，ROAS 3.0

AI Agent:
  [调用 Campaign Automation]
  → create_campaign(creative_ids, budget=100, target_roas=3.0)
  
  正在创建广告...
  
  ✅ 全部完成！
  - 素材：10 张已生成
  - 广告：Campaign #123456 已创建
  - 预算：$100/天
  - 目标：ROAS 3.0
  
  我会持续监控并自动优化。
```

### 示例 3：智能问题诊断

```
用户: 这个产品卖得不好

AI Agent:
  [意图识别] → 用户遇到问题，需要诊断
  [协调器规划] → Ad Performance → Market Insights
  
  让我帮你分析一下...
  
  [调用 Ad Performance]
  → get_reports()
  → analyze_performance()
  
  📊 近 7 天数据：
  - CTR: 0.8%（偏低）
  - CPA: $45（偏高）
  - ROAS: 1.5（低于行业平均）
  
  [调用 Market Insights]
  → analyze_competitor()
  
  🔍 竞品分析：
  - 竞品平均 CTR: 1.5%
  - 你的素材风格较传统
  - 竞品使用更现代的视觉风格
  
  💡 我的建议：
  1. 生成新素材（现代简约风格）
  2. 调整目标受众（25-35 岁）
  3. 优化落地页（添加用户评价）
  
  需要我帮你执行这些优化吗？
```

---

## 非功能性需求（Non-Functional Requirements）

### 性能需求

1. AI Orchestrator SHALL 在 2 秒内开始响应用户消息
2. AI Orchestrator SHALL 支持 100 个并发对话
3. AI Orchestrator SHALL 使用流式响应（Streaming）提升体验

### 可靠性需求

1. AI Orchestrator SHALL 在功能模块失败时自动重试
2. AI Orchestrator SHALL 在 AI 模型失败时切换备选模型
3. AI Orchestrator SHALL 记录所有错误日志供排查

### 可扩展性需求

1. AI Orchestrator SHALL 支持动态添加新功能模块
2. AI Orchestrator SHALL 支持功能模块独立升级
3. AI Orchestrator SHALL 支持功能模块热插拔

---

## 接口协议（Interface Specifications）

AI Orchestrator 的所有接口协议详见：**[INTERFACES.md](../INTERFACES.md)**

### 对外接口

1. **WebSocket Server**：接收前端消息
   - 协议定义：[INTERFACES.md - WebSocket 协议](../INTERFACES.md#1-websocket-协议前端--unified-ai-agent)
   - 消息格式：用户消息、AI 回复、操作建议、错误消息

2. **MCP Client**：调用 Web Platform 工具
   - 协议定义：[INTERFACES.md - MCP 协议](../INTERFACES.md#2-mcp-协议unified-ai-agent--user-portal)
   - 可用工具：get_creatives、create_creative、get_reports、create_campaign 等

3. **Functional Module API**：调用功能模块
   - 协议定义：[INTERFACES.md - Module API](../INTERFACES.md#3-module-apiai-orchestrator--功能模块)
   - 统一接口：execute(action, parameters, context)

### 模块边界

**职责范围**：
- ✅ 对话理解和意图识别
- ✅ 功能模块协调
- ✅ 对话上下文管理
- ✅ 结果聚合和返回

**不负责**：
- ❌ 数据存储（由 Web Platform 负责）
- ❌ 用户认证（由 Web Platform 负责）
- ❌ 具体业务逻辑实现（由功能模块负责）

详见：[INTERFACES.md - AI Orchestrator 边界](../INTERFACES.md#2-unified-ai-agent-边界)

---

## 技术约束（Technical Constraints）

### 核心框架

- **Agent 框架**：LangGraph（LangChain 生态的状态机框架）
- **LLM 模型**：
  - Gemini 2.5 Pro（Chat 对话、MCP Tools 调用）
  - Gemini 2.5 Flash（图片/视频理解、素材分析）
  - Gemini Imagen 3（广告图片生成）
  - Gemini Veo 3.1（广告视频生成）
- **MCP 通信**：MCP SDK (Python)
- **后端框架**：FastAPI (Python 3.11+)
- **WebSocket**：FastAPI WebSocket + LangGraph streaming
- **数据库**：Redis（对话历史和会话状态）
- **部署**：独立服务，AWS ECS

### 为什么选择 LangGraph

| 特性 | LangGraph | 原生 LangChain | AutoGen |
|------|-----------|---------------|---------|
| 状态机支持 | ✅ 原生支持 | ❌ 需自行实现 | ⚠️ 部分支持 |
| 循环与分支 | ✅ 原生支持 | ❌ 需自行实现 | ✅ 支持 |
| 人工介入 (Human-in-the-loop) | ✅ 原生支持 | ❌ 需自行实现 | ✅ 支持 |
| 流式输出 | ✅ 原生支持 | ✅ 支持 | ⚠️ 有限支持 |
| 持久化检查点 | ✅ 原生支持 | ❌ 需自行实现 | ❌ 需自行实现 |
| 多 Agent 协调 | ✅ 原生支持 | ⚠️ 复杂 | ✅ 核心能力 |
| 调试与可观测性 | ✅ LangSmith 集成 | ✅ LangSmith 集成 | ⚠️ 有限 |
| 社区生态 | ✅ 活跃 | ✅ 最活跃 | ⚠️ 较小 |

---

## LangGraph 架构设计

### Agent 状态图（State Graph）

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI Orchestrator (LangGraph)                 │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    State (AgentState)                    │   │
│  │  - messages: List[BaseMessage]     # 对话历史             │   │
│  │  - user_id: str                    # 用户ID              │   │
│  │  - session_id: str                 # 会话ID              │   │
│  │  - current_intent: str             # 当前识别的意图       │   │
│  │  - pending_actions: List[Action]   # 待执行的操作         │   │
│  │  - completed_results: List[Result] # 已完成的结果         │   │
│  │  - requires_confirmation: bool     # 是否需要用户确认     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Graph Nodes                           │   │
│  │                                                          │   │
│  │    [START]                                               │   │
│  │       │                                                  │   │
│  │       ▼                                                  │   │
│  │  ┌─────────┐                                             │   │
│  │  │ router  │ ← 意图识别与路由                             │   │
│  │  └────┬────┘                                             │   │
│  │       │                                                  │   │
│  │       ├──────────────┬──────────────┬─────────────┐     │   │
│  │       ▼              ▼              ▼             ▼     │   │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐ │   │
│  │  │creative │   │reporting│   │market   │   │ad_engine│ │   │
│  │  │_node    │   │_node    │   │_intel   │   │_node    │ │   │
│  │  └────┬────┘   └────┬────┘   │_node    │   └────┬────┘ │   │
│  │       │              │       └────┬────┘        │      │   │
│  │       │              │            │             │      │   │
│  │       └──────────────┴────────────┴─────────────┘      │   │
│  │                      │                                  │   │
│  │                      ▼                                  │   │
│  │               ┌─────────────┐                           │   │
│  │               │ should_     │ ← 条件判断：是否需要确认    │   │
│  │               │ confirm     │                           │   │
│  │               └──────┬──────┘                           │   │
│  │                      │                                  │   │
│  │           ┌──────────┴──────────┐                       │   │
│  │           ▼                     ▼                       │   │
│  │    ┌─────────────┐       ┌─────────────┐               │   │
│  │    │ human_      │       │ execute     │               │   │
│  │    │ confirmation│       │ _actions    │               │   │
│  │    └──────┬──────┘       └──────┬──────┘               │   │
│  │           │                     │                       │   │
│  │           └──────────┬──────────┘                       │   │
│  │                      ▼                                  │   │
│  │               ┌─────────────┐                           │   │
│  │               │ respond     │ ← 生成最终回复             │   │
│  │               └──────┬──────┘                           │   │
│  │                      │                                  │   │
│  │                      ▼                                  │   │
│  │                   [END]                                 │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 功能模块作为 LangGraph 节点

每个功能模块作为一个 LangGraph Node，通过 MCP 调用 Web Platform 的工具：

```python
# Ad Creative Node
async def creative_node(state: AgentState) -> AgentState:
    """素材生成能力节点"""
    action = state.pending_actions[0]

    if action.type == "generate_creative":
        result = await mcp_client.call_tool(
            "create_creative",
            {
                "user_id": state.user_id,
                "product_url": action.params.product_url,
                "count": action.params.count
            }
        )
        state.completed_results.append(result)

    return state
```

---

## MCP 工具调用示例（MCP Tool Invocation Examples）

```python
# 示例：协调器调用功能模块

async def handle_user_message(message: str, context: ConversationContext):
    # 1. 意图识别
    intent = await recognize_intent(message, context)
    
    # 2. 协调器规划
    if intent == "generate_creative_and_create_ad":
        # 多步骤任务
        plan = [
            ("creative", "generate_creative"),
            ("ad_engine", "create_campaign")
        ]
    
    # 3. 执行计划
    results = []
    for module, action in plan:
        if module == "ad_creative":
            # 调用 MCP 工具
            result = await mcp_client.call_tool(
                "create_creative",
                {
                    "user_id": context.user_id,
                    "product_url": extract_url(message),
                    "count": 10
                }
            )
            results.append(result)
        
        elif module == "campaign_automation":
            # 使用前一步的结果
            creative_ids = results[0]["creative_ids"]
            result = await mcp_client.call_tool(
                "create_campaign",
                {
                    "user_id": context.user_id,
                    "creative_ids": creative_ids,
                    "budget": extract_budget(message),
                    "target_roas": extract_roas(message)
                }
            )
            results.append(result)
    
    # 4. 聚合结果返回用户
    return format_response(results)
```

---

## LangGraph 完整实现示例

### 1. 状态定义

```python
from typing import TypedDict, List, Optional, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import operator

class AgentState(TypedDict):
    """Agent 状态定义"""
    # 对话消息历史（使用 operator.add 自动追加）
    messages: Annotated[List[BaseMessage], operator.add]
    # 用户和会话信息
    user_id: str
    session_id: str
    # 意图识别结果
    current_intent: Optional[str]
    # 待执行的操作
    pending_actions: List[dict]
    # 已完成的结果
    completed_results: List[dict]
    # 是否需要用户确认
    requires_confirmation: bool
    # 确认状态
    user_confirmed: Optional[bool]
```

### 2. 节点实现

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# 初始化 LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro")

# Router 节点：意图识别
async def router_node(state: AgentState) -> AgentState:
    """识别用户意图并规划操作"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个广告投放助手的意图识别器。
        根据用户消息识别意图，可能的意图包括：
        - generate_creative: 生成广告素材
        - analyze_report: 查看报表分析
        - create_campaign: 创建广告
        - market_analysis: 市场分析
        - create_landing_page: 创建落地页
        - multi_step: 多步骤任务（如"生成素材并创建广告"）

        返回 JSON 格式：{{"intent": "xxx", "actions": [...]}}
        """),
        ("human", "{input}")
    ])

    last_message = state["messages"][-1].content
    response = await llm.ainvoke(prompt.format(input=last_message))

    # 解析意图
    intent_data = parse_intent(response.content)

    return {
        "current_intent": intent_data["intent"],
        "pending_actions": intent_data["actions"]
    }

# Creative 节点：素材生成
async def creative_node(state: AgentState) -> AgentState:
    """执行素材生成相关操作"""

    results = []
    for action in state["pending_actions"]:
        if action["type"] == "generate_creative":
            result = await mcp_client.call_tool(
                "create_creative",
                {
                    "user_id": state["user_id"],
                    "product_url": action["params"]["product_url"],
                    "count": action["params"].get("count", 10)
                }
            )
            results.append(result)

    return {"completed_results": results}

# Ad Engine 节点：广告创建
async def ad_engine_node(state: AgentState) -> AgentState:
    """执行广告创建相关操作"""

    results = []
    for action in state["pending_actions"]:
        if action["type"] == "create_campaign":
            # 如果有之前生成的素材，使用它们
            creative_ids = []
            for prev_result in state["completed_results"]:
                if "creative_ids" in prev_result:
                    creative_ids.extend(prev_result["creative_ids"])

            result = await mcp_client.call_tool(
                "create_campaign",
                {
                    "user_id": state["user_id"],
                    "creative_ids": creative_ids or action["params"].get("creative_ids"),
                    "budget": action["params"]["budget"],
                    "target_roas": action["params"].get("target_roas", 3.0)
                }
            )
            results.append(result)

    return {"completed_results": results}

# 确认节点：人工介入
async def human_confirmation_node(state: AgentState) -> AgentState:
    """等待用户确认高风险操作"""

    # 生成确认消息
    confirmation_msg = AIMessage(content=f"""
⚠️ 即将执行以下操作，请确认：

{format_pending_actions(state["pending_actions"])}

请回复 "确认" 继续执行，或 "取消" 放弃操作。
""")

    return {
        "messages": [confirmation_msg],
        "requires_confirmation": True
    }

# 响应节点：生成最终回复
async def respond_node(state: AgentState) -> AgentState:
    """生成最终响应"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个友好的广告投放助手。
        根据执行结果生成用户友好的回复。
        使用 Markdown 格式，包含关键数据和下一步建议。
        """),
        ("human", "执行结果：{results}\n\n请生成回复。")
    ])

    response = await llm.ainvoke(
        prompt.format(results=json.dumps(state["completed_results"], ensure_ascii=False))
    )

    return {"messages": [AIMessage(content=response.content)]}
```

### 3. 条件边（Conditional Edges）

```python
def route_by_intent(state: AgentState) -> str:
    """根据意图路由到不同节点"""
    intent = state["current_intent"]

    if intent == "generate_creative":
        return "creative_node"
    elif intent == "analyze_report":
        return "reporting_node"
    elif intent == "create_campaign":
        return "ad_engine_node"
    elif intent == "market_analysis":
        return "market_intel_node"
    elif intent == "create_landing_page":
        return "landing_page_node"
    elif intent == "multi_step":
        return "creative_node"  # 多步骤从第一步开始
    else:
        return "respond_node"  # 默认直接响应

def should_confirm(state: AgentState) -> str:
    """判断是否需要用户确认"""
    # 高风险操作需要确认
    high_risk_actions = ["pause_all", "delete_campaign", "large_budget_change"]

    for action in state["pending_actions"]:
        if action["type"] in high_risk_actions:
            return "human_confirmation"

    return "execute_actions"

def after_module(state: AgentState) -> str:
    """功能模块节点执行后的路由"""
    # 检查是否还有待执行的操作
    remaining_actions = [
        a for a in state["pending_actions"]
        if a not in state.get("executed_actions", [])
    ]

    if remaining_actions:
        # 继续执行下一个模块
        return route_by_intent({"current_intent": remaining_actions[0]["module"]})

    return "respond_node"
```

### 4. 构建 Graph

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

def build_agent_graph() -> StateGraph:
    """构建 Agent 状态图"""

    # 创建 Graph
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("router", router_node)
    workflow.add_node("creative_node", creative_node)
    workflow.add_node("reporting_node", reporting_node)
    workflow.add_node("market_intel_node", market_intel_node)
    workflow.add_node("landing_page_node", landing_page_node)
    workflow.add_node("ad_engine_node", ad_engine_node)
    workflow.add_node("human_confirmation", human_confirmation_node)
    workflow.add_node("respond", respond_node)

    # 设置入口
    workflow.set_entry_point("router")

    # 添加条件边：路由器 → 能力节点
    workflow.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "creative_node": "creative_node",
            "reporting_node": "reporting_node",
            "market_intel_node": "market_intel_node",
            "landing_page_node": "landing_page_node",
            "ad_engine_node": "ad_engine_node",
            "respond_node": "respond"
        }
    )

    # 能力节点 → 确认判断
    for node in ["creative_node", "reporting_node", "market_intel_node",
                 "landing_page_node", "ad_engine_node"]:
        workflow.add_conditional_edges(
            node,
            should_confirm,
            {
                "human_confirmation": "human_confirmation",
                "execute_actions": "respond"
            }
        )

    # 人工确认 → 等待用户输入（interrupt）
    workflow.add_edge("human_confirmation", END)  # 暂停等待用户确认

    # 响应 → 结束
    workflow.add_edge("respond", END)

    # 编译 Graph（带持久化）
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

# 创建 Agent 实例
agent = build_agent_graph()
```

### 5. FastAPI 集成与流式输出

```python
from fastapi import FastAPI, WebSocket
from langchain_core.messages import HumanMessage
import json

app = FastAPI()

@app.websocket("/ws/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()

    # 获取用户信息
    user_id = await get_user_from_token(websocket)

    # Graph 配置（用于持久化）
    config = {"configurable": {"thread_id": session_id}}

    while True:
        # 接收用户消息
        data = await websocket.receive_text()
        message = json.loads(data)

        # 构建初始状态
        initial_state = {
            "messages": [HumanMessage(content=message["content"])],
            "user_id": user_id,
            "session_id": session_id,
            "pending_actions": [],
            "completed_results": [],
            "requires_confirmation": False
        }

        # 流式执行 Graph
        async for event in agent.astream_events(initial_state, config, version="v2"):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                # 流式输出 LLM 响应
                content = event["data"]["chunk"].content
                if content:
                    await websocket.send_json({
                        "type": "stream",
                        "content": content
                    })

            elif kind == "on_tool_end":
                # 工具调用完成通知
                await websocket.send_json({
                    "type": "tool_result",
                    "tool": event["name"],
                    "result": event["data"]["output"]
                })

        # 发送完成消息
        await websocket.send_json({"type": "done"})
```

### 6. 检查点恢复（断点续传）

```python
# 当用户确认后恢复执行
async def resume_after_confirmation(session_id: str, confirmed: bool):
    """用户确认后恢复 Graph 执行"""

    config = {"configurable": {"thread_id": session_id}}

    # 获取当前状态
    state = agent.get_state(config)

    # 更新确认状态
    agent.update_state(config, {"user_confirmed": confirmed})

    if confirmed:
        # 继续执行
        async for event in agent.astream_events(None, config, version="v2"):
            yield event
    else:
        # 取消操作
        yield {"type": "cancelled", "message": "操作已取消"}
```
