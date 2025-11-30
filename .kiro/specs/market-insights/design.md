# 设计文档 - Market Insights（市场洞察）

## Overview（概述）

Market Insights 是 AI Orchestrator 的功能模块之一，作为独立的 Python 模块实现。该模块负责：

1. **竞品分析**：使用 AI 分析竞品产品信息、定价策略、目标受众
2. **热门素材发现**：从 TikTok Creative Center 获取热门广告素材
3. **市场趋势洞察**：通过 Google Trends 获取市场趋势数据
4. **AI 广告策略生成**：基于市场数据生成受众推荐、素材方向、预算规划
5. **策略效果追踪**：对比采纳和未采纳策略的广告表现

该模块通过 MCP 协议与 Web Platform 通信，不直接访问数据库。

---

## Architecture（架构）

### 模块结构

```
ai-orchestrator/
└── app/
    └── modules/
        └── market_insights/
            ├── __init__.py
            ├── capability.py              # 主入口，实现 execute() 接口
            ├── models.py                  # 数据模型定义
            ├── analyzers/
            │   ├── __init__.py
            │   ├── competitor_analyzer.py # 竞品分析
            │   ├── creative_analyzer.py   # 素材分析
            │   └── strategy_generator.py  # 策略生成
            ├── fetchers/
            │   ├── __init__.py
            │   ├── tiktok_fetcher.py      # TikTok Creative Center API
            │   └── trends_fetcher.py      # Google Trends API (pytrends)
            ├── trackers/
            │   ├── __init__.py
            │   └── performance_tracker.py # 策略效果追踪
            └── utils/
                ├── __init__.py
                ├── cache_manager.py       # 缓存管理
                ├── rate_limiter.py        # 速率限制
                └── retry_strategy.py      # 重试策略
```


### 调用路径

#### 路径 1：对话式调用（通过 AI Orchestrator）

```
用户 → AI Orchestrator → Market Insights → MCP Client → Web Platform
```

#### 路径 2：第三方 API 调用

```
Market Insights → TikTok Creative Center API / pytrends → 返回数据
```

### 依赖关系

```
Market Insights
    ├─► MCP Client (调用 Web Platform 工具)
    ├─► Gemini Client (AI 分析和策略生成)
    ├─► TikTok Creative Center API (热门素材)
    ├─► pytrends (Google Trends 数据)
    └─► Redis (缓存)
```

---

## Components and Interfaces（组件和接口）

### 1. MarketInsights (主入口)

```python
class MarketInsights:
    """Market Insights 功能模块主入口"""
    
    async def execute(
        self,
        action: str,
        parameters: dict,
        context: dict
    ) -> dict:
        """
        执行市场洞察操作
        
        Args:
            action: 操作名称
            parameters: 操作参数
            context: 上下文信息（user_id, session_id等）
        
        Returns:
            操作结果
        """
```

**支持的 Actions**：
- `analyze_competitor`: 分析竞品
- `get_trending_creatives`: 获取热门素材
- `analyze_creative_trend`: 分析素材趋势
- `get_market_trends`: 获取市场趋势
- `generate_ad_strategy`: 生成广告策略
- `track_strategy_performance`: 追踪策略效果

### 2. CompetitorAnalyzer (竞品分析器)

```python
class CompetitorAnalyzer:
    """竞品分析器"""
    
    async def analyze(
        self,
        competitor_url: str,
        analysis_type: str = "product",
        depth: str = "detailed"
    ) -> dict:
        """
        分析竞品
        
        Returns:
            {
                "competitor_info": {...},
                "insights": {...},
                "recommendations": [...]
            }
        """
        pass
    
    async def extract_product_info(self, url: str) -> dict:
        """提取产品信息"""
        pass
    
    async def generate_insights(self, product_info: dict) -> dict:
        """使用 AI 生成洞察"""
        pass
```

### 3. TikTokFetcher (TikTok 数据抓取器)

```python
class TikTokFetcher:
    """TikTok Creative Center API 数据抓取"""
    
    async def get_trending_creatives(
        self,
        industry: str,
        region: str,
        time_range: str = "7d",
        limit: int = 20
    ) -> list[dict]:
        """获取热门素材"""
        pass
    
    async def get_creative_details(
        self,
        creative_id: str
    ) -> dict:
        """获取素材详情"""
        pass
```

### 4. TrendsFetcher (趋势数据抓取器)

```python
class TrendsFetcher:
    """Google Trends 数据抓取（使用 pytrends）"""
    
    async def get_interest_over_time(
        self,
        keywords: list[str],
        region: str,
        time_range: str = "30d"
    ) -> dict:
        """获取关键词趋势"""
        pass
    
    async def get_related_queries(
        self,
        keyword: str,
        region: str
    ) -> dict:
        """获取相关查询"""
        pass
```

### 5. StrategyGenerator (策略生成器)

```python
class StrategyGenerator:
    """AI 广告策略生成器"""
    
    async def generate(
        self,
        product_info: dict,
        competitor_analysis: dict | None = None,
        trend_analysis: dict | None = None
    ) -> dict:
        """
        生成广告策略
        
        Returns:
            {
                "audience_recommendations": {...},
                "creative_direction": {...},
                "budget_planning": {...},
                "campaign_structure": {...}
            }
        """
        pass
    
    async def generate_audience_recommendations(
        self,
        product_info: dict,
        trends: dict
    ) -> dict:
        """生成受众推荐"""
        pass
    
    async def generate_creative_direction(
        self,
        product_info: dict,
        competitor_analysis: dict
    ) -> dict:
        """生成素材方向建议"""
        pass
```

### 6. PerformanceTracker (策略效果追踪器)

```python
class PerformanceTracker:
    """策略效果追踪器"""
    
    async def track(
        self,
        strategy_id: str,
        campaign_ids: list[str],
        comparison_period: str = "7d"
    ) -> dict:
        """
        追踪策略效果
        
        Returns:
            {
                "campaigns_with_strategy": {...},
                "campaigns_without_strategy": {...},
                "improvement": {...},
                "insights": "..."
            }
        """
        pass
    
    async def calculate_improvement(
        self,
        with_strategy: dict,
        without_strategy: dict
    ) -> dict:
        """计算提升百分比"""
        pass
```


---

## Data Models（数据模型）

### CompetitorInfo (竞品信息)

```python
from pydantic import BaseModel, Field
from typing import Literal

class CompetitorInfo(BaseModel):
    """竞品信息"""
    name: str
    price: str
    features: list[str]
    target_audience: str
    selling_points: list[str]

class CompetitorInsights(BaseModel):
    """竞品洞察"""
    pricing_strategy: str
    marketing_approach: str
    strengths: list[str]
    weaknesses: list[str]

class CompetitorAnalysis(BaseModel):
    """竞品分析结果"""
    status: Literal["success", "error"]
    competitor_info: CompetitorInfo
    insights: CompetitorInsights
    recommendations: list[str]
```

### TrendingCreative (热门素材)

```python
class TrendingCreative(BaseModel):
    """热门素材"""
    id: str
    title: str
    thumbnail_url: str
    views: int = Field(ge=0)
    engagement_rate: float = Field(ge=0)
    platform: Literal["tiktok"]

class CreativeAnalysis(BaseModel):
    """素材分析结果"""
    visual_style: str
    color_palette: list[str]
    key_elements: list[str]
    success_factors: list[str]
    copywriting_style: str

class TrendingCreativesResponse(BaseModel):
    """热门素材响应"""
    status: Literal["success", "error"]
    creatives: list[TrendingCreative]
    total: int
```

### MarketTrend (市场趋势)

```python
class KeywordTrend(BaseModel):
    """关键词趋势"""
    keyword: str
    search_volume: int = Field(ge=0)
    growth_rate: float
    trend_direction: Literal["rising", "stable", "declining"]
    related_queries: list[str]

class TrendInsights(BaseModel):
    """趋势洞察"""
    hot_topics: list[str]
    emerging_trends: list[str]
    seasonal_patterns: str

class MarketTrendsResponse(BaseModel):
    """市场趋势响应"""
    status: Literal["success", "error"]
    trends: list[KeywordTrend]
    insights: TrendInsights
```

### AdStrategy (广告策略)

```python
class AudienceRecommendation(BaseModel):
    """受众推荐"""
    age_range: str
    gender: Literal["all", "male", "female"]
    interests: list[str]
    behaviors: list[str]

class CreativeDirection(BaseModel):
    """素材方向"""
    visual_style: str
    key_messages: list[str]
    content_types: list[str]
    color_recommendations: list[str]

class BudgetPlanning(BaseModel):
    """预算规划"""
    recommended_daily_budget: float = Field(ge=0)
    campaign_duration: str
    expected_reach: str

class AdGroup(BaseModel):
    """广告组"""
    name: str
    targeting: str
    budget_allocation: str

class CampaignStructure(BaseModel):
    """广告系列结构"""
    ad_groups: list[AdGroup]

class AdStrategy(BaseModel):
    """广告策略"""
    audience_recommendations: AudienceRecommendation
    creative_direction: CreativeDirection
    budget_planning: BudgetPlanning
    campaign_structure: CampaignStructure

class AdStrategyResponse(BaseModel):
    """广告策略响应"""
    status: Literal["success", "error"]
    strategy: AdStrategy
    rationale: str
```

### StrategyPerformance (策略效果)

```python
class PerformanceMetrics(BaseModel):
    """性能指标"""
    avg_roas: float = Field(ge=0)
    avg_ctr: float = Field(ge=0)
    avg_conversion_rate: float = Field(ge=0)

class PerformanceImprovement(BaseModel):
    """性能提升"""
    roas_lift: str
    ctr_lift: str
    conversion_rate_lift: str

class StrategyPerformanceResponse(BaseModel):
    """策略效果响应"""
    status: Literal["success", "error"]
    performance: dict  # campaigns_with_strategy, campaigns_without_strategy, improvement
    insights: str
```


---

## Correctness Properties（正确性属性）

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection（属性反思）

在编写正确性属性之前，我们需要识别并消除冗余：

**识别的冗余**：
- 属性 1.2、1.3、1.4 可以合并为一个属性：验证竞品分析结果的完整性
- 属性 2.2、2.3 可以合并为一个属性：验证热门素材数据的完整性
- 属性 2.4、2.5 可以合并为一个属性：验证素材分析结果的完整性
- 属性 3.2、3.3、3.4、3.5 可以合并为一个属性：验证市场趋势数据的完整性
- 属性 4.2、4.3、4.4、4.5 可以合并为一个属性：验证广告策略的完整性
- 属性 5.1、5.2、5.3、5.4 可以合并为一个属性：验证策略效果追踪的完整性
- 属性 7.1、7.2 可以合并为一个属性：验证缓存 TTL 配置

**合并后的属性**：

---

### Correctness Properties（正确性属性）

Property 1: 竞品分析返回完整结构
*For any* 竞品 URL，调用 analyze_competitor 应返回包含 competitor_info（name、price、features、target_audience、selling_points）、insights（pricing_strategy、marketing_approach、strengths、weaknesses）、recommendations 的完整分析结果
**Validates: Requirements 1.1, 1.2, 1.3, 1.4**

Property 2: 竞品分析失败返回错误信息
*For any* 无效的竞品 URL 或分析失败场景，系统应返回包含 error_code 和 message 的错误响应
**Validates: Requirements 1.5**

Property 3: 热门素材数据完整性
*For any* 行业和地区参数，调用 get_trending_creatives 应返回素材列表，每个素材包含 id、title、thumbnail_url、views、engagement_rate、platform 字段
**Validates: Requirements 2.1, 2.2, 2.3**

Property 4: 素材分析结果完整性
*For any* 素材 ID，调用 analyze_creative_trend 应返回包含 visual_style、color_palette、key_elements、success_factors、copywriting_style 的分析结果，以及 recommendations 列表
**Validates: Requirements 2.4, 2.5**

Property 5: 市场趋势数据完整性
*For any* 关键词列表和地区，调用 get_market_trends 应返回趋势列表（每个包含 search_volume、growth_rate、trend_direction、related_queries）和洞察（hot_topics、emerging_trends、seasonal_patterns）
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

Property 6: 广告策略完整性
*For any* 产品信息，调用 generate_ad_strategy 应返回包含 audience_recommendations（age_range、gender、interests、behaviors）、creative_direction（visual_style、key_messages、content_types）、budget_planning（recommended_daily_budget、campaign_duration）、campaign_structure（ad_groups）的完整策略
**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**

Property 7: 策略效果追踪完整性
*For any* 策略 ID 和广告系列 ID 列表，调用 track_strategy_performance 应返回 campaigns_with_strategy 和 campaigns_without_strategy 的指标对比（avg_roas、avg_ctr、avg_conversion_rate），以及 improvement 百分比和 insights 文字说明
**Validates: Requirements 5.1, 5.2, 5.3, 5.4**

Property 8: 策略追踪失败返回错误信息
*For any* 追踪失败场景，系统应返回包含具体失败原因的错误响应
**Validates: Requirements 5.5**

Property 9: pytrends 速率限制
*For any* 连续的 Google Trends API 调用，系统应遵守每分钟最多 5 次请求的速率限制
**Validates: Requirements 6.2**

Property 10: API 调用失败自动重试
*For any* 第三方 API 调用失败场景，系统应自动重试最多 3 次，并使用指数退避策略
**Validates: Requirements 6.3**

Property 11: API 限额降级处理
*For any* 达到 API 限额的场景，系统应使用缓存数据或返回降级提示
**Validates: Requirements 6.4, 6.6**

Property 12: API 超时处理
*For any* 第三方 API 调用，系统应设置 30 秒超时，超时后返回错误或使用缓存数据
**Validates: Requirements 6.5**

Property 13: 缓存 TTL 配置
*For any* 趋势数据，缓存 TTL 应为 24 小时；*For any* 热门素材数据，缓存 TTL 应为 12 小时
**Validates: Requirements 7.1, 7.2**

Property 14: 缓存命中直接返回
*For any* 缓存命中的请求，系统应直接返回缓存数据，不调用第三方 API
**Validates: Requirements 7.3**

Property 15: 缓存过期刷新
*For any* 缓存过期的请求，系统应重新调用 API 并更新缓存
**Validates: Requirements 7.4**

Property 16: 缓存失败降级
*For any* 缓存操作失败的场景，系统应降级到直接 API 调用
**Validates: Requirements 7.5**


---

## Error Handling（错误处理）

### 错误类型

1. **第三方 API 错误**
   - 401/403: API 密钥无效或权限不足
   - 429: 速率限制
   - 500: 服务错误
   - 超时: 网络超时

2. **MCP 调用错误**
   - 连接失败
   - 工具不存在
   - 参数无效
   - 执行超时

3. **数据验证错误**
   - URL 格式无效
   - 必需字段缺失
   - 数值超出范围

4. **AI 模型错误**
   - 模型调用失败
   - 响应超时
   - 响应格式错误

### 错误处理策略

```python
class ErrorHandler:
    """统一错误处理器"""
    
    async def handle_api_error(self, error: Exception, retry_count: int) -> dict:
        """处理第三方 API 错误"""
        if isinstance(error, RateLimitError):
            return {
                "status": "error",
                "error_code": "1003",
                "message": "超过速率限制，请稍后重试",
                "retry_allowed": True,
                "retry_after": 60
            }
        elif isinstance(error, TimeoutError):
            return {
                "status": "error",
                "error_code": "4002",
                "message": "API 响应超时",
                "retry_allowed": True
            }
        elif retry_count < 3:
            # 自动重试
            await asyncio.sleep(2 ** retry_count)
            return {"retry": True}
        else:
            return {
                "status": "error",
                "error_code": "4002",
                "message": "外部 API 调用失败",
                "retry_allowed": False
            }
    
    async def handle_validation_error(self, error: Exception) -> dict:
        """处理数据验证错误"""
        return {
            "status": "error",
            "error_code": "4005",
            "message": f"数据验证失败: {str(error)}",
            "retry_allowed": False
        }
```

### 降级策略

```python
class DegradationHandler:
    """降级处理器"""
    
    async def handle_tiktok_unavailable(self, cache_manager: CacheManager) -> dict:
        """TikTok API 不可用时的降级处理"""
        # 尝试使用缓存数据（最长 7 天）
        cached_data = await cache_manager.get_stale_cache("trending_creatives", max_age=604800)
        if cached_data:
            return {
                "status": "success",
                "data": cached_data,
                "degraded": True,
                "message": "使用缓存数据，数据可能不是最新"
            }
        return {
            "status": "error",
            "error_code": "4002",
            "message": "热门素材数据暂时不可用",
            "retry_allowed": True
        }
    
    async def handle_trends_unavailable(self, cache_manager: CacheManager, gemini_client) -> dict:
        """Google Trends 不可用时的降级处理"""
        # 尝试使用缓存数据（最长 3 天）
        cached_data = await cache_manager.get_stale_cache("market_trends", max_age=259200)
        if cached_data:
            return {
                "status": "success",
                "data": cached_data,
                "degraded": True,
                "message": "使用缓存数据，数据可能不是最新"
            }
        # 备选：使用 AI 生成趋势分析
        ai_trends = await gemini_client.generate_trend_analysis()
        return {
            "status": "success",
            "data": ai_trends,
            "degraded": True,
            "message": "基于 AI 分析生成的趋势数据"
        }
```

### 重试机制

```python
async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    backoff_factor: int = 2,
    timeout: int = 30
) -> Any:
    """指数退避重试"""
    for attempt in range(max_retries):
        try:
            return await asyncio.wait_for(func(), timeout=timeout)
        except (RetryableError, TimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            wait_time = backoff_factor ** attempt
            await asyncio.sleep(wait_time)
```


---

## Testing Strategy（测试策略）

### Unit Testing（单元测试）

使用 pytest + pytest-asyncio 进行单元测试：

**测试覆盖**：
- CompetitorAnalyzer 的分析逻辑
- TikTokFetcher 的数据抓取
- TrendsFetcher 的趋势获取
- StrategyGenerator 的策略生成
- PerformanceTracker 的效果追踪
- 缓存管理和速率限制
- 错误处理和重试机制

**示例**：
```python
@pytest.mark.asyncio
async def test_competitor_analyzer_returns_valid_structure():
    """测试竞品分析返回有效结构"""
    analyzer = CompetitorAnalyzer(gemini_client=mock_gemini)
    result = await analyzer.analyze(
        competitor_url="https://example.com/product",
        analysis_type="product"
    )
    
    assert "competitor_info" in result
    assert "insights" in result
    assert "recommendations" in result
    assert "name" in result["competitor_info"]
    assert "strengths" in result["insights"]
```

### Property-Based Testing（基于属性的测试）

使用 Hypothesis 进行属性测试，每个测试运行 100 次迭代：

**测试框架**：Hypothesis (Python)

**配置**：
```python
from hypothesis import given, settings
import hypothesis.strategies as st

# 全局配置：每个属性测试运行 100 次
settings.register_profile("default", max_examples=100)
settings.load_profile("default")
```

**测试覆盖**：
- Property 1-16: 所有正确性属性

**示例**：
```python
@given(
    industry=st.sampled_from(["fashion", "electronics", "beauty", "home"]),
    region=st.sampled_from(["US", "UK", "DE", "FR"]),
    limit=st.integers(min_value=1, max_value=50)
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_3_trending_creatives_completeness(industry, region, limit):
    """
    **Feature: market-insights, Property 3: 热门素材数据完整性**
    
    For any 行业和地区参数，调用 get_trending_creatives 应返回完整的素材数据
    """
    # Arrange
    market_insights = MarketInsights()
    
    # Act
    result = await market_insights.execute(
        action="get_trending_creatives",
        parameters={
            "industry": industry,
            "region": region,
            "limit": limit
        },
        context={"user_id": "test_user"}
    )
    
    # Assert
    assert result["status"] == "success"
    assert "creatives" in result
    
    for creative in result["creatives"]:
        assert "id" in creative
        assert "title" in creative
        assert "thumbnail_url" in creative
        assert "views" in creative
        assert "engagement_rate" in creative
        assert "platform" in creative
```


---

## Implementation Details（实现细节）

### 1. 竞品分析实现

```python
class CompetitorAnalyzer:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client
    
    async def analyze(
        self,
        competitor_url: str,
        analysis_type: str = "product",
        depth: str = "detailed"
    ) -> dict:
        """分析竞品"""
        # 使用 AI 分析竞品页面
        prompt = f"""
        分析以下竞品页面并提供详细洞察：
        URL: {competitor_url}
        分析类型: {analysis_type}
        分析深度: {depth}
        
        请提供：
        1. 竞品信息（名称、价格、特点、目标受众、卖点）
        2. 洞察（定价策略、营销方式、优势、劣势）
        3. 差异化竞争建议
        
        以 JSON 格式返回。
        """
        
        response = await self.gemini.generate_content(prompt)
        analysis = json.loads(response.text)
        
        return {
            "status": "success",
            "competitor_info": analysis["competitor_info"],
            "insights": analysis["insights"],
            "recommendations": analysis["recommendations"]
        }
```

### 2. TikTok Creative Center API 集成

```python
class TikTokFetcher:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://business-api.tiktok.com/open_api/v1.3"
    
    async def get_trending_creatives(
        self,
        industry: str,
        region: str,
        time_range: str = "7d",
        limit: int = 20
    ) -> list[dict]:
        """获取热门素材"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Access-Token": await self._get_access_token()
            }
            params = {
                "industry_id": self._get_industry_id(industry),
                "country_code": region,
                "period": self._convert_time_range(time_range),
                "page_size": limit
            }
            
            async with session.get(
                f"{self.base_url}/creative/trending/list/",
                headers=headers,
                params=params,
                timeout=30
            ) as response:
                data = await response.json()
                return self._transform_creatives(data["data"]["list"])
    
    def _transform_creatives(self, raw_list: list) -> list[dict]:
        """转换 API 响应为标准格式"""
        return [
            {
                "id": item["creative_id"],
                "title": item["title"],
                "thumbnail_url": item["thumbnail_url"],
                "views": item["play_count"],
                "engagement_rate": item["engagement_rate"],
                "platform": "tiktok"
            }
            for item in raw_list
        ]
```

### 3. Google Trends 集成（pytrends）

```python
from pytrends.request import TrendReq

class TrendsFetcher:
    def __init__(self):
        self.pytrends = TrendReq(hl='en-US', tz=360)
        self.rate_limiter = RateLimiter(max_requests=5, period=60)
    
    async def get_interest_over_time(
        self,
        keywords: list[str],
        region: str,
        time_range: str = "30d"
    ) -> dict:
        """获取关键词趋势"""
        await self.rate_limiter.acquire()
        
        timeframe = self._convert_time_range(time_range)
        
        # pytrends 是同步库，需要在线程池中运行
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._fetch_trends,
            keywords,
            region,
            timeframe
        )
        
        return result
    
    def _fetch_trends(self, keywords: list[str], region: str, timeframe: str) -> dict:
        """同步获取趋势数据"""
        self.pytrends.build_payload(
            kw_list=keywords,
            geo=region,
            timeframe=timeframe
        )
        
        interest_df = self.pytrends.interest_over_time()
        related = self.pytrends.related_queries()
        
        trends = []
        for keyword in keywords:
            if keyword in interest_df.columns:
                values = interest_df[keyword].values
                growth_rate = self._calculate_growth_rate(values)
                trends.append({
                    "keyword": keyword,
                    "search_volume": int(values[-1]) if len(values) > 0 else 0,
                    "growth_rate": growth_rate,
                    "trend_direction": self._get_trend_direction(growth_rate),
                    "related_queries": self._extract_related(related, keyword)
                })
        
        return {"trends": trends}
    
    def _calculate_growth_rate(self, values: list) -> float:
        """计算增长率"""
        if len(values) < 2:
            return 0.0
        first_half = sum(values[:len(values)//2]) / (len(values)//2)
        second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
        if first_half == 0:
            return 0.0
        return ((second_half - first_half) / first_half) * 100
    
    def _get_trend_direction(self, growth_rate: float) -> str:
        """获取趋势方向"""
        if growth_rate > 10:
            return "rising"
        elif growth_rate < -10:
            return "declining"
        return "stable"
```

### 4. 广告策略生成实现

```python
class StrategyGenerator:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client
    
    async def generate(
        self,
        product_info: dict,
        competitor_analysis: dict | None = None,
        trend_analysis: dict | None = None
    ) -> dict:
        """生成广告策略"""
        prompt = f"""
        基于以下信息生成完整的广告策略：
        
        产品信息：
        - 名称：{product_info['name']}
        - 类别：{product_info['category']}
        - 价格：${product_info['price']}
        - 目标市场：{product_info['target_market']}
        
        {"竞品分析：" + json.dumps(competitor_analysis, ensure_ascii=False) if competitor_analysis else ""}
        {"市场趋势：" + json.dumps(trend_analysis, ensure_ascii=False) if trend_analysis else ""}
        
        请提供：
        1. 受众推荐（年龄范围、性别、兴趣、行为）
        2. 素材方向（视觉风格、关键信息、内容类型、色彩推荐）
        3. 预算规划（每日预算、投放周期、预期触达）
        4. 广告系列结构（广告组划分、定向策略、预算分配）
        
        以 JSON 格式返回。
        """
        
        response = await self.gemini.generate_content(prompt)
        strategy = json.loads(response.text)
        
        return {
            "status": "success",
            "strategy": strategy,
            "rationale": "基于市场趋势分析和竞品研究生成的策略建议"
        }
```


### 5. 缓存管理实现

```python
class CacheManager:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.ttl_config = {
            "trending_creatives": 43200,  # 12 小时
            "market_trends": 86400,       # 24 小时
            "competitor_analysis": 3600,  # 1 小时
        }
    
    async def get(self, cache_type: str, key: str) -> dict | None:
        """获取缓存数据"""
        cache_key = f"{cache_type}:{key}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        return None
    
    async def set(self, cache_type: str, key: str, data: dict) -> None:
        """设置缓存数据"""
        cache_key = f"{cache_type}:{key}"
        ttl = self.ttl_config.get(cache_type, 3600)
        await self.redis.setex(cache_key, ttl, json.dumps(data))
    
    async def get_stale_cache(self, cache_type: str, key: str, max_age: int) -> dict | None:
        """获取过期缓存数据（用于降级）"""
        cache_key = f"{cache_type}:stale:{key}"
        cached = await self.redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            if time.time() - data["cached_at"] < max_age:
                return data["data"]
        return None
    
    async def set_with_stale(self, cache_type: str, key: str, data: dict) -> None:
        """设置缓存并保留过期副本"""
        # 设置正常缓存
        await self.set(cache_type, key, data)
        
        # 设置过期副本（用于降级）
        stale_key = f"{cache_type}:stale:{key}"
        stale_data = {
            "data": data,
            "cached_at": time.time()
        }
        await self.redis.setex(stale_key, 604800, json.dumps(stale_data))  # 7 天
```

### 6. 速率限制实现

```python
class RateLimiter:
    def __init__(self, max_requests: int, period: int):
        self.max_requests = max_requests
        self.period = period
        self.requests = []
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """获取请求许可"""
        async with self.lock:
            now = time.time()
            # 清理过期请求
            self.requests = [t for t in self.requests if now - t < self.period]
            
            if len(self.requests) >= self.max_requests:
                # 等待直到可以发送请求
                wait_time = self.period - (now - self.requests[0])
                await asyncio.sleep(wait_time)
                self.requests = self.requests[1:]
            
            self.requests.append(now)
```

---

## Performance Optimization（性能优化）

### 1. 并行数据获取

```python
async def get_comprehensive_insights(
    self,
    product_info: dict,
    competitor_url: str | None = None
) -> dict:
    """并行获取多种洞察数据"""
    tasks = []
    
    # 并行获取趋势和热门素材
    tasks.append(self._get_market_trends(product_info["category"]))
    tasks.append(self._get_trending_creatives(product_info["category"]))
    
    if competitor_url:
        tasks.append(self._analyze_competitor(competitor_url))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return {
        "trends": results[0] if not isinstance(results[0], Exception) else None,
        "creatives": results[1] if not isinstance(results[1], Exception) else None,
        "competitor": results[2] if len(results) > 2 and not isinstance(results[2], Exception) else None
    }
```

### 2. 缓存预热

```python
async def warm_cache(self, industries: list[str], regions: list[str]) -> None:
    """预热常用数据缓存"""
    for industry in industries:
        for region in regions:
            try:
                await self.get_trending_creatives(industry, region)
            except Exception as e:
                logger.warning(f"Cache warm failed for {industry}/{region}: {e}")
```

---

## Security Considerations（安全考虑）

### API 密钥管理

- TikTok API 密钥存储在环境变量中
- 使用 AWS Secrets Manager 管理敏感配置
- API 密钥定期轮换

### 数据隐私

- 不存储竞品的原始素材
- 仅存储分析结果
- 遵守各平台的 API 使用条款
- 遵守 GDPR、CCPA 等数据隐私法规

### 输入验证

- 验证 URL 格式
- 限制请求参数范围
- 防止注入攻击

---

## Cost Control（成本控制）

### AI 模型调用成本

| 操作 | 模型 | 预估成本 |
|------|------|---------|
| 竞品分析 | Gemini 2.5 Pro | ~$0.10 |
| 素材分析 | Gemini 2.5 Flash | ~$0.05 |
| 策略生成 | Gemini 2.5 Pro | ~$0.15 |
| 趋势分析 | Gemini 2.5 Flash | ~$0.03 |

### 成本控制策略

1. **缓存优先**：优先使用缓存数据，减少 API 调用
2. **模型选择**：简单任务使用 Flash 模型，复杂任务使用 Pro 模型
3. **批量处理**：合并多个请求，减少 API 调用次数
4. **成本监控**：监控 API 调用成本，设置告警阈值

---

**文档版本**：v1.0
**最后更新**：2024-11-30
**维护者**：AAE 开发团队
