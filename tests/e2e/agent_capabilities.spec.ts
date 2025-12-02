/**
 * E2E tests for AI Agent capabilities
 * 
 * Tests the agent's ability to:
 * - Understand user intent
 * - Execute appropriate tools
 * - Handle confirmations
 * - Provide structured responses
 * - Handle errors gracefully
 */

import { test, expect, Page } from '@playwright/test';

// Test configuration
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000';
const WS_TIMEOUT = 30000; // 30 seconds for agent responses

// Helper function to wait for WebSocket connection
async function waitForChatReady(page: Page) {
  await page.waitForSelector('[data-testid="chat-button"]', { timeout: 10000 });
  await page.click('[data-testid="chat-button"]');
  await page.waitForSelector('[data-testid="chat-window"]', { timeout: 5000 });
  await page.waitForSelector('[data-testid="connection-status"][data-status="connected"]', { timeout: 10000 });
}

// Helper function to send message and wait for response
async function sendMessageAndWaitForResponse(page: Page, message: string) {
  const input = page.locator('[data-testid="chat-input"]');
  await input.fill(message);
  await input.press('Enter');
  
  // Wait for message to appear in chat
  await page.waitForSelector(`text="${message}"`, { timeout: 5000 });
  
  // Wait for agent response (look for assistant message)
  await page.waitForSelector('[data-role="assistant"]', { timeout: WS_TIMEOUT });
}

// Helper function to get last assistant message
async function getLastAssistantMessage(page: Page): Promise<string> {
  const messages = page.locator('[data-role="assistant"]');
  const count = await messages.count();
  if (count === 0) return '';
  
  const lastMessage = messages.nth(count - 1);
  return await lastMessage.textContent() || '';
}

test.describe('AI Agent - Creative Generation Capabilities', () => {
  test.beforeEach(async ({ page }) => {
    // Login (assuming dev mode or test user)
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test('should generate ad creative from product description', async ({ page }) => {
    await waitForChatReady(page);
    
    // Send creative generation request
    await sendMessageAndWaitForResponse(
      page,
      '帮我生成一个广告创意，产品是智能手表，目标受众是年轻运动爱好者'
    );
    
    // Check for creative generation response
    const response = await getLastAssistantMessage(page);
    expect(response).toContain('创意');
    
    // Check for embedded card or image
    const hasCard = await page.locator('[data-component="card"]').count() > 0;
    const hasImage = await page.locator('[data-component="image"]').count() > 0;
    expect(hasCard || hasImage).toBeTruthy();
  });

  test('should handle creative generation with confirmation', async ({ page }) => {
    await waitForChatReady(page);
    
    // Request creative generation that requires confirmation
    await sendMessageAndWaitForResponse(
      page,
      '生成5个广告图片变体'
    );
    
    // Should show confirmation dialog (costs credits)
    const confirmButton = page.locator('[data-testid="confirm-button"]');
    await expect(confirmButton).toBeVisible({ timeout: 5000 });
    
    // Check confirmation message mentions credit cost
    const confirmMessage = await page.locator('[data-testid="confirmation-message"]').textContent();
    expect(confirmMessage).toMatch(/积分|credit/i);
    
    // Confirm action
    await confirmButton.click();
    
    // Wait for generation to complete
    await page.waitForSelector('[data-component="card"]', { timeout: WS_TIMEOUT });
  });

  test('should analyze competitor creatives', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '分析竞争对手的广告创意，产品类别是运动鞋'
    );
    
    const response = await getLastAssistantMessage(page);
    expect(response).toMatch(/竞争|分析|趋势/);
    
    // Should show analysis results
    const hasTable = await page.locator('[data-component="table"]').count() > 0;
    const hasCard = await page.locator('[data-component="card"]').count() > 0;
    expect(hasTable || hasCard).toBeTruthy();
  });
});

test.describe('AI Agent - Campaign Management Capabilities', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test('should create campaign with confirmation', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '创建一个新的广告系列，预算1000元，投放Facebook'
    );
    
    // Should request confirmation for campaign creation
    const confirmButton = page.locator('[data-testid="confirm-button"]');
    await expect(confirmButton).toBeVisible({ timeout: 5000 });
    
    // Check confirmation shows campaign details
    const details = await page.locator('[data-testid="confirmation-details"]').textContent();
    expect(details).toContain('1000');
    expect(details).toMatch(/Facebook|Meta/i);
    
    // Confirm
    await confirmButton.click();
    
    // Wait for success message
    await page.waitForSelector('text=/创建成功|成功创建/', { timeout: WS_TIMEOUT });
  });

  test('should list active campaigns', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '显示我的所有活跃广告系列'
    );
    
    // Should show campaign list
    const hasTable = await page.locator('[data-component="table"]').count() > 0;
    const hasCards = await page.locator('[data-component="card"]').count() > 0;
    expect(hasTable || hasCards).toBeTruthy();
  });

  test('should pause campaign with confirmation', async ({ page }) => {
    await waitForChatReady(page);
    
    // First, list campaigns to get a campaign name
    await sendMessageAndWaitForResponse(page, '显示我的广告系列');
    
    // Try to pause a campaign
    await sendMessageAndWaitForResponse(
      page,
      '暂停第一个广告系列'
    );
    
    // Should show confirmation
    const confirmButton = page.locator('[data-testid="confirm-button"]');
    await expect(confirmButton).toBeVisible({ timeout: 5000 });
    
    await confirmButton.click();
    
    // Wait for success
    await page.waitForSelector('text=/暂停成功|已暂停/', { timeout: WS_TIMEOUT });
  });

  test('should optimize campaign budget', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '优化我的广告系列预算分配'
    );
    
    const response = await getLastAssistantMessage(page);
    expect(response).toMatch(/预算|优化|建议/);
    
    // Should show recommendations
    const hasRecommendations = await page.locator('[data-component="card"]').count() > 0;
    expect(hasRecommendations).toBeTruthy();
  });
});

test.describe('AI Agent - Performance Analytics Capabilities', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test('should analyze campaign performance', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '分析我的广告系列表现'
    );
    
    // Should show performance metrics
    const hasChart = await page.locator('[data-component="chart"]').count() > 0;
    const hasMetrics = await page.locator('[data-component="card"]').count() > 0;
    expect(hasChart || hasMetrics).toBeTruthy();
  });

  test('should detect anomalies', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '检测广告数据异常'
    );
    
    const response = await getLastAssistantMessage(page);
    expect(response).toMatch(/异常|检测|正常/);
  });

  test('should provide performance recommendations', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '给我一些提升广告效果的建议'
    );
    
    const response = await getLastAssistantMessage(page);
    expect(response).toMatch(/建议|优化|提升/);
    
    // Should show action buttons
    const hasActionButtons = await page.locator('[data-testid="action-button"]').count() > 0;
    expect(hasActionButtons).toBeTruthy();
  });

  test('should generate performance report', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '生成本周的广告效果报告'
    );
    
    // Should show report or download option
    const response = await getLastAssistantMessage(page);
    expect(response).toMatch(/报告|下载|生成/);
  });
});

test.describe('AI Agent - Landing Page Capabilities', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test('should generate landing page with confirmation', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '为我的产品生成一个落地页，产品是智能音箱'
    );
    
    // Should request confirmation (costs credits)
    const confirmButton = page.locator('[data-testid="confirm-button"]');
    await expect(confirmButton).toBeVisible({ timeout: 5000 });
    
    await confirmButton.click();
    
    // Wait for generation
    await page.waitForSelector('text=/生成成功|已生成/', { timeout: WS_TIMEOUT });
  });

  test('should list landing pages', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '显示我的所有落地页'
    );
    
    const hasTable = await page.locator('[data-component="table"]').count() > 0;
    const hasCards = await page.locator('[data-component="card"]').count() > 0;
    expect(hasTable || hasCards).toBeTruthy();
  });

  test('should analyze landing page performance', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '分析我的落地页转化率'
    );
    
    const response = await getLastAssistantMessage(page);
    expect(response).toMatch(/转化|分析|效果/);
  });
});

test.describe('AI Agent - Market Intelligence Capabilities', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test('should analyze market trends', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '分析运动服装市场的最新趋势'
    );
    
    const response = await getLastAssistantMessage(page);
    expect(response).toMatch(/趋势|市场|分析/);
  });

  test('should track competitors', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '追踪竞争对手的广告策略'
    );
    
    const response = await getLastAssistantMessage(page);
    expect(response).toMatch(/竞争|策略|追踪/);
  });

  test('should provide audience insights', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '分析我的目标受众特征'
    );
    
    const response = await getLastAssistantMessage(page);
    expect(response).toMatch(/受众|特征|分析/);
  });
});

test.describe('AI Agent - Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test('should handle invalid requests gracefully', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '执行一个不存在的操作xyz123'
    );
    
    const response = await getLastAssistantMessage(page);
    // Should provide helpful error message
    expect(response.length).toBeGreaterThan(0);
  });

  test('should handle missing parameters', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '创建广告系列'
    );
    
    // Should ask for missing information
    const response = await getLastAssistantMessage(page);
    expect(response).toMatch(/预算|名称|平台|需要/);
  });

  test('should handle cancellation', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '删除所有广告系列'
    );
    
    // Should show confirmation
    const cancelButton = page.locator('[data-testid="cancel-button"]');
    await expect(cancelButton).toBeVisible({ timeout: 5000 });
    
    // Cancel the action
    await cancelButton.click();
    
    // Should show cancellation message
    await page.waitForSelector('text=/已取消|取消操作/', { timeout: 5000 });
  });

  test('should handle insufficient credits', async ({ page }) => {
    await waitForChatReady(page);
    
    // Try to perform action that costs credits
    await sendMessageAndWaitForResponse(
      page,
      '生成100个广告图片'
    );
    
    // Should show error or warning about credits
    const response = await getLastAssistantMessage(page);
    expect(response).toMatch(/积分|credit|不足|充值/i);
  });
});

test.describe('AI Agent - Multi-step Conversations', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test('should maintain context across messages', async ({ page }) => {
    await waitForChatReady(page);
    
    // First message
    await sendMessageAndWaitForResponse(
      page,
      '我想创建一个广告系列'
    );
    
    // Follow-up without repeating context
    await sendMessageAndWaitForResponse(
      page,
      '预算设置为5000元'
    );
    
    // Another follow-up
    await sendMessageAndWaitForResponse(
      page,
      '投放到TikTok平台'
    );
    
    // Should understand the full context
    const response = await getLastAssistantMessage(page);
    expect(response.length).toBeGreaterThan(0);
  });

  test('should handle clarification requests', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '优化我的广告'
    );
    
    // Agent should ask for clarification
    const response = await getLastAssistantMessage(page);
    expect(response).toMatch(/哪个|哪些|具体|明确/);
    
    // Provide clarification
    await sendMessageAndWaitForResponse(
      page,
      '优化预算分配'
    );
    
    // Should proceed with optimization
    const finalResponse = await getLastAssistantMessage(page);
    expect(finalResponse).toMatch(/预算|优化/);
  });
});

test.describe('AI Agent - Tool Execution', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test('should show tool invocation status', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '获取我的账户信息'
    );
    
    // Should show tool invocation card
    const toolCard = page.locator('[data-testid="tool-invocation-card"]');
    const hasToolCard = await toolCard.count() > 0;
    
    if (hasToolCard) {
      // Check tool name is displayed
      const toolName = await toolCard.locator('[data-testid="tool-name"]').textContent();
      expect(toolName).toBeTruthy();
    }
  });

  test('should handle tool execution errors', async ({ page }) => {
    await waitForChatReady(page);
    
    // Try to access non-existent resource
    await sendMessageAndWaitForResponse(
      page,
      '显示ID为999999的广告系列详情'
    );
    
    const response = await getLastAssistantMessage(page);
    expect(response).toMatch(/未找到|不存在|找不到/);
  });
});

test.describe('AI Agent - Human-in-the-Loop', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test('should request confirmation for destructive actions', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '删除我的第一个广告系列'
    );
    
    // Should show confirmation dialog
    const confirmDialog = page.locator('[data-testid="confirmation-dialog"]');
    await expect(confirmDialog).toBeVisible({ timeout: 5000 });
    
    // Should show warning
    const warningText = await confirmDialog.textContent();
    expect(warningText).toMatch(/确认|删除|警告/);
  });

  test('should request input for missing parameters', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '创建广告系列，名称是春季促销'
    );
    
    // Should ask for budget
    const response = await getLastAssistantMessage(page);
    expect(response).toMatch(/预算/);
    
    // Provide budget
    await sendMessageAndWaitForResponse(page, '预算3000元');
    
    // Should ask for platform
    const response2 = await getLastAssistantMessage(page);
    expect(response2).toMatch(/平台|Facebook|TikTok|Meta/);
  });

  test('should provide options for user selection', async ({ page }) => {
    await waitForChatReady(page);
    
    await sendMessageAndWaitForResponse(
      page,
      '我想投放广告'
    );
    
    // Should show platform options
    const hasOptions = await page.locator('[data-testid="option-button"]').count() > 0;
    
    if (hasOptions) {
      // Click an option
      await page.locator('[data-testid="option-button"]').first().click();
      
      // Should proceed with selected option
      await page.waitForSelector('[data-role="assistant"]', { timeout: WS_TIMEOUT });
    }
  });
});
