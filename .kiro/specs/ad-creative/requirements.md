# 需求文档 - Ad Creative（广告素材生成）

## 简介（Introduction）

Ad Creative 是 AI Orchestrator 的核心功能模块之一，负责素材生成相关的业务逻辑。该模块被 AI Orchestrator 调用，通过 MCP 协议与 Web Platform 通信进行数据存储和读取。该模块专注于素材生成、分析和评分，不负责对话管理和数据存储。

## 术语表（Glossary）

- **Ad Creative**：素材生成功能模块，AI Orchestrator 的能力之一
- **Functional Module**：功能模块，实现具体业务逻辑的功能单元
- **Creative**：素材，包括图片和视频
- **Variant**：变体，基于原始素材生成的不同版本
- **Reference Image**：参考图片，用户上传的示例素材
- **AI Vision**：AI 视觉分析，用于分析素材的构图、色彩、卖点等
- **Creative Score**：素材评分，AI 对素材质量的评估分数
- **Aspect Ratio**：宽高比，如 9:16、1:1、4:5
- **MCP**：Model Context Protocol，用于与 Web Platform 通信
- **Module API**：功能模块接口，被 AI Orchestrator 调用
- **Orchestrator**：协调器，AI Orchestrator 中负责协调功能模块的组件

---

## 模块边界（Module Boundaries）

**职责范围**：
- ✅ 素材生成业务逻辑
- ✅ AI 模型调用（图片生成、素材分析）
- ✅ 素材质量评分
- ✅ 竞品素材分析

**不负责**：
- ❌ 数据存储（通过 MCP 调用 Web Platform）
- ❌ 用户认证和权限（由 Web Platform 负责）
- ❌ 对话管理（由 AI Orchestrator 负责）
- ❌ 意图识别（由 AI Orchestrator 负责）

详见：[INTERFACES.md - 功能模块边界](../INTERFACES.md#3-功能模块边界)

---

## Module API（功能模块接口）

### 接口定义

```python
class AdCreative:
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
            context: 上下文信息（user_id、session_id等）
        
        Returns:
            操作结果
        """
        pass
```

### 支持的 Actions

| Action | 描述 | 参数 | 返回值 |
|--------|------|------|--------|
| `generate_creative` | 生成素材 | product_url, count, style | creative_ids, message |
| `analyze_creative` | 分析素材 | creative_id 或 image_url | insights, recommendations |
| `score_creative` | 评分素材 | creative_id | score, dimensions |
| `generate_variants` | 生成变体 | creative_id, count | variant_ids |

详见：[INTERFACES.md - Ad Creative](../INTERFACES.md#creative-capability)

---

## MCP 工具调用（MCP Tool Invocation）

该模块通过 MCP Client 调用 Web Platform 的工具：

| MCP 工具 | 用途 | 调用时机 |
|---------|------|----------|
| `get_upload_url` | 获取 S3 预签名上传 URL | 素材生成后上传文件前 |
| `create_creative` | 存储生成的素材 | 素材文件上传完成后 |
| `get_creatives` | 获取素材列表 | 用户查询素材时 |
| `update_creative` | 更新素材信息 | 素材评分完成后 |
| `delete_creative` | 删除素材 | 用户删除素材时 |

### 素材文件上传流程

```
┌─────────────────────────────────────────────────────────────┐
│              素材文件上传流程（推荐方案）                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Ad Creative 生成素材（AI 模型）                  │
│     - 调用 Gemini Imagen 3 生成图片                         │
│     - 获得图片二进制数据                                     │
│                                                             │
│  2. 获取预签名上传 URL                                       │
│     - 调用 MCP: get_upload_url()                           │
│     - 参数：user_id, file_name, file_type, file_size       │
│     - 返回：upload_url（预签名 URL）, file_url（CDN URL）   │
│                                                             │
│  3. 上传文件到 S3                                            │
│     - 使用 HTTP PUT 请求上传到 upload_url                   │
│     - 无需 AWS 凭证（预签名 URL 已包含权限）                │
│     - 上传超时：60 秒                                        │
│                                                             │
│  4. 存储素材元数据                                           │
│     - 调用 MCP: create_creative()                          │
│     - 参数：user_id, file_url（CDN URL）, metadata         │
│     - 返回：creative_id, url, created_at                   │
│                                                             │
│  5. 返回结果给 AI Orchestrator                             │
│     - 返回 creative_id 和 CDN URL                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

详见：[INTERFACES.md - MCP 协议](../INTERFACES.md#2-mcp-协议unified-ai-agent--user-portal)

---

## 需求（Requirements）

### 需求 1：产品信息提取

**用户故事**：作为 AI Orchestrator，我需要从产品链接提取信息，以便生成高质量的广告素材。

#### 验收标准

1. WHEN 调用 generate_creative action 并提供 product_url THEN Ad Creative SHALL 自动抓取产品信息
2. WHEN 产品信息抓取成功 THEN Ad Creative SHALL 提取标题、价格、图片、描述、卖点
3. WHEN 支持 Shopify 链接 THEN Ad Creative SHALL 使用 Shopify API 提取数据
4. WHEN 支持 Amazon 链接 THEN Ad Creative SHALL 使用网页解析提取数据
5. WHEN 提取失败 THEN Ad Creative SHALL 返回错误并提示用户手动输入

---

### 需求 2：素材上传

**用户故事**：作为一个用户，我想要上传参考图片，以便 AI 生成类似风格的素材。

#### 验收标准

1. WHEN 用户点击上传按钮 THEN Ad Creative SHALL 显示文件选择对话框
2. WHEN 用户选择图片文件（JPG/PNG） THEN Ad Creative SHALL 验证文件格式和大小（最大 10MB）
3. WHEN 文件验证通过 THEN Ad Creative SHALL 上传文件到 AWS S3
4. WHEN 上传完成 THEN Ad Creative SHALL 显示图片预览
5. WHEN 用户上传超过 5 张图片 THEN Ad Creative SHALL 拒绝上传并提示限制

---

### 需求 3：竞品素材分析

**用户故事**：作为一个用户，我想要分析竞品的爆款素材，以便了解成功要素。

#### 验收标准

1. WHEN 用户粘贴 TikTok 广告链接 THEN Ad Creative SHALL 提取广告素材
2. WHEN 素材提取成功 THEN Ad Creative SHALL 使用 Gemini 2.5 Flash 分析构图、色彩、卖点
3. WHEN 分析完成 THEN Ad Creative SHALL 显示分析结果（构图、色彩、卖点、文案结构）
4. WHEN 分析失败 THEN Ad Creative SHALL 显示错误提示并建议手动上传
5. WHEN 用户保存分析结果 THEN Ad Creative SHALL 存储分析数据供后续使用

---

### 需求 4：图片素材生成

**用户故事**：作为一个用户，我想要生成多个图片变体，以便测试不同的广告素材。

#### 验收标准

1. WHEN 用户点击"生成素材"按钮 THEN Ad Creative SHALL 显示生成配置选项
2. WHEN 用户选择生成数量（3/10 张） THEN Ad Creative SHALL 调用 Gemini Imagen 3
3. WHEN 生成过程中 THEN Ad Creative SHALL 显示进度条和预计时间
4. WHEN 生成完成 THEN Ad Creative SHALL 显示所有生成的图片
5. WHEN 生成失败 THEN Ad Creative SHALL 自动重试最多 3 次

---

### 需求 4.1：素材文件上传

**用户故事**：作为 Ad Creative，我需要将生成的素材文件上传到 S3，以便用户访问和使用。

#### 验收标准

1. WHEN 素材生成完成 THEN Ad Creative SHALL 调用 MCP 工具 get_upload_url 获取预签名 URL
2. WHEN 获取预签名 URL THEN Ad Creative SHALL 使用 HTTP PUT 上传文件到 S3
3. WHEN 文件上传成功 THEN Ad Creative SHALL 调用 MCP 工具 create_creative 存储元数据
4. WHEN 文件上传失败 THEN Ad Creative SHALL 重试最多 3 次
5. WHEN 重试失败 THEN Ad Creative SHALL 返回错误码 5003（STORAGE_ERROR）并通知用户

---

### 需求 5：素材规格适配

**用户故事**：作为一个用户，我想要生成不同规格的素材，以便适配不同的广告平台。

#### 验收标准

1. WHEN 用户选择目标平台（TikTok/Instagram/Facebook） THEN Ad Creative SHALL 自动选择对应的宽高比
2. WHEN 用户选择 TikTok THEN Ad Creative SHALL 生成 9:16 比例的素材
3. WHEN 用户选择 Instagram Feed THEN Ad Creative SHALL 生成 1:1 比例的素材
4. WHEN 用户选择 Facebook Feed THEN Ad Creative SHALL 生成 4:5 比例的素材
5. WHEN 用户自定义宽高比 THEN Ad Creative SHALL 支持自定义尺寸输入

---

### 需求 6：素材编辑（MVP 简化）

**用户故事**：作为一个用户，我想要对生成的素材进行基本调整。

#### 验收标准

1. WHEN 用户点击素材 THEN Ad Creative SHALL 显示素材详情页
2. WHEN 用户点击下载 THEN Ad Creative SHALL 下载原始分辨率的图片
3. WHEN 用户点击删除 THEN Ad Creative SHALL 删除素材并从列表移除
4. WHEN 用户点击重新生成 THEN Ad Creative SHALL 使用相同参数重新生成
5. WHEN 用户需要编辑 THEN Ad Creative SHALL 提示使用第三方工具（Canva/Figma）

---

### 需求 7：素材评分

**用户故事**：作为一个用户，我想要看到 AI 对素材的评分，以便选择最佳素材。

#### 评分机制说明

素材评分采用 **AI 多维度评估 + 加权计算** 的方式：

```
总分 = 视觉冲击力 × 0.3 + 构图平衡 × 0.25 + 色彩和谐 × 0.25 + 文案清晰 × 0.2

评分流程：
1. 调用 Gemini 2.5 Flash 分析素材
2. AI 输出各维度分数（0-100）和分析说明
3. 系统计算加权总分
4. 存储评分结果到 Web Platform
```

**评分维度定义：**

| 维度 | 权重 | 评估标准 |
|------|------|---------|
| 视觉冲击力 | 30% | 画面是否吸引眼球、主体是否突出 |
| 构图平衡 | 25% | 元素布局是否合理、视觉重心是否稳定 |
| 色彩和谐 | 25% | 配色是否协调、对比度是否适中 |
| 文案清晰 | 20% | 文字是否可读、信息是否清晰（无文字则默认满分） |

#### 验收标准

1. WHEN 素材生成完成 THEN Ad Creative SHALL 使用 Gemini 2.5 Flash 分析素材质量
2. WHEN 分析完成 THEN Ad Creative SHALL 显示 0-100 分的加权总分
3. WHEN 显示评分 THEN Ad Creative SHALL 显示各评分维度及其分数
4. WHEN 用户点击评分 THEN Ad Creative SHALL 显示详细分析报告（含 AI 分析说明）
5. WHEN 素材列表显示 THEN Ad Creative SHALL 按评分从高到低排序

---

### 需求 8：素材库管理

**用户故事**：作为一个用户，我想要管理我的素材库，以便复用和组织素材。

#### 验收标准

1. WHEN 用户访问素材库 THEN Ad Creative SHALL 显示所有已生成的素材
2. WHEN 用户搜索素材 THEN Ad Creative SHALL 支持按标签、日期、评分筛选
3. WHEN 用户选择多个素材 THEN Ad Creative SHALL 支持批量下载
4. WHEN 用户删除素材 THEN Ad Creative SHALL 要求确认并删除文件
5. WHEN 素材库超过 100 个 THEN Ad Creative SHALL 提示用户清理旧素材

---

### 需求 9：Credit 余额控制

**用户故事**：作为系统，我需要根据用户 Credit 余额控制素材生成。

#### 验收标准

1. WHEN 用户请求生成素材 THEN Ad Creative SHALL 检查 Credit 余额是否足够
2. WHEN Credit 余额不足 THEN Ad Creative SHALL 返回错误码 6011 并提示充值
3. WHEN Credit 余额充足 THEN Ad Creative SHALL 执行生成并扣减 Credit
4. WHEN 生成失败 THEN Ad Creative SHALL 退还已扣减的 Credit
5. WHEN 批量生成（10张以上） THEN Ad Creative SHALL 享受 8 折优惠（0.4 credits/张）

---

## 非功能性需求（Non-Functional Requirements）

### 性能需求

1. Ad Creative SHALL 在 30-60 秒内生成 10 张图片
2. Ad Creative SHALL 在 10-20 秒内完成素材分析
3. Ad Creative SHALL 支持并发生成（多个用户同时使用）

### 质量需求

1. Ad Creative SHALL 生成的图片分辨率不低于 1080x1920（9:16）
2. Ad Creative SHALL 生成的图片文件大小不超过 5MB
3. Ad Creative SHALL 确保生成的图片符合广告平台规范

### 可靠性需求

1. Ad Creative SHALL 在主模型失败时自动切换到备选模型
2. Ad Creative SHALL 在生成失败时自动重试 3 次
3. Ad Creative SHALL 记录所有生成日志供故障排查

### 成本控制

1. Ad Creative SHALL 控制单次生成成本不超过 $0.50
2. Ad Creative SHALL 缓存相似请求的结果（24 小时）
3. Ad Creative SHALL 监控 AI API 调用成本

---

## 系统边界（System Boundaries）

### 包含的功能（MVP 阶段）
- 素材上传和管理
- 竞品素材分析
- 图片素材生成（Gemini Imagen 3）
- 素材规格适配（9:16、1:1、4:5）
- 素材评分（AI 多维度评估）
- 素材库管理

### MVP 阶段明确不支持的功能

| 功能 | 计划版本 | 替代方案 |
|------|---------|---------|
| 视频素材生成 | V2.0（第 9-10 周） | 用户可上传视频或使用第三方工具 |
| 在线素材编辑器 | V2.0（第 11-12 周） | 建议使用 Canva/Figma 编辑后重新上传 |
| 素材自动投放 | 由 Campaign Automation 负责 | 用户通过 AI Agent 对话创建广告 |
| 批量素材处理 | V1.5（第 9-10 周） | MVP 单次最多生成 10 张 |
| 素材版本管理 | V2.0（第 11-12 周） | MVP 不支持版本历史 |

**注意**：虽然 Credit 计费中列出了视频生成定价（5 credits/个），但 MVP 阶段不实现此功能。该定价为后续版本预留。

---

## MCP 通信需求（MCP Communication Requirements）

### 需求 10：与 Web Platform 通信

**用户故事**：作为 Ad Creative，我需要通过 MCP 协议与 Web Platform 通信，以便读取和写入素材数据。

#### 验收标准

1. WHEN Agent 启动 THEN Ad Creative SHALL 连接到 Web Platform MCP Server
2. WHEN 用户请求素材列表 THEN Ad Creative SHALL 调用 `get_creatives` 工具
3. WHEN 生成新素材 THEN Ad Creative SHALL 调用 `create_creative` 工具存储数据
4. WHEN 更新素材 THEN Ad Creative SHALL 调用 `update_creative` 工具
5. WHEN MCP 调用失败 THEN Ad Creative SHALL 重试并通知用户

---

## 技术约束（Technical Constraints）

- AI 模型：
  - 图片生成：Gemini Imagen 3
  - 视频生成：Gemini Veo 3.1（MVP 阶段暂不实现）
  - 素材分析：Gemini 2.5 Flash（图片/视频理解）
  - MCP 调用：Gemini 2.5 Pro
- 通信协议：MCP (Model Context Protocol) + A2A
- 数据存储：通过 Web Platform API（不直接访问数据库）
- 文件存储：AWS S3（通过 Web Platform）
- 图片处理：Pillow (Python)
- 对话管理：LangChain 或 LlamaIndex
- 前端：Next.js 14 + TypeScript（聊天界面）
- 后端：FastAPI (Python 3.11+)

## MCP 工具定义（MCP Tools Definition）

Ad Creative 作为 MCP Client，调用 Web Platform 提供的工具：

```json
{
  "client_tools": [
    {
      "name": "get_creatives",
      "description": "获取用户的素材列表",
      "parameters": {
        "user_id": "string",
        "filters": "object"
      }
    },
    {
      "name": "create_creative",
      "description": "创建新素材",
      "parameters": {
        "user_id": "string",
        "creative_data": "object",
        "file_url": "string"
      }
    },
    {
      "name": "update_creative",
      "description": "更新素材信息",
      "parameters": {
        "creative_id": "string",
        "updates": "object"
      }
    }
  ]
}
```

**注意**：Ad Creative 不作为 MCP Server，所有功能模块的数据存储和访问都通过 Web Platform 的 MCP Server 统一管理。AI Orchestrator 通过 Module API 直接调用 Ad Creative 的功能。
