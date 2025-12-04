"""API v1 router combining all endpoints."""

from fastapi import APIRouter

from app.api.v1.ad_accounts import router as ad_accounts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.chat import router as chat_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.creatives import router as creatives_router
from app.api.v1.credits import router as credits_router
from app.api.v1.landing_pages import router as landing_pages_router
from app.api.v1.mcp import router as mcp_router
from app.api.v1.media import router as media_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.reports import router as reports_router
from app.api.v1.uploads import router as uploads_router
from app.api.v1.users import router as users_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.websocket import router as websocket_router

api_router = APIRouter()

# Include all v1 routers
api_router.include_router(auth_router)
api_router.include_router(ad_accounts_router)
api_router.include_router(campaigns_router)
api_router.include_router(chat_router)
api_router.include_router(conversations_router)
api_router.include_router(creatives_router)
api_router.include_router(credits_router)
api_router.include_router(landing_pages_router)
api_router.include_router(mcp_router)
api_router.include_router(media_router, prefix="/media", tags=["media"])
api_router.include_router(notifications_router)
api_router.include_router(reports_router)
api_router.include_router(uploads_router)
api_router.include_router(users_router)
api_router.include_router(webhooks_router)
api_router.include_router(websocket_router)
