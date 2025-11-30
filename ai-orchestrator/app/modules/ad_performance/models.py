"""
Pydantic data models for Ad Performance module.
"""

from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class MetricsData(BaseModel):
    """广告指标数据"""

    entity_type: Literal["campaign", "adset", "ad"]
    entity_id: str
    entity_name: str
    date: date
    platform: Literal["meta", "tiktok", "google"]

    # 核心指标
    spend: float = Field(ge=0, description="花费")
    impressions: int = Field(ge=0, description="展示次数")
    clicks: int = Field(ge=0, description="点击次数")
    conversions: int = Field(ge=0, description="转化次数")
    revenue: float = Field(ge=0, description="收入")

    # 计算指标
    ctr: float = Field(ge=0, le=1, description="点击率")
    cpa: float = Field(ge=0, description="单次转化成本")
    roas: float = Field(ge=0, description="广告支出回报率")

    def calculate_derived_metrics(self):
        """计算派生指标"""
        self.ctr = self.clicks / self.impressions if self.impressions > 0 else 0
        self.cpa = self.spend / self.conversions if self.conversions > 0 else 0
        self.roas = self.revenue / self.spend if self.spend > 0 else 0


class PeriodMetrics(BaseModel):
    """周期指标"""

    spend: float
    revenue: float
    roas: float
    conversions: int
    cpa: float


class MetricChange(BaseModel):
    """指标变化"""

    spend: str  # "+4.2%"
    revenue: str
    roas: str
    conversions: str
    cpa: str


class PerformanceAnalysis(BaseModel):
    """表现分析结果"""

    entity_id: str
    entity_name: str
    current_period: PeriodMetrics
    previous_period: PeriodMetrics
    changes: MetricChange
    insights: list[str]


class Anomaly(BaseModel):
    """异常检测结果"""

    metric: str
    entity_type: Literal["campaign", "adset", "ad"]
    entity_id: str
    entity_name: str
    current_value: float
    expected_value: float
    deviation: str  # "+112.5%"
    severity: Literal["low", "medium", "high", "critical"]
    detected_at: str
    recommendation: str


class RecommendationTarget(BaseModel):
    """建议目标"""

    type: Literal["campaign", "adset", "ad"]
    id: str
    name: str


class ExpectedImpact(BaseModel):
    """预期影响"""

    spend_reduction: float | None = None
    spend_increase: float | None = None
    revenue_increase: float | None = None
    roas_improvement: str | None = None
    ctr_improvement: str | None = None


class Recommendation(BaseModel):
    """优化建议"""

    priority: Literal["low", "medium", "high"]
    action: Literal[
        "pause_adset", "increase_budget", "decrease_budget", "refresh_creative"
    ]
    target: RecommendationTarget
    reason: str
    expected_impact: ExpectedImpact
    confidence: float = Field(ge=0, le=1, description="置信度")


class ReportSummary(BaseModel):
    """报告摘要"""

    total_spend: float
    total_revenue: float
    overall_roas: float
    total_conversions: int
    avg_cpa: float


class AIAnalysis(BaseModel):
    """AI 分析"""

    key_insights: list[str]
    trends: dict[str, str]  # {"roas_trend": "declining"}


class DailyReport(BaseModel):
    """每日报告"""

    date: date
    summary: ReportSummary
    ai_analysis: AIAnalysis
    recommendations: list[Recommendation]
