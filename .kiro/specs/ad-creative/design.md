# 设计文档 - Ad Creative（广告素材生成）

## Overview（概述）

Ad Creative 是 AI Orchestrator 的功能模块之一，作为独立的 Python 模块实现。该模块负责：

1. **产品信息提取**：从产品链接（Shopify/Amazon）自动抓取产品信息
2. **素材生成**：使用 Gemini Imagen 3 生成广告图片素材
3. **竞品分析**：分析竞品广告素材的构图、色彩、卖点
4. **素材评分**：使用 AI 多维度评估素材质量
5. **素材管理**：素材库的增删改查和批量操作
6. **规格适配**：根据目标平台自动调整素材尺寸

该模块通过 MCP 协议与 Web Platform 通信，不直接访问数据库。所有文件存储通过 S3 预签名 URL 完成。

---

## Architecture（架构）

### 模块结构

```
ai-orchestrator/
└── app/
    └── modules/
        └── ad_creative/
            ├── __init__.py
            ├── capability.py              # 主入口，实现 execute() 接口
            ├── extractors/
            │   ├── __init__.py
            │   ├── base.py                # 提取器基类
            │   ├── shopify_extractor.py   # Shopify 产品信息提取
            │   └── amazon_extractor.py    # Amazon 产品信息提取
            ├── generators/
            │   ├── __init__.py
            │   ├── image_generator.py     # 图片生成（Gemini Imagen 3）
            │   └── variant_generator.py   # 变体生成
            ├── analyzers/
            │   ├── __init__.py
            │   ├── creative_analyzer.py   # 素材分析
            │   ├── competitor_analyzer.py # 竞品素材分析
            │   └── scoring_engine.py      # 素材评分引擎
            ├── managers/
            │   ├── __init__.py
            │   ├── creative_manager.py    # 素材库管理
            │   └── upload_manager.py      # 文件上传管理
            └── utils/
                ├── __init__.py
                ├── validators.py          # 文件验证
                ├── aspect_ratio.py        # 宽高比处理
                └── credit_checker.py      # Credit 检查
```

### 调用路径

```
用户 → AI Orchestrator → Ad Creative → MCP Client → Web Platform
                              ↓
                        Gemini Imagen 3 (图片生成)
                        Gemini 2.5 Flash (素材分析/评分)
```

### 依赖关系

```
Ad Creative
    ├─► MCP Client (调用 Web Platform 工具)
    ├─► Gemini Client (AI 生成和分析)
    │   ├─► Gemini Imagen 3 (图片生成)
    │   └─► Gemini 2.5 Flash (素材分析/评分)
    ├─► HTTP Client (S3 上传、产品信息抓取)
    └─► Redis (缓存)
```

---

## Components and Interfaces（组件和接口）

### 1. AdCreative (主入口)

```python
class AdCreative:
    """Ad Creative 功能模块主入口"""
    
    async def execute(
        self,
        action: str,
        parameters: dict,
        context: dict
    ) -> dict:
        """
        执行素材生成操作
        
        Args:
            action: 操作名称
            parameters: 操作参数
            context: 上下文信息（user_id, session_id等）
        
        Returns:
            操作结果
        """
```

**支持的 Actions**：

| Action | 描述 | 参数 | 返回值 |
|--------|------|------|--------|
| `generate_creative` | 生成素材 | product_url, count, style, platform | creative_ids, message |
| `analyze_creative` | 分析素材 | creative_id 或 image_url | insights, recommendations |
| `score_creative` | 评分素材 | creative_id | score, dimensions |
| `generate_variants` | 生成变体 | creative_id, count | variant_ids |
| `analyze_competitor` | 分析竞品素材 | ad_url | analysis_result |
| `get_creatives` | 获取素材列表 | filters, sort, limit | creatives |
| `delete_creative` | 删除素材 | creative_id | success |
| `download_creative` | 下载素材 | creative_id | download_url |
| `batch_download` | 批量下载 | creative_ids | download_url |

### 2. ProductExtractor (产品信息提取器)

```python
class BaseExtractor(ABC):
    """产品信息提取器基类"""
    
    @abstractmethod
    async def extract(self, product_url: str) -> ProductInfo:
        """提取产品信息"""
        pass
    
    @abstractmethod
    def supports(self, url: str) -> bool:
        """检查是否支持该 URL"""
        pass

class ShopifyExtractor(BaseExtractor):
    """Shopify 产品信息提取"""
    
    async def extract(self, product_url: str) -> ProductInfo:
        # 使用 Shopify API 提取数据
        pass

class AmazonExtractor(BaseExtractor):
    """Amazon 产品信息提取"""
    
    async def extract(self, product_url: str) -> ProductInfo:
        # 使用网页解析提取数据
        pass
```

### 3. ImageGenerator (图片生成器)

```python
class ImageGenerator:
    """图片素材生成器"""
    
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client
    
    async def generate(
        self,
        product_info: ProductInfo,
        count: int,
        style: str,
        aspect_ratio: str
    ) -> list[GeneratedImage]:
        """
        生成图片素材
        
        Args:
            product_info: 产品信息
            count: 生成数量（3 或 10）
            style: 风格（modern, minimal, vibrant 等）
            aspect_ratio: 宽高比（9:16, 1:1, 4:5）
        
        Returns:
            生成的图片列表
        """
        pass
    
    async def generate_variants(
        self,
        original_creative_id: str,
        count: int
    ) -> list[GeneratedImage]:
        """基于原始素材生成变体"""
        pass
```

### 4. ScoringEngine (评分引擎)

```python
class ScoringEngine:
    """素材评分引擎"""
    
    DIMENSION_WEIGHTS = {
        "visual_impact": 0.30,      # 视觉冲击力
        "composition": 0.25,        # 构图平衡
        "color_harmony": 0.25,      # 色彩和谐
        "text_clarity": 0.20        # 文案清晰
    }
    
    async def score(self, image_url: str) -> CreativeScore:
        """
        评分素材
        
        Returns:
            {
                "total_score": 85,
                "dimensions": {
                    "visual_impact": {"score": 90, "analysis": "..."},
                    "composition": {"score": 85, "analysis": "..."},
                    "color_harmony": {"score": 80, "analysis": "..."},
                    "text_clarity": {"score": 85, "analysis": "..."}
                },
                "ai_analysis": "..."
            }
        """
        pass
    
    def calculate_weighted_score(self, dimensions: dict) -> float:
        """计算加权总分"""
        total = 0
        for dim, weight in self.DIMENSION_WEIGHTS.items():
            total += dimensions[dim]["score"] * weight
        return round(total, 1)
```

### 5. CompetitorAnalyzer (竞品分析器)

```python
class CompetitorAnalyzer:
    """竞品素材分析器"""
    
    async def analyze(self, ad_url: str) -> CompetitorAnalysis:
        """
        分析竞品广告素材
        
        Args:
            ad_url: TikTok 广告链接
        
        Returns:
            {
                "composition": "...",
                "color_scheme": "...",
                "selling_points": [...],
                "copy_structure": "...",
                "recommendations": [...]
            }
        """
        pass
    
    async def extract_creative(self, ad_url: str) -> bytes:
        """从广告链接提取素材"""
        pass
```

### 6. UploadManager (上传管理器)

```python
class UploadManager:
    """文件上传管理器"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp = mcp_client
    
    async def upload_creative(
        self,
        user_id: str,
        image_data: bytes,
        file_name: str,
        metadata: dict
    ) -> UploadResult:
        """
        上传素材到 S3
        
        流程：
        1. 调用 MCP get_upload_url 获取预签名 URL
        2. 使用 HTTP PUT 上传文件到 S3
        3. 调用 MCP create_creative 存储元数据
        """
        pass
    
    async def get_presigned_url(
        self,
        user_id: str,
        file_name: str,
        file_type: str,
        file_size: int
    ) -> dict:
        """获取 S3 预签名上传 URL"""
        pass
```

### 7. CreditChecker (Credit 检查器)

```python
class CreditChecker:
    """Credit 余额检查器"""
    
    CREDIT_RATES = {
        "image_generation": 0.5,      # 每张图片 0.5 credits
        "image_generation_bulk": 0.4,  # 批量（10+）每张 0.4 credits
        "creative_analysis": 0.2,      # 素材分析 0.2 credits
        "competitor_analysis": 1.0     # 竞品分析 1.0 credits
    }
    
    async def check_and_reserve(
        self,
        user_id: str,
        operation: str,
        count: int = 1
    ) -> CreditCheckResult:
        """检查并预留 Credit"""
        pass
    
    async def deduct(
        self,
        user_id: str,
        operation_id: str,
        credits: float
    ) -> bool:
        """扣减 Credit"""
        pass
    
    async def refund(
        self,
        user_id: str,
        operation_id: str,
        credits: float
    ) -> bool:
        """退还 Credit"""
        pass
    
    def calculate_cost(self, operation: str, count: int) -> float:
        """计算操作成本"""
        if operation == "image_generation" and count >= 10:
            return count * self.CREDIT_RATES["image_generation_bulk"]
        return count * self.CREDIT_RATES.get(operation, 0)
```

---

## Data Models（数据模型）

### ProductInfo (产品信息)

```python
from pydantic import BaseModel, Field, HttpUrl
from typing import Literal

class ProductInfo(BaseModel):
    """产品信息"""
    title: str = Field(..., description="产品标题")
    price: float = Field(ge=0, description="产品价格")
    currency: str = Field(default="USD", description="货币")
    images: list[HttpUrl] = Field(..., description="产品图片 URL 列表")
    description: str = Field(..., description="产品描述")
    selling_points: list[str] = Field(default_factory=list, description="卖点列表")
    source: Literal["shopify", "amazon", "manual"] = Field(..., description="数据来源")
```

### GeneratedImage (生成的图片)

```python
class GeneratedImage(BaseModel):
    """生成的图片"""
    image_data: bytes = Field(..., description="图片二进制数据")
    file_name: str = Field(..., description="文件名")
    file_type: Literal["image/jpeg", "image/png"] = Field(..., description="文件类型")
    width: int = Field(gt=0, description="宽度")
    height: int = Field(gt=0, description="高度")
    aspect_ratio: str = Field(..., description="宽高比")
```

### Creative (素材)

```python
class Creative(BaseModel):
    """素材"""
    creative_id: str = Field(..., description="素材 ID")
    user_id: str = Field(..., description="用户 ID")
    url: HttpUrl = Field(..., description="素材 CDN URL")
    thumbnail_url: HttpUrl | None = Field(None, description="缩略图 URL")
    
    # 元数据
    product_url: HttpUrl | None = Field(None, description="产品链接")
    style: str | None = Field(None, description="风格")
    aspect_ratio: str = Field(..., description="宽高比")
    platform: Literal["tiktok", "instagram", "facebook"] | None = Field(None, description="目标平台")
    
    # 评分
    score: float | None = Field(None, ge=0, le=100, description="总分")
    score_dimensions: dict | None = Field(None, description="各维度分数")
    
    # 时间戳
    created_at: str = Field(..., description="创建时间")
    updated_at: str | None = Field(None, description="更新时间")
    
    # 标签
    tags: list[str] = Field(default_factory=list, description="标签")
```

### CreativeScore (素材评分)

```python
class DimensionScore(BaseModel):
    """维度评分"""
    score: float = Field(ge=0, le=100, description="分数")
    analysis: str = Field(..., description="分析说明")

class CreativeScore(BaseModel):
    """素材评分结果"""
    total_score: float = Field(ge=0, le=100, description="加权总分")
    dimensions: dict[str, DimensionScore] = Field(..., description="各维度评分")
    ai_analysis: str = Field(..., description="AI 综合分析")
```

### CompetitorAnalysis (竞品分析)

```python
class CompetitorAnalysis(BaseModel):
    """竞品素材分析结果"""
    composition: str = Field(..., description="构图分析")
    color_scheme: str = Field(..., description="色彩方案")
    selling_points: list[str] = Field(..., description="卖点列表")
    copy_structure: str = Field(..., description="文案结构")
    recommendations: list[str] = Field(..., description="建议")
    saved_at: str | None = Field(None, description="保存时间")
```

### UploadResult (上传结果)

```python
class UploadResult(BaseModel):
    """上传结果"""
    creative_id: str = Field(..., description="素材 ID")
    url: HttpUrl = Field(..., description="CDN URL")
    created_at: str = Field(..., description="创建时间")
```

### CreditCheckResult (Credit 检查结果)

```python
class CreditCheckResult(BaseModel):
    """Credit 检查结果"""
    allowed: bool = Field(..., description="是否允许操作")
    required_credits: float = Field(..., description="所需 Credit")
    available_credits: float = Field(..., description="可用 Credit")
    error_code: str | None = Field(None, description="错误码")
    error_message: str | None = Field(None, description="错误消息")
```

---

## Correctness Properties（正确性属性）

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*



### Property Reflection（属性反思）

在编写正确性属性之前，识别并消除冗余：

**识别的冗余**：
- 5.2, 5.3, 5.4 是 5.1 的具体案例（平台到宽高比映射）→ 合并为一个属性
- 4.1.3 和 10.3 都测试 create_creative MCP 调用 → 合并
- 4.5 和 4.1.4 都测试重试行为 → 合并为通用重试属性
- 7.1, 7.2, 7.3 可合并为评分完整性属性
- 9.1, 9.2, 9.3 可合并为 Credit 流程属性

**合并后的属性**：
- 平台宽高比映射 (5.1-5.4) → Property 6
- 评分完整性 (7.1-7.3) → Property 8
- Credit 流程 (9.1-9.3) → Property 11
- 重试行为 (4.5, 4.1.4, 10.5) → Property 5

---

### Correctness Properties（正确性属性）

Property 1: 产品信息提取完整性
*For any* 有效的产品链接（Shopify/Amazon），调用 generate_creative 时应自动提取产品信息，且提取结果包含 title、price、images、description、selling_points 字段
**Validates: Requirements 1.1, 1.2**

Property 2: 产品信息提取失败处理
*For any* 无效或无法访问的产品链接，系统应返回错误并提示用户手动输入产品信息
**Validates: Requirements 1.5**

Property 3: 文件上传验证
*For any* 上传的文件，系统应验证文件格式（仅 JPG/PNG）和大小（最大 10MB），不符合条件的文件应被拒绝
**Validates: Requirements 2.2**

Property 4: 上传数量限制
*For any* 用户上传操作，当已上传图片数量超过 5 张时，系统应拒绝新上传并返回限制提示
**Validates: Requirements 2.5**

Property 5: 操作失败自动重试
*For any* 素材生成、文件上传或 MCP 调用失败场景，系统应自动重试最多 3 次，并在最终失败时返回适当的错误码
**Validates: Requirements 4.5, 4.1.4, 4.1.5, 10.5**

Property 6: 平台宽高比映射
*For any* 目标平台选择，系统应自动选择对应的宽高比：TikTok → 9:16，Instagram Feed → 1:1，Facebook Feed → 4:5
**Validates: Requirements 5.1, 5.2, 5.3, 5.4**

Property 7: 自定义宽高比支持
*For any* 用户自定义的宽高比输入，系统应接受并使用该尺寸生成素材
**Validates: Requirements 5.5**

Property 8: 素材评分完整性
*For any* 生成的素材，系统应使用 AI 分析并返回 0-100 分的加权总分，以及各维度（visual_impact、composition、color_harmony、text_clarity）的分数和分析说明
**Validates: Requirements 7.1, 7.2, 7.3**

Property 9: 素材列表排序
*For any* 素材列表查询，返回的素材应按评分从高到低排序
**Validates: Requirements 7.5**

Property 10: 素材库筛选功能
*For any* 素材库查询，系统应支持按标签、日期、评分筛选，且筛选结果正确反映筛选条件
**Validates: Requirements 8.2**

Property 11: Credit 余额检查和扣减
*For any* 素材生成请求，系统应先检查 Credit 余额，余额不足时返回错误码 6011，余额充足时执行生成并扣减相应 Credit
**Validates: Requirements 9.1, 9.2, 9.3**

Property 12: Credit 失败退还
*For any* 素材生成失败场景，系统应退还已扣减的 Credit
**Validates: Requirements 9.4**

Property 13: 批量生成折扣
*For any* 批量生成请求（10 张以上），系统应按 0.4 credits/张计费（8 折优惠）
**Validates: Requirements 9.5**

Property 14: 素材上传流程完整性
*For any* 素材生成完成后，系统应依次调用 get_upload_url 获取预签名 URL、上传文件到 S3、调用 create_creative 存储元数据
**Validates: Requirements 4.1.1, 4.1.2, 4.1.3**

Property 15: 竞品素材分析完整性
*For any* 有效的 TikTok 广告链接，分析结果应包含 composition、color_scheme、selling_points、copy_structure 字段
**Validates: Requirements 3.2, 3.3**

Property 16: 素材删除一致性
*For any* 删除的素材，删除后通过 get_creatives 查询应不再返回该素材
**Validates: Requirements 6.3, 8.4**

Property 17: 素材生成数量一致性
*For any* 素材生成请求，生成完成后返回的素材数量应等于请求的数量（3 或 10）
**Validates: Requirements 4.2, 4.4**

Property 18: 素材库容量警告
*For any* 用户素材库，当素材数量超过 100 个时，系统应返回清理提示
**Validates: Requirements 8.5**

Property 19: MCP 工具调用正确性
*For any* 素材列表请求，系统应调用 get_creatives MCP 工具；素材更新请求应调用 update_creative MCP 工具
**Validates: Requirements 10.2, 10.4**

---

## Error Handling（错误处理）

### 错误类型

1. **产品信息提取错误**
   - URL 格式无效
   - 网站无法访问
   - 产品页面结构变化
   - API 限流

2. **AI 模型错误**
   - Gemini Imagen 3 生成失败
   - Gemini 2.5 Flash 分析超时
   - 模型响应格式错误
   - API 配额耗尽

3. **文件上传错误**
   - 预签名 URL 获取失败
   - S3 上传超时
   - 文件大小超限
   - 文件格式不支持

4. **MCP 调用错误**
   - 连接失败
   - 工具不存在
   - 参数无效
   - 执行超时

5. **Credit 错误**
   - 余额不足
   - 扣减失败
   - 退还失败

### 错误码映射

| 错误场景 | 错误码 | 错误类型 | 是否可重试 |
|---------|--------|---------|-----------|
| 产品链接无效 | 6006 | PRODUCT_URL_INVALID | 否 |
| 产品信息提取失败 | 6007 | PRODUCT_INFO_EXTRACTION_FAILED | 是 |
| AI 模型失败 | 4001 | AI_MODEL_FAILED | 是 |
| 生成失败 | 4003 | GENERATION_FAILED | 是 |
| 文件上传失败 | 5003 | STORAGE_ERROR | 是 |
| Credit 余额不足 | 6011 | INSUFFICIENT_CREDITS | 否 |
| Credit 扣减失败 | 6012 | CREDIT_DEDUCTION_FAILED | 是 |

### 错误处理策略

```python
class ErrorHandler:
    """统一错误处理器"""
    
    async def handle_generation_error(
        self,
        error: Exception,
        retry_count: int,
        operation_id: str
    ) -> dict:
        """处理素材生成错误"""
        if retry_count < 3:
            # 自动重试
            await asyncio.sleep(2 ** retry_count)
            return {"retry": True}
        else:
            # 退还 Credit
            await self.credit_checker.refund(
                user_id=self.context["user_id"],
                operation_id=operation_id,
                credits=self.reserved_credits
            )
            return {
                "status": "error",
                "error_code": "4003",
                "message": "素材生成失败，Credit 已退还",
                "retry_allowed": False
            }
    
    async def handle_upload_error(
        self,
        error: Exception,
        retry_count: int
    ) -> dict:
        """处理上传错误"""
        if retry_count < 3:
            await asyncio.sleep(2 ** retry_count)
            return {"retry": True}
        else:
            return {
                "status": "error",
                "error_code": "5003",
                "message": "文件上传失败",
                "retry_allowed": False
            }
```

---

## Testing Strategy（测试策略）

### Unit Testing（单元测试）

使用 pytest + pytest-asyncio 进行单元测试：

**测试覆盖**：
- ProductExtractor 的产品信息提取逻辑
- ImageGenerator 的图片生成流程
- ScoringEngine 的评分计算
- UploadManager 的上传流程
- CreditChecker 的余额检查和扣减
- 错误处理和重试机制

**示例**：
```python
@pytest.mark.asyncio
async def test_scoring_engine_returns_valid_score():
    """测试评分引擎返回有效分数"""
    engine = ScoringEngine(gemini_client=mock_gemini)
    result = await engine.score(image_url="https://example.com/image.jpg")
    
    assert 0 <= result.total_score <= 100
    assert "visual_impact" in result.dimensions
    assert "composition" in result.dimensions
    assert "color_harmony" in result.dimensions
    assert "text_clarity" in result.dimensions
```

### Property-Based Testing（基于属性的测试）

使用 Hypothesis 进行属性测试，每个测试运行 100 次迭代：

**测试框架**：Hypothesis (Python)

**配置**：
```python
from hypothesis import given, settings
import hypothesis.strategies as st

settings.register_profile("default", max_examples=100)
settings.load_profile("default")
```

**测试覆盖**：
- Property 1-19: 所有正确性属性

**示例**：
```python
@given(
    platform=st.sampled_from(["tiktok", "instagram", "facebook"]),
    count=st.sampled_from([3, 10])
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_6_platform_aspect_ratio_mapping(platform, count):
    """
    **Feature: ad-creative, Property 6: 平台宽高比映射**
    
    For any 目标平台选择，系统应自动选择对应的宽高比
    """
    expected_ratios = {
        "tiktok": "9:16",
        "instagram": "1:1",
        "facebook": "4:5"
    }
    
    ad_creative = AdCreative()
    result = await ad_creative.execute(
        action="generate_creative",
        parameters={
            "product_url": "https://example.com/product",
            "count": count,
            "platform": platform
        },
        context={"user_id": "test_user"}
    )
    
    assert result["status"] == "success"
    for creative in result["creatives"]:
        assert creative["aspect_ratio"] == expected_ratios[platform]
```

```python
@given(
    count=st.integers(min_value=10, max_value=50)
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_13_bulk_discount(count):
    """
    **Feature: ad-creative, Property 13: 批量生成折扣**
    
    For any 批量生成请求（10 张以上），系统应按 0.4 credits/张计费
    """
    credit_checker = CreditChecker()
    cost = credit_checker.calculate_cost("image_generation", count)
    
    expected_cost = count * 0.4  # 批量折扣价
    assert cost == expected_cost
```

---

## Implementation Details（实现细节）

### 1. 产品信息提取实现

```python
class ShopifyExtractor(BaseExtractor):
    """Shopify 产品信息提取"""
    
    def supports(self, url: str) -> bool:
        return "shopify" in url or ".myshopify.com" in url
    
    async def extract(self, product_url: str) -> ProductInfo:
        """使用 Shopify API 提取产品信息"""
        # 解析 URL 获取 shop 和 product handle
        shop, handle = self._parse_url(product_url)
        
        # 调用 Shopify Storefront API
        async with aiohttp.ClientSession() as session:
            response = await session.get(
                f"https://{shop}/products/{handle}.json"
            )
            data = await response.json()
        
        product = data["product"]
        return ProductInfo(
            title=product["title"],
            price=float(product["variants"][0]["price"]),
            currency="USD",
            images=[img["src"] for img in product["images"]],
            description=product["body_html"],
            selling_points=self._extract_selling_points(product),
            source="shopify"
        )

class AmazonExtractor(BaseExtractor):
    """Amazon 产品信息提取（网页解析）"""
    
    def supports(self, url: str) -> bool:
        return "amazon.com" in url or "amazon.cn" in url
    
    async def extract(self, product_url: str) -> ProductInfo:
        """使用网页解析提取产品信息"""
        async with aiohttp.ClientSession() as session:
            response = await session.get(product_url, headers=self.headers)
            html = await response.text()
        
        soup = BeautifulSoup(html, "html.parser")
        
        return ProductInfo(
            title=soup.select_one("#productTitle").text.strip(),
            price=self._parse_price(soup),
            currency="USD",
            images=self._extract_images(soup),
            description=self._extract_description(soup),
            selling_points=self._extract_bullet_points(soup),
            source="amazon"
        )
```

### 2. 图片生成实现

```python
class ImageGenerator:
    """图片素材生成器"""
    
    ASPECT_RATIOS = {
        "9:16": (1080, 1920),  # TikTok
        "1:1": (1080, 1080),   # Instagram Feed
        "4:5": (1080, 1350)    # Facebook Feed
    }
    
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client
    
    async def generate(
        self,
        product_info: ProductInfo,
        count: int,
        style: str,
        aspect_ratio: str
    ) -> list[GeneratedImage]:
        """生成图片素材"""
        width, height = self.ASPECT_RATIOS.get(
            aspect_ratio, 
            self._parse_custom_ratio(aspect_ratio)
        )
        
        prompt = self._build_prompt(product_info, style)
        
        images = []
        for i in range(count):
            response = await self.gemini.generate_image(
                model="imagen-3.0-generate-001",
                prompt=prompt,
                config={
                    "number_of_images": 1,
                    "aspect_ratio": aspect_ratio,
                    "safety_filter_level": "block_some"
                }
            )
            
            images.append(GeneratedImage(
                image_data=response.generated_images[0].image.image_bytes,
                file_name=f"creative_{i+1}.png",
                file_type="image/png",
                width=width,
                height=height,
                aspect_ratio=aspect_ratio
            ))
        
        return images
    
    def _build_prompt(self, product_info: ProductInfo, style: str) -> str:
        """构建生成提示词"""
        return f"""
        Create a professional advertising image for:
        Product: {product_info.title}
        Price: {product_info.currency} {product_info.price}
        Key Features: {', '.join(product_info.selling_points[:3])}
        Style: {style}
        
        Requirements:
        - High quality, professional advertising image
        - Clear product focus
        - Appealing to target audience
        - Suitable for social media advertising
        """
```

### 3. 素材评分实现

```python
class ScoringEngine:
    """素材评分引擎"""
    
    DIMENSION_WEIGHTS = {
        "visual_impact": 0.30,
        "composition": 0.25,
        "color_harmony": 0.25,
        "text_clarity": 0.20
    }
    
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client
    
    async def score(self, image_url: str) -> CreativeScore:
        """评分素材"""
        prompt = """
        Analyze this advertising image and score it on the following dimensions (0-100):
        
        1. Visual Impact (视觉冲击力): Is the image eye-catching? Is the subject prominent?
        2. Composition (构图平衡): Is the layout balanced? Is the visual weight stable?
        3. Color Harmony (色彩和谐): Are the colors coordinated? Is the contrast appropriate?
        4. Text Clarity (文案清晰): Is the text readable? Is the information clear?
           (If no text, default to 100)
        
        Return JSON format:
        {
            "visual_impact": {"score": 85, "analysis": "..."},
            "composition": {"score": 80, "analysis": "..."},
            "color_harmony": {"score": 90, "analysis": "..."},
            "text_clarity": {"score": 75, "analysis": "..."},
            "overall_analysis": "..."
        }
        """
        
        response = await self.gemini.generate_content(
            model="gemini-2.5-flash",
            contents=[
                {"type": "image_url", "url": image_url},
                {"type": "text", "text": prompt}
            ]
        )
        
        result = json.loads(response.text)
        dimensions = {
            dim: DimensionScore(
                score=result[dim]["score"],
                analysis=result[dim]["analysis"]
            )
            for dim in self.DIMENSION_WEIGHTS.keys()
        }
        
        return CreativeScore(
            total_score=self.calculate_weighted_score(dimensions),
            dimensions=dimensions,
            ai_analysis=result["overall_analysis"]
        )
    
    def calculate_weighted_score(self, dimensions: dict) -> float:
        """计算加权总分"""
        total = sum(
            dimensions[dim].score * weight
            for dim, weight in self.DIMENSION_WEIGHTS.items()
        )
        return round(total, 1)
```

### 4. 文件上传实现

```python
class UploadManager:
    """文件上传管理器"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp = mcp_client
        self.upload_timeout = 60  # 秒
    
    async def upload_creative(
        self,
        user_id: str,
        image: GeneratedImage,
        metadata: dict
    ) -> UploadResult:
        """上传素材到 S3"""
        # 1. 获取预签名 URL
        upload_info = await self.mcp.call_tool(
            "get_upload_url",
            {
                "user_id": user_id,
                "file_name": image.file_name,
                "file_type": image.file_type,
                "file_size": len(image.image_data),
                "purpose": "creative"
            }
        )
        
        # 2. 上传文件到 S3
        await self._upload_to_s3(
            upload_url=upload_info["upload_url"],
            file_data=image.image_data,
            content_type=image.file_type
        )
        
        # 3. 存储元数据
        result = await self.mcp.call_tool(
            "create_creative",
            {
                "user_id": user_id,
                "file_url": upload_info["file_url"],
                "metadata": {
                    **metadata,
                    "width": image.width,
                    "height": image.height,
                    "aspect_ratio": image.aspect_ratio
                }
            }
        )
        
        return UploadResult(
            creative_id=result["creative_id"],
            url=result["url"],
            created_at=result["created_at"]
        )
    
    async def _upload_to_s3(
        self,
        upload_url: str,
        file_data: bytes,
        content_type: str
    ):
        """使用预签名 URL 上传到 S3"""
        async with aiohttp.ClientSession() as session:
            async with session.put(
                upload_url,
                data=file_data,
                headers={"Content-Type": content_type},
                timeout=aiohttp.ClientTimeout(total=self.upload_timeout)
            ) as response:
                if response.status != 200:
                    raise UploadError(f"S3 upload failed: {response.status}")
```

### 5. Credit 检查实现

```python
class CreditChecker:
    """Credit 余额检查器"""
    
    CREDIT_RATES = {
        "image_generation": 0.5,
        "image_generation_bulk": 0.4,
        "creative_analysis": 0.2,
        "competitor_analysis": 1.0
    }
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp = mcp_client
    
    async def check_and_reserve(
        self,
        user_id: str,
        operation: str,
        count: int = 1
    ) -> CreditCheckResult:
        """检查并预留 Credit"""
        required = self.calculate_cost(operation, count)
        
        result = await self.mcp.call_tool(
            "check_credit",
            {
                "user_id": user_id,
                "estimated_credits": required,
                "operation_type": operation
            }
        )
        
        if not result["allowed"]:
            return CreditCheckResult(
                allowed=False,
                required_credits=required,
                available_credits=result["current_balance"],
                error_code="6011",
                error_message="Credit 余额不足，请充值后继续使用"
            )
        
        return CreditCheckResult(
            allowed=True,
            required_credits=required,
            available_credits=result["current_balance"]
        )
    
    def calculate_cost(self, operation: str, count: int) -> float:
        """计算操作成本"""
        if operation == "image_generation" and count >= 10:
            return count * self.CREDIT_RATES["image_generation_bulk"]
        return count * self.CREDIT_RATES.get(operation, 0)
    
    async def deduct(
        self,
        user_id: str,
        operation_id: str,
        credits: float,
        details: dict
    ) -> bool:
        """扣减 Credit"""
        result = await self.mcp.call_tool(
            "deduct_credit",
            {
                "user_id": user_id,
                "credits": credits,
                "operation_type": "generate_creative",
                "operation_id": operation_id,
                "details": details
            }
        )
        return result["status"] == "success"
    
    async def refund(
        self,
        user_id: str,
        operation_id: str,
        credits: float
    ) -> bool:
        """退还 Credit"""
        result = await self.mcp.call_tool(
            "refund_credit",
            {
                "user_id": user_id,
                "credits": credits,
                "operation_id": operation_id
            }
        )
        return result["status"] == "success"
```

---

## Performance Optimization（性能优化）

### 1. 缓存策略

```python
class CacheManager:
    """缓存管理器"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.product_cache_ttl = 3600  # 1 小时
        self.analysis_cache_ttl = 86400  # 24 小时
    
    async def get_cached_product_info(
        self,
        product_url: str
    ) -> ProductInfo | None:
        """获取缓存的产品信息"""
        cache_key = f"product:{hashlib.md5(product_url.encode()).hexdigest()}"
        cached = await self.redis.get(cache_key)
        
        if cached:
            return ProductInfo.model_validate_json(cached)
        return None
    
    async def cache_product_info(
        self,
        product_url: str,
        product_info: ProductInfo
    ):
        """缓存产品信息"""
        cache_key = f"product:{hashlib.md5(product_url.encode()).hexdigest()}"
        await self.redis.setex(
            cache_key,
            self.product_cache_ttl,
            product_info.model_dump_json()
        )
```

### 2. 并行生成

```python
async def generate_batch(
    self,
    product_info: ProductInfo,
    count: int,
    style: str,
    aspect_ratio: str
) -> list[GeneratedImage]:
    """并行生成多张图片"""
    # 分批并行，每批最多 3 张
    batch_size = 3
    all_images = []
    
    for i in range(0, count, batch_size):
        batch_count = min(batch_size, count - i)
        tasks = [
            self._generate_single(product_info, style, aspect_ratio)
            for _ in range(batch_count)
        ]
        batch_images = await asyncio.gather(*tasks, return_exceptions=True)
        
        for img in batch_images:
            if isinstance(img, GeneratedImage):
                all_images.append(img)
    
    return all_images
```

---

## Security Considerations（安全考虑）

### 1. 文件验证

```python
class FileValidator:
    """文件验证器"""
    
    ALLOWED_TYPES = {"image/jpeg", "image/png"}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def validate(self, file_data: bytes, content_type: str) -> bool:
        """验证文件"""
        # 检查文件类型
        if content_type not in self.ALLOWED_TYPES:
            raise ValidationError("不支持的文件格式，仅支持 JPG/PNG")
        
        # 检查文件大小
        if len(file_data) > self.MAX_FILE_SIZE:
            raise ValidationError("文件大小超过 10MB 限制")
        
        # 检查文件头（防止伪造）
        if not self._verify_magic_bytes(file_data, content_type):
            raise ValidationError("文件内容与类型不匹配")
        
        return True
    
    def _verify_magic_bytes(self, data: bytes, content_type: str) -> bool:
        """验证文件魔数"""
        magic_bytes = {
            "image/jpeg": [b"\xff\xd8\xff"],
            "image/png": [b"\x89PNG\r\n\x1a\n"]
        }
        return any(data.startswith(mb) for mb in magic_bytes.get(content_type, []))
```

### 2. URL 验证

```python
class URLValidator:
    """URL 验证器"""
    
    ALLOWED_DOMAINS = [
        "shopify.com", "myshopify.com",
        "amazon.com", "amazon.cn",
        "tiktok.com"
    ]
    
    def validate(self, url: str) -> bool:
        """验证 URL"""
        parsed = urlparse(url)
        
        # 检查协议
        if parsed.scheme not in ["http", "https"]:
            raise ValidationError("仅支持 HTTP/HTTPS 协议")
        
        # 检查域名
        domain = parsed.netloc.lower()
        if not any(allowed in domain for allowed in self.ALLOWED_DOMAINS):
            raise ValidationError("不支持的域名")
        
        return True
```

---

## Dependencies（依赖）

### Python 包

```
# AI 模型
google-generativeai>=0.8.0

# HTTP 客户端
aiohttp>=3.9.0

# 网页解析
beautifulsoup4>=4.12.0
lxml>=5.0.0

# 图片处理
Pillow>=10.0.0

# 数据验证
pydantic>=2.9.0

# 缓存
redis>=5.0.0

# 测试
pytest>=8.0.0
pytest-asyncio>=0.23.0
hypothesis>=6.100.0
```

### 外部服务

| 服务 | 用途 | 配置 |
|------|------|------|
| Gemini Imagen 3 | 图片生成 | GEMINI_API_KEY |
| Gemini 2.5 Flash | 素材分析/评分 | GEMINI_API_KEY |
| AWS S3 | 文件存储 | 通过 MCP 调用 |
| Redis | 缓存 | REDIS_URL |

---

## Configuration（配置）

```python
class AdCreativeConfig(BaseSettings):
    """Ad Creative 配置"""
    
    # AI 模型
    gemini_api_key: str
    imagen_model: str = "imagen-3.0-generate-001"
    flash_model: str = "gemini-2.5-flash"
    
    # 生成配置
    max_generation_count: int = 10
    generation_timeout: int = 60
    
    # 上传配置
    upload_timeout: int = 60
    max_file_size: int = 10 * 1024 * 1024
    
    # 重试配置
    max_retries: int = 3
    retry_backoff: int = 2
    
    # 缓存配置
    redis_url: str
    product_cache_ttl: int = 3600
    analysis_cache_ttl: int = 86400
    
    # Credit 配置
    image_credit_rate: float = 0.5
    bulk_credit_rate: float = 0.4
    bulk_threshold: int = 10
    
    class Config:
        env_prefix = "AD_CREATIVE_"
```
