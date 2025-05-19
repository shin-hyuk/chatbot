from typing import List, Dict, Any, Optional, Union
import time
import json
import re
import tiktoken
from fastapi import APIRouter, Depends, Request, Body, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator

from api import settings
from api.constants import API_VERSION
from api.db import StatusEnum
from api.db.services.dialog_service import DialogService
from api.db.services.canvas_service import completionOpenAI
from api.db.services.user_service import UserService
from api.utils.fastapi_utils import token_required, get_error_response, get_success_response

router = APIRouter(
    prefix=f"/api/{API_VERSION}/agents_openai",
    tags=["Public Chat API"]
)

class Message(BaseModel):
    role: str
    content: str

class CompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: bool = True
    id: Optional[str] = None

@router.post("/{agent_id}/chat/completions")
async def agents_completion_openai_compatibility(
    agent_id: str,
    request: CompletionRequest,
    tenant_id: str = Depends(token_required)
):
    """
    OpenAI-compatible chat completion API that simulates the behavior of OpenAI's completions endpoint.
    
    This endpoint allows users to interact with a model and receive responses based on a series of historical messages.
    If `stream` is set to True (by default), the response will be streamed in chunks, mimicking the OpenAI-style API.
    If `stream` is set to False explicitly, the response will be returned in a single complete answer.
    
    Parameters:
    - agent_id: The ID of the agent to use for generating completions
    - model: The model name (any value can be used, as it's handled by the server)
    - messages: A list of message objects with role and content
    - stream: Whether to stream the response (default: True)
    - id: Optional session ID
    
    Returns:
    - If stream=True: A streaming response in OpenAI format
    - If stream=False: A complete response object in OpenAI format
    """
    
    # Extract request data
    tiktokenenc = tiktoken.get_encoding("cl100k_base")
    messages = request.messages
    
    if not messages:
        return get_error_response("You must provide at least one message.")
    
    # Check if user owns the agent
    from api.db.services.canvas_service import UserCanvasService
    if not UserCanvasService.query(user_id=tenant_id, id=agent_id):
        return get_error_response(f"You don't own the agent {agent_id}")
    
    # Filter messages to only include user and assistant roles
    filtered_messages = [m for m in messages if m.role in ["user", "assistant"]]
    prompt_tokens = sum(len(tiktokenenc.encode(m.content)) for m in filtered_messages)
    
    if not filtered_messages:
        error_msg = "No valid messages found (user or assistant)."
        return get_success_response(
            data={
                "id": agent_id,
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "message": {"role": "assistant", "content": error_msg},
                    "finish_reason": "stop",
                    "index": 0
                }],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": len(tiktokenenc.encode(error_msg)),
                    "total_tokens": prompt_tokens + len(tiktokenenc.encode(error_msg))
                }
            }
        )
    
    # Get the last user message as the question
    question = next((m.content for m in reversed(messages) if m.role == "user"), "")
    
    # Handle streaming response
    if request.stream:
        return StreamingResponse(
            completionOpenAI(tenant_id, agent_id, question, session_id=request.id, stream=True),
            media_type="text/event-stream"
        )
    else:
        # For non-streaming, return the response directly
        response = next(completionOpenAI(tenant_id, agent_id, question, session_id=request.id, stream=False))
        return response 