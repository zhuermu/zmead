"""
Property-based tests for retry mechanism in BaseFetcher.

**Feature: ad-performance, Property 2: Fetch failure auto-retry**
**Validates: Requirements 1.4, 8.5**
"""

import pytest
from hypothesis import given, settings, strategies as st

from app.modules.ad_performance.fetchers.base import BaseFetcher, RetryableError


class MockFetcher(BaseFetcher):
    """Mock fetcher for testing retry mechanism"""

    def __init__(self, max_retries: int = 3, backoff_factor: int = 2):
        super().__init__(max_retries, backoff_factor)
        self.call_count = 0
        self.fail_until_attempt = 0

    async def fetch_insights(
        self, date_range: dict, levels: list[str], metrics: list[str]
    ) -> dict:
        """Mock implementation"""
        return {"campaigns": [], "adsets": [], "ads": []}

    async def get_account_info(self, account_id: str) -> dict:
        """Mock implementation"""
        return {"account_id": account_id}

    async def failing_operation(self) -> str:
        """Operation that fails until a certain attempt"""
        self.call_count += 1
        if self.call_count < self.fail_until_attempt:
            raise RetryableError(f"Attempt {self.call_count} failed")
        return "success"

    async def always_failing_operation(self) -> str:
        """Operation that always fails"""
        self.call_count += 1
        raise RetryableError(f"Attempt {self.call_count} failed")

    async def non_retryable_operation(self) -> str:
        """Operation that raises non-retryable error"""
        self.call_count += 1
        raise ValueError("Non-retryable error")


@given(
    max_retries=st.integers(min_value=1, max_value=5),
    fail_until_attempt=st.integers(min_value=1, max_value=3),
)
@settings(max_examples=100, deadline=None)
@pytest.mark.asyncio
async def test_property_2_retry_succeeds_within_limit(
    max_retries: int, fail_until_attempt: int
):
    """
    **Feature: ad-performance, Property 2: Fetch failure auto-retry**
    
    For any max_retries and fail_until_attempt where fail_until_attempt <= max_retries,
    the retry mechanism should eventually succeed and return the expected result.
    
    **Validates: Requirements 1.4, 8.5**
    """
    # Only test cases where we should succeed
    if fail_until_attempt > max_retries:
        return

    # Arrange
    fetcher = MockFetcher(max_retries=max_retries, backoff_factor=2)
    fetcher.fail_until_attempt = fail_until_attempt

    # Act
    result = await fetcher.retry_with_backoff(fetcher.failing_operation)

    # Assert
    assert result == "success"
    assert fetcher.call_count == fail_until_attempt


@given(max_retries=st.integers(min_value=1, max_value=5))
@settings(max_examples=100, deadline=None)
@pytest.mark.asyncio
async def test_property_2_retry_exhausts_after_max_attempts(max_retries: int):
    """
    **Feature: ad-performance, Property 2: Fetch failure auto-retry**
    
    For any max_retries, when an operation always fails with RetryableError,
    the retry mechanism should exhaust after exactly max_retries attempts
    and raise the last exception.
    
    **Validates: Requirements 1.4, 8.5**
    """
    # Arrange
    fetcher = MockFetcher(max_retries=max_retries, backoff_factor=2)

    # Act & Assert
    with pytest.raises(RetryableError) as exc_info:
        await fetcher.retry_with_backoff(fetcher.always_failing_operation)

    # Verify we attempted exactly max_retries times
    assert fetcher.call_count == max_retries
    assert f"Attempt {max_retries} failed" in str(exc_info.value)


@given(max_retries=st.integers(min_value=1, max_value=5))
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_2_non_retryable_error_fails_immediately(max_retries: int):
    """
    **Feature: ad-performance, Property 2: Fetch failure auto-retry**
    
    For any max_retries, when an operation raises a non-retryable error,
    the retry mechanism should fail immediately on the first attempt
    without retrying.
    
    **Validates: Requirements 1.4, 8.5**
    """
    # Arrange
    fetcher = MockFetcher(max_retries=max_retries, backoff_factor=2)

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        await fetcher.retry_with_backoff(fetcher.non_retryable_operation)

    # Verify we only attempted once (no retries for non-retryable errors)
    assert fetcher.call_count == 1
    assert "Non-retryable error" in str(exc_info.value)


@given(
    max_retries=st.integers(min_value=2, max_value=5),
    backoff_factor=st.integers(min_value=1, max_value=3),
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_2_backoff_configuration(max_retries: int, backoff_factor: int):
    """
    **Feature: ad-performance, Property 2: Fetch failure auto-retry**
    
    For any max_retries and backoff_factor, the fetcher should be properly
    configured with these values and use them during retry operations.
    
    **Validates: Requirements 1.4, 8.5**
    """
    # Arrange
    fetcher = MockFetcher(max_retries=max_retries, backoff_factor=backoff_factor)

    # Assert configuration
    assert fetcher.max_retries == max_retries
    assert fetcher.backoff_factor == backoff_factor
