# 需求文档 - AAE 架构全面简化

## 简介（Introduction）

当前 AAE 系统存在多处架构复杂性问题：前端使用了不必要的 AI agent 框架、AI Orchestrator 存在 v2/v3 双架构、capability 模块内部结构过于复杂、5 个独立模块可能存在冗余。本需求旨在全面简化架构，提升可维护性和开发效率。

## 术语表（Glossary）

- **Vercel AI SDK**：前端当前使用的 AI agent 框架（`ai` 包）
- **v2 架构**：AI Orchestrator 基于多节点状态机的复杂架构
- **v3 架构**：AI Orchestrator 基于 Gemini Function Calling 的简化架构
- **Capability Module**：AI Orchestrator 中的功能模块（ad_creative, ad_performance 等）
- **Sub-Agent**：通过 Function Calling 暴露给 Gemini 的功能模块

---

## 需求（Requirements）

### 需求 1：移除前端 AI Agent 框架，使用 SSE

**用户故事**：作为开发者，我需要移除前端的 Vercel AI SDK，以便使用更简单的 Server-Sent Events (SSE) 通信方式。

#### 验收标准

1. WHEN 前端简化完成 THEN 系统 SHALL 移除 `ai` 包依赖
2. WHEN 前端简化完成 THEN 系统 SHALL 使用原生 `EventSource` API 替代 AI SDK
3. WHEN 前端简化完成 THEN 系统 SHALL 通过 HTTP POST 发送用户消息
4. WHEN 前端简化完成 THEN 系统 SHALL 通过 SSE 接收 AI 流式响应
5. WHEN 前端简化完成 THEN 系统 SHALL 删除 `frontend/src/app/api/chat/route.ts`（不再需要 Next.js API route）
6. WHEN 前端简化完成 THEN 系统 SHALL 保持聊天功能完整性

---

### 需求 2：完成 AI Orchestrator v3 迁移

**用户故事**：作为开发者，我需要删除 v2 架构代码，以便减少维护负担。

#### 验收标准

1. WHEN v3 迁移完成 THEN 系统 SHALL 只保留 v3 架构的 LangGraph 实现
2. WHEN v3 迁移完成 THEN 系统 SHALL 删除 `app/nodes/` 目录（除 persist.py）
3. WHEN v3 迁移完成 THEN 系统 SHALL 删除 `app/core/routing.py`
4. WHEN v3 迁移完成 THEN 系统 SHALL 统一 API 端点为 `/api/v1/chat`
5. WHEN v3 迁移完成 THEN 系统 SHALL 减少启动时间至少 40%

---

### 需求 3：简化 Capability 模块内部结构

**用户故事**：作为开发者，我需要简化每个 capability 模块的内部结构，以便更容易理解和维护。

#### 验收标准

1. WHEN 模块简化完成 THEN 每个模块 SHALL 只保留 3-4 个核心文件
2. WHEN 模块简化完成 THEN 系统 SHALL 将 fetchers/analyzers/managers 合并到 service.py
3. WHEN 模块简化完成 THEN 系统 SHALL 删除过度抽象的 base 类
4. WHEN 模块简化完成 THEN 系统 SHALL 减少每个模块的文件数量至少 50%
5. WHEN 模块简化完成 THEN 系统 SHALL 保持所有核心功能不变

---

### 需求 4：保持 5 个 Capability 模块独立

**用户故事**：作为开发者，我需要保持 5 个能力模块的独立性，只简化每个模块的内部结构。

#### 验收标准

1. WHEN 模块简化完成 THEN 系统 SHALL 保持 5 个独立模块（ad_creative, market_insights, ad_performance, landing_page, campaign_automation）
2. WHEN 模块简化完成 THEN 每个模块 SHALL 只保留核心文件（capability.py, service.py, models.py, utils.py）
3. WHEN 模块简化完成 THEN 系统 SHALL 删除每个模块的子目录（fetchers/, analyzers/, managers/ 等）
4. WHEN 模块简化完成 THEN 系统 SHALL 将所有业务逻辑合并到 service.py
5. WHEN 模块简化完成 THEN 系统 SHALL 保持模块间的清晰边界

---

### 需求 5：更新架构文档

**用户故事**：作为开发者，我需要更新所有架构文档，以便反映简化后的架构。

#### 验收标准

1. WHEN 文档更新完成 THEN `.kiro/specs/ARCHITECTURE.md` SHALL 反映新架构
2. WHEN 文档更新完成 THEN 系统 SHALL 更新所有相关 README 文件
3. WHEN 文档更新完成 THEN 系统 SHALL 删除过时的架构图
4. WHEN 文档更新完成 THEN 系统 SHALL 更新 API 文档
5. WHEN 文档更新完成 THEN 系统 SHALL 创建迁移指南

---

## 简化后的架构概览

### 前端架构（简化后）

```
frontend/
├── src/
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx       # 主聊天窗口
│   │   │   ├── MessageList.tsx      # 消息列表
│   │   │   ├── MessageBubble.tsx    # 单条消息
│   │   │   ├── ChatInput.tsx        # 输入框
│   │   │   └── EmbeddedComponents/  # 嵌入式组件
│   │   └── ...
│   ├── hooks/
│   │   └── useChat.ts               # 简化的聊天 hook（使用 EventSource）
│   └── lib/
│       ├── api.ts                   # HTTP 客户端（发送消息）
│       └── sse-client.ts            # SSE 客户端（接收流式响应）
```

**通信流程**：
1. 用户输入消息 → HTTP POST `/api/v1/chat`
2. 后端返回 session_id
3. 前端建立 SSE 连接 → `EventSource('/api/v1/chat/stream?session_id=xxx')`
4. 后端通过 SSE 推送流式响应
5. 前端实时渲染消息

**移除**：
- ❌ `ai` 包依赖
- ❌ `frontend/src/app/api/chat/route.ts`（Next.js API route）
- ❌ Vercel AI SDK 相关代码
- ❌ WebSocket 相关代码（`useWebSocket.ts`, `websocket-client.ts`）

### AI Orchestrator 架构（简化后）

```
ai-orchestrator/
├── app/
│   ├── core/
│   │   ├── graph.py              # v3 LangGraph（2 节点）
│   │   ├── orchestrator.py       # 协调器
│   │   └── persist.py            # 持久化节点
│   ├── agents/
│   │   ├── creative_intelligence.py   # 合并后的创意智能
│   │   ├── ad_performance.py          # 广告性能分析
│   │   └── campaign_automation.py     # 广告投放自动化
│   └── modules/
│       ├── creative_intelligence/     # 3 个模块之一
│       │   ├── capability.py
│       │   ├── service.py            # 合并所有业务逻辑
│       │   └── models.py
│       ├── ad_performance/            # 3 个模块之二
│       │   ├── capability.py
│       │   ├── service.py
│       │   └── models.py
│       └── campaign_automation/       # 3 个模块之三
│           ├── capability.py
│           ├── service.py
│           └── models.py
```

**移除**：
- ❌ v2 架构所有代码
- ❌ `app/nodes/` 目录（除 persist.py）
- ❌ `app/core/routing.py`
- ❌ 每个模块的 fetchers/analyzers/managers 子目录
- ❌ ad_creative 和 market_insights 独立模块
- ❌ landing_page 独立模块

### 5 个独立模块（保持不变）

| 模块 | 职责 | 简化方式 |
|------|------|----------|
| ad_creative | 素材生成和分析 | 合并内部子目录到 service.py |
| market_insights | 竞品分析和策略建议 | 合并内部子目录到 service.py |
| ad_performance | 数据抓取和性能分析 | 合并内部子目录到 service.py |
| landing_page | 落地页生成和管理 | 合并内部子目录到 service.py |
| campaign_automation | 广告投放自动化 | 合并内部子目录到 service.py，保留 adapters/ |

---

## 技术决策：为什么选择 SSE 而不是 WebSocket？

### SSE (Server-Sent Events) 的优势

1. **更简单的架构**
   - 基于 HTTP，无需维护持久连接状态
   - 浏览器原生 `EventSource` API，无需额外库
   - 自动重连机制，无需手动实现

2. **单向通信足够**
   - 用户发送消息：HTTP POST（请求-响应）
   - AI 流式响应：SSE（服务器推送）
   - AAE 不需要客户端主动推送数据

3. **更好的基础设施兼容性**
   - 更容易通过 CDN、代理、负载均衡
   - 标准 HTTP 协议，防火墙友好
   - 更容易调试（可以用 curl 测试）

4. **AI Orchestrator 已支持**
   - 后端已有 SSE 端点实现
   - 前端只需使用标准 API

### WebSocket 的劣势（对于 AAE）

- ❌ 过度设计：不需要双向实时通信
- ❌ 复杂性：需要维护连接状态、心跳、重连
- ❌ 调试困难：需要专门工具
- ❌ 基础设施：某些代理/防火墙可能阻止

### 通信流程对比

**当前（WebSocket）**：
```
1. 建立 WebSocket 连接
2. 发送消息 → WebSocket
3. 接收响应 ← WebSocket
4. 维护连接（心跳、重连）
```

**简化后（SSE）**：
```
1. 发送消息 → HTTP POST /api/v1/chat
2. 获取 session_id
3. 建立 SSE 连接 → EventSource('/api/v1/chat/stream?session_id=xxx')
4. 接收流式响应 ← SSE
5. 浏览器自动处理重连
```

---

## 非功能性需求

### 性能

1. 系统 SHALL 在简化后减少启动时间至少 50%
2. 系统 SHALL 减少前端包大小至少 20%
3. 系统 SHALL 保持相同或更好的响应速度

### 可维护性

1. 系统 SHALL 减少总代码行数至少 40%
2. 系统 SHALL 减少文件数量至少 50%
3. 系统 SHALL 简化代码路径，便于调试

### 兼容性

1. 系统 SHALL 保持与现有 API 的向后兼容
2. 系统 SHALL 保持前端用户体验不变
3. 系统 SHALL 保持所有核心功能完整

---

## 待删除文件清单

### 前端

```
frontend/
├── src/
│   ├── app/api/chat/route.ts         # Next.js API route（不再需要）
│   ├── hooks/
│   │   └── useWebSocket.ts           # WebSocket hook（不再需要）
│   └── lib/
│       └── websocket-client.ts       # WebSocket 客户端（不再需要）
└── package.json                       # 移除 'ai' 依赖
```

### AI Orchestrator - v2 架构

```
ai-orchestrator/app/
├── core/
│   └── routing.py                    # v2 路由逻辑
├── nodes/                            # 整个目录（除 persist.py）
│   ├── router.py
│   ├── planner.py
│   ├── executor.py
│   ├── analyzer.py
│   ├── respond.py
│   └── ...
└── tools/                            # 如果仅用于 v2
```

### AI Orchestrator - 冗余模块

```
ai-orchestrator/app/modules/
├── ad_creative/                      # 合并到 creative_intelligence
├── market_insights/                  # 合并到 creative_intelligence
└── landing_page/                     # 合并到 creative_intelligence
```

### AI Orchestrator - 过度抽象

```
每个模块内：
├── fetchers/                         # 合并到 service.py
├── analyzers/                        # 合并到 service.py
├── managers/                         # 合并到 service.py
├── generators/                       # 合并到 service.py
├── optimizers/                       # 合并到 service.py
├── extractors/                       # 合并到 service.py
└── utils/                            # 只保留真正通用的工具
```

---

## 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 前端 WebSocket 实现不稳定 | 高 | 低 | 充分测试，参考现有实现 |
| 模块合并导致功能丢失 | 高 | 中 | 仔细审查，保留所有核心功能 |
| v2 删除导致回滚困难 | 中 | 低 | 使用 Git 分支，分阶段迁移 |
| 测试失败 | 中 | 中 | 更新测试用例，保持覆盖率 |
| 文档过时 | 低 | 高 | 同步更新所有文档 |

---

## 成功指标

### 代码简化

- 总代码行数减少 30%+
- 文件数量减少 50%+
- 保持 5 个独立模块，简化内部结构

### 性能提升

- 启动时间减少 50%+
- 前端包大小减少 20%+
- 响应速度保持或提升

### 可维护性

- 新开发者上手时间减少 50%
- Bug 修复时间减少 30%
- 代码审查时间减少 40%
