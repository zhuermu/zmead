# 实施计划 - AAE 架构全面简化

## 任务清单

- [ ] 1. 前端 SSE 迁移
  - 移除 Vercel AI SDK，使用原生 EventSource API
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [ ] 1.1 创建新的 useChat hook（SSE 版本）
  - 实现 `frontend/src/hooks/useChat.ts`
  - 使用 EventSource API 接收流式响应
  - 使用 fetch API 发送消息
  - 处理连接错误和重连
  - _Requirements: 1.2, 1.3, 1.4_

- [ ] 1.2 更新 ChatWindow 组件
  - 使用新的 useChat hook
  - 移除 AI SDK 相关代码
  - 保持 UI 和用户体验不变
  - _Requirements: 1.6_

- [ ] 1.3 删除前端 AI 框架依赖
  - 从 `package.json` 移除 `ai` 包
  - 删除 `frontend/src/app/api/chat/route.ts`
  - 删除 WebSocket 相关代码（`useWebSocket.ts`, `websocket-client.ts`）
  - 运行 `npm install` 更新依赖
  - _Requirements: 1.1, 1.5_

- [ ]* 1.4 测试前端聊天功能
  - 测试消息发送和接收
  - 测试流式响应
  - 测试嵌入式组件渲染
  - 测试错误处理
  - _Requirements: 1.6_

- [ ] 2. AI Orchestrator v3 迁移
  - 删除 v2 架构，统一为 v3
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 2.1 验证 v3 功能完整性
  - 运行现有测试确保 v3 正常工作
  - 测试与前端的集成
  - 测试与 Backend MCP Server 的通信
  - _Requirements: 2.1_

- [ ] 2.2 删除 v2 架构代码
  - 删除 `ai-orchestrator/app/core/routing.py`
  - 删除 `ai-orchestrator/app/nodes/` 目录（除 persist.py）
  - 移动 `app/nodes/persist.py` → `app/core/persist.py`
  - 删除 `app/tools/` 目录（如果存在）
  - _Requirements: 2.2, 2.3_

- [ ] 2.3 更新 main.py 启动流程
  - 只初始化 v3 LangGraph
  - 删除 v2 graph 初始化代码
  - 更新导入语句
  - _Requirements: 2.1, 2.5_

- [ ] 2.4 删除 v2 相关测试
  - 删除 `tests/test_intent_recognition_property.py`
  - 删除 `tests/test_execution_order_property.py`
  - 删除其他 v2 专用测试
  - _Requirements: 2.1_

- [ ] 2.5 运行测试验证 v3 迁移
  - 运行所有测试确保通过
  - 测量启动时间改善
  - _Requirements: 2.5_

- [ ] 3. 简化 Ad Creative Module
  - 合并内部子目录到 service.py
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.2, 4.3, 4.4_

- [ ] 3.1 创建新的 service.py
  - 创建 `ai-orchestrator/app/modules/ad_creative/service.py`
  - 定义 `AdCreativeService` 类
  - _Requirements: 3.2, 4.2_

- [ ] 3.2 合并素材生成逻辑
  - 将 `generators/image_generator.py` 的逻辑合并到 service.py
  - 将 `generators/variant_generator.py` 的逻辑合并到 service.py
  - 实现 `generate_image()`, `generate_video()`, `generate_variants()` 方法
  - 确保直接调用 Gemini API，不通过 MCP Tools
  - _Requirements: 3.2, 3.5_

- [ ] 3.3 合并素材分析逻辑
  - 将 `analyzers/scoring_engine.py` 的逻辑合并到 service.py
  - 将 `analyzers/competitor_analyzer.py` 的逻辑合并到 service.py
  - 实现 `analyze_creative()`, `score_creative()` 方法
  - 确保使用 Gemini Vision 进行分析
  - _Requirements: 3.2, 3.5_

- [ ] 3.4 合并素材管理逻辑
  - 将 `managers/creative_manager.py` 的逻辑合并到 service.py
  - 将 `managers/upload_manager.py` 的逻辑合并到 service.py
  - 实现素材 CRUD 操作（通过 MCP Tools）
  - _Requirements: 3.2, 3.5_

- [ ] 3.5 合并产品信息提取逻辑
  - 将 `extractors/amazon_extractor.py` 的逻辑合并到 service.py
  - 将 `extractors/shopify_extractor.py` 的逻辑合并到 service.py
  - 实现 `_extract_product_info()` 方法
  - 确保使用 Gemini 理解网页内容
  - _Requirements: 3.2, 3.5_

- [ ] 3.6 合并工具类
  - 将 `utils/` 下的文件合并到 `utils.py`
  - 只保留真正通用的工具函数
  - _Requirements: 3.2, 3.4_

- [ ] 3.7 更新 capability.py
  - 更新 `AdCreativeAgent` 使用新的 service
  - 明确 AI 能力和 MCP Tools 的划分
  - _Requirements: 4.2, 4.4_

- [ ] 3.8 删除旧的子目录
  - 删除 `generators/`, `analyzers/`, `managers/`, `extractors/`, `utils/`
  - _Requirements: 3.2, 3.4, 4.3_

- [ ]* 3.9 更新测试
  - 更新测试用例指向新的 service.py
  - 确保所有测试通过
  - _Requirements: 3.5_

- [ ] 4. 简化 Market Insights Module
  - 合并内部子目录到 service.py
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.2, 4.3, 4.4_

- [ ] 4.1 创建新的 service.py
  - 创建 `ai-orchestrator/app/modules/market_insights/service.py`
  - 定义 `MarketInsightsService` 类
  - _Requirements: 3.2, 4.2_

- [ ] 4.2 合并竞品分析逻辑
  - 将 `analyzers/competitor_analyzer.py` 的逻辑合并到 service.py
  - 将 `analyzers/strategy_generator.py` 的逻辑合并到 service.py
  - 将 `analyzers/creative_analyzer.py` 的逻辑合并到 service.py
  - 确保使用 Gemini 进行分析
  - _Requirements: 3.2, 3.5_

- [ ] 4.3 合并数据抓取逻辑
  - 将 `fetchers/trends_fetcher.py` 的逻辑合并到 service.py
  - 将 `fetchers/tiktok_fetcher.py` 的逻辑合并到 service.py
  - 实现通过 MCP Tools 获取数据
  - _Requirements: 3.2, 3.5_

- [ ] 4.4 合并性能追踪逻辑
  - 将 `trackers/performance_tracker.py` 的逻辑合并到 service.py
  - _Requirements: 3.2, 3.5_

- [ ] 4.5 合并工具类和更新 capability
  - 合并 `utils/` 到 `utils.py`
  - 更新 `capability.py`
  - 删除旧的子目录
  - _Requirements: 3.2, 3.4, 4.2, 4.3, 4.4_

- [ ]* 4.6 更新测试
  - 更新测试用例
  - 确保所有测试通过
  - _Requirements: 3.5_

- [ ] 5. 简化 Ad Performance Module
  - 合并内部子目录到 service.py
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.2, 4.3, 4.4_

- [ ] 5.1 创建新的 service.py
  - 创建 `ai-orchestrator/app/modules/ad_performance/service.py`
  - 定义 `AdPerformanceService` 类
  - _Requirements: 3.2, 4.2_

- [ ] 5.2 合并数据抓取逻辑
  - 将 `fetchers/meta_fetcher.py` 的逻辑合并到 service.py
  - 将 `fetchers/tiktok_fetcher.py` 的逻辑合并到 service.py
  - 将 `fetchers/google_fetcher.py` 的逻辑合并到 service.py
  - 实现通过 MCP Tools 抓取数据
  - _Requirements: 3.2, 3.5_

- [ ] 5.3 合并性能分析逻辑
  - 将 `analyzers/performance_analyzer.py` 的逻辑合并到 service.py
  - 将 `analyzers/ai_analyzer.py` 的逻辑合并到 service.py
  - 将 `analyzers/anomaly_detector.py` 的逻辑合并到 service.py
  - 将 `analyzers/recommendation_engine.py` 的逻辑合并到 service.py
  - 确保使用 Gemini 进行 AI 分析
  - _Requirements: 3.2, 3.5_

- [ ] 5.4 合并报表生成逻辑
  - 将 `exporters/csv_exporter.py` 的逻辑合并到 service.py
  - 将 `exporters/pdf_exporter.py` 的逻辑合并到 service.py
  - _Requirements: 3.2, 3.5_

- [ ] 5.5 合并工具类和更新 capability
  - 合并 `utils/` 到 `utils.py`
  - 更新 `capability.py`
  - 删除旧的子目录
  - _Requirements: 3.2, 3.4, 4.2, 4.3, 4.4_

- [ ]* 5.6 更新测试
  - 更新测试用例
  - 确保所有测试通过
  - _Requirements: 3.5_

- [ ] 6. 简化 Landing Page Module
  - 合并内部子目录到 service.py
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.2, 4.3, 4.4_

- [ ] 6.1 创建新的 service.py
  - 创建 `ai-orchestrator/app/modules/landing_page/service.py`
  - 定义 `LandingPageService` 类
  - _Requirements: 3.2, 4.2_

- [ ] 6.2 合并页面生成逻辑
  - 将 `generators/page_generator.py` 的逻辑合并到 service.py
  - 实现 `generate_page()` 方法
  - 确保使用 Gemini 生成页面内容
  - _Requirements: 3.2, 3.5_

- [ ] 6.3 合并页面管理逻辑
  - 将 `managers/update_handler.py` 的逻辑合并到 service.py
  - 将 `managers/export_manager.py` 的逻辑合并到 service.py
  - 将 `managers/hosting_manager.py` 的逻辑合并到 service.py
  - 将 `managers/ab_test_manager.py` 的逻辑合并到 service.py
  - _Requirements: 3.2, 3.5_

- [ ] 6.4 合并页面优化逻辑
  - 将 `optimizers/copy_optimizer.py` 的逻辑合并到 service.py
  - 将 `optimizers/translator.py` 的逻辑合并到 service.py
  - 确保使用 Gemini 进行优化和翻译
  - _Requirements: 3.2, 3.5_

- [ ] 6.5 合并追踪逻辑
  - 将 `tracking/event_tracker.py` 的逻辑合并到 service.py
  - 将 `tracking/pixel_injector.py` 的逻辑合并到 service.py
  - 将 `tracking/dual_tracker.py` 的逻辑合并到 service.py
  - _Requirements: 3.2, 3.5_

- [ ] 6.6 合并产品信息提取逻辑
  - 将 `extractors/` 的逻辑合并到 service.py
  - 确保使用 Gemini 理解网页内容
  - _Requirements: 3.2, 3.5_

- [ ] 6.7 合并工具类和更新 capability
  - 合并 `utils/` 到 `utils.py`
  - 更新 `capability.py`
  - 删除旧的子目录
  - _Requirements: 3.2, 3.4, 4.2, 4.3, 4.4_

- [ ]* 6.8 更新测试
  - 更新测试用例
  - 确保所有测试通过
  - _Requirements: 3.5_

- [ ] 7. 简化 Campaign Automation Module
  - 合并内部子目录到 service.py（保留 adapters/）
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.2, 4.3, 4.4_

- [ ] 7.1 创建新的 service.py
  - 创建 `ai-orchestrator/app/modules/campaign_automation/service.py`
  - 定义 `CampaignAutomationService` 类
  - _Requirements: 3.2, 4.2_

- [ ] 7.2 合并广告管理逻辑
  - 将 `managers/campaign_manager.py` 的逻辑合并到 service.py
  - 将 `managers/ab_test_manager.py` 的逻辑合并到 service.py
  - 实现通过 MCP Tools 管理广告
  - _Requirements: 3.2, 3.5_

- [ ] 7.3 合并预算优化逻辑
  - 将 `optimizers/budget_optimizer.py` 的逻辑合并到 service.py
  - 确保使用 Gemini 进行优化建议
  - _Requirements: 3.2, 3.5_

- [ ] 7.4 合并规则引擎逻辑
  - 将 `engines/rule_engine.py` 的逻辑合并到 service.py
  - 实现通过 MCP Tools 应用规则
  - _Requirements: 3.2, 3.5_

- [ ] 7.5 合并 AI 客户端逻辑
  - 将 `clients/ai_client.py` 的逻辑合并到 service.py
  - _Requirements: 3.2, 3.5_

- [ ] 7.6 合并工具类和更新 capability
  - 合并 `utils/` 到 `utils.py`
  - 更新 `capability.py`
  - **保留** `adapters/` 目录
  - 删除其他旧的子目录
  - _Requirements: 3.2, 3.4, 4.2, 4.3, 4.4_

- [ ]* 7.7 更新测试
  - 更新测试用例
  - 确保所有测试通过
  - _Requirements: 3.5_

- [ ] 8. Checkpoint - 验证所有模块简化
  - 确保所有测试通过，询问用户是否有问题

- [ ] 9. 更新架构文档
  - 更新所有文档反映新架构
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 9.1 更新主架构文档
  - 更新 `.kiro/specs/ARCHITECTURE.md`
  - 反映 SSE 通信方式
  - 反映 v3 架构
  - 反映简化后的模块结构
  - 明确 AI 能力 vs MCP Tools
  - _Requirements: 5.1_

- [ ] 9.2 更新 AI Orchestrator README
  - 更新 `ai-orchestrator/README.md`
  - 描述 v3 架构
  - 描述 5 个 Sub-Agent 的职责
  - 添加开发指南
  - _Requirements: 5.2_

- [ ] 9.3 更新前端 README
  - 更新 `frontend/README.md`（如果存在）
  - 描述 SSE 通信方式
  - 添加开发指南
  - _Requirements: 5.2_

- [ ] 9.4 创建迁移指南
  - 创建 `MIGRATION_GUIDE.md`
  - 说明从旧架构迁移到新架构的步骤
  - 说明破坏性变更
  - _Requirements: 5.5_

- [ ] 9.5 更新 API 文档
  - 更新 API 端点文档
  - 说明 SSE 流式响应格式
  - 说明 MCP Tools 列表
  - _Requirements: 5.4_

- [ ] 10. 最终验证
  - 确保整个系统正常工作

- [ ] 10.1 运行所有测试
  - 运行前端测试（如果有）
  - 运行 Backend 测试
  - 运行 AI Orchestrator 测试
  - 确保所有测试通过
  - _Requirements: 3.5_

- [ ] 10.2 手动测试完整流程
  - 测试用户注册和登录
  - 测试聊天功能
  - 测试生成素材（图片和视频）
  - 测试分析性能
  - 测试创建广告
  - 测试生成落地页
  - _Requirements: 1.6, 3.5_

- [ ] 10.3 性能测试
  - 测量 AI Orchestrator 启动时间
  - 测量前端包大小
  - 测量响应延迟
  - 验证性能指标达标
  - _Requirements: 2.5_

- [ ] 10.4 代码审查
  - 审查代码质量
  - 确保符合编码规范
  - 确保没有遗留的 v2 代码
  - _Requirements: 2.1, 3.1_

- [ ] 11. Final Checkpoint - 确保所有测试通过
  - 确保所有测试通过，询问用户是否有问题
