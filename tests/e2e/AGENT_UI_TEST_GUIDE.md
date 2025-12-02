# AI Agent UI 测试指南

## 概述

本测试套件使用 Playwright 对 AAE 平台的 AI Agent 进行端到端 UI 测试，重点测试通过聊天界面 (http://localhost:3000/dashboard) 访问的 Agent 能力。

## 测试文件

### 1. `agent-ui-capabilities.spec.ts` - 全面的 UI 能力测试

这是主要的测试文件，包含以下测试场景：

#### 基础聊天交互
- ✅ 打开聊天抽屉
- ✅ 发送和接收消息
- ✅ 处理简单查询

#### 广告系列管理
- ✅ 列出广告系列
- ✅ 创建广告系列（带确认）
- ✅ 获取广告系列表现
- ✅ 暂停/恢复广告系列
- ✅ 优化预算分配

#### 创意生成
- ✅ 生成广告创意
- ✅ 列出现有创意
- ✅ 分析创意效果
- ✅ 竞品创意分析

#### 性能分析
- ✅ 分析广告表现
- ✅ 检测数据异常
- ✅ 提供优化建议
- ✅ 生成性能报告

#### 落地页管理
- ✅ 列出落地页
- ✅ 生成落地页（带确认）
- ✅ 分析转化率

#### 市场洞察
- ✅ 分析市场趋势
- ✅ 追踪竞争对手
- ✅ 提供受众洞察

#### 账户管理
- ✅ 显示账户信息
- ✅ 显示积分余额
- ✅ 列出广告账户

#### 多轮对话
- ✅ 跨消息维护上下文
- ✅ 处理澄清请求

#### 错误处理
- ✅ 处理不明确的请求
- ✅ 处理缺失参数
- ✅ 处理无效操作

#### 确认流程
- ✅ 破坏性操作的确认
- ✅ 消耗积分操作的确认

#### 工具执行可见性
- ✅ 显示工具执行状态
- ✅ 处理工具执行错误

#### 响应质量
- ✅ 提供结构化响应
- ✅ 提供可操作的建议
- ✅ 处理双语查询（中英文）

### 2. `agent-core.spec.ts` - 核心功能快速测试

简化的测试套件，用于快速验证核心功能：
- 问候语响应
- 广告系列查询
- 创意查询
- 性能查询
- 账户查询

## 运行测试

### 前置条件

确保所有服务正在运行：

```bash
# 1. 启动 Backend (端口 8000)
cd backend
uvicorn app.main:app --reload --port 8000

# 2. 启动 Frontend (端口 3000)
cd frontend
npm run dev

# 3. 启动 AI Orchestrator (端口 8001)
cd ai-orchestrator
uvicorn app.main:app --reload --port 8001
```

### 安装依赖

```bash
cd tests/e2e
npm install
npx playwright install
```

### 运行所有测试

```bash
# 使用测试脚本（推荐）
./run-agent-tests.sh

# 或直接使用 npm
npm test
```

### 运行特定测试文件

```bash
# 运行完整的 UI 能力测试
npx playwright test agent-ui-capabilities.spec.ts

# 运行核心功能测试
npx playwright test agent-core.spec.ts

# 运行特定测试用例
npx playwright test --grep "should open chat drawer"
```

### 调试模式

```bash
# 显示浏览器窗口
./run-agent-tests.sh --headed

# 使用 Playwright Inspector
./run-agent-tests.sh --debug

# 使用 UI 模式（推荐用于开发）
./run-agent-tests.sh --ui
```

### 运行特定文件

```bash
./run-agent-tests.sh --file agent-core.spec.ts
```

## 测试架构

### 辅助函数

测试使用以下辅助函数简化操作：

```typescript
// 打开聊天并等待连接
async function openChat(page: Page)

// 发送消息并等待响应
async function sendMessageAndWait(page: Page, message: string)

// 获取最后一条消息
async function getLastMessage(page: Page): Promise<string>

// 检查是否有确认对话框
async function hasConfirmationDialog(page: Page): Promise<boolean>

// 点击确认按钮
async function clickConfirm(page: Page)

// 调试截图
async function debugScreenshot(page: Page, name: string)
```

### 选择器策略

测试使用灵活的选择器策略来适应不同的实现：

```typescript
// 聊天按钮
button:has-text("AI 助手"), button[aria-label*="AI"]

// 聊天输入
textarea, input[placeholder*="消息"]

// 消息
[data-role="assistant"], [class*="message"][class*="assistant"]

// 确认按钮
button:has-text("确认"), button:has-text("Confirm")
```

## 截图和调试

所有测试都会生成截图保存在 `.playwright-mcp/` 目录：

```bash
# 查看截图
ls -la .playwright-mcp/

# 截图命名规则
before-open-chat.png          # 打开聊天前
after-open-chat.png           # 打开聊天后
test-greeting.png             # 问候测试
test-campaigns.png            # 广告系列测试
list-campaigns.png            # 列出广告系列
create-campaign-request.png   # 创建广告系列请求
# ... 等等
```

## 测试报告

运行测试后查看 HTML 报告：

```bash
npx playwright show-report
```

报告包含：
- 测试结果统计
- 失败测试的详细信息
- 截图
- 执行时间
- 错误堆栈

## 常见问题

### 1. 聊天按钮找不到

**问题**: `Error: Timeout waiting for selector`

**解决方案**:
- 确认 Frontend 在 http://localhost:3000 运行
- 检查聊天按钮是否渲染
- 验证按钮文本是否为 "AI 助手"
- 查看浏览器控制台错误

### 2. Agent 没有响应

**问题**: 消息发送后没有收到回复

**解决方案**:
- 确认 AI Orchestrator 在 http://localhost:8001 运行
- 检查 WebSocket 连接状态
- 验证 Backend MCP 工具已注册
- 查看 AI Orchestrator 日志
- 确认 GEMINI_API_KEY 已配置

### 3. 测试超时

**问题**: `Test timeout of 30000ms exceeded`

**解决方案**:
- 增加 `RESPONSE_TIMEOUT` 常量
- 检查服务响应速度
- 验证网络连接
- 查看服务日志

### 4. 确认对话框未出现

**问题**: 期望的确认对话框没有显示

**解决方案**:
- 检查 Agent 是否在文本中请求确认
- 验证前端确认组件实现
- 查看 Agent 响应内容
- 检查 MCP 工具的 `requires_confirmation` 元数据

## 测试覆盖的 Agent 能力

根据当前的 Agent 架构，测试覆盖以下能力模块：

### 1. Ad Creative (广告创意)
- `ai-orchestrator/app/modules/ad_creative/`
- 创意生成、变体生成、竞品分析

### 2. Ad Performance (广告性能)
- `ai-orchestrator/app/modules/ad_performance/`
- 性能分析、异常检测、优化建议

### 3. Campaign Automation (广告系列自动化)
- `ai-orchestrator/app/modules/campaign_automation/`
- 广告系列创建、预算优化、规则引擎

### 4. Landing Page (落地页)
- `ai-orchestrator/app/modules/landing_page/`
- 落地页生成、A/B 测试、转化追踪

### 5. Market Insights (市场洞察)
- `ai-orchestrator/app/modules/market_insights/`
- 市场趋势、竞品追踪、受众分析

### 6. MCP Tools (后端工具)
- `backend/app/mcp/tools/`
- 账户管理、积分管理、通知等

## 扩展测试

### 添加新测试场景

1. 在 `agent-ui-capabilities.spec.ts` 中添加新的 `test.describe` 块
2. 使用辅助函数简化测试代码
3. 添加有意义的断言
4. 生成调试截图
5. 更新本文档

### 测试模板

```typescript
test.describe('AI Agent - New Feature', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    await openChat(page);
  });

  test('should handle new feature request', async ({ page }) => {
    await sendMessageAndWait(page, '你的测试消息');
    
    await debugScreenshot(page, 'new-feature-test');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    expect(response).toMatch(/期望的模式/);
  });
});
```

## CI/CD 集成

测试可以集成到 CI/CD 流程：

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Agent Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start services
        run: docker-compose up -d
      
      - name: Wait for services
        run: |
          timeout 60 bash -c 'until curl -f http://localhost:3000; do sleep 2; done'
      
      - name: Run tests
        run: |
          cd tests/e2e
          npm install
          npx playwright install --with-deps
          npm test
      
      - name: Upload screenshots
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-screenshots
          path: tests/e2e/.playwright-mcp/
```

## 最佳实践

1. **测试独立性**: 每个测试应该独立运行，不依赖其他测试
2. **明确等待**: 使用明确的等待条件，避免固定延迟
3. **有意义的断言**: 断言应该验证实际功能，不只是元素存在
4. **错误消息**: 提供清晰的错误消息帮助调试
5. **截图**: 为关键步骤生成截图
6. **清理**: 测试后清理测试数据（如果需要）

## 性能考虑

- 测试设计为并行执行
- 使用共享浏览器上下文
- 优化等待策略
- 截图仅在需要时生成

## 贡献指南

添加新测试时：

1. 遵循现有测试结构
2. 使用提供的辅助函数
3. 添加适当的注释
4. 生成调试截图
5. 更新本文档
6. 确保测试在本地通过

## 相关文档

- `README.md` - E2E 测试总览
- `AGENT_TEST_GUIDE.md` - Agent 测试指南
- `playwright.config.ts` - Playwright 配置
- `utils/test-helpers.ts` - 辅助函数文档

## 支持

如有问题或需要帮助：

1. 查看测试截图了解失败原因
2. 检查服务日志
3. 使用 `--debug` 模式逐步调试
4. 查看 Playwright 文档: https://playwright.dev
