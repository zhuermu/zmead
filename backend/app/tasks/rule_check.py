"""Rule checking background tasks for Campaign Automation."""

import asyncio
import logging
from datetime import UTC, datetime

import httpx
from celery import shared_task

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _check_campaign_rules_async() -> dict:
    """
    Check campaign automation rules.
    
    This task calls the AI Orchestrator to check all campaign automation rules
    and execute actions when conditions are met.
    """
    try:
        # Call AI Orchestrator rule check endpoint
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{settings.ai_orchestrator_url}/api/campaign-automation/check-rules",
                headers={
                    "Authorization": f"Bearer {settings.ai_orchestrator_service_token}",
                    "Content-Type": "application/json",
                },
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    "Campaign rules checked successfully",
                    extra={
                        "rules_checked": result.get("rules_checked", 0),
                        "actions_taken": result.get("actions_taken", 0),
                    },
                )
                return {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "status": "success",
                    "message": "Campaign rules checked successfully",
                    "rules_checked": result.get("rules_checked", 0),
                    "actions_taken": result.get("actions_taken", 0),
                }
            else:
                logger.error(
                    f"Failed to check campaign rules: {response.status_code}",
                    extra={"response": response.text},
                )
                return {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "status": "error",
                    "message": f"Failed to check rules: {response.status_code}",
                }
                
    except Exception as e:
        logger.error(
            f"Error checking campaign rules: {e}",
            extra={"error": str(e)},
        )
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "error",
            "message": f"Error checking rules: {str(e)}",
        }


@shared_task(
    name="app.tasks.rule_check.check_campaign_rules",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def check_campaign_rules(self) -> dict:
    """
    Celery task to check campaign automation rules.
    
    This task is scheduled to run every 6 hours to check all campaign
    automation rules and execute actions when conditions are met.
    
    Requirements: 6.2, 6.3, 6.4, 6.5
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(_check_campaign_rules_async())
    except Exception as e:
        logger.error(f"Campaign rule check task failed: {e}")
        # Retry on failure
        raise self.retry(exc=e)
