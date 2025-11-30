"""
Data aggregator for multi-platform metrics.
"""

from typing import Literal
import structlog

logger = structlog.get_logger(__name__)


class DataAggregator:
    """Aggregates metrics data across platforms and entities."""

    async def aggregate_by_platform(
        self, metrics_list: list[dict]
    ) -> dict[str, dict]:
        """
        Aggregate metrics by platform.

        Args:
            metrics_list: List of metrics data from different platforms

        Returns:
            {
                "total": {
                    "spend": float,
                    "revenue": float,
                    "roas": float,
                    "conversions": int,
                    "cpa": float,
                    "impressions": int,
                    "clicks": int,
                    "ctr": float
                },
                "by_platform": {
                    "meta": {...},
                    "tiktok": {...},
                    "google": {...}
                }
            }

        Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
        """
        logger.info("aggregating_by_platform", metrics_count=len(metrics_list))

        # Initialize platform aggregates
        platform_aggregates: dict[str, dict] = {}

        # Aggregate by platform
        for metrics in metrics_list:
            platform = metrics.get("platform")
            if not platform:
                logger.warning("metrics_missing_platform", metrics=metrics)
                continue

            if platform not in platform_aggregates:
                platform_aggregates[platform] = {
                    "spend": 0.0,
                    "revenue": 0.0,
                    "conversions": 0,
                    "impressions": 0,
                    "clicks": 0,
                }

            # Sum up metrics
            platform_aggregates[platform]["spend"] += metrics.get("spend", 0.0)
            platform_aggregates[platform]["revenue"] += metrics.get("revenue", 0.0)
            platform_aggregates[platform]["conversions"] += metrics.get(
                "conversions", 0
            )
            platform_aggregates[platform]["impressions"] += metrics.get(
                "impressions", 0
            )
            platform_aggregates[platform]["clicks"] += metrics.get("clicks", 0)

        # Calculate derived metrics for each platform
        for platform, agg in platform_aggregates.items():
            agg["roas"] = agg["revenue"] / agg["spend"] if agg["spend"] > 0 else 0.0
            agg["cpa"] = (
                agg["spend"] / agg["conversions"] if agg["conversions"] > 0 else 0.0
            )
            agg["ctr"] = (
                agg["clicks"] / agg["impressions"] if agg["impressions"] > 0 else 0.0
            )

        # Calculate total metrics
        total = {
            "spend": sum(p["spend"] for p in platform_aggregates.values()),
            "revenue": sum(p["revenue"] for p in platform_aggregates.values()),
            "conversions": sum(p["conversions"] for p in platform_aggregates.values()),
            "impressions": sum(p["impressions"] for p in platform_aggregates.values()),
            "clicks": sum(p["clicks"] for p in platform_aggregates.values()),
        }

        # Calculate derived metrics for total
        total["roas"] = total["revenue"] / total["spend"] if total["spend"] > 0 else 0.0
        total["cpa"] = (
            total["spend"] / total["conversions"] if total["conversions"] > 0 else 0.0
        )
        total["ctr"] = (
            total["clicks"] / total["impressions"] if total["impressions"] > 0 else 0.0
        )

        # Validate data consistency (total = sum of platforms)
        self._validate_consistency(total, platform_aggregates)

        logger.info(
            "aggregation_complete",
            total_spend=total["spend"],
            platforms=list(platform_aggregates.keys()),
        )

        return {"total": total, "by_platform": platform_aggregates}

    def _validate_consistency(
        self, total: dict, platform_aggregates: dict[str, dict]
    ) -> None:
        """
        Validate that total equals sum of platforms.

        Args:
            total: Total aggregated metrics
            platform_aggregates: Per-platform aggregated metrics

        Raises:
            ValueError: If data is inconsistent
        """
        # Check spend consistency
        platform_spend_sum = sum(p["spend"] for p in platform_aggregates.values())
        if abs(total["spend"] - platform_spend_sum) > 0.01:  # Allow small float errors
            logger.error(
                "spend_inconsistency",
                total_spend=total["spend"],
                platform_sum=platform_spend_sum,
            )
            raise ValueError(
                f"Spend inconsistency: total={total['spend']}, "
                f"platform_sum={platform_spend_sum}"
            )

        # Check revenue consistency
        platform_revenue_sum = sum(p["revenue"] for p in platform_aggregates.values())
        if abs(total["revenue"] - platform_revenue_sum) > 0.01:
            logger.error(
                "revenue_inconsistency",
                total_revenue=total["revenue"],
                platform_sum=platform_revenue_sum,
            )
            raise ValueError(
                f"Revenue inconsistency: total={total['revenue']}, "
                f"platform_sum={platform_revenue_sum}"
            )

        # Check conversions consistency
        platform_conversions_sum = sum(
            p["conversions"] for p in platform_aggregates.values()
        )
        if total["conversions"] != platform_conversions_sum:
            logger.error(
                "conversions_inconsistency",
                total_conversions=total["conversions"],
                platform_sum=platform_conversions_sum,
            )
            raise ValueError(
                f"Conversions inconsistency: total={total['conversions']}, "
                f"platform_sum={platform_conversions_sum}"
            )

        logger.debug("data_consistency_validated")
