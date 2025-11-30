"""
Performance Analyzer for analyzing ad performance with period comparison.

This module provides the PerformanceAnalyzer class for analyzing entity performance,
calculating period metrics, computing percentage changes, and generating insights.

Requirements: 3.1, 3.2, 3.3
"""

import structlog
from datetime import datetime, timedelta

from ..models import (
    PerformanceAnalysis,
    PeriodMetrics,
    MetricChange,
)

logger = structlog.get_logger(__name__)


class PerformanceAnalyzer:
    """广告表现分析器
    
    Analyzes ad performance by:
    - Calculating period metrics (spend, revenue, ROAS, conversions, CPA)
    - Comparing current period with previous period
    - Computing percentage changes
    - Formatting changes as percentage strings
    
    Requirements: 3.1, 3.2, 3.3
    """

    def __init__(self):
        """Initialize PerformanceAnalyzer."""
        logger.info("performance_analyzer_initialized")

    async def analyze_entity(
        self,
        entity_type: str,
        entity_id: str,
        entity_name: str,
        current_data: list[dict],
        historical_data: list[dict],
    ) -> PerformanceAnalysis:
        """
        分析单个实体的表现
        
        Analyzes performance of a single entity by comparing current and previous periods.
        
        Args:
            entity_type: Type of entity (campaign, adset, ad)
            entity_id: Entity ID
            entity_name: Entity name
            current_data: List of metrics for current period
            historical_data: List of metrics for previous period
            
        Returns:
            PerformanceAnalysis with current_period, previous_period, changes, insights
            
        Requirements: 3.1, 3.2, 3.3
        """
        log = logger.bind(
            entity_type=entity_type,
            entity_id=entity_id,
            current_data_count=len(current_data),
            historical_data_count=len(historical_data),
        )
        log.info("analyze_entity_start")
        
        # Calculate period metrics
        current_period = self._calculate_period_metrics(current_data)
        previous_period = self._calculate_period_metrics(historical_data)
        
        # Calculate changes
        changes = self._calculate_changes(current_period, previous_period)
        
        # Generate basic insights (AI insights handled separately)
        insights = self._generate_basic_insights(
            entity_name=entity_name,
            current_period=current_period,
            previous_period=previous_period,
            changes=changes,
        )
        
        log.info(
            "analyze_entity_complete",
            current_spend=current_period.spend,
            current_roas=current_period.roas,
            insights_count=len(insights),
        )
        
        return PerformanceAnalysis(
            entity_id=entity_id,
            entity_name=entity_name,
            current_period=current_period,
            previous_period=previous_period,
            changes=changes,
            insights=insights,
        )

    def _calculate_period_metrics(self, data: list[dict]) -> PeriodMetrics:
        """
        Calculate aggregated metrics for a period.
        
        Args:
            data: List of metric dicts for the period
            
        Returns:
            PeriodMetrics with aggregated values
        """
        if not data:
            return PeriodMetrics(
                spend=0.0,
                revenue=0.0,
                roas=0.0,
                conversions=0,
                cpa=0.0,
            )
        
        # Aggregate metrics
        total_spend = sum(float(d.get("spend", 0)) for d in data)
        total_revenue = sum(float(d.get("revenue", 0)) for d in data)
        total_conversions = sum(int(d.get("conversions", 0)) for d in data)
        
        # Calculate derived metrics
        roas = total_revenue / total_spend if total_spend > 0 else 0.0
        cpa = total_spend / total_conversions if total_conversions > 0 else 0.0
        
        return PeriodMetrics(
            spend=total_spend,
            revenue=total_revenue,
            roas=roas,
            conversions=total_conversions,
            cpa=cpa,
        )

    def _calculate_changes(
        self,
        current: PeriodMetrics,
        previous: PeriodMetrics,
    ) -> MetricChange:
        """
        Calculate percentage changes between periods.
        
        Args:
            current: Current period metrics
            previous: Previous period metrics
            
        Returns:
            MetricChange with formatted percentage strings
            
        Requirements: 3.3
        """
        return MetricChange(
            spend=self._format_percentage_change(current.spend, previous.spend),
            revenue=self._format_percentage_change(current.revenue, previous.revenue),
            roas=self._format_percentage_change(current.roas, previous.roas),
            conversions=self._format_percentage_change(
                float(current.conversions), float(previous.conversions)
            ),
            cpa=self._format_percentage_change(current.cpa, previous.cpa),
        )

    def _format_percentage_change(
        self,
        current_value: float,
        previous_value: float,
    ) -> str:
        """
        Format percentage change as string.
        
        Args:
            current_value: Current period value
            previous_value: Previous period value
            
        Returns:
            Formatted string like "+4.2%" or "-10.5%" or "N/A"
        """
        if previous_value == 0:
            if current_value == 0:
                return "0.0%"
            return "N/A"
        
        change_pct = ((current_value - previous_value) / previous_value) * 100
        return f"{change_pct:+.1f}%"

    def _generate_basic_insights(
        self,
        entity_name: str,
        current_period: PeriodMetrics,
        previous_period: PeriodMetrics,
        changes: MetricChange,
    ) -> list[str]:
        """
        Generate basic insights based on metric changes.
        
        Args:
            entity_name: Entity name
            current_period: Current period metrics
            previous_period: Previous period metrics
            changes: Calculated changes
            
        Returns:
            List of insight strings
        """
        insights = []
        
        # ROAS insight
        roas_change = self._parse_percentage(changes.roas)
        if roas_change is not None:
            if roas_change > 10:
                insights.append(
                    f"ROAS 上涨 {roas_change:.1f}%，表现优秀"
                )
            elif roas_change < -10:
                insights.append(
                    f"ROAS 下降 {abs(roas_change):.1f}%，需要关注"
                )
        
        # CPA insight
        cpa_change = self._parse_percentage(changes.cpa)
        if cpa_change is not None:
            if cpa_change > 20:
                insights.append(
                    f"CPA 上涨 {cpa_change:.1f}%，成本控制需要优化"
                )
            elif cpa_change < -20:
                insights.append(
                    f"CPA 下降 {abs(cpa_change):.1f}%，成本效率提升"
                )
        
        # Spend insight
        spend_change = self._parse_percentage(changes.spend)
        if spend_change is not None:
            if spend_change > 30:
                insights.append(
                    f"花费增加 {spend_change:.1f}%，请确认预算调整"
                )
        
        # Conversions insight
        conv_change = self._parse_percentage(changes.conversions)
        if conv_change is not None:
            if conv_change > 20:
                insights.append(
                    f"转化数增加 {conv_change:.1f}%，效果提升明显"
                )
            elif conv_change < -20:
                insights.append(
                    f"转化数下降 {abs(conv_change):.1f}%，建议检查广告设置"
                )
        
        # Add summary if no specific insights
        if not insights:
            insights.append(
                f"当前 ROAS {current_period.roas:.2f}，"
                f"CPA ${current_period.cpa:.2f}"
            )
        
        return insights

    def _parse_percentage(self, change_str: str) -> float | None:
        """
        Parse percentage string to float.
        
        Args:
            change_str: Percentage string like "+4.2%" or "-10.5%"
            
        Returns:
            Float value or None if N/A
        """
        if change_str == "N/A":
            return None
        
        try:
            return float(change_str.replace("%", ""))
        except ValueError:
            return None

    @staticmethod
    def get_comparison_date_range(
        start_date: str,
        end_date: str,
        comparison_period: str,
    ) -> tuple[str, str]:
        """
        Calculate comparison period date range.
        
        Args:
            start_date: Current period start date (YYYY-MM-DD)
            end_date: Current period end date (YYYY-MM-DD)
            comparison_period: "previous_week" or "previous_month"
            
        Returns:
            Tuple of (comparison_start, comparison_end) dates
        """
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        period_days = (end - start).days + 1
        
        if comparison_period == "previous_week":
            # Previous week (7 days before)
            comp_end = start - timedelta(days=1)
            comp_start = comp_end - timedelta(days=period_days - 1)
        elif comparison_period == "previous_month":
            # Previous month (30 days before)
            comp_end = start - timedelta(days=1)
            comp_start = comp_end - timedelta(days=29)
        else:
            # Default: same period length before
            comp_end = start - timedelta(days=1)
            comp_start = comp_end - timedelta(days=period_days - 1)
        
        return comp_start.date().isoformat(), comp_end.date().isoformat()
