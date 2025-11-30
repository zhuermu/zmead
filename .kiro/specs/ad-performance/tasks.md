# Implementation Plan - Ad Performance

- [x] 1. Set up project structure and core interfaces
  - Create directory structure for ad_performance module in ai-orchestrator
  - Define base classes and interfaces (BaseFetcher, BaseAnalyzer)
  - Set up Pydantic data models (MetricsData, PerformanceAnalysis, Anomaly, Recommendation)
  - Configure Hypothesis for property-based testing (100 iterations)
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 1.1 Write property test for data models
  - **Property 1: Data fetch returns complete structure**
  - **Validates: Requirements 1.1, 1.2, 1.3**

- [ ] 2. Implement AdPerformance main entry point
  - Create AdPerformance class with execute() method
  - Implement action routing (fetch_ad_data, generate_daily_report, etc.)
  - Add error handling and logging
  - Initialize dependencies (MCP client, Gemini client, Redis cache)
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1_

- [x] 3. Implement platform data fetchers
- [x] 3.1 Create BaseFetcher abstract class
  - Define fetch_insights() interface
  - Define get_account_info() interface
  - Add retry mechanism with exponential backoff
  - _Requirements: 1.1, 1.4_

- [x] 3.2 Write property test for retry mechanism
  - **Property 2: Fetch failure auto-retry**
  - **Validates: Requirements 1.4, 8.5**

- [x] 3.3 Implement MetaFetcher
  - Integrate facebook-business SDK
  - Implement fetch_insights() for Meta Marketing API
  - Transform API response to standard format
  - Handle Meta-specific errors
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 3.4 Implement TikTokFetcher
  - Integrate tiktok-business-api SDK
  - Implement fetch_insights() for TikTok Ads API
  - Transform API response to standard format
  - Handle TikTok-specific errors
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 3.5 Implement GoogleFetcher (stub for MVP)
  - Create stub implementation returning empty data
  - Add TODO comments for future implementation
  - _Requirements: 1.1_

- [x] 4. Implement MCP integration for data persistence
- [x] 4.1 Implement save_metrics MCP call
  - Call save_metrics tool after successful fetch
  - Handle MCP errors and retries
  - _Requirements: 1.5_

- [x] 4.2 Implement get_metrics MCP call
  - Call get_metrics tool to retrieve historical data
  - Parse and validate response
  - _Requirements: 3.2, 7.1_

- [x] 4.3 Write property test for data persistence
  - **Property 3: Fetch data correctly saved**
  - **Validates: Requirements 1.5**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement performance analyzer
- [x] 6.1 Create PerformanceAnalyzer class
  - Implement analyze_entity() method
  - Calculate period metrics and changes
  - Format percentage changes
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 6.2 Integrate AI insights generation
  - Create AIAnalyzer class
  - Implement analyze_metrics() using Gemini 2.5 Pro
  - Parse AI response and extract insights
  - _Requirements: 3.4_

- [x] 6.3 Write property test for performance analysis
  - **Property 5: Performance analysis result completeness**
  - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

- [x] 7. Implement anomaly detection
- [x] 7.1 Create AnomalyDetector class
  - Implement statistical anomaly detection (Z-score)
  - Calculate expected value and standard deviation
  - Determine severity based on deviation
  - _Requirements: 4.1, 4.4_

- [x] 7.2 Implement severity thresholds
  - Add CPA threshold (>50% = high severity)
  - Add ROAS threshold (>30% decline = critical)
  - Generate recommendations for anomalies
  - _Requirements: 4.2, 4.3, 4.5_

- [x] 7.3 Write property test for anomaly detection
  - **Property 6: Anomaly detection identification**
  - **Validates: Requirements 4.1, 4.4, 4.5**

- [x] 7.4 Write example tests for severity thresholds
  - **Property 7: CPA anomaly severity**
  - **Property 8: ROAS anomaly severity**
  - **Validates: Requirements 4.2, 4.3**

- [x] 8. Implement recommendation engine
- [x] 8.1 Create RecommendationEngine class
  - Implement generate() method
  - Calculate confidence scores
  - _Requirements: 5.1, 5.5_

- [x] 8.2 Implement underperforming entity identification
  - Identify low ROAS adsets
  - Check for consistent underperformance (3+ days)
  - Generate pause_adset recommendations
  - _Requirements: 5.2_

- [x] 8.3 Write property test for pause recommendations
  - **Property 9: Low-performing entity pause recommendation**
  - **Validates: Requirements 5.2**

- [x] 8.4 Implement high-performing entity identification
  - Identify high ROAS adsets
  - Generate increase_budget recommendations
  - Calculate expected impact
  - _Requirements: 5.3_

- [x] 8.5 Write property test for budget increase recommendations
  - **Property 10: High-performing entity budget increase**
  - **Validates: Requirements 5.3**

- [x] 8.6 Implement creative fatigue detection
  - Detect declining CTR trends
  - Generate refresh_creative recommendations
  - _Requirements: 5.4_

- [x] 8.7 Write property test for creative refresh recommendations
  - **Property 11: Creative fatigue refresh recommendation**
  - **Validates: Requirements 5.4**

- [x] 8.8 Write property test for recommendation completeness
  - **Property 12: Recommendation data completeness**
  - **Validates: Requirements 5.1, 5.5, 10.1, 10.2, 10.3, 10.4, 10.5**

- [-] 9. Implement daily report generation
- [x] 9.1 Create report generator
  - Aggregate metrics from MCP
  - Calculate summary statistics
  - Call AI analyzer for insights
  - Call recommendation engine
  - Assemble complete report structure
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 9.2 Write property test for daily report
  - **Property 4: Daily report data completeness**
  - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

- [x] 9.3 Implement notification data formatting
  - Format daily_report notification data
  - Format anomaly_alert notification data
  - Set priority based on severity
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ] 9.4 Write property test for notification data
  - **Property 17: Notification data completeness and correctness**
  - **Validates: Requirements 9.1, 9.2, 9.3, 9.4**

- [x] 10. Implement multi-platform data aggregation
- [x] 10.1 Create DataAggregator class
  - Implement aggregate_by_platform() method
  - Calculate total metrics across platforms
  - Validate data consistency (total = sum of platforms)
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 10.2 Write property test for data aggregation
  - **Property 16: Multi-platform data aggregation completeness**
  - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

- [-] 11. Implement report exporters
- [x] 11.1 Create CSVExporter class
  - Convert metrics data to pandas DataFrame
  - Export to CSV format
  - Validate data completeness
  - _Requirements: 6.1, 6.2_

- [x] 11.2 Write property test for CSV export
  - **Property 13: CSV export data completeness**
  - **Validates: Requirements 6.1, 6.2**

- [ ] 11.3 Create PDFExporter class
  - Generate PDF with reportlab
  - Add charts using matplotlib
  - Include AI analysis text
  - _Requirements: 6.3_

- [ ] 11.4 Write property test for PDF export
  - **Property 14: PDF export content completeness**
  - **Validates: Requirements 6.3**

- [ ] 11.5 Implement S3 upload and link generation
  - Upload file to S3 using MCP get_upload_url
  - Generate download URL
  - Set 24-hour expiration
  - _Requirements: 6.4, 6.5_

- [ ] 11.6 Write property test for file upload
  - **Property 15: Export file upload and link generation**
  - **Validates: Requirements 6.4, 6.5**

- [x] 12. Implement caching layer
  - Create CacheManager class
  - Implement get_cached_metrics() and cache_metrics()
  - Set 5-minute TTL
  - Add cache invalidation logic
  - _Requirements: Performance requirements_

- [x] 13. Implement error handling
  - Create ErrorHandler class
  - Handle API errors (401, 403, 429, 500, timeout)
  - Handle MCP errors
  - Handle AI model errors
  - Return standardized error responses
  - _Requirements: 8.5_

- [x] 14. Wire up AI Orchestrator integration
  - Register Ad Performance module in AI Orchestrator
  - Update reporting_node.py to call Ad Performance
  - Test end-to-end flow from AI Orchestrator
  - _Requirements: All_

- [x] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
