"""
AI Analyzer for generating AI-powered insights using Gemini 2.5 Pro.

This module provides the AIAnalyzer class for generating intelligent insights
from ad performance data using Google's Gemini AI model.

Requirements: 3.4
"""

import json
import structlog
from pydantic import BaseModel

from app.services.gemini_client import GeminiClient, GeminiError
from ..models import AIAnalysis, PeriodMetrics, MetricChange

logger = structlog.get_logger(__name__)


class AIInsightsResponse(BaseModel):
    """Structured response for AI insights."""
    key_insights: list[str]
    trends: dict[str, str]


class AIAnalyzer:
    """AI 分析器
    
    Uses Gemini 2.5 Pro to generate intelligent insights from ad performance data.
    
    Features:
    - Analyzes metrics and generates key insights
    - Identifies trends (improving, declining, stable)
    - Provides actionable recommendations
    - Handles AI errors gracefully with fallback responses
    
    Requirements: 3.4
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize AIAnalyzer.
        
        Args:
            gemini_client: Optional Gemini client instance
        """
        self.gemini_client = gemini_client or GeminiClient()
        logger.info("ai_analyzer_initialized")

    async def analyze_metrics(
        self,
        current_period: PeriodMetrics,
        previous_period: PeriodMetrics,
        changes: MetricChange,
        entity_name: str | None = None,
    ) -> AIAnalysis:
        """
        使用 AI 分析指标并生成洞察
        
        Analyzes metrics using Gemini 2.5 Pro and generates insights.
        
        Args:
            current_period: Current period metrics
            previous_period: Previous period metrics
            changes: Calculated metric changes
            entity_name: Optional entity name for context
            
        Returns:
            AIAnalysis with key_insights and trends
            
        Requirements: 3.4
        """
        log = logger.bind(
            entity_name=entity_name,
            current_roas=current_period.roas,
            current_spend=current_period.spend,
        )
        log.info("analyze_metrics_start")
        
        try:
            # Build prompt for Gemini
            prompt = self._build_analysis_prompt(
                current_period=current_period,
                previous_period=previous_period,
                changes=changes,
                entity_name=entity_name,
            )
            
            # Try structured output first
            try:
                result = await self.gemini_client.structured_output(
                    messages=[{"role": "user", "content": prompt}],
                    schema=AIInsightsResponse,
                    temperature=0.3,
                )
                
                analysis = AIAnalysis(
                    key_insights=result.key_insights,
                    trends=result.trends,
                )
                
            except Exception as e:
                # Fallback to regular completion with JSON parsing
                log.warning("structured_output_failed", error=str(e))
                
                response = await self.gemini_client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )
                
                analysis = self._parse_ai_response(response, current_period, changes)
            
            log.info(
                "analyze_metrics_complete",
                insights_count=len(analysis.key_insights),
                trends=analysis.trends,
            )
            
            return analysis
            
        except GeminiError as e:
            log.error("gemini_error", error=str(e))
            # Return fallback analysis
            return self._generate_fallback_analysis(current_period, changes)
        except Exception as e:
            log.error("analyze_metrics_error", error=str(e), exc_info=True)
            return self._generate_fallback_analysis(current_period, changes)

    def _build_analysis_prompt(
        self,
        current_period: PeriodMetrics,
        previous_period: PeriodMetrics,
        changes: MetricChange,
        entity_name: str | None = None,
    ) -> str:
        """
        Build prompt for AI analysis.
        
        Args:
            current_period: Current period metrics
            previous_period: Previous period metrics
            changes: Calculated changes
            entity_name: Optional entity name
            
        Returns:
            Formatted prompt string
        """
        entity_context = f"实体名称：{entity_name}\n" if entity_name else ""
        
        return f"""分析以下广告数据并提供洞察：

{entity_context}当前周期数据：
- 花费：${current_period.spend:.2f}
- 收入：${current_period.revenue:.2f}
- ROAS：{current_period.roas:.2f}
- 转化数：{current_period.conversions}
- CPA：${current_period.cpa:.2f}

上一周期数据：
- 花费：${previous_period.spend:.2f}
- 收入：${previous_period.revenue:.2f}
- ROAS：{previous_period.roas:.2f}
- 转化数：{previous_period.conversions}
- CPA：${previous_period.cpa:.2f}

变化情况：
- 花费变化：{changes.spend}
- 收入变化：{changes.revenue}
- ROAS 变化：{changes.roas}
- 转化变化：{changes.conversions}
- CPA 变化：{changes.cpa}

请提供：
1. 3-5 条关键洞察（简洁明了，每条不超过 50 字）
2. 趋势分析（上升/下降/稳定）

以 JSON 格式返回：
{{
  "key_insights": ["洞察1", "洞察2", "洞察3"],
  "trends": {{
    "roas_trend": "declining|stable|improving",
    "spend_trend": "declining|stable|increasing",
    "conversion_trend": "declining|stable|improving",
    "cpa_trend": "declining|stable|increasing"
  }}
}}

只返回 JSON，不要其他内容。"""

    def _parse_ai_response(
        self,
        response: str,
        current_period: PeriodMetrics,
        changes: MetricChange,
    ) -> AIAnalysis:
        """
        Parse AI response and extract insights.
        
        Args:
            response: Raw AI response text
            current_period: Current period metrics for fallback
            changes: Changes for fallback
            
        Returns:
            AIAnalysis with parsed or fallback data
        """
        try:
            # Try to extract JSON from response
            # Handle cases where response might have markdown code blocks
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            data = json.loads(json_str.strip())
            
            return AIAnalysis(
                key_insights=data.get("key_insights", []),
                trends=data.get("trends", {}),
            )
            
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.warning("ai_response_parse_failed", error=str(e), response=response[:200])
            return self._generate_fallback_analysis(current_period, changes)

    def _generate_fallback_analysis(
        self,
        current_period: PeriodMetrics,
        changes: MetricChange,
    ) -> AIAnalysis:
        """
        Generate fallback analysis when AI fails.
        
        Args:
            current_period: Current period metrics
            changes: Calculated changes
            
        Returns:
            AIAnalysis with basic insights
        """
        insights = [
            f"当前 ROAS {current_period.roas:.2f}",
            f"总花费 ${current_period.spend:.2f}",
            f"总收入 ${current_period.revenue:.2f}",
        ]
        
        # Add change-based insights
        roas_change = self._parse_percentage(changes.roas)
        if roas_change is not None:
            if roas_change > 0:
                insights.append(f"ROAS 上涨 {roas_change:.1f}%")
            elif roas_change < 0:
                insights.append(f"ROAS 下降 {abs(roas_change):.1f}%")
        
        trends = {
            "roas_trend": self._determine_trend(changes.roas),
            "spend_trend": self._determine_trend(changes.spend),
            "conversion_trend": self._determine_trend(changes.conversions),
            "cpa_trend": self._determine_trend(changes.cpa),
        }
        
        return AIAnalysis(
            key_insights=insights[:5],  # Limit to 5 insights
            trends=trends,
        )

    def _parse_percentage(self, change_str: str) -> float | None:
        """Parse percentage string to float."""
        if change_str == "N/A":
            return None
        try:
            return float(change_str.replace("%", ""))
        except ValueError:
            return None

    def _determine_trend(self, change_str: str) -> str:
        """
        Determine trend from change percentage string.
        
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

    async def generate_entity_insights(
        self,
        entity_type: str,
        entity_name: str,
        metrics: dict,
        context: str | None = None,
    ) -> list[str]:
        """
        Generate insights for a specific entity.
        
        Args:
            entity_type: Type of entity (campaign, adset, ad)
            entity_name: Entity name
            metrics: Entity metrics dict
            context: Optional additional context
            
        Returns:
            List of insight strings
        """
        log = logger.bind(
            entity_type=entity_type,
            entity_name=entity_name,
        )
        log.info("generate_entity_insights_start")
        
        try:
            prompt = f"""为以下广告{entity_type}生成 3 条简短洞察：

名称：{entity_name}
指标：
- 花费：${metrics.get('spend', 0):.2f}
- 收入：${metrics.get('revenue', 0):.2f}
- ROAS：{metrics.get('roas', 0):.2f}
- 转化数：{metrics.get('conversions', 0)}
- CPA：${metrics.get('cpa', 0):.2f}
- CTR：{metrics.get('ctr', 0):.4f}

{f'额外上下文：{context}' if context else ''}

请返回 3 条简短洞察，每条不超过 30 字，以 JSON 数组格式返回：
["洞察1", "洞察2", "洞察3"]

只返回 JSON 数组，不要其他内容。"""

            response = await self.gemini_client.fast_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            
            # Parse response
            try:
                insights = json.loads(response.strip())
                if isinstance(insights, list):
                    return insights[:3]
            except json.JSONDecodeError:
                pass
            
            # Fallback
            return [
                f"ROAS {metrics.get('roas', 0):.2f}",
                f"CPA ${metrics.get('cpa', 0):.2f}",
                f"转化数 {metrics.get('conversions', 0)}",
            ]
            
        except Exception as e:
            log.error("generate_entity_insights_error", error=str(e))
            return [
                f"ROAS {metrics.get('roas', 0):.2f}",
                f"CPA ${metrics.get('cpa', 0):.2f}",
            ]
