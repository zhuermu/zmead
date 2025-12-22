# AAE (Automated Ad Engine)

自动化广告引擎 - 带AI助手的广告SaaS平台

## 项目概述

AAE是一个现代化的广告管理平台，集成了AI助手来帮助用户管理跨平台广告活动（Meta、TikTok、Google Ads）。用户通过统一的对话界面与AI交互，完成素材生成、市场洞察、性能分析、落地页创建和广告投放自动化等任务。

## 快速开始

详细的开发指南请查看 [CLAUDE.md](./CLAUDE.md)

### 本地开发启动

```bash
# 1. 启动基础设施（推荐）
docker-compose up -d mysql redis

# 2. 启动后端服务（新终端）
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# 3. 启动AI编排器（新终端）
cd ai-orchestrator && source venv/bin/activate && uvicorn app.main:app --reload --port 8001

# 4. 启动前端（新终端）
cd frontend && npm run dev
```

访问: http://localhost:3000

## 核心功能

### ✨ 多模态AI对话
- 支持图片、视频、文档上传和AI理解
- 实时流式响应
- ReAct模式思考过程展示
- 会话历史管理

### 🎨 广告创意生成
- AI驱动的图片生成（Gemini Imagen 3）
- 视频生成（Gemini Veo 3.1）
- 多语言支持

### 📊 智能分析
- 市场洞察和竞品分析
- 广告性能报告
- 异常检测

### 🚀 广告自动化
- 跨平台广告投放
- 预算优化
- 落地页生成

## 技术栈

### 前端
- **框架**: Next.js 14 (App Router)
- **UI**: React 18, Tailwind CSS
- **状态管理**: Zustand, React Query
- **AI集成**: Vercel AI SDK
- **类型安全**: TypeScript

### 后端
- **API**: FastAPI (Python 3.12+)
- **MCP Server**: Model Context Protocol
- **数据库**: MySQL 8.4 + Redis 7.x
- **存储**: Amazon S3 + CloudFront CDN
- **异步任务**: Celery

### AI编排
- **框架**: Strands Agents (多模型支持)
- **LLM**: AWS Bedrock (Claude 4.5 Sonnet, Qwen3 235B, Nova 2 Lite) + Gemini fallback
- **Web搜索**: 统一工具，自动降级 (Amazon Nova Search → Google Grounding)
- **图片生成**: Qwen-Image (AWS SageMaker) + Bedrock Stable Diffusion
- **视频生成**: Wan2.2 (AWS SageMaker)
- **存储**: AWS S3 + 预签名URL (1小时有效期)
- **流式响应**: SSE实时传输，无缓冲

## 项目结构

```
zmead/
├── backend/                 # Web平台后端 (FastAPI)
│   ├── app/
│   │   ├── api/            # REST API端点
│   │   ├── mcp/            # MCP服务器实现
│   │   ├── models/         # 数据库模型
│   │   ├── services/       # 业务逻辑
│   │   └── tasks/          # Celery异步任务
│   └── alembic/            # 数据库迁移
├── ai-orchestrator/         # AI代理服务 (Strands Agents)
│   ├── app/
│   │   ├── core/           # Strands Agent核心
│   │   ├── tools/          # 统一工具 (web_search等)
│   │   ├── modules/        # 业务逻辑实现
│   │   ├── prompts/        # LLM提示词
│   │   └── services/       # 模型提供商 (Bedrock, Gemini)
│   └── tests/
├── frontend/                # Web界面 (Next.js)
│   └── src/
│       ├── app/            # 页面路由
│       ├── components/     # React组件
│       ├── hooks/          # 自定义Hooks
│       └── lib/            # 工具和API客户端
└── .kiro/specs/            # 需求和架构文档
```

## 环境配置

### Backend (.env)
```bash
# 数据库
DATABASE_URL=mysql+aiomysql://aae_user:aae_password@localhost:3306/aae_platform
REDIS_URL=redis://localhost:6379/0

# 安全
SECRET_KEY=your-secret-key-here
WEB_PLATFORM_SERVICE_TOKEN=your-service-token

# AWS配置
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# S3存储桶
S3_BUCKET_CREATIVES=aae-creatives
S3_BUCKET_LANDING_PAGES=aae-landing-pages
S3_BUCKET_EXPORTS=aae-exports
S3_BUCKET_UPLOADS=aae-user-uploads
CLOUDFRONT_DOMAIN=your-cloudfront-domain.cloudfront.net

# 存储提供商 (s3 或 gcs)
STORAGE_PROVIDER=s3
```

### AI Orchestrator (.env)
```bash
# AI模型配置
DEFAULT_MODEL_PROVIDER=bedrock  # gemini 或 bedrock
GEMINI_API_KEY=your-gemini-api-key  # 如果使用Gemini

# AWS配置
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Bedrock模型
BEDROCK_MODEL_CLAUDE=anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_MODEL_QWEN=qwen.qwen3-235b-a22b-2507-v1:0
BEDROCK_MODEL_NOVA=us.amazon.nova-lite-v1:0

# SageMaker端点
SAGEMAKER_ENDPOINT_QWEN_IMAGE=qwen-image-endpoint
SAGEMAKER_ENDPOINT_WAN_VIDEO=wan-video-endpoint

# 服务配置
WEB_PLATFORM_URL=http://localhost:8000
WEB_PLATFORM_SERVICE_TOKEN=same-as-backend-token
REDIS_URL=redis://localhost:6379/0
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**重要**: 
- `WEB_PLATFORM_SERVICE_TOKEN` 必须在backend和ai-orchestrator中保持一致
- AWS凭证可以通过环境变量或IAM角色提供
- 详细的AWS配置指南请参见 [AWS_DEPLOYMENT_GUIDE.md](./AWS_DEPLOYMENT_GUIDE.md)

## 最近更新

### 2025-12-19: 统一Web搜索和流式优化 ✅

**核心功能增强**:
- ✅ 统一`web_search`工具，自动降级 (Amazon Nova Search → Google Grounding)
- ✅ S3预签名URL支持，图片/视频安全访问（1小时有效期）
- ✅ 实时流式响应，移除文本缓冲，真实传输模型输出
- ✅ 前端工具名称映射，用户友好的中文显示（如"互联网搜索"）

**技术实现**:
- ✅ `NovaSearchTool`: Amazon Bedrock Converse API + nova_grounding
- ✅ `WebSearchTool`: 自动降级逻辑，透明切换搜索提供商
- ✅ S3Client: 预签名URL生成方法（1小时过期）
- ✅ Strands Agent: 直接转发delta.text，无缓冲
- ✅ Frontend: AgentProcessingCard工具名称映射

**详细文档**:
- [统一Web搜索实现](./ai-orchestrator/WEB_SEARCH_UNIFIED.md)
- [Nova Search实现详情](./ai-orchestrator/NOVA_SEARCH_IMPLEMENTATION.md)

### 2025-12-18: AWS集成完成 ✅

完成了从Google Cloud到AWS的全面迁移：

**基础设施迁移**:
- ✅ S3存储替代GCS（支持CloudFront CDN）
- ✅ AWS Bedrock多模型支持（Claude 4.5 Sonnet, Qwen3, Nova 2 Lite）
- ✅ SageMaker自定义模型部署（Qwen-Image, Wan2.2）
- ✅ Strands Agents框架替代LangGraph

**用户功能**:
- ✅ 用户可选择AI模型提供商（Gemini或Bedrock）
- ✅ 模型偏好设置界面
- ✅ 多提供商积分扣除支持
- ✅ 完整的AWS服务集成测试

**部署配置**:
- ✅ Docker配置更新
- ✅ AWS凭证管理
- ✅ 部署脚本和验证工具
- ✅ 完整的文档和故障排查指南

**详细文档**:
- [AWS部署指南](./AWS_DEPLOYMENT_GUIDE.md)
- [AWS配置摘要](./AWS_MIGRATION_CONFIGURATION_SUMMARY.md)
- [集成测试摘要](./TASK_12_INTEGRATION_TESTS_SUMMARY.md)

### 2025-12-04: 多模态文件上传功能完成 ✅

实现了完整的文件上传功能，支持图片、视频和文档：

**功能特性**:
- ✅ 直接上传到S3（使用预签名URL）
- ✅ 实时上传进度显示
- ✅ 图片/视频预览
- ✅ 多文件上传支持
- ✅ 拖拽上传
- ✅ 文件大小和类型验证
- ✅ 与AI模型集成

**支持的文件类型**:
- 图片: PNG, JPEG, WebP, HEIC (最大20MB)
- 视频: MP4, MOV, WebM (最大200MB)
- 文档: PDF, TXT, HTML, CSS等 (最大50MB)

## 开发指南

### 数据库迁移
```bash
cd backend
alembic upgrade head                           # 应用迁移
alembic revision --autogenerate -m "message"   # 创建迁移
```

### 运行测试
```bash
# Backend测试
cd backend && pytest

# AI Orchestrator测试
cd ai-orchestrator && pytest

# Frontend测试
cd frontend && npm run test
```

### 代码质量
```bash
# Python (Backend & AI Orchestrator)
ruff check .        # 检查代码问题
ruff format .       # 格式化代码
mypy app/           # 类型检查

# JavaScript (Frontend)
npm run lint        # ESLint检查
```

## MCP工具参考

核心MCP工具（在`INTERFACES.md`中定义）:

| 工具 | 分类 | 用途 |
|------|------|------|
| `check_credit` / `deduct_credit` | 计费 | 积分管理 |
| `create_creative` | 创意 | 存储生成的素材 |
| `create_campaign` | 广告引擎 | 创建广告活动 |
| `get_reports` | 报告 | 获取广告性能数据 |

## 架构文档

完整的架构和需求文档位于 `.kiro/specs/`:

- **ARCHITECTURE.md** - 系统架构概览
- **INTERFACES.md** - API和协议规范
- **web-platform/requirements.md** - Web平台需求
- **ai-orchestrator/requirements.md** - AI编排器实现
- 各模块需求文档（ad-creative, market-insights等）

## AWS S3 + CloudFront 配置指南

本节介绍如何创建 S3 存储桶并配置 CloudFront CDN 分发。

### 1. 创建 S3 存储桶

```bash
# 创建存储桶（以 aae-landing-pages 为例）
aws s3api create-bucket \
  --bucket <bucket-name> \
  --region us-east-1

# 如果是非 us-east-1 区域，需要指定 LocationConstraint
aws s3api create-bucket \
  --bucket <bucket-name> \
  --region <region> \
  --create-bucket-configuration LocationConstraint=<region>
```

### 2. 配置 S3 CORS

创建 `cors.json` 文件：

```json
{
  "CORSRules": [
    {
      "AllowedOrigins": ["http://localhost:3000", "https://*.zmead.com"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
      "AllowedHeaders": ["*"],
      "ExposeHeaders": ["ETag", "Content-Length", "Content-Type"],
      "MaxAgeSeconds": 3600
    }
  ]
}
```

应用 CORS 配置：

```bash
aws s3api put-bucket-cors \
  --bucket <bucket-name> \
  --cors-configuration file://cors.json
```

### 3. 创建 ACM SSL 证书（如果没有）

```bash
# 在 us-east-1 区域创建证书（CloudFront 要求）
aws acm request-certificate \
  --domain-name "*.zmead.com" \
  --subject-alternative-names "zmead.com" \
  --validation-method DNS \
  --region us-east-1

# 获取证书 ARN 后，按提示完成 DNS 验证
```

### 4. 创建 CloudFront Origin Access Control (OAC)

```bash
aws cloudfront create-origin-access-control \
  --origin-access-control-config '{
    "Name": "<bucket-name>-oac",
    "Description": "OAC for <bucket-name>",
    "SigningProtocol": "sigv4",
    "SigningBehavior": "always",
    "OriginAccessControlOriginType": "s3"
  }'

# 记录返回的 OAC ID（如 E2XIA6TY1Q8XE0）
```

### 5. 创建 CloudFront 分发

创建 `cloudfront-config.json`：

```json
{
  "CallerReference": "<unique-reference>",
  "Aliases": {
    "Quantity": 1,
    "Items": ["<your-domain.zmead.com>"]
  },
  "DefaultRootObject": "index.html",
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "<bucket-name>-s3",
        "DomainName": "<bucket-name>.s3.us-east-1.amazonaws.com",
        "OriginAccessControlId": "<OAC-ID>",
        "S3OriginConfig": {
          "OriginAccessIdentity": ""
        }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "<bucket-name>-s3",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"],
      "CachedMethods": {
        "Quantity": 2,
        "Items": ["GET", "HEAD"]
      }
    },
    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
    "Compress": true
  },
  "Comment": "CDN for <bucket-name>",
  "Enabled": true,
  "PriceClass": "PriceClass_100",
  "ViewerCertificate": {
    "ACMCertificateArn": "<your-acm-certificate-arn>",
    "SSLSupportMethod": "sni-only",
    "MinimumProtocolVersion": "TLSv1.2_2021"
  }
}
```

创建分发：

```bash
aws cloudfront create-distribution \
  --distribution-config file://cloudfront-config.json

# 记录返回的 Distribution ID 和 DomainName（如 d3s362bp9ghetp.cloudfront.net）
```

### 6. 配置 S3 存储桶策略

创建 `bucket-policy.json`：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontServicePrincipal",
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudfront.amazonaws.com"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::<bucket-name>/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::<account-id>:distribution/<distribution-id>"
        }
      }
    }
  ]
}
```

应用策略：

```bash
aws s3api put-bucket-policy \
  --bucket <bucket-name> \
  --policy file://bucket-policy.json
```

### 7. 配置 DNS

在你的 DNS 提供商添加 CNAME 记录：

```
<your-domain.zmead.com>  →  <distribution-id>.cloudfront.net
```

### 8. 验证配置

```bash
# 检查 CloudFront 分发状态
aws cloudfront get-distribution --id <distribution-id> --query 'Distribution.Status'

# 状态变为 "Deployed" 后即可访问
curl -I https://<your-domain.zmead.com>/
```

### 当前已配置的域名

| 域名 | S3 存储桶 | CloudFront ID | 用途 |
|------|-----------|---------------|------|
| landing.zmead.com | aae-landing-pages | EG1ZSKV9LEAHJ | 落地页托管 |

## 故障排查

### Backend无法启动
```bash
# 检查MySQL是否运行
docker-compose ps mysql
# 测试数据库连接
mysql -h 127.0.0.1 -u aae_user -paae_password aae_platform
```

### AI Orchestrator连接错误
```bash
# 验证服务令牌匹配
grep WEB_PLATFORM_SERVICE_TOKEN backend/.env
grep WEB_PLATFORM_SERVICE_TOKEN ai-orchestrator/.env
```

### Frontend无法连接后端
```bash
# 检查API URL配置
# 本地开发应为: http://localhost:8000
cat frontend/.env.local
```

## 常见问题

### Q: 图片上传后不显示
**A**: 检查 `next.config.mjs` 是否配置了 `storage.googleapis.com` 域名

### Q: AI说看不到图片
**A**: 检查后端日志，确认Gemini File API上传成功；验证请求格式是 `attachments` 而非 `tempAttachments`

### Q: 上传一直显示加载中
**A**: 检查GCS credentials配置、文件大小是否超限、查看后端日志

## 贡献指南

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 许可证

[待定]

## 联系方式

- 项目维护: [待定]
- Issue: [GitHub Issues](https://github.com/your-repo/issues)
- 文档: 查看 [CLAUDE.md](./CLAUDE.md) 获取详细开发指南

---

**注意**: 本项目使用 `CLAUDE.md` 作为AI辅助开发的指导文档。开发时请确保Claude Code能够访问该文件以获得最佳开发体验。
