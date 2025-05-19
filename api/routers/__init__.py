"""
FastAPI routers package that organizes API endpoints by functionality.
"""

from api.routers.user import router as user_router
from api.routers.sdk import chat_router
from api.routers.chat import router as public_chat_router
from api.routers.kb import router as kb_router
from api.routers.assistant import router as assistant_router
from api.routers.assistant import defaults_router
from api.routers.admin.token import router as admin_token_router

# Export all routers for easy inclusion in the main app
__all__ = [
    "user_router",
    "chat_router",
    "public_chat_router",
    "kb_router",
    "assistant_router",
    "defaults_router",
    "admin_token_router"
] 