from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, Request, Body
from pydantic import BaseModel, Field, validator

from api import settings
from api.constants import API_VERSION
from api.db import StatusEnum
from api.db.services.dialog_service import DialogService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.llm_service import TenantLLMService
from api.db.services.user_service import TenantService
from api.utils import get_uuid
from api.utils.fastapi_utils import token_required, get_error_data_result, get_result, check_duplicate_ids

router = APIRouter(
    prefix=f"/api/{API_VERSION}/chats",
    tags=["SDK Chat"]
)

# Pydantic model for LLM settings
class LLMSettings(BaseModel):
    model_name: str
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.95
    top_k: Optional[int] = 50
    max_tokens: Optional[int] = 500
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0

    class Config:
        extra = "allow"

# Pydantic model for prompt parameters
class PromptParameter(BaseModel):
    key: str
    optional: bool = False

# Pydantic model for prompt configuration
class PromptConfig(BaseModel):
    system: Optional[str] = None
    prologue: Optional[str] = "Hi! I'm your assistant, what can I do for you?"
    parameters: Optional[List[PromptParameter]] = []
    empty_response: Optional[str] = "Sorry! No relevant content was found in the knowledge base!"
    quote: Optional[bool] = True
    tts: Optional[bool] = False
    refine_multiturn: Optional[bool] = True
    similarity_threshold: Optional[float] = None
    vector_similarity_weight: Optional[float] = None
    top_n: Optional[int] = None
    rerank_id: Optional[str] = None
    top_k: Optional[int] = None

    class Config:
        extra = "allow"

# Pydantic model for creating a chat
class CreateChatRequest(BaseModel):
    name: str
    description: Optional[str] = "A helpful Assistant"
    llm: Optional[LLMSettings] = None
    dataset_ids: List[str] = []
    prompt: Optional[PromptConfig] = None
    avatar: Optional[str] = ""
    similarity_threshold: Optional[float] = 0.0
    vector_similarity_weight: Optional[float] = 1.0
    top_n: Optional[int] = 6
    top_k: Optional[int] = 1024
    rerank_id: Optional[str] = ""

    class Config:
        extra = "allow"

# Pydantic model for updating a chat
class UpdateChatRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    llm: Optional[LLMSettings] = None
    dataset_ids: Optional[List[str]] = None
    prompt: Optional[PromptConfig] = None
    avatar: Optional[str] = None
    show_quotation: Optional[bool] = None

    class Config:
        extra = "allow"

# Pydantic model for bulk delete
class BulkDeleteRequest(BaseModel):
    ids: List[str]

@router.post("")
async def create_chat(
    request: CreateChatRequest,
    tenant_id: str = Depends(token_required)
):
    """
    Create a new chat
    """
    try:
        # Convert request model to dict for processing
        req = request.dict(exclude_unset=True)
        
        # Validate dataset IDs
        ids = [i for i in req.get("dataset_ids", []) if i]
        for kb_id in ids:
            kbs = KnowledgebaseService.accessible(kb_id=kb_id, user_id=tenant_id)
            if not kbs:
                return get_error_data_result(f"You don't own the dataset {kb_id}")
            kbs = KnowledgebaseService.query(id=kb_id)
            kb = kbs[0]
            if kb.chunk_num == 0:
                return get_error_data_result(f"The dataset {kb_id} doesn't own parsed file")
        
        kbs = KnowledgebaseService.get_by_ids(ids) if ids else []
        embd_ids = [TenantLLMService.split_model_name_and_factory(kb.embd_id)[0] for kb in kbs]
        embd_count = list(set(embd_ids))
        if len(embd_count) > 1:
            return get_result(
                message='Datasets use different embedding models."',
                code=settings.RetCode.AUTHENTICATION_ERROR
            )
        
        req["kb_ids"] = ids
        
        # Process LLM settings
        llm = req.get("llm")
        if llm:
            if "model_name" in llm:
                req["llm_id"] = llm.pop("model_name")
                if not TenantLLMService.query(tenant_id=tenant_id, llm_name=req["llm_id"], model_type="chat"):
                    return get_error_data_result(f"`model_name` {req.get('llm_id')} doesn't exist")
            req["llm_setting"] = req.pop("llm")
        
        # Get tenant
        e, tenant = TenantService.get_by_id(tenant_id)
        if not e:
            return get_error_data_result(message="Tenant not found!")
        
        # Process prompt configuration
        prompt = req.get("prompt")
        key_mapping = {
            "parameters": "variables",
            "prologue": "opener",
            "quote": "show_quote",
            "system": "prompt",
            "rerank_id": "rerank_model",
            "vector_similarity_weight": "keywords_similarity_weight"
        }
        
        key_list = ["similarity_threshold", "vector_similarity_weight", "top_n", "rerank_id", "top_k"]
        if prompt:
            for new_key, old_key in key_mapping.items():
                if old_key in prompt:
                    prompt[new_key] = prompt.pop(old_key)
            for key in key_list:
                if key in prompt:
                    req[key] = prompt.pop(key)
            req["prompt_config"] = req.pop("prompt")
        
        # Initialize additional fields
        req["id"] = get_uuid()
        req["description"] = req.get("description", "A helpful Assistant")
        req["icon"] = req.get("avatar", "")
        req["top_n"] = req.get("top_n", 6)
        req["top_k"] = req.get("top_k", 1024)
        req["rerank_id"] = req.get("rerank_id", "")
        
        # Validate rerank model
        if req.get("rerank_id"):
            value_rerank_model = ["BAAI/bge-reranker-v2-m3", "maidalun1020/bce-reranker-base_v1"]
            if req["rerank_id"] not in value_rerank_model and not TenantLLMService.query(
                tenant_id=tenant_id,
                llm_name=req.get("rerank_id"),
                model_type="rerank"
            ):
                return get_error_data_result(f"`rerank_model` {req.get('rerank_id')} doesn't exist")
        
        # Use tenant's default LLM if not specified
        if not req.get("llm_id"):
            req["llm_id"] = tenant.llm_id
        
        # Validate name
        if not req.get("name"):
            return get_error_data_result(message="`name` is required.")
        if DialogService.query(name=req["name"], tenant_id=tenant_id, status=StatusEnum.VALID.value):
            return get_error_data_result(message="Duplicated chat name in creating chat.")
        
        # Set tenant_id
        if req.get("tenant_id"):
            return get_error_data_result(message="`tenant_id` must not be provided.")
        req["tenant_id"] = tenant_id
        
        # Set default prompt parameters
        default_prompt = {
            "system": """You are an intelligent assistant. Please summarize the content of the knowledge base to answer the question. Please list the data in the knowledge base and answer in detail. When all knowledge base content is irrelevant to the question, your answer must include the sentence "The answer you are looking for is not found in the knowledge base!" Answers need to consider chat history.
          Here is the knowledge base:
          {knowledge}
          The above is the knowledge base.""",
            "prologue": "Hi! I'm your assistant, what can I do for you?",
            "parameters": [
                {"key": "knowledge", "optional": False}
            ],
            "empty_response": "Sorry! No relevant content was found in the knowledge base!",
            "quote": True,
            "tts": False,
            "refine_multiturn": True
        }
        
        key_list_2 = ["system", "prologue", "parameters", "empty_response", "quote", "tts", "refine_multiturn"]
        if "prompt_config" not in req:
            req['prompt_config'] = {}
        for key in key_list_2:
            temp = req['prompt_config'].get(key)
            if (not temp and key == 'system') or (key not in req["prompt_config"]):
                req['prompt_config'][key] = default_prompt[key]
        
        # Validate parameters are used in system prompt
        for p in req['prompt_config']["parameters"]:
            if p.get("optional"):
                continue
            if req['prompt_config']["system"].find("{%s}" % p["key"]) < 0:
                return get_error_data_result(
                    message="Parameter '{}' is not used".format(p["key"]))
        
        # Save chat
        if not DialogService.save(**req):
            return get_error_data_result(message="Fail to new a chat!")
        
        # Get and format response
        e, res = DialogService.get_by_id(req["id"])
        if not e:
            return get_error_data_result(message="Fail to new a chat!")
        
        res = res.to_json()
        
        # Rename keys for response formatting
        renamed_dict = {}
        for key, value in res["prompt_config"].items():
            new_key = key_mapping.get(key, key)
            renamed_dict[new_key] = value
        
        res["prompt"] = renamed_dict
        del res["prompt_config"]
        
        # Add additional parameters to prompt
        new_dict = {
            "similarity_threshold": res["similarity_threshold"],
            "keywords_similarity_weight": 1 - res["vector_similarity_weight"],
            "top_n": res["top_n"],
            "rerank_model": res['rerank_id']
        }
        res["prompt"].update(new_dict)
        
        # Remove keys that are now in prompt
        for key in key_list:
            del res[key]
        
        # Rename LLM fields
        res["llm"] = res.pop("llm_setting")
        res["llm"]["model_name"] = res.pop("llm_id")
        
        # Final response formatting
        del res["kb_ids"]
        res["dataset_ids"] = req["dataset_ids"]
        res["avatar"] = res.pop("icon")
        
        return get_result(data=res)
    
    except Exception as e:
        return get_error_data_result(message=str(e))

@router.put("/{chat_id}")
async def update_chat(
    chat_id: str,
    request: UpdateChatRequest,
    tenant_id: str = Depends(token_required)
):
    """
    Update an existing chat
    """
    try:
        # Check if chat exists and belongs to tenant
        if not DialogService.query(tenant_id=tenant_id, id=chat_id, status=StatusEnum.VALID.value):
            return get_error_data_result(message='You do not own the chat')
        
        # Convert request model to dict for processing
        req = request.dict(exclude_unset=True)
        
        # Handle show_quotation to do_refer conversion
        if "show_quotation" in req:
            req["do_refer"] = req.pop("show_quotation")
        
        # Validate dataset IDs if provided
        ids = req.get("dataset_ids")
        if ids is not None:
            for kb_id in ids:
                kbs = KnowledgebaseService.accessible(kb_id=kb_id, user_id=tenant_id)
                if not kbs:
                    return get_error_data_result(f"You don't own the dataset {kb_id}")
                kbs = KnowledgebaseService.query(id=kb_id)
                kb = kbs[0]
                if kb.chunk_num == 0:
                    return get_error_data_result(f"The dataset {kb_id} doesn't own parsed file")
                
            kbs = KnowledgebaseService.get_by_ids(ids)
            embd_ids = [TenantLLMService.split_model_name_and_factory(kb.embd_id)[0] for kb in kbs]
            embd_count = list(set(embd_ids))
            if len(embd_count) != 1:
                return get_result(
                    message='Datasets use different embedding models."',
                    code=settings.RetCode.AUTHENTICATION_ERROR)
            req["kb_ids"] = ids
        
        # Process LLM settings
        llm = req.get("llm")
        if llm:
            if "model_name" in llm:
                req["llm_id"] = llm.pop("model_name")
                if not TenantLLMService.query(tenant_id=tenant_id, llm_name=req["llm_id"], model_type="chat"):
                    return get_error_data_result(f"`model_name` {req.get('llm_id')} doesn't exist")
            req["llm_setting"] = req.pop("llm")
        
        # Get tenant
        e, tenant = TenantService.get_by_id(tenant_id)
        if not e:
            return get_error_data_result(message="Tenant not found!")
        
        # Process prompt configuration
        prompt = req.get("prompt")
        key_mapping = {
            "parameters": "variables",
            "prologue": "opener",
            "quote": "show_quote",
            "system": "prompt",
            "rerank_id": "rerank_model",
            "vector_similarity_weight": "keywords_similarity_weight"
        }
        
        if prompt:
            for new_key, old_key in key_mapping.items():
                if old_key in prompt:
                    prompt[new_key] = prompt.pop(old_key)
            
            # Extract top-level parameters from prompt
            key_list = ["similarity_threshold", "vector_similarity_weight", "top_n", "rerank_id"]
            for key in key_list:
                if key in prompt:
                    req[key] = prompt.pop(key)
            
            req["prompt_config"] = req.pop("prompt")
        
        # Update chat
        e, res = DialogService.get_by_id(chat_id)
        if not e:
            return get_error_data_result(message="Chat not found!")
        
        # Update fields
        for key, value in req.items():
            if key != "id":
                setattr(res, key, value)
        
        # Save changes
        if not res.save():
            return get_error_data_result(message="Fail to update the chat!")
        
        # Get and format response
        res = res.to_json()
        
        # Rename keys for response formatting
        renamed_dict = {}
        for key, value in res["prompt_config"].items():
            new_key = key_mapping.get(key, key)
            renamed_dict[new_key] = value
        
        res["prompt"] = renamed_dict
        del res["prompt_config"]
        
        # Add additional parameters to prompt
        new_dict = {
            "similarity_threshold": res["similarity_threshold"],
            "keywords_similarity_weight": 1 - res["vector_similarity_weight"],
            "top_n": res["top_n"],
            "rerank_model": res['rerank_id']
        }
        res["prompt"].update(new_dict)
        
        # Remove keys that are now in prompt
        key_list = ["similarity_threshold", "vector_similarity_weight", "top_n", "rerank_id"]
        for key in key_list:
            del res[key]
        
        # Rename LLM fields
        res["llm"] = res.pop("llm_setting")
        res["llm"]["model_name"] = res.pop("llm_id")
        
        # Format dataset_ids
        res["dataset_ids"] = res.pop("kb_ids")
        res["avatar"] = res.pop("icon")
        
        return get_result(data=res)
    
    except Exception as e:
        return get_error_data_result(message=str(e))

@router.delete("")
async def delete_chats(
    request: BulkDeleteRequest,
    tenant_id: str = Depends(token_required)
):
    """
    Delete one or more chats
    """
    try:
        ids = request.ids
        if not ids:
            return get_error_data_result(message="Invalid ids parameter")
        
        # Check for duplicate IDs
        if check_duplicate_ids(ids):
            return get_error_data_result(message="Duplicate ids in the list")
        
        # Verify ownership of all chats
        for id in ids:
            if not DialogService.query(id=id, tenant_id=tenant_id, status=StatusEnum.VALID.value):
                return get_error_data_result(message=f"You do not own the chat {id}")
        
        # Delete chats
        for id in ids:
            try:
                DialogService.delete(id=id)
            except Exception as e:
                return get_error_data_result(message=f"Failed to delete chat {id}: {str(e)}")
        
        return get_result(data={"delete_ids": ids})
    
    except Exception as e:
        return get_error_data_result(message=str(e))

@router.get("")
async def list_chats(tenant_id: str = Depends(token_required)):
    """
    List all chats for the tenant
    """
    try:
        chats = DialogService.query(tenant_id=tenant_id, status=StatusEnum.VALID.value)
        result = []
        
        for chat in chats:
            chat_data = chat.to_json()
            
            # Process prompt config
            key_mapping = {
                "parameters": "variables",
                "prologue": "opener",
                "quote": "show_quote",
                "system": "prompt",
                "rerank_id": "rerank_model",
                "vector_similarity_weight": "keywords_similarity_weight"
            }
            
            renamed_dict = {}
            for key, value in chat_data["prompt_config"].items():
                new_key = key_mapping.get(key, key)
                renamed_dict[new_key] = value
            
            chat_data["prompt"] = renamed_dict
            del chat_data["prompt_config"]
            
            # Add additional parameters to prompt
            new_dict = {
                "similarity_threshold": chat_data["similarity_threshold"],
                "keywords_similarity_weight": 1 - chat_data["vector_similarity_weight"],
                "top_n": chat_data["top_n"],
                "rerank_model": chat_data['rerank_id']
            }
            chat_data["prompt"].update(new_dict)
            
            # Remove keys that are now in prompt
            key_list = ["similarity_threshold", "vector_similarity_weight", "top_n", "rerank_id"]
            for key in key_list:
                del chat_data[key]
            
            # Rename LLM fields
            chat_data["llm"] = chat_data.pop("llm_setting")
            chat_data["llm"]["model_name"] = chat_data.pop("llm_id")
            
            # Format dataset_ids
            chat_data["dataset_ids"] = chat_data.pop("kb_ids")
            chat_data["avatar"] = chat_data.pop("icon")
            
            result.append(chat_data)
        
        return get_result(data=result)
    
    except Exception as e:
        return get_error_data_result(message=str(e)) 