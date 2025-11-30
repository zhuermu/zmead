"""
Budget Optimizer for Campaign Automation.

This module implements budget optimization logic based on performance metrics.
It analyzes campaign performance and generates optimization recommendations
following predefined rules.

Optimization Rules:
1. ROAS > target * 1.5 → Increase budget 20%
2. CPA > target * 1.5 → Decrease budget 20%
3. No conversions for 3 days → Pause adset
4. Budget adjustment cap: Maximum 50% per change

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from app.core.errors import ErrorHandler
from app.modules.campaign_automation.models import OptimizationAction, OptimizationResult
from app.services.mcp_client import MCPClient, MCPError

logger = structlog.get_logger(__name__)


class BudgetOptimizer:
    """
    Budget Optimizer for campaign performance optimization.
    
    Analyzes adset performance data and generates optimization recommendations
    based on ROAS, CPA, and conversion metrics.
    """
    
    # Optimization thresholds
    ROAS_THRESHOLD_MULTIPLIER = 1.5  # ROAS must exceed target * 1.5
    CPA_THRESHOLD_MULTIPLIER = 1.5   # CPA must exceed target * 1.5
    NO_CONVERSION_DAYS = 3           # Days without conversions before pause
    
    # Budget adjustment factors
    BUDGET_INCREASE_FACTOR = 1.2     # Increase by 20%
    BUDGET_DECREASE_FACTOR = 0.8     # Decrease by 20%
    MAX_BUDGET_CHANGE_FACTOR = 1.5   # Maximum 50% change
    
    def __init__(self, mcp_client: MCPClient):
        """
        Initialize Budget Optimizer.
        
        Args:
            mcp_client: MCP client for fetching performance data
        """
        self.mcp_client = mcp_client
        self.error_handler = ErrorHandler()
    
    async def analyze_performance(
        self,
        campaign_id: str,
        target_metric: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Analyze campaign performance data.
        
        Fetches performance metrics from Web Platform and returns
        structured performance data for optimization analysis.
        
        Args:
            campaign_id: Campaign ID to analyze
            target_metric: Target metric for optimization ('roas' or 'cpa')
            context: Request context with user_id
        
        Returns:
            Performance data with adset-level metrics
        
        Requirements: 3.1
        """
        logger.info(
            "analyzing_campaign_performance",
            campaign_id=campaign_id,
            target_metric=target_metric,
            user_id=context.get("user_id"),
        )
        
        try:
            # Fetch performance data from Web Platform
            performance_data = await self._get_performance_data(
                campaign_id=campaign_id,
                context=context,
            )
            
            logger.info(
                "performance_analysis_complete",
                campaign_id=campaign_id,
                adset_count=len(performance_data.get("adsets", [])),
            )
            
            return performance_data
            
        except MCPError as e:
            logger.error(
                "mcp_error_analyzing_performance",
                campaign_id=campaign_id,
                error=str(e),
            )
            raise
        except Exception as e:
            logger.error(
                "error_analyzing_performance",
                campaign_id=campaign_id,
                error=str(e),
            )
            raise
    
    async def optimize_budget(
        self,
        campaign_id: str,
        optimization_strategy: str,
        target_metric: str,
        context: dict[str, Any],
    ) -> OptimizationResult:
        """
        Optimize campaign budget based on performance data.
        
        Applies optimization rules to generate budget adjustment recommendations:
        - ROAS > target * 1.5 → Increase budget 20%
        - CPA > target * 1.5 → Decrease budget 20%
        - No conversions for 3 days → Pause adset
        - Budget changes capped at 50%
        
        Args:
            campaign_id: Campaign ID to optimize
            optimization_strategy: Optimization strategy ('auto')
            target_metric: Target metric ('roas' or 'cpa')
            context: Request context with user_id
        
        Returns:
            OptimizationResult with list of optimization actions
        
        Requirements: 3.2, 3.3, 3.4, 3.5
        """
        logger.info(
            "optimizing_campaign_budget",
            campaign_id=campaign_id,
            strategy=optimization_strategy,
            target_metric=target_metric,
            user_id=context.get("user_id"),
        )
        
        try:
            # Get performance data
            performance_data = await self._get_performance_data(
                campaign_id=campaign_id,
                context=context,
            )
            
            # Generate optimization actions
            optimizations: list[OptimizationAction] = []
            
            for adset in performance_data.get("adsets", []):
                # Apply optimization rules
                actions = self._apply_optimization_rules(
                    adset=adset,
                    target_metric=target_metric,
                )
                optimizations.extend(actions)
            
            # Create result
            result = OptimizationResult(
                campaign_id=campaign_id,
                optimizations=optimizations,
                total_actions=len(optimizations),
                timestamp=datetime.now(timezone.utc),
            )
            
            logger.info(
                "budget_optimization_complete",
                campaign_id=campaign_id,
                total_actions=result.total_actions,
                actions=[opt.action for opt in optimizations],
            )
            
            return result
            
        except MCPError as e:
            logger.error(
                "mcp_error_optimizing_budget",
                campaign_id=campaign_id,
                error=str(e),
            )
            raise
        except Exception as e:
            logger.error(
                "error_optimizing_budget",
                campaign_id=campaign_id,
                error=str(e),
            )
            raise
    
    def _apply_optimization_rules(
        self,
        adset: dict[str, Any],
        target_metric: str,
    ) -> list[OptimizationAction]:
        """
        Apply optimization rules to a single adset.
        
        Rules:
        1. ROAS > target * 1.5 → Increase budget 20%
        2. CPA > target * 1.5 → Decrease budget 20%
        3. No conversions for 3 days → Pause adset
        4. Budget changes capped at 50%
        
        Args:
            adset: Adset performance data
            target_metric: Target metric ('roas' or 'cpa')
        
        Returns:
            List of optimization actions for this adset
        
        Requirements: 3.2, 3.3, 3.4
        """
        actions: list[OptimizationAction] = []
        
        adset_id = adset.get("id") or adset.get("adset_id")
        daily_budget = adset.get("daily_budget", 0)
        conversions = adset.get("conversions", 0)
        days_running = adset.get("days_running", 0)
        
        # Rule 3: No conversions for 3 days → Pause
        if conversions == 0 and days_running >= self.NO_CONVERSION_DAYS:
            actions.append(
                OptimizationAction(
                    adset_id=adset_id,
                    action="pause",
                    reason=f"连续 {self.NO_CONVERSION_DAYS} 天无转化",
                )
            )
            logger.info(
                "optimization_rule_pause",
                adset_id=adset_id,
                days_running=days_running,
            )
            return actions  # Don't apply other rules if pausing
        
        # Rule 1: ROAS optimization
        if target_metric == "roas":
            roas = adset.get("roas", 0)
            target_roas = adset.get("target_roas", 0)
            
            if target_roas > 0 and roas > target_roas * self.ROAS_THRESHOLD_MULTIPLIER:
                new_budget = daily_budget * self.BUDGET_INCREASE_FACTOR
                
                # Apply budget change cap
                new_budget = self._apply_budget_cap(daily_budget, new_budget)
                
                actions.append(
                    OptimizationAction(
                        adset_id=adset_id,
                        action="increase_budget",
                        old_budget=daily_budget,
                        new_budget=new_budget,
                        reason=(
                            f"ROAS {roas:.2f} 超过目标 {target_roas:.2f} 的 "
                            f"{self.ROAS_THRESHOLD_MULTIPLIER}x，表现优秀"
                        ),
                    )
                )
                logger.info(
                    "optimization_rule_increase_budget",
                    adset_id=adset_id,
                    roas=roas,
                    target_roas=target_roas,
                    old_budget=daily_budget,
                    new_budget=new_budget,
                )
        
        # Rule 2: CPA optimization
        elif target_metric == "cpa":
            cpa = adset.get("cpa", 0)
            target_cpa = adset.get("target_cpa", 0)
            
            if target_cpa > 0 and cpa > target_cpa * self.CPA_THRESHOLD_MULTIPLIER:
                new_budget = daily_budget * self.BUDGET_DECREASE_FACTOR
                
                # Apply budget change cap
                new_budget = self._apply_budget_cap(daily_budget, new_budget)
                
                actions.append(
                    OptimizationAction(
                        adset_id=adset_id,
                        action="decrease_budget",
                        old_budget=daily_budget,
                        new_budget=new_budget,
                        reason=(
                            f"CPA {cpa:.2f} 超过目标 {target_cpa:.2f} 的 "
                            f"{self.CPA_THRESHOLD_MULTIPLIER}x，需要优化"
                        ),
                    )
                )
                logger.info(
                    "optimization_rule_decrease_budget",
                    adset_id=adset_id,
                    cpa=cpa,
                    target_cpa=target_cpa,
                    old_budget=daily_budget,
                    new_budget=new_budget,
                )
        
        return actions
    
    def _apply_budget_cap(self, old_budget: float, new_budget: float) -> float:
        """
        Apply budget change cap (maximum 50% change).
        
        Args:
            old_budget: Current budget
            new_budget: Proposed new budget
        
        Returns:
            Capped budget value
        
        Requirements: 3.4
        """
        max_budget = old_budget * self.MAX_BUDGET_CHANGE_FACTOR
        min_budget = old_budget / self.MAX_BUDGET_CHANGE_FACTOR
        
        if new_budget > max_budget:
            logger.warning(
                "budget_increase_capped",
                old_budget=old_budget,
                proposed_budget=new_budget,
                capped_budget=max_budget,
            )
            return max_budget
        elif new_budget < min_budget:
            logger.warning(
                "budget_decrease_capped",
                old_budget=old_budget,
                proposed_budget=new_budget,
                capped_budget=min_budget,
            )
            return min_budget
        
        return new_budget
    
    async def _get_performance_data(
        self,
        campaign_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Fetch performance data from Web Platform.
        
        Retrieves adset-level performance metrics for the past 7 days.
        
        Args:
            campaign_id: Campaign ID
            context: Request context with user_id
        
        Returns:
            Performance data with adset metrics
        
        Requirements: 3.1
        """
        # Calculate date range (last 7 days)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        # Fetch metrics from Web Platform via MCP
        result = await self.mcp_client.call_tool(
            "get_reports",
            {
                "user_id": context["user_id"],
                "campaign_id": campaign_id,
                "date_range": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "level": "adset",
                "metrics": [
                    "spend",
                    "revenue",
                    "conversions",
                    "roas",
                    "cpa",
                    "impressions",
                    "clicks",
                ],
            },
        )
        
        # Extract adsets from result
        adsets = result.get("data", {}).get("adsets", [])
        
        # Enrich with calculated fields
        for adset in adsets:
            # Ensure numeric fields have defaults
            adset.setdefault("conversions", 0)
            adset.setdefault("roas", 0)
            adset.setdefault("cpa", 0)
            adset.setdefault("daily_budget", 0)
            adset.setdefault("target_roas", 0)
            adset.setdefault("target_cpa", 0)
            
            # Calculate days_running only if not already set
            # For adsets with 0 conversions, we use the full 7-day window
            # For adsets with conversions, we assume they've been running less
            if "days_running" not in adset:
                if adset["conversions"] == 0:
                    adset["days_running"] = 7  # Full window for no conversions
                else:
                    adset["days_running"] = 1  # Has conversions, so not eligible for pause
        
        return {
            "campaign_id": campaign_id,
            "adsets": adsets,
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }
