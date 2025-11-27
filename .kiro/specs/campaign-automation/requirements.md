# 需求文档 - Campaign Automation（广告投放自动化）

## 简介（Introduction）

Campaign Automation 是 AI Orchestrator 的功能模块之一，负责广告创建、管理和优化相关的业务逻辑。该模块被 AI Orchestrator 调用，通过 MCP 协议与 Web Platform 通信进行数据存储，专注于自动化广告投放和预算优化。

## 术语表（Glossary）

- **Campaign Automation**：广告引擎功能模块
- **Campaign**：广告系列
- **Adset**：广告组
- **Ad**：广告
- **Budget Optimizer**：预算优化器
- **Rule Engine**：规则引擎，自动执行预算调整、暂停等操作
- **Placement**：版位，广告展示的位置
- **Lookalike Audience**：相似受众
- **ROAS**：广告支出回报率（Return on Ad Spend）
- **CPA**：单次转化成本（Cost Per Acquisition）
- **CTR**：点击率（Click-Through Rate）
- **Module API**：功能模块接口，被 AI Orchestrator 调用
- **MCP Client**：MCP 客户端，调用 Web Platform 工具

---

## 接口协议（Interface Specifications）

Campaign Automation 的所有接口协议详见：**[INTERFACES.md](../INTERFACES.md)**

### 对外接口

1. **Module API**：被 AI Orchestrator 调用
   - 协议定义：[INTERFACES.md - Functional Module API](../INTERFACES.md#3-capability-module-apiunified-ai-agent--功能模块)
   - 统一接口：execute(action, parameters, context)

2. **MCP Client**：调用 Web Platform 工具
   - 协议定义：[INTERFACES.md - MCP 协议](../INTERFACES.md#2-mcp-协议unified-ai-agent--user-portal)
   - 工具调用：create_campaign、get_campaigns、update_campaign 等

3. **Ad Platform APIs**：调用广告平台 API
   - Meta Marketing API
   - TikTok Ads API
   - Google Ads API

### 模块边界

**职责范围**：
- ✅ 广告创建逻辑
- ✅ 广告结构生成（Campaign/Adset/Ad）
- ✅ 预算优化算法
- ✅ 规则引擎执行
- ✅ A/B 测试管理
- ✅ 广告平台 API 调用

**不负责**：
- ❌ 数据存储（由 Web Platform 负责）
- ❌ 用户认证（由 Web Platform 负责）
- ❌ 对话管理（由 AI Orchestrator 负责）
- ❌ 素材生成（由 Ad Creative 负责）
- ❌ 报表分析（由 Ad Performance 负责）

详见：[INTERFACES.md - 功能模块边界](../INTERFACES.md#3-功能模块边界)

---

## Module API（功能模块接口）

### 接口定义

```python
class CampaignAutomation:
    async def execute(
        self,
        action: str,
        parameters: dict,
        context: dict
    ) -> dict:
        """
        执行广告引擎操作
        
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

#### 1. create_campaign - 创建广告系列

**参数**：
```json
{
  "objective": "sales",
  "daily_budget": 100,
  "target_roas": 3.0,
  "product_url": "https://shop.com/product",
  "creative_ids": ["creative_1", "creative_2"],
  "target_countries": ["US", "CA"],
  "platform": "meta"
}
```

**返回**：
```json
{
  "status": "success",
  "campaign_id": "campaign_123",
  "adsets": [
    {
      "adset_id": "adset_1",
      "name": "US 18-35",
      "daily_budget": 33.33,
      "targeting": {"age_min": 18, "age_max": 35, "countries": ["US"]}
    },
    {
      "adset_id": "adset_2",
      "name": "US 36-50",
      "daily_budget": 33.33,
      "targeting": {"age_min": 36, "age_max": 50, "countries": ["US"]}
    }
  ],
  "ads": [
    {"ad_id": "ad_1", "creative_id": "creative_1", "adset_id": "adset_1"},
    {"ad_id": "ad_2", "creative_id": "creative_2", "adset_id": "adset_1"}
  ],
  "message": "广告系列创建成功"
}
```

#### 2. optimize_budget - 优化预算

**参数**：
```json
{
  "campaign_id": "campaign_123",
  "optimization_strategy": "auto",
  "target_metric": "roas"
}
```

**返回**：
```json
{
  "status": "success",
  "optimizations": [
    {
      "adset_id": "adset_1",
      "action": "increase_budget",
      "old_budget": 33.33,
      "new_budget": 40.00,
      "reason": "ROAS 3.5 超过目标，表现优秀"
    },
    {
      "adset_id": "adset_2",
      "action": "pause",
      "reason": "连续 3 天无转化"
    }
  ],
  "message": "预算优化完成"
}
```

#### 3. manage_campaign - 管理广告系列

**参数**：
```json
{
  "campaign_id": "campaign_123",
  "action": "pause",
  "reason": "用户请求暂停"
}
```

**返回**：
```json
{
  "status": "success",
  "campaign_id": "campaign_123",
  "new_status": "paused",
  "message": "广告系列已暂停"
}
```

#### 4. create_ab_test - 创建 A/B 测试

**参数**：
```json
{
  "test_name": "Creative Test",
  "creative_ids": ["creative_1", "creative_2", "creative_3"],
  "daily_budget": 90,
  "test_duration_days": 3,
  "platform": "meta"
}
```

**返回**：
```json
{
  "status": "success",
  "test_id": "test_123",
  "campaign_id": "campaign_456",
  "adsets": [
    {"adset_id": "adset_1", "creative_id": "creative_1", "budget": 30},
    {"adset_id": "adset_2", "creative_id": "creative_2", "budget": 30},
    {"adset_id": "adset_3", "creative_id": "creative_3", "budget": 30}
  ],
  "message": "A/B 测试已创建，将运行 3 天"
}
```

#### 5. analyze_ab_test - 分析 A/B 测试结果

**参数**：
```json
{
  "test_id": "test_123"
}
```

**返回**：
```json
{
  "status": "success",
  "test_id": "test_123",
  "results": [
    {
      "creative_id": "creative_1",
      "spend": 90,
      "revenue": 315,
      "roas": 3.5,
      "ctr": 2.8,
      "rank": 1
    },
    {
      "creative_id": "creative_2",
      "spend": 90,
      "revenue": 225,
      "roas": 2.5,
      "ctr": 2.1,
      "rank": 2
    },
    {
      "creative_id": "creative_3",
      "spend": 90,
      "revenue": 180,
      "roas": 2.0,
      "ctr": 1.8,
      "rank": 3
    }
  ],
  "winner": {
    "creative_id": "creative_1",
    "confidence": 95
  },
  "recommendations": [
    "暂停 creative_3（表现最差）",
    "增加 creative_1 预算 50%"
  ]
}
```

#### 6. create_rule - 创建自动化规则

**参数**：
```json
{
  "rule_name": "Auto Pause High CPA",
  "condition": {
    "metric": "cpa",
    "operator": "greater_than",
    "value": 50,
    "time_range": "24h"
  },
  "action": {
    "type": "pause_adset"
  },
  "applies_to": {
    "campaign_ids": ["campaign_123"]
  }
}
```

**返回**：
```json
{
  "status": "success",
  "rule_id": "rule_456",
  "message": "规则已创建，每 6 小时检查一次"
}
```

#### 7. get_campaign_status - 获取广告系列状态

**参数**：
```json
{
  "campaign_id": "campaign_123"
}
```

**返回**：
```json
{
  "status": "success",
  "campaign": {
    "campaign_id": "campaign_123",
    "name": "Summer Sale Campaign",
    "status": "active",
    "daily_budget": 100,
    "spend_today": 87.50,
    "revenue_today": 245.00,
    "roas_today": 2.8,
    "cpa_today": 15.20
  },
  "adsets": [
    {
      "adset_id": "adset_1",
      "name": "US 18-35",
      "status": "active",
      "spend": 45.00,
      "roas": 3.5
    },
    {
      "adset_id": "adset_2",
      "name": "US 36-50",
      "status": "paused",
      "spend": 42.50,
      "roas": 1.8
    }
  ]
}
```

详见：[INTERFACES.md - Campaign Automation](../INTERFACES.md#ad-engine-capability)

---

## MCP 工具调用（MCP Tool Invocation）

该模块通过 MCP Client 调用 Web Platform 的以下工具：

### 1. create_campaign - 存储广告系列

```python
result = await mcp_client.call_tool(
    "create_campaign",
    {
        "user_id": context["user_id"],
        "platform": "meta",
        "campaign_data": {
            "campaign_id": "campaign_123",
            "name": "Summer Sale",
            "objective": "sales",
            "daily_budget": 100,
            "status": "active"
        }
    }
)
```

### 2. get_campaigns - 获取广告系列列表

```python
result = await mcp_client.call_tool(
    "get_campaigns",
    {
        "user_id": context["user_id"],
        "platform": "meta",
        "status": "active"
    }
)
```

### 3. update_campaign - 更新广告系列

```python
result = await mcp_client.call_tool(
    "update_campaign",
    {
        "user_id": context["user_id"],
        "campaign_id": "campaign_123",
        "updates": {
            "status": "paused",
            "daily_budget": 120
        }
    }
)
```

详见：[INTERFACES.md - MCP 协议](../INTERFACES.md#2-mcp-协议unified-ai-agent--user-portal)

---

## 需求（Requirements）

### 需求 1：自动广告结构生成

**用户故事**：作为 AI Orchestrator，我需要调用 Campaign Automation 创建广告，以便自动生成最优的广告结构。

#### 验收标准

1. WHEN 调用 create_campaign action THEN Campaign Automation SHALL 自动创建 Campaign
2. WHEN Campaign 创建 THEN Campaign Automation SHALL 根据目标国家自动创建多个 Adset
3. WHEN Adset 创建 THEN Campaign Automation SHALL 自动配置受众定位（Broad Audience 或 Lookalike）
4. WHEN Adset 创建 THEN Campaign Automation SHALL 自动配置版位（自动版位）
5. WHEN Adset 创建 THEN Campaign Automation SHALL 自动配置出价策略（最低成本）

---

### 需求 2：素材自动挂载

**用户故事**：作为 AI Orchestrator，我需要将素材挂载到广告，以便快速发布。

#### 验收标准

1. WHEN 提供 creative_ids THEN Campaign Automation SHALL 从 Web Platform 获取素材信息
2. WHEN 素材获取 THEN Campaign Automation SHALL 自动创建 Ad 并挂载素材
3. WHEN 素材有多个 THEN Campaign Automation SHALL 为每个素材创建独立的 Ad
4. WHEN 素材挂载 THEN Campaign Automation SHALL 自动生成广告文案（使用 AI）
5. WHEN 文案生成 THEN Campaign Automation SHALL 返回文案供确认

---

### 需求 3：自动预算优化

**用户故事**：作为 AI Orchestrator，我需要优化广告预算，以便提升广告效果。

#### 验收标准

1. WHEN 调用 optimize_budget action THEN Campaign Automation SHALL 分析广告表现数据
2. WHEN CPA 超过目标 150% THEN Campaign Automation SHALL 自动降低预算 20%
3. WHEN ROAS 超过目标 150% THEN Campaign Automation SHALL 自动提升预算 20%
4. WHEN 无转化 3 天 THEN Campaign Automation SHALL 自动暂停 Adset
5. WHEN 执行优化 THEN Campaign Automation SHALL 返回优化操作列表和原因

---

### 需求 4：广告系列管理

**用户故事**：作为 AI Orchestrator，我需要管理广告系列，以便执行用户的操作请求。

#### 验收标准

1. WHEN 调用 manage_campaign action THEN Campaign Automation SHALL 执行指定操作（暂停/启动/删除）
2. WHEN 操作执行 THEN Campaign Automation SHALL 调用广告平台 API
3. WHEN API 调用成功 THEN Campaign Automation SHALL 通过 MCP 更新 Web Platform 数据
4. WHEN API 调用失败 THEN Campaign Automation SHALL 自动重试最多 3 次
5. WHEN 操作完成 THEN Campaign Automation SHALL 返回新状态和确认消息

---

### 需求 5：A/B 测试自动化

**用户故事**：作为 AI Orchestrator，我需要创建和分析 A/B 测试，以便找到最佳素材。

#### 统计方法说明

A/B 测试采用 **卡方检验（Chi-Square Test）** 判断统计显著性：

```
统计方法：卡方检验（Chi-Square Test）
显著性水平：α = 0.05（对应 95% 置信度）
最小样本量：每个变体至少 100 次转化事件

判定条件：
- p-value < 0.05 → 差异显著，可宣布获胜者
- p-value >= 0.05 → 差异不显著，建议继续测试或增加样本量

获胜者判定：
- 转化率差异显著 + 转化率更高的变体 → 获胜者
- 若样本量不足，返回"数据不足，建议继续测试"
```

#### 验收标准

1. WHEN 调用 create_ab_test action THEN Campaign Automation SHALL 创建 A/B 测试 Campaign
2. WHEN 测试创建 THEN Campaign Automation SHALL 为每个素材分配相等预算
3. WHEN 调用 analyze_ab_test action THEN Campaign Automation SHALL 使用卡方检验分析测试结果
4. WHEN 分析完成且样本充足 THEN Campaign Automation SHALL 识别获胜素材（p-value < 0.05）
5. WHEN 样本不足（转化 < 100） THEN Campaign Automation SHALL 返回"数据不足，建议继续测试"
6. WHEN 识别获胜者 THEN Campaign Automation SHALL 提供优化建议

---

### 需求 6：规则引擎

**用户故事**：作为 AI Orchestrator，我需要创建自动化规则，以便系统自动执行操作。

#### 验收标准

1. WHEN 调用 create_rule action THEN Campaign Automation SHALL 创建自动化规则
2. WHEN 规则创建 THEN Campaign Automation SHALL 每 6 小时检查一次条件
3. WHEN 条件满足 THEN Campaign Automation SHALL 执行对应操作
4. WHEN 操作执行 THEN Campaign Automation SHALL 记录执行日志
5. WHEN 规则触发 THEN Campaign Automation SHALL 返回触发通知

---

### 需求 7：多平台支持

**用户故事**：作为 AI Orchestrator，我需要支持多个广告平台，以便统一管理。

#### 验收标准

1. WHEN 指定 platform 为 "meta" THEN Campaign Automation SHALL 调用 Meta Marketing API
2. WHEN 指定 platform 为 "tiktok" THEN Campaign Automation SHALL 调用 TikTok Ads API
3. WHEN 指定 platform 为 "google" THEN Campaign Automation SHALL 调用 Google Ads API
4. WHEN 跨平台操作 THEN Campaign Automation SHALL 确保操作一致性
5. WHEN 平台 API 失败 THEN Campaign Automation SHALL 返回平台特定的错误信息

---

### 需求 8：广告状态查询

**用户故事**：作为 AI Orchestrator，我需要查询广告状态，以便向用户报告表现。

#### 验收标准

1. WHEN 调用 get_campaign_status action THEN Campaign Automation SHALL 从广告平台获取实时数据
2. WHEN 数据获取 THEN Campaign Automation SHALL 返回 Campaign、Adset、Ad 的完整状态
3. WHEN 返回数据 THEN Campaign Automation SHALL 包含花费、收入、ROAS、CPA 等关键指标
4. WHEN 数据不可用 THEN Campaign Automation SHALL 返回最近一次缓存的数据
5. WHEN 查询失败 THEN Campaign Automation SHALL 返回清晰的错误信息

---

### 需求 9：错误处理与重试

**用户故事**：作为系统，我需要优雅地处理错误，以便保证服务可靠性。

#### 验收标准

1. WHEN 广告平台 API 调用失败 THEN Campaign Automation SHALL 自动重试最多 3 次
2. WHEN 网络超时 THEN Campaign Automation SHALL 设置 30 秒超时并重试
3. WHEN 达到 API 限额 THEN Campaign Automation SHALL 返回限额错误并建议稍后重试
4. WHEN 达到重试上限 THEN Campaign Automation SHALL 返回明确的错误信息
5. WHEN 发生错误 THEN Campaign Automation SHALL 记录详细的错误日志

---

## 非功能性需求（Non-Functional Requirements）

### 性能需求

1. Campaign Automation SHALL 在 10 秒内完成广告创建
2. Campaign Automation SHALL 在 5 秒内完成预算优化
3. Campaign Automation SHALL 在 3 秒内返回广告状态
4. Campaign Automation SHALL 支持 10 个并发操作

### 可靠性需求

1. Campaign Automation SHALL 在 API 调用失败时自动重试
2. Campaign Automation SHALL 记录所有操作日志供审计
3. Campaign Automation SHALL 在系统重启后自动恢复规则引擎
4. Campaign Automation SHALL 确保广告操作的原子性（全部成功或全部回滚）

### 安全需求

1. Campaign Automation SHALL 验证用户权限后才执行操作
2. Campaign Automation SHALL 限制单次预算调整幅度（最大 50%）
3. Campaign Automation SHALL 记录所有敏感操作（删除、大额预算调整）
4. Campaign Automation SHALL 加密存储广告平台 API 密钥

### 成本控制需求

1. Campaign Automation SHALL 控制单次广告创建成本不超过 $0.10
2. Campaign Automation SHALL 缓存广告状态数据（5 分钟）
3. Campaign Automation SHALL 监控 API 调用成本并报警

---

## 技术约束（Technical Constraints）

### 广告平台 API

- **Meta Marketing API**：v18.0+
- **TikTok Ads API**：v1.3+
- **Google Ads API**：v14+

### 技术栈

- **开发语言**：Python 3.11+
- **框架**：FastAPI
- **广告 SDK**：facebook-business SDK, tiktok-business-api, google-ads
- **MCP 通信**：MCP SDK (Python)
- **缓存**：Redis
- **任务队列**：Celery（规则引擎定时任务）

### AI 模型

- **文案生成**：Gemini 2.5 Pro
- **策略分析**：Gemini 2.5 Pro
- **数据理解**：Gemini 2.5 Flash

### 部署约束

- **容器化**：Docker
- **编排**：Kubernetes 或 Docker Compose
- **监控**：Prometheus + Grafana
- **日志**：结构化日志（JSON 格式）

---

## 实现示例（Implementation Examples）

### Capability 接口实现

```python
class CampaignAutomation:
    def __init__(self):
        self.meta_api = MetaMarketingAPI()
        self.tiktok_api = TikTokAdsAPI()
        self.google_api = GoogleAdsAPI()
        self.mcp_client = MCPClient()
        self.gemini_client = GeminiClient()
        self.cache = RedisCache()
    
    async def execute(self, action: str, parameters: dict, context: dict) -> dict:
        try:
            if action == "create_campaign":
                return await self._create_campaign(parameters, context)
            elif action == "optimize_budget":
                return await self._optimize_budget(parameters, context)
            elif action == "manage_campaign":
                return await self._manage_campaign(parameters, context)
            elif action == "create_ab_test":
                return await self._create_ab_test(parameters, context)
            elif action == "analyze_ab_test":
                return await self._analyze_ab_test(parameters, context)
            elif action == "create_rule":
                return await self._create_rule(parameters, context)
            elif action == "get_campaign_status":
                return await self._get_campaign_status(parameters, context)
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Campaign automation error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _create_campaign(self, parameters: dict, context: dict) -> dict:
        platform = parameters.get("platform", "meta")
        
        # 选择对应的广告平台 API
        if platform == "meta":
            api = self.meta_api
        elif platform == "tiktok":
            api = self.tiktok_api
        elif platform == "google":
            api = self.google_api
        else:
            return {"status": "error", "message": f"Unsupported platform: {platform}"}
        
        # 创建 Campaign
        campaign = await api.create_campaign(
            name=f"Campaign {datetime.now().strftime('%Y%m%d')}",
            objective=parameters["objective"],
            daily_budget=parameters["daily_budget"]
        )
        
        # 创建 Adsets
        adsets = []
        countries = parameters.get("target_countries", ["US"])
        age_groups = [(18, 35), (36, 50), (51, 65)]
        
        budget_per_adset = parameters["daily_budget"] / len(age_groups)
        
        for age_min, age_max in age_groups:
            adset = await api.create_adset(
                campaign_id=campaign["id"],
                name=f"{countries[0]} {age_min}-{age_max}",
                daily_budget=budget_per_adset,
                targeting={
                    "age_min": age_min,
                    "age_max": age_max,
                    "countries": countries,
                    "targeting_optimization": "none"  # Broad audience
                },
                optimization_goal="value",
                bid_strategy="lowest_cost_without_cap"
            )
            adsets.append(adset)
        
        # 创建 Ads
        ads = []
        creative_ids = parameters.get("creative_ids", [])
        
        for adset in adsets:
            for creative_id in creative_ids:
                # 生成广告文案
                copy = await self._generate_ad_copy(
                    product_url=parameters.get("product_url"),
                    creative_id=creative_id
                )
                
                ad = await api.create_ad(
                    adset_id=adset["id"],
                    creative_id=creative_id,
                    name=f"Ad {creative_id}",
                    copy=copy
                )
                ads.append(ad)
        
        # 保存到 Web Platform
        await self.mcp_client.call_tool(
            "create_campaign",
            {
                "user_id": context["user_id"],
                "platform": platform,
                "campaign_data": {
                    "campaign_id": campaign["id"],
                    "name": campaign["name"],
                    "objective": parameters["objective"],
                    "daily_budget": parameters["daily_budget"],
                    "status": "active"
                }
            }
        )
        
        return {
            "status": "success",
            "campaign_id": campaign["id"],
            "adsets": [{"adset_id": a["id"], "name": a["name"], "daily_budget": budget_per_adset} for a in adsets],
            "ads": [{"ad_id": a["id"], "creative_id": a["creative_id"]} for a in ads],
            "message": "广告系列创建成功"
        }
    
    async def _optimize_budget(self, parameters: dict, context: dict) -> dict:
        campaign_id = parameters["campaign_id"]
        target_metric = parameters.get("target_metric", "roas")
        
        # 获取广告表现数据
        performance = await self._get_performance_data(campaign_id)
        
        optimizations = []
        
        for adset in performance["adsets"]:
            if target_metric == "roas":
                if adset["roas"] > adset["target_roas"] * 1.5:
                    # 表现优秀，增加预算
                    new_budget = adset["daily_budget"] * 1.2
                    await self._update_adset_budget(adset["id"], new_budget)
                    optimizations.append({
                        "adset_id": adset["id"],
                        "action": "increase_budget",
                        "old_budget": adset["daily_budget"],
                        "new_budget": new_budget,
                        "reason": f"ROAS {adset['roas']} 超过目标，表现优秀"
                    })
                elif adset["conversions"] == 0 and adset["days_running"] >= 3:
                    # 连续 3 天无转化，暂停
                    await self._pause_adset(adset["id"])
                    optimizations.append({
                        "adset_id": adset["id"],
                        "action": "pause",
                        "reason": "连续 3 天无转化"
                    })
        
        return {
            "status": "success",
            "optimizations": optimizations,
            "message": "预算优化完成"
        }
    
    async def _generate_ad_copy(self, product_url: str, creative_id: str) -> str:
        # 使用 Gemini 生成广告文案
        prompt = f"为以下产品生成吸引人的广告文案（50 字以内）：{product_url}"
        response = await self.gemini_client.generate_content(prompt)
        return response["text"]
```

### 广告平台 API 调用示例

```python
# Meta Marketing API
async def create_campaign_meta(name: str, objective: str, daily_budget: float) -> dict:
    campaign = Campaign(parent_id=ad_account_id)
    campaign[Campaign.Field.name] = name
    campaign[Campaign.Field.objective] = objective
    campaign[Campaign.Field.status] = Campaign.Status.active
    campaign[Campaign.Field.daily_budget] = int(daily_budget * 100)  # 转换为分
    campaign.remote_create()
    return {"id": campaign[Campaign.Field.id], "name": name}

# TikTok Ads API
async def create_campaign_tiktok(name: str, objective: str, daily_budget: float) -> dict:
    response = await tiktok_api.campaign_create(
        advertiser_id=advertiser_id,
        campaign_name=name,
        objective_type=objective,
        budget_mode="BUDGET_MODE_DAY",
        budget=daily_budget
    )
    return {"id": response["data"]["campaign_id"], "name": name}
```

---

**文档版本**：v1.0
**最后更新**：2024-11-26
**维护者**：AAE 开发团队
