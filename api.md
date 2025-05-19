# RAGFlow API Documentation

This document provides a comprehensive list of all API endpoints available in the RAGFlow application.

## Base URL

All API routes begin with `/v1/` for the specific service endpoints or `/api/v1` for SDK endpoints.

## Authentication

Many endpoints require authentication via a token in the Authorization header.

## API Endpoints

### API/System Endpoints

#### `GET /v1/system/version`
- Gets the version information of the RAGFlow application.

#### `GET /v1/system/status`
- Gets the status of the RAGFlow application.

#### `POST /v1/system/new_token`
- Creates a new API token.

#### `GET /v1/system/token_list`
- Gets a list of all API tokens.

#### `DELETE /v1/system/token/<token>`
- Deletes a specific API token.

#### `GET /v1/system/config`
- Gets the system configuration.

### User Management

#### `POST/GET /v1/user/login`
- Logs a user into the system.

#### `GET /v1/user/login/channels`
- Gets available login channels.

#### `GET /v1/user/login/<channel>`
- Initiates login via a specific channel.

#### `GET /v1/user/oauth/callback/<channel>`
- OAuth callback URL for a specific channel.

#### `GET /v1/user/github_callback`
- GitHub OAuth callback.

#### `GET /v1/user/feishu_callback`
- Feishu OAuth callback.

#### `GET /v1/user/logout`
- Logs out the current user.

#### `POST /v1/user/setting`
- Updates user settings.

#### `GET /v1/user/info`
- Gets information about the current user.

#### `POST /v1/user/register`
- Registers a new user.

#### `GET /v1/user/tenant_info`
- Gets the tenant information for the current user.

#### `POST /v1/user/set_tenant_info`
- Updates tenant information.

### Tenant Management

#### `GET /v1/tenant/<tenant_id>/user/list`
- Gets a list of users for a specific tenant.

#### `POST /v1/tenant/<tenant_id>/user`
- Creates a new user in a specific tenant.

#### `DELETE /v1/tenant/<tenant_id>/user/<user_id>`
- Deletes a user from a specific tenant.

#### `GET /v1/tenant/list`
- Gets a list of all tenants.

#### `PUT /v1/tenant/agree/<tenant_id>`
- Accepts an agreement for a specific tenant.

### Knowledge Base Management

#### `POST /v1/kb/create`
- Creates a new knowledge base.

#### `POST /v1/kb/update`
- Updates an existing knowledge base.

#### `GET /v1/kb/detail`
- Gets details of a knowledge base.

#### `POST /v1/kb/list`
- Lists all knowledge bases.

#### `POST /v1/kb/rm`
- Removes a knowledge base.

#### `GET /v1/kb/<kb_id>/tags`
- Gets tags for a specific knowledge base.

#### `GET /v1/kb/tags`
- Gets all available tags.

#### `POST /v1/kb/<kb_id>/rm_tags`
- Removes tags from a specific knowledge base.

#### `POST /v1/kb/<kb_id>/rename_tag`
- Renames a tag in a specific knowledge base.

#### `GET /v1/kb/<kb_id>/knowledge_graph`
- Gets the knowledge graph for a specific knowledge base.

#### `DELETE /v1/kb/<kb_id>/knowledge_graph`
- Deletes the knowledge graph for a specific knowledge base.

### Document Management

#### `POST /v1/document/upload`
- Uploads a document.

#### `POST /v1/document/web_crawl`
- Crawls a website and adds it as a document.

#### `POST /v1/document/create`
- Creates a new document.

#### `POST /v1/document/list`
- Lists all documents.

#### `POST /v1/document/infos`
- Gets information about specific documents.

#### `GET /v1/document/thumbnails`
- Gets thumbnails for documents.

#### `POST /v1/document/change_status`
- Changes the status of a document.

#### `POST /v1/document/rm`
- Removes a document.

#### `POST /v1/document/run`
- Runs a document processing task.

#### `POST /v1/document/rename`
- Renames a document.

#### `GET /v1/document/get/<doc_id>`
- Gets a specific document by ID.

#### `POST /v1/document/change_parser`
- Changes the parser for a document.

#### `GET /v1/document/image/<image_id>`
- Gets an image from a document.

#### `POST /v1/document/upload_and_parse`
- Uploads and parses a document in one step.

#### `POST /v1/document/parse`
- Parses an existing document.

#### `POST /v1/document/set_meta`
- Sets metadata for a document.

### File Management

#### `POST /v1/file/upload`
- Uploads a file.

#### `POST /v1/file/create`
- Creates a new file.

#### `GET /v1/file/list`
- Lists all files.

#### `GET /v1/file/root_folder`
- Gets the root folder.

#### `GET /v1/file/parent_folder`
- Gets the parent folder of a specified file/folder.

#### `GET /v1/file/all_parent_folder`
- Gets all parent folders of a specified file/folder.

#### `POST /v1/file/rm`
- Removes a file or folder.

#### `POST /v1/file/rename`
- Renames a file or folder.

#### `GET /v1/file/get/<file_id>`
- Gets a specific file by ID.

#### `POST /v1/file/mv`
- Moves a file or folder.

### File to Document Conversion

#### `POST /v1/file2document/convert`
- Converts a file to a document.

#### `POST /v1/file2document/rm`
- Removes a file to document conversion.

### Chunk Management

#### `POST /v1/chunk/list`
- Lists all chunks.

#### `GET /v1/chunk/get`
- Gets a specific chunk.

#### `POST /v1/chunk/set`
- Sets/updates a chunk.

#### `POST /v1/chunk/switch`
- Switches chunk state.

#### `POST /v1/chunk/rm`
- Removes a chunk.

#### `POST /v1/chunk/create`
- Creates a new chunk.

#### `POST /v1/chunk/retrieval_test`
- Tests chunk retrieval.

#### `GET /v1/chunk/knowledge_graph`
- Gets the knowledge graph for a chunk.

### Conversation Management

#### `POST /v1/conversation/set`
- Creates or updates a conversation.

#### `GET /v1/conversation/get`
- Gets a specific conversation.

#### `GET /v1/conversation/getsse/<dialog_id>`
- Gets server-sent events for a conversation.

#### `POST /v1/conversation/rm`
- Removes a conversation.

#### `GET /v1/conversation/list`
- Lists all conversations.

#### `POST /v1/conversation/completion`
- Gets a completion for a conversation.

#### `POST /v1/conversation/tts`
- Converts text to speech in a conversation.

#### `POST /v1/conversation/delete_msg`
- Deletes a message in a conversation.

#### `POST /v1/conversation/thumbup`
- Gives a thumbs up to a message in a conversation.

#### `POST /v1/conversation/ask`
- Asks a question in a conversation.

#### `POST /v1/conversation/mindmap`
- Generates a mind map for a conversation.

#### `POST /v1/conversation/related_questions`
- Gets related questions for a conversation.

### Dialog Management

#### `POST /v1/dialog/set`
- Creates or updates a dialog.

#### `GET /v1/dialog/get`
- Gets a specific dialog.

#### `GET /v1/dialog/list`
- Lists all dialogs.

#### `POST /v1/dialog/rm`
- Removes a dialog.

### Canvas Management

#### `GET /v1/canvas/templates`
- Gets canvas templates.

#### `GET /v1/canvas/list`
- Lists all canvases.

#### `POST /v1/canvas/rm`
- Removes a canvas.

#### `POST /v1/canvas/set`
- Creates or updates a canvas.

#### `GET /v1/canvas/get/<canvas_id>`
- Gets a specific canvas by ID.

#### `GET /v1/canvas/getsse/<canvas_id>`
- Gets server-sent events for a canvas.

#### `POST /v1/canvas/completion`
- Gets a completion for a canvas.

#### `POST /v1/canvas/reset`
- Resets a canvas.

#### `GET /v1/canvas/input_elements`
- Gets input elements for a canvas.

#### `POST /v1/canvas/debug`
- Debugs a canvas.

#### `POST /v1/canvas/test_db_connect`
- Tests database connection for a canvas.

#### `GET /v1/canvas/getlistversion/<canvas_id>`
- Gets list of versions for a canvas.

#### `GET /v1/canvas/getversion/<version_id>`
- Gets a specific version of a canvas.

#### `GET /v1/canvas/listteam`
- Lists teams for canvas.

#### `POST /v1/canvas/setting`
- Updates canvas settings.

### LLM (Language Model) Management

#### `GET /v1/llm/factories`
- Gets available LLM factories.

#### `POST /v1/llm/set_api_key`
- Sets an API key for an LLM.

#### `POST /v1/llm/add_llm`
- Adds a new LLM.

#### `POST /v1/llm/delete_llm`
- Deletes an LLM.

#### `POST /v1/llm/delete_factory`
- Deletes an LLM factory.

#### `GET /v1/llm/my_llms`
- Gets the user's LLMs.

#### `GET /v1/llm/list`
- Lists all available LLMs.

### Plugin Management

#### `GET /v1/plugin/llm_tools`
- Gets available LLM tools.

### Langfuse Integration

#### `POST/PUT /v1/langfuse/api_key`
- Sets Langfuse API key.

#### `GET /v1/langfuse/api_key`
- Gets Langfuse API key.

#### `DELETE /v1/langfuse/api_key`
- Deletes Langfuse API key.

### API/SDK Endpoints

#### `POST /api/v1/new_token`
- Creates a new API token.

#### `GET /api/v1/token_list`
- Gets a list of all API tokens.

#### `POST /api/v1/rm`
- Removes a resource.

#### `GET /api/v1/stats`
- Gets system statistics.

#### `GET /api/v1/new_conversation`
- Creates a new conversation.

#### `POST /api/v1/completion`
- Gets a completion.

#### `GET /api/v1/conversation/<conversation_id>`
- Gets a specific conversation.

#### `POST /api/v1/document/upload`
- Uploads a document.

#### `POST /api/v1/document/upload_and_parse`
- Uploads and parses a document.

#### `POST /api/v1/list_chunks`
- Lists chunks.

#### `GET /api/v1/get_chunk/<chunk_id>`
- Gets a specific chunk.

#### `POST /api/v1/list_kb_docs`
- Lists knowledge base documents.

#### `POST /api/v1/document/infos`
- Gets document information.

#### `DELETE /api/v1/document`
- Deletes a document.

#### `POST /api/v1/completion_aibotk`
- Gets a completion from AIBot-K.

#### `POST /api/v1/retrieval`
- Performs retrieval.

## Future API/SDK Endpoints (Planned)

The following sections describe planned API endpoints that are being developed to extend RAGFlow's capabilities. These endpoints follow RESTful design principles and aim to provide a more comprehensive and intuitive API for knowledge base and document management.

#### `POST /api/v1/kb/create`
- Creates a new knowledge base.
- Parameters:
  - `name` (string, required): Knowledge base name.
  - `description` (string, optional): Description of the knowledge base.
  - `parser_id` (string, required): PDF parser/chunking method (default: "naive" for DeepDoc).
  - `embd_id` (string, optional): Embedding model ID (defaults to tenant's default model if not specified).
  - `parser_config` (object, optional): Contains chunking configuration with properties:
    - `chunk_size` (number, optional): Recommended chunk size (default: 512).
    - `delimiter` (string, optional): Delimiter for text (default: "\n").
    - `pagerank` (number, optional): Page rank value (default: 0).
    - `auto_keyword` (boolean, optional): Enable auto-keyword extraction (default: false).
    - `auto_question` (boolean, optional): Enable auto-question generation (default: false).
    - `excel_to_html` (boolean, optional): Convert Excel to HTML (default: false).
    - `raptor` (object, optional): RAPTOR configuration:
      - `use_raptor` (boolean, optional): Use RAPTOR to enhance retrieval (default: false).
    - `knowledge_graph` (object, optional): Knowledge graph extraction configuration:
      - `use_graph_rag` (boolean, optional): Extract knowledge graph (default: false).
  - `tag_sets` (array, optional): List of tag set knowledge base IDs.
  - `avatar` (string, optional): Base64-encoded image for the knowledge base icon.
  - `permission` (string, optional): Permissions setting ("me" or "team", default: "me").
  - `language` (string, optional): Document language.

#### `PUT /api/v1/kb/update`
- Updates an existing knowledge base.
- Parameters:
  - `kb_id` (string, required): ID of the knowledge base to update.
  - All other parameters are the same as for the create endpoint.
  - Note: Some properties like `parser_id` and `embd_id` might be immutable once documents have been processed.

#### `GET /api/v1/kb/list`
- Returns all knowledge bases and their configuration properties.
- Parameters:
  - `page` (number, optional): Page number for pagination.
  - `page_size` (number, optional): Number of items per page.
  - `keywords` (string, optional): Search keyword for filtering results.
  - `parser_id` (string, optional): Filter by parser/chunking method.
- Returns:
  - `total` (number): Total number of knowledge bases.
  - `kbs` (array): List of knowledge base objects with all properties.

#### `GET /api/v1/kb/detail`
- Gets detailed information about a specific knowledge base.
- Parameters:
  - `kb_id` (string, required): ID of the knowledge base.
- Returns:
  - Detailed knowledge base object with all configuration options.

#### `DELETE /api/v1/kb`
- Deletes a knowledge base.
- Parameters:
  - `kb_id` (string, required): ID of the knowledge base to delete.

#### `POST /api/v1/kb/{kb_id}/documents`
- Uploads one or more documents to the specified knowledge base.
- Parameters:
  - `kb_id` (string, required): The ID of the knowledge base to add documents to.
  - `file` (file or array of files, required): The document file(s) to upload.
- Notes:
  - Documents inherit the current knowledge base's configuration (chunking method, chunk size, delimiter, auto-keyword, auto-question, RAPTOR usage, etc.).
  - **Documents are automatically processed for parsing after upload.** (Use `POST /v1/document/run` with parameters `doc_ids` and `run` for manual control if needed)
- Returns:
  - An array of document objects with their IDs, names, and processing status.

#### `PUT /api/v1/kb/{kb_id}/documents/{doc_id}`
- Updates a specific document's properties.
- Parameters:
  - `kb_id` (string, required): The ID of the knowledge base containing the document.
  - `doc_id` (string, required): The ID of the document to update.
  - `name` (string, optional): New name for the document.
  - `parser_id` (string, optional): Chunking method to use for the document.
  - `parser_config` (object, optional): Configuration for the document parser, including:
    - `chunk_size` (number, optional): Recommended chunk size.
    - `delimiter` (string, optional): Delimiter for text.
    - `auto_keyword` (boolean, optional): Enable auto-keyword extraction.
    - `auto_question` (boolean, optional): Enable auto-question generation.
    - `raptor` (object, optional): RAPTOR configuration.
- Notes:
  - **Document is automatically re-processed after configuration updates.** (Use `POST /v1/document/run` with parameters `doc_ids` and `run` for manual control if needed)

#### `DELETE /api/v1/kb/{kb_id}/documents/{doc_id}`
- Removes a specific document from the knowledge base.
- Parameters:
  - `kb_id` (string, required): The ID of the knowledge base containing the document.
  - `doc_id` (string, required): The ID of the document to delete.

#### `DELETE /api/v1/kb/{kb_id}/documents`
- Removes all documents from the specified knowledge base.
- Parameters:
  - `kb_id` (string, required): The ID of the knowledge base to clear documents from.
  - `ids` (array, optional): If provided, only deletes documents with the specified IDs. If null, deletes all documents.

#### `GET /api/v1/kb/{kb_id}/documents`
- Lists documents within a knowledge base.
- Parameters:
  - `kb_id` (string, required): The ID of the knowledge base.
  - `page` (number, optional): Page number for pagination.
  - `page_size` (number, optional): Number of items per page.
  - `keywords` (string, optional): Search keyword for filtering results.
  - `run_status` (array, optional): Filter by processing status.
  - `types` (array, optional): Filter by document type.
- Returns:
  - `total` (number): Total number of matching documents.
  - `docs` (array): List of document objects with properties:
    - `id` (string): Document ID.
    - `name` (string): Document name.
    - `chunk_count` (number): Number of chunks in the document.
    - `token_count` (number): Number of tokens in the document.
    - `chunk_method` (string): Chunking method used.
    - `run` (string): Processing status.
    - `progress` (number): Processing progress (0-100).
    - `create_time` (number): Creation timestamp.

#### `GET /api/v1/kb/{kb_id}/documents/{doc_id}`
- Gets detailed information about a specific document.
- Parameters:
  - `kb_id` (string, required): The ID of the knowledge base.
  - `doc_id` (string, required): The ID of the document.
- Returns:
  - Detailed document object with all properties and configuration.

## Assistant Management API Endpoints (Planned)

The following endpoints provide management capabilities for RAGFlow chat assistants:

#### `POST /api/v1/assistant`
- Create or update a chat assistant.
- Parameters:
  - `name` (string, required): Assistant name.
  - `description` (string, optional): Description of assistant.
  - `icon` (string, optional): Base64-encoded image for the assistant icon.
  - `kb_ids` (array of strings, required): List of knowledge base IDs to use.
  - `prompt_config` (object, optional): Configuration for the assistant's prompt with properties:
    - `system` (string, required): System prompt for the LLM.
    - `prologue` (string, optional): Opening greeting message (default: "Hi! I am your assistant, can I help you?").
    - `empty_response` (string, optional): Response when no relevant content is found.
    - `quote` (boolean, optional): Whether to show source citations (default: true).
    - `keyword` (boolean, optional): Enable keyword analysis (default: false).
    - `tts` (boolean, optional): Enable text-to-speech (default: false).
    - `refine_multiturn` (boolean, optional): Enable multi-turn query optimization (default: false).
    - `parameters` (array, optional): Variables for prompt template (default: `[{"key": "knowledge", "optional": true}]`).
  - `similarity_threshold` (number, optional): Similarity threshold for retrieval (default: 0.2).
  - `vector_similarity_weight` (number, optional): Weight for keyword similarity (default: 0.7).
  - `top_n` (number, optional): Number of chunks to retrieve (default: 8).
  - `use_kg` (boolean, optional): Use knowledge graph for retrieval (default: false).
  - `reasoning` (boolean, optional): Enable reasoning capability (default: false).
  - `rerank_id` (string, optional): ID of reranking model to use.
  - `llm_id` (string, required): ID of the chat model to use.
  - `llm_setting` (object, optional): LLM configuration with properties:
    - `temperature` (number, optional): Controls randomness of output (default: 0.10).
    - `top_p` (number, optional): Controls diversity of output (default: 0.30).
    - `presence_penalty` (number, optional): Controls repetition (default: 0.40).
    - `frequency_penalty` (number, optional): Controls word frequency (default: 0.70).
    - `max_tokens` (number, optional): Maximum response length (default: 512).
  - `id` (string, optional): If updating an existing assistant, provide the assistant ID.

#### `GET /api/v1/assistant`
- Returns all chat assistants with their configuration properties.
- Parameters:
  - `page` (number, optional): Page number for pagination (default: 1).
  - `page_size` (number, optional): Items per page (default: 30).
  - `orderby` (string, optional): Sort field (create_time or update_time, default: create_time).
  - `desc` (boolean, optional): Sort in descending order (default: true).
  - `name` (string, optional): Filter by assistant name.
  - `id` (string, optional): Filter by assistant ID.

#### `DELETE /api/v1/assistant`
- Delete one or more assistants.
- Parameters:
  - `ids` (array of strings, optional): IDs of assistants to delete. If not provided, deletes all assistants.

#### `POST /api/v1/defaults`
- Set default models for new resources.
- Parameters:
  - `embedding_model` (string, required): Default embedding model for new knowledge bases.
  - `chat_model` (string, required): Default chat model for new assistants.

#### `GET /api/v1/defaults`
- Get current default model settings.
- Returns object with `embedding_model` and `chat_model` properties.

#### `POST /api/v1/assistant/{assistant_id}/set-default`
- Set a chat assistant as the default for user interactions.
- This endpoint designates a specific assistant to serve as the global default on the company page. All regular users will interact with this default assistant when they visit. Admin users with proper authorization can still access and interact with any assistant.
- Parameters:
  - `assistant_id` (string, required): ID of the assistant to set as default.

## Public Chat API and Authentication

RAGFlow's public API includes a simplified chat interface designed for both anonymous users and administrators.

### Authentication Model

- **Admin Users**: Require API tokens with administrative privileges
  - Admin tokens must be included in the `Authorization` header as `Bearer <token>`
  - Admin users have full access to manage knowledge bases, documents, assistants, and configurations
  - Admin users can chat with any assistant by specifying the `assistant_id`

- **Regular Users**: No authentication required
  - Public/anonymous access to the chat endpoint only
  - Automatically interact with the default assistant 
  - Cannot access or modify any configuration or resource management endpoints

### Admin Token Management

Admin tokens provide access to sensitive operations and should be managed securely. These endpoints are not publicly accessible and themselves require administrative authentication.

> **Security Note**: All admin endpoints enforce strict authentication. Requests without a valid admin token will be rejected with a 401 Unauthorized response. Simply knowing the URL path does not grant access to these endpoints.
>
> **Authentication Header**: Admin tokens must be included in the request header as:  
> `Authorization: Bearer <admin_token>`

#### `POST /api/v1/admin/token/create`
- Creates a new admin API token.
- Authentication: Requires existing admin token or system setup credentials in the Authorization header.
- Security: Requests without valid authentication will be rejected.
- Headers:
  - `Authorization` (required): `Bearer <admin_token>` format with a valid admin token.
- Parameters:
  - `name` (string, required): A descriptive name for the token.
  - `expiration` (number, optional): Token validity in days. Default is no expiration.
- Returns:
  - `token` (string): The newly created admin token.
  - `id` (string): Unique identifier for the token.
  - `tenant_id` (string): The tenant ID associated with this token.
  - `create_time` (number): Creation timestamp in milliseconds.
  - `create_date` (string): Formatted creation date.

#### `GET /api/v1/admin/token/list`
- Lists all admin tokens.
- Authentication: Requires existing admin token.
- Returns:
  - Array of token objects (without the actual token values).

#### `DELETE /api/v1/admin/token/{token_id}`
- Revokes a specific admin token.
- Authentication: Requires existing admin token.
- Parameters:
  - `token_id` (string, required): ID of the token to revoke.

#### Initial Setup Token
- During the initial system setup, a one-time setup code is generated.
- This code can be used only once to create the first admin token via a special endpoint.
- After the first admin token is created, all token management must be done using valid admin tokens.

### Chat Endpoint

#### `POST /api/v1/chat`
- Public chat endpoint to interact with RAGFlow assistants.
- Authentication:
  - For admin users: Requires valid admin token in Authorization header
  - For regular users: No authentication required
- Parameters:
  - `question` (string, required): The user's message or question.
  - `session_id` (string, optional): Session identifier for conversation continuity.
  - `assistant_id` (string, optional, admin only): ID of the specific assistant to chat with. Only valid with admin token.
  - `stream` (boolean, optional): Whether to return responses in streaming format. Default: true.
  - `user_id` (string, optional): User identifier for tracking. Only used when creating a new session (no session_id provided).
- Returns:
  - `answer` (string): The assistant's response.
  - `session_id` (string): ID for continuing the conversation.
  - `reference` (object, optional): If citations/sources were found, includes reference information.
  - `id` (string, optional): Message identifier.
  - `audio_binary` (string, optional): Base64-encoded audio if text-to-speech is enabled.

## Note

This document reflects all current API endpoints available in the RAGFlow application. The endpoints are organized by functionality and include HTTP method and route path information. 