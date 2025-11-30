# 设计文档 - Ad Performance（广告投放报表）

## Overview（概述）

Ad Performance 是 AI Orchestrator 的功能模块之一，作为独立的 Python 模块实现。该模块负责：

1. **数据抓取**：从 Meta/TikTok/Google 广告平台 API 抓取广告数据
2. **数据聚合**：聚合多平台、多层级（Campaign/Adset/Ad）的广告数据
3. **AI 智能分析**：使用 Gemini 2.5 Pro 分析广告表现和趋势
4. **异常检测**：基于统计算法检测指标异常波动
5. **优化建议**：生成可执行的优化建议供 Campaign Automation 执行
6. **报表导出**：生成 CSV/PDF 格式的报表文件

该模块通过 MCP 协议与 Web Platform 通信，不直接访问数据库。

---

## Architecture（架构）

### 模块结构

```
ai-orchestrator/
└── app/
    └── modules/
        └── ad_performance/
            ├── __init__.py
            ├── capability.py          # 主入口，实现 execute() 接口
            ├── fetchers/
            │   ├── __init__.py
            │   ├── meta_fetcher.py    # Meta API 数据抓取
            │   ├── tiktok_fetcher.py  # TikTok API 数据抓取
            │   └── google_fetcher.py  # Google API 数据抓取
            ├── analyzers/
            │   ├── __init__.py
            │   ├── performance_analyzer.py  # 表现分析
            │   ├── anomaly_detector.py      # 异常检测
            │   └── recommendation_engine.py # 建议生成
            ├── exporters/
            │   ├── __init__.py
            │   ├── csv_exporter.py    # CSV 导出
            │   └── pdf_exporter.py    # PDF 导出
            └── utils/
                ├── __init__.py
                ├── metrics_calculator.py  # 指标计算
                └── data_aggregator.py     # 数据聚合
```

### 调用路径

#### 路径 1：对话式调用（通过 AI Orchestrator）

```
用户 → AI Orchestrator → Ad Performance → MCP Client → Web Platform
```

#### 路径 2：定时任务调用（直接调用）

```
Celery Worker → Ad Performance → MCP Client → Web Platform
```

### 依赖关系

```
Ad Performance
    ├─► MCP Client (调用 Web Platform 工具)
    ├─► Gemini Client (AI 分析)
    ├─► Meta/TikTok/Google SDK (广告平台 API)
    └─► Redis (缓存)
```

---

## Components and Interfaces（组件和接口）

### 1. AdPerformance (主入口)

```python
class AdPerformance:
    """Ad Performance 功能模块主入口"""
    
    async def execute(
        self,
        action: str,
        parameters: dict,
        context: dict
    ) -> dict:
        """
        执行报表分析操作
        
        Args:
            action: 操作名称
            parameters: 操作参数
            context: 上下文信息（user_id, session_id等）
        
        Returns:
            操作结果
        """
```

**支持的 Actions**：
- `fetch_ad_data`: 抓取广告数据
- `generate_daily_report`: 生成每日报告
- `analyze_performance`: 分析广告表现
- `detect_anomalies`: 检测异常
- `generate_recommendations`: 生成优化建议
- `export_report`: 导出报表
- `get_metrics_summary`: 获取指标摘要

### 2. PlatformFetcher (数据抓取器)

```python
class BaseFetcher(ABC):
    """广告平台数据抓取器基类"""
    
    @abstractmethod
    async def fetch_insights(
        self,
        date_range: dict,
        levels: list[str],
        metrics: list[str]
    ) -> dict:
        """抓取广告数据"""
        pass
    
    @abstractmethod
    async def get_account_info(self, account_id: str) -> dict:
        """获取账户信息"""
        pass

class MetaFetcher(BaseFetcher):
    """Meta Marketing API 数据抓取"""
    
    async def fetch_insights(self, date_range, levels, metrics) -> dict:
        # 使用 facebook-business SDK
        pass

class TikTokFetcher(BaseFetcher):
    """TikTok Ads API 数据抓取"""
    
    async def fetch_insights(self, date_range, levels, metrics) -> dict:
        # 使用 tiktok-business-api SDK
        pass
```

### 3. PerformanceAnalyzer (表现分析器)

```python
class PerformanceAnalyzer:
    """广告表现分析器"""
    
    async def analyze_entity(
        self,
        entity_type: str,
        entity_id: str,
        current_data: dict,
        historical_data: dict
    ) -> dict:
        """
        分析单个实体的表现
        
        Returns:
            {
                "current_period": {...},
                "previous_period": {...},
                "changes": {...},
                "insights": [...]
            }
        """
        pass
    
    async def generate_insights(
        self,
        metrics: dict,
        changes: dict
    ) -> list[str]:
        """使用 AI 生成洞察"""
        pass
```

### 4. AnomalyDetector (异常检测器)

```python
class AnomalyDetector:
    """异常检测器"""
    
    async def detect(
        self,
        metric: str,
        current_value: float,
        historical_values: list[float],
        sensitivity: str = "medium"
    ) -> dict | None:
        """
        检测指标异常
        
        Returns:
            {
                "metric": "cpa",
                "current_value": 25.50,
                "expected_value": 12.00,
                "deviation": "+112.5%",
                "severity": "high"
            }
        """
        pass
    
    def calculate_expected_value(
        self,
        historical_values: list[float]
    ) -> tuple[float, float]:
        """计算期望值和标准差"""
        pass
```

### 5. RecommendationEngine (建议生成引擎)

```python
class RecommendationEngine:
    """优化建议生成引擎"""
    
    async def generate(
        self,
        metrics_data: dict,
        optimization_goal: str,
        constraints: dict
    ) -> list[dict]:
        """
        生成优化建议
        
        Returns:
            [
                {
                    "priority": "high",
                    "action": "pause_adset",
                    "target": {...},
                    "reason": "...",
                    "expected_impact": {...},
                    "confidence": 0.92
                }
            ]
        """
        pass
    
    async def identify_underperforming(
        self,
        entities: list[dict],
        threshold: float
    ) -> list[dict]:
        """识别低效实体"""
        pass
    
    async def identify_high_performing(
        self,
        entities: list[dict],
        threshold: float
    ) -> list[dict]:
        """识别高效实体"""
        pass
```

### 6. ReportExporter (报表导出器)

```python
class ReportExporter:
    """报表导出器"""
    
    async def export_csv(
        self,
        data: dict,
        file_name: str
    ) -> str:
        """导出 CSV 格式"""
        pass
    
    async def export_pdf(
        self,
        data: dict,
        file_name: str,
        include_charts: bool = True
    ) -> str:
        """导出 PDF 格式（含图表）"""
        pass
    
    async def upload_to_s3(
        self,
        file_path: str,
        user_id: str
    ) -> dict:
        """上传到 S3 并生成下载链接"""
        pass
```

---

## Data Models（数据模型）

### MetricsData (指标数据)

```python
from pydantic import BaseModel, Field
from datetime import date
from typing import Literal

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
```

### PerformanceAnalysis (表现分析结果)

```python
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
```

### Anomaly (异常)

```python
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
```

### Recommendation (优化建议)

```python
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
    action: Literal["pause_adset", "increase_budget", "decrease_budget", "refresh_creative"]
    target: RecommendationTarget
    reason: str
    expected_impact: ExpectedImpact
    confidence: float = Field(ge=0, le=1, description="置信度")
```

### DailyReport (每日报告)

```python
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
```

---

## Correctness Properties（正确性属性）

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property Reflection（属性反思）

在编写正确性属性之前，我们需要识别并消除冗余：

**识别的冗余**：
- 属性 8.1、8.2、8.3 与属性 1.1、2.1、4.1 重复（定时任务调用与普通调用使用相同的接口）
- 属性 8.4 被其他属性覆盖（各个 action 的属性已验证返回结构）
- 属性 9.5 与 9.4 重复（都验证通知数据字段完整性）

**合并的属性**：
- 属性 1.2 和 1.3 可以合并为一个属性：验证抓取数据的完整性（包含三级数据和所有必需指标）
- 属性 2.2、2.3、2.4、2.5 可以合并为一个属性：验证报告数据的完整性
- 属性 3.2、3.3、3.4、3.5 可以合并为一个属性：验证分析结果的完整性
- 属性 9.1、9.2、9.3、9.4 可以合并为一个属性：验证通知数据的完整性和正确性
- 属性 10.2、10.3、10.4、10.5 可以合并为一个属性：验证建议数据的完整性

---

### Correctness Properties（正确性属性）

Property 1: 数据抓取返回完整结构
*For any* 平台（meta/tiktok/google）和日期范围，调用 fetch_ad_data 应返回包含 campaigns、adsets、ads 三级数据，且每个实体包含 spend、impressions、clicks、conversions、revenue 等必需指标
**Validates: Requirements 1.1, 1.2, 1.3**

Property 2: 抓取失败自动重试
*For any* 广告平台 API 调用失败场景，系统应自动重试最多 3 次，并在最终失败时返回错误信息
**Validates: Requirements 1.4, 8.5**

Property 3: 抓取数据正确保存
*For any* 成功抓取的数据，通过 MCP 调用 save_metrics 后，使用 get_metrics 应能查询到相同的数据
**Validates: Requirements 1.5**

Property 4: 每日报告数据完整性
*For any* 日期，调用 generate_daily_report 应返回包含 summary（核心指标）、ai_analysis（AI 分析）、recommendations（优化建议）的完整报告结构
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

Property 5: 表现分析结果完整性
*For any* 实体（campaign/adset/ad）和日期范围，调用 analyze_performance 应返回包含 current_period、previous_period、changes（百分比格式）、insights 的完整分析结果
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

Property 6: 异常检测识别能力
*For any* 指标数据，当当前值偏离历史均值超过阈值时，detect_anomalies 应识别为异常并返回包含 deviation、severity、recommendation 的异常数据
**Validates: Requirements 4.1, 4.4, 4.5**

Property 7: CPA 异常严重性判定
*For any* CPA 数据，当 CPA 上涨超过 50% 时，异常严重性应标记为 high 或 critical
**Validates: Requirements 4.2**

Property 8: ROAS 异常严重性判定
*For any* ROAS 数据，当 ROAS 下降超过 30% 时，异常严重性应标记为 critical
**Validates: Requirements 4.3**

Property 9: 低效实体暂停建议
*For any* ROAS 低于阈值的 Adset，generate_recommendations 应生成 action="pause_adset" 的建议
**Validates: Requirements 5.2**

Property 10: 高效实体加预算建议
*For any* ROAS 高于阈值的 Adset，generate_recommendations 应生成 action="increase_budget" 的建议
**Validates: Requirements 5.3**

Property 11: 素材疲劳更新建议
*For any* CTR 持续下降的 Ad，generate_recommendations 应生成 action="refresh_creative" 的建议
**Validates: Requirements 5.4**

Property 12: 建议数据完整性
*For any* 生成的建议，应包含 action、target（含 id 和 name）、expected_impact、confidence（0-1 之间）字段
**Validates: Requirements 5.1, 5.5, 10.1, 10.2, 10.3, 10.4, 10.5**

Property 13: CSV 导出数据完整性
*For any* 报表数据，导出的 CSV 文件应包含所有数据行和列，且数据与原始数据一致
**Validates: Requirements 6.1, 6.2**

Property 14: PDF 导出内容完整性
*For any* 报表数据，导出的 PDF 文件应包含图表和 AI 分析文本
**Validates: Requirements 6.3**

Property 15: 导出文件上传和链接生成
*For any* 导出的文件，上传到 S3 后应返回有效的下载链接，且过期时间设置为 24 小时后
**Validates: Requirements 6.4, 6.5**

Property 16: 多平台数据聚合完整性
*For any* 多平台数据，调用 get_metrics_summary 应返回包含 total（总体指标）和 by_platform（按平台分组）的完整摘要，且 total 等于各平台数据之和
**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

Property 17: 通知数据完整性和正确性
*For any* 报告生成或异常检测结果，返回的通知数据应包含正确的 type、priority、title、message、data 字段，且 priority 根据严重程度正确设置（normal/urgent）
**Validates: Requirements 9.1, 9.2, 9.3, 9.4**

---

## Error Handling（错误处理）

### 错误类型

1. **广告平台 API 错误**
   - 401/403: Token 失效或权限不足
   - 429: 速率限制
   - 500: 平台服务错误
   - 超时: 网络超时

2. **MCP 调用错误**
   - 连接失败
   - 工具不存在
   - 参数无效
   - 执行超时

3. **数据验证错误**
   - 数据格式不正确
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
        """处理广告平台 API 错误"""
        if isinstance(error, TokenExpiredError):
            return {
                "status": "error",
                "error_code": "6001",
                "message": "广告账户令牌过期",
                "retry_allowed": False
            }
        elif isinstance(error, RateLimitError):
            return {
                "status": "error",
                "error_code": "1003",
                "message": "超过速率限制",
                "retry_allowed": True,
                "retry_after": 60
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
    
    async def handle_mcp_error(self, error: Exception) -> dict:
        """处理 MCP 调用错误"""
        return {
            "status": "error",
            "error_code": "3003",
            "message": f"MCP 调用失败: {str(error)}",
            "retry_allowed": True
        }
```

### 重试机制

```python
async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    backoff_factor: int = 2
) -> Any:
    """指数退避重试"""
    for attempt in range(max_retries):
        try:
            return await func()
        except RetryableError as e:
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
- 各个 Fetcher 的数据抓取逻辑
- MetricsCalculator 的指标计算
- AnomalyDetector 的异常检测算法
- RecommendationEngine 的建议生成逻辑
- 错误处理和重试机制

**示例**：
```python
@pytest.mark.asyncio
async def test_meta_fetcher_returns_valid_data():
    """测试 Meta Fetcher 返回有效数据"""
    fetcher = MetaFetcher(api_token="test_token")
    result = await fetcher.fetch_insights(
        date_range={"start_date": "2024-11-20", "end_date": "2024-11-26"},
        levels=["campaign"],
        metrics=["spend", "revenue"]
    )
    
    assert "campaigns" in result
    assert len(result["campaigns"]) > 0
    assert "spend" in result["campaigns"][0]
    assert "revenue" in result["campaigns"][0]
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
- Property 1-17: 所有正确性属性

**示例**：
```python
@given(
    platform=st.sampled_from(["meta", "tiktok", "google"]),
    start_date=st.dates(min_value=date(2024, 1, 1), max_value=date(2024, 12, 31)),
    end_date=st.dates(min_value=date(2024, 1, 1), max_value=date(2024, 12, 31))
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_1_fetch_returns_complete_structure(platform, start_date, end_date):
    """
    **Feature: ad-performance, Property 1: 数据抓取返回完整结构**
    
    For any 平台和日期范围，调用 fetch_ad_data 应返回包含三级数据和必需指标
    """
    # Arrange
    if end_date < start_date:
        start_date, end_date = end_date, start_date
    
    ad_performance = AdPerformance()
    
    # Act
    result = await ad_performance.execute(
        action="fetch_ad_data",
        parameters={
            "platform": platform,
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "levels": ["campaign", "adset", "ad"],
            "metrics": ["spend", "impressions", "clicks", "conversions", "revenue"]
        },
        context={"user_id": "test_user"}
    )
    
    # Assert
    assert result["status"] == "success"
    assert "data" in result
    assert "campaigns" in result["data"]
    assert "adsets" in result["data"]
    assert "ads" in result["data"]
    
    # 验证每个实体包含必需指标
    for campaign in result["data"]["campaigns"]:
        assert "spend" in campaign
        assert "impressions" in campaign
        assert "clicks" in campaign
        assert "conversions" in campaign
        assert "revenue" in campaign
```

---

## Implementation Details（实现细节）

### 1. 数据抓取实现

#### Meta Marketing API 集成

```python
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount

class MetaFetcher:
    def __init__(self, access_token: str):
        FacebookAdsApi.init(access_token=access_token)
    
    async def fetch_insights(
        self,
        account_id: str,
        date_range: dict,
        levels: list[str],
        metrics: list[str]
    ) -> dict:
        """抓取 Meta 广告数据"""
        account = AdAccount(f"act_{account_id}")
        
        results = {"campaigns": [], "adsets": [], "ads": []}
        
        for level in levels:
            insights = account.get_insights(
                fields=metrics + [f"{level}_id", f"{level}_name"],
                params={
                    "time_range": {
                        "since": date_range["start_date"],
                        "until": date_range["end_date"]
                    },
                    "level": level
                }
            )
            
            results[f"{level}s"] = [
                self._transform_insight(insight) for insight in insights
            ]
        
        return results
    
    def _transform_insight(self, insight: dict) -> dict:
        """转换 API 响应为标准格式"""
        return {
            "entity_id": insight.get("campaign_id") or insight.get("adset_id") or insight.get("ad_id"),
            "name": insight.get("campaign_name") or insight.get("adset_name") or insight.get("ad_name"),
            "spend": float(insight.get("spend", 0)),
            "impressions": int(insight.get("impressions", 0)),
            "clicks": int(insight.get("clicks", 0)),
            "conversions": int(insight.get("conversions", 0)),
            "revenue": float(insight.get("revenue", 0))
        }
```

### 2. AI 分析实现

```python
class AIAnalyzer:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client
    
    async def analyze_metrics(self, metrics: dict, historical: dict) -> dict:
        """使用 AI 分析指标"""
        prompt = f"""
        分析以下广告数据并提供洞察：
        
        当前数据：
        - 花费：${metrics['spend']}
        - 收入：${metrics['revenue']}
        - ROAS：{metrics['roas']}
        - 转化数：{metrics['conversions']}
        - CPA：${metrics['cpa']}
        
        历史对比：
        - 花费变化：{historical['spend_change']}
        - ROAS 变化：{historical['roas_change']}
        - CPA 变化：{historical['cpa_change']}
        
        请提供：
        1. 3-5 条关键洞察
        2. 趋势分析（上升/下降/稳定）
        3. 可能的原因分析
        
        以 JSON 格式返回：
        {{
          "key_insights": ["洞察1", "洞察2", ...],
          "trends": {{
            "roas_trend": "declining",
            "spend_trend": "stable",
            "conversion_trend": "declining"
          }}
        }}
        """
        
        response = await self.gemini.generate_content(prompt)
        return json.loads(response.text)
```

### 3. 异常检测算法

```python
import numpy as np
from scipy import stats

class AnomalyDetector:
    def __init__(self):
        self.sensitivity_thresholds = {
            "low": 3.0,      # 3 个标准差
            "medium": 2.5,   # 2.5 个标准差
            "high": 2.0      # 2 个标准差
        }
    
    async def detect(
        self,
        metric: str,
        current_value: float,
        historical_values: list[float],
        sensitivity: str = "medium"
    ) -> dict | None:
        """检测异常"""
        if len(historical_values) < 3:
            return None  # 数据不足
        
        # 计算统计指标
        mean = np.mean(historical_values)
        std = np.std(historical_values)
        
        if std == 0:
            return None  # 无变化
        
        # 计算 Z-score
        z_score = abs((current_value - mean) / std)
        threshold = self.sensitivity_thresholds[sensitivity]
        
        if z_score > threshold:
            deviation = ((current_value - mean) / mean) * 100
            severity = self._calculate_severity(z_score, deviation)
            
            return {
                "metric": metric,
                "current_value": current_value,
                "expected_value": mean,
                "deviation": f"{deviation:+.1f}%",
                "severity": severity,
                "z_score": z_score
            }
        
        return None
    
    def _calculate_severity(self, z_score: float, deviation: float) -> str:
        """计算严重性"""
        if z_score > 4.0 or abs(deviation) > 100:
            return "critical"
        elif z_score > 3.0 or abs(deviation) > 50:
            return "high"
        elif z_score > 2.5 or abs(deviation) > 30:
            return "medium"
        else:
            return "low"
```

### 4. 建议生成逻辑

```python
class RecommendationEngine:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client
    
    async def generate(
        self,
        metrics_data: dict,
        optimization_goal: str,
        constraints: dict
    ) -> list[Recommendation]:
        """生成优化建议"""
        recommendations = []
        
        # 识别低效实体
        underperforming = await self.identify_underperforming(
            metrics_data,
            threshold=constraints.get("min_roas_threshold", 2.0)
        )
        
        for entity in underperforming:
            recommendations.append(Recommendation(
                priority="high",
                action="pause_adset",
                target=RecommendationTarget(
                    type=entity["type"],
                    id=entity["id"],
                    name=entity["name"]
                ),
                reason=f"ROAS {entity['roas']} 低于目标 {constraints['min_roas_threshold']}",
                expected_impact=ExpectedImpact(
                    spend_reduction=entity["spend"],
                    roas_improvement="+0.3"
                ),
                confidence=0.9
            ))
        
        # 识别高效实体
        high_performing = await self.identify_high_performing(
            metrics_data,
            threshold=constraints.get("min_roas_threshold", 2.0) * 1.5
        )
        
        for entity in high_performing:
            recommendations.append(Recommendation(
                priority="high",
                action="increase_budget",
                target=RecommendationTarget(
                    type=entity["type"],
                    id=entity["id"],
                    name=entity["name"]
                ),
                reason=f"ROAS {entity['roas']} 远超目标，有扩展空间",
                expected_impact=ExpectedImpact(
                    spend_increase=entity["spend"] * 0.2,
                    revenue_increase=entity["revenue"] * 0.2
                ),
                confidence=0.85
            ))
        
        # 识别素材疲劳
        creative_fatigue = await self.identify_creative_fatigue(metrics_data)
        
        for entity in creative_fatigue:
            recommendations.append(Recommendation(
                priority="medium",
                action="refresh_creative",
                target=RecommendationTarget(
                    type="ad",
                    id=entity["id"],
                    name=entity["name"]
                ),
                reason=f"CTR 下降 {entity['ctr_decline']}%，可能存在素材疲劳",
                expected_impact=ExpectedImpact(
                    ctr_improvement="+0.5%",
                    roas_improvement="+0.2"
                ),
                confidence=0.75
            ))
        
        return recommendations
    
    async def identify_underperforming(
        self,
        metrics_data: dict,
        threshold: float
    ) -> list[dict]:
        """识别低效实体"""
        underperforming = []
        
        for entity in metrics_data.get("adsets", []):
            if entity.get("roas", 0) < threshold:
                # 检查是否连续多天低效
                historical = await self._get_historical_performance(entity["id"])
                if self._is_consistently_low(historical, threshold):
                    underperforming.append(entity)
        
        return underperforming
    
    def _is_consistently_low(
        self,
        historical: list[dict],
        threshold: float,
        days: int = 3
    ) -> bool:
        """检查是否连续多天低效"""
        if len(historical) < days:
            return False
        
        recent = historical[-days:]
        return all(day["roas"] < threshold for day in recent)
```

### 5. 报表导出实现

```python
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
import matplotlib.pyplot as plt

class CSVExporter:
    async def export(self, data: dict, file_name: str) -> str:
        """导出 CSV"""
        df = pd.DataFrame(data["metrics"])
        file_path = f"/tmp/{file_name}.csv"
        df.to_csv(file_path, index=False)
        return file_path

class PDFExporter:
    async def export(
        self,
        data: dict,
        file_name: str,
        include_charts: bool = True
    ) -> str:
        """导出 PDF（含图表）"""
        file_path = f"/tmp/{file_name}.pdf"
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        elements = []
        
        # 添加标题
        elements.append(Paragraph(f"广告报表 - {data['date']}", style_title))
        
        # 添加摘要表格
        summary_data = [
            ["指标", "数值"],
            ["总花费", f"${data['summary']['total_spend']}"],
            ["总收入", f"${data['summary']['total_revenue']}"],
            ["ROAS", f"{data['summary']['overall_roas']}"],
        ]
        elements.append(Table(summary_data))
        
        # 添加图表
        if include_charts:
            chart_path = await self._generate_chart(data)
            elements.append(Image(chart_path))
        
        # 添加 AI 分析
        for insight in data["ai_analysis"]["key_insights"]:
            elements.append(Paragraph(f"• {insight}", style_body))
        
        doc.build(elements)
        return file_path
    
    async def _generate_chart(self, data: dict) -> str:
        """生成趋势图表"""
        plt.figure(figsize=(10, 6))
        plt.plot(data["dates"], data["roas_values"], label="ROAS")
        plt.xlabel("日期")
        plt.ylabel("ROAS")
        plt.title("ROAS 趋势")
        plt.legend()
        
        chart_path = "/tmp/chart.png"
        plt.savefig(chart_path)
        plt.close()
        
        return chart_path
```

---

## Performance Optimization（性能优化）

### 1. 缓存策略

```python
class CacheManager:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.cache_ttl = 300  # 5 分钟
    
    async def get_cached_metrics(
        self,
        user_id: str,
        date: str,
        platform: str
    ) -> dict | None:
        """获取缓存的指标数据"""
        cache_key = f"metrics:{user_id}:{platform}:{date}"
        cached = await self.redis.get(cache_key)
        
        if cached:
            return json.loads(cached)
        return None
    
    async def cache_metrics(
        self,
        user_id: str,
        date: str,
        platform: str,
        data: dict
    ):
        """缓存指标数据"""
        cache_key = f"metrics:{user_id}:{platform}:{date}"
        await self.redis.setex(
            cache_key,
            self.cache_ttl,
            json.dumps(data)
        )
```

### 2. 并行数据抓取

```python
async def fetch_all_platforms(
    self,
    user_id: str,
    date_range: dict
) -> dict:
    """并行抓取所有平台数据"""
    tasks = []
    
    for platform in ["meta", "tiktok", "google"]:
        task = self._fetch_platform_data(platform, user_id, date_range)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 合并结果
    combined = {"campaigns": [], "adsets": [], "ads": []}
    for result in results:
        if isinstance(result, dict):
            for level in ["campaigns", "adsets", "ads"]:
                combined[level].extend(result.get(level, []))
    
    return combined
```

### 3. 批量 MCP 调用

```python
async def save_metrics_batch(
    self,
    user_id: str,
    metrics_list: list[dict]
) -> list[dict]:
    """批量保存指标数据"""
    tasks = []
    
    for metrics in metrics_list:
        task = self.mcp_client.call_tool(
            "save_metrics",
            {
                "user_id": user_id,
                "platform": metrics["platform"],
                "date": metrics["date"],
                "metrics": metrics
            }
        )
        tasks.append(task)
    
    return await asyncio.gather(*tasks)
```

---

## Security Considerations（安全考虑）

### 1. Token 安全

- 广告平台 Token 通过 MCP 从 Web Platform 获取，不在模块中存储
- Token 使用后立即清除内存
- 所有 API 调用使用 HTTPS

### 2. 数据隐私

- 用户数据通过 user_id 隔离
- 所有 MCP 调用包含 user_id 验证
- 导出的报表文件设置 24 小时过期

### 3. 成本控制

- 缓存数据减少 API 调用
- 监控单次操作成本
- 超过成本阈值时告警

---

## Deployment（部署）

### 容器化

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY app/ ./app/

# 运行
CMD ["python", "-m", "app.modules.ad_performance"]
```

### 环境变量

```bash
# Gemini API
GEMINI_API_KEY=xxx

# MCP
MCP_SERVER_URL=http://web-platform:8000/mcp
MCP_AUTH_TOKEN=xxx

# Redis
REDIS_URL=redis://redis:6379/0

# 广告平台 API（从 MCP 获取，这里仅用于测试）
META_APP_ID=xxx
META_APP_SECRET=xxx
TIKTOK_APP_ID=xxx
TIKTOK_APP_SECRET=xxx
```

### 监控指标

- API 调用成功率
- 平均响应时间
- 异常检测准确率
- 建议采纳率
- MCP 调用延迟

---

## Future Enhancements（未来增强）

1. **机器学习模型**：使用 ML 模型替代统计算法进行异常检测
2. **预测分析**：预测未来 7 天的广告表现
3. **自动优化**：自动执行低风险的优化建议
4. **多维度分析**：按地域、设备、时段等维度分析
5. **竞品对比**：与 Market Insights 集成，对比竞品表现

---

**文档版本**：v1.0  
**最后更新**：2024-11-28  
**维护者**：AAE 开发团队
