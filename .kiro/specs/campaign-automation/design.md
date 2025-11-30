# Campaign Automation 设计文档（Design Document）

## 概述（Overview）

Campaign Automation 是 AAE 系统的广告投放自动化功能模块，负责广告创建、管理和优化的业务逻辑。该模块作为独立的功能模块被 AI Orchestrator 调用，通过 MCP 协议与 Web Platform 通信进行数据存储，专注于自动化广告投放和预算优化。

### 核心能力

1. **自动广告结构生成**：根据目标和预算自动创建 Campaign/Adset/Ad 三层结构
2. **智能预算优化**：基于表现数据自动调整预算分配
3. **A/B 测试管理**：自动化创建和分析素材测试
4. **规则引擎**：自动执行预算调整、暂停等操作
5. **多平台支持**：统一接口支持 Meta、TikTok、Google Ads

### 设计原则

- **模块化**：功能模块独立，通过标准接口通信
- **可扩展**：易于添加新的广告平台支持
- **智能化**：利用 AI 进行文案生成和策略优化
- **可靠性**：完善的错误处理和重试机制
- **成本优化**：缓存机制减少 API 调用成本

---

## 架构（Architecture）

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      AI Orchestrator                         │
│                    (对话协调层)                               │
└────────────────────┬────────────────────────────────────────┘
                     │ Module API
                     │ execute(action, parameters, context)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Campaign Automation Module                      │
│                  (广告投放自动化)                             │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Campaign   │  │   Budget     │  │     Rule     │     │
│  │   Manager    │  │  Optimizer   │  │    Engine    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   A/B Test   │  │   Platform   │  │     AI       │     │
│  │   Manager    │  │   Adapters   │  │   Client     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────┬─────────────────────┬───────────────────┬─────────┘
         │ MCP Client          │ Ad Platform APIs  │ Gemini API
         ▼                     ▼                   ▼
┌─────────────────┐   ┌─────────────────┐   ┌──────────────┐
│  Web Platform   │   │   Meta Ads API  │   │  Gemini API  │
│  (MCP Server)   │   │  TikTok Ads API │   │              │
│                 │   │  Google Ads API │   │              │
└─────────────────┘   └─────────────────┘   └──────────────┘
```

### 模块边界

**职责范围**：
- ✅ 广告创建逻辑（Campaign/Adset/Ad 结构生成）
- ✅ 预算优化算法
- ✅ 规则引擎执行
- ✅ A/B 测试管理
- ✅ 广告平台 API 调用
- ✅ AI 文案生成

**不负责**：
- ❌ 数据存储（由 Web Platform 负责）
- ❌ 用户认证（由 Web Platform 负责）
- ❌ 对话管理（由 AI Orchestrator 负责）
- ❌ 素材生成（由 Ad Creative 负责）
- ❌ 报表分析（由 Ad Performance 负责）


---

## 组件和接口（Components and Interfaces）

### 1. Campaign Manager（广告系列管理器）

负责广告系列的创建、更新和管理。

**职责**：
- 创建 Campaign/Adset/Ad 三层结构
- 配置受众定位和版位
- 管理广告状态（启动/暂停/删除）
- 素材挂载和文案生成

**接口**：
```python
class CampaignManager:
    async def create_campaign(
        self,
        objective: str,
        daily_budget: float,
        target_countries: List[str],
        creative_ids: List[str],
        platform: str,
        context: dict
    ) -> dict:
        """创建完整的广告系列结构"""
        pass
    
    async def update_campaign_status(
        self,
        campaign_id: str,
        status: str,
        platform: str,
        context: dict
    ) -> dict:
        """更新广告系列状态"""
        pass
    
    async def get_campaign_details(
        self,
        campaign_id: str,
        platform: str,
        context: dict
    ) -> dict:
        """获取广告系列详情"""
        pass
```

### 2. Budget Optimizer（预算优化器）

基于表现数据自动优化预算分配。

**职责**：
- 分析广告表现数据
- 计算优化建议
- 执行预算调整
- 自动暂停低效广告组

**优化策略**：
```python
class BudgetOptimizer:
    async def analyze_performance(
        self,
        campaign_id: str,
        target_metric: str,
        context: dict
    ) -> dict:
        """分析广告表现"""
        pass
    
    async def optimize_budget(
        self,
        campaign_id: str,
        optimization_strategy: str,
        target_metric: str,
        context: dict
    ) -> List[dict]:
        """
        优化规则：
        1. ROAS > 目标 * 1.5 → 增加预算 20%
        2. CPA > 目标 * 1.5 → 降低预算 20%
        3. 连续 3 天无转化 → 暂停 Adset
        4. 预算调整上限：单次最大 50%
        """
        pass
```

### 3. A/B Test Manager（A/B 测试管理器）

自动化创建和分析 A/B 测试。

**职责**：
- 创建 A/B 测试 Campaign
- 均分预算到各变体
- 使用卡方检验分析结果
- 识别获胜素材

**统计方法**：
```python
class ABTestManager:
    async def create_ab_test(
        self,
        test_name: str,
        creative_ids: List[str],
        daily_budget: float,
        test_duration_days: int,
        platform: str,
        context: dict
    ) -> dict:
        """创建 A/B 测试"""
        pass
    
    async def analyze_ab_test(
        self,
        test_id: str,
        context: dict
    ) -> dict:
        """
        使用卡方检验分析测试结果：
        - 显著性水平：α = 0.05（95% 置信度）
        - 最小样本量：每个变体至少 100 次转化
        - p-value < 0.05 → 差异显著
        - 返回获胜者和优化建议
        """
        pass
    
    def chi_square_test(
        self,
        variant_a: dict,
        variant_b: dict
    ) -> dict:
        """执行卡方检验"""
        pass
```

### 4. Rule Engine（规则引擎）

自动执行预定义的规则。

**职责**：
- 创建和管理自动化规则
- 定期检查规则条件
- 执行规则动作
- 记录执行日志

**规则结构**：
```python
class RuleEngine:
    async def create_rule(
        self,
        rule_name: str,
        condition: dict,
        action: dict,
        applies_to: dict,
        context: dict
    ) -> dict:
        """
        创建规则
        
        condition: {
            "metric": "cpa",
            "operator": "greater_than",
            "value": 50,
            "time_range": "24h"
        }
        
        action: {
            "type": "pause_adset"
        }
        """
        pass
    
    async def check_rules(self) -> List[dict]:
        """每 6 小时检查一次所有规则"""
        pass
    
    async def execute_rule_action(
        self,
        rule_id: str,
        target_id: str,
        action: dict
    ) -> dict:
        """执行规则动作"""
        pass
```

### 5. Platform Adapters（平台适配器）

统一不同广告平台的 API 调用。

**职责**：
- 封装平台特定的 API 调用
- 统一返回格式
- 处理平台特定的错误
- 实现重试机制

**接口**：
```python
class PlatformAdapter(ABC):
    @abstractmethod
    async def create_campaign(self, params: dict) -> dict:
        pass
    
    @abstractmethod
    async def create_adset(self, params: dict) -> dict:
        pass
    
    @abstractmethod
    async def create_ad(self, params: dict) -> dict:
        pass
    
    @abstractmethod
    async def update_budget(self, adset_id: str, budget: float) -> dict:
        pass
    
    @abstractmethod
    async def pause_adset(self, adset_id: str) -> dict:
        pass

class MetaAdapter(PlatformAdapter):
    """Meta Marketing API 适配器"""
    pass

class TikTokAdapter(PlatformAdapter):
    """TikTok Ads API 适配器"""
    pass

class GoogleAdapter(PlatformAdapter):
    """Google Ads API 适配器"""
    pass
```

### 6. AI Client（AI 客户端）

调用 Gemini API 生成广告文案。

**职责**：
- 生成广告文案
- 优化文案质量
- 处理 AI 调用失败

**接口**：
```python
class AIClient:
    async def generate_ad_copy(
        self,
        product_url: str,
        creative_id: str,
        platform: str,
        max_length: int = 125
    ) -> str:
        """
        生成广告文案
        
        Prompt 模板：
        "为以下产品生成吸引人的广告文案（{max_length} 字以内）：
        产品链接：{product_url}
        平台：{platform}
        
        要求：
        1. 突出产品卖点
        2. 包含行动号召（CTA）
        3. 符合平台规范
        4. 语言简洁有力"
        """
        pass
```

---

## 数据模型（Data Models）

### Campaign 数据结构

```python
@dataclass
class Campaign:
    campaign_id: str
    name: str
    objective: str  # sales, traffic, awareness
    daily_budget: float
    status: str  # active, paused, deleted
    platform: str  # meta, tiktok, google
    target_roas: Optional[float] = None
    target_cpa: Optional[float] = None
    created_at: datetime
    updated_at: datetime
```

### Adset 数据结构

```python
@dataclass
class Adset:
    adset_id: str
    campaign_id: str
    name: str
    daily_budget: float
    status: str
    targeting: dict  # 受众定位配置
    optimization_goal: str  # value, conversions, clicks
    bid_strategy: str  # lowest_cost, target_cost
    created_at: datetime
    updated_at: datetime
```

### Ad 数据结构

```python
@dataclass
class Ad:
    ad_id: str
    adset_id: str
    creative_id: str
    name: str
    copy: str  # 广告文案
    status: str
    created_at: datetime
    updated_at: datetime
```

### Rule 数据结构

```python
@dataclass
class Rule:
    rule_id: str
    rule_name: str
    condition: dict
    action: dict
    applies_to: dict
    check_interval: int  # 检查间隔（秒）
    enabled: bool
    last_checked_at: Optional[datetime]
    created_at: datetime
```

### A/B Test 数据结构

```python
@dataclass
class ABTest:
    test_id: str
    test_name: str
    campaign_id: str
    creative_ids: List[str]
    daily_budget: float
    test_duration_days: int
    start_date: datetime
    end_date: datetime
    status: str  # running, completed, cancelled
    results: Optional[dict] = None
    winner: Optional[str] = None
```


---

## 正确性属性（Correctness Properties）

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### 验收标准测试性分析（Acceptance Criteria Testing Prework）

#### 需求 1：自动广告结构生成

1.1 WHEN 调用 create_campaign action THEN Campaign Automation SHALL 自动创建 Campaign
- Thoughts: 这是测试创建操作的基本功能。我们可以生成随机的 campaign 参数，调用 create_campaign，然后验证返回的 campaign_id 是否有效，以及 campaign 是否被正确创建。
- Testable: yes - property

1.2 WHEN Campaign 创建 THEN Campaign Automation SHALL 根据目标国家自动创建多个 Adset
- Thoughts: 这是测试 adset 创建逻辑。对于任意的国家列表和年龄组配置，创建 campaign 后应该生成对应数量的 adsets。
- Testable: yes - property

1.3 WHEN Adset 创建 THEN Campaign Automation SHALL 自动配置受众定位（Broad Audience 或 Lookalike）
- Thoughts: 这是测试 adset 配置。对于任意创建的 adset，其 targeting 配置应该包含正确的受众定位设置。
- Testable: yes - property

1.4 WHEN Adset 创建 THEN Campaign Automation SHALL 自动配置版位（自动版位）
- Thoughts: 这是测试版位配置。对于任意创建的 adset，应该包含自动版位配置。
- Testable: yes - property

1.5 WHEN Adset 创建 THEN Campaign Automation SHALL 自动配置出价策略（最低成本）
- Thoughts: 这是测试出价策略配置。对于任意创建的 adset，bid_strategy 应该设置为 lowest_cost。
- Testable: yes - property

#### 需求 2：素材自动挂载

2.1 WHEN 提供 creative_ids THEN Campaign Automation SHALL 从 Web Platform 获取素材信息
- Thoughts: 这是测试 MCP 调用。对于任意的 creative_ids 列表，应该能够成功调用 MCP 工具获取素材信息。
- Testable: yes - property

2.2 WHEN 素材获取 THEN Campaign Automation SHALL 自动创建 Ad 并挂载素材
- Thoughts: 这是测试 ad 创建。对于任意获取的素材，应该创建对应的 ad 并正确挂载。
- Testable: yes - property

2.3 WHEN 素材有多个 THEN Campaign Automation SHALL 为每个素材创建独立的 Ad
- Thoughts: 这是测试 ad 数量。创建的 ad 数量应该等于素材数量乘以 adset 数量。
- Testable: yes - property

2.4 WHEN 素材挂载 THEN Campaign Automation SHALL 自动生成广告文案（使用 AI）
- Thoughts: 这是测试文案生成。对于任意的素材，应该能够生成非空的文案。
- Testable: yes - property

2.5 WHEN 文案生成 THEN Campaign Automation SHALL 返回文案供确认
- Thoughts: 这是测试返回值。create_campaign 的返回结果应该包含生成的文案信息。
- Testable: yes - property

#### 需求 3：自动预算优化

3.1 WHEN 调用 optimize_budget action THEN Campaign Automation SHALL 分析广告表现数据
- Thoughts: 这是测试数据分析。对于任意的 campaign，应该能够获取并分析表现数据。
- Testable: yes - property

3.2 WHEN CPA 超过目标 150% THEN Campaign Automation SHALL 自动降低预算 20%
- Thoughts: 这是测试优化规则。对于 CPA 超标的 adset，应该生成降低预算的优化建议。
- Testable: yes - property

3.3 WHEN ROAS 超过目标 150% THEN Campaign Automation SHALL 自动提升预算 20%
- Thoughts: 这是测试优化规则。对于 ROAS 超标的 adset，应该生成提升预算的优化建议。
- Testable: yes - property

3.4 WHEN 无转化 3 天 THEN Campaign Automation SHALL 自动暂停 Adset
- Thoughts: 这是测试暂停规则。对于连续 3 天无转化的 adset，应该生成暂停建议。
- Testable: yes - property

3.5 WHEN 执行优化 THEN Campaign Automation SHALL 返回优化操作列表和原因
- Thoughts: 这是测试返回格式。优化结果应该包含操作列表和每个操作的原因。
- Testable: yes - property

#### 需求 4：广告系列管理

4.1 WHEN 调用 manage_campaign action THEN Campaign Automation SHALL 执行指定操作（暂停/启动/删除）
- Thoughts: 这是测试管理操作。对于任意的操作类型，应该能够正确执行。
- Testable: yes - property

4.2 WHEN 操作执行 THEN Campaign Automation SHALL 调用广告平台 API
- Thoughts: 这是测试 API 调用。执行操作时应该调用对应平台的 API。
- Testable: yes - example

4.3 WHEN API 调用成功 THEN Campaign Automation SHALL 通过 MCP 更新 Web Platform 数据
- Thoughts: 这是测试数据同步。API 调用成功后应该更新 Web Platform 的数据。
- Testable: yes - property

4.4 WHEN API 调用失败 THEN Campaign Automation SHALL 自动重试最多 3 次
- Thoughts: 这是测试重试机制。API 失败时应该自动重试，最多 3 次。
- Testable: yes - property

4.5 WHEN 操作完成 THEN Campaign Automation SHALL 返回新状态和确认消息
- Thoughts: 这是测试返回格式。操作完成后应该返回更新后的状态。
- Testable: yes - property

#### 需求 5：A/B 测试自动化

5.1 WHEN 调用 create_ab_test action THEN Campaign Automation SHALL 创建 A/B 测试 Campaign
- Thoughts: 这是测试 A/B 测试创建。对于任意的素材列表，应该能够创建测试 campaign。
- Testable: yes - property

5.2 WHEN 测试创建 THEN Campaign Automation SHALL 为每个素材分配相等预算
- Thoughts: 这是测试预算分配。每个变体的预算应该相等（总预算 / 变体数量）。
- Testable: yes - property

5.3 WHEN 调用 analyze_ab_test action THEN Campaign Automation SHALL 使用卡方检验分析测试结果
- Thoughts: 这是测试统计分析。应该使用卡方检验计算 p-value。
- Testable: yes - property

5.4 WHEN 分析完成且样本充足 THEN Campaign Automation SHALL 识别获胜素材（p-value < 0.05）
- Thoughts: 这是测试获胜者判定。当 p-value < 0.05 且样本充足时，应该返回获胜者。
- Testable: yes - property

5.5 WHEN 样本不足（转化 < 100） THEN Campaign Automation SHALL 返回"数据不足，建议继续测试"
- Thoughts: 这是测试边界情况。当样本量不足时，应该返回特定的提示信息。
- Testable: edge-case

5.6 WHEN 识别获胜者 THEN Campaign Automation SHALL 提供优化建议
- Thoughts: 这是测试建议生成。识别获胜者后应该提供具体的优化建议。
- Testable: yes - property

#### 需求 6：规则引擎

6.1 WHEN 调用 create_rule action THEN Campaign Automation SHALL 创建自动化规则
- Thoughts: 这是测试规则创建。对于任意的规则配置，应该能够成功创建。
- Testable: yes - property

6.2 WHEN 规则创建 THEN Campaign Automation SHALL 每 6 小时检查一次条件
- Thoughts: 这是测试定时任务。规则应该按照指定的间隔检查。这是一个时间相关的测试，不适合单元测试。
- Testable: no

6.3 WHEN 条件满足 THEN Campaign Automation SHALL 执行对应操作
- Thoughts: 这是测试规则执行。当条件满足时，应该执行对应的操作。
- Testable: yes - property

6.4 WHEN 操作执行 THEN Campaign Automation SHALL 记录执行日志
- Thoughts: 这是测试日志记录。执行操作后应该记录日志。
- Testable: yes - property

6.5 WHEN 规则触发 THEN Campaign Automation SHALL 返回触发通知
- Thoughts: 这是测试通知机制。规则触发时应该返回通知信息。
- Testable: yes - property

#### 需求 7：多平台支持

7.1 WHEN 指定 platform 为 "meta" THEN Campaign Automation SHALL 调用 Meta Marketing API
- Thoughts: 这是测试平台路由。指定 meta 平台时应该使用 MetaAdapter。
- Testable: yes - example

7.2 WHEN 指定 platform 为 "tiktok" THEN Campaign Automation SHALL 调用 TikTok Ads API
- Thoughts: 这是测试平台路由。指定 tiktok 平台时应该使用 TikTokAdapter。
- Testable: yes - example

7.3 WHEN 指定 platform 为 "google" THEN Campaign Automation SHALL 调用 Google Ads API
- Thoughts: 这是测试平台路由。指定 google 平台时应该使用 GoogleAdapter。
- Testable: yes - example

7.4 WHEN 跨平台操作 THEN Campaign Automation SHALL 确保操作一致性
- Thoughts: 这是测试接口一致性。不同平台的操作应该返回统一格式的结果。
- Testable: yes - property

7.5 WHEN 平台 API 失败 THEN Campaign Automation SHALL 返回平台特定的错误信息
- Thoughts: 这是测试错误处理。API 失败时应该返回清晰的错误信息。
- Testable: yes - property

#### 需求 8：广告状态查询

8.1 WHEN 调用 get_campaign_status action THEN Campaign Automation SHALL 从广告平台获取实时数据
- Thoughts: 这是测试数据获取。应该能够从平台 API 获取实时数据。
- Testable: yes - property

8.2 WHEN 数据获取 THEN Campaign Automation SHALL 返回 Campaign、Adset、Ad 的完整状态
- Thoughts: 这是测试返回格式。返回的数据应该包含所有层级的状态信息。
- Testable: yes - property

8.3 WHEN 返回数据 THEN Campaign Automation SHALL 包含花费、收入、ROAS、CPA 等关键指标
- Thoughts: 这是测试数据完整性。返回的数据应该包含所有关键指标。
- Testable: yes - property

8.4 WHEN 数据不可用 THEN Campaign Automation SHALL 返回最近一次缓存的数据
- Thoughts: 这是测试缓存机制。当实时数据不可用时，应该返回缓存数据。
- Testable: yes - property

8.5 WHEN 查询失败 THEN Campaign Automation SHALL 返回清晰的错误信息
- Thoughts: 这是测试错误处理。查询失败时应该返回清晰的错误信息。
- Testable: yes - property

#### 需求 9：错误处理与重试

9.1 WHEN 广告平台 API 调用失败 THEN Campaign Automation SHALL 自动重试最多 3 次
- Thoughts: 这是测试重试机制。API 失败时应该自动重试。
- Testable: yes - property

9.2 WHEN 网络超时 THEN Campaign Automation SHALL 设置 30 秒超时并重试
- Thoughts: 这是测试超时处理。应该设置合理的超时时间。
- Testable: yes - property

9.3 WHEN 达到 API 限额 THEN Campaign Automation SHALL 返回限额错误并建议稍后重试
- Thoughts: 这是测试限额处理。达到限额时应该返回特定的错误信息。
- Testable: yes - property

9.4 WHEN 达到重试上限 THEN Campaign Automation SHALL 返回明确的错误信息
- Thoughts: 这是测试重试上限。达到重试上限后应该返回错误。
- Testable: yes - property

9.5 WHEN 发生错误 THEN Campaign Automation SHALL 记录详细的错误日志
- Thoughts: 这是测试日志记录。发生错误时应该记录详细的日志。
- Testable: yes - property

### 属性反思（Property Reflection）

在完成初步分析后，我们需要识别和消除冗余属性：

**冗余分析**：

1. **预算优化规则（3.2, 3.3, 3.4）** 可以合并为一个综合属性：
   - 原属性 3.2：CPA 超标 → 降低预算
   - 原属性 3.3：ROAS 超标 → 提升预算
   - 原属性 3.4：无转化 → 暂停
   - **合并后**：预算优化应该根据表现指标生成正确的优化建议

2. **平台路由（7.1, 7.2, 7.3）** 是具体示例，可以合并为一个属性：
   - **合并后**：对于任意支持的平台，应该路由到正确的适配器

3. **错误处理（9.1, 9.2, 9.4）** 可以合并：
   - **合并后**：API 调用失败时应该按照重试策略执行，达到上限后返回错误

### 正确性属性列表

#### Property 1: Campaign 创建完整性
*For any* valid campaign parameters, creating a campaign should return a valid campaign_id and successfully create the campaign structure.
**Validates: Requirements 1.1**

#### Property 2: Adset 数量正确性
*For any* campaign with N age groups, the number of created adsets should equal N.
**Validates: Requirements 1.2**

#### Property 3: Adset 配置完整性
*For any* created adset, it should have valid targeting configuration (audience type, age range, countries), placement settings (automatic), and bid strategy (lowest_cost).
**Validates: Requirements 1.3, 1.4, 1.5**

#### Property 4: 素材挂载完整性
*For any* list of creative_ids and adsets, the number of created ads should equal len(creative_ids) × len(adsets), and each ad should have a non-empty copy.
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

#### Property 5: 预算优化规则正确性
*For any* adset performance data, the optimization recommendations should follow the rules: ROAS > target × 1.5 → increase budget 20%, CPA > target × 1.5 → decrease budget 20%, no conversions for 3 days → pause adset.
**Validates: Requirements 3.2, 3.3, 3.4**

#### Property 6: 优化结果格式完整性
*For any* optimization operation, the result should include a list of optimizations with adset_id, action, and reason for each optimization.
**Validates: Requirements 3.5**

#### Property 7: 管理操作执行正确性
*For any* valid campaign management operation (pause/start/delete), the operation should be executed and the new status should be reflected in the return value.
**Validates: Requirements 4.1, 4.5**

#### Property 8: 数据同步一致性
*For any* successful platform API call, the data should be synchronized to Web Platform via MCP.
**Validates: Requirements 4.3**

#### Property 9: API 重试机制
*For any* failed API call, the system should retry up to 3 times with exponential backoff, and return an error after reaching the retry limit.
**Validates: Requirements 4.4, 9.1, 9.4**

#### Property 10: A/B 测试预算均分
*For any* A/B test with N variants and total budget B, each variant should receive budget B/N.
**Validates: Requirements 5.2**

#### Property 11: A/B 测试统计分析
*For any* A/B test with sufficient sample size (≥100 conversions per variant), the analysis should use chi-square test and return p-value and winner if p-value < 0.05.
**Validates: Requirements 5.3, 5.4**

#### Property 12: A/B 测试建议生成
*For any* A/B test with identified winner, the result should include specific optimization recommendations.
**Validates: Requirements 5.6**

#### Property 13: 规则创建和执行
*For any* valid rule configuration, the rule should be created successfully, and when the condition is met, the corresponding action should be executed and logged.
**Validates: Requirements 6.1, 6.3, 6.4, 6.5**

#### Property 14: 平台适配器路由
*For any* supported platform (meta, tiktok, google), the system should route to the correct adapter and return results in a unified format.
**Validates: Requirements 7.1, 7.2, 7.3, 7.4**

#### Property 15: 平台错误处理
*For any* platform API error, the system should return a clear error message with error code and details.
**Validates: Requirements 7.5, 9.3, 9.5**

#### Property 16: 状态查询完整性
*For any* campaign status query, the result should include campaign, adset, and ad level data with all key metrics (spend, revenue, ROAS, CPA).
**Validates: Requirements 8.1, 8.2, 8.3**

#### Property 17: 缓存降级机制
*For any* failed real-time data fetch, the system should return cached data if available.
**Validates: Requirements 8.4**

#### Property 18: 超时处理
*For any* API call, a 30-second timeout should be enforced, and timeout errors should trigger retry.
**Validates: Requirements 9.2**


---

## 错误处理（Error Handling）

### 错误分类

#### 1. 平台 API 错误

**Meta API 错误**：
- 令牌过期：返回 6001 错误，提示重新授权
- 预算不足：返回 6002 错误，提示充值
- 素材被拒：返回 6003 错误，提示修改素材
- API 限额：返回 1003 错误，建议稍后重试

**TikTok API 错误**：
- 认证失败：返回 1002 错误
- 参数无效：返回 1001 错误
- 服务不可用：返回 4000 错误，自动重试

**Google Ads API 错误**：
- 配额超限：返回 1005 错误
- 政策违规：返回 6005 错误

#### 2. MCP 调用错误

- 工具未找到：返回 3001 错误
- 参数无效：返回 3002 错误
- 执行超时：返回 3004 错误，自动重试
- 连接失败：返回 3000 错误，自动重试

#### 3. AI 服务错误

- 模型超时：返回 4001 错误，自动重试
- 生成失败：返回 4003 错误，使用默认文案
- 配额超限：返回 1005 错误

#### 4. 业务逻辑错误

- 广告账户未绑定：返回 6000 错误
- 素材不存在：返回 5000 错误
- 预算配置无效：返回 1001 错误
- Credit 余额不足：返回 6011 错误

### 重试策略

```python
class RetryStrategy:
    """重试策略配置"""
    
    # 可重试的错误类型
    RETRYABLE_ERRORS = [
        "CONNECTION_FAILED",
        "TIMEOUT",
        "API_RATE_LIMIT",
        "SERVICE_UNAVAILABLE",
        "AI_MODEL_FAILED"
    ]
    
    # 重试配置
    MAX_RETRIES = 3
    BASE_DELAY = 1  # 秒
    MAX_DELAY = 30  # 秒
    BACKOFF_FACTOR = 2  # 指数退避因子
    
    @staticmethod
    async def retry_with_backoff(
        func: Callable,
        max_retries: int = MAX_RETRIES,
        error_types: List[str] = RETRYABLE_ERRORS
    ) -> Any:
        """
        指数退避重试
        
        重试延迟：1s, 2s, 4s
        """
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                
                error_type = getattr(e, 'error_type', 'UNKNOWN')
                if error_type not in error_types:
                    raise
                
                delay = min(
                    RetryStrategy.BASE_DELAY * (RetryStrategy.BACKOFF_FACTOR ** attempt),
                    RetryStrategy.MAX_DELAY
                )
                
                logger.warning(
                    f"Retry attempt {attempt + 1}/{max_retries} after {delay}s",
                    extra={"error": str(e), "error_type": error_type}
                )
                
                await asyncio.sleep(delay)
```

### 错误响应格式

```python
@dataclass
class ErrorResponse:
    status: str = "error"
    error: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "error": {
                "code": self.error.get("code"),
                "type": self.error.get("type"),
                "message": self.error.get("message"),
                "details": self.error.get("details", {}),
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": self.error.get("request_id")
            }
        }

# 使用示例
error = ErrorResponse(
    error={
        "code": "6001",
        "type": "AD_ACCOUNT_TOKEN_EXPIRED",
        "message": "广告账户授权已过期，请重新授权",
        "details": {
            "ad_account_id": "act_123456",
            "platform": "meta",
            "action_url": "/settings/ad-accounts"
        },
        "request_id": "req_123456"
    }
)
```

### 降级策略

#### 1. AI 文案生成降级

```python
async def generate_ad_copy_with_fallback(
    product_url: str,
    creative_id: str,
    platform: str
) -> str:
    """
    AI 文案生成（带降级）
    
    降级策略：
    1. 尝试 Gemini 2.5 Pro
    2. 失败后尝试 Gemini 2.5 Flash
    3. 仍失败则使用模板文案
    """
    try:
        return await gemini_client.generate_content(
            prompt=f"生成广告文案：{product_url}",
            model="gemini-2.5-pro"
        )
    except Exception as e:
        logger.warning(f"Gemini Pro failed, trying Flash: {e}")
        try:
            return await gemini_client.generate_content(
                prompt=f"生成广告文案：{product_url}",
                model="gemini-2.5-flash"
            )
        except Exception as e:
            logger.error(f"All AI models failed, using template: {e}")
            return f"限时优惠！立即购买 {product_url}"
```

#### 2. 数据查询降级

```python
async def get_campaign_status_with_cache(
    campaign_id: str,
    platform: str,
    context: dict
) -> dict:
    """
    获取广告状态（带缓存降级）
    
    降级策略：
    1. 尝试从平台 API 获取实时数据
    2. 失败后从 Redis 缓存获取
    3. 缓存也失败则返回错误
    """
    cache_key = f"campaign_status:{campaign_id}"
    
    try:
        # 尝试获取实时数据
        status = await platform_adapter.get_campaign_status(campaign_id)
        
        # 更新缓存
        await redis_client.setex(
            cache_key,
            300,  # 5 分钟
            json.dumps(status)
        )
        
        return status
    except Exception as e:
        logger.warning(f"Failed to fetch real-time data, trying cache: {e}")
        
        # 尝试从缓存获取
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.info("Returning cached data")
            return json.loads(cached_data)
        
        # 缓存也失败
        raise Exception("Failed to fetch campaign status from both API and cache")
```

### 日志记录

```python
# 结构化日志格式
logger.error(
    "Campaign creation failed",
    extra={
        "error_code": "4003",
        "error_type": "GENERATION_FAILED",
        "user_id": context["user_id"],
        "session_id": context["session_id"],
        "platform": "meta",
        "parameters": {
            "objective": "sales",
            "daily_budget": 100
        },
        "retry_count": 2,
        "stack_trace": traceback.format_exc()
    }
)
```

---

## 测试策略（Testing Strategy）

### 单元测试

**测试范围**：
- 各组件的核心逻辑
- 数据模型验证
- 错误处理逻辑
- 工具函数

**测试框架**：pytest + pytest-asyncio

**示例**：
```python
@pytest.mark.asyncio
async def test_campaign_manager_create_campaign():
    """测试 Campaign 创建"""
    manager = CampaignManager()
    
    result = await manager.create_campaign(
        objective="sales",
        daily_budget=100,
        target_countries=["US"],
        creative_ids=["creative_1"],
        platform="meta",
        context={"user_id": "user_123"}
    )
    
    assert result["status"] == "success"
    assert "campaign_id" in result
    assert len(result["adsets"]) == 3  # 3 age groups

@pytest.mark.asyncio
async def test_budget_optimizer_roas_increase():
    """测试 ROAS 超标时增加预算"""
    optimizer = BudgetOptimizer()
    
    performance_data = {
        "adsets": [
            {
                "id": "adset_1",
                "roas": 4.5,  # 超过目标 3.0 的 150%
                "target_roas": 3.0,
                "daily_budget": 30
            }
        ]
    }
    
    optimizations = await optimizer.optimize_budget(
        campaign_id="campaign_123",
        optimization_strategy="auto",
        target_metric="roas",
        context={"user_id": "user_123"}
    )
    
    assert len(optimizations) == 1
    assert optimizations[0]["action"] == "increase_budget"
    assert optimizations[0]["new_budget"] == 36  # 30 * 1.2
```

### 属性测试（Property-Based Testing）

**测试框架**：Hypothesis

**配置**：每个属性测试运行至少 100 次迭代

**标注格式**：每个属性测试必须包含注释，格式为：
```python
# Feature: campaign-automation, Property 1: Campaign 创建完整性
```

**示例**：
```python
from hypothesis import given, strategies as st

# Feature: campaign-automation, Property 1: Campaign 创建完整性
@given(
    objective=st.sampled_from(["sales", "traffic", "awareness"]),
    daily_budget=st.floats(min_value=10, max_value=10000),
    target_countries=st.lists(
        st.sampled_from(["US", "CA", "UK", "AU"]),
        min_size=1,
        max_size=5
    ),
    creative_ids=st.lists(
        st.text(min_size=1, max_size=20),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_campaign_creation_completeness(
    objective, daily_budget, target_countries, creative_ids
):
    """
    Property 1: Campaign 创建完整性
    For any valid campaign parameters, creating a campaign should return 
    a valid campaign_id and successfully create the campaign structure.
    """
    manager = CampaignManager()
    
    result = await manager.create_campaign(
        objective=objective,
        daily_budget=daily_budget,
        target_countries=target_countries,
        creative_ids=creative_ids,
        platform="meta",
        context={"user_id": "user_123"}
    )
    
    # 验证返回格式
    assert result["status"] == "success"
    assert "campaign_id" in result
    assert result["campaign_id"] is not None
    assert len(result["campaign_id"]) > 0
    
    # 验证 campaign 被创建
    campaign = await manager.get_campaign_details(
        campaign_id=result["campaign_id"],
        platform="meta",
        context={"user_id": "user_123"}
    )
    assert campaign is not None

# Feature: campaign-automation, Property 2: Adset 数量正确性
@given(
    age_groups=st.lists(
        st.tuples(
            st.integers(min_value=18, max_value=65),
            st.integers(min_value=18, max_value=65)
        ).filter(lambda x: x[0] < x[1]),
        min_size=1,
        max_size=5
    )
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_adset_count_correctness(age_groups):
    """
    Property 2: Adset 数量正确性
    For any campaign with N age groups, the number of created adsets 
    should equal N.
    """
    manager = CampaignManager()
    
    result = await manager.create_campaign(
        objective="sales",
        daily_budget=100,
        target_countries=["US"],
        creative_ids=["creative_1"],
        platform="meta",
        age_groups=age_groups,
        context={"user_id": "user_123"}
    )
    
    assert len(result["adsets"]) == len(age_groups)

# Feature: campaign-automation, Property 5: 预算优化规则正确性
@given(
    roas=st.floats(min_value=0, max_value=10),
    target_roas=st.floats(min_value=1, max_value=5),
    cpa=st.floats(min_value=1, max_value=100),
    target_cpa=st.floats(min_value=1, max_value=50),
    days_no_conversion=st.integers(min_value=0, max_value=7)
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_budget_optimization_rules(
    roas, target_roas, cpa, target_cpa, days_no_conversion
):
    """
    Property 5: 预算优化规则正确性
    For any adset performance data, the optimization recommendations 
    should follow the rules.
    """
    optimizer = BudgetOptimizer()
    
    performance_data = {
        "adsets": [{
            "id": "adset_1",
            "roas": roas,
            "target_roas": target_roas,
            "cpa": cpa,
            "target_cpa": target_cpa,
            "days_running": days_no_conversion,
            "conversions": 0 if days_no_conversion >= 3 else 10,
            "daily_budget": 30
        }]
    }
    
    optimizations = await optimizer.optimize_budget(
        campaign_id="campaign_123",
        optimization_strategy="auto",
        target_metric="roas",
        context={"user_id": "user_123"}
    )
    
    # 验证优化规则
    if roas > target_roas * 1.5:
        assert any(opt["action"] == "increase_budget" for opt in optimizations)
    elif cpa > target_cpa * 1.5:
        assert any(opt["action"] == "decrease_budget" for opt in optimizations)
    elif days_no_conversion >= 3:
        assert any(opt["action"] == "pause" for opt in optimizations)
```

### 集成测试

**测试范围**：
- Module API 端到端测试
- MCP 工具调用测试
- 平台 API 集成测试（使用 Mock）

**示例**：
```python
@pytest.mark.asyncio
async def test_integration_create_campaign_end_to_end():
    """端到端测试：创建完整广告系列"""
    capability = CampaignAutomation()
    
    # 模拟 MCP 和平台 API
    with patch('mcp_client.call_tool') as mock_mcp, \
         patch('meta_adapter.create_campaign') as mock_meta:
        
        mock_mcp.return_value = {"status": "success"}
        mock_meta.return_value = {"id": "campaign_123"}
        
        result = await capability.execute(
            action="create_campaign",
            parameters={
                "objective": "sales",
                "daily_budget": 100,
                "creative_ids": ["creative_1", "creative_2"],
                "platform": "meta"
            },
            context={"user_id": "user_123"}
        )
        
        assert result["status"] == "success"
        assert "campaign_id" in result
        assert mock_mcp.called
        assert mock_meta.called
```

### 测试覆盖率目标

- 单元测试覆盖率：> 80%
- 属性测试：覆盖所有 18 个正确性属性
- 集成测试：覆盖所有 Module API actions


---

## 技术实现细节（Technical Implementation Details）

### 1. Module API 实现

```python
class CampaignAutomation:
    """Campaign Automation 功能模块"""
    
    def __init__(self):
        self.campaign_manager = CampaignManager()
        self.budget_optimizer = BudgetOptimizer()
        self.ab_test_manager = ABTestManager()
        self.rule_engine = RuleEngine()
        self.mcp_client = MCPClient()
        self.gemini_client = GeminiClient()
        self.redis_client = RedisClient()
        
        # 平台适配器
        self.adapters = {
            "meta": MetaAdapter(),
            "tiktok": TikTokAdapter(),
            "google": GoogleAdapter()
        }
    
    async def execute(
        self,
        action: str,
        parameters: dict,
        context: dict
    ) -> dict:
        """
        执行广告引擎操作
        
        支持的 actions:
        - create_campaign
        - optimize_budget
        - manage_campaign
        - create_ab_test
        - analyze_ab_test
        - create_rule
        - get_campaign_status
        """
        try:
            # 路由到对应的处理方法
            handler = getattr(self, f"_handle_{action}", None)
            if not handler:
                return {
                    "status": "error",
                    "error": {
                        "code": "1001",
                        "type": "INVALID_REQUEST",
                        "message": f"Unknown action: {action}"
                    }
                }
            
            # 执行操作
            result = await handler(parameters, context)
            return result
            
        except Exception as e:
            logger.error(
                f"Campaign automation error: {action}",
                extra={
                    "error": str(e),
                    "action": action,
                    "user_id": context.get("user_id"),
                    "stack_trace": traceback.format_exc()
                }
            )
            return {
                "status": "error",
                "error": {
                    "code": "1000",
                    "type": "UNKNOWN_ERROR",
                    "message": str(e)
                }
            }
    
    async def _handle_create_campaign(
        self,
        parameters: dict,
        context: dict
    ) -> dict:
        """处理创建广告系列请求"""
        platform = parameters.get("platform", "meta")
        adapter = self.adapters.get(platform)
        
        if not adapter:
            return {
                "status": "error",
                "error": {
                    "code": "1001",
                    "type": "INVALID_REQUEST",
                    "message": f"Unsupported platform: {platform}"
                }
            }
        
        # 创建 Campaign
        campaign = await adapter.create_campaign({
            "name": f"Campaign {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "objective": parameters["objective"],
            "daily_budget": parameters["daily_budget"]
        })
        
        # 创建 Adsets
        adsets = await self._create_adsets(
            campaign_id=campaign["id"],
            daily_budget=parameters["daily_budget"],
            target_countries=parameters.get("target_countries", ["US"]),
            adapter=adapter
        )
        
        # 创建 Ads
        ads = await self._create_ads(
            adsets=adsets,
            creative_ids=parameters.get("creative_ids", []),
            product_url=parameters.get("product_url"),
            platform=platform,
            adapter=adapter,
            context=context
        )
        
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
            "adsets": [
                {
                    "adset_id": a["id"],
                    "name": a["name"],
                    "daily_budget": a["daily_budget"]
                }
                for a in adsets
            ],
            "ads": [
                {
                    "ad_id": a["id"],
                    "creative_id": a["creative_id"],
                    "adset_id": a["adset_id"]
                }
                for a in ads
            ],
            "message": "广告系列创建成功"
        }
    
    async def _create_adsets(
        self,
        campaign_id: str,
        daily_budget: float,
        target_countries: List[str],
        adapter: PlatformAdapter
    ) -> List[dict]:
        """创建 Adsets"""
        age_groups = [(18, 35), (36, 50), (51, 65)]
        budget_per_adset = daily_budget / len(age_groups)
        
        adsets = []
        for age_min, age_max in age_groups:
            adset = await adapter.create_adset({
                "campaign_id": campaign_id,
                "name": f"{target_countries[0]} {age_min}-{age_max}",
                "daily_budget": budget_per_adset,
                "targeting": {
                    "age_min": age_min,
                    "age_max": age_max,
                    "countries": target_countries,
                    "targeting_optimization": "none"  # Broad audience
                },
                "optimization_goal": "value",
                "bid_strategy": "lowest_cost_without_cap",
                "placements": "automatic"
            })
            adsets.append(adset)
        
        return adsets
    
    async def _create_ads(
        self,
        adsets: List[dict],
        creative_ids: List[str],
        product_url: str,
        platform: str,
        adapter: PlatformAdapter,
        context: dict
    ) -> List[dict]:
        """创建 Ads"""
        ads = []
        
        for adset in adsets:
            for creative_id in creative_ids:
                # 生成广告文案
                copy = await self._generate_ad_copy(
                    product_url=product_url,
                    creative_id=creative_id,
                    platform=platform
                )
                
                # 创建 Ad
                ad = await adapter.create_ad({
                    "adset_id": adset["id"],
                    "creative_id": creative_id,
                    "name": f"Ad {creative_id}",
                    "copy": copy
                })
                
                ads.append({
                    "id": ad["id"],
                    "creative_id": creative_id,
                    "adset_id": adset["id"],
                    "copy": copy
                })
        
        return ads
    
    async def _generate_ad_copy(
        self,
        product_url: str,
        creative_id: str,
        platform: str
    ) -> str:
        """生成广告文案（带降级）"""
        try:
            prompt = f"""为以下产品生成吸引人的广告文案（125 字以内）：
产品链接：{product_url}
平台：{platform}

要求：
1. 突出产品卖点
2. 包含行动号召（CTA）
3. 符合平台规范
4. 语言简洁有力"""
            
            response = await self.gemini_client.generate_content(
                prompt=prompt,
                model="gemini-2.5-pro"
            )
            return response["text"]
            
        except Exception as e:
            logger.warning(f"AI copy generation failed, using template: {e}")
            return f"限时优惠！立即购买 {product_url}"
```

### 2. 平台适配器实现

```python
class MetaAdapter(PlatformAdapter):
    """Meta Marketing API 适配器"""
    
    def __init__(self):
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
    
    async def create_campaign(self, params: dict) -> dict:
        """创建 Campaign"""
        from facebook_business.adobjects.campaign import Campaign
        from facebook_business.adobjects.adaccount import AdAccount
        
        ad_account = AdAccount(f"act_{params['ad_account_id']}")
        
        campaign = Campaign(parent_id=ad_account.get_id_assured())
        campaign[Campaign.Field.name] = params["name"]
        campaign[Campaign.Field.objective] = params["objective"]
        campaign[Campaign.Field.status] = Campaign.Status.active
        campaign[Campaign.Field.daily_budget] = int(params["daily_budget"] * 100)
        
        campaign.remote_create()
        
        return {
            "id": campaign[Campaign.Field.id],
            "name": params["name"]
        }
    
    async def create_adset(self, params: dict) -> dict:
        """创建 Adset"""
        from facebook_business.adobjects.adset import AdSet
        
        adset = AdSet(parent_id=params["campaign_id"])
        adset[AdSet.Field.name] = params["name"]
        adset[AdSet.Field.daily_budget] = int(params["daily_budget"] * 100)
        adset[AdSet.Field.billing_event] = AdSet.BillingEvent.impressions
        adset[AdSet.Field.optimization_goal] = AdSet.OptimizationGoal.value
        adset[AdSet.Field.bid_strategy] = AdSet.BidStrategy.lowest_cost_without_cap
        adset[AdSet.Field.targeting] = params["targeting"]
        adset[AdSet.Field.status] = AdSet.Status.active
        
        adset.remote_create()
        
        return {
            "id": adset[AdSet.Field.id],
            "name": params["name"],
            "daily_budget": params["daily_budget"]
        }
    
    async def create_ad(self, params: dict) -> dict:
        """创建 Ad"""
        from facebook_business.adobjects.ad import Ad
        from facebook_business.adobjects.adcreative import AdCreative
        
        # 创建 AdCreative
        creative = AdCreative(parent_id=params["ad_account_id"])
        creative[AdCreative.Field.name] = params["name"]
        creative[AdCreative.Field.object_story_spec] = {
            "page_id": params["page_id"],
            "link_data": {
                "message": params["copy"],
                "link": params["link"],
                "image_hash": params["creative_id"]
            }
        }
        creative.remote_create()
        
        # 创建 Ad
        ad = Ad(parent_id=params["adset_id"])
        ad[Ad.Field.name] = params["name"]
        ad[Ad.Field.creative] = {"creative_id": creative[AdCreative.Field.id]}
        ad[Ad.Field.status] = Ad.Status.active
        
        ad.remote_create()
        
        return {
            "id": ad[Ad.Field.id],
            "creative_id": params["creative_id"]
        }
    
    async def update_budget(self, adset_id: str, budget: float) -> dict:
        """更新预算"""
        from facebook_business.adobjects.adset import AdSet
        
        adset = AdSet(adset_id)
        adset[AdSet.Field.daily_budget] = int(budget * 100)
        adset.remote_update()
        
        return {"status": "success", "new_budget": budget}
    
    async def pause_adset(self, adset_id: str) -> dict:
        """暂停 Adset"""
        from facebook_business.adobjects.adset import AdSet
        
        adset = AdSet(adset_id)
        adset[AdSet.Field.status] = AdSet.Status.paused
        adset.remote_update()
        
        return {"status": "success", "new_status": "paused"}
```

### 3. 预算优化器实现

```python
class BudgetOptimizer:
    """预算优化器"""
    
    async def optimize_budget(
        self,
        campaign_id: str,
        optimization_strategy: str,
        target_metric: str,
        context: dict
    ) -> List[dict]:
        """
        优化预算
        
        优化规则：
        1. ROAS > 目标 * 1.5 → 增加预算 20%
        2. CPA > 目标 * 1.5 → 降低预算 20%
        3. 连续 3 天无转化 → 暂停 Adset
        """
        # 获取表现数据
        performance = await self._get_performance_data(campaign_id, context)
        
        optimizations = []
        
        for adset in performance["adsets"]:
            # 规则 1: ROAS 超标 → 增加预算
            if target_metric == "roas" and adset.get("roas", 0) > adset.get("target_roas", 0) * 1.5:
                new_budget = adset["daily_budget"] * 1.2
                optimizations.append({
                    "adset_id": adset["id"],
                    "action": "increase_budget",
                    "old_budget": adset["daily_budget"],
                    "new_budget": new_budget,
                    "reason": f"ROAS {adset['roas']:.2f} 超过目标 {adset['target_roas']:.2f}，表现优秀"
                })
            
            # 规则 2: CPA 超标 → 降低预算
            elif target_metric == "cpa" and adset.get("cpa", 0) > adset.get("target_cpa", 0) * 1.5:
                new_budget = adset["daily_budget"] * 0.8
                optimizations.append({
                    "adset_id": adset["id"],
                    "action": "decrease_budget",
                    "old_budget": adset["daily_budget"],
                    "new_budget": new_budget,
                    "reason": f"CPA {adset['cpa']:.2f} 超过目标 {adset['target_cpa']:.2f}，需要优化"
                })
            
            # 规则 3: 连续 3 天无转化 → 暂停
            if adset.get("conversions", 0) == 0 and adset.get("days_running", 0) >= 3:
                optimizations.append({
                    "adset_id": adset["id"],
                    "action": "pause",
                    "reason": "连续 3 天无转化"
                })
        
        return optimizations
    
    async def _get_performance_data(
        self,
        campaign_id: str,
        context: dict
    ) -> dict:
        """获取表现数据"""
        # 从 MCP 获取数据
        result = await self.mcp_client.call_tool(
            "get_reports",
            {
                "user_id": context["user_id"],
                "campaign_id": campaign_id,
                "date_range": {
                    "start_date": (datetime.now() - timedelta(days=7)).isoformat(),
                    "end_date": datetime.now().isoformat()
                },
                "level": "adset",
                "metrics": ["spend", "revenue", "conversions", "roas", "cpa"]
            }
        )
        
        return result
```

### 4. A/B 测试管理器实现

```python
class ABTestManager:
    """A/B 测试管理器"""
    
    async def analyze_ab_test(
        self,
        test_id: str,
        context: dict
    ) -> dict:
        """
        分析 A/B 测试结果
        
        使用卡方检验判断统计显著性
        """
        # 获取测试数据
        test_data = await self._get_test_data(test_id, context)
        
        # 检查样本量
        min_sample_size = 100
        variants = test_data["variants"]
        
        for variant in variants:
            if variant["conversions"] < min_sample_size:
                return {
                    "status": "success",
                    "test_id": test_id,
                    "message": "数据不足，建议继续测试",
                    "details": {
                        "min_required": min_sample_size,
                        "current_samples": [v["conversions"] for v in variants]
                    }
                }
        
        # 执行卡方检验
        chi_square_result = self._chi_square_test(variants)
        
        # 判断获胜者
        winner = None
        if chi_square_result["p_value"] < 0.05:
            # 差异显著，选择转化率最高的
            winner = max(variants, key=lambda v: v["conversion_rate"])
        
        # 生成建议
        recommendations = self._generate_recommendations(variants, winner)
        
        return {
            "status": "success",
            "test_id": test_id,
            "results": [
                {
                    "creative_id": v["creative_id"],
                    "spend": v["spend"],
                    "revenue": v["revenue"],
                    "roas": v["roas"],
                    "ctr": v["ctr"],
                    "conversion_rate": v["conversion_rate"],
                    "rank": i + 1
                }
                for i, v in enumerate(sorted(variants, key=lambda x: x["roas"], reverse=True))
            ],
            "winner": {
                "creative_id": winner["creative_id"],
                "confidence": 95,
                "p_value": chi_square_result["p_value"]
            } if winner else None,
            "recommendations": recommendations
        }
    
    def _chi_square_test(self, variants: List[dict]) -> dict:
        """执行卡方检验"""
        from scipy.stats import chi2_contingency
        
        # 构建列联表
        observed = [
            [v["conversions"], v["impressions"] - v["conversions"]]
            for v in variants
        ]
        
        # 执行检验
        chi2, p_value, dof, expected = chi2_contingency(observed)
        
        return {
            "chi2": chi2,
            "p_value": p_value,
            "dof": dof
        }
    
    def _generate_recommendations(
        self,
        variants: List[dict],
        winner: Optional[dict]
    ) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        if winner:
            # 找出表现最差的
            worst = min(variants, key=lambda v: v["roas"])
            recommendations.append(f"暂停 {worst['creative_id']}（表现最差）")
            recommendations.append(f"增加 {winner['creative_id']} 预算 50%")
        else:
            recommendations.append("差异不显著，建议继续测试或增加样本量")
        
        return recommendations
```

### 5. 缓存策略

```python
class CacheManager:
    """缓存管理器"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.default_ttl = 300  # 5 分钟
    
    async def get_or_fetch(
        self,
        key: str,
        fetch_func: Callable,
        ttl: int = None
    ) -> Any:
        """获取缓存或执行获取函数"""
        # 尝试从缓存获取
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        
        # 缓存未命中，执行获取函数
        data = await fetch_func()
        
        # 存入缓存
        await self.redis.setex(
            key,
            ttl or self.default_ttl,
            json.dumps(data)
        )
        
        return data
    
    async def invalidate(self, pattern: str):
        """清除缓存"""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
```

---

## 部署和运维（Deployment and Operations）

### 部署架构

```
┌─────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Campaign Automation Service (3 replicas)        │  │
│  │  - CPU: 2 cores                                  │  │
│  │  - Memory: 4GB                                   │  │
│  │  - Auto-scaling: 3-10 pods                       │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Redis Cache (1 replica)                         │  │
│  │  - Memory: 2GB                                   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Celery Workers (2 replicas)                     │  │
│  │  - For Rule Engine periodic tasks                │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 环境变量配置

```bash
# .env
# AI Orchestrator
AI_ORCHESTRATOR_URL=http://ai-orchestrator:8001

# Web Platform MCP
MCP_SERVER_URL=http://web-platform:8000/mcp
MCP_AUTH_TOKEN=<service_token>

# Gemini API
GEMINI_API_KEY=<api_key>
GEMINI_MODEL_PRO=gemini-2.5-pro
GEMINI_MODEL_FLASH=gemini-2.5-flash

# Meta Ads
META_APP_ID=<app_id>
META_APP_SECRET=<app_secret>
META_API_VERSION=v18.0

# TikTok Ads
TIKTOK_APP_ID=<app_id>
TIKTOK_APP_SECRET=<app_secret>

# Google Ads
GOOGLE_ADS_DEVELOPER_TOKEN=<token>
GOOGLE_ADS_CLIENT_ID=<client_id>
GOOGLE_ADS_CLIENT_SECRET=<client_secret>

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 监控指标

```python
# Prometheus 指标
from prometheus_client import Counter, Histogram, Gauge

# 请求计数
campaign_requests_total = Counter(
    'campaign_automation_requests_total',
    'Total campaign automation requests',
    ['action', 'status']
)

# 响应时间
campaign_request_duration = Histogram(
    'campaign_automation_request_duration_seconds',
    'Campaign automation request duration',
    ['action']
)

# 活跃规则数
active_rules_gauge = Gauge(
    'campaign_automation_active_rules',
    'Number of active automation rules'
)

# API 调用计数
platform_api_calls_total = Counter(
    'platform_api_calls_total',
    'Total platform API calls',
    ['platform', 'endpoint', 'status']
)
```

### 告警规则

```yaml
# Prometheus 告警规则
groups:
  - name: campaign_automation
    rules:
      - alert: HighErrorRate
        expr: rate(campaign_requests_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in campaign automation"
          
      - alert: SlowResponse
        expr: histogram_quantile(0.95, campaign_request_duration_seconds) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow response time (P95 > 10s)"
          
      - alert: PlatformAPIFailure
        expr: rate(platform_api_calls_total{status="error"}[5m]) > 0.2
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High platform API failure rate"
```

---

**文档版本**：v1.0  
**最后更新**：2024-11-29  
**维护者**：AAE 开发团队
