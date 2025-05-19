from typing import Any, Dict, Optional, Union, TypeVar, Callable, List
from functools import wraps

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from api.db import StatusEnum
from api.db.services.user_service import UserService
from api import settings

T = TypeVar('T')

# Models for standardized API responses
class StandardResponse(BaseModel):
    code: int = Field(0, description="Status code")
    message: str = Field("success", description="Response message")
    data: Optional[Any] = Field(None, description="Response data")

# Authentication
auth_header = APIKeyHeader(name="Authorization", auto_error=False)

async def token_required(authorization: Optional[str] = Depends(auth_header)) -> str:
    """
    Validate token and extract tenant_id.
    Raises HTTP exception if validation fails.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    try:
        user = UserService.query(
            access_token=authorization, 
            status=StatusEnum.VALID.value
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        return user[0].id
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}"
        )

# Response utilities
def get_json_result(
    data: Any = None, 
    code: int = settings.RetCode.SUCCESS, 
    message: str = "success"
) -> Dict[str, Any]:
    """
    Returns a standardized JSON response format.
    """
    return {
        "code": code,
        "message": message,
        "data": data
    }

def get_error_data_result(
    message: str = "error", 
    code: int = settings.RetCode.PARAM_ERROR
) -> Dict[str, Any]:
    """
    Returns a standardized error response.
    """
    return get_json_result(
        data=None,
        code=code,
        message=message
    )

def get_result(
    data: Any = None, 
    code: int = settings.RetCode.SUCCESS, 
    message: str = "success"
) -> Dict[str, Any]:
    """
    Alias for get_json_result for compatibility.
    """
    return get_json_result(data, code, message)

def construct_response(
    data: Any = None, 
    code: int = settings.RetCode.SUCCESS, 
    message: str = "success", 
    auth: str = None
) -> Dict[str, Any]:
    """
    Construct a response with optional authentication.
    """
    response = get_json_result(data, code, message)
    if auth:
        response["auth"] = auth
    return response

# FastAPI-specific response helpers
def get_error_response(
    message: str = "error",
    code: int = settings.RetCode.PARAM_ERROR, 
    status_code: int = status.HTTP_400_BAD_REQUEST
) -> JSONResponse:
    """
    Returns a FastAPI JSONResponse with an error.
    """
    return JSONResponse(
        status_code=status_code,
        content=get_error_data_result(message, code)
    )

def get_success_response(
    data: Any = None, 
    message: str = "success",
    code: int = settings.RetCode.SUCCESS,
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    """
    Returns a FastAPI JSONResponse with success data.
    """
    return JSONResponse(
        status_code=status_code,
        content=get_json_result(data, code, message)
    )

# Request validation
def validate_params(*required_params):
    """
    Decorator for checking required parameters in request body.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            try:
                data = await request.json()
            except Exception:
                data = {}
            
            missing_params = [param for param in required_params if param not in data]
            if missing_params:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required parameters: {', '.join(missing_params)}"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Utility functions for checking data
def check_duplicate_ids(ids: List[str]) -> bool:
    """
    Check if there are duplicate IDs in a list.
    """
    return len(ids) != len(set(ids)) 