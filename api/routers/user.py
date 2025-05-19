from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status, Body
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, Field, EmailStr
from werkzeug.security import generate_password_hash, check_password_hash

from api.db.services.user_service import UserService, TenantService, UserTenantService
from api.db.services.file_service import FileService
from api.db.services.llm_service import TenantLLMService, LLMService
from api.db import UserTenantRole, FileType
from api import settings
from api.utils import (
    get_uuid, 
    get_format_time, 
    decrypt, 
    download_img, 
    current_timestamp, 
    datetime_format
)
from api.utils.fastapi_utils import (
    token_required, 
    get_json_result, 
    get_error_data_result, 
    construct_response,
    validate_params
)
from api.apps.auth import get_auth_client

router = APIRouter(
    prefix=f"/{settings.API_VERSION}/user",
    tags=["User"]
)

# Pydantic models for request/response validation
class LoginRequest(BaseModel):
    email: str
    password: str

class TenantInfoResponse(BaseModel):
    tenant_id: str
    asr_id: str
    embd_id: str
    img2txt_id: str
    llm_id: str

class TenantInfoUpdateRequest(BaseModel):
    tenant_id: str
    asr_id: str
    embd_id: str
    img2txt_id: str
    llm_id: str

class UserRegistrationRequest(BaseModel):
    nickname: str
    email: EmailStr
    password: str

class UserSettingsRequest(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    oldPassword: Optional[str] = None
    newPassword: Optional[str] = None

@router.post("/login")
async def login(login_data: LoginRequest):
    """
    User login endpoint.
    """
    email = login_data.email
    users = UserService.query(email=email)
    if not users:
        return get_json_result(
            data=False,
            code=settings.RetCode.AUTHENTICATION_ERROR,
            message=f"Email: {email} is not registered!"
        )

    password = login_data.password
    try:
        password = decrypt(password)
    except Exception:
        return get_json_result(
            data=False, 
            code=settings.RetCode.SERVER_ERROR, 
            message="Fail to crypt password"
        )

    user = UserService.query_user(email, password)
    if user:
        response_data = user.to_json()
        user.access_token = get_uuid()
        user.update_time = current_timestamp()
        user.update_date = datetime_format(datetime.now())
        user.save()
        msg = "Welcome back!"
        return construct_response(data=response_data, auth=user.get_id(), message=msg)
    else:
        return get_json_result(
            data=False,
            code=settings.RetCode.AUTHENTICATION_ERROR,
            message="Email and password do not match!"
        )

@router.get("/login/channels")
async def get_login_channels():
    """
    Get all supported authentication channels.
    """
    try:
        channels = []
        for channel, config in settings.OAUTH_CONFIG.items():
            channels.append({
                "channel": channel,
                "display_name": config.get("display_name", channel.title()),
                "icon": config.get("icon", "sso"),
            })
        return get_json_result(data=channels)
    except Exception as e:
        return get_json_result(
            data=[],
            message=f"Load channels failure, error: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@router.get("/login/{channel}")
async def oauth_login(channel: str):
    """
    Redirect to OAuth login page
    """
    channel_config = settings.OAUTH_CONFIG.get(channel)
    if not channel_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel name: {channel}"
        )
    auth_cli = get_auth_client(channel_config)
    auth_url = auth_cli.get_authorization_url()
    return RedirectResponse(auth_url)

@router.get("/oauth/callback/{channel}")
async def oauth_callback(channel: str, code: Optional[str] = None):
    """
    Handle the OAuth/OIDC callback for various channels dynamically.
    """
    if not code:
        return RedirectResponse("/?error=missing_code")
    
    try:
        channel_config = settings.OAUTH_CONFIG.get(channel)
        if not channel_config:
            raise ValueError(f"Invalid channel name: {channel}")
        
        auth_cli = get_auth_client(channel_config)
        
        # Exchange authorization code for access token
        token_info = auth_cli.exchange_code_for_token(code)
        access_token = token_info.get("access_token")
        if not access_token:
            return RedirectResponse("/?error=token_failed")

        id_token = token_info.get("id_token")

        # Fetch user info
        user_info = auth_cli.fetch_user_info(access_token, id_token=id_token)
        if not user_info.email:
            return RedirectResponse("/?error=email_missing")

        # Login or register
        users = UserService.query(email=user_info.email)
        user_id = get_uuid()
        
        if not users:
            try:
                try:
                    avatar = download_img(user_info.avatar_url)
                except Exception:
                    avatar = ""

                users = user_register(
                    user_id,
                    {
                        "access_token": get_uuid(),
                        "email": user_info.email,
                        "avatar": avatar,
                        "nickname": user_info.nickname,
                    }
                )
            except Exception as e:
                rollback_user_registration(user_id)
                raise e
        
        user = users[0]
        user.access_token = get_uuid()
        user.save()
        
        return RedirectResponse(f"/?token={user.access_token}")
    except Exception as e:
        return RedirectResponse(f"/?error={str(e)}")

@router.get("/logout")
async def logout(tenant_id: str = Depends(token_required)):
    """
    User logout
    """
    try:
        users = UserService.query(id=tenant_id)
        if users:
            user = users[0]
            user.access_token = ""
            user.save()
        return get_json_result(True)
    except Exception as e:
        return get_json_result(
            data=False,
            code=settings.RetCode.EXCEPTION_ERROR,
            message=str(e)
        )

@router.post("/setting")
async def setting_user(
    settings_data: UserSettingsRequest,
    tenant_id: str = Depends(token_required)
):
    """
    Update user settings
    """
    try:
        users = UserService.query(id=tenant_id)
        if not users:
            return get_json_result(
                data=False,
                code=settings.RetCode.PARAM_ERROR,
                message="User not found"
            )
        
        user = users[0]
        
        # Update nickname
        if settings_data.nickname is not None:
            user.nickname = settings_data.nickname
        
        # Update avatar
        if settings_data.avatar is not None:
            user.avatar = settings_data.avatar
        
        # Update password
        if settings_data.oldPassword and settings_data.newPassword:
            try:
                old_pwd = decrypt(settings_data.oldPassword)
                new_pwd = decrypt(settings_data.newPassword)
                
                if not check_password_hash(user.pwd_hash, old_pwd):
                    return get_json_result(
                        data=False,
                        code=settings.RetCode.PARAM_ERROR,
                        message="Old password is incorrect"
                    )
                
                user.pwd_hash = generate_password_hash(new_pwd)
            except Exception:
                return get_json_result(
                    data=False,
                    code=settings.RetCode.SERVER_ERROR,
                    message="Fail to crypt password"
                )
        
        user.save()
        return get_json_result(True)
    except Exception as e:
        return get_json_result(
            data=False,
            code=settings.RetCode.EXCEPTION_ERROR,
            message=str(e)
        )

@router.get("/info")
async def user_profile(tenant_id: str = Depends(token_required)):
    """
    Get user profile information
    """
    try:
        users = UserService.query(id=tenant_id)
        if not users:
            return get_json_result(
                data=False,
                code=settings.RetCode.PARAM_ERROR,
                message="User not found"
            )
        
        user_info = users[0].to_json()
        return get_json_result(user_info)
    except Exception as e:
        return get_json_result(
            data=False,
            code=settings.RetCode.EXCEPTION_ERROR,
            message=str(e)
        )

def rollback_user_registration(user_id: str):
    """
    Rollback user registration in case of error
    """
    try:
        UserService.delete(id=user_id)
    except Exception:
        pass
    
    try:
        TenantService.delete(id=user_id)
    except Exception:
        pass
    
    try:
        UserTenantService.delete(user_id=user_id)
    except Exception:
        pass

def user_register(user_id: str, user: Dict[str, Any]):
    """
    Register a new user
    """
    # Create user
    llm_default = LLMService.default_llm()
    if not user.get("pwd_hash"):
        user["pwd_hash"] = generate_password_hash(get_uuid())
    user["id"] = user_id
    user["update_time"] = current_timestamp()
    user["update_date"] = get_format_time()
    
    if not UserService.save(**user):
        raise Exception("Save user error")
    
    # Create tenant
    tenant = {
        "id": user_id,
        "name": user.get("nickname", ""),
        "tenant_type": "personal",
        "update_time": current_timestamp(),
        "update_date": get_format_time(),
        "asr_id": llm_default.get("asr", ""),
        "embd_id": llm_default.get("embd", ""),
        "img2txt_id": llm_default.get("img2txt", ""),
        "llm_id": llm_default.get("llm", ""),
    }
    
    if not TenantService.save(**tenant):
        raise Exception("Save tenant error")
    
    # Create user tenant relationship
    user_tenant = {
        "user_id": user_id,
        "tenant_id": user_id,
        "role": UserTenantRole.OWNER.value,
        "update_time": current_timestamp(),
        "update_date": get_format_time(),
    }
    
    if not UserTenantService.save(**user_tenant):
        raise Exception("Save user tenant relationship error")
    
    return UserService.query(id=user_id)

@router.post("/register")
@validate_params("nickname", "email", "password")
async def user_add(request: Request):
    """
    Register a new user
    """
    try:
        user_data = await request.json()
        nickname = user_data.get("nickname")
        email = user_data.get("email")
        
        # Email validation
        if not email:
            return get_error_data_result("Email is required")
        
        # Check email format
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        if not re.match(regex, email):
            return get_error_data_result("Invalid email format")
        
        # Check if email already exists
        if UserService.query(email=email):
            return get_error_data_result(f"Email: {email} is already registered")
        
        # Password validation
        password = user_data.get("password")
        if not password:
            return get_error_data_result("Password is required")
        
        try:
            password = decrypt(password)
        except Exception:
            return get_error_data_result("Fail to crypt password")
        
        # Register user
        user_id = get_uuid()
        user = {
            "nickname": nickname,
            "email": email,
            "pwd_hash": generate_password_hash(password),
            "access_token": get_uuid(),
        }
        
        try:
            user_register(user_id, user)
        except Exception as e:
            rollback_user_registration(user_id)
            return get_error_data_result(str(e))
        
        # Return new user
        users = UserService.query(id=user_id)
        if not users:
            return get_error_data_result("Fail to create user")
        
        user = users[0]
        response_data = user.to_json()
        return construct_response(data=response_data, auth=user.get_id())
    
    except Exception as e:
        return get_error_data_result(str(e))

@router.get("/tenant_info")
async def tenant_info(tenant_id: str = Depends(token_required)):
    """
    Get tenant information
    """
    try:
        e, res = TenantService.get_by_id(tenant_id)
        if not e:
            return get_error_data_result(message="Tenant not found!")
        
        return get_json_result(
            data={
                "tenant_id": res.id,
                "asr_id": res.asr_id,
                "embd_id": res.embd_id,
                "img2txt_id": res.img2txt_id,
                "llm_id": res.llm_id,
            }
        )
    except Exception as e:
        return get_error_data_result(str(e))

@router.post("/set_tenant_info")
async def set_tenant_info(
    tenant_info: TenantInfoUpdateRequest,
    tenant_id: str = Depends(token_required)
):
    """
    Update tenant information
    """
    try:
        if tenant_info.tenant_id != tenant_id:
            return get_error_data_result(message="You don't own the tenant!")
        
        e, tenant = TenantService.get_by_id(tenant_id)
        if not e:
            return get_error_data_result(message="Tenant not found!")
        
        # Update tenant information
        tenant.asr_id = tenant_info.asr_id
        tenant.embd_id = tenant_info.embd_id
        tenant.img2txt_id = tenant_info.img2txt_id
        tenant.llm_id = tenant_info.llm_id
        tenant.update_time = current_timestamp()
        tenant.update_date = get_format_time()
        
        if not tenant.save():
            return get_error_data_result(message="Fail to update tenant!")
        
        return get_json_result(True)
    except Exception as e:
        return get_error_data_result(str(e)) 