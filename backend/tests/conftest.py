"""Pytest configuration and fixtures for backend tests."""

from collections.abc import AsyncGenerator
from datetime import datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User


# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio backend for anyio."""
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session.
    
    Uses an in-memory SQLite database for isolation and speed.
    Each test gets a fresh database.
    """
    from decimal import Decimal
    from app.models.credit_config import CreditConfig
    
    # Create engine with in-memory SQLite
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with async_session() as session:
        # Create default credit config for tests
        credit_config = CreditConfig(
            id=1,
            gemini_flash_input_rate=Decimal("0.01"),
            gemini_flash_output_rate=Decimal("0.04"),
            gemini_pro_input_rate=Decimal("0.05"),
            gemini_pro_output_rate=Decimal("0.2"),
            image_generation_rate=Decimal("0.5"),
            video_generation_rate=Decimal("5"),
            landing_page_rate=Decimal("15"),
            competitor_analysis_rate=Decimal("10"),
            optimization_suggestion_rate=Decimal("20"),
            registration_bonus=Decimal("500"),
            packages={},
        )
        session.add(credit_config)
        await session.commit()
        
        yield session
        await session.rollback()
    
    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=1,  # Explicitly set ID for SQLite compatibility
        email="test@example.com",
        display_name="Test User",
        oauth_provider="google",
        oauth_id="test-google-id",
        conversational_provider="gemini",
        conversational_model="gemini-2.5-flash",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, test_user: User) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client with authenticated user."""
    from app.api.deps import get_current_user
    
    async def override_get_db():
        yield db_session
    
    async def override_get_current_user():
        return test_user
    
    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    # Create client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer test-token-{test_user.id}"}
    ) as ac:
        yield ac
    
    # Clean up
    app.dependency_overrides.clear()
