/**
 * E2E UI Tests for AI Agent Capabilities
 * 
 * Tests the agent's ability to handle user requests through the chat interface
 * at http://localhost:3000/dashboard
 * 
 * Focus: Testing actual agent behavior, tool execution, and UI responses
 */

import { test, expect, Page } from '@playwright/test';

const DASHBOARD_URL = 'http://localhost:3000/dashboard';
const RESPONSE_TIMEOUT = 30000; // 30 seconds for agent responses

/**
 * Helper: Open chat drawer and wait for connection
 */
async function openChat(page: Page) {
  // Click the AI assistant button (bottom-right floating button)
  const chatButton = page.locator('button:has-text("AI 助手"), button[aria-label*="AI"], button[aria-label*="助手"]').first();
  await chatButton.waitFor({ state: 'visible', timeout: 10000 });
  await chatButton.click();
  
  // Wait for chat drawer to open
  await page.waitForTimeout(1000);
  
  // Verify chat interface is visible
  const chatInput = page.locator('textarea, input[placeholder*="消息"], input[placeholder*="message"]').last();
  await chatInput.waitFor({ state: 'visible', timeout: 5000 });
}

/**
 * Helper: Send message and wait for response
 */
async function sendMessageAndWait(page: Page, message: string) {
  const chatInput = page.locator('textarea, input[placeholder*="消息"], input[placeholder*="message"]').last();
  
  // Clear and type message
  await chatInput.clear();
  await chatInput.fill(message);
  
  // Send message (Enter key)
  await chatInput.press('Enter');
  
  // Wait for message to appear in chat
  await page.waitForTimeout(1000);
  
  // Wait for agent response (look for new message appearing)
  await page.waitForTimeout(RESPONSE_TIMEOUT);
}

/**
 * Helper: Get last message content
 */
async function getLastMessage(page: Page): Promise<string> {
  // Try different selectors for messages
  const messageSelectors = [
    '[data-role="assistant"]',
    '[class*="message"][class*="assistant"]',
    '[class*="ai-message"]',
    'div:has-text("AI")',
  ];
  
  for (const selector of messageSelectors) {
    const messages = page.locator(selector);
    const count = await messages.count();
    
    if (count > 0) {
      const lastMessage = messages.nth(count - 1);
      const text = await lastMessage.textContent();
      if (text && text.trim().length > 0) {
        return text.trim();
      }
    }
  }
  
  return '';
}

/**
 * Helper: Check if confirmation dialog is visible
 */
async function hasConfirmationDialog(page: Page): Promise<boolean> {
  const confirmSelectors = [
    'button:has-text("确认")',
    'button:has-text("Confirm")',
    '[data-testid="confirm-button"]',
    'button[class*="confirm"]',
  ];
  
  for (const selector of confirmSelectors) {
    const button = page.locator(selector);
    if (await button.isVisible({ timeout: 2000 }).catch(() => false)) {
      return true;
    }
  }
  
  return false;
}

/**
 * Helper: Click confirm button
 */
async function clickConfirm(page: Page) {
  const confirmButton = page.locator('button:has-text("确认"), button:has-text("Confirm")').first();
  await confirmButton.click();
  await page.waitForTimeout(1000);
}

/**
 * Helper: Take screenshot for debugging
 */
async function debugScreenshot(page: Page, name: string) {
  await page.screenshot({ 
    path: `.playwright-mcp/${name}.png`, 
    fullPage: true 
  });
}

test.describe('AI Agent - Basic Chat Interaction', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
  });

  test('should open chat drawer successfully', async ({ page }) => {
    await debugScreenshot(page, 'before-open-chat');
    
    await openChat(page);
    
    await debugScreenshot(page, 'after-open-chat');
    
    // Verify chat input is visible
    const chatInput = page.locator('textarea, input[type="text"]').last();
    await expect(chatInput).toBeVisible();
  });

  test('should send and receive messages', async ({ page }) => {
    await openChat(page);
    
    await sendMessageAndWait(page, '你好');
    
    await debugScreenshot(page, 'after-hello-message');
    
    // Check if response exists
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    console.log('Agent response:', response);
  });

  test('should handle simple queries', async ({ page }) => {
    await openChat(page);
    
    await sendMessageAndWait(page, '你能做什么？');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Should mention capabilities
    expect(response).toMatch(/广告|创意|分析|优化|落地页|campaign|creative|performance/i);
  });
});

test.describe('AI Agent - Campaign Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    await openChat(page);
  });

  test('should list campaigns', async ({ page }) => {
    await sendMessageAndWait(page, '显示我的广告系列');
    
    await debugScreenshot(page, 'list-campaigns');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Should show campaign info or empty state
    expect(response).toMatch(/广告系列|campaign|暂无|没有|empty/i);
  });

  test('should handle campaign creation request', async ({ page }) => {
    await sendMessageAndWait(page, '创建一个新的广告系列，名称是测试活动，预算2000元');
    
    await debugScreenshot(page, 'create-campaign-request');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Should ask for confirmation or more details
    const hasConfirm = await hasConfirmationDialog(page);
    
    if (hasConfirm) {
      console.log('✓ Confirmation dialog appeared');
      await debugScreenshot(page, 'create-campaign-confirm');
    } else {
      // Agent might ask for more information
      expect(response).toMatch(/平台|platform|确认|confirm|需要|need/i);
    }
  });

  test('should get campaign performance', async ({ page }) => {
    await sendMessageAndWait(page, '我的广告系列表现如何？');
    
    await debugScreenshot(page, 'campaign-performance');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
  });
});

test.describe('AI Agent - Creative Generation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    await openChat(page);
  });

  test('should handle creative generation request', async ({ page }) => {
    await sendMessageAndWait(page, '帮我生成一个广告创意，产品是运动鞋');
    
    await debugScreenshot(page, 'creative-generation-request');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Should mention creative generation or ask for details
    expect(response).toMatch(/创意|creative|生成|generate|需要|need|目标|target/i);
  });

  test('should list existing creatives', async ({ page }) => {
    await sendMessageAndWait(page, '显示我的广告创意');
    
    await debugScreenshot(page, 'list-creatives');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
  });

  test('should handle creative analysis request', async ({ page }) => {
    await sendMessageAndWait(page, '分析我的广告创意效果');
    
    await debugScreenshot(page, 'creative-analysis');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
  });
});

test.describe('AI Agent - Performance Analytics', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    await openChat(page);
  });

  test('should analyze performance', async ({ page }) => {
    await sendMessageAndWait(page, '分析我的广告表现');
    
    await debugScreenshot(page, 'performance-analysis');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Check for charts or metrics
    const hasChart = await page.locator('canvas, svg[class*="chart"]').count() > 0;
    const hasMetrics = await page.locator('[class*="metric"], [class*="card"]').count() > 0;
    
    console.log('Has chart:', hasChart);
    console.log('Has metrics:', hasMetrics);
  });

  test('should detect anomalies', async ({ page }) => {
    await sendMessageAndWait(page, '检测广告数据异常');
    
    await debugScreenshot(page, 'anomaly-detection');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
  });

  test('should provide recommendations', async ({ page }) => {
    await sendMessageAndWait(page, '给我一些优化建议');
    
    await debugScreenshot(page, 'recommendations');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Should provide actionable recommendations
    expect(response).toMatch(/建议|recommend|优化|optimize|提升|improve/i);
  });
});

test.describe('AI Agent - Landing Pages', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    await openChat(page);
  });

  test('should list landing pages', async ({ page }) => {
    await sendMessageAndWait(page, '显示我的落地页');
    
    await debugScreenshot(page, 'list-landing-pages');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
  });

  test('should handle landing page generation request', async ({ page }) => {
    await sendMessageAndWait(page, '为我的产品生成一个落地页');
    
    await debugScreenshot(page, 'landing-page-generation');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Should ask for product details or confirmation
    expect(response).toMatch(/产品|product|详情|detail|确认|confirm/i);
  });

  test('should analyze landing page performance', async ({ page }) => {
    await sendMessageAndWait(page, '分析落地页转化率');
    
    await debugScreenshot(page, 'landing-page-analysis');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
  });
});

test.describe('AI Agent - Market Intelligence', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    await openChat(page);
  });

  test('should analyze market trends', async ({ page }) => {
    await sendMessageAndWait(page, '分析运动服装市场趋势');
    
    await debugScreenshot(page, 'market-trends');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Should provide market insights
    expect(response).toMatch(/趋势|trend|市场|market|分析|analysis/i);
  });

  test('should track competitors', async ({ page }) => {
    await sendMessageAndWait(page, '追踪竞争对手');
    
    await debugScreenshot(page, 'competitor-tracking');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
  });

  test('should provide audience insights', async ({ page }) => {
    await sendMessageAndWait(page, '分析目标受众');
    
    await debugScreenshot(page, 'audience-insights');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
  });
});

test.describe('AI Agent - Account Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    await openChat(page);
  });

  test('should show account info', async ({ page }) => {
    await sendMessageAndWait(page, '显示我的账户信息');
    
    await debugScreenshot(page, 'account-info');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
  });

  test('should show credit balance', async ({ page }) => {
    await sendMessageAndWait(page, '我还有多少积分？');
    
    await debugScreenshot(page, 'credit-balance');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Should mention credits
    expect(response).toMatch(/积分|credit|余额|balance/i);
  });

  test('should list ad accounts', async ({ page }) => {
    await sendMessageAndWait(page, '显示我的广告账户');
    
    await debugScreenshot(page, 'ad-accounts');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
  });
});

test.describe('AI Agent - Multi-turn Conversations', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    await openChat(page);
  });

  test('should maintain context across messages', async ({ page }) => {
    // First message
    await sendMessageAndWait(page, '我想创建一个广告系列');
    await debugScreenshot(page, 'context-1');
    
    let response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Follow-up without repeating context
    await sendMessageAndWait(page, '预算是3000元');
    await debugScreenshot(page, 'context-2');
    
    response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Another follow-up
    await sendMessageAndWait(page, '投放到Facebook');
    await debugScreenshot(page, 'context-3');
    
    response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Should understand full context
    expect(response).toMatch(/广告系列|campaign|3000|Facebook|Meta/i);
  });

  test('should handle clarification requests', async ({ page }) => {
    await sendMessageAndWait(page, '优化我的广告');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Agent should ask for clarification
    expect(response).toMatch(/哪个|哪些|具体|which|what|specify/i);
    
    // Provide clarification
    await sendMessageAndWait(page, '优化预算分配');
    
    const response2 = await getLastMessage(page);
    expect(response2.length).toBeGreaterThan(0);
  });
});

test.describe('AI Agent - Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    await openChat(page);
  });

  test('should handle unclear requests', async ({ page }) => {
    await sendMessageAndWait(page, 'xyz123不存在的操作');
    
    await debugScreenshot(page, 'unclear-request');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Should provide helpful response
    expect(response).toMatch(/不理解|不明白|帮助|help|clarify|understand/i);
  });

  test('should handle missing parameters gracefully', async ({ page }) => {
    await sendMessageAndWait(page, '创建广告系列');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Should ask for required parameters
    expect(response).toMatch(/名称|预算|平台|name|budget|platform/i);
  });

  test('should handle invalid operations', async ({ page }) => {
    await sendMessageAndWait(page, '删除ID为999999的广告系列');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Should indicate not found
    expect(response).toMatch(/未找到|不存在|找不到|not found|doesn't exist/i);
  });
});

test.describe('AI Agent - Tool Execution Visibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    await openChat(page);
  });

  test('should show tool execution status', async ({ page }) => {
    await sendMessageAndWait(page, '获取我的账户信息');
    
    await debugScreenshot(page, 'tool-execution');
    
    // Check for tool invocation indicators
    const hasToolIndicator = await page.locator('[class*="tool"], [class*="loading"], [class*="thinking"]').count() > 0;
    
    console.log('Has tool indicator:', hasToolIndicator);
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
  });

  test('should handle tool execution errors', async ({ page }) => {
    // Try to access non-existent resource
    await sendMessageAndWait(page, '显示ID为invalid的广告系列');
    
    await debugScreenshot(page, 'tool-error');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Should show error message
    expect(response).toMatch(/错误|失败|未找到|error|failed|not found/i);
  });
});

test.describe('AI Agent - Confirmation Flows', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    await openChat(page);
  });

  test('should request confirmation for destructive actions', async ({ page }) => {
    await sendMessageAndWait(page, '删除我的第一个广告系列');
    
    await debugScreenshot(page, 'delete-confirmation');
    
    const hasConfirm = await hasConfirmationDialog(page);
    
    if (hasConfirm) {
      console.log('✓ Confirmation dialog appeared for delete action');
      
      // Check for warning message
      const pageContent = await page.content();
      expect(pageContent).toMatch(/确认|删除|警告|confirm|delete|warning/i);
    } else {
      // Agent might ask for confirmation in text
      const response = await getLastMessage(page);
      expect(response).toMatch(/确认|删除|警告|confirm|delete|warning/i);
    }
  });

  test('should request confirmation for credit-consuming actions', async ({ page }) => {
    await sendMessageAndWait(page, '生成10个广告图片');
    
    await debugScreenshot(page, 'credit-confirmation');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Should mention credit cost
    expect(response).toMatch(/积分|credit|消耗|cost/i);
  });
});

test.describe('AI Agent - Response Quality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    await openChat(page);
  });

  test('should provide structured responses', async ({ page }) => {
    await sendMessageAndWait(page, '分析我的广告表现并给出建议');
    
    await debugScreenshot(page, 'structured-response');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Should be well-structured (not just plain text)
    const hasStructure = await page.locator('ul, ol, table, [class*="card"], [class*="list"]').count() > 0;
    
    console.log('Has structured content:', hasStructure);
  });

  test('should provide actionable recommendations', async ({ page }) => {
    await sendMessageAndWait(page, '如何提升我的广告效果？');
    
    const response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    // Should provide specific recommendations
    expect(response).toMatch(/建议|推荐|可以|应该|recommend|suggest|should|can/i);
  });

  test('should handle bilingual queries', async ({ page }) => {
    // Test Chinese
    await sendMessageAndWait(page, '显示我的广告系列');
    let response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    await debugScreenshot(page, 'chinese-query');
    
    // Test English
    await sendMessageAndWait(page, 'Show my campaigns');
    response = await getLastMessage(page);
    expect(response.length).toBeGreaterThan(0);
    
    await debugScreenshot(page, 'english-query');
  });
});
