"""Tests for Human-in-the-Loop components.

This module tests the Evaluator and HumanInLoopHandler components
to ensure they correctly determine when human input is needed and
properly format requests/responses.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.evaluator import (
    ConfirmationType,
    Evaluator,
    EvaluationResult,
)
from app.core.human_in_loop import (
    HumanInLoopHandler,
    UserInputRequest,
    UserInputResponse,
    UserInputType,
)
from app.core.planner import PlanAction


@pytest.fixture
def mock_gemini_client():
    """Fixture for mock Gemini client."""
    client = AsyncMock()
    # Mock chat method to return JSON response
    client.chat = AsyncMock(
        return_value='{"is_clear": true, "confidence": 0.95, "unclear_params": [], "reason": "All clear"}'
    )
    return client


class TestEvaluator:
    """Tests for the Evaluator component."""

    @pytest.fixture
    def evaluator(self, mock_gemini_client):
        """Create an Evaluator instance."""
        return Evaluator(gemini_client=mock_gemini_client)

    @pytest.mark.asyncio
    async def test_high_risk_operation_requires_confirmation(self, evaluator):
        """Test that high-risk operations require confirmation."""
        plan = PlanAction(
            thought="Creating a campaign",
            action="create_campaign",
            action_input={"name": "Test Campaign", "budget": 100},
            is_complete=False,
        )

        result = await evaluator.evaluate_plan(
            plan=plan,
            user_message="Create a campaign",
            execution_history=[],
        )

        assert result.needs_human_input is True
        assert result.confirmation_type == ConfirmationType.CONFIRM
        assert result.reason == "high_risk"

    @pytest.mark.asyncio
    async def test_spending_operation_requires_confirmation(self, evaluator):
        """Test that spending operations require confirmation."""
        plan = PlanAction(
            thought="Creating a campaign with budget",
            action="create_campaign",
            action_input={"name": "Test", "budget": 100},
            is_complete=False,
        )

        result = await evaluator.evaluate_plan(
            plan=plan,
            user_message="Create campaign with $100 budget",
            execution_history=[],
        )

        assert result.needs_human_input is True
        assert result.confirmation_type == ConfirmationType.CONFIRM

    @pytest.mark.asyncio
    async def test_missing_parameters_require_input(self, evaluator):
        """Test that missing parameters trigger input request."""
        plan = PlanAction(
            thought="Need product info",
            action="generate_image_tool",
            action_input={},  # Missing product_info
            is_complete=False,
        )

        result = await evaluator.evaluate_plan(
            plan=plan,
            user_message="Generate an image",
            execution_history=[],
        )

        assert result.needs_human_input is True
        assert result.confirmation_type == ConfirmationType.INPUT
        assert "product_info" in result.reason

    @pytest.mark.asyncio
    async def test_ambiguous_parameters_require_selection(self, evaluator):
        """Test that ambiguous parameters trigger selection request."""
        plan = PlanAction(
            thought="Generate image with style",
            action="generate_image_tool",
            action_input={
                "product_info": {"name": "Product"},
                "style": "nice",  # Ambiguous
            },
            is_complete=False,
        )

        result = await evaluator.evaluate_plan(
            plan=plan,
            user_message="Generate a nice image",
            execution_history=[],
        )

        # Should detect ambiguous style parameter
        assert result.needs_human_input is True
        assert result.confirmation_type == ConfirmationType.SELECT

    @pytest.mark.asyncio
    async def test_complete_task_needs_no_input(self, evaluator):
        """Test that completed tasks don't need input."""
        plan = PlanAction(
            thought="Task is complete",
            action=None,
            action_input=None,
            is_complete=True,
            final_answer="Done!",
        )

        result = await evaluator.evaluate_plan(
            plan=plan,
            user_message="Do something",
            execution_history=[],
        )

        assert result.needs_human_input is False


class TestHumanInLoopHandler:
    """Tests for the HumanInLoopHandler component."""

    @pytest.fixture
    def handler(self):
        """Create a HumanInLoopHandler instance."""
        return HumanInLoopHandler()

    def test_create_confirmation_request(self, handler):
        """Test creating a confirmation request."""
        request = handler.create_confirmation_request(
            question="Proceed with action?",
            suggested_action={"action": "test", "params": {}},
        )

        assert request.type == UserInputType.CONFIRMATION
        assert request.question == "Proceed with action?"
        assert len(request.options) == 2  # Yes and No
        assert any(opt["value"] == "yes" for opt in request.options)
        assert any(opt["value"] == "no" for opt in request.options)

    def test_create_selection_request(self, handler):
        """Test creating a selection request."""
        options = [
            {"value": "option1", "label": "Option 1"},
            {"value": "option2", "label": "Option 2"},
        ]

        request = handler.create_selection_request(
            question="Choose an option:",
            options=options,
        )

        assert request.type == UserInputType.SELECTION
        assert request.question == "Choose an option:"
        # Should have original options + Other + Cancel
        assert len(request.options) >= 4
        assert any(opt["value"] == "__other__" for opt in request.options)
        assert any(opt["value"] == "__cancel__" for opt in request.options)

    def test_create_input_request(self, handler):
        """Test creating an input request."""
        request = handler.create_input_request(
            question="Enter value:",
            placeholder="Type here...",
        )

        assert request.type == UserInputType.TEXT_INPUT
        assert request.question == "Enter value:"
        assert request.metadata["placeholder"] == "Type here..."
        # Should have Cancel option
        assert any(opt["value"] == "__cancel__" for opt in request.options)

    def test_process_confirmation_yes(self, handler):
        """Test processing a 'yes' confirmation."""
        request = handler.create_confirmation_request(
            question="Confirm?",
        )

        response = handler.process_user_response(
            request=request,
            user_input={"value": "yes"},
        )

        assert response.type == UserInputType.CONFIRMATION
        assert response.value is True
        assert response.cancelled is False

    def test_process_confirmation_no(self, handler):
        """Test processing a 'no' confirmation."""
        request = handler.create_confirmation_request(
            question="Confirm?",
        )

        response = handler.process_user_response(
            request=request,
            user_input={"value": "no"},
        )

        assert response.type == UserInputType.CONFIRMATION
        assert response.value is False
        assert response.cancelled is False

    def test_process_cancel(self, handler):
        """Test processing a cancellation."""
        request = handler.create_selection_request(
            question="Choose:",
            options=[{"value": "opt1", "label": "Option 1"}],
        )

        response = handler.process_user_response(
            request=request,
            user_input={"selected_option": "__cancel__"},
        )

        assert response.cancelled is True

    def test_process_selection_with_option(self, handler):
        """Test processing a selection."""
        request = handler.create_selection_request(
            question="Choose:",
            options=[
                {"value": "modern", "label": "Modern"},
                {"value": "classic", "label": "Classic"},
            ],
        )

        response = handler.process_user_response(
            request=request,
            user_input={"selected_option": "modern"},
        )

        assert response.type == UserInputType.SELECTION
        assert response.value == "modern"
        assert response.selected_option is not None
        assert response.selected_option["label"] == "Modern"
        assert response.cancelled is False

    def test_process_selection_with_other(self, handler):
        """Test processing 'Other' selection with custom value."""
        request = handler.create_selection_request(
            question="Choose:",
            options=[{"value": "opt1", "label": "Option 1"}],
        )

        response = handler.process_user_response(
            request=request,
            user_input={
                "selected_option": "__other__",
                "custom_value": "my custom value",
            },
        )

        assert response.value == "my custom value"
        assert response.cancelled is False

    def test_process_text_input(self, handler):
        """Test processing text input."""
        request = handler.create_input_request(
            question="Enter name:",
        )

        response = handler.process_user_response(
            request=request,
            user_input={"value": "Test Name"},
        )

        assert response.type == UserInputType.TEXT_INPUT
        assert response.value == "Test Name"
        assert response.cancelled is False

    def test_process_empty_text_input_cancels(self, handler):
        """Test that empty text input is treated as cancellation."""
        request = handler.create_input_request(
            question="Enter name:",
        )

        response = handler.process_user_response(
            request=request,
            user_input={"value": ""},
        )

        assert response.cancelled is True

    def test_create_request_from_evaluation(self, handler):
        """Test creating request from evaluation result."""
        evaluation = EvaluationResult(
            needs_human_input=True,
            confirmation_type=ConfirmationType.CONFIRM,
            question="Proceed?",
            suggested_action={"action": "test"},
        )

        request = handler.create_request_from_evaluation(evaluation)

        assert request.type == UserInputType.CONFIRMATION
        assert request.question == "Proceed?"

    def test_format_for_frontend(self, handler):
        """Test formatting request for frontend."""
        request = handler.create_confirmation_request(
            question="Test question?",
        )

        formatted = handler.format_for_frontend(request)

        assert formatted["type"] == "confirmation"
        assert formatted["question"] == "Test question?"
        assert "options" in formatted
        assert "metadata" in formatted
