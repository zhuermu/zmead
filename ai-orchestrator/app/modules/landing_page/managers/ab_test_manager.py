"""
A/B Test Manager for Landing Page module.

Handles creation and analysis of A/B tests for landing page optimization.
Uses chi-square test for statistical significance analysis.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from scipy.stats import chi2_contingency

from ..models import (
    ABTest,
    ABTestAnalysis,
    ABTestWinner,
    ChiSquareResult,
    Variant,
    VariantStats,
)

logger = logging.getLogger(__name__)


class ABTestManager:
    """
    A/B Test Manager for Landing Pages

    Manages creation and analysis of A/B tests for landing page optimization.
    Uses chi-square test to determine statistical significance.

    Statistical Method:
    - Chi-square test for independence
    - Significance level: α = 0.05 (95% confidence)
    - Minimum sample size: 100 conversions per variant

    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
    """

    MIN_CONVERSIONS_FOR_SIGNIFICANCE = 100
    SIGNIFICANCE_LEVEL = 0.05  # α = 0.05 for 95% confidence
    COOKIE_NAME = "aae_ab_variant"

    def __init__(self, mcp_client=None, redis_client=None):
        """
        Initialize A/B Test Manager

        Args:
            mcp_client: MCP client for data persistence
            redis_client: Redis client for caching variant assignments
        """
        self.mcp_client = mcp_client
        self.redis_client = redis_client

    async def create_test(
        self,
        test_name: str,
        landing_page_id: str,
        variants: list[dict],
        traffic_split: list[int],
        duration_days: int,
        context: dict,
    ) -> dict:
        """
        Create A/B test for landing page

        Creates multiple variants of a landing page with specified traffic allocation.
        Uses cookie-based session consistency for traffic distribution.

        Args:
            test_name: Name of the test
            landing_page_id: Base landing page ID
            variants: List of variant configurations with name and changes
            traffic_split: Traffic allocation percentages (must sum to 100)
            duration_days: Duration of test in days
            context: User context (user_id, session_id)

        Returns:
            dict: Test creation result with test_id and variant_urls

        Requirements: 6.1, 6.2
        """
        user_id = context.get("user_id", "user")

        logger.info(
            f"Creating A/B test: {test_name}",
            extra={
                "test_name": test_name,
                "landing_page_id": landing_page_id,
                "num_variants": len(variants),
                "traffic_split": traffic_split,
                "duration_days": duration_days,
                "user_id": user_id,
            },
        )

        # Validate traffic split
        if sum(traffic_split) != 100:
            raise ValueError(
                f"Traffic split must sum to 100, got {sum(traffic_split)}"
            )

        if len(variants) != len(traffic_split):
            raise ValueError(
                f"Number of variants ({len(variants)}) must match "
                f"traffic split entries ({len(traffic_split)})"
            )

        # Generate test ID
        test_id = f"test_{uuid4().hex[:12]}"

        # Create variant objects with URLs
        variant_objects = []
        variant_urls = []

        for i, variant_config in enumerate(variants):
            variant_name = variant_config.get("name", f"Variant {chr(65 + i)}")
            changes = variant_config.get("changes", {})

            # Generate variant URL with query parameter
            variant_letter = chr(97 + i)  # a, b, c, ...
            variant_url = (
                f"https://{user_id}.aae-pages.com/{landing_page_id}"
                f"?variant={variant_letter}"
            )

            variant_obj = Variant(
                name=variant_name,
                changes=changes,
                url=variant_url,
            )
            variant_objects.append(variant_obj)
            variant_urls.append(variant_url)

        # Calculate dates
        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(days=duration_days)

        # Create A/B test record
        ab_test = ABTest(
            test_id=test_id,
            test_name=test_name,
            landing_page_id=landing_page_id,
            variants=variant_objects,
            traffic_split=traffic_split,
            duration_days=duration_days,
            status="running",
            created_at=start_date,
        )

        # Persist to Web Platform via MCP
        if self.mcp_client:
            try:
                await self.mcp_client.call_tool(
                    "create_ab_test",
                    {
                        "user_id": user_id,
                        "ab_test_data": {
                            "test_id": test_id,
                            "test_name": test_name,
                            "landing_page_id": landing_page_id,
                            "variants": [v.model_dump() for v in variant_objects],
                            "traffic_split": traffic_split,
                            "duration_days": duration_days,
                            "status": "running",
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat(),
                        },
                    },
                )
            except Exception as e:
                logger.warning(
                    f"Failed to persist A/B test to MCP: {e}",
                    extra={"test_id": test_id, "error": str(e)},
                )

        logger.info(
            f"A/B test created successfully: {test_id}",
            extra={
                "test_id": test_id,
                "num_variants": len(variant_objects),
                "variant_urls": variant_urls,
            },
        )

        return {
            "status": "success",
            "test_id": test_id,
            "variant_urls": variant_urls,
            "message": f"A/B 测试已创建，将运行 {duration_days} 天",
        }

    def allocate_traffic(
        self,
        traffic_split: list[int],
        session_id: str | None = None,
    ) -> int:
        """
        Allocate traffic to a variant based on configured split.

        Uses deterministic allocation based on session_id for consistency,
        or random allocation if no session_id is provided.

        Args:
            traffic_split: List of percentages for each variant
            session_id: Optional session ID for consistent allocation

        Returns:
            int: Index of the allocated variant (0-based)

        Requirements: 6.2
        """
        if session_id:
            # Deterministic allocation based on session hash
            hash_value = hash(session_id) % 100
        else:
            # Random allocation
            hash_value = secrets.randbelow(100)

        # Find which variant this hash falls into
        cumulative = 0
        for i, split in enumerate(traffic_split):
            cumulative += split
            if hash_value < cumulative:
                return i

        # Fallback to last variant
        return len(traffic_split) - 1

    def generate_variant_cookie(
        self,
        test_id: str,
        variant_index: int,
    ) -> dict:
        """
        Generate cookie data for session consistency.

        Args:
            test_id: A/B test ID
            variant_index: Index of allocated variant

        Returns:
            dict: Cookie configuration

        Requirements: 6.2
        """
        return {
            "name": self.COOKIE_NAME,
            "value": f"{test_id}:{variant_index}",
            "max_age": 30 * 24 * 60 * 60,  # 30 days
            "http_only": True,
            "secure": True,
            "same_site": "lax",
        }

    async def analyze_test(
        self,
        test_id: str,
        context: dict,
    ) -> ABTestAnalysis:
        """
        Analyze A/B test results

        Uses chi-square test to determine statistical significance.
        Requires minimum 100 conversions per variant for valid analysis.

        Args:
            test_id: Test ID
            context: User context

        Returns:
            ABTestAnalysis: Analysis results with winner and recommendations

        Requirements: 6.3, 6.4, 6.5, 6.6
        """
        user_id = context.get("user_id")

        logger.info(
            f"Analyzing A/B test: {test_id}",
            extra={"test_id": test_id, "user_id": user_id},
        )

        # Get test data from MCP
        test_data = await self._get_test_data(test_id, context)

        # Extract variant statistics
        variant_stats = test_data.get("variant_stats", [])

        if not variant_stats or len(variant_stats) < 2:
            return ABTestAnalysis(
                test_id=test_id,
                results=[],
                winner=None,
                recommendation="数据不足，需要至少两个变体的数据",
                is_significant=False,
                p_value=None,
            )

        # Convert to VariantStats objects
        results = []
        for stat in variant_stats:
            visits = stat.get("visits", 0)
            conversions = stat.get("conversions", 0)
            conversion_rate = (conversions / visits * 100) if visits > 0 else 0

            results.append(
                VariantStats(
                    variant=stat.get("variant", "Unknown"),
                    visits=visits,
                    conversions=conversions,
                    conversion_rate=round(conversion_rate, 2),
                )
            )

        # Check sample size (Requirement 6.5)
        insufficient_samples = [
            r for r in results
            if r.conversions < self.MIN_CONVERSIONS_FOR_SIGNIFICANCE
        ]

        if insufficient_samples:
            total_conversions = sum(r.conversions for r in results)
            logger.warning(
                f"Insufficient sample size for test {test_id}",
                extra={
                    "test_id": test_id,
                    "min_required": self.MIN_CONVERSIONS_FOR_SIGNIFICANCE,
                    "current_conversions": [r.conversions for r in results],
                },
            )

            return ABTestAnalysis(
                test_id=test_id,
                results=results,
                winner=None,
                recommendation=(
                    f"数据不足，建议继续测试。当前转化数：{total_conversions}，"
                    f"每个变体至少需要 {self.MIN_CONVERSIONS_FOR_SIGNIFICANCE} 次转化。"
                ),
                is_significant=False,
                p_value=None,
                min_conversions_required=self.MIN_CONVERSIONS_FOR_SIGNIFICANCE,
            )

        # Perform chi-square test (Requirement 6.3)
        chi_result = self.chi_square_test(results)

        # Determine winner (Requirement 6.4)
        winner = None
        if chi_result.is_significant:
            # Find variant with highest conversion rate
            best_variant = max(results, key=lambda x: x.conversion_rate)
            worst_variant = min(results, key=lambda x: x.conversion_rate)

            # Calculate improvement
            if worst_variant.conversion_rate > 0:
                improvement = (
                    (best_variant.conversion_rate - worst_variant.conversion_rate)
                    / worst_variant.conversion_rate
                    * 100
                )
            else:
                improvement = 100.0

            winner = ABTestWinner(
                variant=best_variant.variant,
                confidence=round((1 - chi_result.p_value) * 100, 1),
                improvement=f"+{improvement:.1f}%",
            )

            logger.info(
                f"Winner identified for test {test_id}: {winner.variant}",
                extra={
                    "test_id": test_id,
                    "winner": winner.variant,
                    "p_value": chi_result.p_value,
                    "improvement": winner.improvement,
                },
            )
        else:
            logger.info(
                f"No significant difference found for test {test_id}",
                extra={
                    "test_id": test_id,
                    "p_value": chi_result.p_value,
                },
            )

        # Generate recommendations (Requirement 6.6)
        recommendation = self._generate_recommendation(
            results, winner, chi_result
        )

        return ABTestAnalysis(
            test_id=test_id,
            results=results,
            winner=winner,
            recommendation=recommendation,
            is_significant=chi_result.is_significant,
            p_value=chi_result.p_value,
            min_conversions_required=self.MIN_CONVERSIONS_FOR_SIGNIFICANCE,
        )

    def chi_square_test(
        self,
        variant_stats: list[VariantStats],
    ) -> ChiSquareResult:
        """
        Perform chi-square test for independence

        Tests whether conversion rates differ significantly across variants.

        Uses 2xN contingency table:
                    Variant A   Variant B   ...
        Converted       a           c       ...
        Not Converted   b           d       ...

        Args:
            variant_stats: List of variant statistics

        Returns:
            ChiSquareResult: Chi-square test results

        Requirements: 6.3
        """
        # Build contingency table
        # Rows: [conversions, non-conversions] for each variant
        observed = [
            [stat.conversions, stat.visits - stat.conversions]
            for stat in variant_stats
        ]

        # Perform chi-square test
        chi2, p_value, dof, expected = chi2_contingency(observed)

        is_significant = p_value < self.SIGNIFICANCE_LEVEL

        logger.debug(
            "Chi-square test results",
            extra={
                "chi2": chi2,
                "p_value": p_value,
                "dof": dof,
                "is_significant": is_significant,
            },
        )

        return ChiSquareResult(
            chi_square=chi2,
            p_value=p_value,
            is_significant=is_significant,
        )

    def _generate_recommendation(
        self,
        results: list[VariantStats],
        winner: Optional[ABTestWinner],
        chi_result: ChiSquareResult,
    ) -> str:
        """
        Generate usage recommendations based on test results

        Args:
            results: List of variant results
            winner: Winner information (if determined)
            chi_result: Chi-square test result

        Returns:
            str: Recommendation text

        Requirements: 6.6
        """
        if winner:
            return (
                f"使用 {winner.variant} 作为主版本，"
                f"预期转化率提升 {winner.improvement}"
            )
        else:
            return "两个变体表现相近，建议继续测试或选择任一版本"

    async def _get_test_data(
        self,
        test_id: str,
        context: dict,
    ) -> dict:
        """
        Get test data from MCP

        Retrieves A/B test configuration and performance data.

        Args:
            test_id: Test ID
            context: User context

        Returns:
            dict: Test data with variant statistics
        """
        if not self.mcp_client:
            # Return mock data for testing
            return {
                "test_id": test_id,
                "variant_stats": [],
            }

        try:
            # Get A/B test data
            test_result = await self.mcp_client.call_tool(
                "get_ab_test",
                {
                    "user_id": context.get("user_id"),
                    "test_id": test_id,
                },
            )

            if not test_result:
                raise ValueError(f"Test not found: {test_id}")

            return test_result

        except Exception as e:
            logger.error(
                f"Failed to get test data: {e}",
                extra={"test_id": test_id, "error": str(e)},
            )
            raise

