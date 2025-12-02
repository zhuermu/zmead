"""
Campaign Automation API endpoints.

Provides HTTP endpoints for campaign automation functionality,
including rule checking for Celery tasks.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import validate_service_token
from app.modules.campaign_automation.engines.rule_engine import RuleEngine

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/campaign-automation", tags=["campaign-automation"])


class RuleCheckResponse(BaseModel):
    """Response model for rule checking"""
    
    status: str
    rules_checked: int
    actions_taken: int
    results: list[dict]
    message: str


@router.post("/check-rules", response_model=RuleCheckResponse)
async def check_rules(
    user_id: str | None = None,
    _token: str = Depends(validate_service_token),
) -> RuleCheckResponse:
    """
    Check campaign automation rules and execute actions.
    
    This endpoint is called by the Celery periodic task to check all
    campaign automation rules and execute actions when conditions are met.
    
    Args:
        user_id: Optional user ID to check rules for specific user
        _token: Service authentication token (from dependency)
    
    Returns:
        RuleCheckResponse: Rule checking results
        
    Requirements: 6.2, 6.3, 6.4, 6.5
    """
    try:
        logger.info(
            "check_rules_start",
            user_id=user_id,
        )
        
        # Initialize Rule Engine
        rule_engine = RuleEngine()
        
        # Check rules
        results = await rule_engine.check_rules(user_id=user_id)
        
        # Count actions taken
        actions_taken = sum(
            len(result.get("actions_taken", []))
            for result in results
        )
        
        logger.info(
            "check_rules_complete",
            rules_checked=len(results),
            actions_taken=actions_taken,
        )
        
        return RuleCheckResponse(
            status="success",
            rules_checked=len(results),
            actions_taken=actions_taken,
            results=results,
            message=f"Checked {len(results)} rules, took {actions_taken} actions",
        )
        
    except Exception as e:
        logger.error(
            "check_rules_error",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check rules: {str(e)}",
        )
