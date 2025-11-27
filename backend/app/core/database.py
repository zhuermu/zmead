"""Database connection and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()


async def seed_credit_config() -> None:
    """Seed default credit configuration if not exists."""
    from app.models.credit_config import CreditConfig

    async with async_session_maker() as session:
        from sqlalchemy import select

        result = await session.execute(select(CreditConfig).limit(1))
        existing = result.scalar_one_or_none()

        if not existing:
            # Create default configuration
            default_packages = {
                "package_experience": {
                    "name": "体验包",
                    "price_cents": 9900,
                    "credits": 1000,
                    "discount_percent": 0,
                },
                "package_standard": {
                    "name": "标准包",
                    "price_cents": 29900,
                    "credits": 3000,
                    "discount_percent": 10,
                },
                "package_professional": {
                    "name": "专业包",
                    "price_cents": 99900,
                    "credits": 10000,
                    "discount_percent": 20,
                },
                "package_enterprise": {
                    "name": "企业包",
                    "price_cents": 299900,
                    "credits": 30000,
                    "discount_percent": 30,
                },
            }

            config = CreditConfig(packages=default_packages)
            session.add(config)
            await session.commit()
