"""
Ad Performance capability - Main entry point for the module.

This module provides the main entry point for Ad Performance functionality,
including data fetching, report generation, anomaly detection, and recommendations.

Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1
"""

import structlog
from redis.asyncio import Redis

from app.core.errors import ErrorHandler
from app.services.gemini_client import GeminiClient, GeminiError
from app.services.mcp_client import MCPClient, MCPError
from .analyzers.recommendation_engine import RecommendationEngine
from .models import ReportSummary, AIAnalysis, DailyReport
from .utils import DataAggregator, CacheManager, AdPerformanceErrorHandler

logger = structlog.get_logger(__name__)


class AdPerformance:
    """Ad Performance 功能模块主入口
    
    Provides comprehensive ad performance analytics including:
    - Multi-platform data fetching (Meta, TikTok, Google)
    - Daily report generation with AI insights
    - Performance analysis and comparison
    - Anomaly detection with severity classification
    - Optimization recommendations
    - Report export (CSV, PDF)
    - Multi-platform metrics aggregation
    
    Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1
    """

    def __init__(
        self,
        mcp_client: MCPClient | None = None,
        gemini_client: GeminiClient | None = None,
        redis_client: Redis | None = None,
    ):
        """初始化 Ad Performance 模块
        
        Args:
            mcp_client: MCP client for Web Platform communication
            gemini_client: Gemini client for AI analysis
            redis_client: Redis client for caching
        """
        # Initialize dependencies
        self.mcp_client = mcp_client or MCPClient()
        self.gemini_client = gemini_client or GeminiClient()
        self.redis_client = redis_client
        
        # Initialize utility components
        self.data_aggregator = DataAggregator()
        
        # Initialize cache manager if Redis is available
        self.cache_manager = CacheManager(redis_client) if redis_client else None
        
        logger.info(
            "ad_performance_initialized",
            has_mcp=self.mcp_client is not None,
            has_gemini=self.gemini_client is not None,
            has_redis=self.redis_client is not None,
            has_cache=self.cache_manager is not None,
        )

    async def execute(self, action: str, parameters: dict, context: dict) -> dict:
        """
        执行报表分析操作
        
        Implements action routing with comprehensive error handling and logging.
        All errors are caught and converted to structured error responses.

        Args:
            action: 操作名称 (fetch_ad_data, generate_daily_report, etc.)
            parameters: 操作参数
            context: 上下文信息（user_id, session_id等）

        Returns:
            操作结果，格式：
            - 成功: {"status": "success", "data": {...}, "message": "..."}
            - 失败: {"status": "error", "error": {...}}
            
        Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1
        """
        user_id = context.get("user_id")
        session_id = context.get("session_id")
        
        log = logger.bind(
            action=action,
            user_id=user_id,
            session_id=session_id,
        )
        
        log.info("ad_performance_execute_start", parameters=parameters)
        
        try:
            # Route to appropriate handler
            if action == "fetch_ad_data":
                result = await self._fetch_ad_data(parameters, context)
            elif action == "generate_daily_report":
                result = await self._generate_daily_report(parameters, context)
            elif action == "analyze_performance":
                result = await self._analyze_performance(parameters, context)
            elif action == "detect_anomalies":
                result = await self._detect_anomalies(parameters, context)
            elif action == "generate_recommendations":
                result = await self._generate_recommendations(parameters, context)
            elif action == "export_report":
                result = await self._export_report(parameters, context)
            elif action == "get_metrics_summary":
                result = await self._get_metrics_summary(parameters, context)
            else:
                log.warning("unknown_action", action=action)
                return {
                    "status": "error",
                    "error": {
                        "code": "1001",
                        "type": "INVALID_ACTION",
                        "message": f"Unknown action: {action}",
                        "details": {
                            "action": action,
                            "supported_actions": [
                                "fetch_ad_data",
                                "generate_daily_report",
                                "analyze_performance",
                                "detect_anomalies",
                                "generate_recommendations",
                                "export_report",
                                "get_metrics_summary",
                            ],
                        },
                    },
                }
            
            log.info("ad_performance_execute_success", action=action)
            return result
            
        except (MCPError, GeminiError) as e:
            # Handle known service errors
            log.error(
                "ad_performance_service_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            error_state = ErrorHandler.handle_error(
                error=e,
                context=f"ad_performance.{action}",
                user_id=user_id,
                session_id=session_id,
            )
            return {
                "status": "error",
                **error_state,
            }
            
        except Exception as e:
            # Handle unexpected errors
            log.error(
                "ad_performance_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            error_state = ErrorHandler.handle_error(
                error=e,
                context=f"ad_performance.{action}",
                user_id=user_id,
                session_id=session_id,
            )
            return {
                "status": "error",
                **error_state,
            }

    async def _fetch_ad_data(self, parameters: dict, context: dict) -> dict:
        """抓取广告数据
        
        Fetches ad data from advertising platforms (Meta, TikTok, Google).
        
        Args:
            parameters: {
                "platform": "meta" | "tiktok" | "google",
                "date_range": {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"},
                "levels": ["campaign", "adset", "ad"],
                "metrics": ["spend", "impressions", "clicks", "conversions", "revenue"]
            }
            context: {"user_id": str, "session_id": str}
            
        Returns:
            {
                "status": "success",
                "data": {
                    "campaigns": [...],
                    "adsets": [...],
                    "ads": [...]
                },
                "sync_time": "ISO timestamp",
                "message": "数据抓取成功"
            }
            
        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
        """
        logger.info("fetch_ad_data_stub", parameters=parameters)
        
        # TODO: Implement in task 3 (platform fetchers)
        return {
            "status": "success",
            "data": {"campaigns": [], "adsets": [], "ads": []},
            "sync_time": "2024-11-28T00:00:00Z",
            "message": "Data fetch not yet implemented (task 3)",
        }
    
    async def _save_metrics_to_mcp(
        self,
        user_id: str,
        ad_account_id: int,
        metrics_data: list[dict],
    ) -> list[dict]:
        """Save metrics data to Web Platform via MCP
        
        Calls save_metrics MCP tool for each metric entity with retry logic.
        
        Args:
            user_id: User ID
            ad_account_id: Ad account ID
            metrics_data: List of metric dicts with entity info and values
            
        Returns:
            List of save results with IDs
            
        Raises:
            MCPError: If save fails after retries
            
        Requirements: 1.5
        """
        log = logger.bind(
            user_id=user_id,
            ad_account_id=ad_account_id,
            metrics_count=len(metrics_data),
        )
        log.info("save_metrics_start")
        
        results = []
        failed_saves = []
        
        for metric in metrics_data:
            try:
                # Call save_metrics MCP tool
                result = await self.mcp_client.call_tool(
                    "save_metrics",
                    {
                        "timestamp": metric["timestamp"],
                        "ad_account_id": ad_account_id,
                        "entity_type": metric["entity_type"],
                        "entity_id": metric["entity_id"],
                        "entity_name": metric["entity_name"],
                        "impressions": metric.get("impressions", 0),
                        "clicks": metric.get("clicks", 0),
                        "spend": metric.get("spend", 0),
                        "conversions": metric.get("conversions", 0),
                        "revenue": metric.get("revenue", 0),
                    },
                )
                
                results.append({
                    "entity_id": metric["entity_id"],
                    "entity_type": metric["entity_type"],
                    "saved_id": result.get("id"),
                    "status": "success",
                })
                
            except MCPError as e:
                log.error(
                    "save_metrics_failed",
                    entity_id=metric["entity_id"],
                    entity_type=metric["entity_type"],
                    error=str(e),
                )
                failed_saves.append({
                    "entity_id": metric["entity_id"],
                    "entity_type": metric["entity_type"],
                    "error": str(e),
                })
        
        log.info(
            "save_metrics_complete",
            successful=len(results),
            failed=len(failed_saves),
        )
        
        # If all saves failed, raise error
        if failed_saves and not results:
            raise MCPError(
                f"Failed to save all metrics: {len(failed_saves)} failures",
                code="3003",
                details={"failed_saves": failed_saves},
            )
        
        # If some saves failed, include in results
        if failed_saves:
            results.extend([
                {
                    "entity_id": f["entity_id"],
                    "entity_type": f["entity_type"],
                    "status": "failed",
                    "error": f["error"],
                }
                for f in failed_saves
            ])
        
        # Invalidate cache for affected dates
        if self.cache_manager and results:
            # Extract unique dates from saved metrics
            dates = set()
            for metric in metrics_data:
                if "timestamp" in metric:
                    # Extract date from timestamp (YYYY-MM-DD)
                    date_str = metric["timestamp"][:10]
                    dates.add(date_str)
            
            # Invalidate cache for each date
            for date in dates:
                await self.cache_manager.invalidate_cache(
                    user_id=user_id,
                    date=date,
                )
                log.info("cache_invalidated", date=date)
        
        return results
    
    async def _get_metrics_from_mcp(
        self,
        user_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        ad_account_id: int | None = None,
        entity_type: str | None = None,
    ) -> dict:
        """Get historical metrics from Web Platform via MCP
        
        Calls get_metrics MCP tool to retrieve aggregated metrics.
        Uses caching to reduce API calls.
        
        Args:
            user_id: User ID
            start_date: Start date (ISO format YYYY-MM-DD)
            end_date: End date (ISO format YYYY-MM-DD)
            ad_account_id: Optional ad account filter
            entity_type: Optional entity type filter (campaign, adset, ad)
            
        Returns:
            Aggregated metrics dict with totals and averages
            
        Raises:
            MCPError: If retrieval fails after retries
            
        Requirements: 3.2, 7.1, Performance requirements
        """
        log = logger.bind(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            ad_account_id=ad_account_id,
            entity_type=entity_type,
        )
        log.info("get_metrics_start")
        
        # Try to get from cache if available and date range is single day
        if self.cache_manager and start_date == end_date and start_date:
            cached_metrics = await self.cache_manager.get_cached_metrics(
                user_id=user_id,
                date=start_date,
                platform=None,  # Cache all platforms together for aggregated metrics
            )
            if cached_metrics:
                log.info("get_metrics_from_cache")
                return cached_metrics
        
        # Build parameters
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if ad_account_id:
            params["ad_account_id"] = ad_account_id
        if entity_type:
            params["entity_type"] = entity_type
        
        try:
            # Call get_metrics MCP tool
            result = await self.mcp_client.call_tool("get_metrics", params)
            
            log.info(
                "get_metrics_complete",
                total_spend=result.get("total_spend"),
                total_revenue=result.get("total_revenue"),
            )
            
            # Parse and validate response
            metrics = {
                "total_impressions": result.get("total_impressions", 0),
                "total_clicks": result.get("total_clicks", 0),
                "total_spend": float(result.get("total_spend", "0")),
                "total_conversions": result.get("total_conversions", 0),
                "total_revenue": float(result.get("total_revenue", "0")),
                "avg_ctr": result.get("avg_ctr", 0.0),
                "avg_cpc": float(result.get("avg_cpc", "0")),
                "avg_cpa": float(result.get("avg_cpa", "0")),
                "avg_roas": result.get("avg_roas", 0.0),
                "period_start": result.get("period_start"),
                "period_end": result.get("period_end"),
            }
            
            # Cache the result if single day query
            if self.cache_manager and start_date == end_date and start_date:
                await self.cache_manager.cache_metrics(
                    user_id=user_id,
                    date=start_date,
                    platform=None,
                    data=metrics,
                )
                log.info("metrics_cached")
            
            return metrics
            
        except MCPError as e:
            log.error("get_metrics_failed", error=str(e))
            raise
    
    async def _get_detailed_metrics_from_mcp(
        self,
        user_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        ad_account_id: int | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict:
        """Get detailed metrics list from Web Platform via MCP
        
        Calls get_reports MCP tool to retrieve paginated detailed metrics.
        
        Args:
            user_id: User ID
            start_date: Start date (ISO format YYYY-MM-DD)
            end_date: End date (ISO format YYYY-MM-DD)
            ad_account_id: Optional ad account filter
            entity_type: Optional entity type filter
            entity_id: Optional entity ID filter
            page: Page number (1-indexed)
            page_size: Items per page (max 100)
            
        Returns:
            Dict with metrics list, pagination info
            
        Raises:
            MCPError: If retrieval fails after retries
            
        Requirements: 3.2, 7.1
        """
        log = logger.bind(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )
        log.info("get_detailed_metrics_start")
        
        # Build parameters
        params = {
            "page": page,
            "page_size": min(page_size, 100),
        }
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if ad_account_id:
            params["ad_account_id"] = ad_account_id
        if entity_type:
            params["entity_type"] = entity_type
        if entity_id:
            params["entity_id"] = entity_id
        
        try:
            # Call get_reports MCP tool
            result = await self.mcp_client.call_tool("get_reports", params)
            
            log.info(
                "get_detailed_metrics_complete",
                total=result.get("total", 0),
                returned=len(result.get("metrics", [])),
            )
            
            return result
            
        except MCPError as e:
            log.error("get_detailed_metrics_failed", error=str(e))
            raise

    async def _generate_daily_report(self, parameters: dict, context: dict) -> dict:
        """生成每日报告
        
        Generates daily performance report with AI analysis and recommendations.
        
        Args:
            parameters: {
                "date": "YYYY-MM-DD",
                "include_ai_analysis": bool,
                "include_recommendations": bool
            }
            context: {"user_id": str, "session_id": str}
            
        Returns:
            {
                "status": "success",
                "report": {
                    "date": "YYYY-MM-DD",
                    "summary": {...},
                    "ai_analysis": {...},
                    "recommendations": [...]
                },
                "notifications": [...],
                "message": "每日报告生成成功"
            }
            
        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
        """
        from datetime import datetime, timedelta
        
        user_id = context.get("user_id")
        report_date = parameters.get("date")
        include_ai_analysis = parameters.get("include_ai_analysis", True)
        include_recommendations = parameters.get("include_recommendations", True)
        
        log = logger.bind(
            user_id=user_id,
            report_date=report_date,
            include_ai_analysis=include_ai_analysis,
            include_recommendations=include_recommendations,
        )
        log.info("generate_daily_report_start")
        
        try:
            # 1. Aggregate metrics from MCP for the specified date
            metrics = await self._get_metrics_from_mcp(
                user_id=user_id,
                start_date=report_date,
                end_date=report_date,
            )
            
            # 2. Calculate summary statistics
            summary = ReportSummary(
                total_spend=metrics.get("total_spend", 0.0),
                total_revenue=metrics.get("total_revenue", 0.0),
                overall_roas=metrics.get("avg_roas", 0.0),
                total_conversions=metrics.get("total_conversions", 0),
                avg_cpa=metrics.get("avg_cpa", 0.0),
            )
            
            log.info(
                "summary_calculated",
                total_spend=summary.total_spend,
                total_revenue=summary.total_revenue,
                overall_roas=summary.overall_roas,
            )
            
            # 3. Call AI analyzer for insights (if requested)
            ai_analysis = None
            if include_ai_analysis:
                ai_analysis = await self._generate_ai_insights(
                    current_metrics=metrics,
                    report_date=report_date,
                    user_id=user_id,
                )
                log.info("ai_analysis_generated", insights_count=len(ai_analysis.key_insights))
            else:
                # Provide empty AI analysis
                ai_analysis = AIAnalysis(
                    key_insights=[],
                    trends={},
                )
            
            # 4. Call recommendation engine (if requested)
            recommendations = []
            if include_recommendations:
                # Get detailed metrics for recommendations
                detailed_result = await self._get_detailed_metrics_from_mcp(
                    user_id=user_id,
                    start_date=report_date,
                    end_date=report_date,
                    page=1,
                    page_size=100,
                )
                
                # Group metrics by entity type
                metrics_data = self._group_metrics_by_entity_type(
                    detailed_result.get("metrics", [])
                )
                
                # Generate recommendations
                engine = RecommendationEngine(mcp_client=self.mcp_client)
                recommendations = await engine.generate(
                    metrics_data=metrics_data,
                    optimization_goal="maximize_roas",
                    constraints={"min_roas_threshold": 2.0},
                )
                
                log.info("recommendations_generated", count=len(recommendations))
            
            # 5. Assemble complete report structure
            report = DailyReport(
                date=datetime.fromisoformat(report_date).date(),
                summary=summary,
                ai_analysis=ai_analysis,
                recommendations=recommendations,
            )
            
            # 6. Format notification data
            notifications = self._format_notification_data(
                report=report,
                report_date=report_date,
            )
            
            log.info(
                "generate_daily_report_complete",
                notifications_count=len(notifications),
            )
            
            return {
                "status": "success",
                "report": report.model_dump(mode="json"),
                "notifications": notifications,
                "message": "每日报告生成成功",
            }
            
        except Exception as e:
            log.error(
                "generate_daily_report_failed",
                error=str(e),
                exc_info=True,
            )
            raise
    
    async def _generate_ai_insights(
        self,
        current_metrics: dict,
        report_date: str,
        user_id: str,
    ) -> "AIAnalysis":
        """Generate AI insights using Gemini
        
        Args:
            current_metrics: Current period metrics
            report_date: Report date
            user_id: User ID
            
        Returns:
            AIAnalysis with key insights and trends
        """
        from datetime import datetime, timedelta
        
        log = logger.bind(user_id=user_id, report_date=report_date)
        log.info("generate_ai_insights_start")
        
        try:
            # Get previous day metrics for comparison
            previous_date = (
                datetime.fromisoformat(report_date) - timedelta(days=1)
            ).date().isoformat()
            
            previous_metrics = await self._get_metrics_from_mcp(
                user_id=user_id,
                start_date=previous_date,
                end_date=previous_date,
            )
            
            # Calculate changes
            changes = self._calculate_metric_changes(current_metrics, previous_metrics)
            
            # Build prompt for Gemini
            prompt = f"""分析以下广告数据并提供洞察：

当前数据（{report_date}）：
- 花费：${current_metrics.get('total_spend', 0):.2f}
- 收入：${current_metrics.get('total_revenue', 0):.2f}
- ROAS：{current_metrics.get('avg_roas', 0):.2f}
- 转化数：{current_metrics.get('total_conversions', 0)}
- CPA：${current_metrics.get('avg_cpa', 0):.2f}

与前一天对比：
- 花费变化：{changes.get('spend_change', 'N/A')}
- ROAS 变化：{changes.get('roas_change', 'N/A')}
- CPA 变化：{changes.get('cpa_change', 'N/A')}
- 转化变化：{changes.get('conversions_change', 'N/A')}

请提供：
1. 3-5 条关键洞察（简洁明了）
2. 趋势分析（上升/下降/稳定）

以 JSON 格式返回：
{{
  "key_insights": ["洞察1", "洞察2", "洞察3"],
  "trends": {{
    "roas_trend": "declining|stable|improving",
    "spend_trend": "declining|stable|increasing",
    "conversion_trend": "declining|stable|improving"
  }}
}}
"""
            
            # Call Gemini
            response = await self.gemini_client.generate_content(prompt)
            
            # Parse response
            import json
            try:
                analysis_data = json.loads(response.text)
                analysis = AIAnalysis(
                    key_insights=analysis_data.get("key_insights", []),
                    trends=analysis_data.get("trends", {}),
                )
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                log.warning("ai_response_parse_failed", response=response.text)
                analysis = AIAnalysis(
                    key_insights=[
                        f"总花费 ${current_metrics.get('total_spend', 0):.2f}",
                        f"总收入 ${current_metrics.get('total_revenue', 0):.2f}",
                        f"ROAS {current_metrics.get('avg_roas', 0):.2f}",
                    ],
                    trends={
                        "roas_trend": self._determine_trend(changes.get("roas_change", "0%")),
                        "spend_trend": self._determine_trend(changes.get("spend_change", "0%")),
                        "conversion_trend": self._determine_trend(changes.get("conversions_change", "0%")),
                    },
                )
            
            log.info("generate_ai_insights_complete")
            return analysis
            
        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            # Return fallback analysis
            return AIAnalysis(
                key_insights=[
                    f"总花费 ${current_metrics.get('total_spend', 0):.2f}",
                    f"总收入 ${current_metrics.get('total_revenue', 0):.2f}",
                    f"ROAS {current_metrics.get('avg_roas', 0):.2f}",
                ],
                trends={},
            )
    
    def _calculate_metric_changes(
        self,
        current: dict,
        previous: dict,
    ) -> dict:
        """Calculate percentage changes between periods
        
        Args:
            current: Current period metrics
            previous: Previous period metrics
            
        Returns:
            Dict with formatted percentage changes
        """
        changes = {}
        
        for metric in ["total_spend", "total_revenue", "avg_roas", "avg_cpa", "total_conversions"]:
            current_val = current.get(metric, 0)
            previous_val = previous.get(metric, 0)
            
            if previous_val > 0:
                change_pct = ((current_val - previous_val) / previous_val) * 100
                changes[f"{metric.replace('total_', '').replace('avg_', '')}_change"] = (
                    f"{change_pct:+.1f}%"
                )
            else:
                changes[f"{metric.replace('total_', '').replace('avg_', '')}_change"] = "N/A"
        
        return changes
    
    def _determine_trend(self, change_str: str) -> str:
        """Determine trend from change percentage string
        
        Args:
            change_str: Change string like "+5.2%" or "-3.1%"
            
        Returns:
            Trend: "improving", "declining", or "stable"
        """
        if change_str == "N/A":
            return "stable"
        
        try:
            change_val = float(change_str.replace("%", ""))
            if change_val > 5:
                return "improving"
            elif change_val < -5:
                return "declining"
            else:
                return "stable"
        except ValueError:
            return "stable"
    
    def _group_metrics_by_entity_type(self, metrics: list[dict]) -> dict:
        """Group metrics by entity type
        
        Args:
            metrics: List of metric dicts
            
        Returns:
            Dict with campaigns, adsets, ads lists
        """
        grouped = {
            "campaigns": [],
            "adsets": [],
            "ads": [],
        }
        
        for metric in metrics:
            entity_type = metric.get("entity_type")
            if entity_type == "campaign":
                grouped["campaigns"].append(metric)
            elif entity_type == "adset":
                grouped["adsets"].append(metric)
            elif entity_type == "ad":
                grouped["ads"].append(metric)
        
        return grouped
    
    def _format_notification_data(
        self,
        report: "DailyReport",
        report_date: str,
    ) -> list[dict]:
        """Format notification data for Web Platform
        
        Args:
            report: Daily report
            report_date: Report date
            
        Returns:
            List of notification dicts
            
        Requirements: 9.1, 9.2, 9.3, 9.4
        """
        notifications = []
        
        # Always create daily report notification
        notifications.append({
            "type": "daily_report",
            "priority": "normal",
            "title": "每日报告已生成",
            "message": (
                f"您的 {report_date} 广告报告已生成，"
                f"ROAS {report.summary.overall_roas:.2f}"
            ),
            "data": {
                "report_date": report_date,
                "summary": {
                    "total_spend": report.summary.total_spend,
                    "total_revenue": report.summary.total_revenue,
                    "overall_roas": report.summary.overall_roas,
                    "total_conversions": report.summary.total_conversions,
                    "avg_cpa": report.summary.avg_cpa,
                },
            },
        })
        
        # Create anomaly alert notifications for high-priority recommendations
        for rec in report.recommendations:
            if rec.priority == "high":
                # Determine severity based on action
                if rec.action == "pause_adset":
                    severity = "urgent"
                    title = "检测到低效广告组"
                    message = f"{rec.target.name}: {rec.reason}"
                else:
                    severity = "normal"
                    title = "发现优化机会"
                    message = f"{rec.target.name}: {rec.reason}"
                
                notifications.append({
                    "type": "anomaly_alert",
                    "priority": severity,
                    "title": title,
                    "message": message,
                    "data": {
                        "action": rec.action,
                        "target_type": rec.target.type,
                        "target_id": rec.target.id,
                        "target_name": rec.target.name,
                        "reason": rec.reason,
                        "confidence": rec.confidence,
                        "expected_impact": rec.expected_impact.model_dump(mode="json"),
                    },
                })
        
        return notifications

    async def _analyze_performance(self, parameters: dict, context: dict) -> dict:
        """分析广告表现
        
        Analyzes performance of specific entity with period comparison.
        
        Args:
            parameters: {
                "entity_type": "campaign" | "adset" | "ad",
                "entity_id": str,
                "date_range": {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"},
                "comparison_period": "previous_week" | "previous_month"
            }
            context: {"user_id": str, "session_id": str}
            
        Returns:
            {
                "status": "success",
                "analysis": {
                    "entity_id": str,
                    "entity_name": str,
                    "current_period": {...},
                    "previous_period": {...},
                    "changes": {...},
                    "insights": [...]
                }
            }
            
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
        """
        from .analyzers import PerformanceAnalyzer, AIAnalyzer
        
        user_id = context.get("user_id")
        entity_type = parameters.get("entity_type")
        entity_id = parameters.get("entity_id")
        date_range = parameters.get("date_range", {})
        comparison_period = parameters.get("comparison_period", "previous_week")
        
        log = logger.bind(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            date_range=date_range,
            comparison_period=comparison_period,
        )
        log.info("analyze_performance_start")
        
        try:
            # Initialize analyzers
            performance_analyzer = PerformanceAnalyzer()
            ai_analyzer = AIAnalyzer(gemini_client=self.gemini_client)
            
            # Get current period date range
            start_date = date_range.get("start_date")
            end_date = date_range.get("end_date")
            
            if not start_date or not end_date:
                return {
                    "status": "error",
                    "message": "date_range with start_date and end_date is required",
                }
            
            # Calculate comparison period date range
            comp_start, comp_end = PerformanceAnalyzer.get_comparison_date_range(
                start_date=start_date,
                end_date=end_date,
                comparison_period=comparison_period,
            )
            
            log.info(
                "date_ranges_calculated",
                current_start=start_date,
                current_end=end_date,
                comparison_start=comp_start,
                comparison_end=comp_end,
            )
            
            # Fetch current period metrics from MCP
            current_result = await self._get_detailed_metrics_from_mcp(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                entity_type=entity_type,
                entity_id=entity_id,
            )
            current_metrics = current_result.get("metrics", [])
            
            # Fetch comparison period metrics from MCP
            historical_result = await self._get_detailed_metrics_from_mcp(
                user_id=user_id,
                start_date=comp_start,
                end_date=comp_end,
                entity_type=entity_type,
                entity_id=entity_id,
            )
            historical_metrics = historical_result.get("metrics", [])
            
            # Get entity name from current metrics
            entity_name = "Unknown"
            if current_metrics:
                entity_name = current_metrics[0].get("entity_name", "Unknown")
            
            # Analyze entity performance
            analysis = await performance_analyzer.analyze_entity(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                current_data=current_metrics,
                historical_data=historical_metrics,
            )
            
            # Generate AI insights
            ai_analysis = await ai_analyzer.analyze_metrics(
                current_period=analysis.current_period,
                previous_period=analysis.previous_period,
                changes=analysis.changes,
                entity_name=entity_name,
            )
            
            # Combine basic insights with AI insights
            combined_insights = analysis.insights + ai_analysis.key_insights
            # Remove duplicates while preserving order
            seen = set()
            unique_insights = []
            for insight in combined_insights:
                if insight not in seen:
                    seen.add(insight)
                    unique_insights.append(insight)
            
            log.info(
                "analyze_performance_complete",
                current_spend=analysis.current_period.spend,
                current_roas=analysis.current_period.roas,
                insights_count=len(unique_insights),
            )
            
            return {
                "status": "success",
                "analysis": {
                    "entity_id": analysis.entity_id,
                    "entity_name": analysis.entity_name,
                    "current_period": analysis.current_period.model_dump(),
                    "previous_period": analysis.previous_period.model_dump(),
                    "changes": analysis.changes.model_dump(),
                    "insights": unique_insights,
                    "trends": ai_analysis.trends,
                },
                "message": "表现分析完成",
            }
            
        except Exception as e:
            log.error(
                "analyze_performance_failed",
                error=str(e),
                exc_info=True,
            )
            raise

    async def _detect_anomalies(self, parameters: dict, context: dict) -> dict:
        """检测异常
        
        Detects anomalies in metrics using statistical analysis.
        
        Args:
            parameters: {
                "metrics": ["roas", "cpa", "ctr"],
                "sensitivity": "low" | "medium" | "high",
                "lookback_days": int
            }
            context: {"user_id": str, "session_id": str}
            
        Returns:
            {
                "status": "success",
                "anomalies": [
                    {
                        "metric": str,
                        "entity_type": str,
                        "entity_id": str,
                        "current_value": float,
                        "expected_value": float,
                        "deviation": str,
                        "severity": "low" | "medium" | "high" | "critical",
                        "recommendation": str
                    }
                ],
                "message": "检测到 N 个异常"
            }
            
        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
        """
        logger.info("detect_anomalies_stub", parameters=parameters)
        
        # TODO: Implement in task 7 (anomaly detection)
        return {
            "status": "success",
            "anomalies": [],
            "message": "Anomaly detection not yet implemented (task 7)",
        }

    async def _generate_recommendations(self, parameters: dict, context: dict) -> dict:
        """生成优化建议
        
        Generates optimization recommendations based on performance data.
        
        Args:
            parameters: {
                "optimization_goal": "maximize_roas" | "minimize_cpa",
                "budget_constraint": float,
                "min_roas_threshold": float
            }
            context: {"user_id": str, "session_id": str}
            
        Returns:
            {
                "status": "success",
                "recommendations": [
                    {
                        "priority": "low" | "medium" | "high",
                        "action": "pause_adset" | "increase_budget" | "refresh_creative",
                        "target": {...},
                        "reason": str,
                        "expected_impact": {...},
                        "confidence": float
                    }
                ],
                "summary": {...}
            }
            
        Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
        """
        logger.info("generate_recommendations_stub", parameters=parameters)
        
        # TODO: Implement in task 8 (recommendation engine)
        return {
            "status": "success",
            "recommendations": [],
            "summary": {
                "total_recommendations": 0,
                "high_priority": 0,
                "medium_priority": 0,
            },
            "message": "Recommendation generation not yet implemented (task 8)",
        }

    async def _export_report(self, parameters: dict, context: dict) -> dict:
        """导出报表
        
        Exports report in specified format (CSV, PDF).
        
        Args:
            parameters: {
                "report_type": "daily" | "weekly" | "monthly",
                "date_range": {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"},
                "format": "csv" | "pdf",
                "include_charts": bool
            }
            context: {"user_id": str, "session_id": str}
            
        Returns:
            {
                "status": "success",
                "download_url": str,
                "expires_at": str,
                "file_size": str,
                "message": "报表已导出"
            }
            
        Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
        """
        logger.info("export_report_stub", parameters=parameters)
        
        # TODO: Implement in task 11 (report exporters)
        return {
            "status": "success",
            "download_url": "https://example.com/report.pdf",
            "expires_at": "2024-11-29T00:00:00Z",
            "file_size": "0 MB",
            "message": "Report export not yet implemented (task 11)",
        }

    async def _get_metrics_summary(self, parameters: dict, context: dict) -> dict:
        """获取指标摘要
        
        Aggregates metrics across platforms and entities.
        
        Args:
            parameters: {
                "date_range": {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"},
                "group_by": "platform" | "campaign" | "date"
            }
            context: {"user_id": str, "session_id": str}
            
        Returns:
            {
                "status": "success",
                "summary": {
                    "total": {...},
                    "by_platform": {...}
                }
            }
            
        Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
        """
        logger.info("get_metrics_summary", parameters=parameters, context=context)
        
        try:
            # Get date range
            date_range = parameters.get("date_range", {})
            if not date_range:
                return {
                    "status": "error",
                    "message": "date_range is required",
                }
            
            # Fetch metrics from MCP
            logger.info("fetching_metrics_for_summary", date_range=date_range)
            
            try:
                mcp_result = await self.mcp_client.call_tool(
                    "get_metrics",
                    {
                        "user_id": context["user_id"],
                        "date_range": date_range,
                    },
                )
            except MCPError as e:
                logger.error("mcp_get_metrics_failed", error=str(e))
                return {
                    "status": "error",
                    "message": f"Failed to fetch metrics: {str(e)}",
                }
            
            # Extract metrics list from MCP response
            metrics_list = mcp_result.get("metrics", [])
            
            if not metrics_list:
                logger.warning("no_metrics_found", date_range=date_range)
                return {
                    "status": "success",
                    "summary": {
                        "total": {
                            "spend": 0.0,
                            "revenue": 0.0,
                            "roas": 0.0,
                            "conversions": 0,
                            "cpa": 0.0,
                        },
                        "by_platform": {},
                    },
                    "message": "No metrics found for the specified date range",
                }
            
            # Aggregate by platform
            aggregated = await self.data_aggregator.aggregate_by_platform(metrics_list)
            
            logger.info(
                "metrics_summary_complete",
                total_spend=aggregated["total"]["spend"],
                platforms=list(aggregated["by_platform"].keys()),
            )
            
            return {
                "status": "success",
                "summary": aggregated,
                "message": "Metrics summary generated successfully",
            }
            
        except ValueError as e:
            # Data consistency error
            logger.error("data_consistency_error", error=str(e))
            return {
                "status": "error",
                "message": f"Data consistency error: {str(e)}",
            }
        except Exception as e:
            logger.error("get_metrics_summary_error", error=str(e), exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to generate metrics summary: {str(e)}",
            }
