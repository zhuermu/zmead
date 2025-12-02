"""Planner Node - Task decomposition and planning.

This node analyzes user requests and generates execution plans
for complex multi-step tasks.

Requirements: Architecture v2.0 - Planning Capability
"""

from typing import Any

import structlog
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field

from app.core.models import ExecutionPlan, ExecutionStep
from app.core.state import AgentState
from app.services.gemini_client import GeminiClient, GeminiError
from app.tools.registry import get_tool_registry

logger = structlog.get_logger(__name__)


# Credit threshold for requiring confirmation
CONFIRMATION_CREDIT_THRESHOLD = 10.0


class PlannerStep(BaseModel):
    """A single step in the execution plan.

    Note: All fields must be explicitly required or have defaults to ensure
    LangChain's structured output parser populates them correctly.
    """

    step_id: int = Field(default=1, description="步骤编号，从1开始")
    action: str = Field(default="执行任务", description="动作描述")
    tool: str = Field(default="", description="要调用的工具名称，如 generate_creative, get_ad_performance")
    # Flatten tool_params into explicit fields for better LLM extraction
    product_description: str | None = Field(default=None, description="产品描述，用于generate_creative工具")
    count: int | None = Field(default=None, description="生成数量，用于generate_creative工具")
    style: str | None = Field(default=None, description="风格，用于generate_creative工具")
    platform: str | None = Field(default=None, description="广告平台，如meta, tiktok, google")
    date_range: str | None = Field(default=None, description="日期范围，如last_7_days, last_30_days")
    depends_on: list[int] = Field(default_factory=list, description="依赖的步骤ID列表")
    reason: str = Field(default="", description="执行原因")
    estimated_cost: float = Field(default=0.5, description="预估credit消耗")

    def to_tool_params(self) -> dict[str, Any]:
        """Convert flattened fields back to tool_params dict."""
        params: dict[str, Any] = {}
        if self.product_description:
            params["product_description"] = self.product_description
        if self.count:
            params["count"] = self.count
        if self.style:
            params["style"] = self.style
        if self.platform:
            params["platform"] = self.platform
        if self.date_range:
            params["date_range"] = self.date_range
        return params


class PlannerOutput(BaseModel):
    """Structured output from planner LLM."""

    goal: str = Field(description="用户的目标")
    complexity: str = Field(description="任务复杂度: simple, moderate, complex")
    steps: list[PlannerStep] = Field(description="执行步骤列表，每步包含tool和tool_params")
    requires_confirmation: bool = Field(default=False, description="是否需要用户确认")


PLANNER_SYSTEM_PROMPT = """你是一个广告投放AI助手的任务规划器。

你的职责是将用户的请求分解为具体的执行步骤。

## 可用工具

{tool_descriptions}

## 规划原则

1. **先获取数据，再分析，最后行动**：确保有足够信息再执行操作
2. **依赖关系**：如果步骤B需要步骤A的结果，在depends_on中标注
3. **并行优化**：没有依赖的步骤可以并行执行
4. **成本意识**：估算每步骤的credit消耗
5. **安全第一**：高风险操作（暂停全部、删除、大额预算变更）需要确认

## 复杂度判断

- **simple**: 单一明确任务，1-2步骤（如：查看昨天数据、生成4张素材）
- **moderate**: 需要分析或组合，2-4步骤（如：分析表现差的广告并生成替代素材）
- **complex**: 复杂多步骤，需要多轮交互，4+步骤

## 输出格式

返回JSON格式，包含:
- goal: 用户目标的简洁描述
- complexity: simple/moderate/complex
- steps: 步骤列表，每步包含:
  - step_id: 步骤编号(从1开始)
  - action: 动作描述
  - tool: 工具名称 (generate_creative, get_ad_performance, web_scrape)
  - product_description: 产品描述(generate_creative工具必填)
  - count: 生成数量(generate_creative工具)
  - style: 风格(generate_creative工具)
  - platform: 广告平台(get_ad_performance工具)
  - date_range: 日期范围(get_ad_performance工具)
  - depends_on: 依赖的步骤ID列表
  - reason: 执行原因
  - estimated_cost: 预估credit消耗
- requires_confirmation: 是否需要用户确认(高成本或高风险时为true)

## 示例

用户: "看看我上周Meta广告的表现"
```json
{{
  "goal": "查看上周Meta广告表现数据",
  "complexity": "simple",
  "steps": [
    {{
      "step_id": 1,
      "action": "获取Meta广告数据",
      "tool": "get_ad_performance",
      "platform": "meta",
      "date_range": "last_7_days",
      "depends_on": [],
      "reason": "获取用户请求的广告表现数据",
      "estimated_cost": 1.0
    }}
  ],
  "requires_confirmation": false
}}
```

用户: "生成4张猫粮广告图"
```json
{{
  "goal": "生成猫粮广告素材",
  "complexity": "simple",
  "steps": [
    {{
      "step_id": 1,
      "action": "生成4张猫粮广告图",
      "tool": "generate_creative",
      "product_description": "猫粮广告",
      "count": 4,
      "style": "现代风格",
      "depends_on": [],
      "reason": "生成用户请求的广告素材",
      "estimated_cost": 2.0
    }}
  ],
  "requires_confirmation": false
}}
```

用户: "帮我生成高端猫粮的广告素材"
```json
{{
  "goal": "生成高端猫粮广告素材",
  "complexity": "simple",
  "steps": [
    {{
      "step_id": 1,
      "action": "生成高端猫粮广告图",
      "tool": "generate_creative",
      "product_description": "高端猫粮，天然有机成分，适合挑食猫咪",
      "count": 4,
      "style": "奢华风格",
      "depends_on": [],
      "reason": "生成高端猫粮的广告素材",
      "estimated_cost": 2.0
    }}
  ],
  "requires_confirmation": false
}}
```
"""


def _format_tool_descriptions() -> str:
    """Format available tools for the prompt."""
    registry = get_tool_registry()
    tools = registry.list_definitions()

    lines = []
    for tool in tools:
        params_desc = ", ".join(
            f"{k}: {v.get('type', 'any')}"
            for k, v in tool.parameters.get("properties", {}).items()
        )
        lines.append(f"- **{tool.name}**: {tool.description}")
        lines.append(f"  参数: {params_desc}")
        lines.append(f"  成本: {tool.credit_cost} credits")
        lines.append("")

    return "\n".join(lines)


def _format_plan_for_user(plan: ExecutionPlan) -> str:
    """Format execution plan for user display."""
    lines = [
        "📋 **执行计划**",
        "",
        f"**目标**: {plan.goal}",
        f"**预估消耗**: {plan.estimated_total_credits} credits",
        "",
        "**执行步骤**:",
    ]

    for step in plan.steps:
        deps = f" (依赖步骤 {step.depends_on})" if step.depends_on else ""
        lines.append(f"{step.step_id}. {step.action}{deps}")

    lines.extend(
        [
            "",
            "请确认是否执行此计划？回复「确认」开始执行，或告诉我需要调整的地方。",
        ]
    )

    return "\n".join(lines)


async def planner_node(state: AgentState) -> dict[str, Any]:
    """Task planning node.

    Analyzes user request and generates an execution plan.

    Args:
        state: Current agent state

    Returns:
        State updates with execution plan
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )
    log.info("planner_node_start")

    messages = state.get("messages", [])
    if not messages:
        log.warning("planner_node_no_messages")
        return {
            "error": {
                "code": "NO_MESSAGE",
                "type": "NO_MESSAGE",
                "message": "没有收到消息",
            }
        }

    # Get user message
    last_message = messages[-1]
    user_message = (
        last_message.content if hasattr(last_message, "content") else str(last_message)
    )

    try:
        # Initialize Gemini
        gemini = GeminiClient()

        # Format tool descriptions
        tool_descriptions = _format_tool_descriptions()

        # Build prompt
        system_prompt = PLANNER_SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions)

        prompt_messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"用户请求: {user_message}\n\n请制定执行计划。",
            },
        ]

        # Get structured output
        result = await gemini.structured_output(
            messages=prompt_messages,
            schema=PlannerOutput,
            temperature=0.2,
        )

        log.info(
            "planner_node_plan_generated",
            goal=result.goal,
            complexity=result.complexity,
            step_count=len(result.steps),
        )

        # Convert to ExecutionPlan
        # Handle both dict (from LLM) and PlannerStep objects
        steps = []
        for step in result.steps:
            if isinstance(step, dict):
                # LLM returned raw dict - convert to PlannerStep first
                step_obj = PlannerStep(**step)
            else:
                step_obj = step

            steps.append(
                ExecutionStep(
                    step_id=step_obj.step_id,
                    action=step_obj.action,
                    tool=step_obj.tool,
                    tool_params=step_obj.to_tool_params(),
                    depends_on=step_obj.depends_on,
                    reason=step_obj.reason,
                    estimated_cost=step_obj.estimated_cost,
                )
            )

        total_cost = sum(s.estimated_cost for s in steps)

        # Determine if confirmation is needed
        requires_confirmation = result.requires_confirmation or (
            total_cost > CONFIRMATION_CREDIT_THRESHOLD
        )

        plan = ExecutionPlan(
            goal=result.goal,
            complexity=result.complexity,  # type: ignore
            steps=steps,
            estimated_total_credits=total_cost,
            requires_confirmation=requires_confirmation,
        )

        log.info(
            "planner_node_complete",
            complexity=plan.complexity,
            steps=plan.step_count,
            total_cost=total_cost,
            requires_confirmation=requires_confirmation,
        )

        # For simple tasks, auto-confirm
        if plan.complexity == "simple" and not requires_confirmation:
            return {
                "execution_plan": plan.model_dump(),
                "current_step_index": 0,
                "plan_confirmed": True,
                "step_results": [],
                "execution_complete": False,
            }

        # For complex tasks or high cost, show plan and wait for confirmation
        plan_summary = _format_plan_for_user(plan)

        return {
            "execution_plan": plan.model_dump(),
            "current_step_index": 0,
            "plan_confirmed": not requires_confirmation,
            "step_results": [],
            "execution_complete": False,
            "messages": [AIMessage(content=plan_summary)] if requires_confirmation else [],
        }

    except GeminiError as e:
        log.error("planner_node_gemini_error", error=str(e))
        return {
            "error": {
                "code": "PLANNING_FAILED",
                "type": "GEMINI_ERROR",
                "message": f"规划失败: {str(e)}",
            }
        }
    except Exception as e:
        log.error("planner_node_error", error=str(e), exc_info=True)
        return {
            "error": {
                "code": "PLANNING_FAILED",
                "type": "UNEXPECTED_ERROR",
                "message": f"规划失败: {str(e)}",
            }
        }
