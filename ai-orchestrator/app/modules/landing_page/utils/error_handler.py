"""
Error handling for Landing Page module.

This module provides unified error handling with appropriate error codes
and retry strategies for different failure scenarios.
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Error codes for Landing Page module"""
    
    # Product extraction errors
    PRODUCT_URL_INVALID = "6006"
    PRODUCT_INFO_EXTRACTION_FAILED = "6007"
    
    # Landing page errors
    LANDING_PAGE_DOMAIN_NOT_VERIFIED = "6008"
    
    # AI model errors
    AI_MODEL_FAILED = "4001"
    GENERATION_FAILED = "4003"
    
    # Storage errors
    STORAGE_ERROR = "5003"
    
    # Data errors
    DATA_NOT_FOUND = "5000"
    
    # MCP errors
    MCP_EXECUTION_FAILED = "3003"


class ErrorHandler:
    """Unified error handler for Landing Page module"""
    
    MAX_RETRIES = 3
    BASE_DELAY = 2  # seconds
    
    def __init__(self):
        self.retry_count = {}
    
    async def handle_extraction_error(
        self,
        error: Exception,
        retry_count: int,
        product_url: str
    ) -> Dict[str, Any]:
        """
        Handle product information extraction errors
        
        Args:
            error: The exception that occurred
            retry_count: Current retry attempt number
            product_url: The product URL being extracted
        
        Returns:
            Error response dict with retry flag or error details
        """
        logger.error(
            f"Product extraction error (attempt {retry_count + 1}): {error}",
            extra={"product_url": product_url}
        )
        
        if retry_count < self.MAX_RETRIES:
            # Exponential backoff
            delay = self.BASE_DELAY ** retry_count
            await asyncio.sleep(delay)
            return {"retry": True}
        else:
            return {
                "status": "error",
                "error_code": ErrorCode.PRODUCT_INFO_EXTRACTION_FAILED,
                "message": "产品信息提取失败，请检查链接或手动输入产品信息",
                "suggestion": "请确保链接可访问，或尝试手动输入产品信息",
                "details": str(error)
            }
    
    async def handle_generation_error(
        self,
        error: Exception,
        retry_count: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle landing page generation errors
        
        Args:
            error: The exception that occurred
            retry_count: Current retry attempt number
            context: Additional context about the generation
        
        Returns:
            Error response dict with retry flag or error details
        """
        logger.error(
            f"Landing page generation error (attempt {retry_count + 1}): {error}",
            extra=context or {}
        )
        
        if retry_count < self.MAX_RETRIES:
            # Exponential backoff
            delay = self.BASE_DELAY ** retry_count
            await asyncio.sleep(delay)
            return {"retry": True}
        else:
            return {
                "status": "error",
                "error_code": ErrorCode.GENERATION_FAILED,
                "message": "落地页生成失败，请稍后重试",
                "retry_allowed": True,
                "details": str(error)
            }
    
    async def handle_optimization_error(
        self,
        error: Exception,
        original_text: str,
        section: str
    ) -> Dict[str, Any]:
        """
        Handle copy optimization errors - returns original text as fallback
        
        Args:
            error: The exception that occurred
            original_text: The original text before optimization
            section: The section being optimized
        
        Returns:
            Success response with original text and fallback flag
        """
        logger.warning(
            f"Copy optimization failed for section '{section}', using fallback: {error}"
        )
        
        return {
            "status": "success",
            "optimized_text": original_text,
            "improvements": [],
            "confidence_score": 0.0,
            "fallback": True,
            "message": "文案优化失败，返回原文案"
        }
    
    async def handle_translation_error(
        self,
        error: Exception,
        retry_count: int,
        target_language: str
    ) -> Dict[str, Any]:
        """
        Handle translation errors
        
        Args:
            error: The exception that occurred
            retry_count: Current retry attempt number
            target_language: The target language code
        
        Returns:
            Error response dict with retry flag or error details
        """
        logger.error(
            f"Translation error for language '{target_language}' "
            f"(attempt {retry_count + 1}): {error}"
        )
        
        if retry_count < self.MAX_RETRIES:
            # Exponential backoff
            delay = self.BASE_DELAY ** retry_count
            await asyncio.sleep(delay)
            return {"retry": True}
        else:
            return {
                "status": "error",
                "error_code": ErrorCode.AI_MODEL_FAILED,
                "message": f"翻译失败：不支持的语言或翻译服务暂时不可用",
                "target_language": target_language,
                "details": str(error)
            }
    
    async def handle_storage_error(
        self,
        error: Exception,
        retry_count: int,
        operation: str
    ) -> Dict[str, Any]:
        """
        Handle storage (S3) errors
        
        Args:
            error: The exception that occurred
            retry_count: Current retry attempt number
            operation: The storage operation being performed
        
        Returns:
            Error response dict with retry flag or error details
        """
        logger.error(
            f"Storage error during '{operation}' (attempt {retry_count + 1}): {error}"
        )
        
        if retry_count < self.MAX_RETRIES:
            # Exponential backoff
            delay = self.BASE_DELAY ** retry_count
            await asyncio.sleep(delay)
            return {"retry": True}
        else:
            return {
                "status": "error",
                "error_code": ErrorCode.STORAGE_ERROR,
                "message": "文件上传失败，请稍后重试",
                "operation": operation,
                "details": str(error)
            }
    
    async def handle_mcp_error(
        self,
        error: Exception,
        retry_count: int,
        tool_name: str
    ) -> Dict[str, Any]:
        """
        Handle MCP tool execution errors
        
        Args:
            error: The exception that occurred
            retry_count: Current retry attempt number
            tool_name: The MCP tool being called
        
        Returns:
            Error response dict with retry flag or error details
        """
        logger.error(
            f"MCP tool '{tool_name}' error (attempt {retry_count + 1}): {error}"
        )
        
        if retry_count < self.MAX_RETRIES:
            # Exponential backoff
            delay = self.BASE_DELAY ** retry_count
            await asyncio.sleep(delay)
            return {"retry": True}
        else:
            return {
                "status": "error",
                "error_code": ErrorCode.MCP_EXECUTION_FAILED,
                "message": "数据操作失败，请稍后重试",
                "tool_name": tool_name,
                "details": str(error)
            }
    
    def handle_validation_error(
        self,
        field: str,
        value: Any,
        expected_format: str
    ) -> Dict[str, Any]:
        """
        Handle validation errors (non-retryable)
        
        Args:
            field: The field that failed validation
            value: The invalid value
            expected_format: Description of expected format
        
        Returns:
            Error response dict
        """
        logger.warning(
            f"Validation error for field '{field}': "
            f"value '{value}' does not match expected format '{expected_format}'"
        )
        
        return {
            "status": "error",
            "error_code": ErrorCode.PRODUCT_URL_INVALID,
            "message": f"字段 '{field}' 格式无效",
            "field": field,
            "expected_format": expected_format,
            "provided_value": str(value)
        }
    
    def handle_not_found_error(
        self,
        resource_type: str,
        resource_id: str
    ) -> Dict[str, Any]:
        """
        Handle resource not found errors (non-retryable)
        
        Args:
            resource_type: Type of resource (e.g., "landing_page", "ab_test")
            resource_id: ID of the resource
        
        Returns:
            Error response dict
        """
        logger.warning(
            f"Resource not found: {resource_type} with ID '{resource_id}'"
        )
        
        return {
            "status": "error",
            "error_code": ErrorCode.DATA_NOT_FOUND,
            "message": f"{resource_type} 不存在",
            "resource_type": resource_type,
            "resource_id": resource_id
        }
    
    def is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error is retryable
        
        Args:
            error: The exception to check
        
        Returns:
            True if the error should be retried
        """
        # Network errors, timeouts, and temporary failures are retryable
        retryable_exceptions = (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        )
        
        # Check exception type
        if isinstance(error, retryable_exceptions):
            return True
        
        # Check error message for common retryable patterns
        error_msg = str(error).lower()
        retryable_patterns = [
            "timeout",
            "connection",
            "temporary",
            "rate limit",
            "throttle",
            "503",
            "502",
            "504"
        ]
        
        return any(pattern in error_msg for pattern in retryable_patterns)
