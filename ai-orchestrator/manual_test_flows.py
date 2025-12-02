"""
Manual Test Flows for ReAct Agent v2

This script demonstrates the key flows that should be tested manually:
1. Clear task (automatic execution)
2. Ambiguous task (request selection)
3. Important operation (request confirmation)
4. Complex task (multiple human interventions)
"""

import asyncio
import json
# Note: Imports commented out as this is a documentation/guide script
# from app.core.react_agent import ReActAgent
# from app.services.gemini_client import GeminiClient
# from app.services.mcp_client import MCPClient


async def test_clear_task():
    """
    Test 1: Clear Task (Automatic Execution)
    
    Expected behavior:
    - Agent understands the intent clearly
    - No human intervention required
    - Executes tools automatically
    - Returns final result
    """
    print("\n" + "="*80)
    print("TEST 1: Clear Task (Automatic Execution)")
    print("="*80)
    
    agent = ReActAgent()
    
    # Example: "Show me my campaign performance for last week"
    message = "Show me my campaign performance for last week"
    user_id = "test_user_123"
    session_id = "test_session_1"
    
    print(f"\nUser Message: {message}")
    print("\nExpected: Agent should automatically fetch data and return results")
    print("No human intervention should be required\n")
    
    try:
        response = await agent.process_message(
            user_message=message,
            user_id=user_id,
            session_id=session_id,
        )
        
        print(f"Response Status: {response.status}")
        print(f"Response Message: {response.message[:200]}...")
        
        if response.status == "completed":
            print("✅ PASS: Task completed automatically")
        else:
            print(f"❌ FAIL: Expected 'completed', got '{response.status}'")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")


async def test_ambiguous_task():
    """
    Test 2: Ambiguous Task (Request Selection)
    
    Expected behavior:
    - Agent identifies ambiguity
    - Returns status "waiting_for_user"
    - Provides options for user to choose
    - Includes "Other" and "Cancel" options
    """
    print("\n" + "="*80)
    print("TEST 2: Ambiguous Task (Request Selection)")
    print("="*80)
    
    agent = ReActAgent()
    
    # Example: "Generate an ad creative" (missing style, platform, etc.)
    message = "Generate an ad creative"
    user_id = "test_user_123"
    session_id = "test_session_2"
    
    print(f"\nUser Message: {message}")
    print("\nExpected: Agent should ask for clarification with options")
    print("Should include preset options + 'Other' + 'Cancel'\n")
    
    try:
        response = await agent.process_message(
            user_message=message,
            user_id=user_id,
            session_id=session_id,
        )
        
        print(f"Response Status: {response.status}")
        print(f"Response Message: {response.message}")
        
        if response.status == "waiting_for_user":
            print("✅ PASS: Agent is waiting for user input")
            
            if response.options:
                print(f"\nOptions provided: {len(response.options)}")
                for i, option in enumerate(response.options, 1):
                    print(f"  {i}. {option}")
                    
                # Check for "Other" and "Cancel"
                has_other = any("other" in str(opt).lower() for opt in response.options)
                has_cancel = any("cancel" in str(opt).lower() for opt in response.options)
                
                if has_other and has_cancel:
                    print("✅ PASS: Includes 'Other' and 'Cancel' options")
                else:
                    print(f"❌ FAIL: Missing 'Other' or 'Cancel' option")
            else:
                print("❌ FAIL: No options provided")
        else:
            print(f"❌ FAIL: Expected 'waiting_for_user', got '{response.status}'")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")


async def test_important_operation():
    """
    Test 3: Important Operation (Request Confirmation)
    
    Expected behavior:
    - Agent identifies operation involves spending/risk
    - Returns status "waiting_for_user"
    - Shows operation details
    - Asks for confirmation
    """
    print("\n" + "="*80)
    print("TEST 3: Important Operation (Request Confirmation)")
    print("="*80)
    
    agent = ReActAgent()
    
    # Example: "Create a campaign with $1000 budget"
    message = "Create a campaign with $1000 budget targeting US users"
    user_id = "test_user_123"
    session_id = "test_session_3"
    
    print(f"\nUser Message: {message}")
    print("\nExpected: Agent should prepare campaign and ask for confirmation")
    print("Should show budget, targeting, and other details\n")
    
    try:
        response = await agent.process_message(
            user_message=message,
            user_id=user_id,
            session_id=session_id,
        )
        
        print(f"Response Status: {response.status}")
        print(f"Response Message: {response.message}")
        
        if response.status == "waiting_for_user":
            print("✅ PASS: Agent is requesting confirmation")
            
            # Check if message contains budget info
            if "$1000" in response.message or "1000" in response.message:
                print("✅ PASS: Confirmation includes budget details")
            else:
                print("⚠️  WARNING: Budget details not clearly shown")
                
        else:
            print(f"❌ FAIL: Expected 'waiting_for_user', got '{response.status}'")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")


async def test_complex_task():
    """
    Test 4: Complex Task (Multiple Human Interventions)
    
    Expected behavior:
    - Agent breaks down complex task
    - Multiple rounds of human intervention
    - Each intervention is appropriate (selection or confirmation)
    - Final result after all interventions
    """
    print("\n" + "="*80)
    print("TEST 4: Complex Task (Multiple Human Interventions)")
    print("="*80)
    
    agent = ReActAgent()
    
    # Example: "Create a complete campaign with creative and landing page"
    message = "Create a complete campaign with creative and landing page for my product"
    user_id = "test_user_123"
    session_id = "test_session_4"
    
    print(f"\nUser Message: {message}")
    print("\nExpected: Agent should handle multiple steps with interventions")
    print("May ask for: product URL, creative style, budget, etc.\n")
    
    try:
        # First interaction
        response = await agent.process_message(
            user_message=message,
            user_id=user_id,
            session_id=session_id,
        )
        
        print(f"Round 1 - Status: {response.status}")
        print(f"Round 1 - Message: {response.message[:200]}...")
        
        if response.status == "waiting_for_user":
            print("✅ PASS: Agent is requesting first input")
            
            # Simulate user providing product URL
            print("\n[Simulating user input: product URL]")
            response = await agent.process_message(
                user_message="https://example.com/product",
                user_id=user_id,
                session_id=session_id,
            )
            
            print(f"\nRound 2 - Status: {response.status}")
            print(f"Round 2 - Message: {response.message[:200]}...")
            
            if response.status == "waiting_for_user":
                print("✅ PASS: Agent is requesting second input")
            elif response.status == "completed":
                print("✅ PASS: Task completed after one intervention")
            else:
                print(f"⚠️  Status: {response.status}")
        else:
            print(f"⚠️  First response status: {response.status}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")


async def main():
    """Run all manual test flows"""
    print("\n" + "="*80)
    print("ReAct Agent v2 - Manual Test Flows")
    print("="*80)
    print("\nThese tests demonstrate the key flows of the ReAct Agent:")
    print("1. Clear tasks execute automatically")
    print("2. Ambiguous tasks request selection")
    print("3. Important operations request confirmation")
    print("4. Complex tasks handle multiple interventions")
    print("\n" + "="*80)
    
    # Note: These tests require actual services to be running
    # For now, we'll just document the expected behavior
    
    print("\n⚠️  NOTE: These tests require the following services to be running:")
    print("  - Redis (for state management)")
    print("  - Backend MCP Server (for tool execution)")
    print("  - Gemini API (for LLM calls)")
    print("\nTo run these tests:")
    print("  1. Start Redis: redis-server")
    print("  2. Start Backend: cd backend && uvicorn app.main:app --reload")
    print("  3. Start AI Orchestrator: cd ai-orchestrator && uvicorn app.main:app --reload --port 8001")
    print("  4. Run this script: python manual_test_flows.py")
    
    # Uncomment to run actual tests (requires services)
    # await test_clear_task()
    # await test_ambiguous_task()
    # await test_important_operation()
    # await test_complex_task()
    
    print("\n" + "="*80)
    print("Manual Testing Guide")
    print("="*80)
    print("""
To manually test the system:

1. Start all services (Backend, AI Orchestrator, Frontend)

2. Open the frontend chat interface

3. Test Clear Task:
   - Message: "Show me my campaign performance"
   - Expected: Automatic execution, no prompts
   
4. Test Ambiguous Task:
   - Message: "Generate an ad creative"
   - Expected: Options for style, platform, etc.
   
5. Test Important Operation:
   - Message: "Create a campaign with $500 budget"
   - Expected: Confirmation request with details
   
6. Test Complex Task:
   - Message: "Create a complete campaign with creative"
   - Expected: Multiple prompts for product URL, style, budget, etc.

7. Verify Human-in-the-Loop:
   - Options include preset choices + "Other" + "Cancel"
   - "Other" allows free text input
   - "Cancel" stops the operation
   
8. Verify State Management:
   - Agent remembers context across interactions
   - Can resume after user input
   - Handles errors gracefully
""")


if __name__ == "__main__":
    asyncio.run(main())
