from typing import Optional, List, Dict, Any, Union
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel, Field, validator, root_validator

from api import settings
from api.constants import API_VERSION
from api.db import StatusEnum
from api.db.services.dialog_service import DialogService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.llm_service import TenantLLMService, LLMService
from api.db.services.user_service import TenantService
from api.utils import get_uuid, current_timestamp, get_format_time
from api.utils.fastapi_utils import token_required, get_json_result, get_error_data_result, check_duplicate_ids

# Pydantic models for request/response validation
class PromptParameter(BaseModel):
    key: str
    optional: bool = False

class LLMSetting(BaseModel):
    temperature: Optional[float] = 0.10
    top_p: Optional[float] = 0.30
    presence_penalty: Optional[float] = 0.40
    frequency_penalty: Optional[float] = 0.70
    max_tokens: Optional[int] = 512
    
    class Config:
        extra = "allow"

class PromptConfig(BaseModel):
    system: str
    prologue: Optional[str] = "Hi! I am your assistant, can I help you?"
    empty_response: Optional[str] = None
    quote: Optional[bool] = True
    keyword: Optional[bool] = False
    tts: Optional[bool] = False
    refine_multiturn: Optional[bool] = False
    parameters: Optional[List[PromptParameter]] = Field(default_factory=lambda: [{"key": "knowledge", "optional": True}])
    
    class Config:
        extra = "allow"

class AssistantCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    kb_ids: List[str]
    prompt_config: Optional[PromptConfig] = None
    similarity_threshold: Optional[float] = 0.2
    vector_similarity_weight: Optional[float] = 0.7
    top_n: Optional[int] = 8
    use_kg: Optional[bool] = False
    reasoning: Optional[bool] = False
    rerank_id: Optional[str] = None
    llm_id: str
    llm_setting: Optional[LLMSetting] = None
    id: Optional[str] = None
    
    class Config:
        extra = "allow"

class AssistantListParams(BaseModel):
    page: int = 1
    page_size: int = 30
    orderby: str = "create_time"
    desc: bool = True
    name: Optional[str] = None
    id: Optional[str] = None

class DefaultModelsUpdate(BaseModel):
    embedding_model: str
    chat_model: str
    
    class Config:
        extra = "allow"

router = APIRouter(
    prefix=f"/api/{API_VERSION}/assistant",
    tags=["Assistant Management"]
)

# Default models endpoint
defaults_router = APIRouter(
    prefix=f"/api/{API_VERSION}/defaults",
    tags=["Default Models"]
)

@router.post("", response_model=Dict[str, Any])
async def create_assistant(
    assistant_data: AssistantCreate,
    tenant_id: str = Depends(token_required)
):
    """
    Create or update a chat assistant.
    """
    try:
        # Convert request model to dict
        req = assistant_data.dict(exclude_unset=True)
        
        # Validate knowledge base IDs
        kb_ids = req.get("kb_ids", [])
        if not kb_ids:
            return get_error_data_result(
                message="At least one knowledge base must be specified",
                code=settings.RetCode.PARAM_ERROR
            )
        
        # Check for duplicate IDs
        if check_duplicate_ids(kb_ids):
            return get_error_data_result(
                message="Duplicate knowledge base IDs",
                code=settings.RetCode.PARAM_ERROR
            )
        
        # Check if knowledge bases exist and belong to tenant
        for kb_id in kb_ids:
            kb = KnowledgebaseService.accessible(kb_id=kb_id, user_id=tenant_id)
            if not kb:
                return get_error_data_result(
                    message=f"Knowledge base {kb_id} not found or not accessible",
                    code=settings.RetCode.PARAM_ERROR
                )
        
        # Check if LLM exists and is accessible
        llm_id = req.get("llm_id")
        if not llm_id:
            return get_error_data_result(
                message="LLM ID is required",
                code=settings.RetCode.PARAM_ERROR
            )
            
        if not TenantLLMService.query(tenant_id=tenant_id, llm_name=llm_id, model_type="chat"):
            return get_error_data_result(
                message=f"LLM {llm_id} not found or not accessible",
                code=settings.RetCode.PARAM_ERROR
            )
        
        # Check reranker if provided
        rerank_id = req.get("rerank_id")
        if rerank_id:
            value_rerank_model = ["BAAI/bge-reranker-v2-m3", "maidalun1020/bce-reranker-base_v1"]
            if rerank_id not in value_rerank_model and not TenantLLMService.query(
                tenant_id=tenant_id,
                llm_name=rerank_id,
                model_type="rerank"
            ):
                return get_error_data_result(
                    message=f"Reranker {rerank_id} not found or not accessible",
                    code=settings.RetCode.PARAM_ERROR
                )
        
        # Update or create assistant
        assistant_id = req.get("id")
        if assistant_id:
            # Update existing assistant
            assistant = DialogService.query(id=assistant_id, tenant_id=tenant_id, status=StatusEnum.VALID.value)
            if not assistant:
                return get_error_data_result(
                    message=f"Assistant {assistant_id} not found or not accessible",
                    code=settings.RetCode.PARAM_ERROR
                )
                
            # Update fields
            assistant_obj = assistant[0]
            
            # Skip duplicate name check if name is unchanged
            new_name = req.get("name")
            if new_name and new_name != assistant_obj.name:
                # Check for duplicate name
                existing = DialogService.query(name=new_name, tenant_id=tenant_id, status=StatusEnum.VALID.value)
                if existing and existing[0].id != assistant_id:
                    return get_error_data_result(
                        message=f"Assistant with name '{new_name}' already exists",
                        code=settings.RetCode.PARAM_ERROR
                    )
                
            # Convert kb_ids to string for storage if present
            if "kb_ids" in req:
                req["kb_ids"] = ",".join(req["kb_ids"])
                
            # Update fields
            req["update_time"] = current_timestamp()
            req["update_date"] = get_format_time()
            
            for key, value in req.items():
                if key != "id":
                    setattr(assistant_obj, key, value)
                    
            if not assistant_obj.save():
                return get_error_data_result(
                    message="Failed to update assistant",
                    code=settings.RetCode.SERVER_ERROR
                )
                
            # Get updated assistant
            e, assistant = DialogService.get_by_id(assistant_id)
            if not e:
                return get_error_data_result(
                    message="Failed to retrieve updated assistant",
                    code=settings.RetCode.SERVER_ERROR
                )
                
            # Format response
            response = assistant.to_json()
            if "kb_ids" in response and isinstance(response["kb_ids"], str):
                response["kb_ids"] = response["kb_ids"].split(",") if response["kb_ids"] else []
                
            return get_json_result(response)
        else:
            # Create new assistant
            # Check for duplicate name
            name = req.get("name")
            if not name:
                return get_error_data_result(
                    message="Assistant name is required",
                    code=settings.RetCode.PARAM_ERROR
                )
                
            existing = DialogService.query(name=name, tenant_id=tenant_id, status=StatusEnum.VALID.value)
            if existing:
                return get_error_data_result(
                    message=f"Assistant with name '{name}' already exists",
                    code=settings.RetCode.PARAM_ERROR
                )
                
            # Set default values
            req["id"] = get_uuid()
            req["tenant_id"] = tenant_id
            req["create_time"] = current_timestamp()
            req["create_date"] = get_format_time()
            req["update_time"] = current_timestamp()
            req["update_date"] = get_format_time()
            req["status"] = StatusEnum.VALID.value
            
            # Convert kb_ids to string for storage
            if "kb_ids" in req:
                req["kb_ids"] = ",".join(req["kb_ids"])
                
            # Create assistant
            if not DialogService.save(**req):
                return get_error_data_result(
                    message="Failed to create assistant",
                    code=settings.RetCode.SERVER_ERROR
                )
                
            # Get created assistant
            e, assistant = DialogService.get_by_id(req["id"])
            if not e:
                return get_error_data_result(
                    message="Failed to retrieve created assistant",
                    code=settings.RetCode.SERVER_ERROR
                )
                
            # Format response
            response = assistant.to_json()
            if "kb_ids" in response and isinstance(response["kb_ids"], str):
                response["kb_ids"] = response["kb_ids"].split(",") if response["kb_ids"] else []
                
            return get_json_result(response)
            
    except Exception as e:
        return get_error_data_result(
            message=f"Error creating/updating assistant: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@router.get("", response_model=Dict[str, Any])
async def list_assistants(
    page: int = 1,
    page_size: int = 30,
    orderby: str = "create_time",
    desc: bool = True,
    name: Optional[str] = None,
    id: Optional[str] = None,
    tenant_id: str = Depends(token_required)
):
    """
    Returns all chat assistants with their configuration properties.
    """
    try:
        # Build filter conditions
        filters = {"tenant_id": tenant_id, "status": StatusEnum.VALID.value}
        if id:
            filters["id"] = id
        
        # Get total count and paginated assistants
        total = DialogService.count(filters, name)
        assistants = DialogService.query_page(
            page=page,
            page_size=page_size,
            filters=filters,
            keywords=name,
            order_by=orderby,
            desc=desc
        )
        
        # Format assistants for response
        assistant_list = []
        for assistant in assistants:
            assistant_data = assistant.to_json()
            if "kb_ids" in assistant_data and isinstance(assistant_data["kb_ids"], str):
                assistant_data["kb_ids"] = assistant_data["kb_ids"].split(",") if assistant_data["kb_ids"] else []
            assistant_list.append(assistant_data)
            
        return get_json_result({
            "total": total,
            "assistants": assistant_list
        })
        
    except Exception as e:
        return get_error_data_result(
            message=f"Error listing assistants: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@router.delete("", response_model=Dict[str, Any])
async def delete_assistants(
    ids: Optional[List[str]] = None,
    tenant_id: str = Depends(token_required)
):
    """
    Delete one or more assistants.
    """
    try:
        deleted_ids = []
        
        if ids:
            # Check for duplicate IDs
            if check_duplicate_ids(ids):
                return get_error_data_result(
                    message="Duplicate assistant IDs",
                    code=settings.RetCode.PARAM_ERROR
                )
                
            # Delete specific assistants
            for assistant_id in ids:
                # Check if assistant exists and belongs to tenant
                assistant = DialogService.query(id=assistant_id, tenant_id=tenant_id, status=StatusEnum.VALID.value)
                if not assistant:
                    continue
                    
                # Delete assistant
                if DialogService.delete(id=assistant_id):
                    deleted_ids.append(assistant_id)
        else:
            # Delete all assistants for this tenant
            assistants = DialogService.query(tenant_id=tenant_id, status=StatusEnum.VALID.value)
            for assistant in assistants:
                if DialogService.delete(id=assistant.id):
                    deleted_ids.append(assistant.id)
                    
        return get_json_result({"deleted_ids": deleted_ids})
        
    except Exception as e:
        return get_error_data_result(
            message=f"Error deleting assistants: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@router.post("/{assistant_id}/set-default", response_model=Dict[str, Any])
async def set_default_assistant(
    assistant_id: str,
    tenant_id: str = Depends(token_required)
):
    """
    Set a chat assistant as the default for user interactions.
    """
    try:
        # Check if assistant exists and belongs to tenant
        assistant = DialogService.query(id=assistant_id, tenant_id=tenant_id, status=StatusEnum.VALID.value)
        if not assistant:
            return get_error_data_result(
                message=f"Assistant {assistant_id} not found or not accessible",
                code=settings.RetCode.PARAM_ERROR
            )
            
        # Get tenant
        e, tenant = TenantService.get_by_id(tenant_id)
        if not e:
            return get_error_data_result(
                message="Tenant not found",
                code=settings.RetCode.SERVER_ERROR
            )
            
        # Update tenant with default assistant
        tenant.default_assistant_id = assistant_id
        tenant.update_time = current_timestamp()
        tenant.update_date = get_format_time()
        
        if not tenant.save():
            return get_error_data_result(
                message="Failed to set default assistant",
                code=settings.RetCode.SERVER_ERROR
            )
            
        return get_json_result({"id": assistant_id, "default": True})
        
    except Exception as e:
        return get_error_data_result(
            message=f"Error setting default assistant: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@defaults_router.post("", response_model=Dict[str, Any])
async def set_default_models(
    defaults: DefaultModelsUpdate,
    tenant_id: str = Depends(token_required)
):
    """
    Set default models for new resources.
    """
    try:
        # Get tenant
        e, tenant = TenantService.get_by_id(tenant_id)
        if not e:
            return get_error_data_result(
                message="Tenant not found",
                code=settings.RetCode.SERVER_ERROR
            )
            
        # Validate embedding model
        embd_id = defaults.embedding_model
        if not TenantLLMService.query(tenant_id=tenant_id, llm_name=embd_id, model_type="embd"):
            return get_error_data_result(
                message=f"Embedding model {embd_id} not found or not accessible",
                code=settings.RetCode.PARAM_ERROR
            )
            
        # Validate chat model
        llm_id = defaults.chat_model
        if not TenantLLMService.query(tenant_id=tenant_id, llm_name=llm_id, model_type="chat"):
            return get_error_data_result(
                message=f"Chat model {llm_id} not found or not accessible",
                code=settings.RetCode.PARAM_ERROR
            )
            
        # Update tenant with default models
        tenant.embd_id = embd_id
        tenant.llm_id = llm_id
        tenant.update_time = current_timestamp()
        tenant.update_date = get_format_time()
        
        if not tenant.save():
            return get_error_data_result(
                message="Failed to set default models",
                code=settings.RetCode.SERVER_ERROR
            )
            
        return get_json_result({
            "embedding_model": embd_id,
            "chat_model": llm_id
        })
        
    except Exception as e:
        return get_error_data_result(
            message=f"Error setting default models: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@defaults_router.get("", response_model=Dict[str, Any])
async def get_default_models(tenant_id: str = Depends(token_required)):
    """
    Get current default model settings.
    """
    try:
        # Get tenant
        e, tenant = TenantService.get_by_id(tenant_id)
        if not e:
            return get_error_data_result(
                message="Tenant not found",
                code=settings.RetCode.SERVER_ERROR
            )
            
        return get_json_result({
            "embedding_model": tenant.embd_id,
            "chat_model": tenant.llm_id
        })
        
    except Exception as e:
        return get_error_data_result(
            message=f"Error getting default models: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        ) 