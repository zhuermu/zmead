# 需求文档 - AI Orchestrator 架构统一

## 简介（Introduction）

当前 AI Orchestrator 存在两套并行的 LangGraph 架构（v2 和 v3），导致代码冗余、维护困难、开发路径不清晰。本需求旨在统一架构，保留简化的 v3 架构，删除复杂的 v2 架构及相关冗余代码。

## 术语表（Glossary）

- **v2 架构**：基于多节点状态机的复杂架构（router → planner → executor → analyzer → respond → persist）
- **v3 架构**：基于 Gemini Function Calling 的简化架构（orchestrator → persist）
- **Sub-Agent**：通过 Function Calling 暴露给 Gemini 的功能模块
- **Orchestrator**：v3 架构的核心协调器，处理意图识别和 Agent 调用

---

## 需求（Requirements）

### 需求 1：删除 v2 架构相关代码

**用户故事**：作为开发者，我需要删除 v2 架构的冗余代码，以便减少维护负担和代码复杂度。

#### 验收标准

1. WHEN 架构统一完成 THEN 系统 SHALL 只保留 v3 架构的 LangGraph 实现
2. WHEN 删除 v2 代码 THEN 系统 SHALL 删除 `app/core/graph.py` 中的 v2 实现
3. WHEN 删除 v2 代码 THEN 系统 SHALL 删除 `app/core/routing.py` 中的 v2 路由逻辑
4. WHEN 删除 v2 代码 THEN 系统 SHALL 删除 `app/nodes/` 目录下的 v2 专用节点
5. WHEN 删除 v2 代码 THEN 系统 SHALL 删除 `app/tools/` 目录（如果仅用于 v2）

---

### 需求 2：统一 API 端点

**用户故事**：作为开发者，我需要统一 Chat API 端点，以便前端只需对接一个接口。

#### 验收标准

1. WHEN API 统一完成 THEN 系统 SHALL 将 `/api/v1/chat` 指向 v3 实现
2. WHEN API 统一完成 THEN 系统 SHALL 删除 `/api/v1/chat/v3` 端点（合并到主端点）
3. WHEN API 统一完成 THEN 系统 SHALL 保持与前端的接口兼容性
4. WHEN API 统一完成 THEN 系统 SHALL 支持 SSE 流式响应
5. WHEN API 统一完成 THEN 系统 SHALL 支持同步响应模式

---

### 需求 3：简化模块结构

**用户故事**：作为开发者，我需要简化功能模块的内部结构，以便更容易理解和维护。

#### 验收标准

1. WHEN 模块简化完成 THEN 每个模块 SHALL 只保留必要的文件（capability.py, models.py, service.py）
2. WHEN 模块简化完成 THEN 系统 SHALL 将分散的 fetchers/analyzers/managers 合并到 service.py
3. WHEN 模块简化完成 THEN 系统 SHALL 保留模块的核心功能不变
4. WHEN 模块简化完成 THEN 系统 SHALL 删除未使用的工具类文件
5. WHEN 模块简化完成 THEN 系统 SHALL 保持测试覆盖率

---

### 需求 4：更新启动流程

**用户故事**：作为开发者，我需要更新应用启动流程，以便只初始化 v3 架构。

#### 验收标准

1. WHEN 启动流程更新 THEN `app/main.py` SHALL 只编译 v3 LangGraph
2. WHEN 启动流程更新 THEN 系统 SHALL 删除 v2 graph 的初始化代码
3. WHEN 启动流程更新 THEN 系统 SHALL 保留 Agent 注册逻辑
4. WHEN 启动流程更新 THEN 系统 SHALL 保留 MCP Client 初始化
5. WHEN 启动流程更新 THEN 系统 SHALL 更新健康检查端点

---

### 需求 5：更新文档

**用户故事**：作为开发者，我需要更新架构文档，以便反映统一后的架构。

#### 验收标准

1. WHEN 文档更新完成 THEN README.md SHALL 只描述 v3 架构
2. WHEN 文档更新完成 THEN 系统 SHALL 删除 v2 相关的架构图和说明
3. WHEN 文档更新完成 THEN 系统 SHALL 更新 `.kiro/specs/ai-orchestrator/design.md`
4. WHEN 文档更新完成 THEN 系统 SHALL 保留 ARCHITECTURE_V3.md 作为主架构文档
5. WHEN 文档更新完成 THEN 系统 SHALL 更新 API 文档

---

## 待删除文件清单

### 核心文件（v2 专用）

```
app/core/graph.py          # v2 LangGraph 构建器（保留 v3 版本）
app/core/routing.py        # v2 条件路由逻辑
```

### 节点文件（v2 专用）

```
app/nodes/router.py        # v2 意图识别节点
app/nodes/planner.py       # v2 任务规划节点
app/nodes/executor.py      # v2 执行器节点
app/nodes/analyzer.py      # v2 分析器节点
app/nodes/respond.py       # v2 响应生成节点（v3 在 orchestrator 中处理）
app/nodes/confirmation.py  # v2 确认节点
app/nodes/*_stub.py        # 所有 stub 节点
```

### API 文件

```
app/api/chat.py            # v2 Chat API（合并到 chat_v3.py）
```

### 工具文件（如果仅用于 v2）

```
app/tools/                 # 整个目录（v3 使用 agents/）
```

---

## 待保留文件清单

### 核心文件

```
app/core/graph_v3.py       # v3 LangGraph（重命名为 graph.py）
app/core/orchestrator.py   # v3 协调器
app/core/state.py          # 状态定义（两版本共用）
app/core/config.py         # 配置
app/core/errors.py         # 错误处理
app/core/retry.py          # 重试逻辑
app/core/auth.py           # 认证
app/core/logging.py        # 日志
app/core/redis_client.py   # Redis 客户端
app/core/context.py        # 上下文管理
```

### Agent 文件

```
app/agents/                # 整个目录（v3 核心）
```

### 模块文件

```
app/modules/               # 保留，但简化内部结构
```

### API 文件

```
app/api/chat_v3.py         # 重命名为 chat.py
app/api/health.py          # 健康检查
app/api/campaign_automation.py  # 保留
```

### 服务文件

```
app/services/mcp_client.py     # MCP 客户端
app/services/gemini_client.py  # Gemini 客户端
app/services/gemini3_client.py # Gemini 3 客户端（如果存在）
```

---

## 非功能性需求

### 兼容性

1. 系统 SHALL 保持与前端 WebSocket/HTTP 接口的兼容性
2. 系统 SHALL 保持与 Web Platform MCP Server 的兼容性
3. 系统 SHALL 保持 SSE 流式响应格式不变

### 性能

1. 系统 SHALL 在架构统一后保持相同或更好的响应速度
2. 系统 SHALL 减少启动时间（只编译一个 graph）

### 可维护性

1. 系统 SHALL 减少代码行数至少 30%
2. 系统 SHALL 简化代码路径，便于调试

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 删除代码导致功能丢失 | 高 | 在删除前确认 v3 已实现所有必要功能 |
| 前端接口不兼容 | 高 | 保持 API 响应格式一致 |
| 测试失败 | 中 | 更新测试用例指向 v3 实现 |
| 文档过时 | 低 | 同步更新所有文档 |

