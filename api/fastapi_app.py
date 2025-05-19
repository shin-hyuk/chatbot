import logging
import os
from typing import Dict, Optional, Any

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer

from api import settings
from api.constants import API_VERSION
from api.db import StatusEnum
from api.db.db_models import close_connection
from api.db.services.user_service import UserService
from api.utils import CustomJSONEncoder
from api.routers.user import router as user_router
from api.routers.sdk.chat import router as sdk_chat_router
from api.routers.chat import router as public_chat_router
from api.routers.kb import router as kb_router
from api.routers.assistant import router as assistant_router
from api.routers.assistant import defaults_router
from api.routers.admin.token import router as admin_token_router

app = FastAPI(
    title="RAGFlow API",
    description="RAGFlow API powered by FastAPI",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=2592000,
)

# Set max content length
max_content_length = int(os.environ.get("MAX_CONTENT_LENGTH", 1024 * 1024 * 1024))

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="RAGFlow API",
        version="1.0.0",
        description="",
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"] = {
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header"
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Swagger UI route
@app.get("/apidocs/", include_in_schema=False)
async def get_swagger_documentation():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="RAGFlow API",
        swagger_js_url="/flasgger_static/swagger-ui-bundle.js",
        swagger_css_url="/flasgger_static/swagger-ui.css",
    )

# Authentication dependency
async def get_current_user(request: Request):
    jwt = Serializer(secret_key=settings.SECRET_KEY)
    authorization = request.headers.get("Authorization")
    if authorization:
        try:
            access_token = str(jwt.loads(authorization))
            user = UserService.query(
                access_token=access_token, status=StatusEnum.VALID.value
            )
            if user:
                return user[0]
            else:
                raise HTTPException(status_code=401, detail="Authentication failed")
        except Exception as e:
            logging.warning(f"Authentication error: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")
    else:
        raise HTTPException(status_code=401, detail="Authorization header is missing")

# Custom exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.exception(exc)
    return JSONResponse(
        status_code=500,
        content={
            "code": settings.RetCode.EXCEPTION_ERROR,
            "message": str(exc),
            "data": None
        }
    )

# Close DB connection after request
@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    response = await call_next(request)
    close_connection()
    return response

# Include routers
app.include_router(user_router)
app.include_router(sdk_chat_router)
app.include_router(public_chat_router)
app.include_router(kb_router)
app.include_router(assistant_router)
app.include_router(defaults_router)
app.include_router(admin_token_router)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"} 