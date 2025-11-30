"""
Base fetcher abstract class for ad platform data fetching.

Requirements: 1.1, 1.4
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class RetryableError(Exception):
    """Exception that indicates the operation should be retried"""

    pass


class BaseFetcher(ABC):
    """广告平台数据抓取器基类
    
    Provides base functionality for fetching data from ad platforms with
    automatic retry mechanism using exponential backoff.
    
    Requirements: 1.1, 1.4
    """

    def __init__(self, max_retries: int = 3, backoff_factor: int = 2):
        """
        Initialize base fetcher with retry configuration.
        
        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            backoff_factor: Exponential backoff multiplier (default: 2)
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    @abstractmethod
    async def fetch_insights(
        self, date_range: dict, levels: list[str], metrics: list[str]
    ) -> dict:
        """
        抓取广告数据

        Args:
            date_range: 日期范围 {"start_date": "2024-11-20", "end_date": "2024-11-26"}
            levels: 数据层级 ["campaign", "adset", "ad"]
            metrics: 指标列表 ["spend", "impressions", "clicks", "conversions", "revenue"]

        Returns:
            {
                "campaigns": [...],
                "adsets": [...],
                "ads": [...]
            }
            
        Requirements: 1.1, 1.2, 1.3
        """
        pass

    @abstractmethod
    async def get_account_info(self, account_id: str) -> dict:
        """
        获取账户信息

        Args:
            account_id: 广告账户 ID

        Returns:
            账户信息字典
            
        Requirements: 1.1
        """
        pass

    async def retry_with_backoff(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """
        Execute function with exponential backoff retry mechanism.
        
        Automatically retries the function up to max_retries times if it raises
        a RetryableError. Uses exponential backoff between retries.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from successful function execution
            
        Raises:
            Exception: The last exception if all retries fail
            
        Requirements: 1.4, 8.5
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    "retry_attempt",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    func=func.__name__,
                )
                result = await func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(
                        "retry_success",
                        attempt=attempt + 1,
                        func=func.__name__,
                    )
                
                return result

            except RetryableError as e:
                last_exception = e
                
                if attempt == self.max_retries - 1:
                    # Last attempt failed
                    logger.error(
                        "retry_exhausted",
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        func=func.__name__,
                        error=str(e),
                    )
                    raise
                
                # Calculate wait time with exponential backoff
                wait_time = self.backoff_factor**attempt
                
                logger.warning(
                    "retry_failed_waiting",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    wait_time=wait_time,
                    func=func.__name__,
                    error=str(e),
                )
                
                await asyncio.sleep(wait_time)

            except Exception as e:
                # Non-retryable error, fail immediately
                logger.error(
                    "non_retryable_error",
                    attempt=attempt + 1,
                    func=func.__name__,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise

        # Should never reach here, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("Retry logic failed unexpectedly")
