# Implementation Plan - Ad Creative（广告素材生成）

- [x] 1. 设置项目结构和核心接口
  - [x] 1.1 创建模块目录结构
    - 创建 `ai-orchestrator/app/modules/ad_creative/` 目录
    - 创建子目录：extractors/, generators/, analyzers/, managers/, utils/
    - 创建各目录的 `__init__.py` 文件
    - _Requirements: 模块边界_

  - [x] 1.2 定义核心数据模型
    - 创建 `models.py` 定义 ProductInfo、Creative、CreativeScore、CompetitorAnalysis 等模型
    - 使用 Pydantic 进行数据验证
    - _Requirements: 数据模型_

  - [x] 1.3 实现主入口 AdCreative 类
    - 创建 `capability.py` 实现 execute() 接口
    - 定义支持的 actions 路由
    - _Requirements: Module API_

- [x] 2. 实现产品信息提取功能
  - [x] 2.1 实现提取器基类
    - 创建 `extractors/base.py` 定义 BaseExtractor 抽象类
    - 定义 extract() 和 supports() 抽象方法
    - _Requirements: 1.1_

  - [x] 2.2 实现 Shopify 提取器
    - 创建 `extractors/shopify_extractor.py`
    - 使用 Shopify API 提取产品信息
    - _Requirements: 1.3_

  - [x] 2.3 实现 Amazon 提取器
    - 创建 `extractors/amazon_extractor.py`
    - 使用网页解析提取产品信息
    - _Requirements: 1.4_

  - [ ]* 2.4 编写产品信息提取属性测试
    - **Property 1: 产品信息提取完整性**
    - **Validates: Requirements 1.1, 1.2**

  - [ ]* 2.5 编写提取失败处理属性测试
    - **Property 2: 产品信息提取失败处理**
    - **Validates: Requirements 1.5**

- [x] 3. 实现文件验证和上传功能
  - [x] 3.1 实现文件验证器
    - 创建 `utils/validators.py`
    - 实现文件格式验证（JPG/PNG）
    - 实现文件大小验证（最大 10MB）
    - 实现文件魔数验证
    - _Requirements: 2.2_

  - [x] 3.2 实现上传管理器
    - 创建 `managers/upload_manager.py`
    - 实现 get_presigned_url() 方法
    - 实现 upload_to_s3() 方法
    - 实现 upload_creative() 完整流程
    - _Requirements: 2.3, 4.1.1, 4.1.2, 4.1.3_

  - [ ]* 3.3 编写文件验证属性测试
    - **Property 3: 文件上传验证**
    - **Validates: Requirements 2.2**

  - [ ]* 3.4 编写上传数量限制属性测试
    - **Property 4: 上传数量限制**
    - **Validates: Requirements 2.5**

  - [ ]* 3.5 编写上传流程属性测试
    - **Property 14: 素材上传流程完整性**
    - **Validates: Requirements 4.1.1, 4.1.2, 4.1.3**

- [x] 4. 实现图片生成功能
  - [x] 4.1 实现宽高比处理工具
    - 创建 `utils/aspect_ratio.py`
    - 实现平台到宽高比映射
    - 实现自定义宽高比解析
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 4.2 实现图片生成器
    - 创建 `generators/image_generator.py`
    - 集成 Gemini Imagen 3 API
    - 实现 generate() 方法
    - 实现并行批量生成
    - _Requirements: 4.2_

  - [x] 4.3 实现重试机制
    - 在生成器中实现指数退避重试
    - 最多重试 3 次
    - _Requirements: 4.5, 4.1.4_

  - [ ]* 4.4 编写重试机制属性测试
    - **Property 5: 操作失败自动重试**
    - **Validates: Requirements 4.5, 4.1.4, 4.1.5, 10.5**

  - [ ]* 4.5 编写平台宽高比映射属性测试
    - **Property 6: 平台宽高比映射**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**

  - [ ]* 4.6 编写自定义宽高比属性测试
    - **Property 7: 自定义宽高比支持**
    - **Validates: Requirements 5.5**

  - [ ]* 4.7 编写生成数量一致性属性测试
    - **Property 17: 素材生成数量一致性**
    - **Validates: Requirements 4.2, 4.4**

- [x] 5. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. 实现素材评分功能
  - [x] 6.1 实现评分引擎
    - 创建 `analyzers/scoring_engine.py`
    - 集成 Gemini 2.5 Flash API
    - 实现四维度评分（视觉冲击力、构图平衡、色彩和谐、文案清晰）
    - 实现加权总分计算
    - _Requirements: 7.1, 7.2, 7.3_

  - [ ]* 6.2 编写评分完整性属性测试
    - **Property 8: 素材评分完整性**
    - **Validates: Requirements 7.1, 7.2, 7.3**

- [x] 7. 实现竞品素材分析功能
  - [x] 7.1 实现竞品分析器
    - 创建 `analyzers/competitor_analyzer.py`
    - 实现 TikTok 广告素材提取
    - 实现构图、色彩、卖点、文案结构分析
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 7.2 实现分析结果保存
    - 通过 MCP 调用 Web Platform 存储分析结果
    - _Requirements: 3.5_

  - [ ]* 7.3 编写竞品分析完整性属性测试
    - **Property 15: 竞品素材分析完整性**
    - **Validates: Requirements 3.2, 3.3**

- [x] 8. 实现素材库管理功能
  - [x] 8.1 实现素材管理器
    - 创建 `managers/creative_manager.py`
    - 实现 get_creatives() 方法（支持筛选和排序）
    - 实现 delete_creative() 方法
    - 实现 download_creative() 方法
    - 实现 batch_download() 方法
    - _Requirements: 6.2, 6.3, 8.1, 8.2, 8.3, 8.4_

  - [ ]* 8.2 编写素材列表排序属性测试
    - **Property 9: 素材列表排序**
    - **Validates: Requirements 7.5**

  - [ ]* 8.3 编写素材库筛选属性测试
    - **Property 10: 素材库筛选功能**
    - **Validates: Requirements 8.2**

  - [ ]* 8.4 编写素材删除一致性属性测试
    - **Property 16: 素材删除一致性**
    - **Validates: Requirements 6.3, 8.4**

  - [ ]* 8.5 编写素材库容量警告属性测试
    - **Property 18: 素材库容量警告**
    - **Validates: Requirements 8.5**

- [x] 9. 实现 Credit 控制功能
  - [x] 9.1 实现 Credit 检查器
    - 创建 `utils/credit_checker.py`
    - 实现 check_and_reserve() 方法
    - 实现 deduct() 方法
    - 实现 refund() 方法
    - 实现 calculate_cost() 方法（含批量折扣）
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 9.2 编写 Credit 流程属性测试
    - **Property 11: Credit 余额检查和扣减**
    - **Validates: Requirements 9.1, 9.2, 9.3**

  - [ ]* 9.3 编写 Credit 退还属性测试
    - **Property 12: Credit 失败退还**
    - **Validates: Requirements 9.4**

  - [ ]* 9.4 编写批量折扣属性测试
    - **Property 13: 批量生成折扣**
    - **Validates: Requirements 9.5**

- [x] 10. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. 实现 MCP 工具调用集成
  - [x] 11.1 集成 MCP Client
    - 在各组件中注入 MCP Client
    - 实现 get_creatives、create_creative、update_creative、delete_creative 调用
    - _Requirements: 10.2, 10.3, 10.4_

  - [x] 11.2 实现 MCP 调用错误处理
    - 实现连接失败重试
    - 实现超时处理
    - _Requirements: 10.5_

  - [ ]* 11.3 编写 MCP 工具调用属性测试
    - **Property 19: MCP 工具调用正确性**
    - **Validates: Requirements 10.2, 10.4**

- [x] 12. 实现变体生成功能
  - [x] 12.1 实现变体生成器
    - 创建 `generators/variant_generator.py`
    - 基于原始素材生成变体
    - _Requirements: 6.4_

- [x] 13. 实现缓存优化
  - [x] 13.1 实现缓存管理器
    - 创建 `utils/cache_manager.py`
    - 实现产品信息缓存（1 小时）
    - 实现分析结果缓存（24 小时）
    - _Requirements: 非功能性需求 - 成本控制_

- [x] 14. 集成测试和文档
  - [x] 14.1 编写集成测试
    - 测试完整的素材生成流程
    - 测试 Credit 扣减和退还流程
    - _Requirements: 全部_

  - [x] 14.2 更新模块 README
    - 编写使用说明
    - 编写配置说明
    - _Requirements: 文档_

- [x] 15. Final Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.
