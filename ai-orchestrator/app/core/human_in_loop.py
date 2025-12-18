"""Human-in-the-Loop handler for agent interactions.

This module provides the HumanInLoopHandler class that manages
user interactions during agent execution, including:
- Confirmation requests (Yes/No)
- Selection requests (Choose from options)
- Input requests (Free-form text)

The handler formats requests for the frontend and processes
user responses back into the agent execution flow.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

from app.core.evaluator import ConfirmationType, EvaluationResult

logger = structlog.get_logger(__name__)


class UserInputType(str, Enum):
    """Type of user input request."""

    CONFIRMATION = "confirmation"  # Yes/No confirmation
    SELECTION = "selection"  # Choose from options
    INPUT = "input"  # Free-form text input


@dataclass
class UserInputRequest:
    """Request for user input.

    This is the format sent to the frontend for rendering.

    Attributes:
        type: Type of input request
        question: Question to display to user
        options: List of options (for selection)
        default_value: Default value (optional)
        metadata: Additional metadata for rendering
    """

    type: UserInputType
    question: str
    options: list[dict[str, Any]] | None = None
    default_value: Any | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "question": self.question,
            "options": self.options,
            "default_value": self.default_value,
            "metadata": self.metadata or {},
        }


@dataclass
class UserInputResponse:
    """Response from user input.

    Attributes:
        type: Type of input that was requested
        value: User's response value
        selected_option: Selected option (for selection type)
        cancelled: Whether user cancelled
        metadata: Additional metadata
    """

    type: UserInputType
    value: Any
    selected_option: dict[str, Any] | None = None
    cancelled: bool = False
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserInputResponse":
        """Create from dictionary."""
        return cls(
            type=UserInputType(data["type"]),
            value=data["value"],
            selected_option=data.get("selected_option"),
            cancelled=data.get("cancelled", False),
            metadata=data.get("metadata"),
        )


class HumanInLoopHandler:
    """Handler for human-in-the-loop interactions.

    This class manages the creation of user input requests and
    processing of user responses during agent execution.

    Example:
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
    """

    def __init__(self):
        """Initialize the handler."""
        logger.info("human_in_loop_handler_initialized")

    def create_request_from_evaluation(
        self,
        evaluation: EvaluationResult,
    ) -> UserInputRequest:
        """Create a user input request from an evaluation result.

        Args:
            evaluation: Evaluation result from Evaluator

        Returns:
            UserInputRequest formatted for frontend
        """
        log = logger.bind(
            confirmation_type=evaluation.confirmation_type.value,
        )
        log.info("create_request_from_evaluation")

        if evaluation.confirmation_type == ConfirmationType.CONFIRM:
            return self.create_confirmation_request(
                question=evaluation.question or "Confirm this action?",
                suggested_action=evaluation.suggested_action,
                reason=evaluation.reason,
            )

        elif evaluation.confirmation_type == ConfirmationType.SELECT:
            return self.create_selection_request(
                question=evaluation.question or "Please select an option:",
                options=evaluation.options or [],
                reason=evaluation.reason,
            )

        elif evaluation.confirmation_type == ConfirmationType.INPUT:
            return self.create_input_request(
                question=evaluation.question or "Please provide input:",
                reason=evaluation.reason,
            )

        else:
            # Should not happen, but handle gracefully
            return self.create_confirmation_request(
                question="Proceed with this action?",
                suggested_action=evaluation.suggested_action,
            )

    def create_confirmation_request(
        self,
        question: str,
        suggested_action: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> UserInputRequest:
        """Create a confirmation request (Yes/No).

        Args:
            question: Question to ask user
            suggested_action: Action that will be executed if confirmed
            reason: Reason for confirmation

        Returns:
            UserInputRequest for confirmation
        """
        options = [
            {
                "value": "yes",
                "label": "✅ 确认",
                "description": "继续执行",
                "primary": True,
            },
            {
                "value": "no",
                "label": "❌ 取消",
                "description": "取消此操作",
                "primary": False,
            },
        ]

        metadata = {
            "suggested_action": suggested_action,
            "reason": reason,
        }

        return UserInputRequest(
            type=UserInputType.CONFIRMATION,
            question=question,
            options=options,
            metadata=metadata,
        )

    def create_selection_request(
        self,
        question: str,
        options: list[dict[str, Any]],
        reason: str | None = None,
    ) -> UserInputRequest:
        """Create a selection request (choose from options).

        Args:
            question: Question to ask user
            options: List of options to choose from
            reason: Reason for selection

        Returns:
            UserInputRequest for selection
        """
        # Ensure options have required fields
        formatted_options = []
        for i, option in enumerate(options):
            formatted_option = {
                "value": option.get("value", f"option_{i}"),
                "label": option.get("label", f"Option {i + 1}"),
                "description": option.get("description"),
                "primary": option.get("primary", False),
            }
            formatted_options.append(formatted_option)

        # Ensure "Other" and "Cancel" options are present
        has_other = any(opt["value"] == "__other__" for opt in formatted_options)
        has_cancel = any(opt["value"] == "__cancel__" for opt in formatted_options)

        if not has_other:
            formatted_options.append(
                {
                    "value": "__other__",
                    "label": "➕ 其他",
                    "description": "自定义输入",
                    "primary": False,
                }
            )

        if not has_cancel:
            formatted_options.append(
                {
                    "value": "__cancel__",
                    "label": "❌ 取消",
                    "description": "取消此操作",
                    "primary": False,
                }
            )

        metadata = {
            "reason": reason,
            "allow_custom": True,
        }

        return UserInputRequest(
            type=UserInputType.SELECTION,
            question=question,
            options=formatted_options,
            metadata=metadata,
        )

    def create_input_request(
        self,
        question: str,
        placeholder: str | None = None,
        default_value: str | None = None,
        reason: str | None = None,
    ) -> UserInputRequest:
        """Create a text input request.

        Args:
            question: Question to ask user
            placeholder: Placeholder text for input field
            default_value: Default value
            reason: Reason for input

        Returns:
            UserInputRequest for text input
        """
        # Add cancel option
        options = [
            {
                "value": "__cancel__",
                "label": "❌ 取消",
                "description": "取消此操作",
                "primary": False,
            }
        ]

        metadata = {
            "placeholder": placeholder or "请输入...",
            "reason": reason,
        }

        return UserInputRequest(
            type=UserInputType.INPUT,
            question=question,
            options=options,
            default_value=default_value,
            metadata=metadata,
        )

    def process_user_response(
        self,
        request: UserInputRequest,
        user_input: dict[str, Any],
    ) -> UserInputResponse:
        """Process user's response to an input request.

        Args:
            request: Original input request
            user_input: User's response data

        Returns:
            UserInputResponse with processed response
        """
        log = logger.bind(request_type=request.type.value)
        log.info("process_user_response")

        # Extract value from user input
        value = user_input.get("value")
        selected_option_value = user_input.get("selected_option")

        # Find selected option if provided
        selected_option = None
        if selected_option_value and request.options:
            for option in request.options:
                if option["value"] == selected_option_value:
                    selected_option = option
                    break

        # Check for cancellation
        cancelled = False
        if value == "__cancel__" or selected_option_value == "__cancel__":
            cancelled = True
            log.info("user_cancelled")

        # Handle "Other" option for selection
        custom_value_provided = False
        if selected_option_value == "__other__":
            # User wants to provide custom input
            # Frontend should prompt for text input
            custom_value = user_input.get("custom_value")
            if custom_value:
                value = custom_value
                custom_value_provided = True
                log.info("custom_value_provided", value=custom_value)
            else:
                # No custom value provided, treat as cancelled
                cancelled = True
                log.info("no_custom_value_provided")

        # Process based on request type
        if request.type == UserInputType.CONFIRMATION:
            # Convert to boolean
            if isinstance(value, str):
                value = value.lower() in ("yes", "y", "true", "1", "确认")

        elif request.type == UserInputType.SELECTION:
            # Value is the selected option value
            # But if custom value was provided, use that instead
            if not custom_value_provided and selected_option:
                value = selected_option["value"]

        elif request.type == UserInputType.INPUT:
            # Value is the text input
            if not value or (isinstance(value, str) and not value.strip()):
                cancelled = True
                log.info("empty_text_input")

        response = UserInputResponse(
            type=request.type,
            value=value,
            selected_option=selected_option,
            cancelled=cancelled,
            metadata=user_input.get("metadata"),
        )

        log.info(
            "user_response_processed",
            cancelled=cancelled,
            has_value=value is not None,
        )

        return response

    def format_for_frontend(
        self,
        request: UserInputRequest,
    ) -> dict[str, Any]:
        """Format request for frontend rendering.

        Args:
            request: User input request

        Returns:
            Dictionary formatted for frontend
        """
        return {
            "type": request.type.value,
            "question": request.question,
            "options": request.options,
            "default_value": request.default_value,
            "metadata": request.metadata or {},
            "timestamp": None,  # Frontend can add timestamp
        }

    def create_error_request(
        self,
        error_message: str,
        allow_retry: bool = True,
    ) -> UserInputRequest:
        """Create an error notification with retry option.

        Args:
            error_message: Error message to display
            allow_retry: Whether to allow retry

        Returns:
            UserInputRequest for error handling
        """
        options = []

        if allow_retry:
            options.append(
                {
                    "value": "retry",
                    "label": "🔄 重试",
                    "description": "重新尝试",
                    "primary": True,
                }
            )

        options.append(
            {
                "value": "cancel",
                "label": "❌ 取消",
                "description": "取消操作",
                "primary": False,
            }
        )

        return UserInputRequest(
            type=UserInputType.CONFIRMATION,
            question=f"❌ 错误：{error_message}",
            options=options,
            metadata={"is_error": True},
        )

    def create_success_notification(
        self,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a success notification.

        Args:
            message: Success message
            data: Additional data to display

        Returns:
            Dictionary formatted for frontend
        """
        return {
            "type": "notification",
            "status": "success",
            "message": message,
            "data": data,
            "timestamp": None,  # Frontend can add timestamp
        }

    def create_progress_update(
        self,
        message: str,
        progress: float | None = None,
        step: int | None = None,
        total_steps: int | None = None,
    ) -> dict[str, Any]:
        """Create a progress update notification.

        Args:
            message: Progress message
            progress: Progress percentage (0-1)
            step: Current step number
            total_steps: Total number of steps

        Returns:
            Dictionary formatted for frontend
        """
        return {
            "type": "notification",
            "status": "progress",
            "message": message,
            "progress": progress,
            "step": step,
            "total_steps": total_steps,
            "timestamp": None,  # Frontend can add timestamp
        }
