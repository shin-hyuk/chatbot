"""
FastAPI SDK routers package that organizes API endpoints for SDK functionality.
"""

from api.routers.sdk.chat import router as chat_router

__all__ = [
    "chat_router",
] 