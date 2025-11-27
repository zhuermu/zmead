# AAE 系统接口协议文档（Interface Specifications）

## 文档说明

本文档定义 AAE 系统各模块之间的接口协议和边界，确保模块间通信标准化。

---

## 模块边界定义（Module Boundaries）

### 1. User Portal 边界

**职责范围**：
- ✅ 用户界面（Web 前端）
- ✅ 用户认证和授权
- ✅ 数据存储和管理
- ✅ MCP Server 实现
- ✅ WebSocket Server 实现

**不负责**：
- ❌ AI 对话逻辑
- ❌ 意图识别
- ❌ 能力模块协调

**对外接口**：
- WebSocket API（前端 ↔ Unified AI Agent）
- MCP Server（Unified AI Agent ↔ User Portal）
- RESTful API（可选，用于第三方集成）

---

### 2. Unified AI Agent 边界

**职责范围**：
- ✅ 对话理解和意图识别
- ✅ 能力模块协调
- ✅ 对话上下文管理
- ✅ 结果聚合和返回

**不负责**：
- ❌ 数据存储
- ❌ 用户认证
- ❌ 具体业务逻辑实现

**对外接口**：
- WebSocket API（接收前端消息）
- MCP Client（调用 User Portal 工具）
- Capability Module API（调用能力模块）

---

### 3. 能力模块边界

**职责范围**：
- ✅ 具体业务逻辑实现
- ✅ AI 模型调用
- ✅ 第三方 API 调用

**不负责**：
- ❌ 数据存储（通过 MCP 调用 User Portal）
- ❌ 对话管理
- ❌ 用户认证

**对外接口**：
- Capability API（被 Unified AI Agent 调用）
- MCP Client（调用 User Portal 工具）

---

## 接口协议定义（Interface Protocols）

### 1. WebSocket 协议（前端 ↔ Unified AI Agent）

#### 连接建立

```
WebSocket URL: wss://api.aae.com/ws/chat
Headers:
  Authorization: Bearer <jwt_token>
  User-Agent: AAE-Web/1.0
```

#### 消息格式

**用户消息**：
```json
{
  "type": "user_message",
  "message_id": "msg_123456",
  "content": "帮我生成素材并创建广告",
  "user_id": "user_123",
  "session_id": "session_456",
  "timestamp": "2024-11-26T10:00:00Z",
  "metadata": {
    "page": "dashboard",
    "context": {}
  }
}
```

**AI 回复（流式）**：
```json
{
  "type": "agent_message",
  "message_id": "msg_123457",
  "content": "好的！正在为你生成素材...",
  "streaming": true,
  "chunk_index": 0,
  "session_id": "session_456",
  "timestamp": "2024-11-26T10:00:01Z"
}
```

**AI 回复（完整）**：
```json
{
  "type": "agent_message",
  "message_id": "msg_123457",
  "content": "✅ 素材和广告都已完成！",
  "streaming": false,
  "session_id": "session_456",
  "timestamp": "2024-11-26T10:00:30Z",
  "metadata": {
    "creative_ids": ["creative_1", "creative_2"],
    "campaign_id": "campaign_123"
  }
}
```

**操作建议**：
```json
{
  "type": "agent_action",
  "message_id": "msg_123458",
  "action": "show_button",
  "button_text": "查看素材",
  "button_action": "navigate",
  "button_params": {
    "url": "/creatives"
  },
  "session_id": "session_456"
}
```

**错误消息**：
```json
{
  "type": "error",
  "message_id": "msg_123459",
  "error_code": "GENERATION_FAILED",
  "error_message": "素材生成失败，请稍后重试",
  "session_id": "session_456",
  "timestamp": "2024-11-26T10:00:15Z"
}
```

---

### 2. MCP 协议（Unified AI Agent ↔ User Portal）

#### 连接建立

```python
# MCP Client 初始化
mcp_client = MCPClient(
    server_url="http://localhost:8000/mcp",
    auth_token="<service_token>"
)
```

#### 工具定义

**User Portal 提供的 MCP 工具**：

```json
{
  "tools": [
    {
      "name": "get_creatives",
      "description": "获取用户的素材列表",
      "parameters": {
        "type": "object",
        "properties": {
          "user_id": {"type": "string", "required": true},
          "limit": {"type": "integer", "default": 10},
          "offset": {"type": "integer", "default": 0},
          "filters": {
            "type": "object",
            "properties": {
              "status": {"type": "string"},
              "created_after": {"type": "string"}
            }
          }
        }
      },
      "returns": {
        "type": "array",
        "items": {
          "creative_id": "string",
          "url": "string",
          "score": "number",
          "created_at": "string"
        }
      }
    },
    {
      "name": "create_creative",
      "description": "创建新素材",
      "parameters": {
        "type": "object",
        "properties": {
          "user_id": {"type": "string", "required": true},
          "file_url": {"type": "string", "required": true},
          "metadata": {
            "type": "object",
            "properties": {
              "product_url": {"type": "string"},
              "style": {"type": "string"},
              "score": {"type": "number"}
            }
          }
        }
      },
      "returns": {
        "creative_id": "string",
        "url": "string",
        "created_at": "string"
      }
    },
    {
      "name": "get_reports",
      "description": "获取广告报表数据",
      "parameters": {
        "type": "object",
        "properties": {
          "user_id": {"type": "string", "required": true},
          "date_range": {
            "type": "object",
            "properties": {
              "start_date": {"type": "string"},
              "end_date": {"type": "string"}
            }
          },
          "metrics": {
            "type": "array",
            "items": {"type": "string"}
          },
          "level": {
            "type": "string",
            "enum": ["campaign", "adset", "ad"]
          }
        }
      },
      "returns": {
        "type": "array",
        "items": {
          "id": "string",
          "name": "string",
          "metrics": "object"
        }
      }
    },
    {
      "name": "create_campaign",
      "description": "创建广告 Campaign",
      "parameters": {
        "type": "object",
        "properties": {
          "user_id": {"type": "string", "required": true},
          "ad_account_id": {"type": "string", "required": true},
          "campaign_data": {
            "type": "object",
            "properties": {
              "name": {"type": "string"},
              "objective": {"type": "string"},
              "budget": {"type": "number"},
              "creative_ids": {"type": "array"}
            }
          }
        }
      },
      "returns": {
        "campaign_id": "string",
        "status": "string",
        "created_at": "string"
      }
    },
    {
      "name": "create_landing_page",
      "description": "创建落地页",
      "parameters": {
        "type": "object",
        "properties": {
          "user_id": {"type": "string", "required": true},
          "product_url": {"type": "string", "required": true},
          "template": {"type": "string"},
          "language": {"type": "string", "default": "en"}
        }
      },
      "returns": {
        "landing_page_id": "string",
        "url": "string",
        "created_at": "string"
      }
    },
    {
      "name": "analyze_competitor",
      "description": "分析竞品",
      "parameters": {
        "type": "object",
        "properties": {
          "user_id": {"type": "string", "required": true},
          "competitor_url": {"type": "string", "required": true},
          "analysis_type": {
            "type": "string",
            "enum": ["product", "creative", "strategy"]
          }
        }
      },
      "returns": {
        "analysis_id": "string",
        "insights": "object",
        "recommendations": "array"
      }
    }
  ]
}
```

---

### MCP 工具完整清单（Complete MCP Tools List）

User Portal 作为 MCP Server，为 Unified AI Agent 提供以下工具：

#### 素材管理工具（Creative Management Tools）

| 工具名称 | 描述 | 使用场景 |
|---------|------|---------|
| `get_creatives` | 获取素材列表 | Creative Capability 查询素材 |
| `get_creative` | 获取单个素材详情 | Creative Capability 获取素材信息 |
| `create_creative` | 创建新素材 | Creative Capability 存储生成的素材 |
| `update_creative` | 更新素材元数据 | Creative Capability 更新素材评分/标签 |
| `delete_creative` | 删除素材 | Creative Capability 删除素材 |

#### 报表数据工具（Reporting Data Tools）

| 工具名称 | 描述 | 使用场景 |
|---------|------|---------|
| `get_reports` | 获取报表数据 | Reporting Capability 查询广告数据 |
| `get_metrics` | 获取指标数据 | Reporting Capability 获取时序数据 |
| `save_metrics` | 保存指标数据 | Reporting Capability 存储抓取的数据 |
| `analyze_performance` | 分析广告表现 | Reporting Capability 分析数据 |

#### 落地页管理工具（Landing Page Management Tools）

| 工具名称 | 描述 | 使用场景 |
|---------|------|---------|
| `get_landing_pages` | 获取落地页列表 | Landing Page Capability 查询落地页 |
| `get_landing_page` | 获取单个落地页 | Landing Page Capability 获取落地页详情 |
| `create_landing_page` | 创建落地页 | Landing Page Capability 存储生成的落地页 |
| `update_landing_page` | 更新落地页 | Landing Page Capability 更新落地页内容 |
| `delete_landing_page` | 删除落地页 | Landing Page Capability 删除落地页 |

#### 投放管理工具（Campaign Management Tools）

| 工具名称 | 描述 | 使用场景 |
|---------|------|---------|
| `get_campaigns` | 获取广告系列列表 | Ad Engine Capability 查询广告 |
| `get_campaign` | 获取单个广告系列 | Ad Engine Capability 获取广告详情 |
| `create_campaign` | 创建广告系列 | Ad Engine Capability 创建广告 |
| `update_campaign` | 更新广告系列 | Ad Engine Capability 更新广告状态/预算 |
| `delete_campaign` | 删除广告系列 | Ad Engine Capability 删除广告 |

#### 市场洞察工具（Market Intelligence Tools）

| 工具名称 | 描述 | 使用场景 |
|---------|------|---------|
| `save_insight` | 保存洞察结果 | Market Intelligence Capability 存储分析结果 |
| `get_insights` | 获取历史洞察 | Market Intelligence Capability 查询历史分析 |
| `analyze_competitor` | 分析竞品 | Market Intelligence Capability 竞品分析 |
| `get_trends` | 获取市场趋势 | Market Intelligence Capability 趋势分析 |

#### 用户管理工具（User Management Tools）

| 工具名称 | 描述 | 使用场景 |
|---------|------|---------|
| `get_user_info` | 获取用户信息 | 所有 Capability 获取用户数据 |

#### Credit 计费工具（Credit Billing Tools）

| 工具名称 | 描述 | 使用场景 |
|---------|------|---------|
| `get_credit_balance` | 获取 Credit 余额 | 检查用户可用余额 |
| `check_credit` | 检查 Credit 是否足够 | 执行操作前预检查 |
| `deduct_credit` | 扣减 Credit | 操作完成后扣费 |
| `refund_credit` | 退还 Credit | 操作失败时退款 |
| `get_credit_history` | 获取 Credit 消耗历史 | 查询消费明细 |
| `get_credit_config` | 获取 Credit 换算配置 | 获取当前计费规则 |
| `estimate_credit` | 预估操作消耗 | 操作前预估成本 |

##### get_credit_balance 工具详情

**请求参数**：
```json
{
  "user_id": "user_123"
}
```

**返回结果**：
```json
{
  "status": "success",
  "balance": {
    "subscription_credits": 25000,
    "purchased_credits": 5000,
    "total_available": 30000,
    "subscription_plan": "standard",
    "subscription_expires_at": "2024-12-26T00:00:00Z",
    "overage_enabled": true
  }
}
```

##### check_credit 工具详情

**请求参数**：
```json
{
  "user_id": "user_123",
  "estimated_credits": 20,
  "operation_type": "generate_creative"
}
```

**返回结果**：
```json
{
  "status": "success",
  "allowed": true,
  "current_balance": 30000,
  "after_balance": 29980,
  "funding_source": "subscription"
}
```

##### deduct_credit 工具详情

**请求参数**：
```json
{
  "user_id": "user_123",
  "credits": 20,
  "operation_type": "generate_creative",
  "operation_id": "op_123456",
  "details": {
    "model": "stable-diffusion-xl",
    "count": 10
  }
}
```

**返回结果**：
```json
{
  "status": "success",
  "deducted": 20,
  "from_subscription": 20,
  "from_purchased": 0,
  "remaining_balance": {
    "subscription_credits": 24980,
    "purchased_credits": 5000,
    "total_available": 29980
  },
  "transaction_id": "txn_789"
}
```

##### get_credit_config 工具详情

**请求参数**：
```json
{
  "config_type": "all"
}
```

**返回结果**：
```json
{
  "status": "success",
  "config": {
    "model_rates": {
      "gemini-2.5-flash": {
        "input_per_1k_tokens": 0.1,
        "output_per_1k_tokens": 0.4
      },
      "claude-3.5-sonnet": {
        "input_per_1k_tokens": 2.0,
        "output_per_1k_tokens": 10.0
      },
      "stable-diffusion-xl": {
        "per_image": 2.0
      }
    },
    "operation_estimates": {
      "chat_simple": 1,
      "chat_complex": 5,
      "generate_creative": 2,
      "generate_landing_page": 30,
      "analyze_competitor": 15,
      "analyze_report": 10
    },
    "subscription_plans": {
      "standard": {
        "price_cny": 199,
        "credits": 30000
      },
      "professional": {
        "price_cny": 1999,
        "credits": 400000
      }
    },
    "overage_rate": 0.01
  }
}
```

#### 对话管理工具（Conversation Management Tools）

| 工具名称 | 描述 | 使用场景 |
|---------|------|---------|
| `save_conversation` | 保存对话历史 | Unified AI Agent 持久化对话 |
| `get_conversation_history` | 获取历史对话 | Unified AI Agent 恢复对话上下文 |
| `clear_conversation` | 清除对话上下文 | Unified AI Agent 开始新对话 |
| `get_conversation_list` | 获取用户对话列表 | User Portal 显示对话历史 |

#### 广告账户管理工具（Ad Account Management Tools）

| 工具名称 | 描述 | 使用场景 |
|---------|------|---------|
| `get_ad_account_token` | 获取广告账户访问令牌 | Ad Engine/Reporting Capability 调用广告平台 API |
| `list_ad_accounts` | 列出用户绑定的所有广告账户 | 选择操作账户 |
| `get_active_ad_account` | 获取当前选中的广告账户 | 确定操作目标账户 |
| `set_active_ad_account` | 设置当前操作的广告账户 | 切换操作账户 |
| `refresh_ad_account_token` | 刷新广告账户令牌 | 令牌过期时自动刷新 |

#### Landing Page 事件追踪工具（Landing Page Event Tools）

| 工具名称 | 描述 | 使用场景 |
|---------|------|---------|
| `save_lp_event` | 保存落地页事件 | 落地页追踪脚本上报事件 |
| `get_lp_events` | 获取落地页事件列表 | Reporting Capability 分析转化数据 |
| `get_lp_conversion_summary` | 获取落地页转化摘要 | 落地页性能分析 |

---

### MCP 工具索引表（MCP Tools Index）

按使用频率排序的快速索引：

| 优先级 | 工具名称 | 类别 | 调用频率 |
|-------|---------|------|---------|
| P0 | `check_credit` | Credit 计费 | 极高（每次操作前） |
| P0 | `deduct_credit` | Credit 计费 | 极高（每次操作后） |
| P0 | `create_creative` | 素材管理 | 高 |
| P0 | `create_campaign` | 投放管理 | 高 |
| P0 | `get_reports` | 报表数据 | 高 |
| P1 | `get_credit_balance` | Credit 计费 | 中 |
| P1 | `get_creatives` | 素材管理 | 中 |
| P1 | `get_campaigns` | 投放管理 | 中 |
| P1 | `save_metrics` | 报表数据 | 中 |
| P1 | `create_landing_page` | 落地页管理 | 中 |
| P2 | `refund_credit` | Credit 计费 | 低（失败时） |
| P2 | `update_creative` | 素材管理 | 低 |
| P2 | `update_campaign` | 投放管理 | 低 |
| P2 | `analyze_competitor` | 市场洞察 | 低 |
| P2 | `get_trends` | 市场洞察 | 低 |

---

#### 调用示例

```python
# 调用 MCP 工具
result = await mcp_client.call_tool(
    tool_name="create_creative",
    parameters={
        "user_id": "user_123",
        "file_url": "s3://bucket/creative.jpg",
        "metadata": {
            "product_url": "https://shop.com/product",
            "style": "modern",
            "score": 92
        }
    }
)

# 返回结果
{
    "creative_id": "creative_789",
    "url": "https://cdn.aae.com/creatives/creative_789.jpg",
    "created_at": "2024-11-26T10:00:30Z"
}
```

---

### 3. Capability Module API（Unified AI Agent ↔ 能力模块）

#### 接口定义

每个能力模块提供统一的接口：

```python
class CapabilityModule:
    async def execute(
        self,
        action: str,
        parameters: dict,
        context: dict
    ) -> dict:
        """
        执行能力模块的操作
        
        Args:
            action: 操作名称（如 "generate_creative"）
            parameters: 操作参数
            context: 上下文信息（用户ID、会话ID等）
        
        Returns:
            操作结果
        """
        pass
```

#### Creative Capability

```python
# 生成素材
result = await creative_capability.execute(
    action="generate_creative",
    parameters={
        "product_url": "https://shop.com/product",
        "count": 10,
        "style": "modern"
    },
    context={
        "user_id": "user_123",
        "session_id": "session_456"
    }
)

# 返回
{
    "status": "success",
    "creative_ids": ["creative_1", "creative_2", ...],
    "message": "已生成 10 张素材"
}
```

#### Market Intelligence Capability

```python
# 分析竞品
result = await market_intelligence_capability.execute(
    action="analyze_competitor",
    parameters={
        "competitor_url": "https://competitor.com/product"
    },
    context={
        "user_id": "user_123",
        "session_id": "session_456"
    }
)

# 返回
{
    "status": "success",
    "insights": {
        "price": "$79.99",
        "features": [...],
        "target_audience": "25-35岁"
    },
    "recommendations": [
        "使用简约风格素材",
        "目标受众 25-35 岁"
    ]
}
```

#### Reporting Capability

```python
# 获取报表
result = await reporting_capability.execute(
    action="get_performance_report",
    parameters={
        "date_range": {
            "start_date": "2024-11-20",
            "end_date": "2024-11-26"
        },
        "metrics": ["spend", "roas", "cpa"]
    },
    context={
        "user_id": "user_123",
        "session_id": "session_456"
    }
)

# 返回
{
    "status": "success",
    "report": {
        "total_spend": 875.50,
        "average_roas": 2.8,
        "average_cpa": 15.20
    },
    "insights": [
        "CPA 偏高，建议优化",
        "Adset X 表现较差"
    ]
}
```

#### Landing Page Capability

```python
# 生成落地页
result = await landing_page_capability.execute(
    action="create_landing_page",
    parameters={
        "product_url": "https://shop.com/product",
        "template": "modern",
        "language": "en"
    },
    context={
        "user_id": "user_123",
        "session_id": "session_456"
    }
)

# 返回
{
    "status": "success",
    "landing_page_id": "lp_123",
    "url": "https://user123.aae-pages.com/lp_123",
    "message": "落地页已生成"
}
```

#### Ad Engine Capability

```python
# 创建广告
result = await ad_engine_capability.execute(
    action="create_campaign",
    parameters={
        "budget": 100,
        "target_roas": 3.0,
        "creative_ids": ["creative_1", "creative_2"],
        "landing_page_id": "lp_123"
    },
    context={
        "user_id": "user_123",
        "session_id": "session_456"
    }
)

# 返回
{
    "status": "success",
    "campaign_id": "campaign_123",
    "adsets": ["adset_1", "adset_2", "adset_3"],
    "message": "广告已创建"
}
```

---

## 数据流示例（Data Flow Examples）

### 示例 1：用户生成素材

```
1. 用户在前端输入："帮我生成素材"
   │
   ▼
2. 前端通过 WebSocket 发送消息到 Unified AI Agent
   {
     "type": "user_message",
     "content": "帮我生成素材",
     "user_id": "user_123"
   }
   │
   ▼
3. Unified AI Agent 识别意图 → Creative Capability
   │
   ▼
4. Creative Capability 调用 AI 模型生成素材
   │
   ▼
5. Creative Capability 通过 MCP 调用 User Portal
   mcp_client.call_tool("create_creative", {...})
   │
   ▼
6. User Portal 存储素材到 S3 和 PostgreSQL
   │
   ▼
7. User Portal 返回结果给 Creative Capability
   {
     "creative_id": "creative_789",
     "url": "https://cdn.aae.com/..."
   }
   │
   ▼
8. Creative Capability 返回结果给 Unified AI Agent
   │
   ▼
9. Unified AI Agent 通过 WebSocket 返回给前端
   {
     "type": "agent_message",
     "content": "✅ 素材已生成！"
   }
   │
   ▼
10. 前端显示结果给用户
```

### 示例 2：用户创建完整广告流程

```
1. 用户："帮我生成素材并创建广告"
   │
   ▼
2. Unified AI Agent 识别多意图
   - 意图1: 生成素材 (Creative Capability)
   - 意图2: 创建广告 (Ad Engine Capability)
   │
   ▼
3. 协调器规划执行顺序
   Step 1: Creative Capability
   Step 2: Ad Engine Capability
   │
   ▼
4. 执行 Step 1: Creative Capability
   - 生成素材
   - 通过 MCP 存储到 User Portal
   - 返回 creative_ids
   │
   ▼
5. 执行 Step 2: Ad Engine Capability
   - 使用 Step 1 的 creative_ids
   - 创建 Campaign
   - 通过 MCP 存储到 User Portal
   - 返回 campaign_id
   │
   ▼
6. 聚合结果返回用户
   "✅ 素材和广告都已完成！
    - 素材：10 张
    - Campaign: #123456"
```

---

## 错误处理协议（Error Handling Protocol）

### 统一错误响应格式

所有 API（WebSocket、MCP、Capability）都应使用以下统一的错误格式：

```json
{
  "status": "error",
  "error": {
    "code": "4003",
    "type": "GENERATION_FAILED",
    "message": "素材生成失败",
    "details": {
      "reason": "AI 模型超时",
      "retry_after": 60,
      "retry_count": 2,
      "max_retries": 3
    },
    "timestamp": "2024-11-26T10:00:15Z",
    "request_id": "req_123456"
  }
}
```

### 错误代码字典（Error Code Dictionary）

#### 通用错误 (1xxx)

| 代码 | 类型 | 说明 | 是否可重试 | HTTP 状态码 |
|------|------|------|-----------|------------|
| 1000 | UNKNOWN_ERROR | 未知错误 | 否 | 500 |
| 1001 | INVALID_REQUEST | 无效请求 | 否 | 400 |
| 1002 | UNAUTHORIZED | 未授权 | 否 | 401 |
| 1003 | RATE_LIMIT_EXCEEDED | 超过速率限制 | 是 | 429 |
| 1004 | FORBIDDEN | 禁止访问 | 否 | 403 |
| 1005 | QUOTA_EXCEEDED | 超过使用限额 | 否 | 429 |

#### WebSocket 错误 (2xxx)

| 代码 | 类型 | 说明 | 是否可重试 | 处理建议 |
|------|------|------|-----------|---------|
| 2000 | CONNECTION_FAILED | 连接失败 | 是 | 自动重连 |
| 2001 | MESSAGE_TOO_LARGE | 消息过大 | 否 | 分割消息 |
| 2002 | INVALID_MESSAGE_FORMAT | 消息格式无效 | 否 | 检查格式 |
| 2003 | CONNECTION_TIMEOUT | 连接超时 | 是 | 重新连接 |
| 2004 | HEARTBEAT_TIMEOUT | 心跳超时 | 是 | 重新连接 |

#### MCP 错误 (3xxx)

| 代码 | 类型 | 说明 | 是否可重试 | 处理建议 |
|------|------|------|-----------|---------|
| 3000 | MCP_CONNECTION_FAILED | MCP 连接失败 | 是 | 重试连接 |
| 3001 | MCP_TOOL_NOT_FOUND | 工具未找到 | 否 | 检查工具名称 |
| 3002 | MCP_INVALID_PARAMETERS | 参数无效 | 否 | 检查参数 |
| 3003 | MCP_EXECUTION_FAILED | 执行失败 | 是 | 重试执行 |
| 3004 | MCP_TIMEOUT | 执行超时 | 是 | 增加超时时间 |

#### 能力模块错误 (4xxx)

| 代码 | 类型 | 说明 | 是否可重试 | 处理建议 |
|------|------|------|-----------|---------|
| 4000 | CAPABILITY_NOT_AVAILABLE | 能力模块不可用 | 是 | 稍后重试 |
| 4001 | AI_MODEL_FAILED | AI 模型失败 | 是 | 切换备选模型 |
| 4002 | EXTERNAL_API_FAILED | 外部 API 失败 | 是 | 重试调用 |
| 4003 | GENERATION_FAILED | 生成失败 | 是 | 重新生成 |
| 4004 | ANALYSIS_FAILED | 分析失败 | 是 | 重新分析 |
| 4005 | VALIDATION_FAILED | 验证失败 | 否 | 检查输入 |

#### 数据错误 (5xxx)

| 代码 | 类型 | 说明 | 是否可重试 | 处理建议 |
|------|------|------|-----------|---------|
| 5000 | DATA_NOT_FOUND | 数据未找到 | 否 | 检查 ID |
| 5001 | DATA_VALIDATION_FAILED | 数据验证失败 | 否 | 检查数据格式 |
| 5002 | DATABASE_ERROR | 数据库错误 | 是 | 重试操作 |
| 5003 | STORAGE_ERROR | 存储错误 | 是 | 重试上传 |
| 5004 | DATA_CONFLICT | 数据冲突 | 否 | 解决冲突 |

#### 业务错误 (6xxx)

| 代码 | 类型 | 说明 | 是否可重试 | 处理建议 |
|------|------|------|-----------|---------|
| 6000 | AD_ACCOUNT_NOT_BOUND | 广告账户未绑定 | 否 | 提示用户绑定账户 |
| 6001 | AD_ACCOUNT_TOKEN_EXPIRED | 广告账户令牌过期 | 否 | 提示用户重新授权 |
| 6002 | AD_ACCOUNT_INSUFFICIENT_BALANCE | 广告账户余额不足 | 否 | 提示用户充值 |
| 6003 | AD_CREATIVE_REJECTED | 素材被平台拒绝 | 否 | 提示修改素材 |
| 6004 | AD_CAMPAIGN_REVIEW_FAILED | 广告审核失败 | 否 | 提示修改广告内容 |
| 6005 | AD_PLATFORM_POLICY_VIOLATION | 违反平台政策 | 否 | 提示检查广告内容 |
| 6006 | PRODUCT_URL_INVALID | 产品链接无效 | 否 | 提示检查链接 |
| 6007 | PRODUCT_INFO_EXTRACTION_FAILED | 产品信息提取失败 | 是 | 提示手动输入 |
| 6008 | LANDING_PAGE_DOMAIN_NOT_VERIFIED | 落地页域名未验证 | 否 | 提示验证域名 |
| 6009 | SUBSCRIPTION_EXPIRED | 订阅已过期 | 否 | 提示续费 |
| 6010 | FEATURE_NOT_AVAILABLE | 功能未开放 | 否 | 提示升级套餐 |

---

### 错误处理最佳实践

#### 1. 重试策略

```python
# 指数退避重试
async def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except RetryableError as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            await asyncio.sleep(wait_time)
```

#### 2. 错误日志记录

```python
# 记录详细的错误信息
logger.error(
    "Operation failed",
    extra={
        "error_code": "4003",
        "error_type": "GENERATION_FAILED",
        "user_id": "user_123",
        "request_id": "req_123456",
        "retry_count": 2,
        "stack_trace": traceback.format_exc()
    }
)
```

#### 3. 用户友好的错误消息

```python
# 错误消息映射
ERROR_MESSAGES = {
    # Credit 相关错误
    "6011": "Credit 余额不足，请充值后继续使用",
    "6012": "扣费失败，请重试",
    "6013": "订阅已过期，请续费后继续使用",
    "6014": "超额消费已达上限，请充值后继续",

    # AI 服务错误
    "4001": "AI 服务暂时不可用，请稍后重试",
    "4003": "生成失败，请稍后重试",

    # 数据错误
    "5000": "未找到相关数据，请检查输入"
}
```

---

### 错误响应示例

#### WebSocket 错误

```json
{
  "type": "error",
  "error": {
    "code": "2000",
    "type": "CONNECTION_FAILED",
    "message": "WebSocket 连接失败",
    "details": {
      "reason": "网络超时",
      "retry_after": 5
    },
    "timestamp": "2024-11-26T10:00:15Z",
    "request_id": "req_123456"
  }
}
```

#### MCP 错误

```json
{
  "status": "error",
  "error": {
    "code": "3002",
    "type": "MCP_INVALID_PARAMETERS",
    "message": "MCP 工具参数无效",
    "details": {
      "tool_name": "create_creative",
      "missing_parameters": ["user_id", "file_url"],
      "invalid_parameters": {
        "score": "must be between 0 and 100"
      }
    },
    "timestamp": "2024-11-26T10:00:15Z",
    "request_id": "req_123456"
  }
}
```

#### Capability 错误

```json
{
  "status": "error",
  "error": {
    "code": "4003",
    "type": "GENERATION_FAILED",
    "message": "素材生成失败",
    "details": {
      "reason": "AI 模型超时",
      "retry_after": 60,
      "retry_count": 2,
      "max_retries": 3,
      "fallback_available": true
    },
    "timestamp": "2024-11-26T10:00:15Z",
    "request_id": "req_123456"
  }
}
```

#### Credit 余额不足错误

```json
{
  "status": "error",
  "error": {
    "code": "6011",
    "type": "INSUFFICIENT_CREDITS",
    "message": "Credit 余额不足，请充值后继续使用",
    "details": {
      "required_credits": 20,
      "available_credits": 5,
      "subscription_credits": 0,
      "purchased_credits": 5,
      "overage_enabled": false,
      "recharge_url": "https://aae.com/billing/recharge",
      "upgrade_url": "https://aae.com/pricing"
    },
    "timestamp": "2024-11-26T10:00:15Z",
    "request_id": "req_123456"
  }
}
```

#### Credit 扣减失败错误

```json
{
  "status": "error",
  "error": {
    "code": "6012",
    "type": "CREDIT_DEDUCTION_FAILED",
    "message": "Credit 扣减失败，操作已取消",
    "details": {
      "reason": "concurrent_modification",
      "operation_id": "op_123456",
      "retry_allowed": true
    },
    "timestamp": "2024-11-26T10:00:15Z",
    "request_id": "req_123456"
  }
}
```

#### 订阅过期错误

```json
{
  "status": "error",
  "error": {
    "code": "6013",
    "type": "SUBSCRIPTION_EXPIRED",
    "message": "订阅已过期，请续费后继续使用",
    "details": {
      "expired_at": "2024-11-25T23:59:59Z",
      "purchased_credits": 500,
      "renew_url": "https://aae.com/billing/renew"
    },
    "timestamp": "2024-11-26T10:00:15Z",
    "request_id": "req_123456"
  }
}
```

---

## 认证与授权（Authentication & Authorization）

### WebSocket 认证

```
# 连接时携带 JWT Token
wss://api.aae.com/ws/chat?token=<jwt_token>

# 或在 Headers 中
Authorization: Bearer <jwt_token>
```

### MCP 认证

```python
# Service-to-Service Token
mcp_client = MCPClient(
    server_url="http://localhost:8000/mcp",
    auth_token="<service_token>",
    service_name="unified-ai-agent"
)
```

### 权限验证

```python
# User Portal 验证用户权限
def verify_permission(user_id: str, action: str) -> bool:
    # 检查用户订阅状态
    # 检查使用限额
    # 检查功能权限
    pass
```

---

## 性能要求（Performance Requirements）

### WebSocket

- 连接建立：< 1 秒
- 消息延迟：< 100ms
- 流式响应：每 chunk < 50ms

### MCP

- 工具调用：< 500ms（简单查询）
- 工具调用：< 2 秒（复杂操作）
- 并发支持：100 个并发调用

### Capability Module

- 素材生成：< 60 秒（10 张图片）
- 报表分析：< 5 秒
- 竞品分析：< 10 秒
- 落地页生成：< 10 秒
- 广告创建：< 10 秒

---

## 版本控制（Versioning）

### API 版本

```
WebSocket: wss://api.aae.com/v1/ws/chat
MCP: http://localhost:8000/v1/mcp
Capability: /api/v1/capability/{name}
```

### 版本兼容性

- 向后兼容：保持至少 2 个版本
- 废弃通知：提前 3 个月通知
- 强制升级：仅在安全问题时

---

**文档版本**：v1.0
**最后更新**：2024-11-26
**维护者**：AAE 开发团队
