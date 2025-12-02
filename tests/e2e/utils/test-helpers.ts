/**
 * Test helper utilities for E2E tests
 */

import { Page, expect } from '@playwright/test';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  metadata?: any;
}

export interface ToolInvocation {
  toolName: string;
  status: 'pending' | 'success' | 'error';
  result?: any;
}

/**
 * Wait for chat to be ready and connected
 */
export async function waitForChatReady(page: Page, timeout = 10000) {
  // Wait for chat button
  await page.waitForSelector('[data-testid="chat-button"]', { timeout });
  
  // Click to open chat
  await page.click('[data-testid="chat-button"]');
  
  // Wait for chat window
  await page.waitForSelector('[data-testid="chat-window"]', { timeout: 5000 });
  
  // Wait for WebSocket connection
  await page.waitForSelector(
    '[data-testid="connection-status"][data-status="connected"]',
    { timeout: 10000 }
  );
}

/**
 * Send a message and wait for agent response
 */
export async function sendMessage(
  page: Page,
  message: string,
  waitForResponse = true,
  timeout = 30000
) {
  const input = page.locator('[data-testid="chat-input"]');
  
  // Fill and send message
  await input.fill(message);
  await input.press('Enter');
  
  // Wait for message to appear
  await page.waitForSelector(`text="${message}"`, { timeout: 5000 });
  
  if (waitForResponse) {
    // Wait for agent response
    await page.waitForSelector('[data-role="assistant"]', { timeout });
  }
}

/**
 * Get all messages in the chat
 */
export async function getAllMessages(page: Page): Promise<ChatMessage[]> {
  const messages: ChatMessage[] = [];
  
  const userMessages = page.locator('[data-role="user"]');
  const userCount = await userMessages.count();
  
  for (let i = 0; i < userCount; i++) {
    const content = await userMessages.nth(i).textContent();
    messages.push({
      role: 'user',
      content: content || '',
    });
  }
  
  const assistantMessages = page.locator('[data-role="assistant"]');
  const assistantCount = await assistantMessages.count();
  
  for (let i = 0; i < assistantCount; i++) {
    const content = await assistantMessages.nth(i).textContent();
    messages.push({
      role: 'assistant',
      content: content || '',
    });
  }
  
  return messages;
}

/**
 * Get the last assistant message
 */
export async function getLastAssistantMessage(page: Page): Promise<string> {
  const messages = page.locator('[data-role="assistant"]');
  const count = await messages.count();
  
  if (count === 0) {
    return '';
  }
  
  const lastMessage = messages.nth(count - 1);
  return (await lastMessage.textContent()) || '';
}

/**
 * Get the last user message
 */
export async function getLastUserMessage(page: Page): Promise<string> {
  const messages = page.locator('[data-role="user"]');
  const count = await messages.count();
  
  if (count === 0) {
    return '';
  }
  
  const lastMessage = messages.nth(count - 1);
  return (await lastMessage.textContent()) || '';
}

/**
 * Wait for and click confirmation button
 */
export async function confirmAction(page: Page, timeout = 5000) {
  const confirmButton = page.locator('[data-testid="confirm-button"]');
  await expect(confirmButton).toBeVisible({ timeout });
  await confirmButton.click();
}

/**
 * Wait for and click cancel button
 */
export async function cancelAction(page: Page, timeout = 5000) {
  const cancelButton = page.locator('[data-testid="cancel-button"]');
  await expect(cancelButton).toBeVisible({ timeout });
  await cancelButton.click();
}

/**
 * Check if confirmation dialog is visible
 */
export async function hasConfirmationDialog(page: Page): Promise<boolean> {
  const dialog = page.locator('[data-testid="confirmation-dialog"]');
  return await dialog.isVisible();
}

/**
 * Get confirmation dialog text
 */
export async function getConfirmationText(page: Page): Promise<string> {
  const dialog = page.locator('[data-testid="confirmation-dialog"]');
  return (await dialog.textContent()) || '';
}

/**
 * Check if embedded component exists
 */
export async function hasEmbeddedComponent(
  page: Page,
  type: 'chart' | 'card' | 'table' | 'image'
): Promise<boolean> {
  const component = page.locator(`[data-component="${type}"]`);
  return (await component.count()) > 0;
}

/**
 * Get embedded component data
 */
export async function getEmbeddedComponentData(
  page: Page,
  type: 'chart' | 'card' | 'table' | 'image',
  index = 0
): Promise<any> {
  const component = page.locator(`[data-component="${type}"]`).nth(index);
  const dataAttr = await component.getAttribute('data-component-data');
  
  if (dataAttr) {
    try {
      return JSON.parse(dataAttr);
    } catch {
      return null;
    }
  }
  
  return null;
}

/**
 * Check if action buttons are visible
 */
export async function hasActionButtons(page: Page): Promise<boolean> {
  const buttons = page.locator('[data-testid="action-button"]');
  return (await buttons.count()) > 0;
}

/**
 * Click action button by text
 */
export async function clickActionButton(page: Page, buttonText: string) {
  const button = page.locator(`[data-testid="action-button"]:has-text("${buttonText}")`);
  await button.click();
}

/**
 * Get all action button texts
 */
export async function getActionButtonTexts(page: Page): Promise<string[]> {
  const buttons = page.locator('[data-testid="action-button"]');
  const count = await buttons.count();
  const texts: string[] = [];
  
  for (let i = 0; i < count; i++) {
    const text = await buttons.nth(i).textContent();
    if (text) {
      texts.push(text);
    }
  }
  
  return texts;
}

/**
 * Check if tool invocation card is visible
 */
export async function hasToolInvocationCard(page: Page): Promise<boolean> {
  const card = page.locator('[data-testid="tool-invocation-card"]');
  return (await card.count()) > 0;
}

/**
 * Get tool invocation details
 */
export async function getToolInvocation(page: Page, index = 0): Promise<ToolInvocation | null> {
  const cards = page.locator('[data-testid="tool-invocation-card"]');
  const count = await cards.count();
  
  if (index >= count) {
    return null;
  }
  
  const card = cards.nth(index);
  const toolName = await card.locator('[data-testid="tool-name"]').textContent();
  const statusAttr = await card.getAttribute('data-tool-status');
  
  return {
    toolName: toolName || '',
    status: (statusAttr as any) || 'pending',
  };
}

/**
 * Wait for tool execution to complete
 */
export async function waitForToolCompletion(
  page: Page,
  toolName?: string,
  timeout = 30000
) {
  const selector = toolName
    ? `[data-testid="tool-invocation-card"][data-tool-name="${toolName}"][data-tool-status="success"]`
    : '[data-testid="tool-invocation-card"][data-tool-status="success"]';
  
  await page.waitForSelector(selector, { timeout });
}

/**
 * Check connection status
 */
export async function getConnectionStatus(page: Page): Promise<string> {
  const status = page.locator('[data-testid="connection-status"]');
  return (await status.getAttribute('data-status')) || 'disconnected';
}

/**
 * Wait for connection to be established
 */
export async function waitForConnection(page: Page, timeout = 10000) {
  await page.waitForSelector(
    '[data-testid="connection-status"][data-status="connected"]',
    { timeout }
  );
}

/**
 * Clear chat history
 */
export async function clearChat(page: Page) {
  const clearButton = page.locator('[data-testid="clear-chat-button"]');
  
  if (await clearButton.isVisible()) {
    await clearButton.click();
    
    // Confirm if dialog appears
    const confirmButton = page.locator('[data-testid="confirm-clear-button"]');
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
  }
}

/**
 * Take screenshot with timestamp
 */
export async function takeTimestampedScreenshot(page: Page, name: string) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  await page.screenshot({
    path: `screenshots/${name}-${timestamp}.png`,
    fullPage: true,
  });
}

/**
 * Wait for loading to complete
 */
export async function waitForLoadingComplete(page: Page, timeout = 10000) {
  // Wait for any loading indicators to disappear
  await page.waitForSelector('[data-testid="loading-indicator"]', {
    state: 'hidden',
    timeout,
  }).catch(() => {
    // Ignore if loading indicator doesn't exist
  });
}

/**
 * Check if error message is displayed
 */
export async function hasErrorMessage(page: Page): Promise<boolean> {
  const error = page.locator('[data-testid="error-message"]');
  return await error.isVisible();
}

/**
 * Get error message text
 */
export async function getErrorMessage(page: Page): Promise<string> {
  const error = page.locator('[data-testid="error-message"]');
  return (await error.textContent()) || '';
}

/**
 * Login as dev user (for testing)
 */
export async function loginAsDevUser(page: Page) {
  // Check if already logged in
  const logoutButton = page.locator('[data-testid="logout-button"]');
  if (await logoutButton.isVisible()) {
    return; // Already logged in
  }
  
  // Navigate to login
  await page.goto('/');
  
  // Click Google login (in dev mode, should auto-login)
  const loginButton = page.locator('[data-testid="google-login-button"]');
  if (await loginButton.isVisible()) {
    await loginButton.click();
    
    // Wait for redirect to dashboard
    await page.waitForURL('**/dashboard', { timeout: 10000 });
  }
}

/**
 * Navigate to specific page
 */
export async function navigateTo(page: Page, path: string) {
  await page.goto(path);
  await page.waitForLoadState('networkidle');
}

/**
 * Assert message contains text
 */
export async function assertMessageContains(
  page: Page,
  text: string | RegExp,
  role: 'user' | 'assistant' = 'assistant'
) {
  const lastMessage = role === 'assistant'
    ? await getLastAssistantMessage(page)
    : await getLastUserMessage(page);
  
  if (typeof text === 'string') {
    expect(lastMessage).toContain(text);
  } else {
    expect(lastMessage).toMatch(text);
  }
}

/**
 * Wait for specific message pattern
 */
export async function waitForMessagePattern(
  page: Page,
  pattern: RegExp,
  timeout = 30000
) {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    const lastMessage = await getLastAssistantMessage(page);
    if (pattern.test(lastMessage)) {
      return true;
    }
    
    await page.waitForTimeout(500);
  }
  
  throw new Error(`Timeout waiting for message pattern: ${pattern}`);
}

/**
 * Get credit balance (if displayed)
 */
export async function getCreditBalance(page: Page): Promise<number | null> {
  const creditDisplay = page.locator('[data-testid="credit-balance"]');
  
  if (await creditDisplay.isVisible()) {
    const text = await creditDisplay.textContent();
    const match = text?.match(/\d+/);
    return match ? parseInt(match[0]) : null;
  }
  
  return null;
}
