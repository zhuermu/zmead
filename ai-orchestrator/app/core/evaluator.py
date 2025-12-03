"""Evaluator component for Human-in-the-Loop decision making.

This module provides the Evaluator class that determines when human
confirmation or input is needed during agent execution.

The evaluator checks:
1. Operation risk level (spending, destructive actions)
2. Parameter ambiguity (missing or unclear parameters)
3. User preferences for automation level

Based on these factors, it decides whether to:
- Proceed automatically
- Request confirmation
- Request parameter selection
- Request free-form input
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

from app.core.planner import PlanAction
from app.services.gemini_client import GeminiClient

logger = structlog.get_logger(__name__)


class ConfirmationType(str, Enum):
    """Type of confirmation needed."""

    NONE = "none"  # No confirmation needed
    CONFIRM = "confirm"  # Yes/No confirmation
    SELECT = "select"  # Choose from options
    INPUT = "input"  # Free-form input


@dataclass
class EvaluationResult:
    """Result of evaluating whether human input is needed.

    Attributes:
        needs_human_input: Whether human input is required
        confirmation_type: Type of confirmation needed
        reason: Explanation for why input is needed
        question: Question to ask the user
        options: List of options (for SELECT type)
        suggested_action: Suggested action if user confirms
    """

    needs_human_input: bool
    confirmation_type: ConfirmationType = ConfirmationType.NONE
    reason: str | None = None
    question: str | None = None
    options: list[dict[str, Any]] | None = None
    suggested_action: dict[str, Any] | None = None


class Evaluator:
    """Evaluator for determining when human input is needed.

    The evaluator analyzes planned actions and determines if they
    require human confirmation or input based on:
    - Risk level (spending, destructive operations)
    - Parameter completeness
    - Ambiguity in user intent

    Example:
        evaluator = Evaluator()

        result = await evaluator.evaluate_plan(
            plan=plan,
            user_message="Create a campaign with $100 budget",
            execution_history=[],
        )

        if result.needs_human_input:
            if result.confirmation_type == ConfirmationType.CONFIRM:
                # Ask yes/no question
                print(result.question)
            elif result.confirmation_type == ConfirmationType.SELECT:
                # Show options
                for option in result.options:
                    print(option["label"])
    """

    # Operations that always require confirmation
    HIGH_RISK_OPERATIONS = {
        "create_campaign",
        "update_campaign",
        "pause_campaign",
        "delete_campaign",
        "update_budget",
        "disconnect_ad_account",
    }

    # Operations that involve spending
    SPENDING_OPERATIONS = {
        "create_campaign",
        "update_budget",
        "purchase_credits",
    }

    # Parameters that are commonly ambiguous
    AMBIGUOUS_PARAMETERS = {
        "style",  # Creative style
        "template",  # Landing page template
        "targeting",  # Audience targeting
        "objective",  # Campaign objective
        "placement",  # Ad placement
    }

    # Low-risk operations that should auto-execute without confirmation
    # These are simple tools that don't involve spending, external changes,
    # or sensitive operations
    AUTO_APPROVE_OPERATIONS = {
        "datetime",  # Get current date/time
        "calculator",  # Mathematical calculations
        "google_search",  # Web search (read-only)
        "get_credit_balance",  # Check balance (read-only)
        "get_reports",  # Fetch reports (read-only)
    }

    def __init__(
        self,
        gemini_client: GeminiClient | None = None,
        auto_approve_threshold: float = 0.9,
    ):
        """Initialize the Evaluator.

        Args:
            gemini_client: Gemini client for ambiguity detection
            auto_approve_threshold: Confidence threshold for auto-approval (0-1)
        """
        self.gemini_client = gemini_client or GeminiClient()
        self.auto_approve_threshold = auto_approve_threshold

        logger.info(
            "evaluator_initialized",
            auto_approve_threshold=auto_approve_threshold,
        )

    async def evaluate_plan(
        self,
        plan: PlanAction,
        user_message: str,
        execution_history: list[dict[str, Any]],
        user_id: str | None = None,
    ) -> EvaluationResult:
        """Evaluate if a plan needs human input.

        Args:
            plan: Planned action from Planner
            user_message: Original user message
            execution_history: Previous execution steps
            user_id: User ID for preference lookup

        Returns:
            EvaluationResult indicating if and what type of input is needed
        """
        log = logger.bind(
            action=plan.action,
            user_id=user_id,
        )
        log.info("evaluate_plan_start")

        # If task is complete, no input needed
        if plan.is_complete:
            return EvaluationResult(needs_human_input=False)

        # If no action planned, no input needed
        if not plan.action:
            return EvaluationResult(needs_human_input=False)

        # Check if operation is auto-approved (low risk, simple tools)
        if self._is_auto_approve_operation(plan.action):
            log.info("auto_approve_operation", operation=plan.action)
            return EvaluationResult(needs_human_input=False)

        # Check if operation is high risk
        if self._is_high_risk_operation(plan.action):
            log.info("high_risk_operation_detected", operation=plan.action)
            return await self._create_confirmation_request(
                plan=plan,
                reason="high_risk",
                user_message=user_message,
            )

        # Check if operation involves spending
        if self._is_spending_operation(plan.action, plan.action_input):
            log.info("spending_operation_detected", operation=plan.action)
            return await self._create_confirmation_request(
                plan=plan,
                reason="spending",
                user_message=user_message,
            )

        # Check for missing required parameters
        missing_params = self._check_missing_parameters(plan)
        if missing_params:
            log.info("missing_parameters_detected", params=missing_params)
            return await self._create_input_request(
                plan=plan,
                missing_params=missing_params,
                user_message=user_message,
            )

        # Check for ambiguous parameters
        ambiguous_params = self._check_ambiguous_parameters(plan)
        if ambiguous_params:
            log.info("ambiguous_parameters_detected", params=ambiguous_params)
            return await self._create_selection_request(
                plan=plan,
                ambiguous_params=ambiguous_params,
                user_message=user_message,
            )

        # Check parameter clarity using LLM
        clarity_result = await self._check_parameter_clarity(
            plan=plan,
            user_message=user_message,
        )

        if not clarity_result["is_clear"]:
            log.info(
                "unclear_parameters_detected",
                confidence=clarity_result.get("confidence", 0),
            )
            return await self._create_selection_request(
                plan=plan,
                ambiguous_params=clarity_result.get("unclear_params", []),
                user_message=user_message,
            )

        # All checks passed - no human input needed
        log.info("evaluation_complete", needs_input=False)
        return EvaluationResult(needs_human_input=False)

    def _is_auto_approve_operation(self, operation: str) -> bool:
        """Check if operation should be auto-approved.

        These are low-risk, read-only, or utility operations that
        don't require human confirmation.

        Args:
            operation: Operation name

        Returns:
            True if should auto-approve
        """
        return operation in self.AUTO_APPROVE_OPERATIONS

    def _is_high_risk_operation(self, operation: str) -> bool:
        """Check if operation is high risk.

        Args:
            operation: Operation name

        Returns:
            True if high risk
        """
        return operation in self.HIGH_RISK_OPERATIONS

    def _is_spending_operation(
        self,
        operation: str,
        parameters: dict[str, Any] | None,
    ) -> bool:
        """Check if operation involves spending.

        Args:
            operation: Operation name
            parameters: Operation parameters

        Returns:
            True if involves spending
        """
        if operation not in self.SPENDING_OPERATIONS:
            return False

        # Check if budget is significant (> $50)
        if parameters and "budget" in parameters:
            try:
                budget = float(parameters["budget"])
                return budget > 50
            except (ValueError, TypeError):
                return True  # If can't parse, be safe and ask

        return True

    def _check_missing_parameters(self, plan: PlanAction) -> list[str]:
        """Check for missing required parameters.

        Args:
            plan: Planned action

        Returns:
            List of missing parameter names
        """
        if plan.action_input is None:
            # If action_input is None, check if any params are required
            required_params = {
                "create_campaign": ["name", "budget", "objective"],
                "generate_image_tool": ["product_info"],
                "generate_page_content_tool": ["product_info"],
                "create_landing_page": ["content"],
            }
            return required_params.get(plan.action, [])

        missing = []

        # Define required parameters per operation
        required_params = {
            "create_campaign": ["name", "budget", "objective"],
            "generate_image_tool": ["product_info"],
            "generate_page_content_tool": ["product_info"],
            "create_landing_page": ["content"],
        }

        operation_required = required_params.get(plan.action, [])

        for param in operation_required:
            if param not in plan.action_input or not plan.action_input[param]:
                missing.append(param)

        return missing

    def _check_ambiguous_parameters(self, plan: PlanAction) -> list[str]:
        """Check for ambiguous parameters.

        Args:
            plan: Planned action

        Returns:
            List of ambiguous parameter names
        """
        if not plan.action_input:
            return []

        ambiguous = []

        for param_name in plan.action_input.keys():
            if param_name in self.AMBIGUOUS_PARAMETERS:
                # Check if value is generic or unclear
                value = plan.action_input[param_name]
                if isinstance(value, str) and len(value) < 10:
                    # Short values might be ambiguous
                    ambiguous.append(param_name)

        return ambiguous

    async def _check_parameter_clarity(
        self,
        plan: PlanAction,
        user_message: str,
    ) -> dict[str, Any]:
        """Use LLM to check if parameters are clear from user message.

        Args:
            plan: Planned action
            user_message: User's message

        Returns:
            Dictionary with clarity assessment
        """
        if not plan.action_input:
            return {"is_clear": True, "confidence": 1.0}

        prompt = f"""Analyze if the user's intent is clear for the planned action.

User message: "{user_message}"

Planned action: {plan.action}
Parameters: {plan.action_input}

Questions:
1. Are all parameters clearly specified in the user message?
2. Is there any ambiguity that would benefit from user clarification?
3. What is your confidence level (0-1) that the parameters are correct?

Respond in JSON format:
{{
    "is_clear": true/false,
    "confidence": 0.0-1.0,
    "unclear_params": ["param1", "param2"],
    "reason": "explanation"
}}
"""

        try:
            response = await self.gemini_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )

            # Parse JSON response
            import json

            result = json.loads(response)

            # Check confidence threshold
            confidence = result.get("confidence", 0)
            if confidence < self.auto_approve_threshold:
                result["is_clear"] = False

            return result

        except Exception as e:
            logger.error("parameter_clarity_check_failed", error=str(e))
            # On error, assume clear to avoid blocking execution
            # This is safe because high-risk operations are already checked
            return {
                "is_clear": True,
                "confidence": 0.8,
                "unclear_params": [],
                "reason": "Assuming clear due to check failure",
            }

    async def _create_confirmation_request(
        self,
        plan: PlanAction,
        reason: str,
        user_message: str,
    ) -> EvaluationResult:
        """Create a confirmation request.

        Args:
            plan: Planned action
            reason: Reason for confirmation
            user_message: User's message

        Returns:
            EvaluationResult with confirmation request
        """
        # Generate confirmation question
        question = await self._generate_confirmation_question(
            plan=plan,
            reason=reason,
            user_message=user_message,
        )

        return EvaluationResult(
            needs_human_input=True,
            confirmation_type=ConfirmationType.CONFIRM,
            reason=reason,
            question=question,
            suggested_action={
                "action": plan.action,
                "parameters": plan.action_input,
            },
        )

    async def _create_selection_request(
        self,
        plan: PlanAction,
        ambiguous_params: list[str],
        user_message: str,
    ) -> EvaluationResult:
        """Create a selection request for ambiguous parameters.

        Args:
            plan: Planned action
            ambiguous_params: List of ambiguous parameter names
            user_message: User's message

        Returns:
            EvaluationResult with selection request
        """
        # Generate options for the first ambiguous parameter
        param_name = ambiguous_params[0]

        question, options = await self._generate_parameter_options(
            plan=plan,
            param_name=param_name,
            user_message=user_message,
        )

        return EvaluationResult(
            needs_human_input=True,
            confirmation_type=ConfirmationType.SELECT,
            reason=f"ambiguous_parameter:{param_name}",
            question=question,
            options=options,
        )

    async def _create_input_request(
        self,
        plan: PlanAction,
        missing_params: list[str],
        user_message: str,
    ) -> EvaluationResult:
        """Create an input request for missing parameters.

        Args:
            plan: Planned action
            missing_params: List of missing parameter names
            user_message: User's message

        Returns:
            EvaluationResult with input request
        """
        # Generate question for the first missing parameter
        param_name = missing_params[0]

        question = await self._generate_input_question(
            plan=plan,
            param_name=param_name,
            user_message=user_message,
        )

        return EvaluationResult(
            needs_human_input=True,
            confirmation_type=ConfirmationType.INPUT,
            reason=f"missing_parameter:{param_name}",
            question=question,
        )

    async def _generate_confirmation_question(
        self,
        plan: PlanAction,
        reason: str,
        user_message: str,
    ) -> str:
        """Generate a confirmation question using LLM.

        Args:
            plan: Planned action
            reason: Reason for confirmation
            user_message: User's message

        Returns:
            Confirmation question
        """
        prompt = f"""Generate a clear confirmation question for the user.

User message: "{user_message}"

Planned action: {plan.action}
Parameters: {plan.action_input}
Reason for confirmation: {reason}

Generate a friendly confirmation question that:
1. Summarizes what will be done
2. Highlights key details (budget, targeting, etc.)
3. Asks for confirmation

Keep it concise and clear. Return only the question text.
"""

        try:
            question = await self.gemini_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return question.strip()

        except Exception as e:
            logger.error("generate_confirmation_question_failed", error=str(e))
            # Fallback to generic question
            return f"Confirm: Execute {plan.action} with parameters {plan.action_input}?"

    async def _generate_parameter_options(
        self,
        plan: PlanAction,
        param_name: str,
        user_message: str,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Generate options for an ambiguous parameter.

        Args:
            plan: Planned action
            param_name: Parameter name
            user_message: User's message

        Returns:
            Tuple of (question, options list)
        """
        # Define preset options for common parameters
        preset_options = {
            "style": [
                {"value": "modern", "label": "现代简约", "description": "简洁、专业的现代风格"},
                {"value": "vibrant", "label": "活力多彩", "description": "鲜艳、充满活力的色彩"},
                {"value": "luxury", "label": "高端奢华", "description": "精致、高端的奢华感"},
            ],
            "template": [
                {"value": "product", "label": "产品展示", "description": "突出产品特性和优势"},
                {"value": "promotion", "label": "促销活动", "description": "强调优惠和限时活动"},
                {"value": "brand", "label": "品牌故事", "description": "讲述品牌理念和价值"},
            ],
            "objective": [
                {"value": "conversions", "label": "转化", "description": "优化购买和转化"},
                {"value": "traffic", "label": "流量", "description": "增加网站访问量"},
                {"value": "awareness", "label": "品牌认知", "description": "提升品牌知名度"},
            ],
        }

        options = preset_options.get(param_name, [])

        # Always add "Other" and "Cancel" options
        options.extend(
            [
                {
                    "value": "__other__",
                    "label": "其他",
                    "description": "自定义输入",
                },
                {
                    "value": "__cancel__",
                    "label": "取消",
                    "description": "取消此操作",
                },
            ]
        )

        # Generate question
        question = f"请选择 {param_name}："

        return question, options

    async def _generate_input_question(
        self,
        plan: PlanAction,
        param_name: str,
        user_message: str,
    ) -> str:
        """Generate a question for missing parameter input.

        Args:
            plan: Planned action
            param_name: Parameter name
            user_message: User's message

        Returns:
            Input question
        """
        # Map parameter names to friendly questions
        param_questions = {
            "product_info": "请提供产品信息或产品链接：",
            "name": "请输入名称：",
            "budget": "请输入预算金额（美元）：",
            "url": "请输入网址：",
            "content": "请输入内容：",
        }

        return param_questions.get(param_name, f"请输入 {param_name}：")
