"""Executor Node - Unified tool execution.

This node executes tools from the execution plan, handling:
- Tool lookup from registry
- Parameter resolution (including references to previous results)
- Credit management
- Error handling

Requirements: Architecture v2.0 - Multi-step Execution
"""

import re
from typing import Any

import structlog

from app.core.models import ExecutionPlan, ExecutionStep, StepResult
from app.core.state import AgentState
from app.tools.base import ToolContext, ToolResult
from app.tools.registry import get_tool_registry

logger = structlog.get_logger(__name__)


def _resolve_params(
    params: dict[str, Any], previous_results: dict[int, Any]
) -> dict[str, Any]:
    """Resolve parameter references to previous step results.

    Supports syntax like:
    - "$step_1" -> entire result of step 1
    - "$step_1.data" -> data field of step 1 result
    - "$step_1.data.records" -> nested field access

    Args:
        params: Original parameters with potential references
        previous_results: Results from previous steps (step_id -> result)

    Returns:
        Resolved parameters
    """
    resolved = {}

    for key, value in params.items():
        if isinstance(value, str) and value.startswith("$step_"):
            # Parse reference: $step_1.data.field
            match = re.match(r"\$step_(\d+)(?:\.(.+))?", value)
            if match:
                step_id = int(match.group(1))
                path = match.group(2)

                if step_id in previous_results:
                    result = previous_results[step_id]
                    if path:
                        resolved[key] = _get_nested_value(result, path)
                    else:
                        resolved[key] = result
                else:
                    resolved[key] = None
            else:
                resolved[key] = value
        elif isinstance(value, dict):
            # Recursively resolve nested dicts
            resolved[key] = _resolve_params(value, previous_results)
        elif isinstance(value, list):
            # Resolve list items
            resolved[key] = [
                _resolve_params({"item": item}, previous_results).get("item", item)
                if isinstance(item, (str, dict))
                else item
                for item in value
            ]
        else:
            resolved[key] = value

    return resolved


def _get_nested_value(obj: Any, path: str) -> Any:
    """Get nested value from object using dot notation.

    Args:
        obj: Object to extract from (dict or object with attributes)
        path: Dot-separated path (e.g., "data.records.0.name")

    Returns:
        Value at path, or None if not found
    """
    parts = path.split(".")
    current = obj

    for part in parts:
        if current is None:
            return None

        # Try dict access
        if isinstance(current, dict):
            current = current.get(part)
        # Try list index
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            current = current[idx] if idx < len(current) else None
        # Try attribute access
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return None

    return current


async def executor_node(state: AgentState) -> dict[str, Any]:
    """Unified tool execution node.

    Executes the current step from the execution plan.

    Args:
        state: Current agent state

    Returns:
        State updates with step results
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
    )

    # Get execution plan
    plan_data = state.get("execution_plan")
    if not plan_data:
        log.error("executor_node_no_plan")
        return {
            "error": {
                "code": "NO_PLAN",
                "type": "EXECUTION_ERROR",
                "message": "没有执行计划",
            }
        }

    plan = ExecutionPlan(**plan_data) if isinstance(plan_data, dict) else plan_data

    # Get current step index
    current_index = state.get("current_step_index", 0)
    step_results = state.get("step_results", [])

    # Check if we have more steps
    if current_index >= len(plan.steps):
        log.info("executor_node_complete", total_steps=len(plan.steps))
        return {"execution_complete": True}

    # Get current step
    step = plan.steps[current_index]

    log.info(
        "executor_node_start",
        step_id=step.step_id,
        tool=step.tool,
        step_index=current_index,
        total_steps=len(plan.steps),
    )

    # Build previous results map
    previous_results = {r["step_id"]: r.get("data") for r in step_results}

    # Check dependencies
    for dep_id in step.depends_on:
        dep_result = next((r for r in step_results if r["step_id"] == dep_id), None)
        if not dep_result or not dep_result.get("success"):
            log.warning(
                "executor_node_dependency_failed",
                step_id=step.step_id,
                missing_dep=dep_id,
            )
            return {
                "step_results": step_results
                + [
                    StepResult(
                        step_id=step.step_id,
                        tool=step.tool,
                        success=False,
                        error=f"依赖步骤 {dep_id} 未成功完成",
                    ).model_dump()
                ],
                "current_step_index": current_index + 1,
            }

    # Get tool from registry
    registry = get_tool_registry()
    tool = registry.get(step.tool)

    if not tool:
        log.error("executor_node_tool_not_found", tool=step.tool)
        return {
            "step_results": step_results
            + [
                StepResult(
                    step_id=step.step_id,
                    tool=step.tool,
                    success=False,
                    error=f"工具不存在: {step.tool}",
                ).model_dump()
            ],
            "current_step_index": current_index + 1,
        }

    # Build execution context
    context = ToolContext(
        user_id=state.get("user_id", ""),
        session_id=state.get("session_id", ""),
        previous_results=previous_results,
        memory_context=state.get("memory_context"),
    )

    # Resolve parameters
    resolved_params = _resolve_params(step.tool_params, previous_results)

    log.info(
        "executor_node_executing",
        tool=step.tool,
        params=resolved_params,
    )

    try:
        # Validate parameters
        validated_params = tool.validate_params(resolved_params)

        # Execute tool
        result = await tool.execute(validated_params, context)

        # Create step result
        step_result = StepResult(
            step_id=step.step_id,
            tool=step.tool,
            success=result.success,
            data=result.data,
            error=result.error,
            credit_consumed=result.credit_consumed,
        )

        log.info(
            "executor_node_step_complete",
            step_id=step.step_id,
            tool=step.tool,
            success=result.success,
            credit_consumed=result.credit_consumed,
        )

        return {
            "step_results": step_results + [step_result.model_dump()],
            "current_step_index": current_index + 1,
            "credit_checked": True,
        }

    except Exception as e:
        log.error(
            "executor_node_error",
            step_id=step.step_id,
            tool=step.tool,
            error=str(e),
            exc_info=True,
        )

        step_result = StepResult(
            step_id=step.step_id,
            tool=step.tool,
            success=False,
            error=str(e),
        )

        return {
            "step_results": step_results + [step_result.model_dump()],
            "current_step_index": current_index + 1,
            "error": {
                "code": "TOOL_EXECUTION_FAILED",
                "type": "EXECUTION_ERROR",
                "message": f"执行 {step.tool} 失败: {str(e)}",
            },
        }
