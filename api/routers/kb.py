from typing import Optional, List, Dict, Any, Union
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Request, status, File, UploadFile, Form, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator, root_validator

from api import settings
from api.constants import API_VERSION
from api.db import StatusEnum
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.document_service import DocumentService
from api.utils import get_uuid, current_timestamp, get_format_time
from api.utils.fastapi_utils import token_required, get_json_result, get_error_data_result

# Pydantic models for request/response validation
class RaptorConfig(BaseModel):
    use_raptor: bool = False

class KnowledgeGraphConfig(BaseModel):
    use_graph_rag: bool = False

class ParserConfig(BaseModel):
    chunk_size: Optional[int] = 512
    delimiter: Optional[str] = "\n"
    pagerank: Optional[float] = 0
    auto_keyword: Optional[bool] = False
    auto_question: Optional[bool] = False
    excel_to_html: Optional[bool] = False
    raptor: Optional[RaptorConfig] = Field(default_factory=RaptorConfig)
    knowledge_graph: Optional[KnowledgeGraphConfig] = Field(default_factory=KnowledgeGraphConfig)
    
    class Config:
        extra = "allow"

class PermissionType(str, Enum):
    me = "me"
    team = "team"

class KnowledgeBaseCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    parser_id: str  # PDF parser/chunking method
    embd_id: Optional[str] = None
    parser_config: Optional[ParserConfig] = Field(default_factory=ParserConfig)
    tag_sets: Optional[List[str]] = []
    avatar: Optional[str] = None
    permission: Optional[PermissionType] = PermissionType.me
    language: Optional[str] = None
    
    class Config:
        extra = "allow"

class KnowledgeBaseUpdate(BaseModel):
    kb_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    parser_id: Optional[str] = None
    embd_id: Optional[str] = None
    parser_config: Optional[ParserConfig] = None
    tag_sets: Optional[List[str]] = None
    avatar: Optional[str] = None
    permission: Optional[PermissionType] = None
    language: Optional[str] = None
    
    class Config:
        extra = "allow"

class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    parser_id: Optional[str] = None
    parser_config: Optional[ParserConfig] = None
    
    class Config:
        extra = "allow"

class KnowledgeBaseListParams(BaseModel):
    page: Optional[int] = 1
    page_size: Optional[int] = 30
    keywords: Optional[str] = None
    parser_id: Optional[str] = None

class DocumentListParams(BaseModel):
    page: Optional[int] = 1
    page_size: Optional[int] = 30
    keywords: Optional[str] = None
    run_status: Optional[List[str]] = None
    types: Optional[List[str]] = None

router = APIRouter(
    prefix=f"/api/{API_VERSION}/kb",
    tags=["Knowledge Base Management"]
)

# Knowledge Base Management Endpoints
@router.post("", response_model=Dict[str, Any])
async def create_knowledge_base(
    kb_data: KnowledgeBaseCreate,
    tenant_id: str = Depends(token_required)
):
    """
    Creates a new knowledge base.
    """
    try:
        # Convert request model to dict
        kb_dict = kb_data.dict(exclude_unset=True)
        
        # Set ID and tenant ID
        kb_dict["id"] = get_uuid()
        kb_dict["tenant_id"] = tenant_id
        kb_dict["create_time"] = current_timestamp()
        kb_dict["create_date"] = get_format_time()
        kb_dict["update_time"] = current_timestamp()
        kb_dict["update_date"] = get_format_time()
        kb_dict["chunk_num"] = 0
        kb_dict["status"] = StatusEnum.VALID.value
        
        # Use tenant's default embedding model if not specified
        if not kb_dict.get("embd_id"):
            from api.db.services.user_service import TenantService
            tenant = TenantService.query(id=tenant_id, status=StatusEnum.VALID.value)
            if tenant:
                kb_dict["embd_id"] = tenant[0].embd_id
        
        # Save knowledge base
        if not KnowledgebaseService.save(**kb_dict):
            return get_error_data_result(
                message="Failed to create knowledge base",
                code=settings.RetCode.SERVER_ERROR
            )
            
        # Get the created knowledge base
        kb = KnowledgebaseService.query(id=kb_dict["id"])
        if not kb:
            return get_error_data_result(
                message="Knowledge base created but could not be retrieved",
                code=settings.RetCode.SERVER_ERROR
            )
            
        return get_json_result(kb[0].to_json())
        
    except Exception as e:
        return get_error_data_result(
            message=f"Error creating knowledge base: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@router.put("", response_model=Dict[str, Any])
async def update_knowledge_base(
    kb_data: KnowledgeBaseUpdate,
    tenant_id: str = Depends(token_required)
):
    """
    Updates an existing knowledge base.
    """
    try:
        # Check if knowledge base exists and belongs to tenant
        kb_id = kb_data.kb_id
        kb = KnowledgebaseService.accessible(kb_id=kb_id, user_id=tenant_id)
        if not kb:
            return get_error_data_result(
                message=f"Knowledge base {kb_id} not found or not accessible",
                code=settings.RetCode.PARAM_ERROR
            )
            
        # Convert request model to dict
        update_dict = kb_data.dict(exclude={"kb_id"}, exclude_unset=True)
        update_dict["update_time"] = current_timestamp()
        update_dict["update_date"] = get_format_time()
        
        # Update knowledge base
        kb_obj = kb[0]
        for key, value in update_dict.items():
            setattr(kb_obj, key, value)
            
        if not kb_obj.save():
            return get_error_data_result(
                message="Failed to update knowledge base",
                code=settings.RetCode.SERVER_ERROR
            )
            
        return get_json_result(kb_obj.to_json())
        
    except Exception as e:
        return get_error_data_result(
            message=f"Error updating knowledge base: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@router.get("/list", response_model=Dict[str, Any])
async def list_knowledge_bases(
    page: int = 1,
    page_size: int = 30,
    keywords: Optional[str] = None,
    parser_id: Optional[str] = None,
    tenant_id: str = Depends(token_required)
):
    """
    Returns all knowledge bases and their configuration properties.
    """
    try:
        # Build filter conditions
        filters = {"tenant_id": tenant_id, "status": StatusEnum.VALID.value}
        if parser_id:
            filters["parser_id"] = parser_id
            
        # Get total count and paginated knowledge bases
        total = KnowledgebaseService.count(filters, keywords)
        kbs = KnowledgebaseService.query_page(
            page=page,
            page_size=page_size,
            filters=filters,
            keywords=keywords
        )
        
        # Format knowledge bases for response
        kb_list = [kb.to_json() for kb in kbs]
        
        return get_json_result({
            "total": total,
            "kbs": kb_list
        })
        
    except Exception as e:
        return get_error_data_result(
            message=f"Error listing knowledge bases: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@router.get("/detail", response_model=Dict[str, Any])
async def get_knowledge_base_detail(
    kb_id: str,
    tenant_id: str = Depends(token_required)
):
    """
    Gets detailed information about a specific knowledge base.
    """
    try:
        # Check if knowledge base exists and belongs to tenant
        kb = KnowledgebaseService.accessible(kb_id=kb_id, user_id=tenant_id)
        if not kb:
            return get_error_data_result(
                message=f"Knowledge base {kb_id} not found or not accessible",
                code=settings.RetCode.PARAM_ERROR
            )
            
        return get_json_result(kb[0].to_json())
        
    except Exception as e:
        return get_error_data_result(
            message=f"Error getting knowledge base detail: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@router.delete("", response_model=Dict[str, Any])
async def delete_knowledge_base(
    kb_id: str,
    tenant_id: str = Depends(token_required)
):
    """
    Deletes a knowledge base.
    """
    try:
        # Check if knowledge base exists and belongs to tenant
        kb = KnowledgebaseService.accessible(kb_id=kb_id, user_id=tenant_id)
        if not kb:
            return get_error_data_result(
                message=f"Knowledge base {kb_id} not found or not accessible",
                code=settings.RetCode.PARAM_ERROR
            )
            
        # Delete knowledge base
        if not KnowledgebaseService.delete(id=kb_id):
            return get_error_data_result(
                message=f"Failed to delete knowledge base {kb_id}",
                code=settings.RetCode.SERVER_ERROR
            )
            
        # Delete all documents in this knowledge base
        DocumentService.delete_by_kb(kb_id)
            
        return get_json_result({"id": kb_id, "deleted": True})
        
    except Exception as e:
        return get_error_data_result(
            message=f"Error deleting knowledge base: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

# Document Management Endpoints
@router.post("/{kb_id}/documents", response_model=Dict[str, Any])
async def upload_documents(
    kb_id: str,
    files: List[UploadFile] = File(...),
    tenant_id: str = Depends(token_required)
):
    """
    Uploads one or more documents to the specified knowledge base.
    """
    try:
        # Check if knowledge base exists and belongs to tenant
        kb = KnowledgebaseService.accessible(kb_id=kb_id, user_id=tenant_id)
        if not kb:
            return get_error_data_result(
                message=f"Knowledge base {kb_id} not found or not accessible",
                code=settings.RetCode.PARAM_ERROR
            )
            
        # Process each file
        doc_ids = []
        doc_results = []
        
        for file in files:
            # Read file content
            file_content = await file.read()
            
            # Create document record
            doc_id = get_uuid()
            doc_data = {
                "id": doc_id,
                "kb_id": kb_id,
                "name": file.filename,
                "parser_id": kb[0].parser_id,
                "parser_config": kb[0].parser_config,
                "create_time": current_timestamp(),
                "create_date": get_format_time(),
                "update_time": current_timestamp(),
                "update_date": get_format_time(),
                "status": StatusEnum.VALID.value,
                "run": "todo",
                "progress": 0
            }
            
            # Save document metadata
            success = DocumentService.save(**doc_data)
            if not success:
                return get_error_data_result(
                    message=f"Failed to save document {file.filename}",
                    code=settings.RetCode.SERVER_ERROR
                )
                
            # Save file content
            success = DocumentService.save_file(doc_id, file.filename, file_content)
            if not success:
                DocumentService.delete(id=doc_id)
                return get_error_data_result(
                    message=f"Failed to save file content for {file.filename}",
                    code=settings.RetCode.SERVER_ERROR
                )
                
            doc_ids.append(doc_id)
            doc_results.append({
                "id": doc_id,
                "name": file.filename,
                "status": "todo"
            })
            
        # Start processing documents
        if doc_ids:
            DocumentService.run_documents(doc_ids, "run")
            
        return get_json_result(doc_results)
        
    except Exception as e:
        return get_error_data_result(
            message=f"Error uploading documents: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@router.put("/{kb_id}/documents/{doc_id}", response_model=Dict[str, Any])
async def update_document(
    kb_id: str,
    doc_id: str,
    doc_data: DocumentUpdate,
    tenant_id: str = Depends(token_required)
):
    """
    Updates a specific document's properties.
    """
    try:
        # Check if knowledge base exists and belongs to tenant
        kb = KnowledgebaseService.accessible(kb_id=kb_id, user_id=tenant_id)
        if not kb:
            return get_error_data_result(
                message=f"Knowledge base {kb_id} not found or not accessible",
                code=settings.RetCode.PARAM_ERROR
            )
            
        # Check if document exists and belongs to this knowledge base
        doc = DocumentService.query(id=doc_id, kb_id=kb_id, status=StatusEnum.VALID.value)
        if not doc:
            return get_error_data_result(
                message=f"Document {doc_id} not found in knowledge base {kb_id}",
                code=settings.RetCode.PARAM_ERROR
            )
            
        # Update document
        update_dict = doc_data.dict(exclude_unset=True)
        update_dict["update_time"] = current_timestamp()
        update_dict["update_date"] = get_format_time()
        
        doc_obj = doc[0]
        for key, value in update_dict.items():
            setattr(doc_obj, key, value)
            
        if not doc_obj.save():
            return get_error_data_result(
                message="Failed to update document",
                code=settings.RetCode.SERVER_ERROR
            )
            
        # Re-process document if parser configuration changed
        if "parser_id" in update_dict or "parser_config" in update_dict:
            DocumentService.run_documents([doc_id], "run")
            
        return get_json_result(doc_obj.to_json())
        
    except Exception as e:
        return get_error_data_result(
            message=f"Error updating document: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@router.delete("/{kb_id}/documents/{doc_id}", response_model=Dict[str, Any])
async def delete_document(
    kb_id: str,
    doc_id: str,
    tenant_id: str = Depends(token_required)
):
    """
    Removes a specific document from the knowledge base.
    """
    try:
        # Check if knowledge base exists and belongs to tenant
        kb = KnowledgebaseService.accessible(kb_id=kb_id, user_id=tenant_id)
        if not kb:
            return get_error_data_result(
                message=f"Knowledge base {kb_id} not found or not accessible",
                code=settings.RetCode.PARAM_ERROR
            )
            
        # Check if document exists and belongs to this knowledge base
        doc = DocumentService.query(id=doc_id, kb_id=kb_id, status=StatusEnum.VALID.value)
        if not doc:
            return get_error_data_result(
                message=f"Document {doc_id} not found in knowledge base {kb_id}",
                code=settings.RetCode.PARAM_ERROR
            )
            
        # Delete document
        if not DocumentService.delete(id=doc_id):
            return get_error_data_result(
                message=f"Failed to delete document {doc_id}",
                code=settings.RetCode.SERVER_ERROR
            )
            
        return get_json_result({"id": doc_id, "deleted": True})
        
    except Exception as e:
        return get_error_data_result(
            message=f"Error deleting document: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@router.delete("/{kb_id}/documents", response_model=Dict[str, Any])
async def delete_documents(
    kb_id: str,
    ids: Optional[List[str]] = None,
    tenant_id: str = Depends(token_required)
):
    """
    Removes all documents or specified documents from the knowledge base.
    """
    try:
        # Check if knowledge base exists and belongs to tenant
        kb = KnowledgebaseService.accessible(kb_id=kb_id, user_id=tenant_id)
        if not kb:
            return get_error_data_result(
                message=f"Knowledge base {kb_id} not found or not accessible",
                code=settings.RetCode.PARAM_ERROR
            )
            
        deleted_ids = []
        
        if ids:
            # Delete specific documents
            for doc_id in ids:
                doc = DocumentService.query(id=doc_id, kb_id=kb_id, status=StatusEnum.VALID.value)
                if doc and DocumentService.delete(id=doc_id):
                    deleted_ids.append(doc_id)
        else:
            # Delete all documents in this knowledge base
            docs = DocumentService.query(kb_id=kb_id, status=StatusEnum.VALID.value)
            for doc in docs:
                if DocumentService.delete(id=doc.id):
                    deleted_ids.append(doc.id)
                    
        return get_json_result({"deleted_ids": deleted_ids})
        
    except Exception as e:
        return get_error_data_result(
            message=f"Error deleting documents: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@router.get("/{kb_id}/documents", response_model=Dict[str, Any])
async def list_documents(
    kb_id: str,
    page: int = 1,
    page_size: int = 30,
    keywords: Optional[str] = None,
    run_status: Optional[List[str]] = Query(None),
    types: Optional[List[str]] = Query(None),
    tenant_id: str = Depends(token_required)
):
    """
    Lists documents within a knowledge base.
    """
    try:
        # Check if knowledge base exists and belongs to tenant
        kb = KnowledgebaseService.accessible(kb_id=kb_id, user_id=tenant_id)
        if not kb:
            return get_error_data_result(
                message=f"Knowledge base {kb_id} not found or not accessible",
                code=settings.RetCode.PARAM_ERROR
            )
            
        # Build filter conditions
        filters = {"kb_id": kb_id, "status": StatusEnum.VALID.value}
        if run_status:
            filters["run"] = run_status
        if types:
            filters["type"] = types
            
        # Get total count and paginated documents
        total = DocumentService.count(filters, keywords)
        docs = DocumentService.query_page(
            page=page,
            page_size=page_size,
            filters=filters,
            keywords=keywords
        )
        
        # Format documents for response
        doc_list = []
        for doc in docs:
            doc_data = {
                "id": doc.id,
                "name": doc.name,
                "chunk_count": doc.chunk_count or 0,
                "token_count": doc.token_count or 0,
                "chunk_method": doc.parser_id,
                "run": doc.run,
                "progress": doc.progress or 0,
                "create_time": doc.create_time
            }
            doc_list.append(doc_data)
            
        return get_json_result({
            "total": total,
            "docs": doc_list
        })
        
    except Exception as e:
        return get_error_data_result(
            message=f"Error listing documents: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        )

@router.get("/{kb_id}/documents/{doc_id}", response_model=Dict[str, Any])
async def get_document_detail(
    kb_id: str,
    doc_id: str,
    tenant_id: str = Depends(token_required)
):
    """
    Gets detailed information about a specific document.
    """
    try:
        # Check if knowledge base exists and belongs to tenant
        kb = KnowledgebaseService.accessible(kb_id=kb_id, user_id=tenant_id)
        if not kb:
            return get_error_data_result(
                message=f"Knowledge base {kb_id} not found or not accessible",
                code=settings.RetCode.PARAM_ERROR
            )
            
        # Check if document exists and belongs to this knowledge base
        doc = DocumentService.query(id=doc_id, kb_id=kb_id, status=StatusEnum.VALID.value)
        if not doc:
            return get_error_data_result(
                message=f"Document {doc_id} not found in knowledge base {kb_id}",
                code=settings.RetCode.PARAM_ERROR
            )
            
        return get_json_result(doc[0].to_json())
        
    except Exception as e:
        return get_error_data_result(
            message=f"Error getting document detail: {str(e)}",
            code=settings.RetCode.EXCEPTION_ERROR
        ) 