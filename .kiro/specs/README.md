# AAE 系统需求文档总览

## 📋 文档结构

本目录包含 AAE（Automated Ad Engine）系统的完整需求文档，采用**统一对话入口 + 模块化能力**的设计。

---

## 🏗️ 系统架构

AAE 系统采用**统一 AI Agent + 5 种能力模块**的架构：

- **统一对话入口**：用户只需与一个 AI Agent 对话
- **Web Platform**：核心数据管理平台，存储所有业务数据
- **5 种能力模块**：Creative、Market Intelligence、Reporting、Landing Page、Ad Engine
- **MCP 协议**：Agent 与 Portal 之间的通信协议
- **智能协调器**：根据用户意图调用相应能力模块

详细架构请查看：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 💡 核心理念

**一个对话入口，多种能力**

用户不需要切换不同的 Agent 或界面，只需与一个智能助手对话：

```
用户: 帮我生成素材并创建广告
AI Agent: [自动调用 Ad Creative + Campaign Automation]
         ✅ 素材和广告都已完成！
```

AI Agent 会自动：
1. 理解用户意图
2. 选择需要的能力模块
3. 协调多个能力模块完成任务
4. 返回统一的结果

---

## 📁 需求文档列表

### 1. [Web Platform - Web 平台（前端 + 后端 + 数据管理）](./web-platform/requirements.md)

**职责**：
- **用户入口**：提供 Web 界面
- **嵌入式 AI Agent 对话界面**：用户通过对话完成所有操作
- **WebSocket 实时通信**：前端与 AI Agent 通信
- 用户认证、订阅管理
- 数据管理模块（素材、报表、落地页、投放）
- MCP Server 实现

**界面示例**：
```
┌─────────────────────────────────────────┐
│  Dashboard          [用户头像]          │
├─────────────────────────────────────────┤
│  [核心指标]  [趋势图表]                 │
│                                         │
│                      ┌────────────┐    │
│                      │ AI Agent   │    │
│                      │ 对话窗口   │    │
│                      │            │    │
│                      │ 用户: ...  │    │
│                      │ AI: ...    │    │
│                      └────────────┘    │
│                      [💬 对话图标]     │
└─────────────────────────────────────────┘
```

**关键需求**：15 个需求
- 用户注册与认证
- 广告账户绑定
- 订阅管理
- Dashboard 仪表板
- **嵌入式 AI Agent 对话界面**（新增）
- **对话界面功能**（新增）
- 用户设置
- 计费与发票
- 素材管理模块
- 报表数据模块
- 落地页管理模块
- 投放管理模块
- Agent API 接口
- **AI Agent 通信（MCP）**（新增）
- **WebSocket 实时通信**（新增）
- 权限与限额管理

---

### 2. [AI Orchestrator - AI 协调器（对话引擎 + 能力调度）](./ai-orchestrator/requirements.md)

**交互方式**：统一对话入口 ✅

**职责**：
- 提供统一的对话入口
- 理解用户意图
- 协调 5 种能力模块
- 管理对话上下文

**对话示例**：
```
用户: 帮我生成素材并创建广告
AI Agent: [调用 Ad Creative]
         正在生成 10 张素材...
         ✅ 素材已生成
         
         [调用 Campaign Automation]
         正在创建广告...
         ✅ 广告已创建
         
         全部完成！需要我做什么？
```

**5 种能力模块**：

#### 2.1 Ad Creative（广告素材生成）
- 生成广告素材（图片）
- 分析竞品素材
- 评估素材质量
- MCP 工具：`generate_creative`, `analyze_creative`

#### 2.2 Market Insights（市场洞察）
- 竞品分析
- 趋势洞察
- 策略建议
- MCP 工具：`analyze_competitor`, `get_trends`

#### 2.3 Ad Performance（广告投放报表）
- 数据抓取
- AI 分析
- 异常检测
- MCP 工具：`get_reports`, `analyze_performance`

#### 2.4 Landing Page（落地页生成）
- 生成落地页
- 多语言支持
- A/B 测试
- MCP 工具：`create_landing_page`, `ab_test`

#### 2.5 Campaign Automation（广告投放自动化）
- 创建广告
- 优化预算
- 规则引擎
- MCP 工具：`create_campaign`, `optimize_budget`

**关键需求**：
- 意图识别与理解
- 能力模块协调
- 对话上下文管理
- MCP 通信
- 多能力协作

---

## 🔄 能力模块协作示例

### 示例：用户创建完整广告流程

```
1. 用户 → AI Agent: "帮我生成素材并创建广告"

2. AI Agent (意图识别):
   - 识别意图：需要生成素材 + 创建广告
   - 规划执行：Ad Creative → Campaign Automation

3. AI Agent (执行):
   [调用 Ad Creative]
   - 调用 MCP: generate_creative()
   - 生成 10 张素材
   
   [调用 Campaign Automation]
   - 调用 MCP: create_campaign()
   - 创建广告并挂载素材

4. AI Agent → 用户: 
   "✅ 全部完成！
    - 素材：10 张已生成
    - 广告：Campaign #123456 已创建
    需要我做什么？"
```

### 示例：智能问题诊断

```
1. 用户 → AI Agent: "这个产品卖得不好"

2. AI Agent (意图识别):
   - 识别意图：用户遇到问题，需要诊断
   - 规划执行：Ad Performance → Market Insights

3. AI Agent (执行):
   [调用 Ad Performance]
   - 调用 MCP: get_reports()
   - 分析：CTR 偏低、CPA 偏高
   
   [调用 Market Insights]
   - 调用 MCP: analyze_competitor()
   - 发现：竞品素材更现代

4. AI Agent → 用户:
   "我帮你分析了一下：
    📊 你的 CTR 0.8%，竞品平均 1.5%
    🔍 竞品使用更现代的素材风格
    
    💡 建议：
    1. 生成新素材（现代风格）
    2. 优化目标受众
    
    需要我帮你执行吗？"
```

---

## 📊 开发优先级

基于 90 天计划：

| 周次 | 模块 | 状态 |
|------|------|------|
| 1-2 周 | Web Platform（核心平台 + MCP Server） | 📝 需求已完成 |
| 3-6 周 | AI Orchestrator（对话引擎 + 协调器） | 📝 需求已完成 |
| 3-4 周 | Ad Creative（广告素材生成） | 📝 需求已完成 |
| 5 周 | Ad Performance（广告投放报表） | 📝 需求已完成 |
| 6 周 | Market Insights + Landing Page | 📝 需求已完成 |
| 9-10 周 | Campaign Automation（广告投放自动化） | 📝 需求已完成 |
| 9-10 周 | 模块集成与优化 | 🔄 待开发 |

---

## 🔧 技术栈

### 前端
- Next.js 14 + TypeScript
- Tailwind CSS + Shadcn/ui
- WebSocket（实时对话）

### 后端
- FastAPI (Python 3.11+)
- LangChain（对话管理）
- MCP SDK（协议实现）

### 数据库
- PostgreSQL 14 + TimescaleDB
- Redis

### AI 模型
- Gemini 2.5 Flash（对话 + 文本）
- AWS Bedrock Stable Diffusion XL（图片）
- AWS Bedrock Claude 3.5 Sonnet（备选）

### 部署
- AWS ECS + RDS + ElastiCache + S3
- AWS 新加坡区域

---

## 📝 下一步行动

### 立即行动
1. ✅ Web Platform 需求已完成
2. ✅ Ad Creative 需求已完成
3. ✅ Market Insights 需求已完成
4. ✅ Campaign Automation 需求已完成
5. ✅ Landing Page 需求已完成
6. ✅ Ad Performance 需求已完成
7. ✅ AI Orchestrator 需求已完成
8. ✅ 旧 Agent 文件夹已清理

### 后续步骤
1. 为每个模块创建 `design.md`（设计文档）
2. 为每个模块创建 `tasks.md`（任务清单）
3. 开始开发 Web Platform
4. 逐步开发各个 Agent

---

## 📚 参考资料

- [系统架构文档](./ARCHITECTURE.md)
- [接口协议文档](./INTERFACES.md)
- [需求修复总结](./REQUIREMENTS_FIX_SUMMARY.md)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [Google Gemini Agent Example](https://codelabs.developers.google.com/codelabs/currency-agent?hl=zh-cn#0)

---

## 🎯 核心创新点

1. **统一对话入口**：用户只需与一个 AI Agent 对话，无需切换界面
2. **智能意图识别**：AI 自动理解用户需求并调用相应能力
3. **能力模块化**：5 种能力模块可独立开发和扩展
4. **智能协调**：自动协调多个能力模块完成复杂任务
5. **中心化数据**：Web Platform 统一管理数据，避免数据分散
6. **MCP 协议**：标准化的通信协议，易于扩展新能力
7. **AI 驱动**：从素材生成到广告优化，全流程 AI 自动化

## 🆚 与传统多 Agent 架构的区别

### 传统多 Agent 架构
```
用户需要：
1. 打开素材生成 Agent → 生成素材
2. 切换到广告创建 Agent → 创建广告
3. 切换到报表 Agent → 查看数据
```

### AAE 统一 Agent 架构
```
用户只需：
1. 对话："帮我生成素材并创建广告"
2. AI Agent 自动完成所有步骤
3. 返回统一结果
```

**优势**：
- ✅ 用户体验更流畅（无需切换）
- ✅ 学习成本更低（只需自然语言）
- ✅ 任务执行更智能（自动协调）
- ✅ 扩展性更强（新增能力模块即可）

---

**文档版本**：v1.0
**最后更新**：2024-11-26
**维护者**：AAE 开发团队
