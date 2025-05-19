from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, validator

from api import settings
from api.constants import API_VERSION
from api.db import StatusEnum
from api.db.services.user_service import UserService
from api.utils import get_uuid, current_timestamp, get_format_time, datetime_format
from api.utils.fastapi_utils import token_required, get_json_result, get_error_data_result

# Pydantic models for request/response validation
class TokenCreateRequest(BaseModel):
    name: str = Field(..., description="A descriptive name for the token")
    expiration: Optional[int] = Field(None, description="Token validity in days. Default is no expiration")

class TokenResponse(BaseModel):
    token: str = Field(..., description="The API token value")
    id: str = Field(..., description="Unique identifier for the token")
    tenant_id: str = Field(..., description="The tenant ID associated with this token")
    create_time: int = Field(..., description="Creation timestamp in milliseconds")
    create_date: str = Field(..., description="Formatted creation date")
    name: str = Field(..., description="Token name")
    expiration_date: Optional[str] = Field(None, description="Expiration date if applicable")
    
class TokenListItem(BaseModel):
    id: str
    name: str
    tenant_id: str
    create_time: int
    create_date: str
    expiration_date: Optional[str] = None

router = APIRouter(
    prefix=f"/api/{API_VERSION}/admin/token",
    tags=["Admin - Token Management"]
)

@router.post("/create", response_model=TokenResponse)
async def create_token(
    request: TokenCreateRequest,
    tenant_id: str = Depends(token_required)
):
    """
    Creates a new admin API token.
    
    Requires existing admin token or system setup credentials in the Authorization header.
    """
    try:
        token_id = get_uuid()
        token_value = get_uuid()
        
        # Check if user has admin privileges
        user = UserService.query(id=tenant_id, status=StatusEnum.VALID.value)
        if not user or user[0].role != "admin":
            return get_error_data_result(
                message="Only admin users can create tokens",
                code=settings.RetCode.AUTHENTICATION_ERROR
            )
        
        # Calculate expiration date if provided
        expiration_date = None
        if request.expiration:
            expiry_datetime = datetime.now() + timedelta(days=request.expiration)
            expiration_date = datetime_format(expiry_datetime)
        
        # Create token record
        token = {
            "id": token_id,
            "token": token_value,
            "tenant_id": tenant_id,
            "name": request.name,
            "create_time": current_timestamp(),
            "create_date": get_format_time(),
            "expiration_date": expiration_date,
            "status": StatusEnum.VALID.value
        }
        
        # Save token to database
        if not UserService.save_token(**token):
            return get_error_data_result(
                message="Failed to create token",
                code=settings.RetCode.SERVER_ERROR
            )
        
        return get_json_result(token)
    
    except Exception as e:
        return get_error_data_result(
            message=f"Error creating token: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@router.get("/list", response_model=List[TokenListItem])
async def list_tokens(tenant_id: str = Depends(token_required)):
    """
    Lists all admin tokens associated with the current tenant.
    
    Requires existing admin token in the Authorization header.
    """
    try:
        # Check if user has admin privileges
        user = UserService.query(id=tenant_id, status=StatusEnum.VALID.value)
        if not user or user[0].role != "admin":
            return get_error_data_result(
                message="Only admin users can list tokens",
                code=settings.RetCode.AUTHENTICATION_ERROR
            )
            
        # Get tokens for this tenant
        tokens = UserService.query_tokens(tenant_id=tenant_id, status=StatusEnum.VALID.value)
        
        # Format tokens for response
        token_list = []
        for token in tokens:
            token_data = {
                "id": token.id,
                "name": token.name,
                "tenant_id": token.tenant_id,
                "create_time": token.create_time,
                "create_date": token.create_date,
            }
            
            if token.expiration_date:
                token_data["expiration_date"] = token.expiration_date
            
            token_list.append(token_data)
            
        return get_json_result(token_list)
    
    except Exception as e:
        return get_error_data_result(
            message=f"Error listing tokens: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@router.delete("/{token_id}")
async def revoke_token(token_id: str, tenant_id: str = Depends(token_required)):
    """
    Revokes a specific admin token.
    
    Requires existing admin token in the Authorization header.
    
    Parameters:
        token_id: ID of the token to revoke
    """
    try:
        # Check if user has admin privileges
        user = UserService.query(id=tenant_id, status=StatusEnum.VALID.value)
        if not user or user[0].role != "admin":
            return get_error_data_result(
                message="Only admin users can revoke tokens",
                code=settings.RetCode.AUTHENTICATION_ERROR
            )
            
        # Check if token exists and belongs to this tenant
        token = UserService.query_tokens(id=token_id, tenant_id=tenant_id, status=StatusEnum.VALID.value)
        if not token:
            return get_error_data_result(
                message=f"Token {token_id} not found or not accessible",
                code=settings.RetCode.PARAM_ERROR
            )
            
        # Delete the token
        if not UserService.delete_token(id=token_id):
            return get_error_data_result(
                message=f"Failed to delete token {token_id}",
                code=settings.RetCode.SERVER_ERROR
            )
            
        return get_json_result({"id": token_id, "deleted": True})
    
    except Exception as e:
        return get_error_data_result(
            message=f"Error revoking token: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        ) 