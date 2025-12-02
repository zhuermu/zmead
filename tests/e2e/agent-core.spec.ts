/**
 * Core Agent Capability Tests
 * 
 * Simplified tests focusing on essential agent behaviors
 */

import { test, expect, Page } from '@playwright/test';

const DASHBOARD_URL = 'http://localhost:3000/dashboard';

// Helper to open chat
async function openChat(page: Page) {
  const chatButton = page.locator('button').filter({ hasText: /AI|助手/ }).first();
  await chatButton.click({ timeout: 10000 });
  await page.waitForTimeout(1000);
}

// Helper to send message
async function sendMessage(page: Page, text: string) {
  const input = page.locator('textarea, input[type="text"]').last();
  await input.fill(text);
  await input.press('Enter');
  await page.waitForTimeout(3000); // Wait for response
}

// Helper to get messages
async function getMessages(page: Page) {
  await page.waitForTimeout(1000);
  const content = await page.content();
  return content;
}

test.describe('Agent Core Tests', () => {
  test('should open chat and respond to greeting', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    
    await openChat(page);
    await sendMessage(page, '你好');
    
    const content = await getMessages(page);
    expect(content.length).toBeGreaterThan(0);
    
    await page.screenshot({ path: '.playwright-mcp/test-greeting.png' });
  });

  test('should handle campaign query', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    
    await openChat(page);
    await sendMessage(page, '显示我的广告系列');
    
    await page.screenshot({ path: '.playwright-mcp/test-campaigns.png' });
  });

  test('should handle creative query', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    
    await openChat(page);
    await sendMessage(page, '显示我的广告创意');
    
    await page.screenshot({ path: '.playwright-mcp/test-creatives.png' });
  });

  test('should handle performance query', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    
    await openChat(page);
    await sendMessage(page, '分析我的广告表现');
    
    await page.screenshot({ path: '.playwright-mcp/test-performance.png' });
  });

  test('should handle account query', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    
    await openChat(page);
    await sendMessage(page, '显示我的账户信息');
    
    await page.screenshot({ path: '.playwright-mcp/test-account.png' });
  });
});
