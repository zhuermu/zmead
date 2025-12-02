# 需求文档 - AAE ReAct Agent 架构 v2（Skills 动态加载）

## 简介（Introduction）

基于对 Tools 管理和 LLM context 限制的深入分析，我们采用 **ReAct Agent + Skills 动态加载** 架构。新架构将：
- 实现单一 ReAct Agent
- 支持 3 类 Tools（LangChain 内置 + Agent 自定义 + MCP Server）
- 使用 Skills 机制动态加载 Tools
- 实现智能 Human-in-the-Loop
- 避免 LLM context 过大

## 术语表（Glossary）

- **ReAct Agent**：结合推理和行动的 AI Agent 模式
- **Skill**：一组相关 Tools 的集合（如 Creative Skill 包含素材相关的所有 Tools）
- **LangChain Tools**：LangChain 框架内置的通用工具
- **Agent Custom Tools**：Agent 自定义的工具，可以调用大模型
- **MCP Server Tools**：Backend 通过 MCP 协议提供的工具
- **Dynamic Loading**：根据用户意图动态加载相关 Skills 的 Tools

---

## 需求（Requirements）

### 需求 1：实现 3 类 Tools 架构

**用户故事**：作为开发者，我需要支持 3 类 Tools，以便充分利用现有能力和保持架构清晰。

#### 验收标准

1. WHEN Tools 架构实现完成 THEN 系统 SHALL 支持 LangChain 内置 Tools
2. WHEN Tools 架构实现完成 THEN 系统 SHALL 支持 Agent 自定义 Tools（可调用大模型）
3. WHEN Tools 架构实现完成 THEN 系统 SHALL 支持 MCP Server Tools（Backend API）
4. WHEN Tools 架构实现完成 THEN 每类 Tools SHALL 有清晰的职责划分
5. WHEN Tools 架构实现完成 THEN Agent SHALL 能够调用所有 3 类 Tools

---

### 需求 2：（未来优化）Skills 动态加载机制

**用户故事**：作为开发者，当 Tools 数量过多时，我需要实现 Skills 动态加载，以便避免 LLM context 过大。

**注意**：此需求为未来优化，初期实现时可以加载所有 Tools。

#### 验收标准

1. WHEN Skills 机制实现 THEN 系统 SHALL 将 Tools 分组为 5 个 Skills
2. WHEN 用户发送消息 THEN 系统 SHALL 识别需要的 Skills
3. WHEN Skills 识别完成 THEN 系统 SHALL 只加载相关 Skills 的 Tools
4. WHEN Skills 加载完成 THEN 系统 SHALL 使用加载的 Tools 执行任务
5. WHEN 任务执行中需要新 Skill THEN 系统 SHALL 动态加载新 Skill 的 Tools

---

### 需求 3：移除 Sub-Agent 架构

**用户故事**：作为开发者，我需要移除 Sub-Agent 架构，以便简化系统。

#### 验收标准

1. WHEN 架构重构完成 THEN 系统 SHALL 只有一个 Main Agent
2. WHEN 架构重构完成 THEN 系统 SHALL 删除所有 Sub-Agent 代码
3. WHEN 架构重构完成 THEN 系统 SHALL 将 modules/ 转换为业务逻辑实现层
4. WHEN 架构重构完成 THEN 系统 SHALL 保持所有功能完整性
5. WHEN 架构重构完成 THEN 系统 SHALL 减少代码复杂度至少 50%

---

### 需求 4：实现单一 ReAct Agent

**用户故事**：作为开发者，我需要实现单一 ReAct Agent，以便利用 Gemini 的自主规划能力。

#### 验收标准

1. WHEN Agent 接收用户请求 THEN 系统 SHALL 使用 Gemini 自动分解任务
2. WHEN Agent 执行任务 THEN 系统 SHALL 自动选择和调用 Tools
3. WHEN Agent 完成步骤 THEN 系统 SHALL 自动评估是否继续
4. WHEN Agent 遇到模糊情况 THEN 系统 SHALL 请求人工确认
5. WHEN Agent 完成任务 THEN 系统 SHALL 返回最终结果

---

### 需求 5：智能 Human-in-the-Loop

**用户故事**：作为用户，我希望系统在必要时请求确认，但不要在明确任务中打扰我。

#### 验收标准

1. WHEN 任务明确且无风险 THEN 系统 SHALL 自动执行
2. WHEN 任务涉及花费或重要操作 THEN 系统 SHALL 请求确认
3. WHEN 任务参数模糊 THEN 系统 SHALL 提供选项让用户选择
4. WHEN 提供选项 THEN 系统 SHALL 包含预设选项、"其他"选项和"取消"选项
5. WHEN 用户选择"其他" THEN 系统 SHALL 允许自由输入

---

### 需求 6：完成 v2 架构迁移

**用户故事**：作为开发者，我需要删除 v2 架构代码，以便减少维护负担。

#### 验收标准

1. WHEN v2 迁移完成 THEN 系统 SHALL 删除 `app/nodes/` 目录
2. WHEN v2 迁移完成 THEN 系统 SHALL 删除 `app/core/routing.py`
3. WHEN v2 迁移完成 THEN 系统 SHALL 统一 API 端点
4. WHEN v2 迁移完成 THEN 系统 SHALL 减少启动时间至少 40%
5. WHEN v2 迁移完成 THEN 系统 SHALL 删除 v2 相关测试

---

### 需求 7：前端 SSE 通信

**用户故事**：作为开发者，我需要使用 SSE 替代 WebSocket，以便简化通信。

#### 验收标准

1. WHEN 前端重构完成 THEN 系统 SHALL 使用 HTTP POST 发送消息
2. WHEN 前端重构完成 THEN 系统 SHALL 使用 SSE 接收流式响应
3. WHEN 前端重构完成 THEN 系统 SHALL 支持交互式消息（选项按钮）
4. WHEN 前端重构完成 THEN 系统 SHALL 渲染选项（预设 + 其他 + 取消）
5. WHEN 前端重构完成 THEN 系统 SHALL 移除 Vercel AI SDK 依赖

---

## Skills 定义

### Creative Skill（素材创意）

**触发关键词**：素材、图片、视频、创意、设计

**包含的 Tools**：
- LangChain Tools: 无
- Agent Custom Tools:
  - `generate_image_tool` - 生成图片（调用 Gemini Imagen）
  - `generate_video_tool` - 生成视频（调用 Gemini Veo）
  - `analyze_creative_tool` - 分析素材（调用 Gemini Vision）
  - `extract_product_info_tool` - 提取产品信息（调用 Gemini）
- MCP Server Tools:
  - `save_creative` - 保存素材
  - `get_creative` - 获取素材
  - `list_creatives` - 列出素材

---

### Performance Skill（性能分析）

**触发关键词**：表现、数据、分析、报表、ROAS、CTR

**包含的 Tools**：
- LangChain Tools:
  - `calculator` - 计算指标
- Agent Custom Tools:
  - `analyze_performance_tool` - AI 分析性能（调用 Gemini）
  - `detect_anomaly_tool` - 检测异常（调用 Gemini）
  - `generate_recommendations_tool` - 生成建议（调用 Gemini）
- MCP Server Tools:
  - `fetch_ad_data` - 抓取广告数据
  - `get_historical_data` - 获取历史数据
  - `save_report` - 保存报表

---

### Campaign Skill（广告投放）

**触发关键词**：广告、投放、预算、Campaign、Adset

**包含的 Tools**：
- LangChain Tools: 无
- Agent Custom Tools:
  - `optimize_budget_tool` - 优化预算建议（调用 Gemini）
  - `generate_ad_copy_tool` - 生成广告文案（调用 Gemini）
  - `suggest_targeting_tool` - 建议受众定向（调用 Gemini）
- MCP Server Tools:
  - `create_campaign` - 创建广告
  - `update_campaign` - 更新广告
  - `pause_campaign` - 暂停广告
  - `get_campaign` - 获取广告信息

---

### Landing Page Skill（落地页）

**触发关键词**：落地页、页面、网站、Landing Page

**包含的 Tools**：
- LangChain Tools: 无
- Agent Custom Tools:
  - `generate_page_content_tool` - 生成页面内容（调用 Gemini）
  - `translate_content_tool` - 翻译内容（调用 Gemini）
  - `optimize_copy_tool` - 优化文案（调用 Gemini）
- MCP Server Tools:
  - `save_landing_page` - 保存落地页
  - `get_landing_page` - 获取落地页
  - `upload_to_s3` - 上传文件
  - `create_ab_test_record` - 创建 A/B 测试

---

### Market Skill（市场洞察）

**触发关键词**：竞品、市场、趋势、策略

**包含的 Tools**：
- LangChain Tools:
  - `google_search` - 搜索竞品信息
- Agent Custom Tools:
  - `analyze_competitor_tool` - 分析竞品（调用 Gemini）
  - `analyze_trends_tool` - 分析趋势（调用 Gemini）
  - `generate_strategy_tool` - 生成策略（调用 Gemini）
- MCP Server Tools:
  - `fetch_competitor_data` - 抓取竞品数据
  - `fetch_market_data` - 获取市场数据
  - `save_analysis` - 保存分析结果

---

## 非功能性需求

### 性能

1. 系统 SHALL 通过 Skills 动态加载减少 LLM context 大小至少 60%
2. 系统 SHALL 在 Skills 识别阶段响应时间 < 500ms
3. 系统 SHALL 支持最多同时加载 3 个 Skills

### 可维护性

1. 系统 SHALL 提供清晰的 Skill 定义和 Tools 映射
2. 系统 SHALL 支持轻松添加新 Skill
3. 系统 SHALL 支持轻松添加新 Tool 到现有 Skill

### 可扩展性

1. 系统 SHALL 支持动态注册新 Skill
2. 系统 SHALL 支持 Skill 之间的依赖关系
3. 系统 SHALL 支持 Skill 的热加载

---

## 成功指标

### Context 优化

- ✅ LLM context 大小减少 60%+
- ✅ 平均每次只加载 10-15 个 Tools（而不是 50 个）
- ✅ Skills 识别准确率 > 95%

### 性能提升

- ✅ 响应速度提升 30%+
- ✅ Token 使用减少 40%+
- ✅ 成本降低 40%+
