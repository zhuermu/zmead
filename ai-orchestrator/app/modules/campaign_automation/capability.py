"""
Campaign Automation capability - Main entry point for the module.

This module provides the main entry point for Campaign Automation functionality,
including campaign creation, budget optimization, A/B testing, and rule-based automation.

Requirements: All requirements from requirements.md
"""

import structlog
from redis.asyncio import Redis

from app.core.errors import ErrorHandler
from app.services.gemini_client import GeminiClient, GeminiError
from app.services.mcp_client import MCPClient, MCPError
from app.modules.campaign_automation.managers.campaign_manager import CampaignManager
from app.modules.campaign_automation.managers.ab_test_manager import ABTestManager
from app.modules.campaign_automation.optimizers.budget_optimizer import BudgetOptimizer
from app.modules.campaign_automation.engines.rule_engine import RuleEngine
from app.modules.campaign_automation.adapters.router import PlatformRouter

logger = structlog.get_logger(__name__)


class CampaignAutomation:
    """Campaign Automation 功能模块主入口
    
    Provides comprehensive campaign automation capabilities including:
    - Automated campaign structure generation (Campaign/Adset/Ad)
    - Multi-platform support (Meta, TikTok, Google Ads)
    - Budget optimization based on performance
    - A/B testing with statistical analysis
    - Rule-based automation
    - AI-powered ad copy generation
    
    Requirements: All requirements from requirements.md
    """

    def __init__(
        self,
        mcp_client: MCPClient | None = None,
        gemini_client: GeminiClient | None = None,
        redis_client: Redis | None = None,
    ):
        """初始化 Campaign Automation 模块
        
        Args:
            mcp_client: MCP client for Web Platform communication
            gemini_client: Gemini client for AI copy generation
            redis_client: Redis client for caching
        """
        # Initialize dependencies
        self.mcp_client = mcp_client or MCPClient()
        self.gemini_client = gemini_client or GeminiClient()
        self.redis_client = redis_client
        
        # Initialize Platform Router (Task 2)
        self.platform_router = PlatformRouter()
        
        # Initialize Campaign Manager (Task 3)
        self.campaign_manager = CampaignManager(
            mcp_client=self.mcp_client,
            gemini_client=self.gemini_client,
        )
        
        # Initialize Budget Optimizer (Task 6)
        self.budget_optimizer = BudgetOptimizer(
            mcp_client=self.mcp_client,
        )
        
        # Initialize A/B Test Manager (Task 7)
        self.ab_test_manager = ABTestManager(
            mcp_client=self.mcp_client,
            platform_adapter=self.platform_router,
        )
        
        # Initialize Rule Engine (Task 8)
        self.rule_engine = RuleEngine(
            mcp_client=self.mcp_client,
            redis_client=self.redis_client,
        )
        
        logger.info(
            "campaign_automation_initialized",
            has_mcp=self.mcp_client is not None,
            has_gemini=self.gemini_client is not None,
            has_redis=self.redis_client is not None,
            has_campaign_manager=self.campaign_manager is not None,
            has_budget_optimizer=self.budget_optimizer is not None,
            has_ab_test_manager=self.ab_test_manager is not None,
            has_rule_engine=self.rule_engine is not None,
        )

    async def execute(self, action: str, parameters: dict, context: dict) -> dict:
        """
        执行广告引擎操作
        
        Implements action routing with comprehensive error handling and logging.
        All errors are caught and converted to structured error responses.

        Args:
            action: 操作名称 (create_campaign, optimize_budget, etc.)
            parameters: 操作参数
            context: 上下文信息（user_id, session_id等）

        Returns:
            操作结果，格式：
            - 成功: {"status": "success", "data": {...}, "message": "..."}
            - 失败: {"status": "error", "error": {...}}
            
        Supported actions:
            - create_campaign: 创建广告系列
            - optimize_budget: 优化预算
            - manage_campaign: 管理广告系列（暂停/启动/删除）
            - create_ab_test: 创建 A/B 测试
            - analyze_ab_test: 分析 A/B 测试结果
            - create_rule: 创建自动化规则
            - get_campaign_status: 获取广告系列状态
            
        Requirements: All requirements
        """
        user_id = context.get("user_id")
        session_id = context.get("session_id")
        
        log = logger.bind(
            action=action,
            user_id=user_id,
            session_id=session_id,
        )
        
        log.info("campaign_automation_execute_start", parameters=parameters)
        
        try:
            # Route to appropriate handler
            if action == "create_campaign":
                result = await self._handle_create_campaign(parameters, context)
            elif action == "optimize_budget":
                result = await self._handle_optimize_budget(parameters, context)
            elif action == "manage_campaign":
                result = await self._handle_manage_campaign(parameters, context)
            elif action == "create_ab_test":
                result = await self._handle_create_ab_test(parameters, context)
            elif action == "analyze_ab_test":
                result = await self._handle_analyze_ab_test(parameters, context)
            elif action == "create_rule":
                result = await self._handle_create_rule(parameters, context)
            elif action == "get_campaign_status":
                result = await self._handle_get_campaign_status(parameters, context)
            else:
                log.warning("unknown_action", action=action)
                return {
                    "status": "error",
                    "error": {
                        "code": "1001",
                        "type": "INVALID_ACTION",
                        "message": f"Unknown action: {action}",
                        "details": {
                            "action": action,
                            "supported_actions": [
                                "create_campaign",
                                "optimize_budget",
                                "manage_campaign",
                                "create_ab_test",
                                "analyze_ab_test",
                                "create_rule",
                                "get_campaign_status",
                            ],
                        },
                    },
                }
            
            log.info("campaign_automation_execute_success", action=action)
            return result
            
        except (MCPError, GeminiError) as e:
            # Handle known service errors
            log.error(
                "campaign_automation_service_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            error_state = ErrorHandler.handle_error(
                error=e,
                context=f"campaign_automation.{action}",
                user_id=user_id,
                session_id=session_id,
            )
            return {
                "status": "error",
                **error_state,
            }
            
        except Exception as e:
            # Handle unexpected errors
            log.error(
                "campaign_automation_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            error_state = ErrorHandler.handle_error(
                error=e,
                context=f"campaign_automation.{action}",
                user_id=user_id,
                session_id=session_id,
            )
            return {
                "status": "error",
                **error_state,
            }

    async def _handle_create_campaign(
        self,
        parameters: dict,
        context: dict,
    ) -> dict:
        """处理创建广告系列请求
        
        Args:
            parameters: {
                "objective": "sales" | "traffic" | "awareness",
                "daily_budget": float,
                "target_roas": float (optional),
                "product_url": str,
                "creative_ids": list[str],
                "target_countries": list[str],
                "platform": "meta" | "tiktok" | "google"
            }
            context: {"user_id": str, "session_id": str}
            
        Returns:
            {
                "status": "success",
                "campaign_id": str,
                "adsets": [...],
                "ads": [...],
                "message": str
            }
            
        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5
        """
        return await self.campaign_manager.create_campaign(
            objective=parameters.get("objective"),
            daily_budget=parameters.get("daily_budget"),
            target_countries=parameters.get("target_countries", ["US"]),
            creative_ids=parameters.get("creative_ids", []),
            platform=parameters.get("platform", "meta"),
            context=context,
            product_url=parameters.get("product_url"),
            target_roas=parameters.get("target_roas"),
            target_cpa=parameters.get("target_cpa"),
        )

    async def _handle_optimize_budget(
        self,
        parameters: dict,
        context: dict,
    ) -> dict:
        """处理预算优化请求
        
        Args:
            parameters: {
                "campaign_id": str,
                "optimization_strategy": "auto",
                "target_metric": "roas" | "cpa"
            }
            context: {"user_id": str, "session_id": str}
            
        Returns:
            {
                "status": "success",
                "optimizations": [...],
                "message": str
            }
            
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
        """
        result = await self.budget_optimizer.optimize_budget(
            campaign_id=parameters.get("campaign_id"),
            optimization_strategy=parameters.get("optimization_strategy", "auto"),
            target_metric=parameters.get("target_metric", "roas"),
            context=context,
        )
        
        return {
            "status": "success",
            "optimizations": [opt.model_dump() for opt in result.optimizations],
            "message": "预算优化完成",
        }

    async def _handle_manage_campaign(
        self,
        parameters: dict,
        context: dict,
    ) -> dict:
        """处理广告系列管理请求
        
        Args:
            parameters: {
                "campaign_id": str,
                "action": "pause" | "start" | "delete",
                "reason": str (optional)
            }
            context: {"user_id": str, "session_id": str}
            
        Returns:
            {
                "status": "success",
                "campaign_id": str,
                "new_status": str,
                "message": str
            }
            
        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
        """
        # Map action to status
        action = parameters.get("action")
        if action == "start":
            status = "active"
        elif action == "pause":
            status = "pause"
        elif action == "delete":
            status = "delete"
        else:
            return {
                "status": "error",
                "error": {
                    "code": "1001",
                    "type": "INVALID_REQUEST",
                    "message": f"Invalid action: {action}",
                }
            }
        
        return await self.campaign_manager.update_campaign_status(
            campaign_id=parameters.get("campaign_id"),
            status=status,
            platform=parameters.get("platform", "meta"),
            context=context,
            reason=parameters.get("reason"),
        )

    async def _handle_create_ab_test(
        self,
        parameters: dict,
        context: dict,
    ) -> dict:
        """处理创建 A/B 测试请求
        
        Args:
            parameters: {
                "test_name": str,
                "creative_ids": list[str],
                "daily_budget": float,
                "test_duration_days": int,
                "platform": "meta" | "tiktok" | "google"
            }
            context: {"user_id": str, "session_id": str}
            
        Returns:
            {
                "status": "success",
                "test_id": str,
                "campaign_id": str,
                "adsets": [...],
                "message": str
            }
            
        Requirements: 5.1, 5.2
        """
        return await self.ab_test_manager.create_ab_test(
            test_name=parameters.get("test_name"),
            creative_ids=parameters.get("creative_ids", []),
            daily_budget=parameters.get("daily_budget"),
            test_duration_days=parameters.get("test_duration_days", 7),
            platform=parameters.get("platform", "meta"),
            context=context,
        )

    async def _handle_analyze_ab_test(
        self,
        parameters: dict,
        context: dict,
    ) -> dict:
        """处理分析 A/B 测试请求
        
        Args:
            parameters: {
                "test_id": str
            }
            context: {"user_id": str, "session_id": str}
            
        Returns:
            {
                "status": "success",
                "test_id": str,
                "results": [...],
                "winner": {...} | None,
                "recommendations": [...],
                "message": str
            }
            
        Requirements: 5.3, 5.4, 5.5, 5.6
        """
        result = await self.ab_test_manager.analyze_ab_test(
            test_id=parameters.get("test_id"),
            context=context,
        )
        
        return {
            "status": "success",
            "test_id": result.test_id,
            "results": [variant.model_dump() for variant in result.results],
            "winner": result.winner.model_dump() if result.winner else None,
            "recommendations": result.recommendations,
            "message": result.message,
        }

    async def _handle_create_rule(
        self,
        parameters: dict,
        context: dict,
    ) -> dict:
        """处理创建自动化规则请求
        
        Args:
            parameters: {
                "rule_name": str,
                "condition": {...},
                "action": {...},
                "applies_to": {...},
                "check_interval": int (optional, default: 21600 = 6 hours)
            }
            context: {"user_id": str, "session_id": str}
            
        Returns:
            {
                "status": "success",
                "rule_id": str,
                "message": str
            }
            
        Requirements: 6.1, 6.3, 6.4, 6.5
        """
        return await self.rule_engine.create_rule(
            rule_name=parameters.get("rule_name"),
            condition=parameters.get("condition"),
            action=parameters.get("action"),
            applies_to=parameters.get("applies_to"),
            context=context,
            check_interval=parameters.get("check_interval", 21600),
        )

    async def _handle_get_campaign_status(
        self,
        parameters: dict,
        context: dict,
    ) -> dict:
        """处理获取广告系列状态请求
        
        Args:
            parameters: {
                "campaign_id": str
            }
            context: {"user_id": str, "session_id": str}
            
        Returns:
            {
                "status": "success",
                "campaign": {...},
                "adsets": [...],
                "message": str
            }
            
        Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
        """
        return await self.campaign_manager.get_campaign_details(
            campaign_id=parameters.get("campaign_id"),
            platform=parameters.get("platform", "meta"),
            context=context,
        )
