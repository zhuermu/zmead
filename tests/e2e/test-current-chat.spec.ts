/**
 * Test current chat functionality
 * This test validates the actual chat implementation
 */

import { test, expect } from '@playwright/test';

test.describe('Current Chat Implementation Test', () => {
  test('should open chat drawer and inspect current state', async ({ page }) => {
    // Navigate to dashboard
    await page.goto('http://localhost:3000/dashboard');
    await page.waitForLoadState('networkidle');
    
    // Take initial screenshot
    await page.screenshot({ path: '.playwright-mcp/chat-page-initial.png', fullPage: true });
    
    // Find and click the chat button (灯泡图标)
    const chatButton = page.locator('button:has-text("AI 助手")');
    await expect(chatButton).toBeVisible({ timeout: 10000 });
    
    console.log('✓ Chat button found');
    
    // Click to open chat
    await chatButton.click();
    await page.waitForTimeout(1000);
    
    // Take screenshot after opening
    await page.screenshot({ path: '.playwright-mcp/chat-drawer-open.png', fullPage: true });
    
    console.log('✓ Chat drawer opened');
    
    // Check if chat drawer is visible
    const chatDrawer = page.locator('[class*="chat"]').first();
    await expect(chatDrawer).toBeVisible();
    
    // Check for input field
    const inputField = page.locator('textarea, input[type="text"]').last();
    await expect(inputField).toBeVisible();
    
    console.log('✓ Input field found');
    
    // Check for existing messages
    const messages = await page.locator('[class*="message"]').count();
    console.log(`✓ Found ${messages} existing messages`);
    
    // Try to send a test message
    await inputField.fill('你好，测试消息');
    await page.screenshot({ path: '.playwright-mcp/chat-working.png', fullPage: true });
    
    // Press Enter to send
    await inputField.press('Enter');
    await page.waitForTimeout(2000);
    
    // Check console for errors
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    // Wait a bit for response
    await page.waitForTimeout(3000);
    
    // Take final screenshot
    await page.screenshot({ path: '.playwright-mcp/chat-after-send.png', fullPage: true });
    
    // Log any errors
    if (errors.length > 0) {
      console.log('❌ Console errors detected:');
      errors.forEach(err => console.log('  -', err));
    }
    
    // Check network requests
    const requests = await page.evaluate(() => {
      return (window as any).__networkRequests || [];
    });
    
    console.log('Network requests:', requests);
  });

  test('should inspect chat API endpoints', async ({ page }) => {
    // Track network requests
    const requests: any[] = [];
    
    page.on('request', request => {
      if (request.url().includes('/api/') || request.url().includes('/ws/')) {
        requests.push({
          url: request.url(),
          method: request.method(),
        });
      }
    });
    
    page.on('response', response => {
      if (response.url().includes('/api/') || response.url().includes('/ws/')) {
        console.log(`${response.request().method()} ${response.url()} => ${response.status()}`);
      }
    });
    
    // Navigate and interact
    await page.goto('http://localhost:3000/dashboard');
    await page.waitForLoadState('networkidle');
    
    // Open chat
    const chatButton = page.locator('button:has-text("AI 助手")');
    await chatButton.click();
    await page.waitForTimeout(1000);
    
    // Send message
    const inputField = page.locator('textarea, input[type="text"]').last();
    await inputField.fill('测试API端点');
    await inputField.press('Enter');
    
    // Wait for API calls
    await page.waitForTimeout(3000);
    
    // Log all API requests
    console.log('\n=== API Requests ===');
    requests.forEach(req => {
      console.log(`${req.method} ${req.url}`);
    });
  });

  test('should check backend health endpoints', async ({ page }) => {
    // Check backend health
    const backendHealth = await page.request.get('http://localhost:8000/health');
    console.log('Backend health:', backendHealth.status());
    
    if (backendHealth.ok()) {
      const body = await backendHealth.json();
      console.log('Backend response:', body);
    }
    
    // Check AI orchestrator health
    try {
      const aiHealth = await page.request.get('http://localhost:8001/health');
      console.log('AI Orchestrator health:', aiHealth.status());
      
      if (aiHealth.ok()) {
        const body = await aiHealth.json();
        console.log('AI Orchestrator response:', body);
      }
    } catch (e) {
      console.log('AI Orchestrator not accessible:', e);
    }
    
    // Check available chat endpoints
    const endpoints = [
      'http://localhost:8000/api/v1/chat',
      'http://localhost:8000/chat',
      'http://localhost:8001/chat',
      'http://localhost:8001/api/chat',
    ];
    
    console.log('\n=== Testing Chat Endpoints ===');
    for (const endpoint of endpoints) {
      try {
        const response = await page.request.post(endpoint, {
          data: {
            messages: [{ role: 'user', content: 'test' }],
            user_id: '1',
          },
          headers: {
            'Content-Type': 'application/json',
          },
          timeout: 5000,
        });
        console.log(`${endpoint} => ${response.status()}`);
      } catch (e: any) {
        console.log(`${endpoint} => Error: ${e.message}`);
      }
    }
  });
});
