# 需求文档 - Web Platform（Web 平台）

## 简介（Introduction）

AAE 主站是整个 Automated Ad Engine 系统的**用户入口和核心数据管理平台**。用户通过主站访问系统，主站内嵌**统一 AI Agent 对话界面**，用户通过对话完成所有操作。主站负责用户认证、账户管理、订阅计费、广告账户绑定，以及所有业务数据的存储和管理（素材管理、报表管理、落地页管理、投放管理等），并为 AI Agent 提供 MCP Server 接口。

## 术语表（Glossary）

- **AAE System**：Automated Ad Engine，自动化广告引擎系统
- **Web Platform**：用户门户，AAE 系统的核心数据管理平台
- **Ad Account**：广告账户，用户在 Meta/TikTok/Google 的广告账户
- **Credit**：积分，用户用于支付 AI 服务和增值功能的虚拟货币
- **OAuth Token**：OAuth 令牌，用于访问广告平台 API 的授权凭证
- **Dashboard**：仪表板，用户登录后的主页面
- **Billing**：计费系统，处理 Credit 充值和支付
- **Creative Library**：素材库，存储所有生成的广告素材
- **Campaign Management**：投放管理，管理所有广告投放数据
- **Landing Page Library**：落地页库，存储所有生成的落地页
- **Report Data**：报表数据，存储从广告平台抓取的数据
- **MCP**：Model Context Protocol，模型上下文协议
- **Orchestrator**：协调器，AI Orchestrator 中负责协调功能模块的组件

---

## 系统架构（System Architecture）

Web Platform 作为用户入口和核心数据管理平台，包含以下功能模块：

### 前端模块

1. **用户界面**：Next.js 14 + TypeScript + Tailwind CSS
2. **统一 AI Agent 对话界面**：嵌入式聊天组件（WebSocket 实时通信）
3. **Dashboard 仪表板**：数据可视化、快速操作
4. **数据管理界面**：素材库、报表、落地页、投放管理

### 后端模块

1. **用户认证模块**：注册、登录、权限管理
2. **订阅计费模块**：订阅管理、支付处理、发票生成
3. **广告账户管理模块**：OAuth 绑定、Token 管理
4. **素材管理模块**：存储和管理所有广告素材（图片/视频）
5. **报表数据模块**：存储从广告平台抓取的数据
6. **落地页管理模块**：存储和管理所有落地页
7. **投放管理模块**：存储和管理所有 Campaign/Adset/Ad 数据
8. **MCP Server 模块**：为 AI Agent 提供数据访问接口

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Platform (用户入口)                    │
│                                                             │
│  ┌───────────────────────────────────────────────────┐    │
│  │              前端界面 (Next.js)                    │    │
│  │                                                    │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │    │
│  │  │Dashboard │  │素材管理  │  │报表管理  │       │    │
│  │  └──────────┘  └──────────┘  └──────────┘       │    │
│  │                                                    │    │
│  │  ┌─────────────────────────────────────────┐     │    │
│  │  │    统一 AI Agent 对话界面 (嵌入式)      │     │    │
│  │  │                                          │     │    │
│  │  │  用户: 帮我生成素材并创建广告            │     │    │
│  │  │  AI: 好的！正在为你处理...              │     │    │
│  │  │                                          │     │    │
│  │  │  [WebSocket 实时通信]                   │     │    │
│  │  └─────────────────────────────────────────┘     │    │
│  └───────────────────────────────────────────────────┘    │
│                          │                                 │
│                          │ HTTP / WebSocket                │
│                          │                                 │
│  ┌───────────────────────▼───────────────────────────┐    │
│  │              后端服务 (FastAPI)                    │    │
│  │                                                    │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │    │
│  │  │用户认证  │  │订阅计费  │  │账户管理  │       │    │
│  │  └──────────┘  └──────────┘  └──────────┘       │    │
│  │                                                    │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │    │
│  │  │素材管理  │  │报表数据  │  │落地页库  │       │    │
│  │  └──────────┘  └──────────┘  └──────────┘       │    │
│  │                                                    │    │
│  │  ┌─────────────────────────────────────────┐     │    │
│  │  │         MCP Server                       │     │    │
│  │  │  (为 AI Agent 提供数据访问工具)          │     │    │
│  │  └─────────────────────────────────────────┘     │    │
│  └───────────────────────────────────────────────────┘    │
│                          │                                 │
│                          │ PostgreSQL + Redis + S3         │
│                          │                                 │
│  ┌───────────────────────▼───────────────────────────┐    │
│  │              数据存储层                            │    │
│  │                                                    │    │
│  │  - PostgreSQL 14 (业务数据)                       │    │
│  │  - TimescaleDB (时序数据)                         │    │
│  │  - Redis (缓存 + 会话)                            │    │
│  │  - AWS S3 (文件存储)                              │    │
│  └───────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ MCP Protocol
                          │
                  ┌───────▼───────┐
                  │  统一 AI Agent │
                  │  (独立服务)    │
                  │                │
                  │  - 意图识别    │
                  │  - 协调器      │
                  │  - 5种功能模块 │
                  └────────────────┘
```

---

## 需求（Requirements）

### 需求 1：用户认证与认证

**用户故事**：作为一个电商卖家，我想要注册并登录 AAE 系统，以便使用 AI Agent 和广告管理功能。

#### 验收标准
1. WHEN 用户使用 Google OAuth / facebook 登录 THEN Web Platform SHALL 自动创建或登录用户账户

---

### 需求 2：广告账户绑定

**用户故事**：作为一个用户，我想要绑定我的 Meta/TikTok/Google 广告账户，以便系统可以管理我的广告。

#### 验收标准

1. WHEN 用户点击"绑定广告账户"按钮 THEN Web Platform SHALL 启动 OAuth 授权流程
2. WHEN 用户完成 OAuth 授权 THEN Web Platform SHALL 存储加密的访问令牌
3. WHEN 访问令牌过期 THEN Web Platform SHALL 自动刷新令牌
4. WHEN 令牌刷新失败 THEN Web Platform SHALL 通知用户重新授权
5. WHEN 用户绑定多个广告账户 THEN Web Platform SHALL 允许用户在账户之间切换

---

### 需求 2.1：广告账户 Token 失效处理

**用户故事**：作为系统，我需要妥善处理广告账户 Token 失效，以便保证服务连续性。

#### Token 失效处理流程

```
┌─────────────────────────────────────────────────────────────┐
│              Token 失效处理流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 检测 Token 失效                                          │
│     - 广告平台 API 返回 401/403 错误                         │
│     - Token 过期时间临近（提前 24 小时）                     │
│                                                             │
│  2. 自动刷新 Token                                           │
│     - 使用 Refresh Token 调用平台 API                       │
│     - 更新数据库中的 Access Token                           │
│     - 记录刷新日志                                          │
│                                                             │
│  3. 刷新失败处理                                             │
│     - 暂停所有使用该账户的广告操作                           │
│     - 在 Dashboard 显示"账户授权已过期"警告                  │
│     - 发送邮件通知用户                                       │
│     - 发送站内通知                                          │
│     - 提供"重新授权"按钮                                     │
│                                                             │
│  4. 用户重新授权                                             │
│     - 用户点击"重新授权"按钮                                 │
│     - 启动 OAuth 流程                                       │
│     - 授权成功后恢复广告操作                                 │
│     - 发送恢复通知                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 验收标准

1. WHEN 检测到 Token 失效 THEN Web Platform SHALL 尝试自动刷新 Token
2. WHEN Token 刷新失败 THEN Web Platform SHALL 暂停所有使用该账户的广告操作
3. WHEN Token 刷新失败 THEN Web Platform SHALL 在 Dashboard 显示"账户授权已过期"警告横幅
4. WHEN Token 刷新失败 THEN Web Platform SHALL 发送邮件和站内通知要求用户重新授权
5. WHEN 用户点击"重新授权"按钮 THEN Web Platform SHALL 启动 OAuth 流程并在成功后恢复操作

---

### 需求 3：Credit 计费模式

**用户故事**：作为一个用户，我想要通过 Credit 按需付费，以便灵活使用 AI 功能。

#### 计费模式说明

```
┌─────────────────────────────────────────────────────────────────┐
│                    Credit 计费模式（纯 Credit）                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  核心原则：无订阅、按需付费、统一 Credit 结算                     │
│                                                                 │
│  🎁 新用户注册赠送（可配置）：                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  默认 500 Credits（永不过期）                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Credit 消耗规则（后台可动态配置，支持小数）：                     │
│  ┌────────────────────────────────────────┐                    │
│  │ 消耗类型              │ Credit 消耗     │                    │
│  ├────────────────────────────────────────┤                    │
│  │ AI 对话（Gemini Pro） │ 按 token 计算   │                    │
│  │ 图片生成（Imagen 4）  │ 0.5 credits    │                    │
│  │ 视频生成（Veo 3.1）   │ 20 credits      │                    │
│  │ 落地页生成            │ 15 credits     │                    │
│  │ 竞品深度分析          │ 10 credits     │                    │
│  │ 投放优化建议          │ 10 credits     │                    │
│  └────────────────────────────────────────┘                    │
│                                                                 │
│  Credit 包充值（从 1000 credits 起）：                            │
│  ┌────────────────────────────────────────┐                    │
│  │ 包名        │ 价格    │ Credits │ 折扣 │                    │
│  ├────────────────────────────────────────┤                    │
│  │ 体验包      │ ¥99    │ 1,000   │ 原价 │                    │
│  │ 标准包      │ ¥299   │ 3,000   │ 9折  │                    │
│  │ 专业包      │ ¥999    │ 10,000  │ 8折  │                    │
│  │ 企业包      │ ¥2,999  │ 30,000  │ 7折   │                    │
│  └────────────────────────────────────────┘                    │
│                                                                 │
│  余额不足处理：                                                   │
│  - 返回错误码 6011，提示用户充值                                  │
│  - 不支持透支，必须先充值                                        │
│                                                                 │
│  配置管理：                                                       │
│  - 所有费用和消耗规则均可后台配置                                 │
│  - 支持动态调整，实时生效（不追溯历史）                           │
│  - 配置项：注册赠送额度、token 换算系数、增值功能定价、           │
│           Credit 包价格和折扣                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 验收标准

1. WHEN 新用户完成注册 THEN Web Platform SHALL 自动赠送 500 Credits
2. WHEN 用户查看余额 THEN Web Platform SHALL 显示当前 Credit 余额和消费记录
3. WHEN 用户执行消耗 Credit 的操作 THEN Web Platform SHALL 实时扣减余额
4. WHEN Credit 余额不足 THEN Web Platform SHALL 返回错误码 6011 并提示充值
5. WHEN 管理员修改消耗规则 THEN Web Platform SHALL 对新请求生效（不追溯历史）

---

### 需求 3.1：Credit 消耗与计算

**用户故事**：作为系统，我需要根据 AI 模型实际消耗和增值功能计算 Credit，以便精确计费。

#### Credit 换算规则（后台可动态配置）

**AI 模型用途分配：**

| 功能 | 使用模型 | 说明 |
|------|---------|------|
| 图片生成 | Gemini Imagen 4 | 广告素材图片生成 |
| 视频生成 | Gemini Veo 3.1 | 广告视频生成 |
| 图片/视频理解 | Gemini 2.5 Flash | 素材分析、内容识别 |
| Chat 对话 | Gemini 2.5 Pro | 用户对话交互 |
| MCP Tools 调用 | Gemini 2.5 Pro | 工具调用和代码生成 |

**AI 模型调用（按 token 计费，支持小数）：**

| AI 模型 | Token 类型 | 换算比例（每1K tokens） |
|---------|-----------|------------------------|
| Gemini 2.5 Flash | Input | 0.01 credit |
| Gemini 2.5 Flash | Output | 0.04 credit |
| Gemini 2.5 Pro | Input | 0.05 credits |
| Gemini 2.5 Pro | Output | 0.2 credits |

**增值功能（固定收费，支持小数）：**

| 功能 | Credit 消耗 | 使用模型 | 说明 |
|------|------------|---------|------|
| 图片生成 | 0.5 credits/张 | Imagen 3 | 单张图片 |
| 批量图片生成 | 0.4 credits/张 | Imagen 3 | 10张以上享8折 |
| 视频生成 | 5 credits/个 | Veo 3.1 | 短视频素材（MVP 暂不实现） |
| 落地页生成 | 15 credits/个 | Pro + Imagen | 完整落地页 |
| 竞品深度分析 | 10 credits/次 | Pro + Flash | 含报告 |
| 投放优化建议 | 20 credits/次 | Pro | 30天数据分析 |

**增值功能 Credit 消耗说明：**

增值功能采用固定定价，包含了 AI 模型调用成本和平台服务费：

| 功能 | 消耗构成 | 说明 |
|------|---------|------|
| 图片生成 (0.5 credits) | Imagen 3 API 调用 | 直接调用图片生成模型 |
| 落地页生成 (15 credits) | Pro 文案生成 (~3 credits) + Imagen 图片 (~2 credits) + 平台服务 (~10 credits) | 包含 AI 文案、多张配图、页面托管 |
| 竞品深度分析 (10 credits) | Pro 分析 (~5 credits) + Flash 图片理解 (~2 credits) + 平台服务 (~3 credits) | 包含网页抓取、AI 分析、报告生成 |
| 投放优化建议 (20 credits) | Pro 数据分析 (~10 credits) + 平台服务 (~10 credits) | 包含 30 天数据聚合、AI 分析、策略生成 |

**注意**：以上消耗构成仅供参考，实际以固定定价为准，后台可动态调整。

#### 验收标准

1. WHEN AI Agent 完成一次调用 THEN Web Platform SHALL 根据实际 token 消耗计算 Credit
2. WHEN 用户使用增值功能 THEN Web Platform SHALL 按固定 Credit 收费
3. WHEN 计算 Credit THEN Web Platform SHALL 使用后台配置的换算规则
4. WHEN 换算规则更新 THEN Web Platform SHALL 对新请求生效（不追溯历史）
5. WHEN Credit 消耗 THEN Web Platform SHALL 实时扣减用户余额
6. WHEN 扣减失败 THEN Web Platform SHALL 回滚操作并返回错误

---

### 需求 3.2：Credit 包充值

**用户故事**：作为用户，我想要购买 Credit 包获得折扣，以便降低使用成本。

#### Credit 包定价（后台可配置）

| 包名 | 价格 | Credits | 折扣 | 单价 |
|------|------|---------|------|------|
| 体验包 | ¥99 | 1,000 | 原价 | ¥0.1/credit |
| 标准包 | ¥299 | 3,000 | 9折 | ¥0.09/credit |
| 专业包 | ¥999 | 10,000 | 8折 | ¥0.08/credit |
| 企业包 | ¥2,999 | 30,000 | 7折 | ¥0.07/credit |

#### 验收标准

1. WHEN 用户访问充值页面 THEN Web Platform SHALL 显示所有 Credit 包选项和折扣信息
2. WHEN 用户选择 Credit 包 THEN Web Platform SHALL 显示支付金额和到账 Credits
3. WHEN 用户完成支付 THEN Web Platform SHALL 立即充值对应 Credits
4. WHEN 充值完成 THEN Web Platform SHALL 发送充值成功通知
5. WHEN Credit 余额 THEN Web Platform SHALL 永不过期

---

### 需求 3.3：Credit 配置管理（管理后台）

**用户故事**：作为管理员，我想要在后台配置 Credit 相关参数，以便灵活调整定价策略。

#### 可配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| 注册赠送额度 | 500 credits | 新用户注册赠送（永不过期） |
| Gemini 2.5 Flash Input | 0.01 credit/1K tokens | 图片/视频理解 |
| Gemini 2.5 Flash Output | 0.04 credit/1K tokens | 图片/视频理解 |
| Gemini 2.5 Pro Input | 0.05 credits/1K tokens | Chat 对话/MCP 调用 |
| Gemini 2.5 Pro Output | 0.2 credits/1K tokens | Chat 对话/MCP 调用 |
| 图片生成（Imagen 4） | 0.5 credits/张 | 增值功能 |
| 视频生成（Veo 3.1） | 5 credits/个 | 增值功能 |
| 落地页生成 | 15 credits/个 | 增值功能 |
| 竞品分析 | 10 credits/次 | 增值功能 |
| 投放优化建议 | 20 credits/次 | 增值功能 |
| Credit 包定价 | 见需求 3.2 | 充值包价格和折扣 |

#### 验收标准

1. WHEN 管理员访问配置页面 THEN Web Platform SHALL 显示所有可配置项及当前值
2. WHEN 管理员修改配置 THEN Web Platform SHALL 验证输入并保存
3. WHEN 配置更新 THEN Web Platform SHALL 对新请求立即生效
4. WHEN 配置更新 THEN Web Platform SHALL 不追溯已完成的历史交易
5. WHEN 配置变更 THEN Web Platform SHALL 记录变更日志（时间、操作人、旧值、新值）

---

### 需求 4：Dashboard 仪表板

**用户故事**：作为一个用户，我想要在 Dashboard 查看关键指标和快速操作，以便高效管理广告。

#### 验收标准

1. WHEN 用户登录后 THEN Web Platform SHALL 显示 Dashboard 页面
2. WHEN Dashboard 加载 THEN Web Platform SHALL 显示今日和昨日的核心指标（花费/ROAS/CPA）
3. WHEN Dashboard 加载 THEN Web Platform SHALL 显示近 7 天的趋势图表
4. WHEN Dashboard 加载 THEN Web Platform SHALL 显示 AI 智能建议卡片
5. WHEN Dashboard 加载 THEN Web Platform SHALL 在右下角显示 AI Agent 对话入口

---

### 需求 4.1：嵌入式 AI Agent 对话界面

**用户故事**：作为一个用户，我想要在主站任何页面都能与 AI Agent 对话，以便随时获得帮助。

#### 验收标准

1. WHEN 用户访问任何页面 THEN Web Platform SHALL 在右下角显示对话图标
2. WHEN 用户点击对话图标 THEN Web Platform SHALL 展开对话窗口
3. WHEN 对话窗口展开 THEN Web Platform SHALL 通过 WebSocket 连接到 AI Agent
4. WHEN 用户发送消息 THEN Web Platform SHALL 实时显示 AI Agent 的回复
5. WHEN 用户关闭对话窗口 THEN Web Platform SHALL 保存对话历史

---

### 需求 4.2：对话界面功能

**用户故事**：作为一个用户，我想要对话界面提供丰富的功能，以便更好地与 AI 交互。

#### 验收标准

1. WHEN 用户输入消息 THEN Web Platform SHALL 支持文本、图片、链接输入
2. WHEN AI 回复 THEN Web Platform SHALL 支持流式显示（Streaming）
3. WHEN AI 提供操作建议 THEN Web Platform SHALL 显示可点击的按钮
4. WHEN 用户点击建议按钮 THEN Web Platform SHALL 自动执行对应操作
5. WHEN 对话涉及数据 THEN Web Platform SHALL 在对话中嵌入图表和卡片

---

### 需求 5：用户设置

**用户故事**：作为一个用户，我想要管理我的账户设置，以便自定义系统行为。

#### 验收标准

1. WHEN 用户访问设置页面 THEN Web Platform SHALL 显示个人信息、通知偏好、安全设置
2. WHEN 用户修改个人信息 THEN Web Platform SHALL 验证并保存更改
3. WHEN 用户修改通知偏好 THEN Web Platform SHALL 更新通知规则
4. WHEN 用户删除账户 THEN Web Platform SHALL 要求确认并删除所有用户数据

---

### 需求 5.1：数据导出（GDPR 合规）

**用户故事**：作为用户，我想要导出我的所有数据，以便备份或迁移到其他系统。

#### 数据导出内容

```
┌─────────────────────────────────────────────────────────────┐
│                    数据导出包内容                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📦 导出文件结构（ZIP 格式）：                               │
│                                                             │
│  aae_export_user123_20241126.zip                            │
│  ├── user_profile.json          # 用户基本信息              │
│  ├── ad_accounts.json            # 广告账户绑定信息          │
│  ├── credit_history.csv          # Credit 消费记录          │
│  ├── creatives/                  # 素材文件夹               │
│  │   ├── creative_001.jpg                                   │
│  │   ├── creative_002.jpg                                   │
│  │   └── creatives_metadata.json  # 素材元数据             │
│  ├── landing_pages/              # 落地页文件夹             │
│  │   ├── lp_001.html                                        │
│  │   ├── lp_002.html                                        │
│  │   └── landing_pages_metadata.json                       │
│  ├── campaigns/                  # 广告配置文件夹           │
│  │   ├── campaigns.json          # Campaign 配置           │
│  │   ├── adsets.json             # Adset 配置              │
│  │   └── ads.json                # Ad 配置                 │
│  ├── reports/                    # 报表数据文件夹           │
│  │   ├── daily_metrics.csv       # 每日指标数据            │
│  │   └── performance_summary.csv # 性能汇总               │
│  └── README.txt                  # 导出说明文件             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 验收标准

1. WHEN 用户点击"导出所有数据"按钮 THEN Web Platform SHALL 生成包含所有用户数据的 ZIP 文件
2. WHEN 生成导出文件 THEN Web Platform SHALL 包含用户信息、素材文件、落地页、广告配置、报表数据
3. WHEN 导出完成 THEN Web Platform SHALL 生成下载链接并设置 24 小时过期
4. WHEN 导出文件生成 THEN Web Platform SHALL 发送邮件通知用户下载
5. WHEN 导出过程超过 5 分钟 THEN Web Platform SHALL 在后台执行并完成后通知用户

---

### 需求 5.2：账户删除（GDPR 合规）

**用户故事**：作为用户，我想要删除我的账户和所有数据，以便行使数据删除权。

#### 账户删除流程

```
┌─────────────────────────────────────────────────────────────┐
│                    账户删除流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 用户请求删除账户                                         │
│     - 用户在设置页面点击"删除账户"                           │
│     - 显示警告：此操作不可逆                                 │
│                                                             │
│  2. 安全确认                                                 │
│     - 要求用户输入"DELETE"确认                               │
│     - 要求用户输入密码验证身份                               │
│     - 显示将被删除的数据清单                                 │
│                                                             │
│  3. 执行删除                                                 │
│     - 删除用户基本信息                                       │
│     - 删除广告账户绑定（不影响广告平台数据）                 │
│     - 删除所有素材文件（S3）                                 │
│     - 删除所有落地页文件（S3）                               │
│     - 删除所有报表数据                                       │
│     - 删除所有广告配置数据                                   │
│     - 删除所有对话历史                                       │
│     - 删除所有通知记录                                       │
│                                                             │
│  4. 删除确认                                                 │
│     - 发送删除确认邮件                                       │
│     - 注销用户会话                                           │
│     - 重定向到首页                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 验收标准

1. WHEN 用户点击"删除账户" THEN Web Platform SHALL 显示警告对话框并要求输入"DELETE"确认
2. WHEN 用户确认删除 THEN Web Platform SHALL 要求输入密码验证身份
3. WHEN 验证通过 THEN Web Platform SHALL 删除所有用户数据（数据库记录和 S3 文件）
4. WHEN 删除完成 THEN Web Platform SHALL 发送删除确认邮件并注销用户会话
5. WHEN 删除失败 THEN Web Platform SHALL 回滚操作并通知用户

---

### 需求 6：计费

**用户故事**：作为一个用户，我想要查看我的 Credit 余额和充值记录，以便进行财务管理。

#### 验收标准

1. WHEN 用户访问计费页面 THEN Web Platform SHALL 显示当前 Credit 余额
2. WHEN 用户访问计费页面 THEN Web Platform SHALL 显示充值记录和消费记录
3. WHEN 用户访问计费页面 THEN Web Platform SHALL 显示 Credit 包充值选项
4. WHEN 充值成功 THEN Web Platform SHALL 发送充值确认通知到用户邮箱

---

### 需求 7：素材管理模块

**用户故事**：作为系统，我需要提供统一的素材管理功能，以便 Ad Creative 和其他 Agent 访问素材数据。

#### 验收标准

1. WHEN Ad Creative 生成素材 THEN Web Platform SHALL 存储素材元数据到数据库
2. WHEN 素材文件上传 THEN Web Platform SHALL 存储文件到 AWS S3
3. WHEN Agent 请求素材列表 THEN Web Platform SHALL 返回用户的所有素材
4. WHEN Agent 请求素材详情 THEN Web Platform SHALL 返回素材的完整信息（URL、评分、标签）
5. WHEN Agent 删除素材 THEN Web Platform SHALL 删除数据库记录和 S3 文件

---

### 需求 8：报表数据模块

**用户故事**：作为系统，我需要存储和管理所有广告平台的数据，以便 Ad Performance 和其他 Agent 访问。

#### 验收标准

1. WHEN Ad Performance 抓取数据 THEN Web Platform SHALL 存储到 TimescaleDB 时序表
2. WHEN Agent 请求报表数据 THEN Web Platform SHALL 返回指定时间范围的数据
3. WHEN Agent 请求汇总数据 THEN Web Platform SHALL 返回聚合后的指标
4. WHEN 数据超过 90 天 THEN Web Platform SHALL 自动归档到汇总表
5. WHEN Agent 请求趋势分析 THEN Web Platform SHALL 返回时序数据

---

### 需求 9：落地页管理模块

**用户故事**：作为系统，我需要管理所有落地页数据，以便 Landing Page Agent 和其他 Agent 访问。

#### 验收标准

1. WHEN Landing Page Agent 生成落地页 THEN Web Platform SHALL 存储落地页配置到数据库
2. WHEN 落地页发布 THEN Web Platform SHALL 上传 HTML 到 S3 并配置 CloudFront
3. WHEN Agent 请求落地页列表 THEN Web Platform SHALL 返回用户的所有落地页
4. WHEN Agent 请求落地页数据 THEN Web Platform SHALL 返回落地页的转化数据
5. WHEN Agent 更新落地页 THEN Web Platform SHALL 更新数据库和重新部署

---

### 需求 10：投放管理模块

**用户故事**：作为系统，我需要管理所有广告投放数据，以便 Automated Ad Engine Agent 和其他 Agent 访问。

#### 验收标准

1. WHEN Automated Ad Engine Agent 创建广告 THEN Web Platform SHALL 存储 Campaign/Adset/Ad 结构
2. WHEN Agent 请求投放列表 THEN Web Platform SHALL 返回用户的所有投放
3. WHEN Agent 修改投放 THEN Web Platform SHALL 更新数据库并同步到广告平台
4. WHEN Agent 请求投放状态 THEN Web Platform SHALL 返回实时状态
5. WHEN Agent 删除投放 THEN Web Platform SHALL 标记为删除并保留历史记录

---

### 需求 11：Agent API 接口

**用户故事**：作为系统，我需要为 5 个 AI Agent 提供统一的 API 接口，以便 Agent 访问数据。

#### 验收标准

1. WHEN Agent 调用 API THEN Web Platform SHALL 验证 Agent 身份和权限
2. WHEN Agent 请求数据 THEN Web Platform SHALL 返回 JSON 格式的数据
3. WHEN Agent 写入数据 THEN Web Platform SHALL 验证数据格式并存储
4. WHEN API 调用失败 THEN Web Platform SHALL 返回清晰的错误信息
5. WHEN API 调用频繁 THEN Web Platform SHALL 实施 Rate Limiting

---

### 需求 12：AI Agent 通信（MCP）

**用户故事**：作为系统，我需要为 AI Agent 提供 MCP Server，以便 Agent 访问数据。

#### 验收标准

1. WHEN AI Agent 启动 THEN Web Platform SHALL 接受 MCP 连接
2. WHEN AI Agent 调用工具 THEN Web Platform SHALL 验证权限并执行
3. WHEN 工具执行成功 THEN Web Platform SHALL 返回结果给 AI Agent
4. WHEN 工具执行失败 THEN Web Platform SHALL 返回错误信息
5. WHEN AI Agent 断开连接 THEN Web Platform SHALL 清理会话状态

---

### 需求 12.1：WebSocket 实时通信

**用户故事**：作为系统，我需要通过 WebSocket 与 AI Agent 实时通信，以便提供流畅的对话体验。

#### WebSocket 连接稳定性机制

```
┌─────────────────────────────────────────────────────────────┐
│              WebSocket 连接稳定性保障                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 心跳机制                                                 │
│     - 每 30 秒发送 ping 消息                                │
│     - 60 秒未收到 pong 则判定连接断开                       │
│                                                             │
│  2. 自动重连                                                 │
│     - 连接断开后立即尝试重连                                 │
│     - 使用指数退避策略（1s, 2s, 4s）                        │
│     - 最多重连 3 次                                          │
│                                                             │
│  3. 消息队列                                                 │
│     - 断开期间的消息存入本地队列                             │
│     - 重连成功后自动发送队列中的消息                         │
│     - 队列最多保存 10 条消息                                │
│                                                             │
│  4. 连接状态显示                                             │
│     - 已连接：绿色指示灯                                     │
│     - 重连中：黄色指示灯 + "正在重连..."                     │
│     - 已断开：红色指示灯 + "连接已断开，请刷新页面"          │
│                                                             │
│  5. 超时处理                                                 │
│     - 消息发送后 60 秒未收到响应                            │
│     - 显示"响应超时，请重试"提示                             │
│     - 提供"重新发送"按钮                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 验收标准

1. WHEN 用户打开对话窗口 THEN Web Platform SHALL 建立 WebSocket 连接并显示连接状态
2. WHEN 连接建立 THEN Web Platform SHALL 每 30 秒发送心跳消息
3. WHEN 连接断开 THEN Web Platform SHALL 自动重连最多 3 次（指数退避）
4. WHEN 重连成功 THEN Web Platform SHALL 发送队列中的待发消息
5. WHEN 重连失败 THEN Web Platform SHALL 显示"连接已断开"提示并建议用户刷新页面
6. WHEN 消息发送超时（60 秒） THEN Web Platform SHALL 显示超时提示并提供重试按钮

---

### 需求 12.2：定时任务调度

**用户故事**：作为系统，我需要调度定时任务，以便自动执行数据抓取和报告生成。

#### 定时任务架构（修正版）

```
┌─────────────────────────────────────────────────────────────┐
│              Web Platform 定时任务调度架构                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Celery Beat（调度器）                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  定时任务配置：                                      │   │
│  │  - 数据抓取：每 6 小时执行一次                       │   │
│  │  - 报告生成：每天 9:00 执行                         │   │
│  │  - 异常检测：每小时执行一次                          │   │
│  │  - Token 检查：每天 2:00 执行                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          ▼                                   │
│  Celery Worker（执行器）                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. 接收定时任务                                     │   │
│  │  2. 直接调用 Ad Performance（Python 模块）    │   │
│  │  3. Ad Performance 执行数据抓取/分析          │   │
│  │  4. Ad Performance 通过 MCP 存储数据          │   │
│  │  5. Worker 处理结果（发送通知、记录日志）           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ 直接调用（Python 模块导入）
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Ad Performance（Python 模块）             │
│  - fetch_ad_data(): 抓取广告平台数据                        │
│  - generate_daily_report(): 生成每日报告                   │
│  - detect_anomalies(): 检测异常                            │
│  - 通过 MCP Client 调用 Web Platform 存储数据               │
└─────────────────────────────────────────────────────────────┘
```

**架构说明**：

定时任务不需要经过 AI Orchestrator，因为：
- ✅ 定时任务是确定性的后台任务，不需要意图识别
- ✅ Celery Worker 可以直接导入 Ad Performance Python 模块
- ✅ Ad Performance 通过 MCP 访问 Web Platform 数据
- ✅ 避免不必要的网络调用，提升性能

**对话式任务 vs 定时任务**：

| 任务类型 | 触发方式 | 执行路径 | 示例 |
|---------|---------|---------|------|
| 对话式任务 | 用户发起 | 前端 → WebSocket → AI Orchestrator → 功能模块 | "帮我生成素材" |
| 定时任务 | 系统定时 | Celery Beat → Celery Worker → 功能模块直接调用 | 每 6 小时抓取数据 |

#### 验收标准

1. WHEN 系统启动 THEN Web Platform SHALL 启动 Celery Beat 调度器和 Celery Worker
2. WHEN 到达调度时间 THEN Celery Worker SHALL 直接调用 Ad Performance Python 模块
3. WHEN Ad Performance 执行 THEN Ad Performance SHALL 通过 MCP Client 访问 Web Platform 数据
4. WHEN 任务执行完成 THEN Celery Worker SHALL 通过 MCP 调用 create_notification 发送通知
5. WHEN 任务执行失败 THEN Celery Worker SHALL 记录错误日志并重试最多 3 次

---

### 需求 13：Credit 余额管理

**用户故事**：作为系统，我需要管理用户的 Credit 余额，以便实现精确计费。

#### Credit 余额架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    用户 Credit 余额结构                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用户账户                                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │  赠送余额（gifted_credits）                               │   │
│  │  - 注册赠送的 Credits                                    │   │
│  │  - 永不过期                                              │   │
│  │  - 优先消耗                                              │   │
│  │                                                          │   │
│  │  充值余额（purchased_credits）                            │   │
│  │  - 用户购买的 Credits                                    │   │
│  │  - 永不过期                                              │   │
│  │  - 赠送余额用完后消耗                                     │   │
│  │                                                          │   │
│  │  可用余额 = 赠送余额 + 充值余额                            │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  消耗顺序：赠送余额 → 充值余额                                   │
│  余额不足时：返回错误码 6011，提示充值                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 验收标准

1. WHEN AI Agent 调用 MCP 工具 THEN Web Platform SHALL 首先检查用户 Credit 余额
2. WHEN Credit 余额充足 THEN Web Platform SHALL 执行工具并扣减 Credit
3. WHEN Credit 余额不足 THEN Web Platform SHALL 返回余额不足错误（error_code: 6011）并提示充值
4. WHEN 用户充值 THEN Web Platform SHALL 增加充值余额（永不过期）
5. WHEN 扣减 Credit THEN Web Platform SHALL 优先扣减赠送余额，再扣充值余额

---

### 需求 13.1：Credit 消耗记录

**用户故事**：作为用户，我想要查看 Credit 消耗明细，以便了解使用情况。

#### 验收标准

1. WHEN Credit 被消耗 THEN Web Platform SHALL 记录消耗明细（时间、操作类型、消耗量、模型、token数）
2. WHEN 用户查看消耗记录 THEN Web Platform SHALL 显示最近 30 天的消耗明细
3. WHEN 用户查看消耗统计 THEN Web Platform SHALL 按日/周/月汇总消耗数据
4. WHEN 用户导出记录 THEN Web Platform SHALL 支持导出 CSV 格式
5. WHEN 消耗异常（单次 > 1000 credits） THEN Web Platform SHALL 记录告警日志

---

### 需求 13.2：Credit 余额预警

**用户故事**：作为用户，我想要在 Credit 即将用完或过期时收到提醒，以便及时使用或充值。

#### 验收标准

1. WHEN Credit 余额低于 50 THEN Web Platform SHALL 在界面显示余额预警
2. WHEN Credit 余额低于 10 THEN Web Platform SHALL 发送邮件/站内通知
3. WHEN Credit 余额耗尽 THEN Web Platform SHALL 发送紧急通知并提示充值
4. WHEN 用户设置预警阈值 THEN Web Platform SHALL 按用户设置触发预警

---

### 需求 13.3：Credit 扣减逻辑

**用户故事**：作为系统，我需要在 MCP 工具调用时正确扣减 Credit。

#### 验收标准

1. WHEN AI Agent 调用 MCP 工具前 THEN Web Platform SHALL 预估 Credit 消耗并预扣
2. WHEN 工具执行完成 THEN Web Platform SHALL 根据实际消耗调整扣减（多退少补）
3. WHEN 工具执行失败 THEN Web Platform SHALL 全额退还预扣 Credit
4. WHEN 并发扣减 THEN Web Platform SHALL 使用事务保证数据一致性

---

### 需求 14：落地页编辑器

**用户故事**：作为用户，我想在浏览器中编辑落地页，以便自定义内容和样式。

#### 验收标准

1. WHEN 用户打开落地页编辑器 THEN Web Platform SHALL 显示可视化编辑界面
2. WHEN 用户点击文本元素 THEN Web Platform SHALL 允许直接编辑文本内容
3. WHEN 用户点击图片元素 THEN Web Platform SHALL 显示图片上传界面
4. WHEN 用户修改主题颜色 THEN Web Platform SHALL 实时预览颜色变化
5. WHEN 用户保存更改 THEN Web Platform SHALL 调用 Landing Page 更新落地页

---

### 需求 14.1：编辑器功能

**用户故事**：作为用户，我想要编辑器提供丰富的编辑功能，以便灵活自定义。

#### 验收标准

1. WHEN 用户编辑文本 THEN Web Platform SHALL 支持富文本编辑（粗体、斜体、颜色）
2. WHEN 用户上传图片 THEN Web Platform SHALL 自动压缩并上传到 S3
3. WHEN 用户修改布局 THEN Web Platform SHALL 提供拖拽调整功能
4. WHEN 用户撤销操作 THEN Web Platform SHALL 支持撤销/重做（最多 20 步）
5. WHEN 用户预览 THEN Web Platform SHALL 在新标签页打开预览

---

### 需求 15：报表可视化

**用户故事**：作为用户，我想查看可视化的报表，以便快速了解广告表现。

#### 验收标准

1. WHEN 用户访问报表页面 THEN Web Platform SHALL 显示核心指标卡片（花费/ROAS/CPA）
2. WHEN 页面加载 THEN Web Platform SHALL 显示近 7 天的 ROAS 趋势图
3. WHEN 页面加载 THEN Web Platform SHALL 显示近 7 天的 CPA 趋势图
4. WHEN 页面加载 THEN Web Platform SHALL 显示花费结构饼图（按 Campaign 分布）
5. WHEN 用户选择时间范围 THEN Web Platform SHALL 更新所有图表数据

---

### 需求 15.1：多层级数据展示

**用户故事**：作为用户，我想查看不同层级的数据，以便定位问题。

#### 验收标准

1. WHEN 用户访问报表页面 THEN Web Platform SHALL 默认显示 Campaign 层级数据
2. WHEN 用户点击 Campaign THEN Web Platform SHALL 展开显示该 Campaign 下的 Adset 数据
3. WHEN 用户点击 Adset THEN Web Platform SHALL 展开显示该 Adset 下的 Ad 数据
4. WHEN 用户点击 Ad THEN Web Platform SHALL 显示该 Ad 的素材表现
5. WHEN 用户切换层级 THEN Web Platform SHALL 保持筛选和排序条件

---

### 需求 15.2：图表交互

**用户故事**：作为用户，我想与图表交互，以便深入分析数据。

#### 验收标准

1. WHEN 用户悬停在数据点 THEN Web Platform SHALL 显示详细数值
2. WHEN 用户点击图例 THEN Web Platform SHALL 切换对应数据系列的显示/隐藏
3. WHEN 用户拖动时间轴 THEN Web Platform SHALL 缩放时间范围
4. WHEN 用户点击数据点 THEN Web Platform SHALL 显示该时间点的详细数据
5. WHEN 用户导出图表 THEN Web Platform SHALL 生成 PNG 或 SVG 文件

---

### 需求 16：通知中心

**用户故事**：作为用户，我想要在通知中心查看所有通知，以便不错过重要信息。

#### 通知类型和优先级

```
┌─────────────────────────────────────────────────────────────┐
│                    通知类型和优先级                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🔴 紧急通知（实时推送）：                                   │
│  - 广告被平台拒绝                                            │
│  - 广告账户 Token 过期                                       │
│  - 预算耗尽                                                  │
│  - 系统自动暂停广告                                          │
│  - Credit 余额耗尽                                           │
│                                                             │
│  🟡 重要通知（每日汇总）：                                   │
│  - 每日报表生成完成                                          │
│  - AI 优化建议                                               │
│  - CPA/ROAS 异常波动                                         │
│  - 素材生成完成                                              │
│  - 落地页生成完成                                            │
│                                                             │
│  🟢 一般通知（每周汇总）：                                   │
│  - 周报总结                                                  │
│  - 新功能上线                                                │
│  - Credit 充值成功                                           │
│  - 系统维护通知                                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 验收标准

1. WHEN 用户点击通知图标 THEN Web Platform SHALL 显示通知中心面板
2. WHEN 通知中心打开 THEN Web Platform SHALL 显示所有通知（按时间倒序）
3. WHEN 显示通知 THEN Web Platform SHALL 区分已读和未读状态
4. WHEN 用户点击通知 THEN Web Platform SHALL 标记为已读并跳转到相关页面
5. WHEN 用户点击"全部标记为已读" THEN Web Platform SHALL 标记所有通知为已读

---

### 需求 16.1：通知偏好设置

**用户故事**：作为用户，我想要自定义通知偏好，以便只接收我关心的通知。

#### 验收标准

1. WHEN 用户访问通知设置 THEN Web Platform SHALL 显示所有通知类型和推送渠道选项
2. WHEN 用户选择通知类型 THEN Web Platform SHALL 允许用户选择推送渠道（站内/邮件）
3. WHEN 用户关闭某类通知 THEN Web Platform SHALL 不再发送该类通知
4. WHEN 用户保存设置 THEN Web Platform SHALL 立即生效
5. WHEN 紧急通知 THEN Web Platform SHALL 忽略用户设置强制推送（广告被拒、Token 过期）

---

### 需求 16.2：通知推送机制

**用户故事**：作为系统，我需要通过多种渠道推送通知，以便用户及时收到。

#### 验收标准

1. WHEN 生成紧急通知 THEN Web Platform SHALL 同时发送站内通知和邮件
2. WHEN 生成重要通知 THEN Web Platform SHALL 根据用户偏好选择推送渠道
3. WHEN 发送邮件通知 THEN Web Platform SHALL 使用邮件模板并包含操作链接
4. WHEN 发送站内通知 THEN Web Platform SHALL 在通知图标显示未读数量
5. WHEN 通知超过 100 条 THEN Web Platform SHALL 自动归档 30 天前的通知

---

## 非功能性需求（Non-Functional Requirements）

### 性能需求

1. Web Platform SHALL 在 5 秒内加载 Dashboard 页面
2. Web Platform SHALL 在 2 秒内响应用户操作
3. Web Platform SHALL 支持 10 个并发用户（MVP 阶段）

### 安全需求

1. Web Platform SHALL 使用 bcrypt 加密存储用户密码
2. Web Platform SHALL 使用 AES-256 加密存储 OAuth 令牌
3. Web Platform SHALL 强制使用 HTTPS 连接

### 合规性需求

1. Web Platform SHALL 符合 GDPR 数据隐私要求
2. Web Platform SHALL 提供用户数据导出功能
3. Web Platform SHALL 提供用户数据删除功能
4. Web Platform SHALL 显示 Cookie 同意弹窗

---

## 系统边界（System Boundaries）

### 包含的功能（MVP 阶段）
- 用户注册、登录、认证（注册赠送 500 Credits）
- 广告账户绑定（Meta/TikTok/Google）
- Credit 充值和计费
- Dashboard 仪表板
- **嵌入式 AI Agent 对话界面**（用户入口）
- **WebSocket 实时通信**（与 AI Agent 通信）
- 用户设置
- **通知中心**（站内通知 + 邮件通知）
- **数据导出功能**（GDPR 合规）
- **账户删除功能**（GDPR 合规）
- **素材管理模块**（存储和管理所有素材）
- **报表数据模块**（存储广告平台数据）
- **落地页管理模块**（存储和管理落地页）
- **投放管理模块**（存储 Campaign/Adset/Ad 数据）
- **MCP Server**（为 AI Agent 提供数据访问）
- 权限和限额控制

### 不包含的功能（由其他模块负责）
- AI 对话逻辑（由统一 AI Agent 负责）
- 意图识别和协调（由统一 AI Agent 负责）
- 素材生成算法（由 AI Agent 的 Ad Creative 负责）
- 数据分析算法（由 AI Agent 的 Ad Performance 负责）
- 广告策略生成（由 AI Agent 的 Market Insights 负责）

### MVP 阶段明确不支持的功能

以下功能在 MVP 阶段（第 1-6 周）明确不包含，将在后续版本实现：

| 功能 | 计划版本 | 说明 |
|------|---------|------|
| 视频素材生成 | V2.0（第 9-10 周） | 需要更高的 AI 成本和开发时间 |
| 在线素材编辑器 | V2.0（第 11-12 周） | 建议用户使用 Canva/Figma |
| Google Ads 集成 | V1.5（第 11-12 周） | 优先支持 Meta 和 TikTok |
| 团队协作功能 | V3.0（12 周后） | 多用户、权限管理 |
| 双因素认证（2FA） | V2.0（第 11-12 周） | 企业版功能 |
| 自定义域名（落地页） | V1.5（第 11-12 周） | 付费版功能 |
| 多语言界面（中文） | V1.5（第 11-12 周） | MVP 仅英文 |
| 移动端原生 App | V3.0（12 周后） | MVP 仅响应式 Web |
| Shopify 插件 | V2.0（第 11-12 周） | 落地页自动上传到 Shopify |
| 白标方案 | V3.0（12 周后） | 面向代理商 |

---

## 技术约束（Technical Constraints）

### 前端技术栈

- **框架**：Next.js 14 + TypeScript
- **样式**：Tailwind CSS + Shadcn/ui
- **AI 对话 SDK**：Vercel AI SDK（`ai` 包）
- **状态管理**：Zustand 或 React Context
- **图表**：Recharts 或 Tremor

### Vercel AI SDK 选型理由

| 特性 | Vercel AI SDK | CopilotKit | 自定义实现 |
|------|--------------|------------|-----------|
| Next.js 集成 | ✅ 深度集成 | ⚠️ 需配置 | ❌ 需自行实现 |
| 流式响应 | ✅ 原生支持 | ✅ 支持 | ⚠️ 需手动处理 |
| 工具调用 UI | ✅ 原生支持 | ✅ 支持 | ❌ 需自行实现 |
| TypeScript | ✅ 完整类型 | ✅ 支持 | ⚠️ 需自行定义 |
| React Hooks | ✅ useChat/useCompletion | ✅ useCopilotChat | ❌ 需自行实现 |
| 社区生态 | ✅ Vercel 官方维护 | ⚠️ 较小 | - |
| 后端无关 | ✅ 支持任意后端 | ⚠️ 有限 | ✅ 完全自由 |

### 后端技术栈

- **后端框架**：FastAPI (Python 3.11+)
- 数据库：MySQL 14 (AWS RDS)
- 缓存：Redis (AWS ElastiCache)
- 文件存储：AWS S3
- CDN：CloudFront
- 认证：Auth0 或 Firebase Authentication
- 支付：Stripe
- AI Agent 通信：
  - WebSocket（前端 ↔ AI Agent）
  - MCP Protocol（AI Agent ↔ Web Platform）
- 部署：AWS 新加坡（ECS + RDS + ElastiCache + S3）

## 对话界面设计（Chat UI Design）

### 界面布局

```
┌─────────────────────────────────────────────────────────┐
│  Dashboard                                    [用户头像] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [核心指标卡片]  [趋势图表]  [AI 建议]                  │
│                                                         │
│                                                         │
│                                          ┌────────────┐ │
│                                          │            │ │
│                                          │  AI Agent  │ │
│                                          │  对话窗口  │ │
│                                          │            │ │
│                                          │  用户: ... │ │
│                                          │  AI: ...   │ │
│                                          │            │ │
│                                          │  [输入框]  │ │
│                                          └────────────┘ │
│                                                         │
│                                          [💬 对话图标]  │
└─────────────────────────────────────────────────────────┘
```

### 对话窗口功能

1. **展开/收起**：点击右下角图标展开或收起
2. **流式显示**：AI 回复逐字显示，提升体验
3. **富文本支持**：支持 Markdown、代码块、图表
4. **快速操作**：AI 建议显示为可点击按钮
5. **历史记录**：自动保存对话历史
6. **多媒体输入**：支持文本、图片、链接

---

## Vercel AI SDK 实现示例

### 1. 安装依赖

```bash
npm install ai @ai-sdk/react
```

### 2. 对话组件（useChat Hook）

```tsx
// components/chat/ChatWindow.tsx
"use client";

import { useChat, Message } from "ai/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "./MessageBubble";
import { ToolCallCard } from "./ToolCallCard";

export function ChatWindow() {
  const [isOpen, setIsOpen] = useState(false);

  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    error,
    reload,
    stop,
  } = useChat({
    api: "/api/chat",  // Next.js API Route
    // 或者直接连接后端
    // api: "https://agent.aae.com/api/chat",
    onResponse(response) {
      // 响应开始时的回调
      console.log("Streaming started");
    },
    onFinish(message) {
      // 响应完成时的回调
      console.log("Message completed:", message);
    },
    onError(error) {
      // 错误处理
      console.error("Chat error:", error);
    },
  });

  return (
    <>
      {/* 悬浮按钮 */}
      <Button
        className="fixed bottom-4 right-4 rounded-full w-14 h-14 shadow-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        💬
      </Button>

      {/* 对话窗口 */}
      {isOpen && (
        <div className="fixed bottom-20 right-4 w-96 h-[600px] bg-white rounded-lg shadow-xl flex flex-col">
          {/* 头部 */}
          <div className="p-4 border-b flex justify-between items-center">
            <h3 className="font-semibold">AI 投放助手</h3>
            <Button variant="ghost" size="sm" onClick={() => setIsOpen(false)}>
              ✕
            </Button>
          </div>

          {/* 消息列表 */}
          <ScrollArea className="flex-1 p-4">
            {messages.map((message) => (
              <div key={message.id}>
                <MessageBubble message={message} />

                {/* 显示工具调用状态 */}
                {message.toolInvocations?.map((toolInvocation) => (
                  <ToolCallCard
                    key={toolInvocation.toolCallId}
                    toolInvocation={toolInvocation}
                  />
                ))}
              </div>
            ))}

            {/* 加载状态 */}
            {isLoading && (
              <div className="flex items-center gap-2 text-gray-500">
                <span className="animate-pulse">●</span>
                AI 正在思考...
              </div>
            )}
          </ScrollArea>

          {/* 输入框 */}
          <form onSubmit={handleSubmit} className="p-4 border-t flex gap-2">
            <Input
              value={input}
              onChange={handleInputChange}
              placeholder="输入消息..."
              disabled={isLoading}
            />
            <Button type="submit" disabled={isLoading || !input.trim()}>
              发送
            </Button>
            {isLoading && (
              <Button type="button" variant="outline" onClick={stop}>
                停止
              </Button>
            )}
          </form>
        </div>
      )}
    </>
  );
}
```

### 3. 消息气泡组件

```tsx
// components/chat/MessageBubble.tsx
import { Message } from "ai";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "mb-4 flex",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "max-w-[80%] rounded-lg px-4 py-2",
          isUser
            ? "bg-blue-500 text-white"
            : "bg-gray-100 text-gray-900"
        )}
      >
        {isUser ? (
          <p>{message.content}</p>
        ) : (
          <ReactMarkdown
            className="prose prose-sm max-w-none"
            components={{
              // 自定义代码块渲染
              code({ node, inline, className, children, ...props }) {
                return inline ? (
                  <code className="bg-gray-200 px-1 rounded" {...props}>
                    {children}
                  </code>
                ) : (
                  <pre className="bg-gray-800 text-white p-2 rounded overflow-x-auto">
                    <code {...props}>{children}</code>
                  </pre>
                );
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}
```

### 4. 工具调用卡片

```tsx
// components/chat/ToolCallCard.tsx
import { ToolInvocation } from "ai";
import { Card } from "@/components/ui/card";
import { Loader2, CheckCircle, XCircle } from "lucide-react";

interface ToolCallCardProps {
  toolInvocation: ToolInvocation;
}

export function ToolCallCard({ toolInvocation }: ToolCallCardProps) {
  const { toolName, state, result } = toolInvocation;

  // 工具名称映射
  const toolDisplayNames: Record<string, string> = {
    create_creative: "生成素材",
    create_campaign: "创建广告",
    get_reports: "获取报表",
    analyze_performance: "分析表现",
  };

  return (
    <Card className="p-3 mb-2 bg-blue-50 border-blue-200">
      <div className="flex items-center gap-2">
        {state === "call" && (
          <>
            <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
            <span className="text-sm text-blue-700">
              正在{toolDisplayNames[toolName] || toolName}...
            </span>
          </>
        )}

        {state === "result" && (
          <>
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span className="text-sm text-green-700">
              {toolDisplayNames[toolName] || toolName}完成
            </span>
          </>
        )}
      </div>

      {/* 显示结果摘要 */}
      {state === "result" && result && (
        <div className="mt-2 text-xs text-gray-600">
          {typeof result === "object" && "message" in result && (
            <p>{result.message}</p>
          )}
        </div>
      )}
    </Card>
  );
}
```

### 5. Next.js API Route（代理到后端）

```ts
// app/api/chat/route.ts
import { StreamingTextResponse, LangChainStream } from "ai";

export const runtime = "edge";

export async function POST(req: Request) {
  const { messages } = await req.json();

  // 获取用户 session
  const session = await getSession(req);

  // 转发到 LangGraph 后端
  const response = await fetch(`${process.env.AGENT_API_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.accessToken}`,
    },
    body: JSON.stringify({
      messages,
      user_id: session.userId,
      session_id: session.chatSessionId,
    }),
  });

  // 返回流式响应
  return new StreamingTextResponse(response.body!);
}
```

### 6. 与 LangGraph 后端集成

```python
# FastAPI 后端 - 返回 Vercel AI SDK 兼容的流式响应
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
import json

app = FastAPI()

@app.post("/chat")
async def chat(request: ChatRequest):
    """处理聊天请求，返回 Vercel AI SDK 兼容的流式响应"""

    async def generate():
        config = {"configurable": {"thread_id": request.session_id}}

        initial_state = {
            "messages": [HumanMessage(content=request.messages[-1]["content"])],
            "user_id": request.user_id,
            "session_id": request.session_id,
        }

        async for event in agent.astream_events(initial_state, config, version="v2"):
            if event["event"] == "on_chat_model_stream":
                # 流式文本输出
                content = event["data"]["chunk"].content
                if content:
                    # Vercel AI SDK 格式: "0:text\n"
                    yield f"0:{json.dumps(content)}\n"

            elif event["event"] == "on_tool_start":
                # 工具调用开始
                tool_call = {
                    "toolCallId": event["run_id"],
                    "toolName": event["name"],
                    "args": event["data"]["input"],
                }
                yield f"9:{json.dumps(tool_call)}\n"

            elif event["event"] == "on_tool_end":
                # 工具调用结束
                tool_result = {
                    "toolCallId": event["run_id"],
                    "result": event["data"]["output"],
                }
                yield f"a:{json.dumps(tool_result)}\n"

        # 结束标记
        yield "d:{}\n"

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "X-Vercel-AI-Data-Stream": "v1",
        }
    )
```

---

### WebSocket 消息格式

```json
{
  "type": "user_message",
  "content": "帮我生成素材并创建广告",
  "user_id": "user123",
  "session_id": "session456",
  "timestamp": "2024-11-26T10:00:00Z"
}

{
  "type": "agent_message",
  "content": "好的！正在为你生成素材...",
  "streaming": true,
  "session_id": "session456",
  "timestamp": "2024-11-26T10:00:01Z"
}

{
  "type": "agent_action",
  "action": "show_button",
  "button_text": "查看素材",
  "button_action": "navigate_to_creatives",
  "session_id": "session456"
}
```

## 接口协议（Interface Specifications）

Web Platform 的所有接口协议详见：**[INTERFACES.md](../INTERFACES.md)**

### 对外接口总览

1. **WebSocket API**：前端 ↔ AI Orchestrator
2. **MCP Server**：AI Orchestrator ↔ Web Platform
3. **RESTful API**：可选，用于第三方集成

### MCP Server 工具列表

Web Platform 作为 MCP Server，提供以下工具给 AI Orchestrator：

| 工具名称 | 描述 | 用途 |
|---------|------|------|
| `get_creatives` | 获取素材列表 | Ad Creative 查询素材 |
| `create_creative` | 创建新素材 | Ad Creative 使用 |
| `get_upload_url` | 获取 S3 预签名上传 URL | Ad Creative 上传素材文件 |
| `get_reports` | 获取报表数据 | Ad Performance 使用 |
| `analyze_performance` | 分析广告表现 | Ad Performance 使用 |
| `create_campaign` | 创建广告 Campaign | Campaign Automation 使用 |
| `update_budget` | 更新广告预算 | Campaign Automation 使用 |
| `create_landing_page` | 创建落地页 | Landing Page 使用 |
| `analyze_competitor` | 分析竞品 | Market Insights 使用 |

完整的工具定义和参数说明请参考：**[INTERFACES.md - MCP 协议](../INTERFACES.md#2-mcp-协议unified-ai-agent--user-portal)**

### WebSocket 消息格式

详见：**[INTERFACES.md - WebSocket 协议](../INTERFACES.md#1-websocket-协议前端--unified-ai-agent)**

### 数据模型

详见各数据管理模块的需求说明。
