"""Credit service for managing user credits."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credit_config import CreditConfig
from app.models.credit_config_log import CreditConfigLog
from app.models.credit_transaction import CreditTransaction
from app.models.user import User
from app.schemas.credit import OperationType, TransactionType


class InsufficientCreditsError(Exception):
    """Raised when user has insufficient credits."""

    def __init__(self, required: Decimal, available: Decimal):
        self.required = required
        self.available = available
        self.error_code = 6011
        super().__init__(
            f"Insufficient credits. Required: {required}, Available: {available}"
        )


class CreditService:
    """Service for credit operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_balance(self, user_id: int) -> dict[str, Decimal]:
        """Get user's credit balance.
        
        Returns:
            Dictionary with gifted_credits, purchased_credits, and total_credits
        """
        result = await self.db.execute(
            select(User.gifted_credits, User.purchased_credits)
            .where(User.id == user_id)
        )
        row = result.first()

        if not row:
            return {
                "gifted_credits": Decimal("0"),
                "purchased_credits": Decimal("0"),
                "total_credits": Decimal("0"),
            }

        gifted = row.gifted_credits or Decimal("0")
        purchased = row.purchased_credits or Decimal("0")

        return {
            "gifted_credits": gifted,
            "purchased_credits": purchased,
            "total_credits": gifted + purchased,
        }

    async def deduct_credits(
        self,
        user_id: int,
        amount: Decimal,
        operation_type: OperationType | str,
        operation_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> CreditTransaction:
        """Deduct credits from user's balance.
        
        Credits are deducted in order: gifted_credits first, then purchased_credits.
        Uses database transaction to ensure atomicity.
        
        Args:
            user_id: User ID
            amount: Amount to deduct (must be positive)
            operation_type: Type of operation consuming credits
            operation_id: Optional unique ID for the operation
            details: Optional additional details (model, tokens, etc.)
            
        Returns:
            CreditTransaction record
            
        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Convert enum to string if needed
        op_type_str = operation_type.value if isinstance(operation_type, OperationType) else operation_type

        # Get current balance with row lock for update
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        total_available = user.gifted_credits + user.purchased_credits

        if total_available < amount:
            raise InsufficientCreditsError(required=amount, available=total_available)

        # Calculate deduction from each source (gifted first)
        from_gifted = Decimal("0")
        from_purchased = Decimal("0")
        remaining = amount

        if user.gifted_credits > 0:
            from_gifted = min(user.gifted_credits, remaining)
            remaining -= from_gifted

        if remaining > 0:
            from_purchased = remaining

        # Update user balances
        user.gifted_credits -= from_gifted
        user.purchased_credits -= from_purchased

        balance_after = user.gifted_credits + user.purchased_credits

        # Create transaction record
        transaction = CreditTransaction(
            user_id=user_id,
            type=TransactionType.DEDUCT.value,
            amount=amount,
            from_gifted=from_gifted,
            from_purchased=from_purchased,
            balance_after=balance_after,
            operation_type=op_type_str,
            operation_id=operation_id,
            details=details or {},
        )

        self.db.add(transaction)
        await self.db.flush()

        return transaction

    async def refund_credits(
        self,
        user_id: int,
        amount: Decimal,
        operation_type: OperationType | str,
        operation_id: str | None = None,
        reason: str | None = None,
    ) -> CreditTransaction:
        """Refund credits to user's balance.
        
        Refunded credits go to purchased_credits by default.
        
        Args:
            user_id: User ID
            amount: Amount to refund (must be positive)
            operation_type: Type of operation being refunded
            operation_id: Optional original operation ID
            reason: Optional reason for refund
            
        Returns:
            CreditTransaction record
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Convert enum to string if needed
        op_type_str = operation_type.value if isinstance(operation_type, OperationType) else operation_type

        # Get user with row lock
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        # Add to purchased credits (refunds go to purchased)
        user.purchased_credits += amount

        balance_after = user.gifted_credits + user.purchased_credits

        # Create transaction record
        details = {}
        if reason:
            details["reason"] = reason

        transaction = CreditTransaction(
            user_id=user_id,
            type=TransactionType.REFUND.value,
            amount=amount,
            from_gifted=Decimal("0"),
            from_purchased=amount,  # Refund goes to purchased
            balance_after=balance_after,
            operation_type=op_type_str,
            operation_id=operation_id,
            details=details,
        )

        self.db.add(transaction)
        await self.db.flush()

        return transaction

    async def add_credits(
        self,
        user_id: int,
        amount: Decimal,
        transaction_type: TransactionType,
        details: dict[str, Any] | None = None,
    ) -> CreditTransaction:
        """Add credits to user's balance (for recharge or gift).
        
        Args:
            user_id: User ID
            amount: Amount to add (must be positive)
            transaction_type: RECHARGE or GIFT
            details: Optional additional details
            
        Returns:
            CreditTransaction record
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        if transaction_type not in (TransactionType.RECHARGE, TransactionType.GIFT):
            raise ValueError("Transaction type must be RECHARGE or GIFT")

        # Get user with row lock
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        # Add to appropriate balance
        if transaction_type == TransactionType.GIFT:
            user.gifted_credits += amount
            from_gifted = amount
            from_purchased = Decimal("0")
        else:
            user.purchased_credits += amount
            from_gifted = Decimal("0")
            from_purchased = amount

        balance_after = user.gifted_credits + user.purchased_credits

        # Create transaction record
        transaction = CreditTransaction(
            user_id=user_id,
            type=transaction_type.value,
            amount=amount,
            from_gifted=from_gifted,
            from_purchased=from_purchased,
            balance_after=balance_after,
            operation_type=None,
            operation_id=None,
            details=details or {},
        )

        self.db.add(transaction)
        await self.db.flush()

        return transaction

    async def get_transaction_history(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        days: int = 30,
    ) -> dict:
        """Get user's credit transaction history.
        
        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            days: Number of days to look back
            
        Returns:
            Dictionary with transactions, total, page, page_size, has_more
        """
        since = datetime.utcnow() - timedelta(days=days)

        # Get total count
        count_result = await self.db.execute(
            select(func.count(CreditTransaction.id))
            .where(CreditTransaction.user_id == user_id)
            .where(CreditTransaction.created_at >= since)
        )
        total = count_result.scalar() or 0

        # Get paginated transactions
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
            .where(CreditTransaction.created_at >= since)
            .order_by(CreditTransaction.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        transactions = list(result.scalars().all())

        return {
            "transactions": transactions,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": offset + len(transactions) < total,
        }

    async def check_sufficient_credits(
        self,
        user_id: int,
        required_amount: Decimal,
    ) -> bool:
        """Check if user has sufficient credits.
        
        Args:
            user_id: User ID
            required_amount: Amount of credits required
            
        Returns:
            True if user has sufficient credits, False otherwise
        """
        balance = await self.get_balance(user_id)
        return balance["total_credits"] >= required_amount

    async def calculate_token_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        provider: str | None = None,
    ) -> Decimal:
        """Calculate credit cost for token usage.
        
        Supports multiple AI providers: Gemini, Bedrock (Claude, Qwen, Nova).
        
        Args:
            model: Model name or identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            provider: Optional provider name ('gemini', 'bedrock', 'sagemaker')
            
        Returns:
            Total credit cost
        """
        config = await self.get_config()

        # Normalize model name for lookup
        model_lower = model.lower().replace("-", "_").replace(".", "_")
        
        # Map model identifiers to rate configuration
        # Gemini models
        if model_lower in ["gemini_flash", "gemini_2_5_flash", "gemini_2_0_flash"] or provider == "gemini" and "flash" in model_lower:
            input_rate = config.gemini_flash_input_rate
            output_rate = config.gemini_flash_output_rate
        elif model_lower in ["gemini_pro", "gemini_2_5_pro", "gemini_3_pro", "gemini_2_0_pro"] or provider == "gemini" and "pro" in model_lower:
            input_rate = config.gemini_pro_input_rate
            output_rate = config.gemini_pro_output_rate
        # Bedrock models - use Gemini Pro rates as baseline for now
        # TODO: Add specific Bedrock model rates to CreditConfig
        elif provider == "bedrock" or any(x in model_lower for x in ["claude", "qwen", "nova", "anthropic", "amazon"]):
            # Use Gemini Pro rates for Bedrock models (can be adjusted in config)
            input_rate = config.gemini_pro_input_rate
            output_rate = config.gemini_pro_output_rate
        # SageMaker models - use Gemini Pro rates as baseline
        elif provider == "sagemaker":
            input_rate = config.gemini_pro_input_rate
            output_rate = config.gemini_pro_output_rate
        else:
            # Default to Gemini Flash rates for unknown models
            input_rate = config.gemini_flash_input_rate
            output_rate = config.gemini_flash_output_rate

        # Rates are per 1K tokens
        input_cost = (Decimal(input_tokens) / 1000) * input_rate
        output_cost = (Decimal(output_tokens) / 1000) * output_rate

        return input_cost + output_cost

    async def get_operation_cost(
        self,
        operation_type: OperationType | str,
    ) -> Decimal:
        """Get the fixed credit cost for an operation type.
        
        Args:
            operation_type: Type of operation
            
        Returns:
            Credit cost for the operation
        """
        config = await self.get_config()

        # Convert enum to string if needed
        op_type = operation_type.value if isinstance(operation_type, OperationType) else operation_type

        rate_map = {
            OperationType.IMAGE_GENERATION.value: config.image_generation_rate,
            OperationType.VIDEO_GENERATION.value: config.video_generation_rate,
            OperationType.LANDING_PAGE.value: config.landing_page_rate,
            OperationType.COMPETITOR_ANALYSIS.value: config.competitor_analysis_rate,
            OperationType.OPTIMIZATION_SUGGESTION.value: config.optimization_suggestion_rate,
        }

        if op_type not in rate_map:
            raise ValueError(f"Unknown operation type: {op_type}")

        return rate_map[op_type]

    async def get_config(self) -> CreditConfig:
        """Get the current credit configuration.
        
        Returns:
            CreditConfig instance (creates default if none exists)
        """
        result = await self.db.execute(
            select(CreditConfig).order_by(CreditConfig.id.desc()).limit(1)
        )
        config = result.scalar_one_or_none()

        if not config:
            # Create default config
            config = CreditConfig()
            self.db.add(config)
            await self.db.flush()

        return config


    async def update_config(
        self,
        updated_by: str,
        **kwargs,
    ) -> CreditConfig:
        """Update credit configuration.
        
        Args:
            updated_by: Admin user identifier
            **kwargs: Configuration fields to update
            
        Returns:
            Updated CreditConfig instance
        """
        config = await self.get_config()

        # Update allowed fields
        allowed_fields = {
            "gemini_flash_input_rate",
            "gemini_flash_output_rate",
            "gemini_pro_input_rate",
            "gemini_pro_output_rate",
            "image_generation_rate",
            "video_generation_rate",
            "landing_page_rate",
            "competitor_analysis_rate",
            "optimization_suggestion_rate",
            "registration_bonus",
            "packages",
        }

        # Log changes before updating
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                old_value = getattr(config, field)
                
                # Only log if value actually changed
                if old_value != value:
                    # Convert values to string for logging
                    old_value_str = str(old_value) if old_value is not None else None
                    new_value_str = str(value)
                    
                    # Create log entry
                    log_entry = CreditConfigLog(
                        config_id=config.id,
                        field_name=field,
                        old_value=old_value_str,
                        new_value=new_value_str,
                        changed_by=updated_by,
                        changed_at=datetime.utcnow(),
                    )
                    self.db.add(log_entry)
                    
                    # Update the config field
                    setattr(config, field, value)

        config.updated_by = updated_by

        await self.db.flush()
        return config

    async def get_config_dict(self) -> dict:
        """Get credit configuration as a dictionary.
        
        Returns:
            Dictionary with all configuration values
        """
        config = await self.get_config()

        return {
            "id": config.id,
            "gemini_flash_input_rate": float(config.gemini_flash_input_rate),
            "gemini_flash_output_rate": float(config.gemini_flash_output_rate),
            "gemini_pro_input_rate": float(config.gemini_pro_input_rate),
            "gemini_pro_output_rate": float(config.gemini_pro_output_rate),
            "image_generation_rate": float(config.image_generation_rate),
            "video_generation_rate": float(config.video_generation_rate),
            "landing_page_rate": float(config.landing_page_rate),
            "competitor_analysis_rate": float(config.competitor_analysis_rate),
            "optimization_suggestion_rate": float(config.optimization_suggestion_rate),
            "registration_bonus": float(config.registration_bonus),
            "packages": config.packages,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            "updated_by": config.updated_by,
        }

    async def get_config_change_history(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Get credit configuration change history.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of change log entries
        """
        result = await self.db.execute(
            select(CreditConfigLog)
            .order_by(CreditConfigLog.changed_at.desc())
            .limit(limit)
            .offset(offset)
        )
        logs = result.scalars().all()

        return [
            {
                "id": log.id,
                "config_id": log.config_id,
                "field_name": log.field_name,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "changed_by": log.changed_by,
                "changed_at": log.changed_at.isoformat(),
                "notes": log.notes,
            }
            for log in logs
        ]
