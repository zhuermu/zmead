# Human-in-the-Loop Implementation Summary

## Overview

This document summarizes the implementation of the Human-in-the-Loop (HITL) feature for the ReAct Agent, which enables intelligent user interaction during agent execution.

## Implementation Date

December 2, 2025

## Components Implemented

### 1. Evaluator (`app/core/evaluator.py`)

The Evaluator component determines when human input is needed during agent execution.

**Key Features:**
- **High-Risk Operation Detection**: Automatically identifies operations that require confirmation (e.g., `create_campaign`, `update_budget`, `delete_campaign`)
- **Spending Detection**: Flags operations involving significant spending (> $50)
- **Missing Parameter Detection**: Identifies when required parameters are missing
- **Ambiguity Detection**: Uses LLM to detect unclear or ambiguous parameters
- **Confidence Threshold**: Configurable auto-approval threshold (default: 0.9)

**Confirmation Types:**
- `NONE`: No confirmation needed
- `CONFIRM`: Yes/No confirmation
- `SELECT`: Choose from predefined options
- `INPUT`: Free-form text input

**Example Usage:**
```python
evaluator = Evaluator()

result = await evaluator.evaluate_plan(
    plan=plan,
    user_message="Create a campaign with $100 budget",
    execution_history=[],
)

if result.needs_human_input:
    # Handle user input request
    print(result.question)
```

### 2. HumanInLoopHandler (`app/core/human_in_loop.py`)

The HumanInLoopHandler manages the creation and processing of user input requests.

**Key Features:**
- **Request Creation**: Formats requests for frontend rendering
- **Response Processing**: Parses and validates user responses
- **Option Management**: Automatically adds "Other" and "Cancel" options
- **Cancellation Handling**: Properly handles user cancellations
- **Custom Input Support**: Allows users to provide custom values for "Other" option

**Request Types:**
1. **Confirmation Request**: Yes/No questions with suggested actions
2. **Selection Request**: Multiple choice with predefined options
3. **Input Request**: Free-form text input with validation

**Example Usage:**
```python
handler = HumanInLoopHandler()

# Create confirmation request
request = handler.create_confirmation_request(
    question="Create campaign with $100 budget?",
    suggested_action={"action": "create_campaign", "params": {...}},
)

# Process user response
response = handler.process_user_response(
    request=request,
    user_input={"value": "yes"},
)

if response.cancelled:
    # User cancelled
    pass
elif response.value:
    # User confirmed
    pass
```

### 3. ReAct Agent Integration (`app/core/react_agent.py`)

The ReAct Agent was updated to integrate the Evaluator and HumanInLoopHandler.

**Changes Made:**
1. Added `evaluator` and `human_in_loop_handler` to constructor
2. Integrated evaluation step after planning in the ReAct loop
3. Added state management for user input requests
4. Implemented `continue_with_user_input()` method for resuming execution
5. Added proper handling of user responses (confirmation, selection, cancellation)

**Execution Flow:**
```
1. User sends message
2. Agent plans next action
3. Evaluator checks if human input is needed
4. If needed:
   - Create user input request
   - Save state
   - Return request to frontend
   - Wait for user response
5. User provides input
6. Agent processes response
7. Continue execution or cancel
```

## User Experience

### Scenario 1: High-Risk Operation (Confirmation)

```
User: "Create a campaign with $100 budget"

Agent: "Create campaign with the following settings:
       - Budget: $100/day
       - Objective: Conversions
       
       Confirm?
       ✅ 确认
       ❌ 取消"

User: [Clicks 确认]

Agent: "✅ Campaign created successfully!"
```

### Scenario 2: Ambiguous Parameter (Selection)

```
User: "Generate an ad image"

Agent: "请选择素材风格：
       1️⃣ 现代简约 - 简洁、专业的现代风格
       2️⃣ 活力多彩 - 鲜艳、充满活力的色彩
       3️⃣ 高端奢华 - 精致、高端的奢华感
       ➕ 其他 - 自定义输入
       ❌ 取消"

User: [Selects 现代简约]

Agent: "Generating image with modern style..."
```

### Scenario 3: Missing Parameter (Input)

```
User: "Generate an image"

Agent: "请提供产品信息或产品链接：
       [Input field]
       ❌ 取消"

User: [Enters "https://example.com/product"]

Agent: "Extracting product information..."
```

## Configuration

### Evaluator Configuration

```python
evaluator = Evaluator(
    gemini_client=gemini_client,
    auto_approve_threshold=0.9,  # Confidence threshold for auto-approval
)
```

### High-Risk Operations

The following operations always require confirmation:
- `create_campaign`
- `update_campaign`
- `pause_campaign`
- `delete_campaign`
- `update_budget`
- `disconnect_ad_account`

### Spending Threshold

Operations involving spending > $50 require confirmation.

### Ambiguous Parameters

The following parameters are checked for ambiguity:
- `style` (creative style)
- `template` (landing page template)
- `targeting` (audience targeting)
- `objective` (campaign objective)
- `placement` (ad placement)

## Testing

A comprehensive test suite was created in `tests/test_human_in_loop.py` covering:

### Evaluator Tests
- High-risk operation detection
- Spending operation detection
- Missing parameter detection
- Ambiguous parameter detection
- Complete task handling

### HumanInLoopHandler Tests
- Confirmation request creation
- Selection request creation
- Input request creation
- Response processing (yes/no/cancel)
- Selection with options
- Custom value handling
- Empty input handling
- Frontend formatting

## API Changes

### AgentResponse

Added new fields:
```python
@dataclass
class AgentResponse:
    status: AgentStatus
    message: str | None = None
    data: dict[str, Any] | None = None
    requires_user_input: bool = False  # NEW
    user_input_request: dict[str, Any] | None = None  # NEW
    error: str | None = None
```

### AgentState

Added new fields:
```python
@dataclass
class AgentState:
    # ... existing fields ...
    waiting_for_user_input: bool = False  # NEW
    user_input_request: dict[str, Any] | None = None  # NEW
```

## Frontend Integration

The frontend should handle the following response format:

```json
{
  "status": "waiting_for_user",
  "message": "Confirm this action?",
  "requires_user_input": true,
  "user_input_request": {
    "type": "confirmation",
    "question": "Create campaign with $100 budget?",
    "options": [
      {
        "value": "yes",
        "label": "✅ 确认",
        "description": "继续执行",
        "primary": true
      },
      {
        "value": "no",
        "label": "❌ 取消",
        "description": "取消此操作",
        "primary": false
      }
    ],
    "metadata": {
      "suggested_action": {
        "action": "create_campaign",
        "parameters": {...}
      },
      "reason": "high_risk"
    }
  }
}
```

## Benefits

1. **Safety**: Prevents accidental execution of high-risk operations
2. **Clarity**: Resolves ambiguous user intents before execution
3. **Flexibility**: Allows users to provide custom values when needed
4. **User Control**: Users can cancel operations at any time
5. **Transparency**: Shows exactly what will be executed before confirmation

## Future Enhancements

1. **User Preferences**: Store user preferences for auto-approval
2. **Learning**: Learn from user confirmations to improve auto-approval
3. **Batch Operations**: Support confirming multiple operations at once
4. **Undo**: Allow users to undo recently confirmed operations
5. **Audit Trail**: Log all confirmations for compliance

## Requirements Validated

This implementation validates the following requirements from the design document:

- **Requirement 5.1**: ✅ System automatically executes clear, low-risk tasks
- **Requirement 5.2**: ✅ System requests confirmation for spending/important operations
- **Requirement 5.3**: ✅ System provides options for ambiguous parameters
- **Requirement 5.4**: ✅ System includes preset options + "Other" + "Cancel"
- **Requirement 5.5**: ✅ System allows free input when user selects "Other"

## Conclusion

The Human-in-the-Loop implementation successfully adds intelligent user interaction to the ReAct Agent, balancing automation with user control. The system now:

- Automatically executes clear, low-risk operations
- Requests confirmation for high-risk or spending operations
- Resolves ambiguity through user selection
- Allows custom input when needed
- Handles cancellations gracefully

This creates a safer, more user-friendly AI agent experience while maintaining the benefits of automation.
