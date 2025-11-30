"""
A/B Test Manager for Campaign Automation module.

Handles creation and analysis of A/B tests for creative optimization.
Uses chi-square test for statistical significance analysis.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from scipy.stats import chi2_contingency

from ..models import (
    ABTest,
    ABTestResult,
    ABTestVariant,
    ABTestWinner,
)

logger = logging.getLogger(__name__)


class ABTestManager:
    """
    A/B Test Manager
    
    Manages creation and analysis of A/B tests for creative optimization.
    Uses chi-square test to determine statistical significance.
    
    Statistical Method:
    - Chi-square test for independence
    - Significance level: α = 0.05 (95% confidence)
    - Minimum sample size: 100 conversions per variant
    """
    
    def __init__(self, mcp_client, platform_adapter):
        """
        Initialize A/B Test Manager
        
        Args:
            mcp_client: MCP client for data persistence
            platform_adapter: Platform adapter for API calls
        """
        self.mcp_client = mcp_client
        self.platform_adapter = platform_adapter
        self.min_sample_size = 100  # Minimum conversions per variant
        self.significance_level = 0.05  # α = 0.05 for 95% confidence
    
    async def create_ab_test(
        self,
        test_name: str,
        creative_ids: list[str],
        daily_budget: float,
        test_duration_days: int,
        platform: str,
        context: dict
    ) -> dict:
        """
        Create A/B test campaign
        
        Creates a campaign with equal budget allocation across all variants.
        Each creative gets its own adset with budget = total_budget / num_variants.
        
        Args:
            test_name: Name of the test
            creative_ids: List of creative IDs to test
            daily_budget: Total daily budget for the test
            test_duration_days: Duration of test in days
            platform: Platform (meta, tiktok, google)
            context: User context (user_id, session_id)
        
        Returns:
            dict: Test creation result with test_id, campaign_id, and adsets
        
        Requirements: 5.1, 5.2
        """
        try:
            logger.info(
                f"Creating A/B test: {test_name}",
                extra={
                    "test_name": test_name,
                    "num_variants": len(creative_ids),
                    "daily_budget": daily_budget,
                    "platform": platform,
                    "user_id": context.get("user_id")
                }
            )
            
            # Generate test ID
            test_id = f"test_{uuid4().hex[:12]}"
            
            # Calculate budget per variant (equal split)
            budget_per_variant = daily_budget / len(creative_ids)
            
            # Create campaign
            campaign = await self.platform_adapter.create_campaign(
                platform=platform,
                params={
                    "name": f"{test_name} - A/B Test",
                    "objective": "conversions",
                    "daily_budget": daily_budget,
                    "status": "active"
                }
            )
            
            campaign_id = campaign["id"]
            
            # Create adsets for each variant
            adsets = []
            for i, creative_id in enumerate(creative_ids):
                adset = await self.platform_adapter.create_adset(
                    platform=platform,
                    params={
                        "campaign_id": campaign_id,
                        "name": f"Variant {chr(65 + i)} - {creative_id}",
                        "daily_budget": budget_per_variant,
                        "targeting": {
                            "age_min": 18,
                            "age_max": 65,
                            "countries": ["US"],
                            "targeting_optimization": "none"
                        },
                        "optimization_goal": "conversions",
                        "bid_strategy": "lowest_cost_without_cap",
                        "placements": "automatic"
                    }
                )
                
                # Create ad for this variant
                await self.platform_adapter.create_ad(
                    platform=platform,
                    params={
                        "adset_id": adset["id"],
                        "creative_id": creative_id,
                        "name": f"Ad - {creative_id}",
                        "copy": f"Test variant {chr(65 + i)}"
                    }
                )
                
                adsets.append({
                    "adset_id": adset["id"],
                    "creative_id": creative_id,
                    "budget": budget_per_variant
                })
            
            # Create A/B test record
            start_date = datetime.now(timezone.utc)
            end_date = start_date + timedelta(days=test_duration_days)
            
            ab_test = ABTest(
                test_id=test_id,
                test_name=test_name,
                campaign_id=campaign_id,
                creative_ids=creative_ids,
                daily_budget=daily_budget,
                test_duration_days=test_duration_days,
                start_date=start_date,
                end_date=end_date,
                status="running"
            )
            
            # Persist to Web Platform via MCP
            await self.mcp_client.call_tool(
                "create_campaign",
                {
                    "user_id": context["user_id"],
                    "platform": platform,
                    "campaign_data": {
                        "campaign_id": campaign_id,
                        "name": ab_test.test_name,
                        "objective": "conversions",
                        "daily_budget": daily_budget,
                        "status": "active",
                        "metadata": {
                            "test_id": test_id,
                            "is_ab_test": True,
                            "test_duration_days": test_duration_days
                        }
                    }
                }
            )
            
            logger.info(
                f"A/B test created successfully: {test_id}",
                extra={
                    "test_id": test_id,
                    "campaign_id": campaign_id,
                    "num_adsets": len(adsets)
                }
            )
            
            return {
                "status": "success",
                "test_id": test_id,
                "campaign_id": campaign_id,
                "adsets": adsets,
                "message": f"A/B 测试已创建，将运行 {test_duration_days} 天"
            }
            
        except Exception as e:
            logger.error(
                f"Failed to create A/B test: {e}",
                extra={
                    "test_name": test_name,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    async def analyze_ab_test(
        self,
        test_id: str,
        context: dict
    ) -> ABTestResult:
        """
        Analyze A/B test results
        
        Uses chi-square test to determine statistical significance.
        Requires minimum 100 conversions per variant for valid analysis.
        
        Args:
            test_id: Test ID
            context: User context
        
        Returns:
            ABTestResult: Analysis results with winner and recommendations
        
        Requirements: 5.3, 5.4, 5.5, 5.6
        """
        try:
            logger.info(
                f"Analyzing A/B test: {test_id}",
                extra={"test_id": test_id, "user_id": context.get("user_id")}
            )
            
            # Get test data from MCP
            test_data = await self._get_test_data(test_id, context)
            
            # Extract variants
            variants = test_data["variants"]
            
            # Check sample size (Requirement 5.5)
            insufficient_samples = [
                v for v in variants if v["conversions"] < self.min_sample_size
            ]
            
            if insufficient_samples:
                logger.warning(
                    f"Insufficient sample size for test {test_id}",
                    extra={
                        "test_id": test_id,
                        "min_required": self.min_sample_size,
                        "current_samples": [v["conversions"] for v in variants]
                    }
                )
                
                return ABTestResult(
                    test_id=test_id,
                    results=[],
                    winner=None,
                    recommendations=["数据不足，建议继续测试"],
                    message=f"数据不足，建议继续测试。每个变体至少需要 {self.min_sample_size} 次转化。"
                )
            
            # Calculate conversion rates
            variant_results = []
            for i, variant in enumerate(variants):
                conversion_rate = (
                    variant["conversions"] / variant["impressions"]
                    if variant["impressions"] > 0
                    else 0
                )
                
                variant_results.append(
                    ABTestVariant(
                        creative_id=variant["creative_id"],
                        spend=variant["spend"],
                        revenue=variant["revenue"],
                        roas=variant["roas"],
                        ctr=variant["ctr"],
                        conversions=variant["conversions"],
                        impressions=variant["impressions"],
                        conversion_rate=conversion_rate,
                        rank=1  # Temporary rank, will be updated after sorting
                    )
                )
            
            # Sort by ROAS and assign ranks
            variant_results.sort(key=lambda v: v.roas, reverse=True)
            for i, variant in enumerate(variant_results):
                variant.rank = i + 1
            
            # Perform chi-square test (Requirement 5.3)
            chi_square_result = self._chi_square_test(variants)
            
            # Determine winner (Requirement 5.4)
            winner = None
            if chi_square_result["p_value"] < self.significance_level:
                # Statistically significant difference found
                best_variant = max(variant_results, key=lambda v: v.conversion_rate)
                winner = ABTestWinner(
                    creative_id=best_variant.creative_id,
                    confidence=95,
                    p_value=chi_square_result["p_value"]
                )
                logger.info(
                    f"Winner identified for test {test_id}: {winner.creative_id}",
                    extra={
                        "test_id": test_id,
                        "winner": winner.creative_id,
                        "p_value": chi_square_result["p_value"]
                    }
                )
            else:
                logger.info(
                    f"No significant difference found for test {test_id}",
                    extra={
                        "test_id": test_id,
                        "p_value": chi_square_result["p_value"]
                    }
                )
            
            # Generate recommendations (Requirement 5.6)
            recommendations = self._generate_recommendations(variant_results, winner)
            
            # Create result
            result = ABTestResult(
                test_id=test_id,
                results=variant_results,
                winner=winner,
                recommendations=recommendations,
                message=(
                    f"测试完成。{'找到获胜变体' if winner else '差异不显著'}。"
                )
            )
            
            logger.info(
                f"A/B test analysis completed: {test_id}",
                extra={
                    "test_id": test_id,
                    "has_winner": winner is not None,
                    "num_recommendations": len(recommendations)
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Failed to analyze A/B test: {e}",
                extra={"test_id": test_id, "error": str(e)},
                exc_info=True
            )
            raise
    
    def _chi_square_test(self, variants: list[dict]) -> dict:
        """
        Perform chi-square test for independence
        
        Tests whether conversion rates differ significantly across variants.
        
        Args:
            variants: List of variant data with conversions and impressions
        
        Returns:
            dict: Chi-square test results with chi2, p_value, and dof
        
        Requirements: 5.3
        """
        # Build contingency table
        # Rows: variants, Columns: [conversions, non-conversions]
        observed = [
            [v["conversions"], v["impressions"] - v["conversions"]]
            for v in variants
        ]
        
        # Perform chi-square test
        chi2, p_value, dof, expected = chi2_contingency(observed)
        
        logger.debug(
            "Chi-square test results",
            extra={
                "chi2": chi2,
                "p_value": p_value,
                "dof": dof,
                "observed": observed
            }
        )
        
        return {
            "chi2": chi2,
            "p_value": p_value,
            "dof": dof,
            "expected": expected.tolist()
        }
    
    def _generate_recommendations(
        self,
        variants: list[ABTestVariant],
        winner: Optional[ABTestWinner]
    ) -> list[str]:
        """
        Generate optimization recommendations
        
        Provides actionable recommendations based on test results.
        
        Args:
            variants: List of variant results (sorted by performance)
            winner: Winner information (if determined)
        
        Returns:
            list[str]: List of recommendations
        
        Requirements: 5.6
        """
        recommendations = []
        
        if winner:
            # Winner identified - provide specific actions
            worst_variant = variants[-1]  # Last in sorted list
            
            recommendations.append(
                f"暂停 {worst_variant.creative_id}（表现最差，ROAS: {worst_variant.roas:.2f}）"
            )
            recommendations.append(
                f"增加 {winner.creative_id} 预算 50%（获胜变体，置信度: {winner.confidence}%）"
            )
            
            # Additional recommendations based on performance gaps
            if len(variants) > 2:
                middle_variants = variants[1:-1]
                if middle_variants:
                    recommendations.append(
                        f"考虑逐步减少中等表现变体的预算"
                    )
        else:
            # No clear winner - suggest continuing or adjusting
            recommendations.append(
                "差异不显著，建议继续测试或增加样本量"
            )
            
            # Check if any variant is clearly underperforming
            if len(variants) >= 2:
                best_roas = variants[0].roas
                worst_roas = variants[-1].roas
                
                if best_roas > worst_roas * 2:
                    recommendations.append(
                        f"考虑暂停 {variants[-1].creative_id}（ROAS 显著低于最佳变体）"
                    )
        
        return recommendations
    
    async def _get_test_data(self, test_id: str, context: dict) -> dict:
        """
        Get test data from MCP
        
        Retrieves performance data for all variants in the test.
        
        Args:
            test_id: Test ID
            context: User context
        
        Returns:
            dict: Test data with variants
        """
        # Get test metadata
        test_result = await self.mcp_client.call_tool(
            "get_campaigns",
            {
                "user_id": context["user_id"],
                "filters": {
                    "metadata.test_id": test_id
                }
            }
        )
        
        if not test_result or "campaigns" not in test_result or len(test_result["campaigns"]) == 0:
            raise ValueError(f"Test not found: {test_id}")
        
        campaign = test_result["campaigns"][0]
        campaign_id = campaign.get("campaign_id") or campaign.get("platform_campaign_id")
        
        # Get performance data for all adsets
        # Use campaign created_at if available, otherwise use 7 days ago
        start_date = campaign.get("created_at")
        if not start_date:
            start_date = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        
        performance_result = await self.mcp_client.call_tool(
            "get_reports",
            {
                "user_id": context["user_id"],
                "campaign_id": campaign_id,
                "level": "adset",
                "metrics": [
                    "spend",
                    "revenue",
                    "conversions",
                    "impressions",
                    "clicks",
                    "roas",
                    "ctr"
                ],
                "date_range": {
                    "start_date": start_date,
                    "end_date": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        # Extract variant data
        variants = []
        for adset_data in performance_result.get("adsets", []):
            # Extract creative_id from adset name or metadata
            creative_id = adset_data.get("creative_id", "unknown")
            
            variants.append({
                "creative_id": creative_id,
                "spend": adset_data.get("spend", 0),
                "revenue": adset_data.get("revenue", 0),
                "roas": adset_data.get("roas", 0),
                "ctr": adset_data.get("ctr", 0),
                "conversions": adset_data.get("conversions", 0),
                "impressions": adset_data.get("impressions", 0)
            })
        
        return {
            "test_id": test_id,
            "campaign_id": campaign_id,
            "variants": variants
        }
