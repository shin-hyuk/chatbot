#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import os
import json
import logging
from functools import wraps
from flask import Blueprint, request, Response, jsonify
from flask_login import current_user, login_required
from werkzeug.exceptions import Unauthorized

from api import settings
from api.utils import get_uuid
from api.db import StatusEnum, FileType, ParserType, FileSource
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.document_service import DocumentService, doc_upload_and_parse
from api.db.services.dialog_service import DialogService
from api.db.services.file_service import FileService
from api.db.services.file2document_service import File2DocumentService
from api.db.services.conversation_service import ConversationService
from api.db.services.user_service import TenantService, UserTenantService
from api.db.services.llm_service import TenantLLMService
from api.db.db_models import File
from api.utils.api_utils import get_json_result, get_data_error_result, server_error_response
from api.utils.web_utils import is_valid_url
from api.utils.file_utils import filename_type, thumbnail
from rag.utils.storage_factory import STORAGE_IMPL
from rag.nlp import search

# Create the manager Blueprint for this centralized API
manager = Blueprint('centralized_api', __name__)

# Global variables to track default settings
_default_assistant_id = None
_default_embedding_model = "text-embedding-3-large@OpenAI"
_default_chat_model = None

# =====================
# Authentication helpers
# =====================

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for admin authorization token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Admin authorization required'}), 401
        
        # Extract and validate token
        token = auth_header.split(' ')[1]
        # Simple token validation for demonstration
        # In a real implementation, you would validate this token against your authentication system
        admin_token = os.environ.get('RAGFLOW_ADMIN_TOKEN', 'admin-token')
        if token != admin_token:
            return jsonify({'error': 'Invalid admin token'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

# =====================
# Knowledge Base endpoints
# =====================

@manager.route('/api/knowledgebase', methods=['POST'])
@admin_required
def create_update_knowledge_base():
    """Create or update a knowledge base"""
    req = request.json
    
    # Validation
    if not req.get('name'):
        return get_data_error_result(message="Knowledge base name is required")
    
    # Default values for required parameters
    req.setdefault('parser_id', 'naive')  # Default to 'naive' chunking method
    
    # Default parser config if not provided
    if not req.get('parser_config'):
        req['parser_config'] = {
            'layout_recognize': 'DeepDoc',
            'chunk_token_num': 512,
            'delimiter': '\\n',
            'pagerank': 0,
            'auto_keywords': 0,
            'auto_questions': 0,
            'html4excel': False
        }
    else:
        # Set defaults for missing parser_config fields
        parser_config = req['parser_config']
        parser_config.setdefault('layout_recognize', 'DeepDoc')
        parser_config.setdefault('chunk_token_num', 512)
        parser_config.setdefault('delimiter', '\\n')
        parser_config.setdefault('pagerank', 0)
        parser_config.setdefault('auto_keywords', 0)
        parser_config.setdefault('auto_questions', 0)
        parser_config.setdefault('html4excel', False)
        
        # Optional raptor and graphrag settings
        if 'raptor' not in parser_config:
            parser_config['raptor'] = {'use_raptor': False}
        if 'graphrag' not in parser_config:
            parser_config['graphrag'] = {'use_graphrag': False}
    
    # Set embedding model - use default if not provided
    req.setdefault('embd_id', _default_embedding_model)
    
    # If updating existing knowledge base
    kb_id = req.get('id')
    if kb_id:
        # Check if KB exists
        e, kb = KnowledgebaseService.get_by_id(kb_id)
        if not e:
            return get_data_error_result(message="Knowledge base not found")
        
        # Update the KB
        if not KnowledgebaseService.update_by_id(kb_id, req):
            return get_data_error_result(message="Failed to update knowledge base")
        
        e, updated_kb = KnowledgebaseService.get_by_id(kb_id)
        return get_json_result(data=updated_kb.to_dict())
    
    # Creating new knowledge base
    try:
        # Generate a new UUID for the knowledge base
        req['id'] = get_uuid()
        req['tenant_id'] = current_user.id if hasattr(current_user, 'id') else '1'  # Default tenant if none
        req['created_by'] = current_user.id if hasattr(current_user, 'id') else '1'  # Default user if none
        
        if not KnowledgebaseService.save(**req):
            return get_data_error_result(message="Failed to create knowledge base")
        
        return get_json_result(data={"kb_id": req["id"]})
    except Exception as e:
        return server_error_response(e)

@manager.route('/api/knowledgebase', methods=['GET'])
@admin_required
def get_knowledge_bases():
    """Returns all knowledge bases"""
    try:
        # Get all knowledge bases
        kbs = KnowledgebaseService.query(status=StatusEnum.VALID.value)
        kb_data = [kb.to_dict() for kb in kbs]
        
        return get_json_result(data=kb_data)
    except Exception as e:
        return server_error_response(e)

# =====================
# Document endpoints
# =====================

@manager.route('/api/knowledgebase/<kb_id>/documents', methods=['POST'])
@admin_required
def add_documents(kb_id):
    """Add one or more documents to a knowledge base"""
    if not kb_id:
        return get_json_result(
            data=False, message='Knowledge base ID is required', 
            code=settings.RetCode.ARGUMENT_ERROR)
    
    if 'file' not in request.files:
        return get_json_result(
            data=False, message='No file provided', 
            code=settings.RetCode.ARGUMENT_ERROR)
    
    file_objs = request.files.getlist('file')
    for file_obj in file_objs:
        if file_obj.filename == '':
            return get_json_result(
                data=False, message='Empty filename detected', 
                code=settings.RetCode.ARGUMENT_ERROR)
    
    # Get the knowledge base
    e, kb = KnowledgebaseService.get_by_id(kb_id)
    if not e:
        return get_data_error_result(message="Knowledge base not found")
    
    # Upload documents
    err, files = FileService.upload_document(kb, file_objs, kb.created_by)
    files = [f[0] for f in files]  # Remove the blob
    
    if err:
        return get_json_result(
            data=files, message="\n".join(err), 
            code=settings.RetCode.SERVER_ERROR)
    
    return get_json_result(data=files)

@manager.route('/api/knowledgebase/<kb_id>/documents/<doc_id>', methods=['DELETE'])
@admin_required
def delete_document(kb_id, doc_id):
    """Remove a specific document from a knowledge base"""
    if not kb_id or not doc_id:
        return get_data_error_result(message="Both knowledge base ID and document ID are required")
    
    try:
        # Check if knowledge base exists
        e, kb = KnowledgebaseService.get_by_id(kb_id)
        if not e:
            return get_data_error_result(message="Knowledge base not found")
        
        # Check if document exists
        doc = DocumentService.query(id=doc_id, kb_id=kb_id)
        if not doc:
            return get_data_error_result(message="Document not found in this knowledge base")
        
        # Remove the document
        if not DocumentService.remove_document(doc[0], kb.tenant_id):
            return get_data_error_result(message="Failed to remove document")
        
        # Remove file associations
        f2d = File2DocumentService.get_by_document_id(doc_id)
        if f2d:
            FileService.filter_delete([File.source_type == FileSource.KNOWLEDGEBASE, File.id == f2d[0].file_id])
        File2DocumentService.delete_by_document_id(doc_id)
        
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)

@manager.route('/api/knowledgebase/<kb_id>/documents', methods=['DELETE'])
@admin_required
def delete_all_documents(kb_id):
    """Remove all documents from a knowledge base"""
    if not kb_id:
        return get_data_error_result(message="Knowledge base ID is required")
    
    try:
        # Check if knowledge base exists
        e, kb = KnowledgebaseService.get_by_id(kb_id)
        if not e:
            return get_data_error_result(message="Knowledge base not found")
        
        # Get all documents in the knowledge base
        docs = DocumentService.query(kb_id=kb_id)
        
        # Remove each document
        for doc in docs:
            if not DocumentService.remove_document(doc, kb.tenant_id):
                return get_data_error_result(message=f"Failed to remove document {doc.id}")
            
            # Remove file associations
            f2d = File2DocumentService.get_by_document_id(doc.id)
            if f2d:
                FileService.filter_delete([File.source_type == FileSource.KNOWLEDGEBASE, File.id == f2d[0].file_id])
            File2DocumentService.delete_by_document_id(doc.id)
        
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)

@manager.route('/api/knowledgebase/<kb_id>/documents', methods=['GET'])
@admin_required
def list_documents(kb_id):
    """List all documents in a knowledge base"""
    if not kb_id:
        return get_data_error_result(message="Knowledge base ID is required")
    
    doc_id = request.args.get("doc_id", None)  # Optional filter by document ID
    
    try:
        # Check if knowledge base exists
        e, kb = KnowledgebaseService.get_by_id(kb_id)
        if not e:
            return get_data_error_result(message="Knowledge base not found")
        
        # Get documents
        if doc_id:
            docs = DocumentService.query(kb_id=kb_id, id=doc_id)
        else:
            docs = DocumentService.query(kb_id=kb_id)
        
        # Format document data
        doc_data = []
        for doc in docs:
            doc_dict = doc.to_dict()
            # Add additional properties
            doc_dict['chunk_number'] = DocumentService.get_chunk_count(doc.id)
            doc_dict['parsing_status'] = DocumentService.get_parsing_status(doc.id)
            doc_data.append(doc_dict)
        
        return get_json_result(data=doc_data)
    except Exception as e:
        return server_error_response(e)

@manager.route('/api/knowledgebase/<kb_id>/documents/<doc_id>', methods=['PATCH'])
@admin_required
def update_document(kb_id, doc_id):
    """Update document properties"""
    if not kb_id or not doc_id:
        return get_data_error_result(message="Both knowledge base ID and document ID are required")
    
    req = request.json
    if not req:
        return get_data_error_result(message="No update data provided")
    
    try:
        # Check if knowledge base exists
        e, kb = KnowledgebaseService.get_by_id(kb_id)
        if not e:
            return get_data_error_result(message="Knowledge base not found")
        
        # Check if document exists
        doc = DocumentService.query(id=doc_id, kb_id=kb_id)
        if not doc:
            return get_data_error_result(message="Document not found in this knowledge base")
        
        # Prepare update data
        update_data = {}
        
        # Handle name update
        if 'name' in req:
            update_data['name'] = req['name']
        
        # Handle parser_id update
        if 'parser_id' in req:
            update_data['parser_id'] = req['parser_id']
        
        # Handle parser_config updates
        parser_config = {}
        if doc[0].parser_config:
            parser_config = doc[0].parser_config
        
        if 'parser_config' in req and req['parser_config']:
            pc = req['parser_config']
            if 'chunk_token_num' in pc:
                parser_config['chunk_token_num'] = pc['chunk_token_num']
            if 'delimiter' in pc:
                parser_config['delimiter'] = pc['delimiter']
            if 'auto_keywords' in pc:
                parser_config['auto_keywords'] = pc['auto_keywords']
            if 'auto_questions' in pc:
                parser_config['auto_questions'] = pc['auto_questions']
            if 'raptor' in pc and 'use_raptor' in pc['raptor']:
                if 'raptor' not in parser_config:
                    parser_config['raptor'] = {}
                parser_config['raptor']['use_raptor'] = pc['raptor']['use_raptor']
        
        if parser_config:
            update_data['parser_config'] = parser_config
        
        # Update the document
        if update_data:
            if not DocumentService.update_by_id(doc_id, update_data):
                return get_data_error_result(message="Failed to update document")
            
            # Re-parse the document
            DocumentService.re_parse_document(doc_id)
        
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)

# =====================
# Chat Assistant endpoints
# =====================

@manager.route('/api/assistant', methods=['POST'])
@admin_required
def create_update_assistant():
    """Create or update a chat assistant"""
    req = request.json
    
    # Validation
    if not req.get('name'):
        return get_data_error_result(message="Assistant name is required")
    
    if 'knowledge_bases' not in req or not req['knowledge_bases']:
        return get_data_error_result(message="At least one knowledge base is required")
    
    # Set default values
    req.setdefault('show_quote', True)
    req.setdefault('keyword_analysis', False)
    req.setdefault('text_to_speech', False)
    req.setdefault('similarity_threshold', 0.2)
    req.setdefault('keyword_similarity_weight', 0.7)
    req.setdefault('top_n', 8)
    req.setdefault('multi_turn_optimization', False)
    req.setdefault('use_knowledge_graph', False)
    req.setdefault('reasoning', False)
    
    # Set default system prompt if not provided
    if not req.get('system_prompt'):
        req['system_prompt'] = """You are a helpful assistant that answers based on the knowledge base content. 
If the answer is not in the knowledge base, clearly state that. Consider the chat history context."""
    
    # LLM settings
    req.setdefault('temperature', 0.10)
    req.setdefault('top_p', 0.30)
    req.setdefault('presence_penalty', 0.40)
    req.setdefault('frequency_penalty', 0.70)
    
    # Model settings
    default_model = _default_chat_model or "gpt-4o@OpenAI"
    req.setdefault('model', default_model)
    
    # Variable (knowledge) is enabled by default
    req.setdefault('variable', {"key": "knowledge", "enabled": True})
    
    # Convert to dialog format for RagFlow
    dialog_data = {
        "name": req["name"],
        "description": req.get("description", ""),
        "kb_ids": req["knowledge_bases"],
        "llm_id": req["model"],
        "llm_setting": {
            "temperature": req["temperature"],
            "top_p": req["top_p"],
            "presence_penalty": req["presence_penalty"],
            "frequency_penalty": req["frequency_penalty"]
        },
        "prompt_config": {
            "system": req["system_prompt"],
            "prologue": req.get("opening_greeting", "Hello! How can I help you today?"),
            "empty_response": req.get("empty_response", "Sorry, I couldn't find relevant information in the knowledge base."),
            "parameters": [
                {"key": "knowledge", "optional": not req.get("variable", {}).get("enabled", True)}
            ]
        },
        "top_n": req["top_n"],
        "similarity_threshold": req["similarity_threshold"],
        "vector_similarity_weight": req["keyword_similarity_weight"],
        "icon": ""  # Can be customized if needed
    }
    
    # If updating existing assistant
    assistant_id = req.get('id')
    if assistant_id:
        # Check if assistant exists
        e, assistant = DialogService.get_by_id(assistant_id)
        if not e:
            return get_data_error_result(message="Assistant not found")
        
        # Update the assistant
        if not DialogService.update_by_id(assistant_id, dialog_data):
            return get_data_error_result(message="Failed to update assistant")
        
        e, updated_assistant = DialogService.get_by_id(assistant_id)
        return get_json_result(data=updated_assistant.to_dict())
    
    # Creating new assistant
    try:
        # Generate a new UUID for the assistant
        dialog_data['id'] = get_uuid()
        dialog_data['tenant_id'] = current_user.id if hasattr(current_user, 'id') else '1'  # Default tenant if none
        
        if not DialogService.save(**dialog_data):
            return get_data_error_result(message="Failed to create assistant")
        
        return get_json_result(data={"assistant_id": dialog_data["id"]})
    except Exception as e:
        return server_error_response(e)

@manager.route('/api/assistant', methods=['GET'])
@admin_required
def get_assistants():
    """Returns all chat assistants"""
    try:
        # Get all assistants
        assistants = DialogService.query(status=StatusEnum.VALID.value)
        assistant_data = []
        
        # Format assistant data
        for assistant in assistants:
            assistant_dict = assistant.to_dict()
            # Convert to the expected format
            formatted_assistant = {
                "id": assistant_dict["id"],
                "name": assistant_dict["name"],
                "description": assistant_dict["description"],
                "knowledge_bases": assistant_dict["kb_ids"],
                "system_prompt": assistant_dict["prompt_config"]["system"],
                "opening_greeting": assistant_dict["prompt_config"]["prologue"],
                "empty_response": assistant_dict["prompt_config"].get("empty_response", ""),
                "show_quote": True,  # Default to on
                "keyword_analysis": False,  # Default to off
                "text_to_speech": False,  # Default to off
                "model": assistant_dict["llm_id"],
                "temperature": assistant_dict["llm_setting"].get("temperature", 0.10),
                "top_p": assistant_dict["llm_setting"].get("top_p", 0.30),
                "presence_penalty": assistant_dict["llm_setting"].get("presence_penalty", 0.40),
                "frequency_penalty": assistant_dict["llm_setting"].get("frequency_penalty", 0.70),
                "similarity_threshold": assistant_dict["similarity_threshold"],
                "keyword_similarity_weight": assistant_dict["vector_similarity_weight"],
                "top_n": assistant_dict["top_n"],
                "multi_turn_optimization": False,  # Default to off
                "use_knowledge_graph": False,  # Default to off
                "reasoning": False,  # Default to off
                "variable": {"key": "knowledge", "enabled": True}  # Default to enabled
            }
            assistant_data.append(formatted_assistant)
        
        return get_json_result(data=assistant_data)
    except Exception as e:
        return server_error_response(e)

@manager.route('/api/assistant/<assistant_id>/set-default', methods=['POST'])
@admin_required
def set_default_assistant(assistant_id):
    """Set a chat assistant as the default for all user chat"""
    try:
        # Check if assistant exists
        e, assistant = DialogService.get_by_id(assistant_id)
        if not e:
            return get_data_error_result(message="Assistant not found")
        
        # Set as global default
        global _default_assistant_id
        _default_assistant_id = assistant_id
        
        return get_json_result(data={"default_assistant_id": assistant_id})
    except Exception as e:
        return server_error_response(e)

@manager.route('/api/defaults', methods=['POST'])
@admin_required
def set_defaults():
    """Set the default embedding model and chat model"""
    req = request.json
    
    try:
        global _default_embedding_model, _default_chat_model
        
        if 'embedding_model' in req:
            _default_embedding_model = req['embedding_model']
        
        if 'chat_model' in req:
            _default_chat_model = req['chat_model']
        
        return get_json_result(data={
            "default_embedding_model": _default_embedding_model,
            "default_chat_model": _default_chat_model
        })
    except Exception as e:
        return server_error_response(e)

@manager.route('/api/defaults', methods=['GET'])
@admin_required
def get_defaults():
    """Get the current default embedding model and chat model"""
    try:
        return get_json_result(data={
            "default_embedding_model": _default_embedding_model,
            "default_chat_model": _default_chat_model,
            "default_assistant_id": _default_assistant_id
        })
    except Exception as e:
        return server_error_response(e)

# =====================
# Chat endpoint
# =====================

@manager.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint for both users and admins"""
    req = request.json
    
    if not req.get('message'):
        return get_data_error_result(message="Message is required")
    
    # Determine if the request is from an admin
    is_admin = False
    auth_header = request.headers.get('Authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        admin_token = os.environ.get('RAGFLOW_ADMIN_TOKEN', 'admin-token')
        is_admin = (token == admin_token)
    
    # Choose the assistant
    assistant_id = None
    
    if is_admin and 'assistant_id' in req:
        # Admin can specify any assistant
        assistant_id = req['assistant_id']
    else:
        # Users must use the default assistant
        if not _default_assistant_id:
            return get_data_error_result(message="No default assistant has been set")
        assistant_id = _default_assistant_id
    
    # Check if assistant exists
    e, assistant = DialogService.get_by_id(assistant_id)
    if not e:
        return get_data_error_result(message="Assistant not found")
    
    # Session handling
    session_id = req.get('session_id')
    if session_id:
        # Check if session exists
        e, conversation = ConversationService.get_by_id(session_id)
        if not e:
            # Create new session if it doesn't exist
            session_id = get_uuid()
            conversation = {
                "id": session_id,
                "dialog_id": assistant_id,
                "name": "Chat session",
                "message": [{"role": "assistant", "content": assistant.prompt_config["prologue"]}]
            }
            ConversationService.save(**conversation)
    else:
        # Create new session
        session_id = get_uuid()
        conversation = {
            "id": session_id,
            "dialog_id": assistant_id,
            "name": "Chat session",
            "message": [{"role": "assistant", "content": assistant.prompt_config["prologue"]}]
        }
        ConversationService.save(**conversation)
    
    # Prepare the message
    user_message = {
        "role": "user",
        "content": req['message']
    }
    
    # Get existing conversation or create new one
    e, conv = ConversationService.get_by_id(session_id)
    if e:
        messages = conv.message if conv.message else []
        messages.append(user_message)
        
        # Update conversation with new message
        ConversationService.update_by_id(session_id, {"message": messages})
        
        # Process the chat request using Ragflow's dialog service
        try:
            # Use the proper tenant ID
            tenant_id = assistant.tenant_id
            
            # Get answer from LLM
            from api.db.services.dialog_service import chat as ragflow_chat
            
            result = ragflow_chat(session_id)
            
            # Format response
            response = {
                "assistant_id": assistant_id,
                "session_id": session_id,
                "message": result.get('content', "I'm sorry, I couldn't process your request."),
                "references": result.get('reference', [])
            }
            
            return get_json_result(data=response)
        except Exception as e:
            logging.error(f"Error in chat processing: {str(e)}")
            return get_data_error_result(message="Failed to process chat message")
    else:
        return get_data_error_result(message="Failed to create or retrieve conversation")

# Register the blueprint
app.register_blueprint(manager, url_prefix='') 