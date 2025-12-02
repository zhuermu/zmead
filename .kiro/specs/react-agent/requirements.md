# 需求文档 - AAE ReAct Agent 架构

## 简介（Introduction）

基于对当前架构的深入分析，我们决定采用**单一 Agent + ReAct 模式**重新设计 AI Orchestrator。新架构将利用 Gemini 的自主规划和编排能力，配合智能的 Human-in-the-Loop 机制，实现更简单、更强大的系统。

## 术语表（Glossary）

- **ReAct Agent**：结合推理（Reasoning）和行动（Acting）的 AI Agent 模式
- **Planner**：Agent 的规划组件，负责理解任务和制定执行计划
- **Tools/APIs**：Agent 可以调用的工具集合（MCP Tools）
- **Memory/State**：Agent 的记忆系统，记录执行历史和中间结果
- **Evaluator/Guardrails**：评估器，判断任务是否完成或需要人工介入
- **Human-in-the-Loop**：人工参与机制，在必要时请求用户确认或输入

---

## 需求（Requirements）

### 需求 1：实现单一 ReAct Agent

**用户故事**：作为开发者，我需要实现一个单一的 ReAct Agent，以便利用 Gemini 的自主规划能力。

#### 验收标准

1. WHEN Agent 接收用户请求 THEN 系统 SHALL 使用 Gemini 自动分解任务为多个步骤
2. WHEN Agent 执行任务 THEN 系统 SHALL 自动选择和调用正确的 MCP Tools
3. WHEN Agent 完成一个步骤 THEN 系统 SHALL 自动评估是否需要继续执行
4. WHEN Agent 遇到模糊情况 THEN 系统 SHALL 请求人工确认或输入
5. WHEN Agent 完成所有步骤 THEN 系统 SHALL 返回最终结果给用户

---

### 需求 2：智能 Human-in-the-Loop 机制

**用户故事**：作为用户，我希望系统在必要时请求我的确认，但不要在明确的任务中打扰我。

#### 验收标准

1. WHEN 任务明确且无风险 THEN 系统 SHALL 自动执行无需人工确认
2. WHEN 任务涉及花费或重要操作 THEN 系统 SHALL 请求人工确认
3. WHEN 任务参数模糊 THEN 系统 SHALL 提供选项让用户选择
4. WHEN 提供选项 THEN 系统 SHALL 包含预设选项、"其他"选项和"取消"选项
5. WHEN 用户选择"其他" THEN 系统 SHALL 允许用户自由输入

---

### 需求 3：移除 Sub-Agent 架构

**用户故事**：作为开发者，我需要移除 Sub-Agent 架构，以便简化系统复杂度。

#### 验收标准

1. WHEN 架构重构完成 THEN 系统 SHALL 只有一个 Main Agent
2. WHEN 架构重构完成 THEN 系统 SHALL 删除所有 Sub-Agent 代码
3. WHEN 架构重构完成 THEN 系统 SHALL 将 modules/ 转换为业务逻辑实现层
4. WHEN 架构重构完成 THEN 系统 SHALL 保持所有功能完整性
5. WHEN 架构重构完成 THEN 系统 SHALL 减少代码复杂度至少 50%

---

### 需求 4：统一 MCP Tools 接口

**用户故事**：作为开发者，我需要统一所有 MCP Tools 接口，以便 Agent 可以直接调用。

#### 验收标准

1. WHEN Tools 统一完成 THEN 系统 SHALL 提供 30-50 个 MCP Tools
2. WHEN Tools 统一完成 THEN 每个 Tool SHALL 有清晰的功能描述
3. WHEN Tools 统一完成 THEN 每个 Tool SHALL 有明确的参数定义
4. WHEN Tools 统一完成 THEN Agent SHALL 能够根据描述自动选择正确的 Tool
5. WHEN Tools 统一完成 THEN Tools SHALL 只负责数据交互，不包含 AI 逻辑

---

### 需求 5：前端 SSE 通信

**用户故事**：作为开发者，我需要使用 SSE 替代 WebSocket，以便简化前端通信。

#### 验收标准

1. WHEN 前端重构完成 THEN 系统 SHALL 使用 HTTP POST 发送消息
2. WHEN 前端重构完成 THEN 系统 SHALL 使用 SSE 接收流式响应
3. WHEN 前端重构完成 THEN 系统 SHALL 支持人工确认的交互式消息
4. WHEN 前端重构完成 THEN 系统 SHALL 渲染选项按钮（预设 + 其他 + 取消）
5. WHEN 前端重构完成 THEN 系统 SHALL 移除 Vercel AI SDK 依赖

---

## Human-in-the-Loop 触发规则

### 必须人工确认的场景

| 场景 | 原因 | 示例 |
|------|------|------|
| 创建广告 | 涉及花费 | "确认创建广告，预算 $100？" |
| 修改预算 | 涉及花费 | "确认将预算从 $50 增加到 $100？" |
| 暂停/删除广告 | 影响投放 | "确认暂停广告 Campaign-123？" |
| 大额充值 | 涉及支付 | "确认充值 $500？" |

### 建议人工选择的场景

| 场景 | 原因 | 示例 |
|------|------|------|
| 素材风格模糊 | 用户偏好 | "请选择素材风格：现代/活力/奢华" |
| 目标受众不明确 | 需要细化 | "请选择目标受众：年轻女性/中年男性/..." |
| 多个可行方案 | 需要决策 | "有 3 个优化建议，请选择" |

### 无需人工确认的场景

| 场景 | 原因 | 示例 |
|------|------|------|
| 查询数据 | 只读操作 | "我的广告表现如何？" |
| 分析性能 | 只读操作 | "分析这个广告" |
| 生成报表 | 只读操作 | "生成报表" |
| 获取建议 | 只读操作 | "给我优化建议" |

---

## 非功能性需求

### 性能

1. 系统 SHALL 在重构后减少启动时间至少 60%
2. 系统 SHALL 减少代码复杂度至少 50%
3. 系统 SHALL 保持相同或更好的响应速度

### 可维护性

1. 系统 SHALL 减少总代码行数至少 50%
2. 系统 SHALL 简化架构，只有一个 Agent
3. 系统 SHALL 提供清晰的 Tool 文档

### 用户体验

1. 系统 SHALL 在明确任务时自动执行
2. 系统 SHALL 在模糊任务时智能请求确认
3. 系统 SHALL 提供友好的选项界面

---

## 成功指标

### 架构简化

- 从 5 个 Sub-Agents 减少到 1 个 Main Agent
- 代码行数减少 50%+
- 文件数量减少 60%+

### 用户体验

- 明确任务的自动执行率 > 80%
- 人工确认的响应时间 < 5 秒
- 用户满意度提升

### 性能提升

- 启动时间减少 60%+
- 响应速度保持或提升
- 内存使用减少 40%+
