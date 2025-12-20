/**
 * Playwright test script for image generation observation event
 * Tests the unified attachment architecture fix
 */

import { chromium } from 'playwright';

async function testImageGeneration() {
  console.log('🚀 Starting Playwright test...\n');

  const browser = await chromium.launch({
    headless: false,  // Show browser for debugging
    slowMo: 500,      // Slow down actions for visibility
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
  });

  const page = await context.newPage();

  // Enable console logging from the page
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.error('❌ Browser console error:', msg.text());
    }
  });

  // Listen to network requests for SSE events
  const sseEvents = [];
  page.on('response', async response => {
    const url = response.url();
    if (url.includes('/api/chat') && response.headers()['content-type']?.includes('text/event-stream')) {
      console.log('📡 SSE Connection established');

      // Try to capture response body (SSE events)
      try {
        const body = await response.text();
        const lines = body.split('\n').filter(line => line.startsWith('data:'));

        for (const line of lines) {
          try {
            const data = JSON.parse(line.substring(5).trim());
            sseEvents.push(data);

            if (data.type === 'observation') {
              console.log('📦 Observation event received:', {
                tool: data.tool,
                success: data.success,
                hasAttachments: !!data.attachments,
                attachmentCount: data.attachments?.length || 0,
              });

              if (data.attachments) {
                console.log('✅ Attachments in observation event:',
                  data.attachments.map(a => ({
                    id: a.id,
                    filename: a.filename,
                    type: a.type,
                    s3Url: a.s3Url?.substring(0, 50) + '...',
                  }))
                );
              }
            } else if (data.type === 'attachments') {
              console.log('⚠️  Separate attachments event (legacy):', {
                count: data.attachments?.length || 0,
              });
            }
          } catch (e) {
            // Ignore parsing errors for non-JSON lines
          }
        }
      } catch (e) {
        console.log('Could not capture SSE body:', e.message);
      }
    }
  });

  try {
    console.log('🌐 Navigating to http://localhost:3000...\n');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });

    // Wait for page to load
    await page.waitForTimeout(2000);

    // Take initial screenshot
    await page.screenshot({ path: '/tmp/test_1_initial.png' });
    console.log('📸 Screenshot saved: /tmp/test_1_initial.png\n');

    // Check if we need to login
    const loginButton = page.locator('button:has-text("登录"), button:has-text("Login")');
    if (await loginButton.count() > 0) {
      console.log('⚠️  Need to login first. Please ensure you are logged in.\n');
      console.log('Waiting 10 seconds for manual login...\n');
      await page.waitForTimeout(10000);
    }

    // Find the chat input
    const chatInput = page.locator('textarea, input[type="text"]').first();
    await chatInput.waitFor({ state: 'visible', timeout: 10000 });

    console.log('💬 Found chat input, entering test message...\n');

    // Enter test message for image generation
    await chatInput.fill('生成一张产品图片');
    await page.waitForTimeout(500);

    // Take screenshot before sending
    await page.screenshot({ path: '/tmp/test_2_before_send.png' });
    console.log('📸 Screenshot saved: /tmp/test_2_before_send.png\n');

    // Send message (look for send button or press Enter)
    const sendButton = page.locator('button[type="submit"], button:has-text("发送"), button:has-text("Send")').first();

    if (await sendButton.count() > 0) {
      console.log('📤 Clicking send button...\n');
      await sendButton.click();
    } else {
      console.log('📤 Pressing Enter to send...\n');
      await chatInput.press('Enter');
    }

    // Wait for AI response
    console.log('⏳ Waiting for AI agent response (up to 30 seconds)...\n');

    // Wait for agent status indicators
    await page.waitForTimeout(5000);

    // Look for observation events or attachments in the UI
    const imageElements = page.locator('img[alt*="image"], img[src*="s3"], img[src*="presigned"]');

    // Wait for images to appear (up to 25 more seconds)
    try {
      await imageElements.first().waitFor({ state: 'visible', timeout: 25000 });
      console.log('✅ Image element appeared in UI!\n');

      const imageCount = await imageElements.count();
      console.log(`📊 Total images found: ${imageCount}\n`);

    } catch (e) {
      console.log('⚠️  No images appeared in UI within timeout\n');
    }

    // Wait a bit more for full rendering
    await page.waitForTimeout(3000);

    // Take final screenshot
    await page.screenshot({ path: '/tmp/test_3_after_response.png', fullPage: true });
    console.log('📸 Screenshot saved: /tmp/test_3_after_response.png\n');

    // Check for attachment display components
    const attachmentDisplay = page.locator('[class*="attachment"], [class*="image-preview"], [class*="generated"]');
    const attachmentCount = await attachmentDisplay.count();
    console.log(`📎 Attachment display components found: ${attachmentCount}\n`);

    // Summary
    console.log('📋 Test Summary:');
    console.log('================');
    console.log(`Total SSE events captured: ${sseEvents.length}`);
    console.log(`Observation events with attachments: ${sseEvents.filter(e => e.type === 'observation' && e.attachments).length}`);
    console.log(`Legacy attachment events: ${sseEvents.filter(e => e.type === 'attachments').length}`);
    console.log(`Images in UI: ${await imageElements.count()}`);
    console.log(`Attachment components: ${attachmentCount}`);
    console.log('\n✅ Test completed!\n');

    // Keep browser open for inspection
    console.log('Browser will remain open for 10 seconds for inspection...\n');
    await page.waitForTimeout(10000);

  } catch (error) {
    console.error('❌ Test failed:', error);
    await page.screenshot({ path: '/tmp/test_error.png' });
    console.log('📸 Error screenshot saved: /tmp/test_error.png\n');
  } finally {
    await browser.close();
    console.log('🏁 Browser closed\n');
  }
}

// Run the test
testImageGeneration().catch(console.error);
