"""
Recommendation engine for generating optimization recommendations.
"""

from typing import Any
from datetime import date, timedelta

from ..models import Recommendation, RecommendationTarget, ExpectedImpact


class RecommendationEngine:
    """
    Generates optimization recommendations based on performance metrics.
    
    Identifies underperforming and high-performing entities, detects creative
    fatigue, and generates actionable recommendations with confidence scores.
    """
    
    def __init__(self, mcp_client: Any = None):
        """
        Initialize the recommendation engine.
        
        Args:
            mcp_client: MCP client for fetching historical data
        """
        self.mcp_client = mcp_client
        self.min_days_for_trend = 3  # Minimum days to establish a trend
    
    async def generate(
        self,
        metrics_data: dict,
        optimization_goal: str = "maximize_roas",
        constraints: dict | None = None
    ) -> list[Recommendation]:
        """
        Generate optimization recommendations.
        
        Args:
            metrics_data: Current metrics data with campaigns, adsets, ads
            optimization_goal: Optimization objective (maximize_roas, minimize_cpa, etc.)
            constraints: Optional constraints (budget_constraint, min_roas_threshold, etc.)
        
        Returns:
            List of recommendations sorted by priority
        """
        if constraints is None:
            constraints = {}
        
        recommendations = []
        
        # Get thresholds from constraints
        min_roas_threshold = constraints.get("min_roas_threshold", 2.0)
        high_roas_multiplier = 1.5
        ctr_decline_threshold = 0.3  # 30% decline
        
        # Identify underperforming entities
        underperforming = await self.identify_underperforming(
            metrics_data.get("adsets", []),
            threshold=min_roas_threshold
        )
        
        for entity in underperforming:
            recommendations.append(Recommendation(
                priority="high",
                action="pause_adset",
                target=RecommendationTarget(
                    type="adset",
                    id=entity["entity_id"],
                    name=entity["name"]
                ),
                reason=f"ROAS {entity['roas']:.2f} below target {min_roas_threshold}, "
                       f"consistently underperforming for {entity.get('days_underperforming', 3)}+ days",
                expected_impact=ExpectedImpact(
                    spend_reduction=entity["spend"],
                    roas_improvement="+0.3"
                ),
                confidence=self._calculate_confidence(entity, "pause")
            ))
        
        # Identify high-performing entities
        high_performing = await self.identify_high_performing(
            metrics_data.get("adsets", []),
            threshold=min_roas_threshold * high_roas_multiplier
        )
        
        for entity in high_performing:
            budget_increase = entity["spend"] * 0.2  # 20% increase
            revenue_increase = budget_increase * entity["roas"]
            
            recommendations.append(Recommendation(
                priority="high",
                action="increase_budget",
                target=RecommendationTarget(
                    type="adset",
                    id=entity["entity_id"],
                    name=entity["name"]
                ),
                reason=f"ROAS {entity['roas']:.2f} exceeds target, strong performance with growth potential",
                expected_impact=ExpectedImpact(
                    spend_increase=budget_increase,
                    revenue_increase=revenue_increase
                ),
                confidence=self._calculate_confidence(entity, "increase_budget")
            ))
        
        # Detect creative fatigue
        creative_fatigue = await self.detect_creative_fatigue(
            metrics_data.get("ads", []),
            decline_threshold=ctr_decline_threshold
        )
        
        for entity in creative_fatigue:
            recommendations.append(Recommendation(
                priority="medium",
                action="refresh_creative",
                target=RecommendationTarget(
                    type="ad",
                    id=entity["entity_id"],
                    name=entity["name"]
                ),
                reason=f"CTR declined {entity['ctr_decline_pct']:.1f}%, indicating creative fatigue",
                expected_impact=ExpectedImpact(
                    ctr_improvement="+0.5%",
                    roas_improvement="+0.2"
                ),
                confidence=self._calculate_confidence(entity, "refresh_creative")
            ))
        
        # Sort by priority (high > medium > low)
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda r: priority_order[r.priority])
        
        return recommendations
    
    async def identify_underperforming(
        self,
        entities: list[dict],
        threshold: float
    ) -> list[dict]:
        """
        Identify underperforming entities based on ROAS threshold.
        
        Args:
            entities: List of entity metrics (adsets)
            threshold: Minimum acceptable ROAS
        
        Returns:
            List of underperforming entities with consistent poor performance
        """
        underperforming = []
        
        for entity in entities:
            roas = entity.get("roas", 0)
            
            # Check if ROAS is below threshold
            if roas < threshold:
                # Check for consistent underperformance
                is_consistent = await self._check_consistent_underperformance(
                    entity["entity_id"],
                    threshold
                )
                
                if is_consistent:
                    entity["days_underperforming"] = self.min_days_for_trend
                    underperforming.append(entity)
        
        return underperforming
    
    async def identify_high_performing(
        self,
        entities: list[dict],
        threshold: float
    ) -> list[dict]:
        """
        Identify high-performing entities that could benefit from increased budget.
        
        Args:
            entities: List of entity metrics (adsets)
            threshold: ROAS threshold for high performance (typically 1.5x min threshold)
        
        Returns:
            List of high-performing entities
        """
        high_performing = []
        
        for entity in entities:
            roas = entity.get("roas", 0)
            
            # Check if ROAS exceeds high performance threshold
            if roas >= threshold:
                high_performing.append(entity)
        
        return high_performing
    
    async def detect_creative_fatigue(
        self,
        entities: list[dict],
        decline_threshold: float = 0.3
    ) -> list[dict]:
        """
        Detect creative fatigue by analyzing CTR trends.
        
        Args:
            entities: List of ad metrics
            decline_threshold: Minimum CTR decline percentage to flag (default 30%)
        
        Returns:
            List of ads showing creative fatigue
        """
        fatigued = []
        
        for entity in entities:
            # Get historical CTR data
            ctr_trend = await self._get_ctr_trend(entity["entity_id"])
            
            # Need at least min_days_for_trend + 1 data points (baseline + recent)
            if ctr_trend and len(ctr_trend) > self.min_days_for_trend:
                # Calculate decline
                recent_ctr = ctr_trend[-1]
                baseline_ctr = sum(ctr_trend[:self.min_days_for_trend]) / self.min_days_for_trend
                
                if baseline_ctr > 0:
                    decline = (baseline_ctr - recent_ctr) / baseline_ctr
                    
                    if decline >= decline_threshold:
                        entity["ctr_decline_pct"] = decline * 100
                        entity["baseline_ctr"] = baseline_ctr
                        entity["recent_ctr"] = recent_ctr
                        fatigued.append(entity)
        
        return fatigued
    
    async def _check_consistent_underperformance(
        self,
        entity_id: str,
        threshold: float
    ) -> bool:
        """
        Check if an entity has been consistently underperforming.
        
        Args:
            entity_id: Entity identifier
            threshold: ROAS threshold
        
        Returns:
            True if consistently underperforming for min_days_for_trend days
        """
        if not self.mcp_client:
            # If no MCP client, assume consistent (for testing)
            return True
        
        # Get historical performance
        historical = await self._get_historical_performance(entity_id)
        
        if len(historical) < self.min_days_for_trend:
            return False
        
        # Check last N days
        recent = historical[-self.min_days_for_trend:]
        return all(day.get("roas", 0) < threshold for day in recent)
    
    async def _get_historical_performance(
        self,
        entity_id: str,
        days: int = 7
    ) -> list[dict]:
        """
        Get historical performance data for an entity.
        
        Args:
            entity_id: Entity identifier
            days: Number of days to retrieve
        
        Returns:
            List of daily metrics
        """
        if not self.mcp_client:
            return []
        
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        try:
            # Call MCP to get historical metrics
            result = await self.mcp_client.call_tool(
                "get_metrics",
                {
                    "entity_id": entity_id,
                    "date_range": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    }
                }
            )
            
            return result.get("metrics", [])
        except Exception:
            return []
    
    async def _get_ctr_trend(self, entity_id: str) -> list[float]:
        """
        Get CTR trend for an ad.
        
        Args:
            entity_id: Ad identifier
        
        Returns:
            List of CTR values over time
        """
        historical = await self._get_historical_performance(entity_id)
        return [day.get("ctr", 0) for day in historical]
    
    def _calculate_confidence(
        self,
        entity: dict,
        action: str
    ) -> float:
        """
        Calculate confidence score for a recommendation.
        
        Args:
            entity: Entity metrics
            action: Recommended action
        
        Returns:
            Confidence score between 0 and 1
        """
        # Base confidence
        confidence = 0.7
        
        # Adjust based on data quality
        if entity.get("conversions", 0) > 10:
            confidence += 0.1
        
        if entity.get("spend", 0) > 100:
            confidence += 0.05
        
        # Adjust based on action type
        if action == "pause":
            # Higher confidence for pause if ROAS is very low
            roas = entity.get("roas", 0)
            if roas < 1.0:
                confidence += 0.15
        elif action == "increase_budget":
            # Higher confidence if ROAS is very high
            roas = entity.get("roas", 0)
            if roas > 4.0:
                confidence += 0.13
        elif action == "refresh_creative":
            # Moderate confidence for creative refresh
            confidence += 0.05
        
        # Cap at 1.0
        return min(confidence, 1.0)
