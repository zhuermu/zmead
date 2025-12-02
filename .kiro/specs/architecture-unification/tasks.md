# 实施计划 - AI Orchestrator 架构统一

## 任务清单

- [x] 1. Phase 1: 验证 v3 功能完整性
  - 验证 v3 API 可以正常处理各种用户消息
  - 验证 v3 与 Web Platform MCP 通信正常
  - 验证 v3 与前端集成正常
  - 运行现有测试确保 v3 功能正常
  - _Requirements: 1.1, 2.3_

- [x] 2. Phase 2: 文件重命名和移动
  - _Requirements: 1.2, 2.1_

- [x] 2.1 重命名核心文件
  - 备份当前代码（创建 Git 分支）
  - 重命名 `app/core/graph_v3.py` → `app/core/graph.py`
  - 重命名 `app/api/chat_v3.py` → `app/api/chat.py`
  - 移动 `app/nodes/persist.py` → `app/core/persist.py`
  - _Requirements: 1.2, 2.1_

- [x] 2.2 更新导入语句
  - 更新 `app/main.py` 中的导入
  - 更新 `app/api/chat.py` 中的导入
  - 更新 `app/core/graph.py` 中的导入
  - 搜索并更新所有引用 `graph_v3` 的地方
  - 搜索并更新所有引用 `chat_v3` 的地方
  - _Requirements: 1.2, 2.1_

- [x] 3. Phase 3: 更新 main.py 启动流程
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 3.1 简化 lifespan 函数
  - 删除 v2 graph 的编译代码
  - 删除 `register_all_tools()` 调用（v2 专用）
  - 保留 `register_all_agents()` 调用
  - 只编译一个 LangGraph
  - _Requirements: 4.1, 4.2_

- [x] 3.2 更新路由注册
  - 删除 v2 chat router 的注册
  - 保留 v3 chat router（已重命名为 chat.py）
  - 保留 health router
  - 保留 campaign_automation router
  - _Requirements: 2.1, 4.1_

- [x] 4. Phase 4: 删除 v2 代码
  - _Requirements: 1.2, 1.3, 1.4, 1.5_

- [x] 4.1 删除 v2 节点文件
  - 删除 `app/nodes/router.py`
  - 删除 `app/nodes/planner.py`
  - 删除 `app/nodes/executor.py`
  - 删除 `app/nodes/analyzer.py`
  - 删除 `app/nodes/respond.py`
  - 删除 `app/nodes/confirmation.py`
  - _Requirements: 1.4_

- [x] 4.2 删除 v2 stub 节点
  - 删除 `app/nodes/creative_stub.py`
  - 删除 `app/nodes/reporting_stub.py`
  - 删除 `app/nodes/market_intel_stub.py`
  - 删除 `app/nodes/landing_page_stub.py`
  - 删除 `app/nodes/ad_engine_stub.py`
  - _Requirements: 1.4_

- [x] 4.3 删除 v2 功能节点
  - 删除 `app/nodes/creative_node.py`
  - 删除 `app/nodes/reporting_node.py`
  - 删除 `app/nodes/market_insights_node.py`
  - 删除 `app/nodes/landing_page_node.py`
  - 删除 `app/nodes/campaign_automation_node.py`
  - 删除 `app/nodes/__init__.py`（如果目录为空）
  - 删除 `app/nodes/` 目录（如果为空）
  - _Requirements: 1.4_

- [x] 4.4 删除 v2 核心文件
  - 删除 `app/core/routing.py`
  - _Requirements: 1.3_

- [x] 4.5 删除 tools 目录
  - 检查 `app/tools/` 是否只用于 v2
  - 如果是，删除整个 `app/tools/` 目录
  - _Requirements: 1.5_

- [x] 5. Phase 5: 删除 v2 测试
  - _Requirements: 1.1_

- [x] 5.1 删除 v2 核心测试
  - 删除 `tests/test_intent_recognition_property.py`（如果测试 v2 router）
  - 删除 `tests/test_execution_order_property.py`（如果测试 v2 planner）
  - 删除 `tests/test_context_resolution_property.py`（如果 v2 特定）
  - 删除 `tests/test_checkpoint_verification.py`（如果 v2 特定）
  - _Requirements: 1.1_

- [x] 5.2 删除 v2 节点测试
  - 删除 `tests/test_reporting_node.py`
  - 删除 `tests/test_phase2_checkpoint.py`
  - _Requirements: 1.1_

- [x] 6. Phase 6: 更新文档
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 6.1 更新主文档
  - 更新 `ai-orchestrator/README.md`，删除 v2 相关内容
  - 更新架构图为 v3 版本
  - 更新 API 文档
  - _Requirements: 5.1, 5.5_

- [x] 6.2 更新 spec 文档
  - 更新 `.kiro/specs/ai-orchestrator/design.md`
  - 删除 v2 架构描述
  - 更新为 v3 架构
  - _Requirements: 5.3_

- [x] 6.3 整理架构文档
  - 重命名 `docs/ARCHITECTURE_V3.md` → `docs/ARCHITECTURE.md`
  - 删除旧的 v2 架构文档（如果存在）
  - _Requirements: 5.4_

- [-] 7. Phase 7: 测试验证
  - _Requirements: 2.3, 2.4, 2.5_

- [ ] 7.1 运行测试套件
  - 运行 `pytest` 确保所有测试通过
  - 修复任何失败的测试
  - _Requirements: 3.5_

- [ ] 7.2 手动功能测试
  - 启动 ai-orchestrator 服务
  - 测试 `/health` 端点
  - 测试 `/api/v1/chat` 端点（流式）
  - 测试 `/api/v1/chat/sync` 端点
  - _Requirements: 2.3, 2.4_

- [ ] 7.3 集成测试
  - 启动完整系统（frontend + backend + ai-orchestrator）
  - 测试前端对话功能
  - 测试各种用户意图（生成素材、查看报表等）
  - 验证 SSE 流式响应正常
  - _Requirements: 2.3, 2.4, 2.5_

- [x] 8. Checkpoint - 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户

