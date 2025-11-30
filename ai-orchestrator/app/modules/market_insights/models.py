"""
Data models for Market Insights module.

Defines Pydantic models for competitor analysis, trending creatives,
market trends, ad strategies, and performance tracking.
"""

from typing import Literal

from pydantic import BaseModel, Field


# =============================================================================
# Competitor Analysis Models
# =============================================================================


class CompetitorInfo(BaseModel):
    """竞品信息 / Competitor information."""

    name: str = Field(..., description="竞品名称")
    price: str = Field(..., description="价格")
    features: list[str] = Field(default_factory=list, description="产品特点")
    target_audience: str = Field(..., description="目标受众")
    selling_points: list[str] = Field(default_factory=list, description="卖点")


class CompetitorInsights(BaseModel):
    """竞品洞察 / Competitor insights."""

    pricing_strategy: str = Field(..., description="定价策略")
    marketing_approach: str = Field(..., description="营销方式")
    strengths: list[str] = Field(default_factory=list, description="优势")
    weaknesses: list[str] = Field(default_factory=list, description="劣势")


class CompetitorAnalysis(BaseModel):
    """竞品分析结果 / Competitor analysis result."""

    status: Literal["success", "error"] = Field(..., description="状态")
    competitor_info: CompetitorInfo | None = Field(None, description="竞品信息")
    insights: CompetitorInsights | None = Field(None, description="洞察")
    recommendations: list[str] = Field(default_factory=list, description="建议")
    error_code: str | None = Field(None, description="错误代码")
    message: str | None = Field(None, description="错误信息")


# =============================================================================
# Trending Creatives Models
# =============================================================================


class TrendingCreative(BaseModel):
    """热门素材 / Trending creative."""

    id: str = Field(..., description="素材ID")
    title: str = Field(..., description="标题")
    thumbnail_url: str = Field(..., description="缩略图URL")
    views: int = Field(ge=0, description="播放量")
    engagement_rate: float = Field(ge=0, description="互动率")
    platform: Literal["tiktok"] = Field(..., description="平台")


class CreativeAnalysis(BaseModel):
    """素材分析结果 / Creative analysis result."""

    visual_style: str = Field(..., description="视觉风格")
    color_palette: list[str] = Field(default_factory=list, description="色彩方案")
    key_elements: list[str] = Field(default_factory=list, description="关键元素")
    success_factors: list[str] = Field(default_factory=list, description="成功要素")
    copywriting_style: str = Field(..., description="文案风格")


class TrendingCreativesResponse(BaseModel):
    """热门素材响应 / Trending creatives response."""

    status: Literal["success", "error"] = Field(..., description="状态")
    creatives: list[TrendingCreative] = Field(default_factory=list, description="素材列表")
    total: int = Field(0, description="总数")
    degraded: bool = Field(False, description="是否降级数据")
    message: str | None = Field(None, description="消息")


class CreativeAnalysisResponse(BaseModel):
    """素材分析响应 / Creative analysis response."""

    status: Literal["success", "error"] = Field(..., description="状态")
    analysis: CreativeAnalysis | None = Field(None, description="分析结果")
    recommendations: list[str] = Field(default_factory=list, description="建议")
    error_code: str | None = Field(None, description="错误代码")
    message: str | None = Field(None, description="错误信息")


# =============================================================================
# Market Trends Models
# =============================================================================


class KeywordTrend(BaseModel):
    """关键词趋势 / Keyword trend."""

    keyword: str = Field(..., description="关键词")
    search_volume: int = Field(ge=0, description="搜索量")
    growth_rate: float = Field(..., description="增长率")
    trend_direction: Literal["rising", "stable", "declining"] = Field(
        ..., description="趋势方向"
    )
    related_queries: list[str] = Field(default_factory=list, description="相关查询")


class TrendInsights(BaseModel):
    """趋势洞察 / Trend insights."""

    hot_topics: list[str] = Field(default_factory=list, description="热门话题")
    emerging_trends: list[str] = Field(default_factory=list, description="新兴趋势")
    seasonal_patterns: str = Field(..., description="季节性模式")


class MarketTrendsResponse(BaseModel):
    """市场趋势响应 / Market trends response."""

    status: Literal["success", "error"] = Field(..., description="状态")
    trends: list[KeywordTrend] = Field(default_factory=list, description="趋势列表")
    insights: TrendInsights | None = Field(None, description="洞察")
    degraded: bool = Field(False, description="是否降级数据")
    message: str | None = Field(None, description="消息")
    error_code: str | None = Field(None, description="错误代码")


# =============================================================================
# Ad Strategy Models
# =============================================================================


class AudienceRecommendation(BaseModel):
    """受众推荐 / Audience recommendation."""

    age_range: str = Field(..., description="年龄范围")
    gender: Literal["all", "male", "female"] = Field(..., description="性别")
    interests: list[str] = Field(default_factory=list, description="兴趣")
    behaviors: list[str] = Field(default_factory=list, description="行为")


class CreativeDirection(BaseModel):
    """素材方向 / Creative direction."""

    visual_style: str = Field(..., description="视觉风格")
    key_messages: list[str] = Field(default_factory=list, description="关键信息")
    content_types: list[str] = Field(default_factory=list, description="内容类型")
    color_recommendations: list[str] = Field(default_factory=list, description="色彩推荐")


class BudgetPlanning(BaseModel):
    """预算规划 / Budget planning."""

    recommended_daily_budget: float = Field(ge=0, description="建议每日预算")
    campaign_duration: str = Field(..., description="投放周期")
    expected_reach: str = Field(..., description="预期触达")


class AdGroup(BaseModel):
    """广告组 / Ad group."""

    name: str = Field(..., description="名称")
    targeting: str = Field(..., description="定向策略")
    budget_allocation: str = Field(..., description="预算分配")


class CampaignStructure(BaseModel):
    """广告系列结构 / Campaign structure."""

    ad_groups: list[AdGroup] = Field(default_factory=list, description="广告组列表")


class AdStrategy(BaseModel):
    """广告策略 / Ad strategy."""

    audience_recommendations: AudienceRecommendation = Field(
        ..., description="受众推荐"
    )
    creative_direction: CreativeDirection = Field(..., description="素材方向")
    budget_planning: BudgetPlanning = Field(..., description="预算规划")
    campaign_structure: CampaignStructure = Field(..., description="广告系列结构")


class AdStrategyResponse(BaseModel):
    """广告策略响应 / Ad strategy response."""

    status: Literal["success", "error"] = Field(..., description="状态")
    strategy: AdStrategy | None = Field(None, description="策略")
    rationale: str = Field("", description="策略依据")
    error_code: str | None = Field(None, description="错误代码")
    message: str | None = Field(None, description="错误信息")


# =============================================================================
# Strategy Performance Models
# =============================================================================


class PerformanceMetrics(BaseModel):
    """性能指标 / Performance metrics."""

    avg_roas: float = Field(ge=0, description="平均ROAS")
    avg_ctr: float = Field(ge=0, description="平均CTR")
    avg_conversion_rate: float = Field(ge=0, description="平均转化率")


class PerformanceImprovement(BaseModel):
    """性能提升 / Performance improvement."""

    roas_lift: str = Field(..., description="ROAS提升")
    ctr_lift: str = Field(..., description="CTR提升")
    conversion_rate_lift: str = Field(..., description="转化率提升")


class StrategyPerformance(BaseModel):
    """策略效果 / Strategy performance."""

    campaigns_with_strategy: PerformanceMetrics = Field(
        ..., description="采纳策略的广告表现"
    )
    campaigns_without_strategy: PerformanceMetrics = Field(
        ..., description="未采纳策略的广告表现"
    )
    improvement: PerformanceImprovement = Field(..., description="提升百分比")


class StrategyPerformanceResponse(BaseModel):
    """策略效果响应 / Strategy performance response."""

    status: Literal["success", "error"] = Field(..., description="状态")
    performance: StrategyPerformance | None = Field(None, description="效果数据")
    insights: str = Field("", description="洞察文字")
    error_code: str | None = Field(None, description="错误代码")
    message: str | None = Field(None, description="错误信息")


# =============================================================================
# Request Models
# =============================================================================


class ProductInfo(BaseModel):
    """产品信息 / Product information."""

    name: str = Field(..., description="产品名称")
    category: str = Field(..., description="类别")
    price: float = Field(ge=0, description="价格")
    target_market: str = Field(..., description="目标市场")


class AnalyzeCompetitorRequest(BaseModel):
    """分析竞品请求 / Analyze competitor request."""

    competitor_url: str = Field(..., description="竞品URL")
    analysis_type: str = Field("product", description="分析类型")
    depth: str = Field("detailed", description="分析深度")


class GetTrendingCreativesRequest(BaseModel):
    """获取热门素材请求 / Get trending creatives request."""

    industry: str = Field(..., description="行业")
    region: str = Field(..., description="地区")
    time_range: str = Field("7d", description="时间范围")
    limit: int = Field(20, ge=1, le=50, description="数量限制")


class AnalyzeCreativeTrendRequest(BaseModel):
    """分析素材趋势请求 / Analyze creative trend request."""

    creative_id: str = Field(..., description="素材ID")
    analysis_depth: str = Field("detailed", description="分析深度")


class GetMarketTrendsRequest(BaseModel):
    """获取市场趋势请求 / Get market trends request."""

    keywords: list[str] = Field(..., description="关键词列表")
    region: str = Field(..., description="地区")
    time_range: str = Field("30d", description="时间范围")


class GenerateAdStrategyRequest(BaseModel):
    """生成广告策略请求 / Generate ad strategy request."""

    product_info: ProductInfo = Field(..., description="产品信息")
    competitor_analysis: bool = Field(True, description="是否包含竞品分析")
    trend_analysis: bool = Field(True, description="是否包含趋势分析")


class TrackStrategyPerformanceRequest(BaseModel):
    """追踪策略效果请求 / Track strategy performance request."""

    strategy_id: str = Field(..., description="策略ID")
    campaign_ids: list[str] = Field(..., description="广告系列ID列表")
    comparison_period: str = Field("7d", description="对比周期")
