# 需求文档 - Ad Performance（广告投放报表）

## 简介（Introduction）

Ad Performance 是 AI Orchestrator 的功能模块之一，负责广告数据抓取、报表生成和 AI 智能分析相关的业务逻辑。该模块被 AI Orchestrator 调用，通过 MCP 协议与 Web Platform 通信进行数据存储，专注于自动化报表和智能优化建议。

## 术语表（Glossary）

- **Ad Performance**：广告投放报表模块
- **Campaign**：广告系列
- **Adset**：广告组
- **Ad**：广告
- **ROAS**：广告支出回报率（Return on Ad Spend）
- **CPA**：单次转化成本（Cost Per Acquisition）
- **CTR**：点击率（Click-Through Rate）
- **MER**：营销效率比（Marketing Efficiency Ratio）
- **Daily Report**：每日报告
- **Anomaly Detection**：异常检测
- **Module API**：功能模块接口，被 AI Orchestrator 调用
- **MCP Client**：MCP 客户端，调用 Web Platform 工具

---

## 接口协议（Interface Specifications）

Ad Performance 的所有接口协议详见：**[INTERFACES.md](../INTERFACES.md)**

### 对外接口

1. **Module API**：被 AI Orchestrator 调用
   - 协议定义：[INTERFACES.md - Module API](../INTERFACES.md#3-module-apiai-orchestrator--功能模块)
   - 统一接口：execute(action, parameters, context)

2. **MCP Client**：调用 Web Platform 工具
   - 协议定义：[INTERFACES.md - MCP 协议](../INTERFACES.md#2-mcp-协议ai-orchestrator--web-platform)
   - 工具调用：save_metrics、get_metrics 等

3. **Ad Platform APIs**：调用广告平台 API
   - Meta Marketing API
   - TikTok Ads API
   - Google Ads API

### 模块边界

**职责范围**：
- ✅ 广告数据抓取
- ✅ 数据聚合和计算
- ✅ AI 智能分析
- ✅ 异常检测
- ✅ 优化建议生成
- ✅ 报表生成和导出

**不负责**：
- ❌ 数据存储（由 Web Platform 负责）
- ❌ 用户认证（由 Web Platform 负责）
- ❌ 对话管理（由 AI Orchestrator 负责）
- ❌ 广告创建和修改（由 Campaign Automation 负责）
- ❌ 报表可视化（由 Web Platform 前端负责）

详见：[INTERFACES.md - 功能模块边界](../INTERFACES.md#3-功能模块边界)

---

## Module API（能力模块接口）

### 接口定义

```python
class AdPerformance:
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
        pass
```

### 支持的 Actions

#### 1. fetch_ad_data - 抓取广告数据

**参数**：
```json
{
  "platform": "meta",
  "date_range": {
    "start_date": "2024-11-20",
    "end_date": "2024-11-26"
  },
  "levels": ["campaign", "adset", "ad"],
  "metrics": ["spend", "impressions", "clicks", "conversions", "revenue"]
}
```

**返回**：
```json
{
  "status": "success",
  "data": {
    "campaigns": [
      {
        "campaign_id": "123456",
        "name": "Summer Sale",
        "spend": 500.00,
        "revenue": 1500.00,
        "roas": 3.0,
        "conversions": 45
      }
    ],
    "adsets": [...],
    "ads": [...]
  },
  "sync_time": "2024-11-26T10:00:00Z",
  "message": "数据抓取成功"
}
```

#### 2. generate_daily_report - 生成每日报告

**参数**：
```json
{
  "date": "2024-11-25",
  "include_ai_analysis": true,
  "include_recommendations": true
}
```

**返回**：
```json
{
  "status": "success",
  "report": {
    "date": "2024-11-25",
    "summary": {
      "total_spend": 500.00,
      "total_revenue": 1350.00,
      "overall_roas": 2.7,
      "total_conversions": 42,
      "avg_cpa": 11.90
    },
    "ai_analysis": {
      "key_insights": [
        "ROAS 下降 10% 相比前一天",
        "CPA 上涨 15%，主要由于 Adset 'US 36-50' 表现下滑",
        "Campaign 'Summer Sale' 表现最佳，ROAS 3.5"
      ],
      "trends": {
        "roas_trend": "declining",
        "spend_trend": "stable",
        "conversion_trend": "declining"
      }
    },
    "recommendations": [
      {
        "priority": "high",
        "action": "pause_adset",
        "target": "adset_789",
        "reason": "连续 3 天 ROAS < 1.5",
        "expected_impact": "节省 $50/天"
      },
      {
        "priority": "medium",
        "action": "increase_budget",
        "target": "adset_456",
        "reason": "ROAS 4.2，表现优秀",
        "expected_impact": "增加收入 $100/天"
      }
    ]
  },
  "message": "每日报告生成成功"
}
```

#### 3. analyze_performance - 分析广告表现

**参数**：
```json
{
  "entity_type": "campaign",
  "entity_id": "campaign_123",
  "date_range": {
    "start_date": "2024-11-20",
    "end_date": "2024-11-26"
  },
  "comparison_period": "previous_week"
}
```

**返回**：
```json
{
  "status": "success",
  "analysis": {
    "entity_id": "campaign_123",
    "entity_name": "Summer Sale",
    "current_period": {
      "spend": 500.00,
      "revenue": 1500.00,
      "roas": 3.0,
      "conversions": 45,
      "cpa": 11.11
    },
    "previous_period": {
      "spend": 480.00,
      "revenue": 1680.00,
      "roas": 3.5,
      "conversions": 48,
      "cpa": 10.00
    },
    "changes": {
      "spend": "+4.2%",
      "revenue": "-10.7%",
      "roas": "-14.3%",
      "conversions": "-6.3%",
      "cpa": "+11.1%"
    },
    "insights": [
      "ROAS 下降主要由于转化率降低",
      "建议检查素材疲劳度",
      "考虑更新广告创意"
    ]
  }
}
```

#### 4. detect_anomalies - 检测异常

**参数**：
```json
{
  "metrics": ["roas", "cpa", "ctr"],
  "sensitivity": "medium",
  "lookback_days": 7
}
```

**返回**：
```json
{
  "status": "success",
  "anomalies": [
    {
      "metric": "cpa",
      "entity_type": "adset",
      "entity_id": "adset_789",
      "entity_name": "US 36-50",
      "current_value": 25.50,
      "expected_value": 12.00,
      "deviation": "+112.5%",
      "severity": "high",
      "detected_at": "2024-11-26T08:00:00Z",
      "recommendation": "暂停该 Adset 或降低预算"
    },
    {
      "metric": "roas",
      "entity_type": "campaign",
      "entity_id": "campaign_456",
      "entity_name": "Black Friday",
      "current_value": 1.2,
      "expected_value": 2.8,
      "deviation": "-57.1%",
      "severity": "critical",
      "detected_at": "2024-11-26T08:00:00Z",
      "recommendation": "立即检查广告设置和素材"
    }
  ],
  "message": "检测到 2 个异常"
}
```

#### 5. generate_recommendations - 生成优化建议

**参数**：
```json
{
  "optimization_goal": "maximize_roas",
  "budget_constraint": 1000,
  "min_roas_threshold": 2.0
}
```

**返回**：
```json
{
  "status": "success",
  "recommendations": [
    {
      "priority": "high",
      "action": "pause_adset",
      "target": {
        "type": "adset",
        "id": "adset_789",
        "name": "US 36-50"
      },
      "reason": "ROAS 1.2 低于目标 2.0，连续 3 天表现不佳",
      "expected_impact": {
        "spend_reduction": 50.00,
        "roas_improvement": "+0.3"
      },
      "confidence": 0.92
    },
    {
      "priority": "high",
      "action": "increase_budget",
      "target": {
        "type": "adset",
        "id": "adset_456",
        "name": "US 18-35"
      },
      "reason": "ROAS 4.5 远超目标，有扩展空间",
      "expected_impact": {
        "spend_increase": 100.00,
        "revenue_increase": 450.00
      },
      "confidence": 0.88
    },
    {
      "priority": "medium",
      "action": "refresh_creative",
      "target": {
        "type": "ad",
        "id": "ad_123",
        "name": "Summer Ad 1"
      },
      "reason": "CTR 下降 30%，可能存在素材疲劳",
      "expected_impact": {
        "ctr_improvement": "+0.5%",
        "roas_improvement": "+0.2"
      },
      "confidence": 0.75
    }
  ],
  "summary": {
    "total_recommendations": 3,
    "high_priority": 2,
    "medium_priority": 1,
    "expected_roas_improvement": "+0.5"
  }
}
```

#### 6. export_report - 导出报表

**参数**：
```json
{
  "report_type": "daily",
  "date_range": {
    "start_date": "2024-11-20",
    "end_date": "2024-11-26"
  },
  "format": "pdf",
  "include_charts": true
}
```

**返回**：
```json
{
  "status": "success",
  "download_url": "https://aae-reports.s3.amazonaws.com/report_123.pdf",
  "expires_at": "2024-11-27T10:00:00Z",
  "file_size": "2.5 MB",
  "message": "报表已导出"
}
```

#### 7. get_metrics_summary - 获取指标摘要

**参数**：
```json
{
  "date_range": {
    "start_date": "2024-11-26",
    "end_date": "2024-11-26"
  },
  "group_by": "platform"
}
```

**返回**：
```json
{
  "status": "success",
  "summary": {
    "total": {
      "spend": 500.00,
      "revenue": 1350.00,
      "roas": 2.7,
      "conversions": 42,
      "cpa": 11.90
    },
    "by_platform": {
      "meta": {
        "spend": 300.00,
        "revenue": 900.00,
        "roas": 3.0,
        "conversions": 28
      },
      "tiktok": {
        "spend": 150.00,
        "revenue": 375.00,
        "roas": 2.5,
        "conversions": 12
      },
      "google": {
        "spend": 50.00,
        "revenue": 75.00,
        "roas": 1.5,
        "conversions": 2
      }
    }
  }
}
```

详见：[INTERFACES.md - Ad Performance](../INTERFACES.md#reporting-capability)

---

## MCP 工具调用（MCP Tool Invocation）

该模块通过 MCP Client 调用 Web Platform 的以下工具：

### 1. save_metrics - 保存指标数据

```python
result = await mcp_client.call_tool(
    "save_metrics",
    {
        "user_id": context["user_id"],
        "platform": "meta",
        "date": "2024-11-26",
        "metrics": {
            "spend": 500.00,
            "revenue": 1500.00,
            "roas": 3.0,
            "conversions": 45
        }
    }
)
```

### 2. get_metrics - 获取历史指标

```python
result = await mcp_client.call_tool(
    "get_metrics",
    {
        "user_id": context["user_id"],
        "date_range": {
            "start_date": "2024-11-20",
            "end_date": "2024-11-26"
        },
        "platforms": ["meta", "tiktok"]
    }
)
```

详见：[INTERFACES.md - MCP 协议](../INTERFACES.md#2-mcp-协议unified-ai-agent--user-portal)

---

## 需求（Requirements）

### 需求 1：自动数据抓取

**用户故事**：作为 AI Orchestrator，我需要抓取广告数据，以便为用户提供报表分析。

#### 验收标准

1. WHEN 调用 fetch_ad_data action THEN Ad Performance SHALL 从广告平台 API 抓取数据
2. WHEN 抓取数据 THEN Ad Performance SHALL 获取 Campaign、Adset、Ad 三级数据
3. WHEN 抓取数据 THEN Ad Performance SHALL 获取花费、展示、点击、转化、收入等指标
4. WHEN 抓取失败 THEN Ad Performance SHALL 自动重试最多 3 次
5. WHEN 抓取完成 THEN Ad Performance SHALL 通过 MCP 保存数据到 Web Platform

---

### 需求 1.1：手动刷新数据

**用户故事**：作为用户，我想要手动刷新广告数据，以便查看最新的表现。

#### 数据同步状态显示

```
┌─────────────────────────────────────────────────────────────┐
│                    数据同步状态显示                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  报表页面顶部显示：                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  📊 数据最后更新：2024-11-26 10:30:00                │   │
│  │  [🔄 刷新数据] 按钮                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  刷新状态：                                                  │
│  - 空闲：显示"刷新数据"按钮                                  │
│  - 刷新中：显示"正在刷新..."和进度动画                       │
│  - 刷新完成：显示"数据已更新"提示（3秒后消失）              │
│  - 刷新失败：显示"刷新失败，请稍后重试"错误提示              │
│                                                             │
│  刷新限制：                                                  │
│  - 两次刷新间隔至少 5 分钟                                   │
│  - 达到限制时按钮禁用并显示倒计时                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 验收标准

1. WHEN 用户访问报表页面 THEN Web Platform SHALL 显示数据最后更新时间
2. WHEN 用户点击"刷新数据"按钮 THEN Web Platform SHALL 通过 AI Agent 调用 Ad Performance 抓取最新数据
3. WHEN 数据刷新中 THEN Web Platform SHALL 显示刷新进度和状态
4. WHEN 数据刷新完成 THEN Web Platform SHALL 更新页面数据并显示"数据已更新"提示
5. WHEN 两次刷新间隔小于 5 分钟 THEN Web Platform SHALL 禁用刷新按钮并显示剩余等待时间

---

### 需求 2：每日报告生成

**用户故事**：作为 AI Orchestrator，我需要生成每日报告，以便为用户提供 AI 分析和建议。

#### 验收标准

1. WHEN 调用 generate_daily_report action THEN Ad Performance SHALL 生成每日报告
2. WHEN 报告生成 THEN Ad Performance SHALL 包含核心指标摘要
3. WHEN 报告生成 THEN Ad Performance SHALL 使用 AI 分析关键变化和趋势
4. WHEN 报告生成 THEN Ad Performance SHALL 生成优化建议
5. WHEN 报告生成 THEN Ad Performance SHALL 返回结构化的报告数据

---

### 需求 3：广告表现分析

**用户故事**：作为 AI Orchestrator，我需要分析广告表现，以便识别问题和机会。

#### 验收标准

1. WHEN 调用 analyze_performance action THEN Ad Performance SHALL 分析指定实体的表现
2. WHEN 分析完成 THEN Ad Performance SHALL 对比当前周期和历史周期
3. WHEN 分析完成 THEN Ad Performance SHALL 计算变化百分比
4. WHEN 分析完成 THEN Ad Performance SHALL 使用 AI 生成洞察
5. WHEN 分析完成 THEN Ad Performance SHALL 返回详细的分析结果

---

### 需求 4：异常检测

**用户故事**：作为 AI Orchestrator，我需要检测异常情况，以便及时提醒用户。

#### 验收标准

1. WHEN 调用 detect_anomalies action THEN Ad Performance SHALL 检测指标异常
2. WHEN CPA 突然上涨超过 50% THEN Ad Performance SHALL 标记为高严重性异常
3. WHEN ROAS 突然下降超过 30% THEN Ad Performance SHALL 标记为严重异常
4. WHEN 检测到异常 THEN Ad Performance SHALL 计算偏离度和严重性
5. WHEN 检测到异常 THEN Ad Performance SHALL 提供处理建议

---

### 需求 5：优化建议生成

**用户故事**：作为 AI Orchestrator，我需要生成优化建议，以便帮助用户改善广告表现。

#### 验收标准

1. WHEN 调用 generate_recommendations action THEN Ad Performance SHALL 分析所有广告实体
2. WHEN 识别低效 Adset THEN Ad Performance SHALL 生成暂停建议
3. WHEN 识别高效 Adset THEN Ad Performance SHALL 生成加预算建议
4. WHEN 识别素材疲劳 THEN Ad Performance SHALL 生成更新素材建议
5. WHEN 生成建议 THEN Ad Performance SHALL 计算预期影响和置信度

---

### 需求 6：报表导出

**用户故事**：作为 AI Orchestrator，我需要导出报表，以便用户进行深度分析或汇报。

#### 验收标准

1. WHEN 调用 export_report action THEN Ad Performance SHALL 生成报表文件
2. WHEN 导出 CSV THEN Ad Performance SHALL 包含完整的数据表格
3. WHEN 导出 PDF THEN Ad Performance SHALL 包含图表和 AI 分析
4. WHEN 导出完成 THEN Ad Performance SHALL 上传到 S3 并生成下载链接
5. WHEN 生成下载链接 THEN Ad Performance SHALL 设置 24 小时过期时间

---

### 需求 7：多平台数据聚合

**用户故事**：作为 AI Orchestrator，我需要聚合多平台数据，以便提供统一的报表视图。

#### 验收标准

1. WHEN 调用 get_metrics_summary action THEN Ad Performance SHALL 聚合所有平台数据
2. WHEN 聚合数据 THEN Ad Performance SHALL 支持按平台分组
3. WHEN 聚合数据 THEN Ad Performance SHALL 计算总体指标
4. WHEN 聚合数据 THEN Ad Performance SHALL 确保数据一致性
5. WHEN 聚合完成 THEN Ad Performance SHALL 返回结构化的摘要数据

---

### 需求 8：定时任务调度

**用户故事**：作为系统，我需要定时抓取数据和生成报告，以便自动化运营。

#### 架构说明（修正版）

定时任务采用 **Web Platform 调度 + 直接调用功能模块** 的架构：

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Platform                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Celery Beat (调度器)                       │   │
│  │  - 每 6 小时触发数据抓取任务                         │   │
│  │  - 每天 9:00 触发报告生成任务                        │   │
│  │  - 每小时触发异常检测任务                            │   │
│  │  - 每天 2:00 触发 Token 检查任务                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Celery Worker (执行器)                     │   │
│  │                                                      │   │
│  │  from modules.ad_performance import AdPerformance │
│  │                                                      │   │
│  │  @celery.task                                        │   │
│  │  def fetch_ad_data_task(user_id):                   │   │
│  │      capability = AdPerformance()             │   │
│  │      result = capability.execute(                   │   │
│  │          action="fetch_ad_data",                    │   │
│  │          parameters={...},                          │   │
│  │          context={"user_id": user_id}               │   │
│  │      )                                               │   │
│  │      # 发送通知                                      │   │
│  │      send_notification(user_id, result)             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ 直接调用（Python 模块导入）
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Ad Performance（Python 模块）             │
│  - fetch_ad_data(): 从广告平台抓取数据                      │
│  - generate_daily_report(): 生成每日报告                   │
│  - detect_anomalies(): 检测异常                            │
│  - 通过 MCP Client 调用 Web Platform 存储数据               │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ MCP Protocol
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Web Platform MCP Server                         │
│  - save_metrics(): 保存指标数据                            │
│  - get_metrics(): 获取历史数据                             │
│  - create_notification(): 创建通知                         │
└─────────────────────────────────────────────────────────────┘
```

**架构说明**：

**为什么不通过 AI Orchestrator？**
- ❌ AI Orchestrator 是对话式的，专注于理解用户意图和协调对话流程
- ❌ 定时任务是确定性的后台任务，不需要意图识别和对话管理
- ✅ Celery Worker 直接导入功能模块 Python 代码更高效
- ✅ 避免不必要的网络调用和序列化开销

**两种调用路径对比**：

| 场景 | 触发方式 | 执行路径 | 是否需要意图识别 |
|------|---------|---------|----------------|
| 用户对话 | 用户发起 | 前端 → WebSocket → AI Orchestrator → 功能模块 | ✅ 需要 |
| 定时任务 | 系统定时 | Celery Beat → Celery Worker → 功能模块（直接调用） | ❌ 不需要 |
| 手动刷新 | 用户点击按钮 | 前端 → WebSocket → AI Orchestrator → 功能模块 | ✅ 需要（理解"刷新"意图） |

**定时任务具体内容**：

1. **数据抓取任务**（每 6 小时）
   - 调用 Meta/TikTok/Google Ads API
   - 获取 Campaign/Adset/Ad 的花费、展示、点击、转化、收入数据
   - 存储到 TimescaleDB 时序表

2. **报告生成任务**（每天 9:00）
   - 汇总昨日数据
   - AI 分析关键变化和趋势
   - 生成优化建议
   - 发送邮件和站内通知

3. **异常检测任务**（每小时）
   - 检测 CPA/ROAS/CTR 异常波动
   - 识别高严重性问题
   - 发送紧急通知

4. **Token 检查任务**（每天 2:00）
   - 检查所有广告账户 Token 有效期
   - 提前 24 小时尝试刷新
   - 刷新失败时通知用户

#### 验收标准

1. WHEN 系统启动 THEN Web Platform SHALL 启动 Celery Beat 调度器和 Celery Worker
2. WHEN 到达调度时间 THEN Celery Worker SHALL 直接导入并调用 Ad Performance Python 模块
3. WHEN Ad Performance 执行 THEN Ad Performance SHALL 通过 MCP Client 访问 Web Platform 数据
4. WHEN 任务执行完成 THEN Celery Worker SHALL 调用 Web Platform API 发送通知给用户
5. WHEN 任务执行失败 THEN Celery Worker SHALL 记录错误日志并重试最多 3 次

---

### 需求 9：通知推送

**用户故事**：作为系统，我需要将定时任务结果推送给用户，以便用户及时了解广告状态。

#### 通知推送流程

```
┌─────────────────────────────────────────────────────────────┐
│              定时任务通知推送流程                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Celery Worker 执行完成                                      │
│         │                                                    │
│         ▼                                                    │
│  调用 Web Platform API                                        │
│  POST /api/internal/notifications                           │
│  {                                                           │
│    "user_id": "user_123",                                   │
│    "type": "daily_report",                                  │
│    "data": {...}                                            │
│  }                                                           │
│         │                                                    │
│         ▼                                                    │
│  Web Platform 处理通知                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. 创建站内通知记录                                 │   │
│  │  2. 根据用户偏好决定是否发送邮件                     │   │
│  │  3. 如果是紧急通知，强制发送邮件                     │   │
│  │  4. 更新未读通知计数                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 验收标准

1. WHEN 每日报告生成完成 THEN Celery Worker SHALL 调用 Web Platform API 创建通知
2. WHEN 检测到严重异常 THEN Celery Worker SHALL 创建紧急通知并强制发送邮件
3. WHEN 用户启用 Webhook THEN Web Platform SHALL 推送通知到用户指定 URL
4. WHEN 用户下次登录 THEN Web Platform SHALL 在通知中心显示未读通知
5. WHEN 用户配置通知偏好 THEN Web Platform SHALL 按用户偏好选择推送渠道

---

## 非功能性需求（Non-Functional Requirements）

### 性能需求

1. Ad Performance SHALL 在 5 秒内完成数据抓取（单平台）
2. Ad Performance SHALL 在 10 秒内生成每日报告
3. Ad Performance SHALL 在 3 秒内完成异常检测
4. Ad Performance SHALL 支持查询 90 天的历史数据

### 数据准确性需求

1. Ad Performance SHALL 确保数据与广告平台一致（误差 < 1%）
2. Ad Performance SHALL 在数据不一致时以广告平台数据为准
3. Ad Performance SHALL 记录所有数据同步日志
4. Ad Performance SHALL 验证数据完整性

### 可靠性需求

1. Ad Performance SHALL 在 API 调用失败时自动重试
2. Ad Performance SHALL 在数据抓取失败时通知用户
3. Ad Performance SHALL 保证每日报告 100% 生成
4. Ad Performance SHALL 在系统重启后自动恢复定时任务

### 成本控制需求

1. Ad Performance SHALL 控制单次数据抓取成本不超过 $0.05
2. Ad Performance SHALL 缓存数据（5 分钟）减少 API 调用
3. Ad Performance SHALL 监控 API 调用成本并报警

---

## 技术约束（Technical Constraints）

### 广告平台 API

- **Meta Marketing API**：v18.0+
- **TikTok Ads API**：v1.3+
- **Google Ads API**：v14+

### AI 模型

- **智能分析**：Gemini 2.5 Pro
- **异常检测**：统计算法 + Gemini 2.5 Flash 辅助
- **建议生成**：Gemini 2.5 Pro

### 技术栈

- **开发语言**：Python 3.11+
- **框架**：FastAPI
- **广告 SDK**：facebook-business SDK, tiktok-business-api, google-ads
- **MCP 通信**：MCP SDK (Python)
- **数据库**：PostgreSQL + TimescaleDB（时序数据）
- **缓存**：Redis
- **任务队列**：Celery（定时任务）
- **图表生成**：Matplotlib 或 Plotly

### 部署约束

- **容器化**：Docker
- **编排**：Kubernetes 或 Docker Compose
- **监控**：Prometheus + Grafana
- **日志**：结构化日志（JSON 格式）

---

## 实现示例（Implementation Examples）

### Capability 接口实现

```python
class AdPerformance:
    def __init__(self):
        self.meta_api = MetaMarketingAPI()
        self.tiktok_api = TikTokAdsAPI()
        self.google_api = GoogleAdsAPI()
        self.gemini_client = GeminiClient()
        self.mcp_client = MCPClient()
        self.cache = RedisCache()
    
    async def execute(self, action: str, parameters: dict, context: dict) -> dict:
        try:
            if action == "fetch_ad_data":
                return await self._fetch_ad_data(parameters, context)
            elif action == "generate_daily_report":
                return await self._generate_daily_report(parameters, context)
            elif action == "analyze_performance":
                return await self._analyze_performance(parameters, context)
            elif action == "detect_anomalies":
                return await self._detect_anomalies(parameters, context)
            elif action == "generate_recommendations":
                return await self._generate_recommendations(parameters, context)
            elif action == "export_report":
                return await self._export_report(parameters, context)
            elif action == "get_metrics_summary":
                return await self._get_metrics_summary(parameters, context)
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Performance analytics error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _fetch_ad_data(self, parameters: dict, context: dict) -> dict:
        platform = parameters["platform"]
        date_range = parameters["date_range"]
        
        # 选择对应的广告平台 API
        if platform == "meta":
            api = self.meta_api
        elif platform == "tiktok":
            api = self.tiktok_api
        elif platform == "google":
            api = self.google_api
        else:
            return {"status": "error", "message": f"Unsupported platform: {platform}"}
        
        # 抓取数据
        data = await api.get_insights(
            date_range=date_range,
            levels=parameters.get("levels", ["campaign"]),
            metrics=parameters.get("metrics", ["spend", "revenue"])
        )
        
        # 保存到 Web Platform
        await self.mcp_client.call_tool(
            "save_metrics",
            {
                "user_id": context["user_id"],
                "platform": platform,
                "date": date_range["end_date"],
                "metrics": data
            }
        )
        
        return {
            "status": "success",
            "data": data,
            "sync_time": datetime.now().isoformat(),
            "message": "数据抓取成功"
        }
    
    async def _generate_daily_report(self, parameters: dict, context: dict) -> dict:
        date = parameters["date"]
        
        # 获取数据
        metrics = await self.mcp_client.call_tool(
            "get_metrics",
            {
                "user_id": context["user_id"],
                "date_range": {
                    "start_date": date,
                    "end_date": date
                }
            }
        )
        
        # 使用 AI 分析
        ai_analysis = await self.gemini_client.generate_content(
            f"分析以下广告数据并提供洞察：{json.dumps(metrics)}"
        )
        
        # 生成建议
        recommendations = await self._generate_recommendations(
            {"optimization_goal": "maximize_roas"},
            context
        )
        
        return {
            "status": "success",
            "report": {
                "date": date,
                "summary": metrics["summary"],
                "ai_analysis": ai_analysis,
                "recommendations": recommendations["recommendations"]
            },
            "message": "每日报告生成成功"
        }
    
    async def _detect_anomalies(self, parameters: dict, context: dict) -> dict:
        metrics = parameters.get("metrics", ["roas", "cpa"])
        lookback_days = parameters.get("lookback_days", 7)
        
        # 获取历史数据
        historical_data = await self._get_historical_data(
            context["user_id"],
            lookback_days
        )
        
        # 检测异常
        anomalies = []
        for metric in metrics:
            detected = await self._detect_metric_anomaly(
                metric,
                historical_data,
                sensitivity=parameters.get("sensitivity", "medium")
            )
            anomalies.extend(detected)
        
        return {
            "status": "success",
            "anomalies": anomalies,
            "message": f"检测到 {len(anomalies)} 个异常"
        }
```

### 广告平台 API 调用示例

```python
# Meta Marketing API
async def fetch_meta_insights(date_range: dict) -> dict:
    insights = account.get_insights(
        fields=[
            'campaign_id',
            'campaign_name',
            'spend',
            'impressions',
            'clicks',
            'conversions',
            'revenue'
        ],
        params={
            'time_range': {
                'since': date_range['start_date'],
                'until': date_range['end_date']
            },
            'level': 'campaign'
        }
    )
    return insights

# AI 分析示例
async def analyze_with_ai(metrics: dict) -> dict:
    prompt = f"""
    分析以下广告数据并提供洞察：
    
    总花费：${metrics['spend']}
    总收入：${metrics['revenue']}
    ROAS：{metrics['roas']}
    转化数：{metrics['conversions']}
    
    请提供：
    1. 关键洞察（3-5 条）
    2. 趋势分析
    3. 优化建议
    """
    
    response = await gemini_client.generate_content(prompt)
    return response
```

---

**文档版本**：v1.0
**最后更新**：2024-11-26
**维护者**：AAE 开发团队
