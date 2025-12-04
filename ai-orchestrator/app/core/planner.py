"""Planner component for ReAct Agent.

The Planner is responsible for:
1. Understanding user intent
2. Deciding what action to take next
3. Selecting appropriate tools
4. Generating reasoning (thoughts)

It uses Gemini to analyze the current state and plan the next step.
Supports streaming output for real-time thought process visibility.
"""

import json
from typing import Any, AsyncIterator

import structlog
from pydantic import BaseModel, Field

from app.services.gemini_client import GeminiClient, GeminiError
from app.tools.base import AgentTool

logger = structlog.get_logger(__name__)


class PlanAction(BaseModel):
    """Planned action from the planner."""

    thought: str = Field(description="Agent's reasoning about what to do next")
    action: str | None = Field(
        default=None,
        description="Tool name to call, or None if task is complete",
    )
    action_input: dict[str, Any] | None = Field(
        default=None,
        description="Parameters for the tool",
    )
    is_complete: bool = Field(
        default=False,
        description="Whether the task is complete",
    )
    final_answer: str | None = Field(
        default=None,
        description="Final answer if task is complete",
    )


class Planner:
    """Planner component for the ReAct Agent.

    The planner uses Gemini to:
    - Understand user intent
    - Analyze current execution state
    - Decide what action to take next
    - Select appropriate tools

    Example:
        planner = Planner(gemini_client)

        plan = await planner.plan_next_action(
            user_message="Generate an ad image",
            available_tools=tools,
            execution_history=history,
        )

        if plan.is_complete:
            print(plan.final_answer)
        else:
            # Execute plan.action with plan.action_input
            pass
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        """Initialize the planner.

        Args:
            gemini_client: Gemini client for LLM calls
        """
        self.gemini_client = gemini_client or GeminiClient()
        logger.info("planner_initialized")

    async def plan_next_action(
        self,
        user_message: str,
        available_tools: list[AgentTool],
        execution_history: list[dict[str, Any]] | None = None,
        user_id: str | None = None,
    ) -> PlanAction:
        """Plan the next action based on current state.

        Args:
            user_message: User's original message
            available_tools: List of available tools
            execution_history: Previous execution steps
            user_id: User ID for context

        Returns:
            PlanAction with next step

        Raises:
            GeminiError: If planning fails
        """
        log = logger.bind(
            user_id=user_id,
            tool_count=len(available_tools),
            history_length=len(execution_history) if execution_history else 0,
        )
        log.info("plan_next_action_start")

        try:
            # Build planning prompt
            prompt = self._build_planning_prompt(
                user_message=user_message,
                available_tools=available_tools,
                execution_history=execution_history,
            )

            # Get plan from Gemini using structured output
            plan = await self.gemini_client.structured_output(
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt(),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                schema=PlanAction,
                temperature=0.3,  # Lower temperature for more focused planning
            )

            log.info(
                "plan_next_action_complete",
                has_action=plan.action is not None,
                is_complete=plan.is_complete,
            )

            return plan

        except GeminiError as e:
            log.error("planning_error", error=str(e))
            raise

    async def plan_next_action_stream(
        self,
        user_message: str,
        available_tools: list[AgentTool],
        execution_history: list[dict[str, Any]] | None = None,
        user_id: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Plan the next action with streaming thought output.

        This method streams the agent's thinking process in real-time,
        allowing users to see how the agent reasons about the task.

        Args:
            user_message: User's original message
            available_tools: List of available tools
            execution_history: Previous execution steps
            user_id: User ID for context
            attachments: Optional file attachments with Gemini File URIs

        Yields:
            dict: Events with type and content:
                - {"type": "thought", "content": str} - Thought chunk
                - {"type": "plan", "data": PlanAction} - Final plan

        Raises:
            GeminiError: If planning fails
        """
        log = logger.bind(
            user_id=user_id,
            tool_count=len(available_tools),
            history_length=len(execution_history) if execution_history else 0,
            has_attachments=bool(attachments),
        )
        log.info("plan_next_action_stream_start")

        try:
            # Build planning prompt
            prompt = self._build_planning_prompt(
                user_message=user_message,
                available_tools=available_tools,
                execution_history=execution_history,
            )

            # Build user message with attachments
            user_msg = {
                "role": "user",
                "content": prompt,
            }

            # Include attachments if present (files already uploaded to Gemini)
            if attachments:
                user_msg["attachments"] = attachments
                log.info("attachments_included_in_planning", count=len(attachments))

            # Stream the thinking process
            full_response = ""
            async for chunk in self.gemini_client.chat_completion_stream(
                messages=[
                    {
                        "role": "system",
                        "content": self._get_streaming_system_prompt(),
                    },
                    user_msg,
                ],
                temperature=0.3,
            ):
                full_response += chunk
                yield {"type": "thought", "content": chunk}

            # Parse the final response to extract the plan
            plan = self._parse_plan_from_response(full_response)

            log.info(
                "plan_next_action_stream_complete",
                has_action=plan.action is not None,
                is_complete=plan.is_complete,
            )

            yield {"type": "plan", "data": plan}

        except GeminiError as e:
            log.error("planning_stream_error", error=str(e))
            raise

    def _get_streaming_system_prompt(self) -> str:
        """Get system prompt for streaming planner.

        Returns:
            System prompt optimized for streaming output
        """
        return """You are an AI agent that helps users with advertising automation tasks.

Analyze the user's request and decide how to respond.

## CRITICAL: When to use tools vs direct response

### MUST USE TOOLS for these tasks (DO NOT just promise to do them):
- **Image generation**: Use `generate_image_tool` - you CANNOT generate images yourself
- **Video generation**: Use `generate_video_tool` - you CANNOT generate videos yourself
- **Data queries**: Use appropriate data tools - you CANNOT access real data yourself
- **File operations**: Use file tools - you CANNOT access files yourself
- **External API calls**: Use API tools - you CANNOT make external requests yourself

### Can answer directly (no tools needed):
- General knowledge questions
- Greetings and casual conversation
- Writing, translation, explanation tasks
- Math calculations, date calculations
- Advice and suggestions (without requiring real data)

## Response format:

### If you need to use a tool (image/video generation, data access, etc.):
```json
{
    "action": "tool_name",
    "action_input": {"param": "value"},
    "is_complete": false,
    "final_answer": null
}
```

### If you can answer directly WITHOUT any tool:
```json
{
    "action": null,
    "action_input": null,
    "is_complete": true,
    "final_answer": "Your direct answer here"
}
```

## IMPORTANT RULES:
1. **NEVER say "I'm generating..." and then set is_complete=true** - you must actually call the tool!
2. If user asks to generate/create something, you MUST call the appropriate tool
3. Only set is_complete=true AFTER the tool has been executed and returned results
4. Do not promise to do something without actually doing it

## CRITICAL: Reflective Problem-Solving Loop (2-3 Rounds)

When you encounter failures or obstacles, DO NOT give up immediately. You MUST reflect and retry 2-3 times before giving up.

### The Reflection Loop (Repeat 2-3 times before giving up):
1. **OBSERVE**: What went wrong? Why did it fail?
2. **REFLECT**: What data do I already have? What alternative approaches exist?
3. **RE-PLAN**: Choose a different path and try again
4. **If still failing after 2-3 attempts**: Only then consider giving up with a clear explanation

### Key Principles:

1. **Retry at least 2-3 times**:
   - First attempt fails? Try a different tool or approach
   - Second attempt fails? Try combining existing data with reasoning
   - Third attempt fails? Try one more creative solution
   - Only give up after exhausting multiple approaches

2. **Use data you already have**: After getting ANY tool result, ask yourself:
   - What can I infer or calculate from this data?
   - Does this data, combined with my knowledge, answer the user's question?

3. **Your reasoning is a tool**: You are an LLM with knowledge and reasoning ability
   - You can calculate dates, do math, make logical inferences
   - Tool results + YOUR reasoning = Complete answers

4. **Decompose complex problems**: Break into steps where each step uses available resources

### IMPORTANT: Only give up after 2-3 reflection rounds
- Do NOT give up after a single failure
- Each failed approach should trigger a new reflection and re-plan
- Track your attempts mentally: "Attempt 1 failed, let me try approach 2..."
- Only say "I cannot help" after genuinely trying 2-3 different approaches

Guidelines:
- For simple questions (greetings, general knowledge, writing tasks), answer directly
- Only use tools when specifically needed (generating images, checking data, etc.)
- Keep explanations brief and user-friendly
- Never include technical details or markdown headers in your response
- When a tool fails, you MUST try alternative approaches (2-3 times) before giving up"""

    def _parse_plan_from_response(self, response: str) -> PlanAction:
        """Parse plan from streaming response.

        Args:
            response: Full response text

        Returns:
            PlanAction extracted from response
        """
        # Extract thought (everything before ## Decision or ```json)
        thought = response
        if "## Decision" in response:
            thought = response.split("## Decision")[0].replace("## Thinking", "").strip()
        elif "```json" in response:
            thought = response.split("```json")[0].replace("## Thinking", "").strip()

        # Extract JSON from response
        try:
            # Try to find JSON block
            if "```json" in response and "```" in response.split("```json")[1]:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "{" in response and "}" in response:
                # Find the last JSON-like structure
                start = response.rfind("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]
            else:
                # No JSON found, treat as direct response
                return PlanAction(
                    thought=thought or response[:500],
                    is_complete=True,
                    final_answer=response,
                )

            data = json.loads(json_str)

            return PlanAction(
                thought=thought or data.get("thought", ""),
                action=data.get("action"),
                action_input=data.get("action_input"),
                is_complete=data.get("is_complete", False),
                final_answer=data.get("final_answer"),
            )

        except (json.JSONDecodeError, IndexError) as e:
            logger.warning("plan_parse_fallback", error=str(e))
            # Fallback: treat entire response as final answer
            return PlanAction(
                thought=thought or response[:500],
                is_complete=True,
                final_answer=response,
            )

    async def understand_intent(
        self,
        user_message: str,
        available_tools: list[AgentTool],
    ) -> dict[str, Any]:
        """Understand user intent and identify required capabilities.

        Args:
            user_message: User's message
            available_tools: Available tools

        Returns:
            Dictionary with intent analysis
        """
        log = logger.bind(tool_count=len(available_tools))
        log.info("understand_intent_start")

        try:
            # Build intent understanding prompt
            prompt = f"""Analyze this user request and identify:
1. Primary intent (what the user wants to accomplish)
2. Required capabilities (what tools/skills are needed)
3. Key entities (products, campaigns, etc.)
4. Ambiguities (missing information that needs clarification)

User Request: {user_message}

Available Tools:
{self._format_tools_for_prompt(available_tools)}

Provide your analysis in JSON format with keys:
- intent: string describing primary intent
- required_tools: list of tool names needed
- entities: dict of identified entities
- ambiguities: list of missing information
- confidence: float 0-1 indicating confidence in understanding
"""

            # Get intent analysis
            response = await self.gemini_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at understanding user intent for advertising automation tasks.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.2,
            )

            # Parse JSON response
            try:
                intent_data = json.loads(response)
            except json.JSONDecodeError:
                # Fallback if not valid JSON
                intent_data = {
                    "intent": response[:200],
                    "required_tools": [],
                    "entities": {},
                    "ambiguities": [],
                    "confidence": 0.5,
                }

            log.info(
                "understand_intent_complete",
                confidence=intent_data.get("confidence", 0),
                required_tools=len(intent_data.get("required_tools", [])),
            )

            return intent_data

        except GeminiError as e:
            log.error("intent_understanding_error", error=str(e))
            raise

    def _get_system_prompt(self) -> str:
        """Get system prompt for the planner.

        Returns:
            System prompt
        """
        return """You are an AI agent that helps users with advertising automation tasks.

Your role is to:
1. Understand what the user wants to accomplish
2. Break down complex tasks into steps
3. Select the right tools to use
4. Execute actions systematically
5. Provide clear, helpful responses

## CRITICAL: When to use tools vs direct response

### MUST USE TOOLS for these tasks (DO NOT just promise to do them):
- **Image generation**: Use `generate_image_tool` - you CANNOT generate images yourself
- **Video generation**: Use `generate_video_tool` - you CANNOT generate videos yourself
- **Data queries**: Use appropriate data tools - you CANNOT access real data yourself
- **File operations**: Use file tools - you CANNOT access files yourself
- **External API calls**: Use API tools - you CANNOT make external requests yourself

### Can answer directly (no tools needed):
- General knowledge questions
- Greetings and casual conversation
- Writing, translation, explanation tasks
- Math calculations, date calculations
- Advice and suggestions (without requiring real data)

## IMPORTANT RULES:
1. **NEVER say "I'm generating..." and then set is_complete=true** - you must actually call the tool!
2. If user asks to generate/create something, you MUST call the appropriate tool
3. Only set is_complete=true AFTER the tool has been executed and returned results
4. Do not promise to do something without actually doing it

Follow the ReAct (Reasoning + Acting) pattern:
- Think: Reason about what to do next
- Act: Choose a tool and provide parameters
- Observe: Process the tool result
- Evaluate: Decide if the task is complete

## CRITICAL: Reflective Problem-Solving Loop (2-3 Rounds)

When you encounter failures or obstacles, DO NOT give up immediately. You MUST reflect and retry 2-3 times before giving up.

### The Reflection Loop:
1. **OBSERVE**: What went wrong? Why did it fail?
2. **REFLECT**: What data do I already have? What alternatives exist?
3. **RE-PLAN**: Choose a different path and try again
4. **If still failing after 2-3 attempts**: Only then consider giving up with explanation

### Key Principles:

1. **Retry at least 2-3 times** before giving up
2. **Your reasoning is powerful**: Tool results + YOUR reasoning = Complete answers
3. **Use data you already have**: Infer and combine information
4. **Decompose problems**: Break complex tasks into steps

Guidelines:
- Be systematic and thorough
- Use tools when needed for generation/data tasks
- Ask for clarification if information is missing
- Complete tasks efficiently without unnecessary steps

When the task is complete, set is_complete=true and provide a final_answer."""

    def _build_planning_prompt(
        self,
        user_message: str,
        available_tools: list[AgentTool],
        execution_history: list[dict[str, Any]] | None,
    ) -> str:
        """Build the planning prompt.

        Args:
            user_message: User's message
            available_tools: Available tools
            execution_history: Execution history

        Returns:
            Planning prompt
        """
        prompt_parts = []

        # User's original request
        prompt_parts.append(f"User Request: {user_message}")
        prompt_parts.append("")

        # Available tools
        prompt_parts.append("Available Tools:")
        prompt_parts.append(self._format_tools_for_prompt(available_tools))
        prompt_parts.append("")

        # Execution history
        if execution_history:
            prompt_parts.append("Execution History:")
            for idx, step in enumerate(execution_history, 1):
                prompt_parts.append(f"\nStep {idx}:")
                prompt_parts.append(f"  Thought: {step.get('thought', 'N/A')}")
                if step.get("action"):
                    prompt_parts.append(f"  Action: {step['action']}")
                    prompt_parts.append(f"  Input: {step.get('action_input', {})}")
                if step.get("observation"):
                    prompt_parts.append(f"  Observation: {step['observation']}")
            prompt_parts.append("")

        # Instructions
        prompt_parts.append("What should I do next?")
        prompt_parts.append("")
        prompt_parts.append("IMPORTANT: Reflect 2-3 times before giving up!")
        prompt_parts.append("- If a tool fails, try alternative approaches (at least 2-3 attempts)")
        prompt_parts.append("- Tools give you DATA, your reasoning gives you ANSWERS")
        prompt_parts.append("- Combine tool results with your knowledge to derive answers")
        prompt_parts.append("- Only give up after genuinely trying 2-3 different approaches")
        prompt_parts.append("")
        prompt_parts.append("Provide:")
        prompt_parts.append("1. thought: Your reasoning about what to do next")
        prompt_parts.append("2. action: Tool name to call (or null if complete)")
        prompt_parts.append("3. action_input: Tool parameters (or null)")
        prompt_parts.append("4. is_complete: true if task is done, false otherwise")
        prompt_parts.append("5. final_answer: Final response to user (if complete)")

        return "\n".join(prompt_parts)

    def _format_tools_for_prompt(self, tools: list[AgentTool]) -> str:
        """Format tools for inclusion in prompt.

        Args:
            tools: List of tools

        Returns:
            Formatted tool descriptions
        """
        if not tools:
            return "No tools available"

        tool_descriptions = []

        for tool in tools:
            # Format parameters
            params = []
            for param in tool.metadata.parameters:
                param_desc = f"  - {param.name} ({param.type})"
                if param.required:
                    param_desc += " [required]"
                param_desc += f": {param.description}"
                if param.enum:
                    param_desc += f" (options: {', '.join(map(str, param.enum))})"
                params.append(param_desc)

            tool_desc = f"""
{tool.name}:
  Description: {tool.metadata.description}
  Parameters:
{chr(10).join(params)}
  Returns: {tool.metadata.returns}
  Credit Cost: {tool.metadata.credit_cost} credits
"""
            tool_descriptions.append(tool_desc)

        return "\n".join(tool_descriptions)

    async def select_tools(
        self,
        user_message: str,
        all_tools: list[AgentTool],
        max_tools: int = 20,
    ) -> list[AgentTool]:
        """Select relevant tools for the user's request.

        This is used for dynamic tool loading to reduce context size.

        Args:
            user_message: User's message
            all_tools: All available tools
            max_tools: Maximum number of tools to select

        Returns:
            List of selected tools
        """
        log = logger.bind(
            total_tools=len(all_tools),
            max_tools=max_tools,
        )
        log.info("select_tools_start")

        try:
            # Build tool selection prompt
            tool_list = "\n".join(
                [
                    f"- {tool.name}: {tool.metadata.description} (tags: {', '.join(tool.metadata.tags)})"
                    for tool in all_tools
                ]
            )

            prompt = f"""Given this user request, select the most relevant tools (up to {max_tools}).

User Request: {user_message}

Available Tools:
{tool_list}

Return a JSON array of tool names that are most relevant to this request.
Consider:
1. Direct relevance to the task
2. Dependencies between tools
3. Common workflows

Example: ["tool1", "tool2", "tool3"]
"""

            # Get tool selection
            response = await self.gemini_client.fast_completion(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.2,
            )

            # Parse tool names
            try:
                selected_names = json.loads(response)
                if not isinstance(selected_names, list):
                    selected_names = []
            except json.JSONDecodeError:
                # Fallback: return all tools
                log.warning("tool_selection_parse_failed", response=response[:200])
                selected_names = [tool.name for tool in all_tools[:max_tools]]

            # Get tool objects
            tool_map = {tool.name: tool for tool in all_tools}
            selected_tools = [
                tool_map[name] for name in selected_names if name in tool_map
            ]

            # Ensure we don't exceed max_tools
            selected_tools = selected_tools[:max_tools]

            log.info(
                "select_tools_complete",
                selected_count=len(selected_tools),
            )

            return selected_tools

        except GeminiError as e:
            log.error("tool_selection_error", error=str(e))
            # Fallback: return first max_tools
            return all_tools[:max_tools]
