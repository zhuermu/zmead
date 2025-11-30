# 设计文档 - Landing Page（落地页生成）

## Overview（概述）

Landing Page 是 AI Orchestrator 的功能模块之一，作为独立的 Python 模块实现。该模块负责：

1. **产品信息解析**：从产品链接（Shopify/Amazon）自动抓取产品信息
2. **落地页生成**：使用 AI 生成高转化率的落地页结构和文案
3. **文案优化**：使用 Gemini 2.5 Pro 优化标题、CTA 等文案
4. **多语言翻译**：使用 Gemini 2.5 Flash 翻译落地页内容
5. **A/B 测试**：创建和分析落地页变体测试
6. **落地页托管**：通过 AWS S3 + CloudFront 托管落地页
7. **落地页导出**：导出完整 HTML 文件供用户自行托管
8. **转化追踪**：集成 Facebook Pixel 和内部分析追踪

该模块通过 MCP 协议与 Web Platform 通信，不直接访问数据库。所有文件存储通过 S3 预签名 URL 完成。

---

## Architecture（架构）

### 模块结构

```
ai-orchestrator/
└── app/
    └── modules/
        └── landing_page/
            ├── __init__.py
            ├── capability.py              # 主入口，实现 execute() 接口
            ├── models.py                  # 数据模型定义
            ├── extractors/
            │   ├── __init__.py
            │   ├── base.py                # 提取器基类
            │   ├── shopify_extractor.py   # Shopify 产品信息提取
            │   └── amazon_extractor.py    # Amazon 产品信息提取
            ├── generators/
            │   ├── __init__.py
            │   ├── page_generator.py      # 落地页结构生成
            │   ├── copy_generator.py      # 文案生成（Gemini 2.5 Pro）
            │   └── template_engine.py     # 模板渲染引擎
            ├── optimizers/
            │   ├── __init__.py
            │   ├── copy_optimizer.py      # 文案优化
            │   └── translator.py          # 多语言翻译（Gemini 2.5 Flash）
            ├── managers/
            │   ├── __init__.py
            │   ├── ab_test_manager.py     # A/B 测试管理
            │   ├── hosting_manager.py     # 托管管理（S3 + CloudFront）
            │   └── export_manager.py      # 导出管理
            ├── tracking/
            │   ├── __init__.py
            │   ├── pixel_injector.py      # Facebook Pixel 注入
            │   └── event_tracker.py       # 事件追踪脚本生成
            └── utils/
                ├── __init__.py
                ├── validators.py          # 输入验证
                ├── color_utils.py         # 颜色格式处理
                └── retry.py               # 重试策略
```

### 调用路径

```
用户 → AI Orchestrator → Landing Page → MCP Client → Web Platform
                              ↓
                        Gemini 2.5 Pro (文案生成/优化)
                        Gemini 2.5 Flash (翻译/内容提取)
                        Gemini Imagen 3 (落地页配图)
                              ↓
                        AWS S3 + CloudFront (托管)
```

### 依赖关系

```
Landing Page
    ├─► MCP Client (调用 Web Platform 工具)
    ├─► Gemini Client (AI 生成和分析)
    │   ├─► Gemini 2.5 Pro (文案生成/优化)
    │   ├─► Gemini 2.5 Flash (翻译/内容提取)
    │   └─► Gemini Imagen 3 (配图生成)
    ├─► HTTP Client (S3 上传、产品信息抓取)
    ├─► AWS S3 Client (文件存储)
    ├─► AWS CloudFront Client (CDN 分发)
    └─► Redis (缓存)
```

---

## Components and Interfaces（组件和接口）

### 1. LandingPage (主入口)

```python
class LandingPage:
    """Landing Page 功能模块主入口"""
    
    async def execute(
        self,
        action: str,
        parameters: dict,
        context: dict
    ) -> dict:
        """
        执行落地页生成操作
        
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
| `parse_product` | 解析产品信息 | product_url, platform | product_info |
| `generate_landing_page` | 生成落地页 | product_info, template, language, pixel_id | landing_page_id, url, sections |
| `update_landing_page` | 更新落地页 | landing_page_id, updates | updated_fields, url |
| `optimize_copy` | 优化文案 | landing_page_id, section, current_text, optimization_goal | optimized_text, improvements |
| `translate_landing_page` | 翻译落地页 | landing_page_id, target_language, sections_to_translate | translated_landing_page_id, url, translations |
| `create_ab_test` | 创建 A/B 测试 | test_name, landing_page_id, variants, traffic_split, duration_days | test_id, variant_urls |
| `analyze_ab_test` | 分析 A/B 测试 | test_id | results, winner, recommendation |
| `publish_landing_page` | 发布落地页 | landing_page_id, custom_domain | url, cdn_url, ssl_status |
| `export_landing_page` | 导出落地页 | landing_page_id, format | download_url, expires_at |

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

### 3. PageGenerator (落地页生成器)

```python
class PageGenerator:
    """落地页结构生成器"""
    
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client
    
    async def generate(
        self,
        product_info: ProductInfo,
        template: str,
        language: str,
        pixel_id: str | None
    ) -> LandingPageContent:
        """
        生成落地页结构
        
        Args:
            product_info: 产品信息
            template: 模板名称（modern, minimal, vibrant）
            language: 语言代码
            pixel_id: Facebook Pixel ID
        
        Returns:
            落地页内容结构
        """
        pass
    
    async def generate_hero_section(
        self,
        product_info: ProductInfo,
        template: str
    ) -> HeroSection:
        """生成 Hero 区域，使用 AI 优化标题"""
        pass
    
    async def extract_features(
        self,
        product_info: ProductInfo,
        count: int = 3
    ) -> list[Feature]:
        """提取核心卖点"""
        pass
```

### 4. CopyOptimizer (文案优化器)

```python
class CopyOptimizer:
    """文案优化器"""
    
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client
    
    async def optimize(
        self,
        current_text: str,
        section: str,
        optimization_goal: str
    ) -> OptimizationResult:
        """
        优化文案
        
        Args:
            current_text: 当前文案
            section: 区域（hero, cta, features）
            optimization_goal: 优化目标（increase_conversion, emotional_appeal）
        
        Returns:
            优化结果，包含优化后文案和改进说明
        """
        pass
```

### 5. Translator (翻译器)

```python
class Translator:
    """多语言翻译器"""
    
    SUPPORTED_LANGUAGES = ["en", "es", "fr", "zh"]
    
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client
    
    async def translate(
        self,
        content: dict,
        target_language: str,
        sections: list[str]
    ) -> TranslationResult:
        """
        翻译落地页内容
        
        Args:
            content: 原始内容
            target_language: 目标语言
            sections: 要翻译的区域
        
        Returns:
            翻译结果
        """
        pass
```

### 6. ABTestManager (A/B 测试管理器)

```python
class ABTestManager:
    """A/B 测试管理器"""
    
    MIN_CONVERSIONS_FOR_SIGNIFICANCE = 100
    SIGNIFICANCE_LEVEL = 0.05  # 95% 置信度
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp = mcp_client
    
    async def create_test(
        self,
        test_name: str,
        landing_page_id: str,
        variants: list[dict],
        traffic_split: list[int],
        duration_days: int
    ) -> ABTest:
        """创建 A/B 测试"""
        pass
    
    async def analyze_test(self, test_id: str) -> ABTestAnalysis:
        """
        分析 A/B 测试结果
        
        使用卡方检验判断统计显著性
        """
        pass
    
    def chi_square_test(
        self,
        variant_a: VariantStats,
        variant_b: VariantStats
    ) -> ChiSquareResult:
        """执行卡方检验"""
        pass
```

### 7. HostingManager (托管管理器)

```python
class HostingManager:
    """落地页托管管理器"""
    
    def __init__(
        self,
        s3_client: S3Client,
        cloudfront_client: CloudFrontClient,
        mcp_client: MCPClient
    ):
        self.s3 = s3_client
        self.cloudfront = cloudfront_client
        self.mcp = mcp_client
    
    async def publish(
        self,
        landing_page_id: str,
        html_content: str,
        custom_domain: str | None = None
    ) -> PublishResult:
        """
        发布落地页
        
        流程：
        1. 上传 HTML 到 S3
        2. 配置 CloudFront 分发
        3. 配置自定义域名（如有）
        4. 启用 HTTPS
        """
        pass
    
    async def configure_custom_domain(
        self,
        landing_page_id: str,
        domain: str
    ) -> DomainConfig:
        """配置自定义域名"""
        pass
```

### 8. ExportManager (导出管理器)

```python
class ExportManager:
    """落地页导出管理器"""
    
    DOWNLOAD_EXPIRY_HOURS = 24
    
    def __init__(self, s3_client: S3Client):
        self.s3 = s3_client
    
    async def export(
        self,
        landing_page_id: str,
        format: str = "html"
    ) -> ExportResult:
        """
        导出落地页
        
        流程：
        1. 生成完整 HTML（内联 CSS/JS）
        2. 注入 Facebook Pixel 代码
        3. 打包为 ZIP 文件
        4. 上传到 S3 并生成预签名下载 URL
        """
        pass
    
    def inline_assets(self, html: str) -> str:
        """内联所有 CSS 和 JavaScript"""
        pass
```

### 9. PixelInjector (Pixel 注入器)

```python
class PixelInjector:
    """Facebook Pixel 注入器"""
    
    def inject(
        self,
        html: str,
        pixel_id: str,
        events: list[str] = ["PageView"]
    ) -> str:
        """
        注入 Facebook Pixel 代码
        
        Args:
            html: 原始 HTML
            pixel_id: Facebook Pixel ID
            events: 要追踪的事件列表
        
        Returns:
            注入后的 HTML
        """
        pass
    
    def generate_event_script(
        self,
        event_type: str,
        event_data: dict | None = None
    ) -> str:
        """生成事件追踪脚本"""
        pass
```

### 10. EventTracker (事件追踪器)

```python
class EventTracker:
    """内部事件追踪器"""
    
    def generate_tracking_script(
        self,
        landing_page_id: str,
        campaign_id: str | None = None
    ) -> str:
        """
        生成内部分析追踪脚本
        
        追踪事件：
        - PageView: 页面访问
        - AddToCart: CTA 点击
        - Purchase: 购买完成
        """
        pass
```

---

## Data Models（数据模型）

### ProductInfo (产品信息)

```python
from pydantic import BaseModel, Field, HttpUrl
from typing import Literal

class Review(BaseModel):
    """用户评价"""
    rating: int = Field(ge=1, le=5, description="评分")
    text: str = Field(..., description="评价内容")

class ProductInfo(BaseModel):
    """产品信息"""
    title: str = Field(..., description="产品标题")
    price: float = Field(ge=0, description="产品价格")
    currency: str = Field(default="USD", description="货币")
    main_image: HttpUrl = Field(..., description="主图 URL")
    images: list[HttpUrl] = Field(default_factory=list, description="产品图片 URL 列表")
    description: str = Field(..., description="产品描述")
    features: list[str] = Field(default_factory=list, description="产品特性")
    reviews: list[Review] = Field(default_factory=list, description="用户评价")
    source: Literal["shopify", "amazon", "manual"] = Field(..., description="数据来源")
```

### LandingPageContent (落地页内容)

```python
class HeroSection(BaseModel):
    """Hero 区域"""
    headline: str = Field(..., description="主标题")
    subheadline: str = Field(..., description="副标题")
    image: HttpUrl = Field(..., description="主图")
    cta_text: str = Field(..., description="CTA 按钮文案")

class Feature(BaseModel):
    """特性/卖点"""
    title: str = Field(..., description="特性标题")
    description: str = Field(..., description="特性描述")
    icon: str = Field(..., description="图标名称")

class CTASection(BaseModel):
    """CTA 区域"""
    text: str = Field(..., description="CTA 文案")
    url: HttpUrl = Field(..., description="跳转链接")

class LandingPageContent(BaseModel):
    """落地页内容结构"""
    landing_page_id: str = Field(..., description="落地页 ID")
    template: str = Field(..., description="模板名称")
    language: str = Field(default="en", description="语言")
    hero: HeroSection = Field(..., description="Hero 区域")
    features: list[Feature] = Field(..., description="特性列表")
    reviews: list[Review] = Field(default_factory=list, description="评价列表")
    faq: list[dict] = Field(default_factory=list, description="FAQ 列表")
    cta: CTASection = Field(..., description="CTA 区域")
    pixel_id: str | None = Field(None, description="Facebook Pixel ID")
```

### OptimizationResult (优化结果)

```python
class OptimizationResult(BaseModel):
    """文案优化结果"""
    optimized_text: str = Field(..., description="优化后的文案")
    improvements: list[str] = Field(..., description="改进说明")
    confidence_score: float = Field(ge=0, le=1, description="置信度")
```

### TranslationResult (翻译结果)

```python
class TranslationResult(BaseModel):
    """翻译结果"""
    translated_landing_page_id: str = Field(..., description="翻译版本 ID")
    url: HttpUrl = Field(..., description="翻译版本 URL")
    translations: dict = Field(..., description="翻译内容")
    source_language: str = Field(..., description="源语言")
    target_language: str = Field(..., description="目标语言")
```

### ABTest (A/B 测试)

```python
class Variant(BaseModel):
    """测试变体"""
    name: str = Field(..., description="变体名称")
    changes: dict = Field(..., description="变更内容")
    url: HttpUrl = Field(..., description="变体 URL")

class VariantStats(BaseModel):
    """变体统计"""
    variant: str = Field(..., description="变体名称")
    visits: int = Field(ge=0, description="访问量")
    conversions: int = Field(ge=0, description="转化数")
    conversion_rate: float = Field(ge=0, description="转化率")

class ABTestWinner(BaseModel):
    """获胜变体"""
    variant: str = Field(..., description="获胜变体名称")
    confidence: float = Field(ge=0, le=100, description="置信度")
    improvement: str = Field(..., description="提升幅度")

class ABTest(BaseModel):
    """A/B 测试"""
    test_id: str = Field(..., description="测试 ID")
    test_name: str = Field(..., description="测试名称")
    landing_page_id: str = Field(..., description="落地页 ID")
    variants: list[Variant] = Field(..., description="变体列表")
    traffic_split: list[int] = Field(..., description="流量分配")
    duration_days: int = Field(gt=0, description="测试时长")
    status: Literal["running", "completed", "paused"] = Field(..., description="状态")
    created_at: str = Field(..., description="创建时间")

class ABTestAnalysis(BaseModel):
    """A/B 测试分析结果"""
    test_id: str = Field(..., description="测试 ID")
    results: list[VariantStats] = Field(..., description="各变体结果")
    winner: ABTestWinner | None = Field(None, description="获胜变体")
    recommendation: str = Field(..., description="使用建议")
    is_significant: bool = Field(..., description="是否统计显著")
    p_value: float | None = Field(None, description="p 值")
```

### PublishResult (发布结果)

```python
class PublishResult(BaseModel):
    """发布结果"""
    landing_page_id: str = Field(..., description="落地页 ID")
    url: HttpUrl = Field(..., description="访问 URL")
    cdn_url: HttpUrl = Field(..., description="CDN URL")
    ssl_status: Literal["active", "pending", "failed"] = Field(..., description="SSL 状态")
    custom_domain: str | None = Field(None, description="自定义域名")
```

### ExportResult (导出结果)

```python
class ExportResult(BaseModel):
    """导出结果"""
    download_url: HttpUrl = Field(..., description="下载链接")
    expires_at: str = Field(..., description="过期时间")
    file_size: int = Field(gt=0, description="文件大小（字节）")
```

---

## Correctness Properties（正确性属性）

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property Reflection（属性反思）

在编写正确性属性之前，识别并消除冗余：

**识别的冗余**：
- 2.2, 2.3, 2.4, 2.5 可合并为"落地页生成完整性"属性
- 3.1, 3.2, 3.3, 3.4, 3.5 可合并为"更新操作正确性"属性
- 5.1, 5.2, 5.3 可合并为"翻译完整性"属性
- 7.1, 7.2, 7.3, 7.5 可合并为"发布流程完整性"属性
- 8.1, 8.2, 8.3, 8.4 可合并为"导出完整性"属性
- 9.1, 9.2, 9.3 可合并为"事件追踪完整性"属性

**合并后的属性**：
- 产品信息提取完整性 (1.1, 1.4) → Property 1
- 平台特定提取路由 (1.2, 1.3) → Property 2
- 提取错误处理 (1.5) → Property 3
- 落地页生成完整性 (2.1-2.5) → Property 4
- 更新操作正确性 (3.1-3.5) → Property 5
- 文案优化响应格式 (4.1, 4.4) → Property 6
- 文案优化回退 (4.5) → Property 7
- 翻译完整性 (5.1-5.4) → Property 8
- 翻译错误处理 (5.5) → Property 9
- A/B 测试创建 (6.1, 6.2) → Property 10
- A/B 测试统计分析 (6.3-6.6) → Property 11
- 发布流程完整性 (7.1-7.5) → Property 12
- 导出完整性 (8.1-8.5) → Property 13
- 事件追踪完整性 (9.1-9.3) → Property 14

---

### Correctness Properties（正确性属性）


Property 1: 产品信息提取完整性
*For any* 有效的产品链接（Shopify/Amazon），调用 parse_product action 时应返回包含 title、price、images、description、reviews 字段的完整产品信息
**Validates: Requirements 1.1, 1.4**

Property 2: 平台特定提取路由
*For any* 产品链接，系统应根据 URL 自动选择正确的提取器：Shopify 链接使用 Shopify API，Amazon 链接使用网页解析
**Validates: Requirements 1.2, 1.3**

Property 3: 提取错误处理
*For any* 无效或无法访问的产品链接，系统应返回错误状态和建议信息，而非抛出异常
**Validates: Requirements 1.5**

Property 4: 落地页生成完整性
*For any* 有效的产品信息和模板，生成的落地页应包含：使用指定模板、AI 优化的 Hero 标题、3 个核心卖点、用户评价区域、以及注入的 Facebook Pixel 代码
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

Property 5: 更新操作正确性
*For any* 落地页更新请求，系统应：正确更新指定字段、保持未更新字段的原有结构、验证图片 URL 有效性、验证颜色格式为 HEX、返回更新字段列表和新 URL
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

Property 6: 文案优化响应格式
*For any* 文案优化请求，系统应使用 AI 模型处理并返回包含 optimized_text 和 improvements 字段的响应
**Validates: Requirements 4.1, 4.4**

Property 7: 文案优化回退
*For any* 文案优化失败场景，系统应返回原始文案而非错误
**Validates: Requirements 4.5**

Property 8: 翻译完整性
*For any* 翻译请求，系统应：使用 AI 翻译所有指定文本、保持原有格式和结构、生成新的语言版本 URL、支持英语/西班牙语/法语/中文
**Validates: Requirements 5.1, 5.2, 5.3, 5.4**

Property 9: 翻译错误处理
*For any* 翻译失败场景（如不支持的语言），系统应返回错误信息而非抛出异常
**Validates: Requirements 5.5**

Property 10: A/B 测试创建
*For any* A/B 测试创建请求，系统应创建指定数量的变体，并按配置的流量比例分配（使用 cookie 保持会话一致性）
**Validates: Requirements 6.1, 6.2**


Property 11: A/B 测试统计分析
*For any* A/B 测试分析请求，系统应：使用卡方检验分析转化率数据、当样本充足（转化 >= 100）且 p-value < 0.05 时识别获胜变体、当样本不足时返回"数据不足"提示、提供使用建议
**Validates: Requirements 6.3, 6.4, 6.5, 6.6**

Property 12: 发布流程完整性
*For any* 发布请求，系统应：上传 HTML 到 S3、通过 CloudFront 分发、生成默认域名、支持自定义域名配置、启用 HTTPS（ssl_status 为 active）
**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

Property 13: 导出完整性
*For any* 导出请求，系统应：生成包含内联 CSS/JS 的完整 HTML、包含 Facebook Pixel 代码、打包为 ZIP 文件、生成 24 小时过期的下载链接
**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**

Property 14: 事件追踪完整性
*For any* 生成的落地页，应包含追踪脚本：页面访问触发 PageView 事件、CTA 点击触发 AddToCart 事件、购买完成触发 Purchase 事件，事件同时发送到 Facebook Pixel 和 Web Platform
**Validates: Requirements 9.1, 9.2, 9.3**

---

## Error Handling（错误处理）

### 错误类型

1. **产品信息提取错误**
   - URL 格式无效
   - 网站无法访问
   - 产品页面结构变化
   - API 限流

2. **AI 模型错误**
   - Gemini 2.5 Pro 生成失败
   - Gemini 2.5 Flash 翻译超时
   - Gemini Imagen 3 配图生成失败
   - 模型响应格式错误
   - API 配额耗尽

3. **文件上传/托管错误**
   - S3 上传超时
   - CloudFront 配置失败
   - SSL 证书申请失败
   - 自定义域名验证失败

4. **MCP 调用错误**
   - 连接失败
   - 工具不存在
   - 参数无效
   - 执行超时

5. **A/B 测试错误**
   - 测试不存在
   - 数据不足
   - 统计计算失败


### 错误码映射

| 错误场景 | 错误码 | 错误类型 | 是否可重试 |
|---------|--------|---------|-----------|
| 产品链接无效 | 6006 | PRODUCT_URL_INVALID | 否 |
| 产品信息提取失败 | 6007 | PRODUCT_INFO_EXTRACTION_FAILED | 是 |
| 落地页域名未验证 | 6008 | LANDING_PAGE_DOMAIN_NOT_VERIFIED | 否 |
| AI 模型失败 | 4001 | AI_MODEL_FAILED | 是 |
| 生成失败 | 4003 | GENERATION_FAILED | 是 |
| 文件上传失败 | 5003 | STORAGE_ERROR | 是 |
| 数据未找到 | 5000 | DATA_NOT_FOUND | 否 |
| MCP 执行失败 | 3003 | MCP_EXECUTION_FAILED | 是 |

### 错误处理策略

```python
class ErrorHandler:
    """统一错误处理器"""
    
    MAX_RETRIES = 3
    
    async def handle_extraction_error(
        self,
        error: Exception,
        retry_count: int,
        product_url: str
    ) -> dict:
        """处理产品信息提取错误"""
        if retry_count < self.MAX_RETRIES:
            await asyncio.sleep(2 ** retry_count)
            return {"retry": True}
        else:
            return {
                "status": "error",
                "error_code": "6007",
                "message": "产品信息提取失败，请检查链接或手动输入产品信息",
                "suggestion": "请确保链接可访问，或尝试手动输入产品信息"
            }
    
    async def handle_generation_error(
        self,
        error: Exception,
        retry_count: int
    ) -> dict:
        """处理落地页生成错误"""
        if retry_count < self.MAX_RETRIES:
            await asyncio.sleep(2 ** retry_count)
            return {"retry": True}
        else:
            return {
                "status": "error",
                "error_code": "4003",
                "message": "落地页生成失败，请稍后重试",
                "retry_allowed": True
            }
    
    async def handle_optimization_error(
        self,
        error: Exception,
        original_text: str
    ) -> dict:
        """处理文案优化错误 - 返回原文案"""
        return {
            "status": "success",
            "optimized_text": original_text,
            "improvements": [],
            "confidence_score": 0,
            "fallback": True
        }
```

---

## Testing Strategy（测试策略）

### Unit Testing（单元测试）

使用 pytest + pytest-asyncio 进行单元测试：

**测试覆盖**：
- ProductExtractor 的产品信息提取逻辑
- PageGenerator 的落地页生成流程
- CopyOptimizer 的文案优化
- Translator 的翻译功能
- ABTestManager 的卡方检验计算
- HostingManager 的发布流程
- ExportManager 的导出流程
- PixelInjector 的 Pixel 注入
- 错误处理和重试机制


**示例**：
```python
@pytest.mark.asyncio
async def test_page_generator_creates_complete_structure():
    """测试落地页生成器创建完整结构"""
    generator = PageGenerator(gemini_client=mock_gemini)
    product_info = ProductInfo(
        title="Test Product",
        price=99.99,
        currency="USD",
        main_image="https://example.com/image.jpg",
        description="Test description",
        features=["Feature 1", "Feature 2", "Feature 3"],
        reviews=[],
        source="shopify"
    )
    
    result = await generator.generate(
        product_info=product_info,
        template="modern",
        language="en",
        pixel_id="123456789"
    )
    
    assert result.hero is not None
    assert result.hero.headline != ""
    assert len(result.features) == 3
    assert result.pixel_id == "123456789"
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
- Property 1-14: 所有正确性属性

**示例**：
```python
@given(
    platform=st.sampled_from(["shopify", "amazon"]),
    has_reviews=st.booleans()
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_1_product_extraction_completeness(platform, has_reviews):
    """
    **Feature: landing-page, Property 1: 产品信息提取完整性**
    
    For any 有效的产品链接，应返回包含所有必需字段的完整产品信息
    """
    landing_page = LandingPage()
    
    # 使用 mock 产品 URL
    product_url = f"https://{platform}.example.com/product/123"
    
    result = await landing_page.execute(
        action="parse_product",
        parameters={"product_url": product_url, "platform": platform},
        context={"user_id": "test_user"}
    )
    
    assert result["status"] == "success"
    product_info = result["product_info"]
    assert "title" in product_info
    assert "price" in product_info
    assert "images" in product_info or "main_image" in product_info
    assert "description" in product_info
    assert "reviews" in product_info
```


```python
@given(
    variant_a_visits=st.integers(min_value=200, max_value=10000),
    variant_a_conversions=st.integers(min_value=100, max_value=500),
    variant_b_visits=st.integers(min_value=200, max_value=10000),
    variant_b_conversions=st.integers(min_value=100, max_value=500)
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_11_ab_test_statistical_analysis(
    variant_a_visits, variant_a_conversions, variant_b_visits, variant_b_conversions
):
    """
    **Feature: landing-page, Property 11: A/B 测试统计分析**
    
    For any A/B 测试分析请求，系统应使用卡方检验分析转化率数据
    """
    # 确保转化数不超过访问数
    variant_a_conversions = min(variant_a_conversions, variant_a_visits)
    variant_b_conversions = min(variant_b_conversions, variant_b_visits)
    
    ab_test_manager = ABTestManager(mcp_client=mock_mcp)
    
    result = ab_test_manager.chi_square_test(
        variant_a=VariantStats(
            variant="A",
            visits=variant_a_visits,
            conversions=variant_a_conversions,
            conversion_rate=variant_a_conversions / variant_a_visits * 100
        ),
        variant_b=VariantStats(
            variant="B",
            visits=variant_b_visits,
            conversions=variant_b_conversions,
            conversion_rate=variant_b_conversions / variant_b_visits * 100
        )
    )
    
    # 验证返回了 p 值
    assert result.p_value is not None
    assert 0 <= result.p_value <= 1
    
    # 验证显著性判断正确
    if result.p_value < 0.05:
        assert result.is_significant == True
    else:
        assert result.is_significant == False
```

```python
@given(
    language=st.sampled_from(["en", "es", "fr", "zh"])
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_8_translation_completeness(language):
    """
    **Feature: landing-page, Property 8: 翻译完整性**
    
    For any 翻译请求，系统应支持英语/西班牙语/法语/中文
    """
    landing_page = LandingPage()
    
    result = await landing_page.execute(
        action="translate_landing_page",
        parameters={
            "landing_page_id": "lp_123",
            "target_language": language,
            "sections_to_translate": ["hero", "features", "faq"]
        },
        context={"user_id": "test_user"}
    )
    
    assert result["status"] == "success"
    assert "translated_landing_page_id" in result
    assert "url" in result
    assert language in result["url"] or result["translated_landing_page_id"].endswith(f"_{language}")
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
        shop, handle = self._parse_url(product_url)
        
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
            main_image=product["images"][0]["src"] if product["images"] else "",
            images=[img["src"] for img in product["images"]],
            description=self._clean_html(product["body_html"]),
            features=self._extract_features(product),
            reviews=[],  # Shopify API 不直接提供评论
            source="shopify"
        )
```


### 2. 落地页生成实现

```python
class PageGenerator:
    """落地页结构生成器"""
    
    TEMPLATES = ["modern", "minimal", "vibrant"]
    
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client
    
    async def generate(
        self,
        product_info: ProductInfo,
        template: str,
        language: str,
        pixel_id: str | None
    ) -> LandingPageContent:
        """生成落地页结构"""
        landing_page_id = f"lp_{uuid.uuid4().hex[:8]}"
        
        # 1. 生成 Hero 区域（AI 优化标题）
        hero = await self.generate_hero_section(product_info, template)
        
        # 2. 提取 3 个核心卖点
        features = await self.extract_features(product_info, count=3)
        
        # 3. 处理评价
        reviews = product_info.reviews[:3] if product_info.reviews else []
        
        # 4. 生成 FAQ
        faq = await self._generate_faq(product_info)
        
        # 5. 生成 CTA
        cta = CTASection(
            text=f"Buy Now - {product_info.currency} {product_info.price}",
            url=product_info.main_image  # 临时，实际应为结账链接
        )
        
        return LandingPageContent(
            landing_page_id=landing_page_id,
            template=template,
            language=language,
            hero=hero,
            features=features,
            reviews=reviews,
            faq=faq,
            cta=cta,
            pixel_id=pixel_id
        )
    
    async def generate_hero_section(
        self,
        product_info: ProductInfo,
        template: str
    ) -> HeroSection:
        """生成 Hero 区域，使用 AI 优化标题"""
        prompt = f"""
        为以下产品生成吸引人的落地页标题和副标题：
        产品名称：{product_info.title}
        产品描述：{product_info.description[:200]}
        价格：{product_info.currency} {product_info.price}
        
        要求：
        - 标题要有情感吸引力和紧迫感
        - 副标题突出核心价值
        - 适合 {template} 风格
        
        返回 JSON 格式：
        {{"headline": "...", "subheadline": "..."}}
        """
        
        response = await self.gemini.generate_content(
            model="gemini-2.5-pro",
            contents=[{"type": "text", "text": prompt}]
        )
        
        result = json.loads(response.text)
        return HeroSection(
            headline=result["headline"],
            subheadline=result["subheadline"],
            image=product_info.main_image,
            cta_text=f"Buy Now - {product_info.currency} {product_info.price}"
        )
    
    async def extract_features(
        self,
        product_info: ProductInfo,
        count: int = 3
    ) -> list[Feature]:
        """提取核心卖点"""
        if product_info.features and len(product_info.features) >= count:
            # 使用已有特性
            return [
                Feature(
                    title=f[:50],
                    description=f,
                    icon=self._suggest_icon(f)
                )
                for f in product_info.features[:count]
            ]
        
        # 使用 AI 提取
        prompt = f"""
        从以下产品信息中提取 {count} 个核心卖点：
        产品名称：{product_info.title}
        产品描述：{product_info.description}
        
        返回 JSON 数组格式：
        [{{"title": "...", "description": "...", "icon": "..."}}]
        """
        
        response = await self.gemini.generate_content(
            model="gemini-2.5-flash",
            contents=[{"type": "text", "text": prompt}]
        )
        
        features_data = json.loads(response.text)
        return [Feature(**f) for f in features_data[:count]]
```


### 3. A/B 测试卡方检验实现

```python
from scipy import stats

class ABTestManager:
    """A/B 测试管理器"""
    
    MIN_CONVERSIONS_FOR_SIGNIFICANCE = 100
    SIGNIFICANCE_LEVEL = 0.05
    
    def chi_square_test(
        self,
        variant_a: VariantStats,
        variant_b: VariantStats
    ) -> ChiSquareResult:
        """
        执行卡方检验
        
        使用 2x2 列联表：
                    转化    未转化
        Variant A   a       b
        Variant B   c       d
        """
        # 构建列联表
        a = variant_a.conversions
        b = variant_a.visits - variant_a.conversions
        c = variant_b.conversions
        d = variant_b.visits - variant_b.conversions
        
        contingency_table = [[a, b], [c, d]]
        
        # 执行卡方检验
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)
        
        is_significant = p_value < self.SIGNIFICANCE_LEVEL
        
        return ChiSquareResult(
            chi2_statistic=chi2,
            p_value=p_value,
            degrees_of_freedom=dof,
            is_significant=is_significant
        )
    
    async def analyze_test(self, test_id: str) -> ABTestAnalysis:
        """分析 A/B 测试结果"""
        # 获取测试数据
        test_data = await self.mcp.call_tool(
            "get_ab_test",
            {"test_id": test_id}
        )
        
        results = []
        for variant in test_data["variants"]:
            stats = await self._get_variant_stats(test_id, variant["name"])
            results.append(stats)
        
        # 检查样本量
        total_conversions = sum(r.conversions for r in results)
        if total_conversions < self.MIN_CONVERSIONS_FOR_SIGNIFICANCE:
            return ABTestAnalysis(
                test_id=test_id,
                results=results,
                winner=None,
                recommendation="数据不足，建议继续测试。当前转化数：{total_conversions}，需要至少 100 次转化。",
                is_significant=False,
                p_value=None
            )
        
        # 执行卡方检验
        chi_result = self.chi_square_test(results[0], results[1])
        
        winner = None
        if chi_result.is_significant:
            # 找出转化率更高的变体
            best_variant = max(results, key=lambda x: x.conversion_rate)
            worst_variant = min(results, key=lambda x: x.conversion_rate)
            improvement = (best_variant.conversion_rate - worst_variant.conversion_rate) / worst_variant.conversion_rate * 100
            
            winner = ABTestWinner(
                variant=best_variant.variant,
                confidence=round((1 - chi_result.p_value) * 100, 1),
                improvement=f"+{improvement:.1f}%"
            )
        
        return ABTestAnalysis(
            test_id=test_id,
            results=results,
            winner=winner,
            recommendation=self._generate_recommendation(winner, chi_result),
            is_significant=chi_result.is_significant,
            p_value=chi_result.p_value
        )
    
    def _generate_recommendation(
        self,
        winner: ABTestWinner | None,
        chi_result: ChiSquareResult
    ) -> str:
        """生成使用建议"""
        if winner:
            return f"使用 {winner.variant} 作为主版本，预期转化率提升 {winner.improvement}"
        else:
            return "两个变体表现相近，建议继续测试或选择任一版本"
```


### 4. 托管和发布实现

```python
class HostingManager:
    """落地页托管管理器"""
    
    DEFAULT_DOMAIN = "aae-pages.com"
    
    def __init__(
        self,
        s3_client: S3Client,
        cloudfront_client: CloudFrontClient,
        mcp_client: MCPClient
    ):
        self.s3 = s3_client
        self.cloudfront = cloudfront_client
        self.mcp = mcp_client
    
    async def publish(
        self,
        landing_page_id: str,
        html_content: str,
        custom_domain: str | None = None
    ) -> PublishResult:
        """发布落地页"""
        user_id = self.context["user_id"]
        
        # 1. 上传 HTML 到 S3
        s3_key = f"landing-pages/{user_id}/{landing_page_id}/index.html"
        await self.s3.put_object(
            Bucket="aae-landing-pages",
            Key=s3_key,
            Body=html_content.encode("utf-8"),
            ContentType="text/html",
            CacheControl="max-age=3600"
        )
        
        # 2. 配置 CloudFront 分发
        cdn_url = await self._configure_cloudfront(s3_key)
        
        # 3. 生成默认域名
        default_url = f"https://{user_id}.{self.DEFAULT_DOMAIN}/{landing_page_id}"
        
        # 4. 配置自定义域名（如有）
        if custom_domain:
            await self.configure_custom_domain(landing_page_id, custom_domain)
            url = f"https://{custom_domain}"
        else:
            url = default_url
        
        # 5. 确保 HTTPS 启用
        ssl_status = await self._ensure_https(landing_page_id, custom_domain)
        
        # 6. 保存到 Web Platform
        await self.mcp.call_tool(
            "update_landing_page",
            {
                "user_id": user_id,
                "landing_page_id": landing_page_id,
                "updates": {
                    "url": url,
                    "cdn_url": cdn_url,
                    "ssl_status": ssl_status,
                    "status": "published"
                }
            }
        )
        
        return PublishResult(
            landing_page_id=landing_page_id,
            url=url,
            cdn_url=cdn_url,
            ssl_status=ssl_status,
            custom_domain=custom_domain
        )
    
    async def _ensure_https(
        self,
        landing_page_id: str,
        custom_domain: str | None
    ) -> str:
        """确保 HTTPS 启用"""
        if custom_domain:
            # 为自定义域名申请 SSL 证书
            cert_arn = await self._request_certificate(custom_domain)
            if cert_arn:
                return "active"
            return "pending"
        else:
            # 默认域名已有 SSL
            return "active"
```

### 5. 导出实现

```python
class ExportManager:
    """落地页导出管理器"""
    
    DOWNLOAD_EXPIRY_HOURS = 24
    
    def __init__(self, s3_client: S3Client, mcp_client: MCPClient):
        self.s3 = s3_client
        self.mcp = mcp_client
    
    async def export(
        self,
        landing_page_id: str,
        format: str = "html"
    ) -> ExportResult:
        """导出落地页"""
        # 1. 获取落地页数据
        landing_page = await self.mcp.call_tool(
            "get_landing_page",
            {"landing_page_id": landing_page_id}
        )
        
        # 2. 生成完整 HTML（内联 CSS/JS）
        html = await self._render_full_html(landing_page)
        html = self.inline_assets(html)
        
        # 3. 注入 Facebook Pixel 代码
        if landing_page.get("pixel_id"):
            pixel_injector = PixelInjector()
            html = pixel_injector.inject(
                html,
                landing_page["pixel_id"],
                events=["PageView", "AddToCart", "Purchase"]
            )
        
        # 4. 打包为 ZIP 文件
        zip_buffer = self._create_zip(html, landing_page_id)
        
        # 5. 上传到 S3
        zip_key = f"exports/{landing_page_id}.zip"
        await self.s3.put_object(
            Bucket="aae-exports",
            Key=zip_key,
            Body=zip_buffer.getvalue(),
            ContentType="application/zip"
        )
        
        # 6. 生成预签名下载 URL（24 小时过期）
        expires_at = datetime.utcnow() + timedelta(hours=self.DOWNLOAD_EXPIRY_HOURS)
        download_url = await self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": "aae-exports", "Key": zip_key},
            ExpiresIn=self.DOWNLOAD_EXPIRY_HOURS * 3600
        )
        
        return ExportResult(
            download_url=download_url,
            expires_at=expires_at.isoformat() + "Z",
            file_size=len(zip_buffer.getvalue())
        )
    
    def inline_assets(self, html: str) -> str:
        """内联所有 CSS 和 JavaScript"""
        soup = BeautifulSoup(html, "html.parser")
        
        # 内联 CSS
        for link in soup.find_all("link", rel="stylesheet"):
            css_content = self._fetch_asset(link["href"])
            style_tag = soup.new_tag("style")
            style_tag.string = css_content
            link.replace_with(style_tag)
        
        # 内联 JavaScript
        for script in soup.find_all("script", src=True):
            js_content = self._fetch_asset(script["src"])
            script.string = js_content
            del script["src"]
        
        return str(soup)
```


### 6. Facebook Pixel 注入实现

```python
class PixelInjector:
    """Facebook Pixel 注入器"""
    
    PIXEL_BASE_SCRIPT = """
    <!-- Facebook Pixel Code -->
    <script>
    !function(f,b,e,v,n,t,s)
    {if(f.fbq)return;n=f.fbq=function(){n.callMethod?
    n.callMethod.apply(n,arguments):n.queue.push(arguments)};
    if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
    n.queue=[];t=b.createElement(e);t.async=!0;
    t.src=v;s=b.getElementsByTagName(e)[0];
    s.parentNode.insertBefore(t,s)}(window, document,'script',
    'https://connect.facebook.net/en_US/fbevents.js');
    fbq('init', '{pixel_id}');
    {events}
    </script>
    <noscript><img height="1" width="1" style="display:none"
    src="https://www.facebook.com/tr?id={pixel_id}&ev=PageView&noscript=1"/>
    </noscript>
    <!-- End Facebook Pixel Code -->
    """
    
    def inject(
        self,
        html: str,
        pixel_id: str,
        events: list[str] = ["PageView"]
    ) -> str:
        """注入 Facebook Pixel 代码"""
        events_script = "\n".join([
            f"fbq('track', '{event}');" for event in events
        ])
        
        pixel_script = self.PIXEL_BASE_SCRIPT.format(
            pixel_id=pixel_id,
            events=events_script
        )
        
        # 在 </head> 前注入
        return html.replace("</head>", f"{pixel_script}\n</head>")
    
    def generate_event_script(
        self,
        event_type: str,
        event_data: dict | None = None
    ) -> str:
        """生成事件追踪脚本"""
        if event_data:
            return f"fbq('track', '{event_type}', {json.dumps(event_data)});"
        return f"fbq('track', '{event_type}');"


class EventTracker:
    """内部事件追踪器"""
    
    TRACKING_SCRIPT_TEMPLATE = """
    <script>
    (function() {
        var lpId = '{landing_page_id}';
        var campaignId = '{campaign_id}';
        var apiEndpoint = 'https://api.aae.com/api/v1/lp-events';
        
        function sendEvent(eventType, eventData) {
            fetch(apiEndpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    landing_page_id: lpId,
                    campaign_id: campaignId,
                    event_type: eventType,
                    event_data: eventData,
                    timestamp: new Date().toISOString()
                })
            });
        }
        
        // PageView 事件
        sendEvent('PageView', {url: window.location.href});
        
        // CTA 点击事件
        document.querySelectorAll('[data-cta]').forEach(function(el) {
            el.addEventListener('click', function() {
                sendEvent('AddToCart', {cta_text: el.textContent});
            });
        });
        
        // Purchase 事件（需要在结账页面触发）
        window.trackPurchase = function(orderData) {
            sendEvent('Purchase', orderData);
        };
    })();
    </script>
    """
    
    def generate_tracking_script(
        self,
        landing_page_id: str,
        campaign_id: str | None = None
    ) -> str:
        """生成内部分析追踪脚本"""
        return self.TRACKING_SCRIPT_TEMPLATE.format(
            landing_page_id=landing_page_id,
            campaign_id=campaign_id or ""
        )
```

---

## Performance Requirements（性能要求）

| 操作 | 时间要求 | 说明 |
|------|---------|------|
| 产品信息提取 | < 5 秒 | 含网络请求 |
| 落地页生成 | < 30 秒 | 含 AI 文案 + 配图生成 |
| 文案优化 | < 10 秒 | 单次 AI 调用 |
| 翻译 | < 15 秒 | 含多区域翻译 |
| A/B 测试分析 | < 5 秒 | 含统计计算 |
| 发布 | < 10 秒 | 含 S3 上传和 CDN 配置 |
| 导出 | < 15 秒 | 含 ZIP 打包 |
| 落地页加载 | < 2 秒 | 用户访问时 |

**注意**：以上时间要求为 P95 响应时间，不含网络传输延迟。

---

## Security Requirements（安全要求）

1. **HTTPS 强制**：所有落地页必须通过 HTTPS 访问
2. **XSS 防护**：用户输入内容必须进行 HTML 转义
3. **输入验证**：验证所有用户输入（URL、颜色格式等）
4. **敏感配置加密**：Pixel ID 等敏感配置加密存储

---

**文档版本**：v1.0
**最后更新**：2024-11-30
**维护者**：AAE 开发团队
