# 需求文档 - Market Insights（市场洞察）

## 简介（Introduction）

Market Insights 是 AI Orchestrator 的功能模块之一，负责市场分析和竞品洞察相关的业务逻辑。该模块被 AI Orchestrator 调用，通过 MCP 协议与 Web Platform 通信进行数据存储，专注于为用户提供 AI 驱动的市场洞察和广告策略建议。

## 术语表（Glossary）

- **Market Insights**：市场洞察功能模块
- **Competitor Analysis**：竞品分析
- **Trend Insights**：趋势洞察
- **Creative Direction**：素材方向建议
- **Audience Recommendation**：受众推荐
- **Ad Strategy**：广告策略
- **Market Trends**：市场趋势
- **Creative Center API**：TikTok 创意中心 API
- **Google Trends API**：Google 趋势 API
- **Module API**：功能模块接口，被 AI Orchestrator 调用
- **MCP Client**：MCP 客户端，调用 Web Platform 工具

---

## 接口协议（Interface Specifications）

Market Insights 的所有接口协议详见：**[INTERFACES.md](../INTERFACES.md)**

### 对外接口

1. **Module API**：被 AI Orchestrator 调用
   - 协议定义：[INTERFACES.md - Functional Module API](../INTERFACES.md#3-capability-module-apiunified-ai-agent--功能模块)
   - 统一接口：execute(action, parameters, context)

2. **MCP Client**：调用 Web Platform 工具
   - 协议定义：[INTERFACES.md - MCP 协议](../INTERFACES.md#2-mcp-协议unified-ai-agent--user-portal)
   - 工具调用：save_insight、get_insights 等

### 模块边界

**职责范围**：
- ✅ 竞品分析逻辑
- ✅ 趋势洞察分析
- ✅ AI 广告策略生成
- ✅ 受众推荐算法
- ✅ 第三方 API 调用（TikTok Creative Center、Google Trends）

**不负责**：
- ❌ 数据存储（由 Web Platform 负责）
- ❌ 用户认证（由 Web Platform 负责）
- ❌ 对话管理（由 AI Orchestrator 负责）
- ❌ 素材生成（由 Ad Creative 负责）
- ❌ 广告创建（由 Campaign Automation 负责）

详见：[INTERFACES.md - 功能模块边界](../INTERFACES.md#3-功能模块边界)

---

## Module API（功能模块接口）

### 接口定义

```python
class MarketInsights:
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
        pass
```

### 支持的 Actions

#### 1. analyze_competitor - 分析竞品

**参数**：
```json
{
  "competitor_url": "https://competitor.com/product",
  "analysis_type": "product",
  "depth": "detailed"
}
```

**返回**：
```json
{
  "status": "success",
  "competitor_info": {
    "name": "Competitor Product",
    "price": "$79.99",
    "features": ["Feature 1", "Feature 2"],
    "target_audience": "25-35岁年轻人",
    "selling_points": ["高性价比", "时尚设计"]
  },
  "insights": {
    "pricing_strategy": "中端定价策略",
    "marketing_approach": "社交媒体营销为主",
    "strengths": ["品牌知名度高", "用户评价好"],
    "weaknesses": ["价格偏高", "配送慢"]
  },
  "recommendations": [
    "可以采用更具竞争力的定价",
    "强调快速配送优势"
  ]
}
```

#### 2. get_trending_creatives - 获取热门素材

**参数**：
```json
{
  "industry": "fashion",
  "region": "US",
  "time_range": "7d",
  "limit": 20
}
```

**返回**：
```json
{
  "status": "success",
  "creatives": [
    {
      "id": "creative_123",
      "title": "Summer Fashion Trends",
      "thumbnail_url": "https://...",
      "views": 1500000,
      "engagement_rate": 8.5,
      "platform": "tiktok"
    }
  ],
  "total": 20
}
```

#### 3. analyze_creative_trend - 分析素材趋势

**参数**：
```json
{
  "creative_id": "creative_123",
  "analysis_depth": "detailed"
}
```

**返回**：
```json
{
  "status": "success",
  "analysis": {
    "visual_style": "简约现代",
    "color_palette": ["#FF6B6B", "#4ECDC4", "#45B7D1"],
    "key_elements": ["产品特写", "生活场景", "用户评价"],
    "success_factors": [
      "清晰的产品展示",
      "情感化场景",
      "强烈的视觉对比"
    ],
    "copywriting_style": "简洁有力，突出痛点"
  },
  "recommendations": [
    "使用类似的简约风格",
    "突出产品核心功能",
    "加入用户真实评价"
  ]
}
```

#### 4. get_market_trends - 获取市场趋势

**参数**：
```json
{
  "keywords": ["sustainable fashion", "eco-friendly"],
  "region": "US",
  "time_range": "30d"
}
```

**返回**：
```json
{
  "status": "success",
  "trends": [
    {
      "keyword": "sustainable fashion",
      "search_volume": 125000,
      "growth_rate": 15.5,
      "trend_direction": "rising",
      "related_queries": ["eco fashion", "ethical clothing"]
    }
  ],
  "insights": {
    "hot_topics": ["可持续时尚", "环保材料"],
    "emerging_trends": ["二手服装", "租赁模式"],
    "seasonal_patterns": "夏季搜索量增加 30%"
  }
}
```

#### 5. generate_ad_strategy - 生成广告策略

**参数**：
```json
{
  "product_info": {
    "name": "Eco-Friendly Water Bottle",
    "category": "home & garden",
    "price": 29.99,
    "target_market": "US"
  },
  "competitor_analysis": true,
  "trend_analysis": true
}
```

**返回**：
```json
{
  "status": "success",
  "strategy": {
    "audience_recommendations": {
      "age_range": "25-45",
      "gender": "all",
      "interests": ["sustainability", "fitness", "outdoor activities"],
      "behaviors": ["eco-conscious shoppers", "health enthusiasts"]
    },
    "creative_direction": {
      "visual_style": "清新自然",
      "key_messages": ["环保", "健康", "耐用"],
      "content_types": ["产品演示", "使用场景", "用户评价"],
      "color_recommendations": ["绿色", "蓝色", "白色"]
    },
    "budget_planning": {
      "recommended_daily_budget": 50,
      "campaign_duration": "30 days",
      "expected_reach": "50,000-100,000"
    },
    "campaign_structure": {
      "ad_groups": [
        {
          "name": "环保意识人群",
          "targeting": "sustainability interests",
          "budget_allocation": "40%"
        },
        {
          "name": "健身爱好者",
          "targeting": "fitness interests",
          "budget_allocation": "35%"
        },
        {
          "name": "户外活动者",
          "targeting": "outdoor interests",
          "budget_allocation": "25%"
        }
      ]
    }
  },
  "rationale": "基于市场趋势分析和竞品研究，环保和健康是当前主要卖点..."
}
```

#### 6. track_strategy_performance - 追踪策略效果

**参数**：
```json
{
  "strategy_id": "strategy_123",
  "campaign_ids": ["campaign_1", "campaign_2"],
  "comparison_period": "7d"
}
```

**返回**：
```json
{
  "status": "success",
  "performance": {
    "campaigns_with_strategy": {
      "avg_roas": 3.5,
      "avg_ctr": 2.8,
      "avg_conversion_rate": 4.2
    },
    "campaigns_without_strategy": {
      "avg_roas": 2.1,
      "avg_ctr": 1.9,
      "avg_conversion_rate": 2.8
    },
    "improvement": {
      "roas_lift": "+66.7%",
      "ctr_lift": "+47.4%",
      "conversion_rate_lift": "+50%"
    }
  },
  "insights": "采纳 AI 策略的广告表现显著优于未采纳策略的广告"
}
```

详见：[INTERFACES.md - Market Insights](../INTERFACES.md#market-intelligence-capability)

---

## MCP 工具调用（MCP Tool Invocation）

该模块通过 MCP Client 调用 Web Platform 的以下工具：

### 1. save_insight - 保存洞察结果

```python
result = await mcp_client.call_tool(
    "save_insight",
    {
        "user_id": context["user_id"],
        "insight_type": "competitor_analysis",
        "data": {
            "competitor_name": "Competitor X",
            "analysis_result": {...}
        }
    }
)
```

### 2. get_insights - 获取历史洞察

```python
result = await mcp_client.call_tool(
    "get_insights",
    {
        "user_id": context["user_id"],
        "insight_type": "trend_analysis",
        "limit": 10
    }
)
```

详见：[INTERFACES.md - MCP 协议](../INTERFACES.md#2-mcp-协议unified-ai-agent--user-portal)

---

## 需求（Requirements）

### 需求 1：竞品分析

**用户故事**：作为 AI Orchestrator，我需要调用 Market Insights 分析竞品，以便为用户提供竞争洞察。

#### 验收标准

1. WHEN 调用 analyze_competitor action THEN Market Insights SHALL 分析竞品产品信息
2. WHEN 分析完成 THEN Market Insights SHALL 返回竞品的卖点、定价策略、目标受众
3. WHEN 分析竞品 THEN Market Insights SHALL 识别竞品的优势和劣势
4. WHEN 生成建议 THEN Market Insights SHALL 提供差异化竞争建议
5. WHEN 分析失败 THEN Market Insights SHALL 返回清晰的错误信息

---

### 需求 2：热门素材发现

**用户故事**：作为 AI Orchestrator，我需要获取热门广告素材，以便帮助用户了解市场趋势。

#### 验收标准

1. WHEN 调用 get_trending_creatives action THEN Market Insights SHALL 调用 TikTok Creative Center API
2. WHEN API 调用成功 THEN Market Insights SHALL 返回热门素材列表
3. WHEN 返回素材 THEN Market Insights SHALL 包含播放量、互动率、平台信息
4. WHEN 调用 analyze_creative_trend THEN Market Insights SHALL 使用 AI Vision 分析素材特点
5. WHEN 分析完成 THEN Market Insights SHALL 返回成功要素和优化建议

---

### 需求 3：市场趋势洞察

**用户故事**：作为 AI Orchestrator，我需要获取市场趋势数据，以便帮助用户把握商机。

#### 验收标准

1. WHEN 调用 get_market_trends action THEN Market Insights SHALL 调用 Google Trends API
2. WHEN API 调用成功 THEN Market Insights SHALL 返回搜索趋势数据
3. WHEN 返回趋势 THEN Market Insights SHALL 包含搜索量、增长率、趋势方向
4. WHEN 分析趋势 THEN Market Insights SHALL 识别热门话题和新兴趋势
5. WHEN 提供洞察 THEN Market Insights SHALL 包含季节性模式和相关查询

---

### 需求 4：AI 广告策略生成

**用户故事**：作为 AI Orchestrator，我需要生成 AI 广告策略，以便为用户提供投放建议。

#### 验收标准

1. WHEN 调用 generate_ad_strategy action THEN Market Insights SHALL 使用 AI 模型生成策略
2. WHEN 策略生成完成 THEN Market Insights SHALL 返回受众推荐
3. WHEN 策略生成完成 THEN Market Insights SHALL 返回素材方向建议
4. WHEN 策略生成完成 THEN Market Insights SHALL 返回预算规划建议
5. WHEN 策略生成完成 THEN Market Insights SHALL 返回广告系列结构建议

---

### 需求 5：策略效果追踪

**用户故事**：作为 AI Orchestrator，我需要追踪策略效果，以便评估 AI 建议的质量。

#### 验收标准

1. WHEN 调用 track_strategy_performance action THEN Market Insights SHALL 对比采纳和未采纳策略的广告表现
2. WHEN 对比完成 THEN Market Insights SHALL 计算 ROAS、CTR、转化率的提升百分比
3. WHEN 返回结果 THEN Market Insights SHALL 包含详细的性能对比数据
4. WHEN 生成洞察 THEN Market Insights SHALL 提供策略效果的文字说明
5. WHEN 追踪失败 THEN Market Insights SHALL 返回具体的失败原因

---

### 需求 6：第三方 API 集成

**用户故事**：作为系统，我需要集成第三方 API，以便获取市场数据。

#### 数据源说明

| 数据源 | 类型 | 用途 | 可靠性 |
|-------|------|------|--------|
| TikTok Creative Center | 官方 API | 热门素材、创意趋势 | 高 |
| pytrends (非官方) | 第三方库 | Google 趋势数据 | 中（有限流风险） |
| SimilarWeb API | 商业 API | 竞品流量分析 | 高（需付费） |
| AI 分析 (Gemini) | 自有 | 竞品页面分析、策略生成 | 高 |

#### 降级策略

```
┌─────────────────────────────────────────────────────────────┐
│                    数据源降级策略                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  热门素材数据:                                               │
│  优先: TikTok Creative Center API                           │
│  降级: 使用缓存数据 (最长 7 天)                              │
│  最终: 返回"数据暂时不可用"提示                              │
│                                                             │
│  市场趋势数据:                                               │
│  优先: pytrends (Google Trends)                             │
│  降级: 使用缓存数据 (最长 3 天)                              │
│  备选: AI 基于行业知识生成趋势分析                           │
│                                                             │
│  竞品分析:                                                   │
│  优先: AI 分析公开页面信息                                   │
│  降级: 返回部分分析结果                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 验收标准

1. WHEN 调用 TikTok Creative Center API THEN Market Insights SHALL 使用官方 API 密钥
2. WHEN 调用 pytrends THEN Market Insights SHALL 遵守速率限制（每分钟最多 5 次请求）
3. WHEN API 调用失败 THEN Market Insights SHALL 自动重试最多 3 次，间隔指数退避
4. WHEN 达到 API 限额 THEN Market Insights SHALL 使用缓存数据或降级方案
5. WHEN API 响应慢 THEN Market Insights SHALL 设置 30 秒超时
6. WHEN 数据源完全不可用 THEN Market Insights SHALL 返回明确的降级提示和可用的部分数据

---

### 需求 7：数据缓存与优化

**用户故事**：作为系统，我需要缓存数据，以便降低 API 调用成本和提升响应速度。

#### 验收标准

1. WHEN 获取趋势数据 THEN Market Insights SHALL 缓存结果 24 小时
2. WHEN 获取热门素材 THEN Market Insights SHALL 缓存结果 12 小时
3. WHEN 缓存命中 THEN Market Insights SHALL 直接返回缓存数据
4. WHEN 缓存过期 THEN Market Insights SHALL 重新调用 API 并更新缓存
5. WHEN 缓存失败 THEN Market Insights SHALL 降级到直接 API 调用

---

## 非功能性需求（Non-Functional Requirements）

### 性能需求

1. Market Insights SHALL 在 15 秒内完成竞品分析
2. Market Insights SHALL 在 10 秒内返回热门素材列表
3. Market Insights SHALL 在 20 秒内生成完整的广告策略
4. Market Insights SHALL 支持 5 个并发分析任务

### 数据质量需求

1. Market Insights SHALL 仅使用公开 API 获取数据（避免爬虫）
2. Market Insights SHALL 每周自动更新趋势数据
3. Market Insights SHALL 仅分析公开可访问的信息
4. Market Insights SHALL 确保分析结果的准确性 > 80%

### 合规性需求

1. Market Insights SHALL 不存储竞品的原始素材
2. Market Insights SHALL 仅存储分析结果
3. Market Insights SHALL 遵守各平台的 API 使用条款
4. Market Insights SHALL 遵守数据隐私法规（GDPR、CCPA）

### 成本控制需求

1. Market Insights SHALL 控制单次分析成本不超过 $0.20
2. Market Insights SHALL 使用缓存减少 API 调用次数
3. Market Insights SHALL 监控 API 调用成本并报警

---

## 技术约束（Technical Constraints）

### AI 模型

- **策略生成**：Gemini 2.5 Pro
- **素材分析**：Gemini 2.5 Flash（图片/视频理解）
- **文本分析**：Gemini 2.5 Flash

### 技术栈

- **开发语言**：Python 3.11+
- **框架**：FastAPI
- **AI SDK**：Google AI SDK
- **MCP 通信**：MCP SDK (Python)
- **缓存**：Redis

### 第三方服务

- **TikTok Creative Center API**：热门素材数据（官方 API）
- **pytrends**：Google 趋势数据（非官方 Python 库，需注意限流）
- **Gemini API**：AI 分析和策略生成
- **SimilarWeb API**（可选）：竞品流量分析（商业 API，后续扩展）

### 部署约束

- **容器化**：Docker
- **编排**：Kubernetes 或 Docker Compose
- **监控**：Prometheus + Grafana
- **日志**：结构化日志（JSON 格式）

---

## 实现示例（Implementation Examples）

### Capability 接口实现

```python
class MarketInsights:
    def __init__(self):
        self.gemini_client = GeminiClient()
        self.tiktok_api = TikTokCreativeCenterAPI()
        self.google_trends = GoogleTrendsAPI()
        self.mcp_client = MCPClient()
        self.cache = RedisCache()
    
    async def execute(self, action: str, parameters: dict, context: dict) -> dict:
        try:
            if action == "analyze_competitor":
                return await self._analyze_competitor(parameters, context)
            elif action == "get_trending_creatives":
                return await self._get_trending_creatives(parameters, context)
            elif action == "analyze_creative_trend":
                return await self._analyze_creative_trend(parameters, context)
            elif action == "get_market_trends":
                return await self._get_market_trends(parameters, context)
            elif action == "generate_ad_strategy":
                return await self._generate_ad_strategy(parameters, context)
            elif action == "track_strategy_performance":
                return await self._track_strategy_performance(parameters, context)
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Market insights error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _analyze_competitor(self, parameters: dict, context: dict) -> dict:
        # 使用 AI 分析竞品
        competitor_url = parameters["competitor_url"]
        
        # 调用 Gemini 分析竞品页面
        analysis = await self.gemini_client.analyze_competitor(competitor_url)
        
        # 保存分析结果到 Web Platform
        await self.mcp_client.call_tool(
            "save_insight",
            {
                "user_id": context["user_id"],
                "insight_type": "competitor_analysis",
                "data": analysis
            }
        )
        
        return {
            "status": "success",
            "competitor_info": analysis["competitor_info"],
            "insights": analysis["insights"],
            "recommendations": analysis["recommendations"]
        }
    
    async def _get_trending_creatives(self, parameters: dict, context: dict) -> dict:
        # 检查缓存
        cache_key = f"trending:{parameters['industry']}:{parameters['region']}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # 调用 TikTok Creative Center API
        creatives = await self.tiktok_api.get_trending_creatives(
            industry=parameters["industry"],
            region=parameters["region"],
            time_range=parameters.get("time_range", "7d"),
            limit=parameters.get("limit", 20)
        )
        
        result = {
            "status": "success",
            "creatives": creatives,
            "total": len(creatives)
        }
        
        # 缓存 12 小时
        await self.cache.set(cache_key, result, ttl=43200)
        
        return result
    
    async def _generate_ad_strategy(self, parameters: dict, context: dict) -> dict:
        # 使用 Gemini 生成广告策略
        product_info = parameters["product_info"]
        
        # 构建 prompt
        prompt = f"""
        基于以下产品信息生成完整的广告策略：
        
        产品名称：{product_info['name']}
        类别：{product_info['category']}
        价格：${product_info['price']}
        目标市场：{product_info['target_market']}
        
        请提供：
        1. 受众推荐（年龄、性别、兴趣、行为）
        2. 素材方向建议（视觉风格、关键信息、内容类型、色彩推荐）
        3. 预算规划建议
        4. 广告系列结构建议
        """
        
        strategy = await self.gemini_client.generate_content(prompt)
        
        # 保存策略到 Web Platform
        await self.mcp_client.call_tool(
            "save_insight",
            {
                "user_id": context["user_id"],
                "insight_type": "ad_strategy",
                "data": strategy
            }
        )
        
        return {
            "status": "success",
            "strategy": strategy,
            "rationale": "基于市场趋势分析和竞品研究..."
        }
```

### 第三方 API 调用示例

```python
# TikTok Creative Center API
async def get_trending_creatives(industry: str, region: str) -> list:
    response = await tiktok_api.request(
        endpoint="/creatives/trending",
        params={
            "industry": industry,
            "region": region,
            "time_range": "7d"
        }
    )
    return response["data"]

# Google Trends API
async def get_market_trends(keywords: list, region: str) -> dict:
    response = await google_trends.interest_over_time(
        keywords=keywords,
        geo=region,
        timeframe="today 1-m"
    )
    return response
```

---

**文档版本**：v1.0
**最后更新**：2024-11-26
**维护者**：AAE 开发团队
