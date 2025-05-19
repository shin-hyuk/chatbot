"""
FastAPI admin routers package that organizes API endpoints for administrative functionality.
"""

from api.routers.admin.token import router as token_router

__all__ = [
    "token_router",
] 