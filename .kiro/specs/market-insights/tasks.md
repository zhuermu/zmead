# Implementation Plan - Market Insights（市场洞察）

- [x] 1. Set up module structure and core interfaces
  - [x] 1.1 Create module directory structure and __init__.py files
    - Create `ai-orchestrator/app/modules/market_insights/` directory
    - Create subdirectories: `analyzers/`, `fetchers/`, `trackers/`, `utils/`
    - Add `__init__.py` files to all directories
    - _Requirements: All_

  - [x] 1.2 Implement data models (models.py)
    - Create Pydantic models: CompetitorInfo, CompetitorInsights, CompetitorAnalysis
    - Create models: TrendingCreative, CreativeAnalysis, TrendingCreativesResponse
    - Create models: KeywordTrend, TrendInsights, MarketTrendsResponse
    - Create models: AudienceRecommendation, CreativeDirection, BudgetPlanning, AdStrategy
    - Create models: PerformanceMetrics, PerformanceImprovement, StrategyPerformanceResponse
    - _Requirements: 1.1-1.5, 2.1-2.5, 3.1-3.5, 4.1-4.5, 5.1-5.5_

  - [ ]* 1.3 Write property test for data models
    - **Property 1: 竞品分析返回完整结构**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**

  - [x] 1.4 Implement capability.py (main entry point)
    - Create MarketInsights class with execute() method
    - Implement action routing for all 6 actions
    - Add error handling wrapper
    - _Requirements: All_


- [-] 2. Implement utility components
  - [x] 2.1 Implement cache_manager.py
    - Create CacheManager class with Redis integration
    - Implement get(), set(), get_stale_cache(), set_with_stale() methods
    - Configure TTL: 12 hours for creatives, 24 hours for trends
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 2.2 Write property tests for cache TTL and behavior
    - **Property 13: 缓存 TTL 配置**
    - **Property 14: 缓存命中直接返回**
    - **Property 15: 缓存过期刷新**
    - **Property 16: 缓存失败降级**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

  - [x] 2.3 Implement rate_limiter.py
    - Create RateLimiter class with configurable max_requests and period
    - Implement acquire() method with async lock
    - Configure for pytrends: 5 requests per minute
    - _Requirements: 6.2_

  - [ ]* 2.4 Write property test for rate limiting
    - **Property 9: pytrends 速率限制**
    - **Validates: Requirements 6.2**

  - [x] 2.5 Implement retry_strategy.py
    - Create retry_with_backoff() function
    - Implement exponential backoff with max 3 retries
    - Add 30 second timeout support
    - _Requirements: 6.3, 6.5_

  - [ ]* 2.6 Write property tests for retry and timeout
    - **Property 10: API 调用失败自动重试**
    - **Property 12: API 超时处理**
    - **Validates: Requirements 6.3, 6.5**

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [x] 4. Implement data fetchers
  - [x] 4.1 Implement tiktok_fetcher.py
    - Create TikTokFetcher class with API authentication
    - Implement get_trending_creatives() method
    - Implement get_creative_details() method
    - Add response transformation to standard format
    - Integrate with cache_manager and retry_strategy
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ]* 4.2 Write property test for trending creatives completeness
    - **Property 3: 热门素材数据完整性**
    - **Validates: Requirements 2.1, 2.2, 2.3**

  - [x] 4.3 Implement trends_fetcher.py
    - Create TrendsFetcher class with pytrends integration
    - Implement get_interest_over_time() method with thread pool executor
    - Implement get_related_queries() method
    - Add growth rate calculation and trend direction logic
    - Integrate with rate_limiter and cache_manager
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 4.4 Write property test for market trends completeness
    - **Property 5: 市场趋势数据完整性**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [x] 6. Implement analyzers
  - [x] 6.1 Implement competitor_analyzer.py
    - Create CompetitorAnalyzer class with Gemini client
    - Implement analyze() method with AI prompt
    - Implement extract_product_info() and generate_insights() methods
    - Add error handling for invalid URLs and AI failures
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 6.2 Write property tests for competitor analysis
    - **Property 1: 竞品分析返回完整结构**
    - **Property 2: 竞品分析失败返回错误信息**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

  - [x] 6.3 Implement creative_analyzer.py
    - Create CreativeAnalyzer class with Gemini Vision client
    - Implement analyze_creative() method for visual analysis
    - Extract visual_style, color_palette, key_elements, success_factors
    - Generate recommendations based on analysis
    - _Requirements: 2.4, 2.5_

  - [ ]* 6.4 Write property test for creative analysis completeness
    - **Property 4: 素材分析结果完整性**
    - **Validates: Requirements 2.4, 2.5**

  - [x] 6.5 Implement strategy_generator.py
    - Create StrategyGenerator class with Gemini client
    - Implement generate() method with comprehensive AI prompt
    - Implement generate_audience_recommendations() method
    - Implement generate_creative_direction() method
    - Generate budget_planning and campaign_structure
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 6.6 Write property test for strategy completeness
    - **Property 6: 广告策略完整性**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**

- [ ] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [x] 8. Implement performance tracker
  - [x] 8.1 Implement performance_tracker.py
    - Create PerformanceTracker class
    - Implement track() method to compare campaigns with/without strategy
    - Implement calculate_improvement() for ROAS, CTR, conversion rate lifts
    - Generate insights text based on comparison
    - Add error handling for tracking failures
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 8.2 Write property tests for strategy tracking
    - **Property 7: 策略效果追踪完整性**
    - **Property 8: 策略追踪失败返回错误信息**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

- [x] 9. Implement error handling and degradation
  - [x] 9.1 Implement error_handler.py
    - Create ErrorHandler class with unified error handling
    - Implement handle_api_error() with retry logic
    - Implement handle_validation_error()
    - Map error codes to user-friendly messages
    - _Requirements: 1.5, 5.5, 6.3, 6.4, 6.5, 6.6_

  - [x] 9.2 Implement degradation_handler.py
    - Create DegradationHandler class
    - Implement handle_tiktok_unavailable() with stale cache fallback
    - Implement handle_trends_unavailable() with AI fallback
    - Return degraded flag and appropriate messages
    - _Requirements: 6.4, 6.6_

  - [ ]* 9.3 Write property test for degradation handling
    - **Property 11: API 限额降级处理**
    - **Validates: Requirements 6.4, 6.6**

- [ ] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [x] 11. Wire up capability and integrate with AI Orchestrator
  - [x] 11.1 Complete capability.py implementation
    - Wire all analyzers, fetchers, and trackers into execute() method
    - Implement action handlers for all 6 actions
    - Add MCP client integration for save_insight and get_insights
    - Implement parallel data fetching for comprehensive insights
    - _Requirements: All_

  - [x] 11.2 Create market_insights_node.py in AI Orchestrator
    - Create MarketInsightsNode class
    - Implement node execution logic
    - Wire to AI Orchestrator graph
    - _Requirements: All_

  - [x] 11.3 Update AI Orchestrator routing
    - Add market insights intent recognition
    - Configure routing to MarketInsightsNode
    - _Requirements: All_

- [x] 12. Integration testing
  - [x]* 12.1 Write integration tests
    - Test end-to-end flow for analyze_competitor
    - Test end-to-end flow for get_trending_creatives
    - Test end-to-end flow for get_market_trends
    - Test end-to-end flow for generate_ad_strategy
    - Test end-to-end flow for track_strategy_performance
    - Test degradation scenarios
    - _Requirements: All_

- [x] 13. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
