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
- **存储**: Google Cloud Storage
- **异步任务**: Celery

### AI编排
- **框架**: LangGraph
- **LLM**: Gemini 2.5 Flash/Pro
- **图片生成**: Gemini Imagen 3
- **视频生成**: Gemini Veo 3.1
- **模式**: ReAct (Reasoning + Acting)

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
├── ai-orchestrator/         # AI代理服务 (LangGraph)
│   ├── app/
│   │   ├── nodes/          # LangGraph节点
│   │   ├── modules/        # 能力模块
│   │   ├── prompts/        # LLM提示词
│   │   └── services/       # MCP客户端, Gemini客户端
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

# Google Cloud Storage
GCS_PROJECT_ID=your-project-id
GCS_CREDENTIALS_PATH=/path/to/credentials.json
GEMINI_API_KEY=your-gemini-api-key

# GCS存储桶
# aae-user-uploads-temp (临时存储, 48h生命周期)
# aae-user-uploads (永久存储)
```

### AI Orchestrator (.env)
```bash
GEMINI_API_KEY=your-gemini-api-key
WEB_PLATFORM_URL=http://localhost:8000
WEB_PLATFORM_SERVICE_TOKEN=same-as-backend-token
REDIS_URL=redis://localhost:6379/0
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**重要**: `WEB_PLATFORM_SERVICE_TOKEN` 必须在backend和ai-orchestrator中保持一致。

## 最近更新

### 2025-12-04: 多模态文件上传功能完成 ✅

实现了完整的文件上传功能，支持图片、视频和文档：

**功能特性**:
- ✅ 直接上传到GCS（使用预签名URL）
- ✅ 实时上传进度显示
- ✅ 图片/视频预览
- ✅ 多文件上传支持
- ✅ 拖拽上传
- ✅ 文件大小和类型验证
- ✅ 与Gemini File API集成

**支持的文件类型**:
- 图片: PNG, JPEG, WebP, HEIC (最大20MB)
- 视频: MP4, MOV, WebM (最大200MB)
- 文档: PDF, TXT, HTML, CSS等 (最大50MB)

**Bug修复记录**: 详见 [TEST_RESULTS_2025-12-04.md](./TEST_RESULTS_2025-12-04.md)

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
