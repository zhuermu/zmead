"""Analyzer Node - Result analysis and decision making.

This node analyzes the results of executed steps and decides:
- Continue: Execute the next step
- Respond: All steps completed, generate final response
- Replan: Something failed, need to adjust the plan

Requirements: Architecture v2.0 - Multi-step Execution
"""

from typing import Any, Literal

import structlog
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field

from app.core.models import ExecutionPlan, StepResult
from app.core.state import AgentState
from app.services.gemini_client import GeminiClient, GeminiError

logger = structlog.get_logger(__name__)


class AnalyzerOutput(BaseModel):
    """Structured output from analyzer LLM."""

    decision: Literal["continue", "respond", "replan"] = Field(
        description="决策: continue=继续执行, respond=生成响应, replan=重新规划"
    )
    reason: str = Field(description="决策原因")
    summary: str | None = Field(default=None, description="执行结果摘要(仅当decision=respond时)")
    replan_suggestion: str | None = Field(
        default=None, description="重新规划建议(仅当decision=replan时)"
    )


ANALYZER_SYSTEM_PROMPT = """你是一个广告投放AI助手的执行分析器。

你的职责是分析已执行步骤的结果，决定下一步行动。

## 执行计划

目标: {goal}
总步骤: {total_steps}
已完成: {completed_steps}

## 已执行的步骤结果

{step_results}

## 决策规则

1. **continue**: 还有未执行的步骤，且之前步骤都成功
2. **respond**:
   - 所有步骤都已完成
   - 或者遇到了无法恢复的错误，需要告知用户
3. **replan**:
   - 某个步骤失败了，但可以通过调整计划来恢复
   - 发现了新的信息需要调整策略

## 输出格式

返回JSON格式:
- decision: "continue" | "respond" | "replan"
- reason: 决策原因
- summary: 当decision=respond时，提供执行结果的摘要
- replan_suggestion: 当decision=replan时，提供调整建议
"""


def _format_step_results(step_results: list[dict]) -> str:
    """Format step results for the prompt."""
    if not step_results:
        return "暂无执行结果"

    lines = []
    for result in step_results:
        status = "✅ 成功" if result.get("success") else "❌ 失败"
        lines.append(f"步骤 {result.get('step_id')}: {result.get('tool')} - {status}")

        if result.get("error"):
            lines.append(f"  错误: {result.get('error')}")
        elif result.get("data"):
            # Summarize data (don't include full data to avoid token overflow)
            data = result.get("data")
            if isinstance(data, dict):
                lines.append(f"  结果: {list(data.keys())}")
            elif isinstance(data, list):
                lines.append(f"  结果: {len(data)} 条记录")
            else:
                lines.append(f"  结果: {str(data)[:100]}")

        lines.append("")

    return "\n".join(lines)


def _generate_completion_summary(
    plan: ExecutionPlan, step_results: list[dict]
) -> str:
    """Generate a summary message for completed execution."""
    success_count = sum(1 for r in step_results if r.get("success"))
    total_count = len(step_results)
    total_credits = sum(r.get("credit_consumed", 0) for r in step_results)

    lines = [
        f"✅ **执行完成**",
        "",
        f"**目标**: {plan.goal}",
        f"**结果**: {success_count}/{total_count} 步骤成功",
    ]

    if total_credits > 0:
        lines.append(f"**消耗**: {total_credits:.1f} credits")

    lines.append("")
    lines.append("**详细结果**:")

    for result in step_results:
        step = plan.get_step(result.get("step_id", 0))
        action_desc = step.action if step else result.get("tool", "未知")

        if result.get("success"):
            lines.append(f"- ✅ {action_desc}")
            # Add brief data summary
            data = result.get("data")
            if data:
                if isinstance(data, dict):
                    if "records" in data:
                        lines.append(f"  获取了 {len(data['records'])} 条记录")
                    elif "images" in data:
                        lines.append(f"  生成了 {len(data['images'])} 张图片")
                    elif "url" in data:
                        lines.append(f"  URL: {data['url']}")
                elif isinstance(data, list):
                    lines.append(f"  返回了 {len(data)} 条数据")
        else:
            lines.append(f"- ❌ {action_desc}: {result.get('error', '未知错误')}")

    return "\n".join(lines)


async def analyzer_node(state: AgentState) -> dict[str, Any]:
    """Result analysis and decision node.

    Analyzes executed step results and decides:
    - continue: Execute next step
    - respond: Generate final response
    - replan: Adjust the execution plan

    Args:
        state: Current agent state

    Returns:
        State updates with decision
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )

    # Get execution plan and results
    plan_data = state.get("execution_plan")
    step_results = state.get("step_results", [])
    current_index = state.get("current_step_index", 0)

    if not plan_data:
        log.error("analyzer_node_no_plan")
        return {
            "error": {
                "code": "NO_PLAN",
                "type": "EXECUTION_ERROR",
                "message": "没有执行计划",
            }
        }

    plan = ExecutionPlan(**plan_data) if isinstance(plan_data, dict) else plan_data

    log.info(
        "analyzer_node_start",
        completed_steps=len(step_results),
        total_steps=len(plan.steps),
        current_index=current_index,
    )

    # Quick decision for simple cases
    # Case 1: All steps completed successfully
    if current_index >= len(plan.steps):
        all_success = all(r.get("success") for r in step_results)

        if all_success:
            log.info("analyzer_node_all_complete")
            summary = _generate_completion_summary(plan, step_results)
            return {
                "execution_complete": True,
                "analyzer_decision": "respond",
                "messages": [AIMessage(content=summary)],
            }

    # Case 2: Last step failed
    if step_results:
        last_result = step_results[-1]
        if not last_result.get("success"):
            log.info(
                "analyzer_node_step_failed",
                step_id=last_result.get("step_id"),
                error=last_result.get("error"),
            )

            # For now, just report the failure
            # In future, could try to replan
            error_summary = _generate_completion_summary(plan, step_results)
            return {
                "execution_complete": True,
                "analyzer_decision": "respond",
                "messages": [AIMessage(content=error_summary)],
            }

    # Case 3: More steps to execute
    if current_index < len(plan.steps):
        log.info(
            "analyzer_node_continue",
            next_step=current_index,
            total_steps=len(plan.steps),
        )
        return {
            "analyzer_decision": "continue",
            "execution_complete": False,
        }

    # Default: respond
    log.info("analyzer_node_default_respond")
    summary = _generate_completion_summary(plan, step_results)
    return {
        "execution_complete": True,
        "analyzer_decision": "respond",
        "messages": [AIMessage(content=summary)],
    }


async def analyzer_node_with_llm(state: AgentState) -> dict[str, Any]:
    """Advanced analyzer using LLM for complex decisions.

    This version uses Gemini to make more nuanced decisions,
    useful for complex multi-step tasks where simple rules
    may not be sufficient.

    Args:
        state: Current agent state

    Returns:
        State updates with decision
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )

    plan_data = state.get("execution_plan")
    step_results = state.get("step_results", [])

    if not plan_data:
        return {"analyzer_decision": "respond"}

    plan = ExecutionPlan(**plan_data) if isinstance(plan_data, dict) else plan_data

    # For simple tasks or near completion, use rule-based
    if plan.complexity == "simple" or len(step_results) >= len(plan.steps) - 1:
        return await analyzer_node(state)

    try:
        gemini = GeminiClient()

        # Format prompt
        prompt = ANALYZER_SYSTEM_PROMPT.format(
            goal=plan.goal,
            total_steps=len(plan.steps),
            completed_steps=len(step_results),
            step_results=_format_step_results(step_results),
        )

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "请分析当前执行状态并决定下一步行动。"},
        ]

        result = await gemini.structured_output(
            messages=messages,
            schema=AnalyzerOutput,
            temperature=0.1,
        )

        log.info(
            "analyzer_node_llm_decision",
            decision=result.decision,
            reason=result.reason,
        )

        if result.decision == "continue":
            return {
                "analyzer_decision": "continue",
                "execution_complete": False,
            }
        elif result.decision == "respond":
            summary = result.summary or _generate_completion_summary(plan, step_results)
            return {
                "execution_complete": True,
                "analyzer_decision": "respond",
                "messages": [AIMessage(content=summary)],
            }
        else:  # replan
            return {
                "analyzer_decision": "replan",
                "execution_complete": False,
                "replan_suggestion": result.replan_suggestion,
            }

    except GeminiError as e:
        log.error("analyzer_node_llm_error", error=str(e))
        # Fall back to rule-based
        return await analyzer_node(state)
