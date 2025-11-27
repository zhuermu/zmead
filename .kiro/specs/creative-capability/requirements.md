# 需求文档 - Creative Capability（素材生成能力模块）

## 简介（Introduction）

Creative Capability 是 Unified AI Agent 的核心能力模块之一，负责素材生成相关的业务逻辑。该模块被 Unified AI Agent 调用，通过 MCP 协议与 User Portal 通信进行数据存储和读取。该模块专注于素材生成、分析和评分，不负责对话管理和数据存储。

## 术语表（Glossary）

- **Creative Capability**：素材生成能力模块，Unified AI Agent 的能力之一
- **Capability Module**：能力模块，实现具体业务逻辑的功能单元
- **Creative**：素材，包括图片和视频
- **Variant**：变体，基于原始素材生成的不同版本
- **Reference Image**：参考图片，用户上传的示例素材
- **AI Vision**：AI 视觉分析，用于分析素材的构图、色彩、卖点等
- **Creative Score**：素材评分，AI 对素材质量的评估分数
- **Aspect Ratio**：宽高比，如 9:16、1:1、4:5
- **MCP**：Model Context Protocol，用于与 User Portal 通信
- **Capability API**：能力模块接口，被 Unified AI Agent 调用
- **Orchestrator**：协调器，Unified AI Agent 中负责协调能力模块的组件

---

## 模块边界（Module Boundaries）

**职责范围**：
- ✅ 素材生成业务逻辑
- ✅ AI 模型调用（图片生成、素材分析）
- ✅ 素材质量评分
- ✅ 竞品素材分析

**不负责**：
- ❌ 数据存储（通过 MCP 调用 User Portal）
- ❌ 用户认证和权限（由 User Portal 负责）
- ❌ 对话管理（由 Unified AI Agent 负责）
- ❌ 意图识别（由 Unified AI Agent 负责）

详见：[INTERFACES.md - 能力模块边界](../INTERFACES.md#3-能力模块边界)

---

## Capability API（能力模块接口）

### 接口定义

```python
class CreativeCapability:
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

详见：[INTERFACES.md - Creative Capability](../INTERFACES.md#creative-capability)

---

## MCP 工具调用（MCP Tool Invocation）

该模块通过 MCP Client 调用 User Portal 的工具：

| MCP 工具 | 用途 | 调用时机 |
|---------|------|----------|
| `create_creative` | 存储生成的素材 | 素材生成完成后 |
| `get_creatives` | 获取素材列表 | 用户查询素材时 |
| `update_creative` | 更新素材信息 | 素材评分完成后 |
| `delete_creative` | 删除素材 | 用户删除素材时 |

详见：[INTERFACES.md - MCP 协议](../INTERFACES.md#2-mcp-协议unified-ai-agent--user-portal)

---

## 需求（Requirements）

### 需求 1：产品信息提取

**用户故事**：作为 Unified AI Agent，我需要从产品链接提取信息，以便生成高质量的广告素材。

#### 验收标准

1. WHEN 调用 generate_creative action 并提供 product_url THEN Creative Capability SHALL 自动抓取产品信息
2. WHEN 产品信息抓取成功 THEN Creative Capability SHALL 提取标题、价格、图片、描述、卖点
3. WHEN 支持 Shopify 链接 THEN Creative Capability SHALL 使用 Shopify API 提取数据
4. WHEN 支持 Amazon 链接 THEN Creative Capability SHALL 使用网页解析提取数据
5. WHEN 提取失败 THEN Creative Capability SHALL 返回错误并提示用户手动输入

---

### 需求 2：素材上传

**用户故事**：作为一个用户，我想要上传参考图片，以便 AI 生成类似风格的素材。

#### 验收标准

1. WHEN 用户点击上传按钮 THEN Creative Agent SHALL 显示文件选择对话框
2. WHEN 用户选择图片文件（JPG/PNG） THEN Creative Agent SHALL 验证文件格式和大小（最大 10MB）
3. WHEN 文件验证通过 THEN Creative Agent SHALL 上传文件到 AWS S3
4. WHEN 上传完成 THEN Creative Agent SHALL 显示图片预览
5. WHEN 用户上传超过 5 张图片 THEN Creative Agent SHALL 拒绝上传并提示限制

---

### 需求 3：竞品素材分析

**用户故事**：作为一个用户，我想要分析竞品的爆款素材，以便了解成功要素。

#### 验收标准

1. WHEN 用户粘贴 TikTok 广告链接 THEN Creative Agent SHALL 提取广告素材
2. WHEN 素材提取成功 THEN Creative Agent SHALL 使用 Gemini Vision 分析构图、色彩、卖点
3. WHEN 分析完成 THEN Creative Agent SHALL 显示分析结果（构图、色彩、卖点、文案结构）
4. WHEN 分析失败 THEN Creative Agent SHALL 显示错误提示并建议手动上传
5. WHEN 用户保存分析结果 THEN Creative Agent SHALL 存储分析数据供后续使用

---

### 需求 4：图片素材生成

**用户故事**：作为一个用户，我想要生成多个图片变体，以便测试不同的广告素材。

#### 验收标准

1. WHEN 用户点击"生成素材"按钮 THEN Creative Agent SHALL 显示生成配置选项
2. WHEN 用户选择生成数量（3/10 张） THEN Creative Agent SHALL 调用 AWS Bedrock Stable Diffusion XL
3. WHEN 生成过程中 THEN Creative Agent SHALL 显示进度条和预计时间
4. WHEN 生成完成 THEN Creative Agent SHALL 显示所有生成的图片
5. WHEN 生成失败 THEN Creative Agent SHALL 自动切换到 Gemini Imagen 3 重试

---

### 需求 5：素材规格适配

**用户故事**：作为一个用户，我想要生成不同规格的素材，以便适配不同的广告平台。

#### 验收标准

1. WHEN 用户选择目标平台（TikTok/Instagram/Facebook） THEN Creative Agent SHALL 自动选择对应的宽高比
2. WHEN 用户选择 TikTok THEN Creative Agent SHALL 生成 9:16 比例的素材
3. WHEN 用户选择 Instagram Feed THEN Creative Agent SHALL 生成 1:1 比例的素材
4. WHEN 用户选择 Facebook Feed THEN Creative Agent SHALL 生成 4:5 比例的素材
5. WHEN 用户自定义宽高比 THEN Creative Agent SHALL 支持自定义尺寸输入

---

### 需求 6：素材编辑（MVP 简化）

**用户故事**：作为一个用户，我想要对生成的素材进行基本调整。

#### 验收标准

1. WHEN 用户点击素材 THEN Creative Agent SHALL 显示素材详情页
2. WHEN 用户点击下载 THEN Creative Agent SHALL 下载原始分辨率的图片
3. WHEN 用户点击删除 THEN Creative Agent SHALL 删除素材并从列表移除
4. WHEN 用户点击重新生成 THEN Creative Agent SHALL 使用相同参数重新生成
5. WHEN 用户需要编辑 THEN Creative Agent SHALL 提示使用第三方工具（Canva/Figma）

---

### 需求 7：素材评分

**用户故事**：作为一个用户，我想要看到 AI 对素材的评分，以便选择最佳素材。

#### 验收标准

1. WHEN 素材生成完成 THEN Creative Agent SHALL 使用 Gemini Vision 分析素材质量
2. WHEN 分析完成 THEN Creative Agent SHALL 显示 0-100 分的评分
3. WHEN 显示评分 THEN Creative Agent SHALL 显示评分维度（视觉冲击力、构图平衡、色彩和谐、文案清晰）
4. WHEN 用户点击评分 THEN Creative Agent SHALL 显示详细分析报告
5. WHEN 素材列表显示 THEN Creative Agent SHALL 按评分从高到低排序

---

### 需求 8：素材库管理

**用户故事**：作为一个用户，我想要管理我的素材库，以便复用和组织素材。

#### 验收标准

1. WHEN 用户访问素材库 THEN Creative Agent SHALL 显示所有已生成的素材
2. WHEN 用户搜索素材 THEN Creative Agent SHALL 支持按标签、日期、评分筛选
3. WHEN 用户选择多个素材 THEN Creative Agent SHALL 支持批量下载
4. WHEN 用户删除素材 THEN Creative Agent SHALL 要求确认并删除文件
5. WHEN 素材库超过 100 个 THEN Creative Agent SHALL 提示用户清理旧素材

---

### 需求 9：使用限额控制

**用户故事**：作为系统，我需要根据用户订阅控制素材生成次数。

#### 验收标准

1. WHEN 免费版用户生成素材 THEN Creative Agent SHALL 检查每日限额（3 次）
2. WHEN 用户达到限额 THEN Creative Agent SHALL 拒绝生成并显示升级提示
3. WHEN 付费版用户生成素材 THEN Creative Agent SHALL 允许无限制生成
4. WHEN 每日 0 点 THEN Creative Agent SHALL 重置免费版用户的每日限额
5. WHEN 用户升级订阅 THEN Creative Agent SHALL 立即解除限额

---

## 非功能性需求（Non-Functional Requirements）

### 性能需求

1. Creative Agent SHALL 在 30-60 秒内生成 10 张图片
2. Creative Agent SHALL 在 10-20 秒内完成素材分析
3. Creative Agent SHALL 支持并发生成（多个用户同时使用）

### 质量需求

1. Creative Agent SHALL 生成的图片分辨率不低于 1080x1920（9:16）
2. Creative Agent SHALL 生成的图片文件大小不超过 5MB
3. Creative Agent SHALL 确保生成的图片符合广告平台规范

### 可靠性需求

1. Creative Agent SHALL 在主模型失败时自动切换到备选模型
2. Creative Agent SHALL 在生成失败时自动重试 3 次
3. Creative Agent SHALL 记录所有生成日志供故障排查

### 成本控制

1. Creative Agent SHALL 控制单次生成成本不超过 $0.50
2. Creative Agent SHALL 缓存相似请求的结果（24 小时）
3. Creative Agent SHALL 监控 AI API 调用成本

---

## 系统边界（System Boundaries）

### 包含的功能
- 素材上传和管理
- 竞品素材分析
- 图片素材生成
- 素材规格适配
- 素材评分
- 素材库管理

### 不包含的功能
- 视频素材生成（MVP 阶段）
- 在线素材编辑器（建议使用第三方工具）
- 素材自动投放（由自动化投放引擎负责）

---

## MCP 通信需求（MCP Communication Requirements）

### 需求 10：与 User Portal 通信

**用户故事**：作为 Creative Agent，我需要通过 MCP 协议与 User Portal 通信，以便读取和写入素材数据。

#### 验收标准

1. WHEN Agent 启动 THEN Creative Agent SHALL 连接到 User Portal MCP Server
2. WHEN 用户请求素材列表 THEN Creative Agent SHALL 调用 `get_creatives` 工具
3. WHEN 生成新素材 THEN Creative Agent SHALL 调用 `create_creative` 工具存储数据
4. WHEN 更新素材 THEN Creative Agent SHALL 调用 `update_creative` 工具
5. WHEN MCP 调用失败 THEN Creative Agent SHALL 重试并通知用户

---

## 技术约束（Technical Constraints）

- AI 模型：
  - 对话理解：Gemini 2.5 Flash
  - 图片生成：AWS Bedrock Stable Diffusion XL（主）+ Gemini Imagen 3（备）
  - 素材分析：Gemini 2.5 Flash Vision
- 通信协议：MCP (Model Context Protocol) + A2A
- 数据存储：通过 User Portal API（不直接访问数据库）
- 文件存储：AWS S3（通过 User Portal）
- 图片处理：Pillow (Python)
- 对话管理：LangChain 或 LlamaIndex
- 前端：Next.js 14 + TypeScript（聊天界面）
- 后端：FastAPI (Python 3.11+)

## MCP 工具定义（MCP Tools Definition）

Creative Agent 作为 MCP Client，调用 User Portal 提供的工具：

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

Creative Agent 同时作为 MCP Server，提供工具给其他 Agent：

```json
{
  "server_tools": [
    {
      "name": "generate_creative",
      "description": "生成广告素材",
      "parameters": {
        "product_url": "string",
        "style": "string",
        "count": "integer"
      }
    },
    {
      "name": "analyze_creative",
      "description": "分析素材质量",
      "parameters": {
        "creative_id": "string"
      }
    }
  ]
}
```
