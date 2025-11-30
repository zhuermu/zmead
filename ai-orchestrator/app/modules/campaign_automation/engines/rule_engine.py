"""
Rule Engine for Campaign Automation.

This module implements the rule engine that automatically executes
predefined rules for campaign management, such as pausing underperforming
adsets or adjusting budgets based on performance metrics.

Requirements: 6.1, 6.3, 6.4, 6.5
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import redis.asyncio as redis
from app.core.redis_client import get_redis
from app.modules.campaign_automation.adapters.router import PlatformRouter
from app.modules.campaign_automation.models import (
    Rule,
    RuleAction,
    RuleAppliesTo,
    RuleCondition,
)
from app.services.mcp_client import MCPClient

logger = logging.getLogger(__name__)


class RuleEngine:
    """
    Rule Engine for automated campaign management.
    
    Manages automation rules that automatically execute actions based on
    performance conditions. Rules are checked periodically (default: every 6 hours)
    and actions are executed when conditions are met.
    
    Example:
        >>> engine = RuleEngine()
        >>> rule = await engine.create_rule(
        ...     rule_name="Auto Pause High CPA",
        ...     condition={
        ...         "metric": "cpa",
        ...         "operator": "greater_than",
        ...         "value": 50,
        ...         "time_range": "24h"
        ...     },
        ...     action={"type": "pause_adset"},
        ...     applies_to={"campaign_ids": ["campaign_123"]},
        ...     context={"user_id": "user_123"}
        ... )
    """
    
    def __init__(
        self,
        mcp_client: Optional[MCPClient] = None,
        redis_client: Optional[redis.Redis] = None,
    ):
        """
        Initialize Rule Engine.
        
        Args:
            mcp_client: MCP client for data access
            redis_client: Redis client for rule storage (optional, will use global if not provided)
        """
        self.mcp_client = mcp_client or MCPClient()
        self._redis_client = redis_client
        self.platform_router = PlatformRouter()
        self.rule_prefix = "campaign_automation:rule:"
        self.log_prefix = "campaign_automation:rule_log:"
    
    async def _get_redis(self) -> redis.Redis:
        """Get Redis client instance."""
        if self._redis_client is not None:
            return self._redis_client
        return await get_redis()
    
    async def create_rule(
        self,
        rule_name: str,
        condition: dict,
        action: dict,
        applies_to: dict,
        context: dict,
        check_interval: int = 21600,  # 6 hours default
    ) -> dict:
        """
        Create an automation rule.
        
        Args:
            rule_name: Name of the rule
            condition: Rule condition configuration
            action: Rule action configuration
            applies_to: Application scope (campaign_ids, adset_ids)
            context: User context (user_id, session_id)
            check_interval: Check interval in seconds (default: 6 hours)
        
        Returns:
            dict: Created rule information
            
        Validates: Requirements 6.1
        """
        try:
            # Generate rule ID
            rule_id = f"rule_{uuid.uuid4().hex[:12]}"
            
            # Create rule model
            rule = Rule(
                rule_id=rule_id,
                rule_name=rule_name,
                condition=RuleCondition(**condition),
                action=RuleAction(**action),
                applies_to=RuleAppliesTo(**applies_to),
                check_interval=check_interval,
                enabled=True,
                last_checked_at=None,
                created_at=datetime.now(timezone.utc),
            )
            
            # Store rule in Redis
            redis_client = await self._get_redis()
            rule_key = f"{self.rule_prefix}{rule_id}"
            await redis_client.set(
                rule_key,
                rule.model_dump_json(),
                ex=None,  # No expiration for rules
            )
            
            # Store user association
            user_rules_key = f"campaign_automation:user_rules:{context['user_id']}"
            await redis_client.sadd(user_rules_key, rule_id)
            
            logger.info(
                f"Rule created: {rule_id}",
                extra={
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "user_id": context.get("user_id"),
                    "check_interval": check_interval,
                },
            )
            
            return {
                "status": "success",
                "rule_id": rule_id,
                "message": f"规则已创建，每 {check_interval // 3600} 小时检查一次",
            }
            
        except Exception as e:
            logger.error(
                f"Failed to create rule: {e}",
                extra={
                    "rule_name": rule_name,
                    "user_id": context.get("user_id"),
                    "error": str(e),
                },
            )
            return {
                "status": "error",
                "error": {
                    "code": "1000",
                    "type": "RULE_CREATION_FAILED",
                    "message": f"Failed to create rule: {str(e)}",
                },
            }
    
    async def check_rules(self, user_id: Optional[str] = None) -> list[dict]:
        """
        Check all rules and execute actions when conditions are met.
        
        This method is called periodically by the Celery task.
        
        Args:
            user_id: Optional user ID to check rules for specific user
        
        Returns:
            list[dict]: List of rule execution results
            
        Validates: Requirements 6.3
        """
        results = []
        
        try:
            # Get all rules to check
            redis_client = await self._get_redis()
            if user_id:
                # Check rules for specific user
                user_rules_key = f"campaign_automation:user_rules:{user_id}"
                rule_ids = await redis_client.smembers(user_rules_key)
            else:
                # Check all rules
                rule_keys = await redis_client.keys(f"{self.rule_prefix}*")
                rule_ids = [key.split(":")[-1] for key in rule_keys]
            
            logger.info(
                f"Checking {len(rule_ids)} rules",
                extra={"user_id": user_id, "rule_count": len(rule_ids)},
            )
            
            for rule_id in rule_ids:
                try:
                    result = await self._check_single_rule(rule_id)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(
                        f"Failed to check rule {rule_id}: {e}",
                        extra={"rule_id": rule_id, "error": str(e)},
                    )
            
            return results
            
        except Exception as e:
            logger.error(
                f"Failed to check rules: {e}",
                extra={"user_id": user_id, "error": str(e)},
            )
            return results
    
    async def _check_single_rule(self, rule_id: str) -> Optional[dict]:
        """
        Check a single rule and execute action if condition is met.
        
        Args:
            rule_id: Rule ID to check
        
        Returns:
            dict: Execution result if action was taken, None otherwise
        """
        # Load rule
        redis_client = await self._get_redis()
        rule_key = f"{self.rule_prefix}{rule_id}"
        rule_data = await redis_client.get(rule_key)
        
        if not rule_data:
            logger.warning(f"Rule not found: {rule_id}")
            return None
        
        rule = Rule.model_validate_json(rule_data)
        
        # Check if rule is enabled
        if not rule.enabled:
            return None
        
        # Check if it's time to check this rule
        if rule.last_checked_at:
            time_since_check = (
                datetime.now(timezone.utc) - rule.last_checked_at
            ).total_seconds()
            if time_since_check < rule.check_interval:
                return None
        
        # Get targets to check
        targets = await self._get_rule_targets(rule)
        
        # Check condition for each target
        actions_taken = []
        for target in targets:
            if await self._evaluate_condition(rule.condition, target):
                # Condition met, execute action
                action_result = await self.execute_rule_action(
                    rule_id=rule_id,
                    target_id=target["id"],
                    target_type=target["type"],
                    action=rule.action.model_dump(),
                    platform=target.get("platform", "meta"),
                )
                
                if action_result["status"] == "success":
                    actions_taken.append({
                        "target_id": target["id"],
                        "target_type": target["type"],
                        "action": rule.action.type,
                        "result": action_result,
                    })
        
        # Update last checked timestamp
        rule.last_checked_at = datetime.now(timezone.utc)
        await redis_client.set(
            rule_key,
            rule.model_dump_json(),
            ex=None,
        )
        
        if actions_taken:
            return {
                "rule_id": rule_id,
                "rule_name": rule.rule_name,
                "actions_taken": actions_taken,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        
        return None
    
    async def _get_rule_targets(self, rule: Rule) -> list[dict]:
        """
        Get targets (campaigns/adsets) that the rule applies to.
        
        Args:
            rule: Rule to get targets for
        
        Returns:
            list[dict]: List of targets with their IDs and types
        """
        targets = []
        
        # Add campaign targets
        if rule.applies_to.campaign_ids:
            for campaign_id in rule.applies_to.campaign_ids:
                targets.append({
                    "id": campaign_id,
                    "type": "campaign",
                })
        
        # Add adset targets
        if rule.applies_to.adset_ids:
            for adset_id in rule.applies_to.adset_ids:
                targets.append({
                    "id": adset_id,
                    "type": "adset",
                })
        
        return targets
    
    async def _evaluate_condition(
        self,
        condition: RuleCondition,
        target: dict,
    ) -> bool:
        """
        Evaluate if a condition is met for a target.
        
        Args:
            condition: Rule condition to evaluate
            target: Target (campaign/adset) to evaluate
        
        Returns:
            bool: True if condition is met, False otherwise
        """
        try:
            # Get performance data for target
            metric_value = await self._get_metric_value(
                target_id=target["id"],
                target_type=target["type"],
                metric=condition.metric,
                time_range=condition.time_range,
            )
            
            if metric_value is None:
                return False
            
            # Evaluate condition
            if condition.operator == "greater_than":
                return metric_value > condition.value
            elif condition.operator == "less_than":
                return metric_value < condition.value
            elif condition.operator == "equals":
                return metric_value == condition.value
            elif condition.operator == "greater_than_or_equal":
                return metric_value >= condition.value
            elif condition.operator == "less_than_or_equal":
                return metric_value <= condition.value
            else:
                logger.warning(f"Unknown operator: {condition.operator}")
                return False
                
        except Exception as e:
            logger.error(
                f"Failed to evaluate condition: {e}",
                extra={
                    "target_id": target["id"],
                    "metric": condition.metric,
                    "error": str(e),
                },
            )
            return False
    
    async def _get_metric_value(
        self,
        target_id: str,
        target_type: str,
        metric: str,
        time_range: str,
    ) -> Optional[float]:
        """
        Get metric value for a target from performance data.
        
        Args:
            target_id: Target ID (campaign or adset)
            target_type: Target type ("campaign" or "adset")
            metric: Metric name (cpa, roas, ctr, spend, conversions)
            time_range: Time range (e.g., "24h", "7d")
        
        Returns:
            float: Metric value, or None if not available
        """
        try:
            # Parse time range
            hours = self._parse_time_range(time_range)
            start_date = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Get performance data from MCP
            # Note: This assumes the MCP tool returns aggregated metrics
            # In production, this would call the actual MCP tool
            result = await self.mcp_client.call_tool(
                "get_reports",
                {
                    f"{target_type}_id": target_id,
                    "date_range": {
                        "start_date": start_date.isoformat(),
                        "end_date": datetime.now(timezone.utc).isoformat(),
                    },
                    "metrics": [metric],
                },
            )
            
            if result.get("status") == "success" and result.get("data"):
                return result["data"].get(metric)
            
            return None
            
        except Exception as e:
            logger.error(
                f"Failed to get metric value: {e}",
                extra={
                    "target_id": target_id,
                    "metric": metric,
                    "error": str(e),
                },
            )
            return None
    
    def _parse_time_range(self, time_range: str) -> int:
        """
        Parse time range string to hours.
        
        Args:
            time_range: Time range string (e.g., "24h", "7d")
        
        Returns:
            int: Number of hours
        """
        try:
            if time_range.endswith("h"):
                return int(time_range[:-1])
            elif time_range.endswith("d"):
                return int(time_range[:-1]) * 24
            else:
                # Default to 24 hours
                return 24
        except ValueError:
            # If parsing fails, default to 24 hours
            return 24
    
    async def execute_rule_action(
        self,
        rule_id: str,
        target_id: str,
        target_type: str,
        action: dict,
        platform: str = "meta",
    ) -> dict:
        """
        Execute a rule action on a target.
        
        Args:
            rule_id: Rule ID
            target_id: Target ID (campaign or adset)
            target_type: Target type ("campaign" or "adset")
            action: Action configuration
            platform: Platform name
        
        Returns:
            dict: Execution result
            
        Validates: Requirements 6.3, 6.4
        """
        try:
            action_type = action["type"]
            adapter = self.platform_router.get_adapter(platform)
            
            if not adapter:
                return {
                    "status": "error",
                    "error": {
                        "code": "1001",
                        "type": "INVALID_PLATFORM",
                        "message": f"Unsupported platform: {platform}",
                    },
                }
            
            result = None
            
            # Execute action based on type
            if action_type == "pause_adset":
                if target_type == "adset":
                    result = await adapter.pause_adset(target_id)
                else:
                    return {
                        "status": "error",
                        "error": {
                            "code": "1001",
                            "type": "INVALID_ACTION",
                            "message": "pause_adset can only be applied to adsets",
                        },
                    }
            
            elif action_type == "pause_campaign":
                if target_type == "campaign":
                    result = await adapter.pause_campaign(target_id)
                else:
                    return {
                        "status": "error",
                        "error": {
                            "code": "1001",
                            "type": "INVALID_ACTION",
                            "message": "pause_campaign can only be applied to campaigns",
                        },
                    }
            
            elif action_type == "increase_budget":
                if target_type == "adset":
                    # Get current budget
                    current_budget = await self._get_current_budget(target_id, platform)
                    if current_budget:
                        increase_pct = action.get("parameters", {}).get("percentage", 20)
                        new_budget = current_budget * (1 + increase_pct / 100)
                        result = await adapter.update_budget(target_id, new_budget)
                else:
                    return {
                        "status": "error",
                        "error": {
                            "code": "1001",
                            "type": "INVALID_ACTION",
                            "message": "increase_budget can only be applied to adsets",
                        },
                    }
            
            elif action_type == "decrease_budget":
                if target_type == "adset":
                    # Get current budget
                    current_budget = await self._get_current_budget(target_id, platform)
                    if current_budget:
                        decrease_pct = action.get("parameters", {}).get("percentage", 20)
                        new_budget = current_budget * (1 - decrease_pct / 100)
                        result = await adapter.update_budget(target_id, new_budget)
                else:
                    return {
                        "status": "error",
                        "error": {
                            "code": "1001",
                            "type": "INVALID_ACTION",
                            "message": "decrease_budget can only be applied to adsets",
                        },
                    }
            
            elif action_type == "send_notification":
                # Send notification via MCP
                result = await self.mcp_client.call_tool(
                    "create_notification",
                    {
                        "title": f"Rule Triggered: {rule_id}",
                        "message": action.get("parameters", {}).get(
                            "message",
                            f"Rule action triggered for {target_type} {target_id}",
                        ),
                        "type": "rule_trigger",
                    },
                )
            
            else:
                return {
                    "status": "error",
                    "error": {
                        "code": "1001",
                        "type": "UNKNOWN_ACTION",
                        "message": f"Unknown action type: {action_type}",
                    },
                }
            
            # Log the action
            await self._log_rule_execution(
                rule_id=rule_id,
                target_id=target_id,
                target_type=target_type,
                action_type=action_type,
                result=result,
            )
            
            logger.info(
                f"Rule action executed: {action_type}",
                extra={
                    "rule_id": rule_id,
                    "target_id": target_id,
                    "target_type": target_type,
                    "action_type": action_type,
                },
            )
            
            return {
                "status": "success",
                "action": action_type,
                "target_id": target_id,
                "result": result,
            }
            
        except Exception as e:
            logger.error(
                f"Failed to execute rule action: {e}",
                extra={
                    "rule_id": rule_id,
                    "target_id": target_id,
                    "action_type": action.get("type"),
                    "error": str(e),
                },
            )
            return {
                "status": "error",
                "error": {
                    "code": "1000",
                    "type": "ACTION_EXECUTION_FAILED",
                    "message": f"Failed to execute action: {str(e)}",
                },
            }
    
    async def _get_current_budget(
        self,
        adset_id: str,
        platform: str,
    ) -> Optional[float]:
        """
        Get current budget for an adset.
        
        Args:
            adset_id: Adset ID
            platform: Platform name
        
        Returns:
            float: Current budget, or None if not available
        """
        try:
            adapter = self.platform_router.get_adapter(platform)
            if not adapter:
                return None
            adset_data = await adapter.get_adset(adset_id)
            return adset_data.get("daily_budget")
        except Exception as e:
            logger.error(
                f"Failed to get current budget: {e}",
                extra={"adset_id": adset_id, "error": str(e)},
            )
            return None
    
    async def _log_rule_execution(
        self,
        rule_id: str,
        target_id: str,
        target_type: str,
        action_type: str,
        result: Any,
    ) -> None:
        """
        Log rule execution for audit trail.
        
        Args:
            rule_id: Rule ID
            target_id: Target ID
            target_type: Target type
            action_type: Action type
            result: Execution result
            
        Validates: Requirements 6.4
        """
        try:
            log_entry = {
                "rule_id": rule_id,
                "target_id": target_id,
                "target_type": target_type,
                "action_type": action_type,
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            # Store log in Redis (with 30-day expiration)
            redis_client = await self._get_redis()
            log_key = f"{self.log_prefix}{rule_id}:{datetime.now(timezone.utc).timestamp()}"
            await redis_client.set(
                log_key,
                str(log_entry),
                ex=30 * 24 * 3600,  # 30 days
            )
            
        except Exception as e:
            logger.error(
                f"Failed to log rule execution: {e}",
                extra={"rule_id": rule_id, "error": str(e)},
            )
    
    async def get_rule(self, rule_id: str) -> Optional[dict]:
        """
        Get a rule by ID.
        
        Args:
            rule_id: Rule ID
        
        Returns:
            dict: Rule data, or None if not found
        """
        try:
            redis_client = await self._get_redis()
            rule_key = f"{self.rule_prefix}{rule_id}"
            rule_data = await redis_client.get(rule_key)
            
            if not rule_data:
                return None
            
            rule = Rule.model_validate_json(rule_data)
            return rule.model_dump()
            
        except Exception as e:
            logger.error(
                f"Failed to get rule: {e}",
                extra={"rule_id": rule_id, "error": str(e)},
            )
            return None
    
    async def list_rules(self, user_id: str) -> list[dict]:
        """
        List all rules for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            list[dict]: List of rules
        """
        try:
            redis_client = await self._get_redis()
            user_rules_key = f"campaign_automation:user_rules:{user_id}"
            rule_ids = await redis_client.smembers(user_rules_key)
            
            rules = []
            for rule_id in rule_ids:
                rule = await self.get_rule(rule_id)
                if rule:
                    rules.append(rule)
            
            return rules
            
        except Exception as e:
            logger.error(
                f"Failed to list rules: {e}",
                extra={"user_id": user_id, "error": str(e)},
            )
            return []
    
    async def delete_rule(self, rule_id: str, user_id: str) -> dict:
        """
        Delete a rule.
        
        Args:
            rule_id: Rule ID
            user_id: User ID
        
        Returns:
            dict: Deletion result
        """
        try:
            redis_client = await self._get_redis()
            # Delete rule
            rule_key = f"{self.rule_prefix}{rule_id}"
            await redis_client.delete(rule_key)
            
            # Remove from user's rule set
            user_rules_key = f"campaign_automation:user_rules:{user_id}"
            await redis_client.srem(user_rules_key, rule_id)
            
            logger.info(
                f"Rule deleted: {rule_id}",
                extra={"rule_id": rule_id, "user_id": user_id},
            )
            
            return {
                "status": "success",
                "message": "Rule deleted successfully",
            }
            
        except Exception as e:
            logger.error(
                f"Failed to delete rule: {e}",
                extra={"rule_id": rule_id, "error": str(e)},
            )
            return {
                "status": "error",
                "error": {
                    "code": "1000",
                    "type": "RULE_DELETION_FAILED",
                    "message": f"Failed to delete rule: {str(e)}",
                },
            }
