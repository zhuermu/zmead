# 需求文档 - Landing Page Capability（落地页生成能力模块）

## 简介（Introduction）

Landing Page Capability 是 Unified AI Agent 的能力模块之一，负责落地页生成和管理相关的业务逻辑。该模块被 Unified AI Agent 调用，通过 MCP 协议与 User Portal 通信进行数据存储，专注于自动生成高转化率的独立站落地页。

## 术语表（Glossary）

- **Landing Page Capability**：落地页生成能力模块
- **Landing Page**：落地页，用户点击广告后到达的页面
- **Hero Section**：首屏区域，包含标题和主图
- **CTA**：行动号召（Call To Action），如"立即购买"按钮
- **Conversion Rate**：转化率
- **Template**：模板，预设的落地页布局
- **Facebook Pixel**：Facebook 像素，用于追踪转化
- **Capability API**：能力模块接口，被 Unified AI Agent 调用
- **MCP Client**：MCP 客户端，调用 User Portal 工具

---

## 接口协议（Interface Specifications）

Landing Page Capability 的所有接口协议详见：**[INTERFACES.md](../INTERFACES.md)**

### 对外接口

1. **Capability API**：被 Unified AI Agent 调用
   - 协议定义：[INTERFACES.md - Capability Module API](../INTERFACES.md#3-capability-module-apiunified-ai-agent--能力模块)
   - 统一接口：execute(action, parameters, context)

2. **MCP Client**：调用 User Portal 工具
   - 协议定义：[INTERFACES.md - MCP 协议](../INTERFACES.md#2-mcp-协议unified-ai-agent--user-portal)
   - 工具调用：create_landing_page、get_landing_pages 等

### 模块边界

**职责范围**：
- ✅ 产品信息提取
- ✅ 落地页结构生成
- ✅ 文案优化（AI）
- ✅ 模板选择和应用
- ✅ 多语言翻译
- ✅ 落地页托管和导出
- ✅ A/B 测试管理

**不负责**：
- ❌ 数据存储（由 User Portal 负责）
- ❌ 用户认证（由 User Portal 负责）
- ❌ 对话管理（由 Unified AI Agent 负责）
- ❌ 素材生成（由 Creative Capability 负责）
- ❌ 转化数据分析（由 Reporting Capability 负责）

详见：[INTERFACES.md - 能力模块边界](../INTERFACES.md#3-能力模块边界)

---

## Capability API（能力模块接口）

### 接口定义

```python
class LandingPageCapability:
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
        pass
```

### 支持的 Actions

#### 1. parse_product - 解析产品信息

**参数**：
```json
{
  "product_url": "https://shop.com/product/123",
  "platform": "shopify"
}
```

**返回**：
```json
{
  "status": "success",
  "product_info": {
    "title": "Premium Wireless Headphones",
    "price": 79.99,
    "currency": "USD",
    "main_image": "https://...",
    "images": ["https://...", "https://..."],
    "description": "High-quality wireless headphones...",
    "features": ["Noise cancellation", "30-hour battery"],
    "reviews": [
      {"rating": 5, "text": "Amazing sound quality!"},
      {"rating": 4, "text": "Great value for money"}
    ]
  }
}
```

#### 2. generate_landing_page - 生成落地页

**参数**：
```json
{
  "product_info": {
    "title": "Premium Wireless Headphones",
    "price": 79.99,
    "main_image": "https://...",
    "description": "..."
  },
  "template": "modern",
  "language": "en",
  "pixel_id": "123456789"
}
```

**返回**：
```json
{
  "status": "success",
  "landing_page_id": "lp_123",
  "url": "https://user123.aae-pages.com/lp_123",
  "sections": {
    "hero": {
      "headline": "Experience Premium Sound Quality",
      "subheadline": "Wireless headphones with 30-hour battery",
      "image": "https://...",
      "cta_text": "Buy Now - $79.99"
    },
    "features": [
      {
        "title": "Active Noise Cancellation",
        "description": "Block out distractions...",
        "icon": "noise-cancel"
      },
      {
        "title": "30-Hour Battery Life",
        "description": "Listen all day long...",
        "icon": "battery"
      },
      {
        "title": "Premium Comfort",
        "description": "Soft ear cushions...",
        "icon": "comfort"
      }
    ],
    "reviews": [...],
    "faq": [...],
    "cta": {...}
  },
  "message": "落地页生成成功"
}
```

#### 3. optimize_copy - 优化文案

**参数**：
```json
{
  "landing_page_id": "lp_123",
  "section": "hero",
  "current_text": "Buy our headphones",
  "optimization_goal": "increase_conversion"
}
```

**返回**：
```json
{
  "status": "success",
  "optimized_text": "Experience Premium Sound - Limited Time Offer!",
  "improvements": [
    "Added emotional appeal",
    "Created urgency",
    "Highlighted value proposition"
  ],
  "confidence_score": 0.92
}
```

#### 4. update_landing_page - 更新落地页

**参数**：
```json
{
  "landing_page_id": "lp_123",
  "updates": {
    "hero.headline": "新标题",
    "hero.subheadline": "新副标题",
    "hero.image": "https://new-image.jpg",
    "theme.primary_color": "#FF6B6B",
    "theme.secondary_color": "#4ECDC4",
    "cta.text": "立即购买",
    "cta.url": "https://shop.com/checkout"
  }
}
```

**返回**：
```json
{
  "status": "success",
  "landing_page_id": "lp_123",
  "updated_fields": [
    "hero.headline",
    "hero.subheadline",
    "hero.image",
    "theme.primary_color",
    "theme.secondary_color",
    "cta.text",
    "cta.url"
  ],
  "url": "https://user123.aae-pages.com/lp_123",
  "message": "落地页已更新"
}
```

#### 5. translate_landing_page - 翻译落地页

**参数**：
```json
{
  "landing_page_id": "lp_123",
  "target_language": "es",
  "sections_to_translate": ["hero", "features", "faq"]
}
```

**返回**：
```json
{
  "status": "success",
  "translated_landing_page_id": "lp_123_es",
  "url": "https://user123.aae-pages.com/lp_123?lang=es",
  "translations": {
    "hero": {
      "headline": "Experimenta Calidad de Sonido Premium",
      "subheadline": "Auriculares inalámbricos con batería de 30 horas"
    },
    "features": [...]
  },
  "message": "翻译完成"
}
```

#### 6. create_ab_test - 创建 A/B 测试

**参数**：
```json
{
  "test_name": "Headline Test",
  "landing_page_id": "lp_123",
  "variants": [
    {
      "name": "Variant A",
      "changes": {
        "hero.headline": "Experience Premium Sound Quality"
      }
    },
    {
      "name": "Variant B",
      "changes": {
        "hero.headline": "Transform Your Listening Experience"
      }
    }
  ],
  "traffic_split": [50, 50],
  "duration_days": 7
}
```

**返回**：
```json
{
  "status": "success",
  "test_id": "test_456",
  "variant_urls": [
    "https://user123.aae-pages.com/lp_123?variant=a",
    "https://user123.aae-pages.com/lp_123?variant=b"
  ],
  "message": "A/B 测试已创建"
}
```

#### 7. analyze_ab_test - 分析 A/B 测试结果

**参数**：
```json
{
  "test_id": "test_456"
}
```

**返回**：
```json
{
  "status": "success",
  "test_id": "test_456",
  "results": [
    {
      "variant": "A",
      "visits": 1000,
      "conversions": 45,
      "conversion_rate": 4.5
    },
    {
      "variant": "B",
      "visits": 1000,
      "conversions": 62,
      "conversion_rate": 6.2
    }
  ],
  "winner": {
    "variant": "B",
    "confidence": 95,
    "improvement": "+37.8%"
  },
  "recommendation": "使用 Variant B 作为主版本"
}
```

#### 8. publish_landing_page - 发布落地页

**参数**：
```json
{
  "landing_page_id": "lp_123",
  "custom_domain": "promo.myshop.com"
}
```

**返回**：
```json
{
  "status": "success",
  "landing_page_id": "lp_123",
  "url": "https://promo.myshop.com",
  "cdn_url": "https://d123.cloudfront.net/lp_123",
  "ssl_status": "active",
  "message": "落地页已发布"
}
```

#### 9. export_landing_page - 导出落地页

**参数**：
```json
{
  "landing_page_id": "lp_123",
  "format": "html"
}
```

**返回**：
```json
{
  "status": "success",
  "download_url": "https://aae-exports.s3.amazonaws.com/lp_123.zip",
  "expires_at": "2024-11-27T10:00:00Z",
  "message": "落地页已导出"
}
```

详见：[INTERFACES.md - Landing Page Capability](../INTERFACES.md#landing-page-capability)

---

## MCP 工具调用（MCP Tool Invocation）

该模块通过 MCP Client 调用 User Portal 的以下工具：

### 1. create_landing_page - 存储落地页

```python
result = await mcp_client.call_tool(
    "create_landing_page",
    {
        "user_id": context["user_id"],
        "landing_page_data": {
            "landing_page_id": "lp_123",
            "title": "Premium Headphones",
            "url": "https://user123.aae-pages.com/lp_123",
            "template": "modern",
            "status": "published"
        }
    }
)
```

### 2. get_landing_pages - 获取落地页列表

```python
result = await mcp_client.call_tool(
    "get_landing_pages",
    {
        "user_id": context["user_id"],
        "status": "published",
        "limit": 10
    }
)
```

详见：[INTERFACES.md - MCP 协议](../INTERFACES.md#2-mcp-协议unified-ai-agent--user-portal)

---

## 需求（Requirements）

### 需求 1：自动解析产品链接

**用户故事**：作为 Unified AI Agent，我需要解析产品链接，以便提取产品信息生成落地页。

#### 验收标准

1. WHEN 调用 parse_product action THEN Landing Page Capability SHALL 提取产品信息
2. WHEN 支持 Shopify 链接 THEN Landing Page Capability SHALL 使用 Shopify API 提取数据
3. WHEN 支持 Amazon 链接 THEN Landing Page Capability SHALL 使用网页解析提取数据
4. WHEN 提取成功 THEN Landing Page Capability SHALL 返回标题、价格、图片、描述、评论
5. WHEN 提取失败 THEN Landing Page Capability SHALL 返回错误信息和建议

---

### 需求 2：自动生成落地页结构

**用户故事**：作为 Unified AI Agent，我需要生成落地页，以便为用户创建高转化率的页面。

#### 验收标准

1. WHEN 调用 generate_landing_page action THEN Landing Page Capability SHALL 选择合适的模板
2. WHEN 生成 Hero 区域 THEN Landing Page Capability SHALL 使用 AI 优化标题文案
3. WHEN 生成 Features 区域 THEN Landing Page Capability SHALL 提取 3 个核心卖点
4. WHEN 生成 Reviews 区域 THEN Landing Page Capability SHALL 展示用户评价
5. WHEN 生成完成 THEN Landing Page Capability SHALL 注入 Facebook Pixel 代码

---

### 需求 3：落地页内容更新

**用户故事**：作为 Unified AI Agent，我需要更新落地页内容，以便用户可以自定义页面。

#### 验收标准

1. WHEN 调用 update_landing_page action THEN Landing Page Capability SHALL 更新指定字段
2. WHEN 更新文本内容 THEN Landing Page Capability SHALL 保持原有格式和结构
3. WHEN 更新图片 THEN Landing Page Capability SHALL 验证图片 URL 有效性
4. WHEN 更新主题颜色 THEN Landing Page Capability SHALL 验证颜色格式（HEX）
5. WHEN 更新完成 THEN Landing Page Capability SHALL 返回更新字段列表和新 URL

---

### 需求 4：文案优化

**用户故事**：作为 Unified AI Agent，我需要优化落地页文案，以便提升转化率。

#### 验收标准

1. WHEN 调用 optimize_copy action THEN Landing Page Capability SHALL 使用 AI 模型优化文案
2. WHEN 优化标题 THEN Landing Page Capability SHALL 增强情感吸引力和紧迫感
3. WHEN 优化 CTA THEN Landing Page Capability SHALL 使用行动导向的语言
4. WHEN 优化完成 THEN Landing Page Capability SHALL 返回优化后的文案和改进说明
5. WHEN 优化失败 THEN Landing Page Capability SHALL 返回原文案

---

### 需求 5：多语言翻译

**用户故事**：作为 Unified AI Agent，我需要翻译落地页，以便服务不同地区的客户。

#### 验收标准

1. WHEN 调用 translate_landing_page action THEN Landing Page Capability SHALL 使用 AI 翻译所有文本
2. WHEN 翻译完成 THEN Landing Page Capability SHALL 保持原有的格式和结构
3. WHEN 翻译完成 THEN Landing Page Capability SHALL 生成新的语言版本 URL
4. WHEN 支持语言 THEN Landing Page Capability SHALL 支持英语、西班牙语、法语、中文
5. WHEN 翻译失败 THEN Landing Page Capability SHALL 返回错误信息

---

### 需求 6：A/B 测试

**用户故事**：作为 Unified AI Agent，我需要创建 A/B 测试，以便找到最佳落地页版本。

#### 验收标准

1. WHEN 调用 create_ab_test action THEN Landing Page Capability SHALL 创建多个变体
2. WHEN 测试开始 THEN Landing Page Capability SHALL 随机分配流量
3. WHEN 调用 analyze_ab_test action THEN Landing Page Capability SHALL 分析转化率数据
4. WHEN 分析完成 THEN Landing Page Capability SHALL 识别获胜变体（统计显著性 > 95%）
5. WHEN 测试结束 THEN Landing Page Capability SHALL 提供使用建议

---

### 需求 7：落地页托管

**用户故事**：作为 Unified AI Agent，我需要托管落地页，以便用户无需自己部署。

#### 验收标准

1. WHEN 调用 publish_landing_page action THEN Landing Page Capability SHALL 上传到 AWS S3
2. WHEN 上传完成 THEN Landing Page Capability SHALL 通过 CloudFront 分发
3. WHEN 分发完成 THEN Landing Page Capability SHALL 生成默认域名
4. WHEN 支持自定义域名 THEN Landing Page Capability SHALL 配置 CNAME 记录
5. WHEN 发布完成 THEN Landing Page Capability SHALL 启用 HTTPS

---

### 需求 8：落地页导出

**用户故事**：作为 Unified AI Agent，我需要导出落地页，以便用户自行托管。

#### 验收标准

1. WHEN 调用 export_landing_page action THEN Landing Page Capability SHALL 生成完整的 HTML 文件
2. WHEN 生成 HTML THEN Landing Page Capability SHALL 包含所有 CSS 和 JavaScript
3. WHEN 生成 HTML THEN Landing Page Capability SHALL 包含 Facebook Pixel 代码
4. WHEN 生成完成 THEN Landing Page Capability SHALL 打包为 ZIP 文件
5. WHEN 生成下载链接 THEN Landing Page Capability SHALL 设置 24 小时过期时间

---

### 需求 9：转化追踪

**用户故事**：作为系统，我需要追踪落地页转化，以便提供数据分析。

#### 数据流转架构

```
┌─────────────────────────────────────────────────────────────┐
│                    用户访问落地页                            │
└─────────────────────────────────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
┌─────────────────────┐    ┌─────────────────────┐
│   Facebook Pixel    │    │  内部分析追踪脚本   │
│   (第三方追踪)       │    │  (AAE 自有追踪)     │
└─────────────────────┘    └─────────────────────┘
              │                       │
              │                       ▼
              │           ┌─────────────────────┐
              │           │    User Portal      │
              │           │  (事件收集 API)      │
              │           │  - save_lp_event    │
              │           └─────────────────────┘
              │                       │
              │                       ▼
              │           ┌─────────────────────┐
              │           │  PostgreSQL/Redis   │
              │           │  (事件存储)          │
              │           └─────────────────────┘
              │                       │
              ▼                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Reporting Capability                            │
│   - 从 User Portal 获取 Landing Page 转化数据               │
│   - 关联广告 Campaign 数据                                   │
│   - 生成统一报表                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 验收标准

1. WHEN 用户访问落地页 THEN Landing Page SHALL 触发 PageView 事件并发送到 Facebook Pixel 和 User Portal
2. WHEN 用户点击 CTA THEN Landing Page SHALL 触发 AddToCart 事件并发送到 Facebook Pixel 和 User Portal
3. WHEN 用户完成购买 THEN Landing Page SHALL 触发 Purchase 事件并发送到 Facebook Pixel 和 User Portal
4. WHEN User Portal 收到事件 THEN User Portal SHALL 存储事件数据并关联 landing_page_id 和 campaign_id
5. WHEN Reporting Capability 生成报表 THEN Reporting Capability SHALL 从 User Portal 获取 Landing Page 转化数据进行统一分析

---

## 非功能性需求（Non-Functional Requirements）

### 性能需求

1. Landing Page Capability SHALL 在 10 秒内生成落地页
2. Landing Page Capability SHALL 确保落地页加载时间 < 2 秒
3. Landing Page Capability SHALL 优化图片大小（< 500KB）
4. Landing Page Capability SHALL 支持 5 个并发生成任务

### 质量需求

1. Landing Page Capability SHALL 确保落地页在移动端完美显示
2. Landing Page Capability SHALL 确保落地页兼容主流浏览器（Chrome/Safari/Firefox）
3. Landing Page Capability SHALL 确保落地页符合 Web 可访问性标准
4. Landing Page Capability SHALL 生成的文案准确率 > 90%

### SEO 需求

1. Landing Page Capability SHALL 自动生成 Meta 标签（title/description）
2. Landing Page Capability SHALL 自动生成 Open Graph 标签（社交分享）
3. Landing Page Capability SHALL 确保页面结构符合 SEO 最佳实践
4. Landing Page Capability SHALL 生成语义化的 HTML 结构

### 安全需求

1. Landing Page Capability SHALL 强制使用 HTTPS
2. Landing Page Capability SHALL 防止 XSS 攻击
3. Landing Page Capability SHALL 验证用户输入内容
4. Landing Page Capability SHALL 加密存储敏感配置

---

## 技术约束（Technical Constraints）

### AI 模型

- **文案优化**：Gemini 2.5 Flash
- **翻译**：Gemini 2.5 Flash
- **内容提取**：Gemini 2.5 Flash

### 技术栈

- **开发语言**：Python 3.11+
- **框架**：FastAPI
- **AI SDK**：Google AI SDK
- **MCP 通信**：MCP SDK (Python)
- **前端渲染**：React
- **托管**：AWS S3 + CloudFront
- **SSL**：AWS Certificate Manager

### 第三方服务

- **Shopify API**：产品信息提取
- **AWS S3**：落地页托管
- **AWS CloudFront**：CDN 分发
- **Facebook Pixel**：转化追踪

### 部署约束

- **容器化**：Docker
- **编排**：Kubernetes 或 Docker Compose
- **监控**：Prometheus + Grafana
- **日志**：结构化日志（JSON 格式）

---

## 实现示例（Implementation Examples）

### Capability 接口实现

```python
class LandingPageCapability:
    def __init__(self):
        self.gemini_client = GeminiClient()
        self.shopify_api = ShopifyAPI()
        self.s3_client = S3Client()
        self.cloudfront_client = CloudFrontClient()
        self.mcp_client = MCPClient()
    
    async def execute(self, action: str, parameters: dict, context: dict) -> dict:
        try:
            if action == "parse_product":
                return await self._parse_product(parameters, context)
            elif action == "generate_landing_page":
                return await self._generate_landing_page(parameters, context)
            elif action == "optimize_copy":
                return await self._optimize_copy(parameters, context)
            elif action == "translate_landing_page":
                return await self._translate_landing_page(parameters, context)
            elif action == "create_ab_test":
                return await self._create_ab_test(parameters, context)
            elif action == "analyze_ab_test":
                return await self._analyze_ab_test(parameters, context)
            elif action == "publish_landing_page":
                return await self._publish_landing_page(parameters, context)
            elif action == "export_landing_page":
                return await self._export_landing_page(parameters, context)
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Landing page capability error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _parse_product(self, parameters: dict, context: dict) -> dict:
        product_url = parameters["product_url"]
        platform = parameters.get("platform", "shopify")
        
        if platform == "shopify":
            # 使用 Shopify API 提取产品信息
            product_info = await self.shopify_api.get_product(product_url)
        else:
            # 使用网页解析
            product_info = await self._scrape_product(product_url)
        
        return {
            "status": "success",
            "product_info": product_info
        }
    
    async def _generate_landing_page(self, parameters: dict, context: dict) -> dict:
        product_info = parameters["product_info"]
        template = parameters.get("template", "modern")
        
        # 使用 AI 优化标题
        optimized_headline = await self.gemini_client.generate_content(
            f"为以下产品生成吸引人的落地页标题：{product_info['title']}"
        )
        
        # 生成落地页结构
        landing_page = {
            "landing_page_id": f"lp_{uuid.uuid4().hex[:8]}",
            "sections": {
                "hero": {
                    "headline": optimized_headline,
                    "subheadline": product_info["description"][:100],
                    "image": product_info["main_image"],
                    "cta_text": f"Buy Now - ${product_info['price']}"
                },
                "features": await self._extract_features(product_info),
                "reviews": product_info.get("reviews", [])[:3],
                "faq": await self._generate_faq(product_info),
                "cta": {
                    "text": "Get Yours Today",
                    "url": product_info.get("checkout_url", "#")
                }
            }
        }
        
        # 渲染 HTML
        html = await self._render_landing_page(landing_page, template)
        
        # 上传到 S3
        url = await self._upload_to_s3(landing_page["landing_page_id"], html)
        
        # 保存到 User Portal
        await self.mcp_client.call_tool(
            "create_landing_page",
            {
                "user_id": context["user_id"],
                "landing_page_data": {
                    "landing_page_id": landing_page["landing_page_id"],
                    "title": product_info["title"],
                    "url": url,
                    "template": template,
                    "status": "published"
                }
            }
        )
        
        return {
            "status": "success",
            "landing_page_id": landing_page["landing_page_id"],
            "url": url,
            "sections": landing_page["sections"],
            "message": "落地页生成成功"
        }
    
    async def _update_landing_page(self, parameters: dict, context: dict) -> dict:
        landing_page_id = parameters["landing_page_id"]
        updates = parameters["updates"]
        
        # 获取现有落地页数据
        landing_page = await self.mcp_client.call_tool(
            "get_landing_page",
            {
                "user_id": context["user_id"],
                "landing_page_id": landing_page_id
            }
        )
        
        # 应用更新
        updated_fields = []
        for field_path, value in updates.items():
            # 解析字段路径（如 "hero.headline"）
            parts = field_path.split(".")
            current = landing_page["sections"]
            
            # 导航到目标字段
            for part in parts[:-1]:
                current = current[part]
            
            # 更新值
            current[parts[-1]] = value
            updated_fields.append(field_path)
        
        # 重新渲染 HTML
        html = await self._render_landing_page(landing_page, landing_page["template"])
        
        # 上传到 S3
        url = await self._upload_to_s3(landing_page_id, html)
        
        # 更新 User Portal
        await self.mcp_client.call_tool(
            "update_landing_page",
            {
                "user_id": context["user_id"],
                "landing_page_id": landing_page_id,
                "updates": landing_page
            }
        )
        
        return {
            "status": "success",
            "landing_page_id": landing_page_id,
            "updated_fields": updated_fields,
            "url": url,
            "message": "落地页已更新"
        }
```

---

**文档版本**：v1.0
**最后更新**：2024-11-26
**维护者**：AAE 开发团队
