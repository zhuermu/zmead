"""
Data models for Ad Creative module.

Defines Pydantic models for product information, creatives, scoring, and analysis.
"""

from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


class ProductInfo(BaseModel):
    """Product information extracted from e-commerce platforms."""

    title: str = Field(..., description="产品标题")
    price: float = Field(ge=0, description="产品价格")
    currency: str = Field(default="USD", description="货币")
    images: list[str] = Field(..., description="产品图片 URL 列表")
    description: str = Field(..., description="产品描述")
    selling_points: list[str] = Field(default_factory=list, description="卖点列表")
    source: Literal["shopify", "amazon", "manual"] = Field(..., description="数据来源")


class GeneratedImage(BaseModel):
    """Generated image from AI model."""

    image_data: bytes = Field(..., description="图片二进制数据")
    file_name: str = Field(..., description="文件名")
    file_type: Literal["image/jpeg", "image/png"] = Field(..., description="文件类型")
    width: int = Field(gt=0, description="宽度")
    height: int = Field(gt=0, description="高度")
    aspect_ratio: str = Field(..., description="宽高比")


class Creative(BaseModel):
    """Creative asset stored in the system."""

    creative_id: str = Field(..., description="素材 ID")
    user_id: str = Field(..., description="用户 ID")
    url: str = Field(..., description="素材 CDN URL")
    thumbnail_url: str | None = Field(None, description="缩略图 URL")

    # Metadata
    product_url: str | None = Field(None, description="产品链接")
    style: str | None = Field(None, description="风格")
    aspect_ratio: str = Field(..., description="宽高比")
    platform: Literal["tiktok", "instagram", "facebook"] | None = Field(
        None, description="目标平台"
    )

    # Scoring
    score: float | None = Field(None, ge=0, le=100, description="总分")
    score_dimensions: dict | None = Field(None, description="各维度分数")

    # Timestamps
    created_at: str = Field(..., description="创建时间")
    updated_at: str | None = Field(None, description="更新时间")

    # Tags
    tags: list[str] = Field(default_factory=list, description="标签")


class DimensionScore(BaseModel):
    """Score for a single evaluation dimension."""

    score: float = Field(ge=0, le=100, description="分数")
    analysis: str = Field(..., description="分析说明")


class CreativeScore(BaseModel):
    """Creative scoring result with multi-dimensional evaluation."""

    total_score: float = Field(ge=0, le=100, description="加权总分")
    dimensions: dict[str, DimensionScore] = Field(..., description="各维度评分")
    ai_analysis: str = Field(..., description="AI 综合分析")


class CompetitorAnalysis(BaseModel):
    """Competitor creative analysis result."""

    composition: str = Field(..., description="构图分析")
    color_scheme: str = Field(..., description="色彩方案")
    selling_points: list[str] = Field(..., description="卖点列表")
    copy_structure: str = Field(..., description="文案结构")
    recommendations: list[str] = Field(..., description="建议")
    saved_at: str | None = Field(None, description="保存时间")


class UploadResult(BaseModel):
    """Result of uploading a creative to storage."""

    creative_id: str = Field(..., description="素材 ID")
    url: str = Field(..., description="CDN URL")
    created_at: str = Field(..., description="创建时间")


class CreditCheckResult(BaseModel):
    """Result of credit balance check."""

    allowed: bool = Field(..., description="是否允许操作")
    required_credits: float = Field(..., description="所需 Credit")
    available_credits: float = Field(..., description="可用 Credit")
    error_code: str | None = Field(None, description="错误码")
    error_message: str | None = Field(None, description="错误消息")


class GenerateCreativeRequest(BaseModel):
    """Request parameters for creative generation."""

    product_url: str | None = Field(None, description="产品链接")
    product_info: ProductInfo | None = Field(None, description="手动输入的产品信息")
    count: Literal[3, 10] = Field(default=3, description="生成数量")
    style: str = Field(default="modern", description="风格")
    platform: Literal["tiktok", "instagram", "facebook"] | None = Field(
        None, description="目标平台"
    )
    aspect_ratio: str | None = Field(None, description="自定义宽高比")


class GenerateCreativeResponse(BaseModel):
    """Response from creative generation."""

    status: Literal["success", "error"] = Field(..., description="状态")
    creative_ids: list[str] = Field(default_factory=list, description="生成的素材 ID 列表")
    creatives: list[Creative] = Field(default_factory=list, description="生成的素材列表")
    message: str = Field(..., description="消息")
    error_code: str | None = Field(None, description="错误码")


class AnalyzeCreativeResponse(BaseModel):
    """Response from creative analysis."""

    status: Literal["success", "error"] = Field(..., description="状态")
    insights: dict | None = Field(None, description="分析洞察")
    recommendations: list[str] = Field(default_factory=list, description="建议")
    message: str = Field(..., description="消息")
    error_code: str | None = Field(None, description="错误码")


class ScoreCreativeResponse(BaseModel):
    """Response from creative scoring."""

    status: Literal["success", "error"] = Field(..., description="状态")
    score: CreativeScore | None = Field(None, description="评分结果")
    message: str = Field(..., description="消息")
    error_code: str | None = Field(None, description="错误码")


class GetCreativesRequest(BaseModel):
    """Request parameters for getting creatives list."""

    filters: dict = Field(default_factory=dict, description="筛选条件")
    sort_by: str = Field(default="score", description="排序字段")
    sort_order: Literal["asc", "desc"] = Field(default="desc", description="排序顺序")
    limit: int = Field(default=20, ge=1, le=100, description="返回数量")
    offset: int = Field(default=0, ge=0, description="偏移量")


class GetCreativesResponse(BaseModel):
    """Response from getting creatives list."""

    status: Literal["success", "error"] = Field(..., description="状态")
    creatives: list[Creative] = Field(default_factory=list, description="素材列表")
    total: int = Field(default=0, description="总数")
    message: str = Field(..., description="消息")
    capacity_warning: bool = Field(default=False, description="容量警告")
