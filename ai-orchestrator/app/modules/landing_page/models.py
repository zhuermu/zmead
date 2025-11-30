"""
Pydantic data models for Landing Page module.

These models define the data structures for product information, landing page content,
optimization results, translation results, A/B tests, and publishing/export results.

Requirements: 1.4, 2.1
"""

from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


class Review(BaseModel):
    """用户评价

    Represents a product review from the source platform.
    """

    rating: int = Field(ge=1, le=5, description="评分 (1-5)")
    text: str = Field(description="评价内容")


class ProductInfo(BaseModel):
    """产品信息

    Contains extracted product information from e-commerce platforms.

    Requirements: 1.4
    """

    title: str = Field(description="产品标题")
    price: float = Field(ge=0, description="产品价格")
    currency: str = Field(default="USD", description="货币")
    main_image: HttpUrl = Field(description="主图 URL")
    images: list[HttpUrl] = Field(default_factory=list, description="产品图片 URL 列表")
    description: str = Field(description="产品描述")
    features: list[str] = Field(default_factory=list, description="产品特性")
    reviews: list[Review] = Field(default_factory=list, description="用户评价")
    source: Literal["shopify", "amazon", "manual"] = Field(description="数据来源")


class HeroSection(BaseModel):
    """Hero 区域

    The main hero section of a landing page with headline, image, and CTA.

    Requirements: 2.2
    """

    headline: str = Field(description="主标题")
    subheadline: str = Field(description="副标题")
    image: HttpUrl = Field(description="主图")
    cta_text: str = Field(description="CTA 按钮文案")


class Feature(BaseModel):
    """特性/卖点

    A single feature or selling point displayed on the landing page.

    Requirements: 2.3
    """

    title: str = Field(description="特性标题")
    description: str = Field(description="特性描述")
    icon: str = Field(description="图标名称")


class CTASection(BaseModel):
    """CTA 区域

    Call-to-action section with button text and destination URL.
    """

    text: str = Field(description="CTA 文案")
    url: HttpUrl = Field(description="跳转链接")


class FAQItem(BaseModel):
    """FAQ 项目

    A single FAQ question and answer pair.
    """

    question: str = Field(description="问题")
    answer: str = Field(description="答案")


class ThemeConfig(BaseModel):
    """主题配置

    Theme configuration for landing page styling.

    Requirements: 3.4
    """

    primary_color: str = Field(
        default="#3B82F6",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="主色调 (HEX 格式)",
    )
    secondary_color: str = Field(
        default="#10B981",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="辅助色 (HEX 格式)",
    )
    font_family: str = Field(default="Inter", description="字体")


class LandingPageContent(BaseModel):
    """落地页内容结构

    Complete landing page content structure including all sections.

    Requirements: 2.1
    """

    landing_page_id: str = Field(description="落地页 ID")
    template: str = Field(description="模板名称")
    language: str = Field(default="en", description="语言")
    hero: HeroSection = Field(description="Hero 区域")
    features: list[Feature] = Field(description="特性列表")
    reviews: list[Review] = Field(default_factory=list, description="评价列表")
    faq: list[FAQItem] = Field(default_factory=list, description="FAQ 列表")
    cta: CTASection = Field(description="CTA 区域")
    theme: ThemeConfig = Field(
        default_factory=ThemeConfig, description="主题配置"
    )
    pixel_id: str | None = Field(default=None, description="Facebook Pixel ID")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="创建时间",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="更新时间",
    )


class OptimizationResult(BaseModel):
    """文案优化结果

    Result of AI-powered copy optimization.

    Requirements: 4.4
    """

    optimized_text: str = Field(description="优化后的文案")
    improvements: list[str] = Field(description="改进说明")
    confidence_score: float = Field(ge=0, le=1, description="置信度")
    fallback: bool = Field(default=False, description="是否为回退结果")


class TranslationResult(BaseModel):
    """翻译结果

    Result of landing page translation.

    Requirements: 5.2, 5.3
    """

    translated_landing_page_id: str = Field(description="翻译版本 ID")
    url: HttpUrl = Field(description="翻译版本 URL")
    translations: dict = Field(description="翻译内容")
    source_language: str = Field(description="源语言")
    target_language: str = Field(description="目标语言")


class Variant(BaseModel):
    """测试变体

    A single variant in an A/B test.

    Requirements: 6.1
    """

    name: str = Field(description="变体名称")
    changes: dict = Field(description="变更内容")
    url: HttpUrl | None = Field(default=None, description="变体 URL")


class VariantStats(BaseModel):
    """变体统计

    Statistics for a single A/B test variant.

    Requirements: 6.3
    """

    variant: str = Field(description="变体名称")
    visits: int = Field(ge=0, description="访问量")
    conversions: int = Field(ge=0, description="转化数")
    conversion_rate: float = Field(ge=0, description="转化率 (%)")


class ABTestWinner(BaseModel):
    """获胜变体

    Information about the winning variant in an A/B test.

    Requirements: 6.4
    """

    variant: str = Field(description="获胜变体名称")
    confidence: float = Field(ge=0, le=100, description="置信度 (%)")
    improvement: str = Field(description="提升幅度")


class ChiSquareResult(BaseModel):
    """卡方检验结果

    Result of chi-square statistical test.

    Requirements: 6.3
    """

    p_value: float = Field(ge=0, le=1, description="p 值")
    chi_square: float = Field(ge=0, description="卡方统计量")
    is_significant: bool = Field(description="是否统计显著")


class ABTest(BaseModel):
    """A/B 测试

    Represents an A/B test configuration.

    Requirements: 6.1, 6.2
    """

    test_id: str = Field(description="测试 ID")
    test_name: str = Field(description="测试名称")
    landing_page_id: str = Field(description="落地页 ID")
    variants: list[Variant] = Field(description="变体列表")
    traffic_split: list[int] = Field(description="流量分配 (%)")
    duration_days: int = Field(gt=0, description="测试时长 (天)")
    status: Literal["running", "completed", "paused"] = Field(
        default="running", description="状态"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="创建时间",
    )


class ABTestAnalysis(BaseModel):
    """A/B 测试分析结果

    Analysis results for an A/B test.

    Requirements: 6.3, 6.4, 6.5, 6.6
    """

    test_id: str = Field(description="测试 ID")
    results: list[VariantStats] = Field(description="各变体结果")
    winner: ABTestWinner | None = Field(default=None, description="获胜变体")
    recommendation: str = Field(description="使用建议")
    is_significant: bool = Field(description="是否统计显著")
    p_value: float | None = Field(default=None, description="p 值")
    min_conversions_required: int = Field(
        default=100, description="最小转化数要求"
    )


class PublishResult(BaseModel):
    """发布结果

    Result of publishing a landing page.

    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
    """

    landing_page_id: str = Field(description="落地页 ID")
    url: HttpUrl = Field(description="访问 URL")
    cdn_url: HttpUrl = Field(description="CDN URL")
    ssl_status: Literal["active", "pending", "failed"] = Field(
        description="SSL 状态"
    )
    custom_domain: str | None = Field(default=None, description="自定义域名")


class ExportResult(BaseModel):
    """导出结果

    Result of exporting a landing page.

    Requirements: 8.1, 8.4, 8.5
    """

    download_url: HttpUrl = Field(description="下载链接")
    expires_at: datetime = Field(description="过期时间")
    file_size: int = Field(gt=0, description="文件大小 (字节)")
