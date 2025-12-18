# Campaign Automation 实现计划（Implementation Plan）

## 任务列表（Task List）

- [x] 1. 设置项目结构和核心接口
  - 创建 `ai-orchestrator/app/modules/campaign_automation/` 目录结构
  - 定义 Module API 接口（`capability.py`）
  - 定义数据模型（`models.py`）
  - 设置测试框架（pytest + Hypothesis）
  - _Requirements: 所有需求_

- [x] 2. 实现平台适配器基础架构
  - 创建 `PlatformAdapter` 抽象基类
  - 实现 `MetaAdapter` 用于 Meta Marketing API
  - 实现 `TikTokAdapter` 用于 TikTok Ads API
  - 实现 `GoogleAdapter` 用于 Google Ads API
  - 实现平台路由逻辑
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 2.1 编写平台适配器属性测试
  - **Property 14: 平台适配器路由**
  - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

- [x] 3. 实现 Campaign Manager（广告系列管理器）
  - 实现 `create_campaign` 方法
  - 实现 `_create_adsets` 方法（自动生成 3 个年龄组）
  - 实现 `_create_ads` 方法（素材挂载）
  - 实现 `update_campaign_status` 方法
  - 实现 `get_campaign_details` 方法
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 4.1, 8.1, 8.2_

- [ ]* 3.1 编写 Campaign 创建属性测试
  - **Property 1: Campaign 创建完整性**
  - **Validates: Requirements 1.1**

- [ ]* 3.2 编写 Adset 数量属性测试
  - **Property 2: Adset 数量正确性**
  - **Validates: Requirements 1.2**

- [ ]* 3.3 编写 Adset 配置属性测试
  - **Property 3: Adset 配置完整性**
  - **Validates: Requirements 1.3, 1.4, 1.5**

- [x] 4. 实现 AI 文案生成
  - 创建 `AIClient` 类
  - 实现 `generate_ad_copy` 方法（调用 Gemini API）
  - 实现降级策略（Pro → Flash → 模板文案）
  - 集成到 Campaign Manager 的 `_create_ads` 方法
  - _Requirements: 2.4, 2.5_

- [ ]* 4.1 编写素材挂载属性测试
  - **Property 4: 素材挂载完整性**
  - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

- [x] 5. 实现 MCP 客户端集成
  - 实现 `get_creatives` MCP 工具调用
  - 实现 `create_campaign` MCP 工具调用（数据持久化）
  - 实现 `update_campaign` MCP 工具调用
  - 实现 `get_reports` MCP 工具调用（获取表现数据）
  - 实现 `get_ad_account_token` MCP 工具调用
  - _Requirements: 2.1, 4.3, 8.1_

- [ ]* 5.1 编写数据同步属性测试
  - **Property 8: 数据同步一致性**
  - **Validates: Requirements 4.3**

- [x] 6. 实现 Budget Optimizer（预算优化器）
  - 创建 `BudgetOptimizer` 类
  - 实现 `analyze_performance` 方法
  - 实现 `optimize_budget` 方法（应用优化规则）
  - 实现 ROAS 超标 → 增加预算 20% 规则
  - 实现 CPA 超标 → 降低预算 20% 规则
  - 实现连续 3 天无转化 → 暂停 Adset 规则
  - 实现预算调整上限（单次最大 50%）
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ]* 6.1 编写预算优化规则属性测试
  - **Property 5: 预算优化规则正确性**
  - **Validates: Requirements 3.2, 3.3, 3.4**

- [ ]* 6.2 编写优化结果格式属性测试
  - **Property 6: 优化结果格式完整性**
  - **Validates: Requirements 3.5**

- [x] 7. 实现 A/B Test Manager（A/B 测试管理器）
  - 创建 `ABTestManager` 类
  - 实现 `create_ab_test` 方法（均分预算）
  - 实现 `analyze_ab_test` 方法
  - 实现 `_chi_square_test` 方法（卡方检验）
  - 实现样本量检查（最小 100 次转化）
  - 实现获胜者判定（p-value < 0.05）
  - 实现 `_generate_recommendations` 方法
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [ ]* 7.1 编写 A/B 测试预算均分属性测试
  - **Property 10: A/B 测试预算均分**
  - **Validates: Requirements 5.2**

- [ ]* 7.2 编写 A/B 测试统计分析属性测试
  - **Property 11: A/B 测试统计分析**
  - **Validates: Requirements 5.3, 5.4**

- [ ]* 7.3 编写 A/B 测试建议生成属性测试
  - **Property 12: A/B 测试建议生成**
  - **Validates: Requirements 5.6**

- [x] 8. 实现 Rule Engine（规则引擎）
  - 创建 `RuleEngine` 类
  - 实现 `create_rule` 方法
  - 实现 `check_rules` 方法（定期检查）
  - 实现 `execute_rule_action` 方法
  - 实现规则日志记录
  - 集成 Celery 定时任务（每 6 小时检查）
  - _Requirements: 6.1, 6.3, 6.4, 6.5_

- [ ]* 8.1 编写规则创建和执行属性测试
  - **Property 13: 规则创建和执行**
  - **Validates: Requirements 6.1, 6.3, 6.4, 6.5**

- [ ] 9. 实现错误处理和重试机制
  - 创建 `RetryStrategy` 类
  - 实现指数退避重试（1s, 2s, 4s）
  - 实现 30 秒超时设置
  - 实现最多 3 次重试
  - 实现错误响应格式化
  - 实现错误日志记录
  - _Requirements: 4.4, 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ]* 9.1 编写 API 重试机制属性测试
  - **Property 9: API 重试机制**
  - **Validates: Requirements 4.4, 9.1, 9.4**

- [ ]* 9.2 编写超时处理属性测试
  - **Property 18: 超时处理**
  - **Validates: Requirements 9.2**

- [ ]* 9.3 编写平台错误处理属性测试
  - **Property 15: 平台错误处理**
  - **Validates: Requirements 7.5, 9.3, 9.5**

- [x] 10. 实现缓存机制
  - 创建 `CacheManager` 类
  - 实现 `get_or_fetch` 方法
  - 实现 `invalidate` 方法
  - 集成 Redis 缓存
  - 实现广告状态缓存（5 分钟 TTL）
  - 实现缓存降级策略
  - _Requirements: 8.4_

- [ ]* 10.1 编写缓存降级属性测试
  - **Property 17: 缓存降级机制**
  - **Validates: Requirements 8.4**

- [x] 11. 实现 Module API 主入口
  - 实现 `CampaignAutomation.execute` 方法
  - 实现 action 路由逻辑
  - 实现 `_handle_create_campaign` 方法
  - 实现 `_handle_optimize_budget` 方法
  - 实现 `_handle_manage_campaign` 方法
  - 实现 `_handle_create_ab_test` 方法
  - 实现 `_handle_analyze_ab_test` 方法
  - 实现 `_handle_create_rule` 方法
  - 实现 `_handle_get_campaign_status` 方法
  - _Requirements: 所有需求_

- [ ]* 11.1 编写管理操作执行属性测试
  - **Property 7: 管理操作执行正确性**
  - **Validates: Requirements 4.1, 4.5**

- [ ]* 11.2 编写状态查询完整性属性测试
  - **Property 16: 状态查询完整性**
  - **Validates: Requirements 8.1, 8.2, 8.3**

- [x] 12. 集成到 AI Orchestrator
  - 在 AI Orchestrator 中注册 Campaign Automation 模块
  - 更新路由节点以支持广告投放意图
  - 实现 Campaign Automation 调用逻辑
  - 测试端到端流程
  - _Requirements: 所有需求_

- [x] 13. Checkpoint - 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户

- [x] 14. 编写集成测试
  - 测试完整的广告创建流程（端到端）
  - 测试预算优化流程
  - 测试 A/B 测试流程
  - 测试规则引擎流程
  - 测试错误处理和重试
  - _Requirements: 所有需求_

- [ ] 15. 配置监控和告警
  - 配置 Prometheus 指标
  - 配置告警规则
  - 配置日志聚合
  - 创建监控仪表板
  - _Requirements: 非功能性需求_

- [ ] 16. 编写部署文档
  - 创建 Dockerfile
  - 创建 Kubernetes 配置
  - 编写环境变量配置文档
  - 编写运维手册
  - _Requirements: 非功能性需求_
