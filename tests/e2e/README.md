# AAE E2E Tests - AI Agent Capabilities

This directory contains end-to-end tests for the AAE AI Agent using Playwright. The tests focus on validating the agent's capabilities across different domains.

## Test Coverage

### 1. Creative Generation Capabilities
- Generate ad creatives from product descriptions
- Handle creative generation with credit confirmations
- Analyze competitor creatives
- Generate creative variants

### 2. Campaign Management Capabilities
- Create campaigns with confirmation
- List active campaigns
- Pause/resume campaigns
- Optimize campaign budgets
- Handle bulk operations

### 3. Performance Analytics Capabilities
- Analyze campaign performance
- Detect anomalies in ad data
- Provide performance recommendations
- Generate performance reports

### 4. Landing Page Capabilities
- Generate landing pages with confirmation
- List landing pages
- Analyze landing page performance
- A/B testing management

### 5. Market Intelligence Capabilities
- Analyze market trends
- Track competitors
- Provide audience insights
- Generate market reports

### 6. Error Handling
- Handle invalid requests gracefully
- Request missing parameters
- Handle cancellations
- Handle insufficient credits

### 7. Multi-step Conversations
- Maintain context across messages
- Handle clarification requests
- Support follow-up questions

### 8. Tool Execution
- Show tool invocation status
- Handle tool execution errors
- Display tool results

### 9. Human-in-the-Loop
- Request confirmations for destructive actions
- Request input for missing parameters
- Provide options for user selection

## Prerequisites

1. **Services Running**:
   - Frontend: `http://localhost:3000`
   - Backend: `http://localhost:8000`
   - AI Orchestrator: `http://localhost:8001`
   - Database: MySQL running
   - Redis: Running

2. **Test Data**:
   - Dev user account created
   - At least one ad account connected
   - Some test campaigns and creatives

3. **Environment Variables**:
   ```bash
   BASE_URL=http://localhost:3000
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

## Installation

```bash
cd tests/e2e
npm install
npm run install  # Install Playwright browsers
```

## Running Tests

### Run All Tests
```bash
npm test
```

### Run Tests by Category
```bash
# Creative generation tests
npm run test:creative

# Campaign management tests
npm run test:campaign

# Performance analytics tests
npm run test:performance

# Landing page tests
npm run test:landing

# Market intelligence tests
npm run test:market

# Error handling tests
npm run test:errors

# Multi-step conversation tests
npm run test:conversation

# Tool execution tests
npm run test:tools

# Human-in-the-loop tests
npm run test:human-loop
```

### Debug Mode
```bash
# Run with browser visible
npm run test:headed

# Run with Playwright Inspector
npm run test:debug

# Run with UI mode
npm run test:ui
```

### View Test Report
```bash
npm run report
```

## Test Architecture

### Helper Functions

- `waitForChatReady(page)`: Opens chat and waits for WebSocket connection
- `sendMessageAndWaitForResponse(page, message)`: Sends message and waits for agent response
- `getLastAssistantMessage(page)`: Retrieves the last assistant message

### Test Data Attributes

The tests rely on specific data attributes in the frontend components:

- `data-testid="chat-button"`: Chat floating button
- `data-testid="chat-window"`: Chat window container
- `data-testid="chat-input"`: Message input field
- `data-testid="connection-status"`: WebSocket connection status
- `data-role="assistant"`: Assistant message bubbles
- `data-role="user"`: User message bubbles
- `data-component="chart|card|table"`: Embedded components
- `data-testid="confirm-button"`: Confirmation button
- `data-testid="cancel-button"`: Cancel button
- `data-testid="action-button"`: Action buttons in messages
- `data-testid="tool-invocation-card"`: Tool execution status

### Frontend Requirements

To make these tests work, ensure your frontend components include the appropriate data attributes:

```tsx
// ChatButton.tsx
<button data-testid="chat-button">...</button>

// ChatWindow.tsx
<div data-testid="chat-window">...</div>

// ConnectionStatus.tsx
<div data-testid="connection-status" data-status={status}>...</div>

// MessageBubble.tsx
<div data-role={message.role}>...</div>

// EmbeddedChart.tsx
<div data-component="chart">...</div>

// EmbeddedCard.tsx
<div data-component="card">...</div>

// ActionButton.tsx
<button data-testid="action-button">...</button>

// ConfirmationDialog.tsx
<button data-testid="confirm-button">Confirm</button>
<button data-testid="cancel-button">Cancel</button>
```

## Test Scenarios

### Scenario 1: Creative Generation Flow
1. User opens chat
2. User requests creative generation
3. Agent shows confirmation (credit cost)
4. User confirms
5. Agent generates creative
6. Agent displays creative in embedded card

### Scenario 2: Campaign Creation Flow
1. User requests campaign creation
2. Agent asks for missing parameters (budget, platform)
3. User provides parameters
4. Agent shows confirmation with details
5. User confirms
6. Agent creates campaign
7. Agent shows success message

### Scenario 3: Performance Analysis Flow
1. User requests performance analysis
2. Agent fetches campaign data
3. Agent analyzes metrics
4. Agent displays charts and recommendations
5. User clicks action button
6. Agent executes recommended action

### Scenario 4: Error Handling Flow
1. User makes invalid request
2. Agent detects error
3. Agent provides helpful error message
4. Agent suggests alternative actions

## Debugging Tips

1. **WebSocket Connection Issues**:
   - Check if backend WebSocket endpoint is running
   - Verify authentication token is valid
   - Check browser console for connection errors

2. **Timeout Issues**:
   - Increase `WS_TIMEOUT` constant
   - Check if AI Orchestrator is responding
   - Verify Gemini API key is valid

3. **Element Not Found**:
   - Verify data attributes are present in components
   - Check if component is rendered conditionally
   - Use `page.pause()` to inspect page state

4. **Test Flakiness**:
   - Add explicit waits for dynamic content
   - Check for race conditions
   - Verify test data is consistent

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Start services
        run: docker-compose up -d
      
      - name: Wait for services
        run: |
          timeout 60 bash -c 'until curl -f http://localhost:3000; do sleep 2; done'
      
      - name: Install dependencies
        run: |
          cd tests/e2e
          npm install
          npm run install
      
      - name: Run tests
        run: |
          cd tests/e2e
          npm test
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: tests/e2e/playwright-report/
```

## Best Practices

1. **Test Independence**: Each test should be independent and not rely on other tests
2. **Clean State**: Use `beforeEach` to ensure clean state
3. **Explicit Waits**: Always wait for elements explicitly, avoid fixed timeouts
4. **Meaningful Assertions**: Assert on meaningful content, not just presence
5. **Error Messages**: Include helpful error messages in assertions
6. **Test Data**: Use realistic test data that matches production scenarios
7. **Cleanup**: Clean up test data after tests complete

## Troubleshooting

### Common Issues

1. **"Connection timeout"**
   - Ensure all services are running
   - Check network connectivity
   - Verify WebSocket endpoint is accessible

2. **"Element not found"**
   - Verify component has correct data attribute
   - Check if element is visible (not hidden by CSS)
   - Increase timeout if element loads slowly

3. **"Authentication failed"**
   - Verify dev user exists in database
   - Check JWT token generation
   - Verify auth middleware is working

4. **"Agent not responding"**
   - Check AI Orchestrator logs
   - Verify Gemini API key is valid
   - Check MCP tools are registered

## Contributing

When adding new tests:

1. Follow existing test structure
2. Add appropriate data attributes to components
3. Document new test scenarios
4. Update this README with new test categories
5. Ensure tests pass locally before committing

## License

MIT
