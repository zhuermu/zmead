"""Performance Agent - Ad performance reports and analytics.

This agent handles:
- Fetching ad performance data
- Generating daily reports
- Detecting anomalies
- Generating optimization recommendations

Requirements: 需求 8 (Ad Performance), ad-performance/requirements.md
"""

from typing import Any

import structlog

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.services.gemini3_client import FunctionDeclaration, get_gemini3_client

logger = structlog.get_logger(__name__)

# Credit costs
CREDIT_PER_REPORT = 1.0
CREDIT_PER_ANALYSIS = 0.5


class PerformanceAgent(BaseAgent):
    """Agent for ad performance analytics.

    Supported actions:
    - get_report: Get ad performance report
    - analyze_performance: Analyze campaign/adset/ad performance
    - detect_anomalies: Detect performance anomalies
    - generate_recommendations: Generate optimization recommendations
    - get_metrics_summary: Get metrics summary across platforms
    """

    name = "performance_agent"
    description = """广告投放报表和分析助手。可以：
- 获取广告报表数据（按 Campaign、Adset、Ad 层级）
- 分析广告表现（对比历史数据，识别趋势）
- 检测异常（CPA 突增、ROAS 下降等）
- 生成优化建议（暂停低效广告、加预算等）
- 获取多平台数据汇总

调用示例：
- 获取报表：action="get_report", params={"platform": "meta", "date_range": "last_7_days"}
- 分析表现：action="analyze_performance", params={"campaign_id": "123", "comparison": "previous_week"}
- 检测异常：action="detect_anomalies", params={"metrics": ["roas", "cpa"]}
- 优化建议：action="generate_recommendations", params={"goal": "maximize_roas"}"""

    def get_tool_declaration(self) -> FunctionDeclaration:
        """Get function declaration for Gemini function calling."""
        return FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "get_report",
                            "analyze_performance",
                            "detect_anomalies",
                            "generate_recommendations",
                            "get_metrics_summary",
                        ],
                        "description": "要执行的操作",
                    },
                    "params": {
                        "type": "object",
                        "properties": {
                            "platform": {
                                "type": "string",
                                "enum": ["meta", "tiktok", "google", "all"],
                                "description": "广告平台",
                                "default": "all",
                            },
                            "date_range": {
                                "type": "string",
                                "enum": ["today", "yesterday", "last_7_days", "last_30_days", "this_month"],
                                "description": "日期范围",
                                "default": "last_7_days",
                            },
                            "start_date": {
                                "type": "string",
                                "description": "开始日期 (YYYY-MM-DD)",
                            },
                            "end_date": {
                                "type": "string",
                                "description": "结束日期 (YYYY-MM-DD)",
                            },
                            "campaign_id": {
                                "type": "string",
                                "description": "Campaign ID（用于具体分析）",
                            },
                            "adset_id": {
                                "type": "string",
                                "description": "Adset ID",
                            },
                            "ad_id": {
                                "type": "string",
                                "description": "Ad ID",
                            },
                            "metrics": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "要检测的指标",
                                "default": ["roas", "cpa", "ctr"],
                            },
                            "comparison": {
                                "type": "string",
                                "enum": ["previous_day", "previous_week", "previous_month"],
                                "description": "对比周期",
                            },
                            "goal": {
                                "type": "string",
                                "enum": ["maximize_roas", "minimize_cpa", "maximize_conversions"],
                                "description": "优化目标",
                            },
                            "sensitivity": {
                                "type": "string",
                                "enum": ["low", "medium", "high"],
                                "description": "异常检测灵敏度",
                                "default": "medium",
                            },
                        },
                    },
                },
                "required": ["action"],
            },
        )

    async def execute(
        self,
        action: str,
        params: dict[str, Any],
        context: AgentContext,
    ) -> AgentResult:
        """Execute performance action."""
        log = logger.bind(
            user_id=context.user_id,
            session_id=context.session_id,
            agent=self.name,
            action=action,
        )
        log.info("performance_agent_execute")

        try:
            if action == "get_report":
                return await self._get_report(params, context)
            elif action == "analyze_performance":
                return await self._analyze_performance(params, context)
            elif action == "detect_anomalies":
                return await self._detect_anomalies(params, context)
            elif action == "generate_recommendations":
                return await self._generate_recommendations(params, context)
            elif action == "get_metrics_summary":
                return await self._get_metrics_summary(params, context)
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown action: {action}",
                )
        except Exception as e:
            log.error("performance_agent_error", error=str(e), exc_info=True)
            return AgentResult(
                success=False,
                error=str(e),
            )

    async def _get_report(
        self,
        params: dict[str, Any],
        context: AgentContext,
    ) -> AgentResult:
        """Get ad performance report."""
        log = logger.bind(user_id=context.user_id, action="get_report")

        platform = params.get("platform", "all")
        date_range = params.get("date_range", "last_7_days")

        log.info("get_report_start", platform=platform, date_range=date_range)

        # Convert date_range string to date dict
        from datetime import datetime, timedelta
        today = datetime.now().date()
        date_ranges = {
            "today": {"start_date": str(today), "end_date": str(today)},
            "yesterday": {"start_date": str(today - timedelta(days=1)), "end_date": str(today - timedelta(days=1))},
            "last_7_days": {"start_date": str(today - timedelta(days=7)), "end_date": str(today)},
            "last_30_days": {"start_date": str(today - timedelta(days=30)), "end_date": str(today)},
            "this_month": {"start_date": str(today.replace(day=1)), "end_date": str(today)},
        }
        date_range_dict = date_ranges.get(date_range, date_ranges["last_7_days"])

        try:
            # Call MCP to get actual data from backend
            from app.agents.mcp_integration import get_agent_mcp_client
            mcp_client = get_agent_mcp_client()

            report_data = await mcp_client.get_reports(
                user_id=context.user_id,
                platform=platform if platform != "all" else None,
                date_range=date_range_dict,
            )

            # Process and return data
            summary = report_data.get("summary", {})
            campaigns = report_data.get("campaigns", [])

            return AgentResult(
                success=True,
                data={
                    "platform": platform,
                    "date_range": date_range,
                    "summary": summary,
                    "campaigns": campaigns,
                },
                credit_consumed=CREDIT_PER_REPORT,
                message=f"获取了 {platform} 平台 {date_range} 的广告报表。总花费 ${summary.get('total_spend', 0):.2f}，ROAS {summary.get('overall_roas', 0):.1f}。",
            )

        except Exception as e:
            log.warning("mcp_get_reports_failed", error=str(e))
            # Fallback to mock data for demo
            mock_data = {
                "platform": platform,
                "date_range": date_range,
                "summary": {
                    "total_spend": 1500.00,
                    "total_revenue": 4500.00,
                    "overall_roas": 3.0,
                    "total_conversions": 150,
                    "avg_cpa": 10.00,
                    "total_impressions": 50000,
                    "total_clicks": 2500,
                    "avg_ctr": 5.0,
                },
                "campaigns": [
                    {
                        "campaign_id": "camp_001",
                        "name": "Summer Sale 2024",
                        "status": "active",
                        "spend": 800.00,
                        "revenue": 2800.00,
                        "roas": 3.5,
                        "conversions": 85,
                        "cpa": 9.41,
                    },
                    {
                        "campaign_id": "camp_002",
                        "name": "Brand Awareness",
                        "status": "active",
                        "spend": 500.00,
                        "revenue": 1200.00,
                        "roas": 2.4,
                        "conversions": 45,
                        "cpa": 11.11,
                    },
                ],
            }

            return AgentResult(
                success=True,
                data=mock_data,
                credit_consumed=CREDIT_PER_REPORT,
                message=f"获取了 {platform} 平台 {date_range} 的广告报表（示例数据）。",
            )

    async def _analyze_performance(
        self,
        params: dict[str, Any],
        context: AgentContext,
    ) -> AgentResult:
        """Analyze specific campaign/adset/ad performance."""
        log = logger.bind(user_id=context.user_id, action="analyze_performance")

        campaign_id = params.get("campaign_id")
        comparison = params.get("comparison", "previous_week")

        log.info("analyze_performance_start", campaign_id=campaign_id)

        # TODO: Fetch real data and use Gemini for analysis
        gemini = get_gemini3_client()

        # Mock analysis
        analysis = {
            "entity_id": campaign_id or "all",
            "current_period": {
                "spend": 500.00,
                "revenue": 1500.00,
                "roas": 3.0,
                "conversions": 45,
                "cpa": 11.11,
            },
            "previous_period": {
                "spend": 480.00,
                "revenue": 1680.00,
                "roas": 3.5,
                "conversions": 48,
                "cpa": 10.00,
            },
            "changes": {
                "spend": "+4.2%",
                "revenue": "-10.7%",
                "roas": "-14.3%",
                "conversions": "-6.3%",
                "cpa": "+11.1%",
            },
            "insights": [
                "ROAS 下降 14.3%，主要由于转化率降低",
                "CPA 上涨 11.1%，建议检查素材疲劳度",
                "花费增加但收入减少，效率下降",
            ],
        }

        return AgentResult(
            success=True,
            data=analysis,
            credit_consumed=CREDIT_PER_ANALYSIS,
            message=f"分析完成。ROAS 较上周下降 14.3%，CPA 上涨 11.1%。建议检查素材疲劳度。",
        )

    async def _detect_anomalies(
        self,
        params: dict[str, Any],
        context: AgentContext,
    ) -> AgentResult:
        """Detect performance anomalies."""
        log = logger.bind(user_id=context.user_id, action="detect_anomalies")

        metrics = params.get("metrics", ["roas", "cpa", "ctr"])
        sensitivity = params.get("sensitivity", "medium")

        log.info("detect_anomalies_start", metrics=metrics)

        # TODO: Implement real anomaly detection
        anomalies = [
            {
                "metric": "cpa",
                "entity_type": "adset",
                "entity_id": "adset_789",
                "entity_name": "US 36-50",
                "current_value": 25.50,
                "expected_value": 12.00,
                "deviation": "+112.5%",
                "severity": "high",
                "recommendation": "暂停该 Adset 或降低预算",
            },
            {
                "metric": "roas",
                "entity_type": "campaign",
                "entity_id": "camp_002",
                "entity_name": "Brand Awareness",
                "current_value": 1.8,
                "expected_value": 2.8,
                "deviation": "-35.7%",
                "severity": "medium",
                "recommendation": "检查广告素材和受众定向",
            },
        ]

        return AgentResult(
            success=True,
            data={
                "anomalies": anomalies,
                "total_detected": len(anomalies),
            },
            credit_consumed=CREDIT_PER_ANALYSIS,
            message=f"检测到 {len(anomalies)} 个异常。其中 Adset 'US 36-50' 的 CPA 异常上涨 112.5%，建议暂停。",
        )

    async def _generate_recommendations(
        self,
        params: dict[str, Any],
        context: AgentContext,
    ) -> AgentResult:
        """Generate optimization recommendations."""
        log = logger.bind(user_id=context.user_id, action="generate_recommendations")

        goal = params.get("goal", "maximize_roas")

        log.info("generate_recommendations_start", goal=goal)

        # TODO: Use Gemini to generate intelligent recommendations
        recommendations = [
            {
                "priority": "high",
                "action": "pause_adset",
                "target": {
                    "type": "adset",
                    "id": "adset_789",
                    "name": "US 36-50",
                },
                "reason": "ROAS 1.2 低于目标 2.0，连续 3 天表现不佳",
                "expected_impact": {
                    "spend_reduction": 50.00,
                    "roas_improvement": "+0.3",
                },
                "confidence": 0.92,
            },
            {
                "priority": "high",
                "action": "increase_budget",
                "target": {
                    "type": "adset",
                    "id": "adset_456",
                    "name": "US 18-35",
                },
                "reason": "ROAS 4.5 远超目标，有扩展空间",
                "expected_impact": {
                    "spend_increase": 100.00,
                    "revenue_increase": 450.00,
                },
                "confidence": 0.88,
            },
            {
                "priority": "medium",
                "action": "refresh_creative",
                "target": {
                    "type": "ad",
                    "id": "ad_123",
                    "name": "Summer Ad 1",
                },
                "reason": "CTR 下降 30%，可能存在素材疲劳",
                "expected_impact": {
                    "ctr_improvement": "+0.5%",
                    "roas_improvement": "+0.2",
                },
                "confidence": 0.75,
            },
        ]

        return AgentResult(
            success=True,
            data={
                "recommendations": recommendations,
                "goal": goal,
                "summary": {
                    "total": len(recommendations),
                    "high_priority": 2,
                    "medium_priority": 1,
                    "expected_roas_improvement": "+0.5",
                },
            },
            credit_consumed=CREDIT_PER_ANALYSIS,
            message=f"生成了 {len(recommendations)} 条优化建议。建议暂停 Adset 'US 36-50' 并为 'US 18-35' 加预算。",
        )

    async def _get_metrics_summary(
        self,
        params: dict[str, Any],
        context: AgentContext,
    ) -> AgentResult:
        """Get metrics summary across platforms."""
        log = logger.bind(user_id=context.user_id, action="get_metrics_summary")

        date_range = params.get("date_range", "today")

        log.info("get_metrics_summary_start", date_range=date_range)

        # TODO: Get real data from MCP
        summary = {
            "date_range": date_range,
            "total": {
                "spend": 500.00,
                "revenue": 1350.00,
                "roas": 2.7,
                "conversions": 42,
                "cpa": 11.90,
            },
            "by_platform": {
                "meta": {
                    "spend": 300.00,
                    "revenue": 900.00,
                    "roas": 3.0,
                    "conversions": 28,
                },
                "tiktok": {
                    "spend": 150.00,
                    "revenue": 375.00,
                    "roas": 2.5,
                    "conversions": 12,
                },
                "google": {
                    "spend": 50.00,
                    "revenue": 75.00,
                    "roas": 1.5,
                    "conversions": 2,
                },
            },
        }

        return AgentResult(
            success=True,
            data=summary,
            credit_consumed=CREDIT_PER_REPORT,
            message=f"今日总花费 ${summary['total']['spend']:.2f}，收入 ${summary['total']['revenue']:.2f}，ROAS {summary['total']['roas']:.1f}。Meta 表现最佳 (ROAS 3.0)。",
        )


# Singleton instance
_performance_agent: PerformanceAgent | None = None


def get_performance_agent() -> PerformanceAgent:
    """Get or create PerformanceAgent singleton."""
    global _performance_agent
    if _performance_agent is None:
        _performance_agent = PerformanceAgent()
    return _performance_agent


# Tool declaration for registration
performance_agent_tool = get_performance_agent().get_tool_declaration()
