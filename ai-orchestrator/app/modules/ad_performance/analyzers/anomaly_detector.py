"""
Anomaly detection for ad performance metrics.
"""

from typing import Literal
import numpy as np
from app.modules.ad_performance.models import Anomaly


class AnomalyDetector:
    """异常检测器 - 使用统计方法检测指标异常"""

    def __init__(self):
        """初始化异常检测器"""
        self.sensitivity_thresholds = {
            "low": 3.0,  # 3 个标准差
            "medium": 2.5,  # 2.5 个标准差
            "high": 2.0,  # 2 个标准差
        }

    async def detect(
        self,
        metric: str,
        entity_type: Literal["campaign", "adset", "ad"],
        entity_id: str,
        entity_name: str,
        current_value: float,
        historical_values: list[float],
        sensitivity: str = "medium",
    ) -> Anomaly | None:
        """
        检测指标异常

        Args:
            metric: 指标名称 (roas, cpa, ctr)
            entity_type: 实体类型
            entity_id: 实体ID
            entity_name: 实体名称
            current_value: 当前值
            historical_values: 历史值列表
            sensitivity: 敏感度 (low, medium, high)

        Returns:
            异常对象，如果没有异常则返回 None
        """
        if len(historical_values) < 3:
            return None  # 数据不足

        # 计算期望值和标准差
        expected_value, std_dev = self.calculate_expected_value(historical_values)

        if std_dev == 0:
            return None  # 无变化

        # 计算 Z-score
        z_score = abs((current_value - expected_value) / std_dev)
        threshold = self.sensitivity_thresholds.get(sensitivity, 2.5)

        if z_score > threshold:
            # 计算偏离百分比
            deviation_pct = ((current_value - expected_value) / expected_value) * 100

            # 计算严重性
            severity = self._calculate_severity(
                metric, z_score, deviation_pct, current_value, expected_value
            )

            # 生成建议
            recommendation = self._generate_recommendation(
                metric, entity_type, severity, deviation_pct
            )

            return Anomaly(
                metric=metric,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                current_value=current_value,
                expected_value=expected_value,
                deviation=f"{deviation_pct:+.1f}%",
                severity=severity,
                detected_at="",  # Will be set by caller
                recommendation=recommendation,
            )

        return None

    def calculate_expected_value(
        self, historical_values: list[float]
    ) -> tuple[float, float]:
        """
        计算期望值和标准差

        Args:
            historical_values: 历史值列表

        Returns:
            (期望值, 标准差)
        """
        mean = float(np.mean(historical_values))
        std = float(np.std(historical_values))
        return mean, std

    def _calculate_severity(
        self,
        metric: str,
        z_score: float,
        deviation_pct: float,
        current_value: float,
        expected_value: float,
    ) -> Literal["low", "medium", "high", "critical"]:
        """
        计算异常严重性

        Args:
            metric: 指标名称
            z_score: Z-score
            deviation_pct: 偏离百分比
            current_value: 当前值
            expected_value: 期望值

        Returns:
            严重性级别
        """
        # 通用严重性判断
        if z_score > 4.0 or abs(deviation_pct) > 100:
            base_severity = "critical"
        elif z_score > 3.0 or abs(deviation_pct) > 50:
            base_severity = "high"
        elif z_score > 2.5 or abs(deviation_pct) > 30:
            base_severity = "medium"
        else:
            base_severity = "low"

        # 根据具体指标调整严重性
        # CPA 上涨超过 50% = high severity (Requirements 4.2)
        if metric == "cpa" and deviation_pct > 50:
            if base_severity in ["low", "medium"]:
                return "high"

        # ROAS 下降超过 30% = critical (Requirements 4.3)
        if metric == "roas" and deviation_pct < -30:
            return "critical"

        return base_severity

    def _generate_recommendation(
        self,
        metric: str,
        entity_type: Literal["campaign", "adset", "ad"],
        severity: Literal["low", "medium", "high", "critical"],
        deviation_pct: float,
    ) -> str:
        """
        生成处理建议

        Args:
            metric: 指标名称
            entity_type: 实体类型
            severity: 严重性
            deviation_pct: 偏离百分比

        Returns:
            建议文本
        """
        if severity in ["critical", "high"]:
            if metric == "cpa":
                if entity_type == "adset":
                    return "暂停该 Adset 或降低预算"
                elif entity_type == "campaign":
                    return "立即检查广告设置和素材"
                else:
                    return "暂停该广告或更新素材"
            elif metric == "roas":
                if entity_type == "adset":
                    return "立即检查 Adset 设置，考虑暂停"
                elif entity_type == "campaign":
                    return "立即检查广告系列设置和素材"
                else:
                    return "检查广告素材和定向设置"
            elif metric == "ctr":
                return "检查广告素材，可能存在素材疲劳"
        else:
            if deviation_pct > 0:
                return f"监控 {metric.upper()} 变化趋势"
            else:
                return f"{metric.upper()} 有所改善，继续观察"

        return "监控指标变化"
