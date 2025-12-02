# AI Agent E2E Testing Guide

## 实际 API 架构

根据后端 API 文档 (http://localhost:8000/docs)，当前的聊天架构如下：

### 后端 API
- **端点**: `POST /api/v1/chat`
- **协议**: SSE (Server-Sent Events)
- **请求格式**:
```json
{
  "messages": [
    {
      "role": "user|assistant|system",
      "content": "string"
    }
  ]
}
```
- **响应**: `text/event-stream` 流式响应
- **认证**: Bearer Token (JWT)

### 前端配置
- **Hook**: `useChat` in `frontend/src/hooks/useChat.ts`
- **API URL**: `/api/v1/chat` (已更新)
- **组件**: `ChatDrawer` in `frontend/src/components/chat/ChatDrawer.tsx`

### AI Orchestrator
- **内部端点**: `POST /api/v1/chat` (AI Orchestrator 服务)
- **架构**: ReAct Agent
- **工具**: MCP Tools (通过 backend MCP server)

## Playwright 测试策略

### 1. 基础连接测试

```typescript
test('should connect to chat and send message', async ({ page }) => {
  // 访问 dashboard
  await page.goto('http://localhost:3000/dashboard');
  
  // 打开聊天
  await page.click('button:has-text("AI 助手")');
  
  // 等待聊天窗口
  await page.waitForSelector('[data-testid="chat-window"]');
  
  // 发送消息
  const input = page.locator('textarea, input[type="text"]').last();
  await input.fill('你好');
  await input.press('Enter');
  
  // 等待响应
  await page.waitForSelector('[data-role="assistant"]', { timeout: 30000 });
  
  // 验证响应
  const response = await page.locator('[data-role="assistant"]').last().textContent();
  expect(response).toBeTruthy();
});
```

### 2. Agent 能力测试

基于 AI Orchestrator 的 ReAct Agent 架构，测试以下能力：

#### 创意生成 (Creative Generation)
```typescript
test('should generate ad creative', async ({ page }) => {
  await openChat(page);
  await sendMessage(page, '帮我生成一个广告创意，产品是智能手表');
  
  // 等待 agent 思考和工具调用
  await page.waitForSelector('[data-testid="tool-invocation"]', { timeout: 30000 });
  
  // 验证响应包含创意内容
  const response = await getLastAssistantMessage(page);
  expect(response).toMatch(/创意|广告|文案/);
});
```

#### 广告系列管理 (Campaign Management)
```typescript
test('should create campaign with confirmation', async ({ page }) => {
  await openChat(page);
  await sendMessage(page, '创建一个新的广告系列，预算1000元');
  
  // 等待确认对话框 (Human-in-the-Loop)
  await page.waitForSelector('[data-testid="confirmation-dialog"]', { timeout: 10000 });
  
  // 确认
  await page.click('[data-testid="confirm-button"]');
  
  // 等待创建完成
  await page.waitForSelector('text=/创建成功|已创建/', { timeout: 30000 });
});
```

#### 性能分析 (Performance Analytics)
```typescript
test('should analyze campaign performance', async ({ page }) => {
  await openChat(page);
  await sendMessage(page, '分析我的广告系列表现');
  
  // 等待图表或数据卡片
  await page.waitForSelector('[data-component="chart"], [data-component="card"]', { 
    timeout: 30000 
  });
  
  // 验证有数据展示
  const hasChart = await page.locator('[data-component="chart"]').count() > 0;
  const hasCard = await page.locator('[data-component="card"]').count() > 0;
  expect(hasChart || hasCard).toBeTruthy();
});
```

### 3. 工具调用测试

测试 MCP Tools 的调用：

```typescript
test('should invoke MCP tools', async ({ page }) => {
  // 监听网络请求
  const mcpCalls: string[] = [];
  page.on('request', request => {
    if (request.url().includes('/api/v1/mcp')) {
      mcpCalls.push(request.url());
    }
  });
  
  await openChat(page);
  await sendMessage(page, '获取我的广告账户信息');
  
  // 等待响应
  await page.waitForTimeout(5000);
  
  // 验证 MCP 工具被调用
  expect(mcpCalls.length).toBeGreaterThan(0);
});
```

### 4. Human-in-the-Loop 测试

测试确认流程：

```typescript
test('should handle user confirmation', async ({ page }) => {
  await openChat(page);
  await sendMessage(page, '删除我的第一个广告系列');
  
  // 应该显示确认对话框
  const confirmDialog = page.locator('[data-testid="confirmation-dialog"]');
  await expect(confirmDialog).toBeVisible({ timeout: 10000 });
  
  // 检查警告信息
  const warningText = await confirmDialog.textContent();
  expect(warningText).toMatch(/确认|删除|警告/);
  
  // 取消操作
  await page.click('[data-testid="cancel-button"]');
  
  // 验证取消消息
  await page.waitForSelector('text=/已取消|取消操作/', { timeout: 5000 });
});
```

### 5. 错误处理测试

```typescript
test('should handle API errors gracefully', async ({ page }) => {
  // 拦截 API 请求并返回错误
  await page.route('**/api/v1/chat', route => {
    route.fulfill({
      status: 500,
      body: JSON.stringify({ detail: 'Internal Server Error' }),
    });
  });
  
  await openChat(page);
  await sendMessage(page, '测试错误处理');
  
  // 应该显示错误消息
  await page.waitForSelector('[data-testid="error-message"]', { timeout: 5000 });
  
  const errorMsg = await page.locator('[data-testid="error-message"]').textContent();
  expect(errorMsg).toBeTruthy();
});
```

## 测试前置条件

### 1. 服务启动
```bash
# Backend
cd backend && uvicorn app.main:app --reload --port 8000

# AI Orchestrator
cd ai-orchestrator && uvicorn app.main:app --reload --port 8001

# Frontend
cd frontend && npm run dev

# Database & Redis
docker-compose up -d mysql redis
```

### 2. 测试数据
- Dev 用户已创建 (`dev@example.com`)
- 至少一个广告账户已绑定
- 一些测试广告系列和创意

### 3. 环境变量
```bash
# Backend
DATABASE_URL=mysql+aiomysql://...
REDIS_URL=redis://localhost:6379/0
GEMINI_API_KEY=your-key

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 运行测试

```bash
cd tests/e2e

# 安装依赖
npm install
npx playwright install chromium

# 运行所有测试
npm test

# 运行特定测试
npx playwright test agent_capabilities.spec.ts

# 调试模式
npx playwright test --debug

# UI 模式
npx playwright test --ui
```

## 测试覆盖范围

### Agent 核心能力
- ✅ 意图识别 (Intent Recognition)
- ✅ 工具选择 (Tool Selection)
- ✅ 工具执行 (Tool Execution)
- ✅ 响应生成 (Response Generation)
- ✅ Human-in-the-Loop (确认流程)

### 业务功能
- ✅ 创意生成
- ✅ 广告系列管理
- ✅ 性能分析
- ✅ 落地页生成
- ✅ 市场洞察

### 错误处理
- ✅ API 错误
- ✅ 超时处理
- ✅ 无效请求
- ✅ 权限错误

## 注意事项

1. **SSE 流式响应**: 前端使用 EventSource 接收流式响应，测试时需要等待完整响应
2. **异步工具调用**: Agent 可能调用多个工具，需要足够的超时时间
3. **Human-in-the-Loop**: 某些操作需要用户确认，测试需要模拟确认流程
4. **Credit 系统**: 某些操作消耗积分，测试前确保有足够积分
5. **Rate Limiting**: 注意 API 速率限制，避免测试被限流

## 调试技巧

1. **查看网络请求**:
```typescript
page.on('request', req => console.log('→', req.method(), req.url()));
page.on('response', res => console.log('←', res.status(), res.url()));
```

2. **查看控制台日志**:
```typescript
page.on('console', msg => console.log('Console:', msg.text()));
```

3. **截图**:
```typescript
await page.screenshot({ path: 'debug.png', fullPage: true });
```

4. **暂停执行**:
```typescript
await page.pause(); // 打开 Playwright Inspector
```

## 下一步

1. 添加更多 data-testid 属性到前端组件
2. 实现完整的 Human-in-the-Loop UI
3. 添加工具调用状态显示
4. 优化错误处理和用户反馈
5. 添加性能监控和日志
