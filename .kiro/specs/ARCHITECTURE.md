# AAE 系统架构文档（Architecture Document）

## 系统概述（System Overview）

AAE（Automated Ad Engine）是一个基于**统一对话式 AI Agent** 的自动化广告管理系统。系统对外提供**一个对话入口**，用户通过自然语言与 Agent 交互，Agent 内部集成了 **5 种核心能力模块**，根据用户意图智能调用相应能力。

---

## 核心架构原则（Core Architecture Principles）

1. **统一对话入口**：用户只需与一个 AI Agent 对话，无需切换不同界面
2. **能力模块化**：Agent 内部由 5 个能力模块组成，可独立扩展
3. **Web Platform 作为核心数据平台**：所有业务数据统一存储和管理
4. **MCP 协议通信**：功能模块通过 MCP 协议与 Web Platform 通信
5. **智能意图识别**：Agent 自动识别用户意图并调用相应能力模块

---

## 系统架构图（System Architecture Diagram）

```
┌─────────────────────────────────────────────────────────────────┐
│                    Web Platform (用户入口)                       │
│                    (Next.js + WebSocket)                        │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │Dashboard │  │素材管理  │  │报表管理  │  │落地页库  │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐      │
│  │         嵌入式 AI Agent 对话界面 (右下角)           │      │
│  │                                                      │      │
│  │  用户: "帮我生成素材并创建广告"                      │      │
│  │  AI: "好的！正在为你生成素材..."                    │      │
│  │                                                      │      │
│  │  [WebSocket 实时通信]                               │      │
│  └─────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ WebSocket (对话)
                              │ HTTP (数据管理)
                              │
┌─────────────────────────────▼─────────────────────────────────────┐
│                        Web Platform                               │
│                   (核心数据管理平台)                               │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   数据管理模块                           │    │
│  │                                                          │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │    │
│  │  │素材管理  │ │报表数据  │ │落地页库  │ │投放管理  │  │    │
│  │  │Module    │ │Module    │ │Module    │ │Module    │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │    │
│  │                                                          │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐               │    │
│  │  │用户认证  │ │订阅计费  │ │账户管理  │               │    │
│  │  │Module    │ │Module    │ │Module    │               │    │
│  │  └──────────┘ └──────────┘ └──────────┘               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   MCP Server                             │    │
│  │              (提供工具给 AI Agent)                        │    │
│  │                                                          │    │
│  │  - get_creatives / create_creative                       │    │
│  │  - get_reports / analyze_performance                     │    │
│  │  - create_landing_page / update_landing_page             │    │
│  │  - create_campaign / update_budget                       │    │
│  │  - get_market_insights / analyze_competitor              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   数据存储层                             │    │
│  │                                                          │    │
│  │  - PostgreSQL 14 (业务数据)                             │    │
│  │  - TimescaleDB (时序数据)                               │    │
│  │  - Redis (缓存 + 会话)                                  │    │
│  │  - AWS S3 (文件存储)                                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                            │ MCP Protocol
                            │
┌───────────────────────────▼───────────────────────────────────────┐
│                    统一 AI Agent                                  │
│                  (对话式智能助手)                                  │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              对话理解与意图识别                          │    │
│  │               (Gemini 2.5 Pro)                           │    │
│  │                                                          │    │
│  │  用户输入 → 意图识别 → 调用能力模块 → 返回结果          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   5 个能力模块                           │    │
│  │                                                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │    │
│  │  │Creative      │  │Market        │  │Reporting     │ │    │
│  │  │Capability    │  │Intelligence  │  │Capability    │ │    │
│  │  │              │  │Capability    │  │              │ │    │
│  │  │- 生成素材    │  │- 竞品分析    │  │- 数据抓取    │ │    │
│  │  │- 分析素材    │  │- 趋势洞察    │  │- AI 分析     │ │    │
│  │  │- 评分素材    │  │- 策略建议    │  │- 异常检测    │ │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │    │
│  │                                                          │    │
│  │  ┌──────────────┐  ┌──────────────┐                    │    │
│  │  │Landing Page  │  │Ad Engine     │                    │    │
│  │  │Capability    │  │Capability    │                    │    │
│  │  │              │  │              │                    │    │
│  │  │- 生成落地页  │  │- 创建广告    │                    │    │
│  │  │- 多语言支持  │  │- 优化预算    │                    │    │
│  │  │- A/B 测试    │  │- 规则引擎    │                    │    │
│  │  └──────────────┘  └──────────────┘                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              能力模块协调器 (Orchestrator)               │    │
│  │                                                          │    │
│  │  - 根据用户意图选择能力模块                              │    │
│  │  - 协调多个能力模块完成复杂任务                          │    │
│  │  - 管理对话上下文和状态                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                            │ 调用广告平台 API
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐         ┌───▼────┐         ┌───▼────┐
   │Meta     │         │TikTok  │         │Google  │
   │Marketing│         │Ads API │         │Ads API │
   │API      │         │        │         │        │
   └─────────┘         └────────┘         └────────┘
```

---

## 两种调用路径（Invocation Paths）

### 路径 1：用户对话式调用（通过 AI Orchestrator）

```
用户发起 → 需要意图识别和对话管理

前端 
  → WebSocket 
  → AI Orchestrator（意图识别 + 协调器）
  → Functional Module
  → MCP Client 
  → Web Platform MCP Server
  → 数据库/S3
```

**适用场景**：
- 用户在对话中说"帮我生成素材"
- 用户在对话中说"查看报表"
- 用户在对话中说"创建广告"
- 所有需要理解用户意图的交互

### 路径 2：系统定时任务调用（直接调用功能模块）

```
系统定时 → 确定性任务，无需意图识别

Web Platform (Celery Beat 调度器)
  → Celery Worker（执行器）
  → Ad Performance（直接 Python 导入）
  → MCP Client
  → Web Platform MCP Server
  → 数据库/S3
```

**适用场景**：
- 每 6 小时自动抓取广告数据
- 每天 9:00 自动生成报告
- 每小时自动检测异常
- 每天 2:00 自动检查 Token 有效期

**为什么定时任务不通过 AI Orchestrator？**
- ❌ AI Orchestrator 是对话式的，专注于意图识别和对话管理
- ❌ 定时任务是确定性的，不需要意图识别
- ✅ Celery Worker 直接导入 Capability Python 模块更高效
- ✅ 减少网络开销和延迟

---

## 对话流程示例（Conversation Flow Examples）

### 示例 1：跨能力协作 - 生成素材并创建广告

```
用户: 帮我生成素材并创建广告

AI Agent:
  [意图识别] → 需要调用 Ad Creative + Campaign Automation
  
  [调用 Ad Creative]
  → 正在为你生成广告素材...
  → 调用 MCP: create_creative()
  → ✅ 已生成 10 张素材
  
  [调用 Campaign Automation]
  → 现在帮你创建广告...
  → 调用 MCP: create_campaign()
  → ✅ 广告已创建
  
  → 用户: "✅ 素材和广告都已完成！
           - 素材库：10 张新素材
           - Campaign ID: 123456789
           需要我帮你做什么？"
```

### 示例 2：单一能力 - 查看报表

```
用户: 我的广告表现如何？

AI Agent:
  [意图识别] → 需要调用 Ad Performance
  
  [调用 Ad Performance]
  → 调用 MCP: get_reports()
  → 调用 MCP: analyze_performance()
  
  → 用户: "📊 今日表现：
           - 花费：$87.50
           - ROAS：2.8（略低于目标 3.0）
           
           ⚠️ 发现问题：
           - Adset "51-65 岁" 表现较差（ROAS 1.8）
           
           💡 建议：
           - 暂停低效 Adset
           - 增加高效 Adset 预算
           
           需要我执行优化吗？"
```

### 示例 3：智能意图识别

```
用户: 这个产品卖得不好

AI Agent:
  [意图识别] → 用户可能需要：
    1. 查看报表（Ad Performance）
    2. 分析市场（Market Insights）
    3. 优化广告（Campaign Automation）
  
  → 用户: "我来帮你分析一下。首先看看广告数据...
           
           [调用 Ad Performance]
           📊 近 7 天数据：
           - CTR: 0.8%（偏低）
           - CPA: $45（偏高）
           
           [调用 Market Insights]
           🔍 竞品分析：
           - 竞品平均 CTR: 1.5%
           - 你的素材风格较传统
           
           💡 建议：
           1. 生成新的素材（更现代的风格）
           2. 调整目标受众
           3. 优化落地页
           
           我可以帮你执行这些优化，需要吗？"
```

---

## 模块职责（Module Responsibilities）

### 1. Web Platform（Web 平台 - 用户入口 + 核心数据管理）

**职责**：
- **用户入口**：提供 Web 界面，用户通过此访问系统
- **嵌入式对话界面**：在主站内嵌 AI Agent 对话窗口
- **WebSocket 通信**：前端与 AI Agent 的实时通信
- 用户认证、授权、订阅管理
- 所有业务数据的存储和管理
- 实现 MCP Server，为 AI Agent 提供数据访问工具

**前端模块**：
- Dashboard 仪表板
- 素材管理界面
- 报表管理界面
- 落地页管理界面
- 投放管理界面
- **嵌入式 AI Agent 对话窗口**（右下角，可展开/收起）

**后端模块**：
- 用户认证模块
- 订阅计费模块
- 素材管理模块：存储素材元数据和文件
- 报表数据模块：存储广告平台数据（时序数据）
- 落地页管理模块：存储落地页配置和文件
- 投放管理模块：存储 Campaign/Adset/Ad 数据
- **MCP Server**：提供工具给 AI Agent
- **WebSocket Server**：处理实时对话

**技术栈**：
- 前端：Next.js 14 + TypeScript + Tailwind CSS + Shadcn/ui
- 对话界面：**Vercel AI SDK**（`ai` 包）+ React
- 后端：FastAPI (Python 3.11+)
- 数据库：PostgreSQL 14 + TimescaleDB
- 缓存：Redis
- 存储：AWS S3
- 通信：HTTP Streaming（前端 ↔ AI Agent）+ MCP（AI Agent ↔ Portal）

---

### 2. AI Orchestrator（AI 协调器 - 对话引擎 + 能力调度）

**职责**：
- 提供统一的对话入口
- 理解用户意图并识别需要调用的能力模块
- 协调多个能力模块完成复杂任务
- 管理对话上下文和状态
- 通过 MCP 与 Web Platform 通信

**核心组件**：

#### 2.1 对话理解与意图识别
- 使用 Gemini 2.5 Flash 或 Claude 3.5 Sonnet
- 识别用户意图（生成素材/查看报表/创建广告等）
- 提取关键信息（预算/目标/产品链接等）
- 维护对话上下文

#### 2.2 能力模块协调器（Orchestrator）
- 根据意图选择能力模块
- 协调多个能力模块（如：生成素材 → 创建广告）
- 管理能力模块的执行顺序
- 聚合多个能力模块的结果

#### 2.3 五个功能模块（Functional Modules）

**Ad Creative（广告素材生成）**
- 生成广告素材（图片）
- 分析竞品素材
- 评估素材质量
- MCP 工具：`generate_creative`, `analyze_creative`, `score_creative`

**Market Insights（市场洞察）**
- 竞品分析
- 趋势洞察
- 策略建议
- MCP 工具：`analyze_competitor`, `get_trends`, `generate_strategy`

**Ad Performance（性能分析报表）**
- 数据抓取
- AI 分析
- 异常检测
- MCP 工具：`get_reports`, `analyze_performance`, `detect_anomaly`

**Landing Page（落地页生成）**
- 生成落地页
- 多语言支持
- A/B 测试
- MCP 工具：`create_landing_page`, `translate_page`, `ab_test`

**Campaign Automation（广告投放自动化）**
- 创建广告
- 优化预算
- 规则引擎
- MCP 工具：`create_campaign`, `optimize_budget`, `apply_rules`

**技术栈**：
- 对话理解：Gemini 2.5 Pro（Chat 对话、MCP Tools 调用）
- 素材分析：Gemini 2.5 Flash（图片/视频理解）
- 图片生成：Gemini Imagen 3
- 视频生成：Gemini Veo 3.1
- 对话管理：LangChain / LlamaIndex
- 广告 API：Meta/TikTok/Google Ads API
- MCP：实现 Client（调用 Web Platform 工具）

---

## 通信协议（Communication Protocol）

### MCP (Model Context Protocol)

AI Orchestrator 与 Web Platform 之间使用 MCP 协议通信：

1. **Web Platform 作为 MCP Server**：
   - 提供数据访问工具（get_creatives、get_reports 等）
   - 提供数据写入工具（create_campaign、update_creative 等）
   - 提供业务逻辑工具（analyze_performance、optimize_budget 等）

2. **AI Orchestrator 作为 MCP Client**：
   - 调用 Web Platform 提供的工具
   - 读取和写入业务数据
   - 不直接访问数据库

### 能力模块内部通信

能力模块之间的通信通过**协调器（Orchestrator）**进行：

```
用户输入
    │
    ▼
┌─────────────────┐
│  意图识别       │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  协调器         │ ◄─── 管理能力模块调用顺序
│  (Orchestrator) │
└─────────────────┘
    │
    ├──► Ad Creative
    │
    ├──► Market Insights
    │
    ├──► Ad Performance
    │
    ├──► Landing Page
    │
    └──► Campaign Automation
         │
         ▼
    聚合结果 → 返回用户
```

**协调器工作流程**：

```python
# 示例：用户说"帮我生成素材并创建广告"

1. 意图识别：
   - 主意图：创建广告
   - 子任务：生成素材 → 创建广告

2. 协调器执行：
   step1 = await creative_capability.generate(product_url)
   step2 = await ad_engine_capability.create_campaign(
       creative_id=step1.creative_id,
       budget=100,
       objective="CONVERSIONS"
   )

3. 返回结果：
   "✅ 素材和广告都已完成！"
```

---

## 数据流示例（Data Flow Examples）

### 示例 1：用户创建广告（跨 Agent 协作）

```
1. 用户 → Creative Agent: "帮我生成素材并创建广告"

2. Creative Agent:
   - 理解意图：需要生成素材 + 创建广告
   - 生成素材
   - 通过 MCP 调用 Web Platform: create_creative()
   - 调用 Campaign Automation 创建广告

3. Campaign Automation:
   - 接收请求
   - 通过 MCP 调用 Web Platform: get_creative()
   - 创建 Campaign
   - 通过 MCP 调用 Web Platform: create_campaign()
   - 返回结果给 Creative Agent

4. Creative Agent → 用户: "✅ 素材已生成，广告已创建！"
```

### 示例 2：用户查看报表并优化

```
1. 用户 → Reporting Agent: "我的广告表现如何？"

2. Ad Performance:
   - 通过 MCP 调用 Web Platform: get_report_data()
   - 分析数据
   - 生成建议

3. Reporting Agent → 用户: "CPA 偏高，建议暂停 Adset X"

4. 用户 → Reporting Agent: "好的，执行"

5. Reporting Agent:
   - 通过 A2A 调用 Automated Ad Engine Agent: pause_adset()

6. Campaign Automation:
   - 执行暂停操作
   - 通过 MCP 调用 Web Platform: update_adset()
   - 调用 Meta API 暂停广告

7. Automated Ad Engine Agent → Reporting Agent: "✅ 已暂停"

8. Reporting Agent → 用户: "✅ Adset X 已暂停"
```

---

## 技术栈总结（Technology Stack Summary）

### 前端
- Next.js 14 + TypeScript
- Tailwind CSS + Shadcn/ui
- WebSocket（实时对话）
- React Query（数据获取）

### 后端
- FastAPI (Python 3.11+)
- LangChain / LlamaIndex（对话管理）
- MCP SDK（协议实现）

### 数据库
- PostgreSQL 14（业务数据）
- TimescaleDB（时序数据）
- Redis（缓存 + 会话）

### 存储
- AWS S3（素材文件、落地页文件）
- CloudFront（CDN）

### AI 模型
- Gemini 2.5 Flash（图片/视频理解、素材分析）
- Gemini 2.5 Pro（Chat 对话、MCP Tools 调用）
- Gemini Imagen 3（广告图片生成）
- Gemini Veo 3.1（广告视频生成）

### 广告平台 API
- Meta Marketing API
- TikTok Ads API
- Google Ads API

### 部署
- AWS ECS（容器化部署）
- AWS RDS（数据库）
- AWS ElastiCache（Redis）
- AWS 新加坡区域

---

## 开发优先级（Development Priority）

### 第 1-2 周：Web Platform 核心
- 用户认证
- 数据模块（素材、报表、落地页、投放）
- MCP Server 实现
- 通知中心

### 第 3-4 周：Ad Creative
- 素材生成
- 竞品分析
- 素材评分
- MCP Client 实现

### 第 5 周：Ad Performance
- 对话式交互
- 数据抓取
- AI 分析
- MCP Client 实现

### 第 6 周：Market Insights + Landing Page
- 市场洞察功能
- 落地页生成功能
- MCP Client 实现

### 第 9-10 周：Campaign Automation
- 广告创建和管理
- 预算优化
- 规则引擎

---

## 参考资料（References）

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Google Gemini Agent Example](https://codelabs.developers.google.com/codelabs/currency-agent?hl=zh-cn#0)
- [LangChain Documentation](https://python.langchain.com/)
- [Meta Marketing API](https://developers.facebook.com/docs/marketing-apis)
- [TikTok Ads API](https://ads.tiktok.com/marketing_api/docs)
