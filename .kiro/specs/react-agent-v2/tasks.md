# 实施计划 - AAE ReAct Agent v2

## 任务清单

- [x] 1. 实现 3 类 Tools 架构
  - 支持 LangChain 内置、Agent 自定义、MCP Server 三类工具
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 1.1 设计 Tools 接口规范
  - 定义 3 类 Tools 的统一接口
  - 定义 Tool 的元数据格式（name, description, parameters）
  - 创建 Tool 基类
  - _Requirements: 1.4_

- [x] 1.2 实现 Agent Custom Tools 注册机制
  - 创建 `ai-orchestrator/app/tools/registry.py`
  - 实现 Tool 注册和查找
  - 支持 Tool 的动态注册
  - _Requirements: 1.2, 1.5_

- [x] 1.3 实现 Creative Tools
  - 创建 `ai-orchestrator/app/tools/creative_tools.py`
  - 实现 `generate_image_tool`（调用 Gemini Imagen）
  - 实现 `generate_video_tool`（调用 Gemini Veo）
  - 实现 `analyze_creative_tool`（调用 Gemini Vision）
  - 实现 `extract_product_info_tool`（调用 Gemini）
  - _Requirements: 1.2_

- [x] 1.4 实现 Performance Tools
  - 创建 `ai-orchestrator/app/tools/performance_tools.py`
  - 实现 `analyze_performance_tool`（调用 Gemini）
  - 实现 `detect_anomaly_tool`（调用 Gemini）
  - 实现 `generate_recommendations_tool`（调用 Gemini）
  - _Requirements: 1.2_

- [x] 1.5 实现 Campaign Tools
  - 创建 `ai-orchestrator/app/tools/campaign_tools.py`
  - 实现 `optimize_budget_tool`（调用 Gemini）
  - 实现 `generate_ad_copy_tool`（调用 Gemini）
  - 实现 `suggest_targeting_tool`（调用 Gemini）
  - _Requirements: 1.2_

- [x] 1.6 实现 Landing Page Tools
  - 创建 `ai-orchestrator/app/tools/landing_page_tools.py`
  - 实现 `generate_page_content_tool`（调用 Gemini）
  - 实现 `translate_content_tool`（调用 Gemini）
  - 实现 `optimize_copy_tool`（调用 Gemini）
  - _Requirements: 1.2_

- [x] 1.7 实现 Market Tools
  - 创建 `ai-orchestrator/app/tools/market_tools.py`
  - 实现 `analyze_competitor_tool`（调用 Gemini）
  - 实现 `analyze_trends_tool`（调用 Gemini）
  - 实现 `generate_strategy_tool`（调用 Gemini）
  - _Requirements: 1.2_

- [x] 1.8 集成 LangChain 内置 Tools
  - 集成 `google_search`
  - 集成 `calculator`
  - 集成其他需要的 LangChain Tools
  - _Requirements: 1.1_

- [x] 1.9 统一 MCP Server Tools
  - 审查现有 Backend MCP Tools
  - 确保 Tools 只负责数据交互
  - 移除 Tools 中的 AI 逻辑
  - 统一 Tool 接口和描述
  - _Requirements: 1.3, 1.5_

- [ ]* 1.10 测试 Tools 集成
  - 测试每个 Agent Custom Tool
  - 测试 LangChain Tools 集成
  - 测试 MCP Server Tools 调用
  - _Requirements: 1.5_

- [x] 2. 实现 ReAct Agent 核心
  - 实现单一 Agent 的 ReAct 循环
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 2.1 创建 ReActAgent 类
  - 创建 `ai-orchestrator/app/core/react_agent.py`
  - 定义 Agent 主循环逻辑
  - 实现状态管理
  - _Requirements: 4.1_

- [x] 2.2 实现 Planner 组件
  - 使用 Gemini 理解用户意图
  - 使用 Gemini 制定执行计划
  - 使用 Gemini 选择需要的 Tools
  - _Requirements: 4.1, 4.2_

- [x] 2.3 实现 Memory 组件
  - 使用 Redis 存储对话历史
  - 使用 LangGraph State 管理执行状态
  - 实现状态持久化
  - _Requirements: 4.1_

- [x] 2.4 实现 Tool 执行逻辑
  - 实现 Tool 调用
  - 处理 Tool 执行结果
  - 处理 Tool 执行错误
  - _Requirements: 4.2_

- [ ]* 2.5 测试 ReAct Agent 核心
  - 测试主循环逻辑
  - 测试 Planner
  - 测试 Memory
  - 测试 Tool 执行
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 3. 实现 Human-in-the-Loop
  - 实现智能的人工确认机制
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 3.1 实现 Evaluator 组件
  - 创建 `ai-orchestrator/app/core/evaluator.py`
  - 实现判断是否需要人工确认的逻辑
  - 定义需要确认的操作列表
  - 实现参数模糊度检测
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 3.2 实现 HumanInLoopHandler
  - 创建 `ai-orchestrator/app/core/human_in_loop.py`
  - 实现确认请求生成
  - 实现选��请求生成（预设 + 其他 + 取消）
  - 实现输入请求生成
  - _Requirements: 5.3, 5.4, 5.5_

- [x] 3.3 集成到 ReAct 循环
  - 在 Planner 后添加 Evaluator 检查
  - 实现等待用户输入的状态
  - 实现用户输入后继续执行
  - _Requirements: 5.1, 5.2_

- [ ]* 3.4 测试 Human-in-the-Loop
  - 测试确认请求生成
  - 测试选项生成
  - 测试用户输入处理
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 4. 前端 SSE 实现
  - 移除 AI SDK，使用 SSE 通信
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 4.1 创建 useChat hook（SSE 版本）
  - 创建 `frontend/src/hooks/useChat.ts`
  - 使用 EventSource API 接收流式响应
  - 使用 fetch API 发送消息
  - 处理连接错误和重连
  - _Requirements: 7.1, 7.2_

- [x] 4.2 实现 UserInputPrompt 组件
  - 创建 `frontend/src/components/chat/UserInputPrompt.tsx`
  - 渲染选项按钮（预设 + 其他 + 取消）
  - 处理用户选择
  - 处理自定义输入
  - _Requirements: 7.3, 7.4_

- [x] 4.3 更新 ChatWindow 组件
  - 使用新的 useChat hook
  - 集成 UserInputPrompt 组件
  - 移除 AI SDK 相关代码
  - 保持 UI 和用户体验
  - _Requirements: 7.2, 7.3_

- [x] 4.4 删除前端 AI 框架依赖
  - 从 `package.json` 移除 `ai` 包
  - 删除 `frontend/src/app/api/chat/route.ts`
  - 删除 WebSocket 相关代码
  - 运行 `npm install`
  - _Requirements: 7.5_

- [x] 4.5 测试前端聊天功能
  - 测试消息发送和接收
  - 测试流式响应
  - 测试选项交互
  - 测试错误处理
  - _Requirements: 7.2, 7.3, 7.4_

- [x] 5. 删除 Sub-Agent 架构
  - 移除所有 Sub-Agent 代码
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 5.1 删除 Sub-Agent 相关代码
  - 删除 `ai-orchestrator/app/agents/` 目录（如果存在）
  - 删除 Sub-Agent 注册逻辑
  - 删除 Sub-Agent 路由逻辑
  - _Requirements: 3.1, 3.2_

- [x] 5.2 重构 modules/ 为实现层
  - 移除 `capability.py`（不再是 Agent）
  - 简化 `service.py`（只保留 AI 能力实现）
  - 删除所有子目录（fetchers/, analyzers/, managers/ 等）
  - 合并到 `service.py`
  - _Requirements: 3.3, 3.4_

- [x] 5.3 更新 modules/ 调用方式
  - modules/ 的方法被 Agent Custom Tools 调用
  - 不再通过 capability.py 调用
  - _Requirements: 3.3_

- [ ]* 5.4 更新测试
  - 更新测试用例
  - 删除 Sub-Agent 相关测试
  - 确保所有测试通过
  - _Requirements: 3.4, 3.5_

- [x] 6. 完成 v2 架构迁移
  - 删除 v2 架构代码
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 6.1 删除 v2 架构代码
  - 删除 `ai-orchestrator/app/core/routing.py`
  - 删除 `ai-orchestrator/app/nodes/` 目录
  - 删除 `app/tools/` 目录（如果仅用于 v2）
  - _Requirements: 6.1, 6.2_

- [x] 6.2 更新 main.py
  - 只初始化 ReAct Agent
  - 删除 v2 graph 初始化
  - 更新导入语句
  - _Requirements: 6.3, 6.4_

- [x] 6.3 删除 v2 相关测试
  - 删除 v2 专用测试文件
  - _Requirements: 6.5_

- [ ]* 6.4 运行测试验证
  - 运行所有测试
  - 测量启动时间改善
  - _Requirements: 6.4_

- [x] 7. Checkpoint - 验证核心功能
  - 确保所有测试通过，询问用户是否有问题

- [x] 8. 更新架构文档
  - 更新所有文档反映新架构
  - _Requirements: 需求 7（如果有文档需求）_

- [x] 8.1 更新主架构文档
  - 更新 `.kiro/specs/ARCHITECTURE.md`
  - 反映 ReAct Agent 架构
  - 反映 3 类 Tools
  - 说明 Human-in-the-Loop 机制
  - 添加 Skills 动态加载的未来规划

- [x] 8.2 更新 AI Orchestrator README
  - 更新 `ai-orchestrator/README.md`
  - 描述 ReAct Agent 架构
  - 描述 3 类 Tools
  - 添加开发指南

- [x] 8.3 创建迁移指南
  - 创建 `MIGRATION_TO_REACT.md`
  - 说明从 Sub-Agents 迁移到 ReAct Agent 的步骤
  - 说明破坏性变更
  - 提供示例代码

- [x] 9. 最终验证
  - 确保整个系统正常工作

- [x] 9.1 运行所有测试
  - 运行 AI Orchestrator 测试
  - 运行 Backend 测试
  - 运行前端测试（如果有）
  - 确保所有测试通过

- [x] 9.2 手动测试完整流程
  - 测试明确任务（自动执行）
  - 测试模糊任务（请求选择）
  - 测试重要操作（请求确认）
  - 测试复杂任务（多次人工介入）

- [x] 9.3 性能测试
  - 测量启动时间
  - 测量响应延迟
  - 测量 Token 使用
  - 验证性能指标达标

- [x] 10. Final Checkpoint - 确保所有测试通过
  - 确保所有测试通过，询问用户是否有问题
