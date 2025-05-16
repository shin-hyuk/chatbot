# Centralized API for RagFlow

This centralized API provides a streamlined interface for managing RagFlow knowledge bases, documents, and chat assistants.

## Authentication

The API uses token-based authentication with two roles:

- **Admin**: Can access all endpoints with a Bearer token
  - Set the admin token as an environment variable: `RAGFLOW_ADMIN_TOKEN`
  - Include the token in requests: `Authorization: Bearer <token>`
  - Example: `Authorization: Bearer admin-token`

- **User/Client**: Only has access to the chat endpoint with the default assistant
  - No authentication required

## Endpoints

### Knowledge Base Management (Admin Only)

#### Create or Update Knowledge Base
- **POST /api/knowledgebase**
- Required parameters:
  - `name` (string): Knowledge base name
- Optional parameters:
  - `description` (string): Description
  - `parser_id` (string): Chunk method (default: "naive")
  - `parser_config` (object): Parsing configuration
    - `layout_recognize` (string, default: "DeepDoc")
    - `chunk_token_num` (number, default: 512)
    - `delimiter` (string, default: "\\n")
    - `pagerank` (number, default: 0)
    - `auto_keywords` (number, default: 0)
    - `auto_questions` (number, default: 0)
    - `html4excel` (boolean, default: false)
    - `raptor.use_raptor` (boolean, default: false)
    - `graphrag.use_graphrag` (boolean, default: false)
  - `embd_id` (string): Embedding model (default: "text-embedding-3-large@OpenAI")
  - `id` (string): Required when updating an existing knowledge base

#### List Knowledge Bases
- **GET /api/knowledgebase**
- Returns all knowledge bases with their configuration

### Document Management (Admin Only)

#### Upload Documents
- **POST /api/knowledgebase/{kb_id}/documents**
- Form data:
  - `file` (file, multiple): Document files to upload

#### Delete Document
- **DELETE /api/knowledgebase/{kb_id}/documents/{doc_id}**
- Path parameters:
  - `kb_id`: Knowledge base ID
  - `doc_id`: Document ID

#### Delete All Documents
- **DELETE /api/knowledgebase/{kb_id}/documents**
- Path parameters:
  - `kb_id`: Knowledge base ID

#### List Documents
- **GET /api/knowledgebase/{kb_id}/documents**
- Path parameters:
  - `kb_id`: Knowledge base ID
- Query parameters (optional):
  - `doc_id`: Filter by document ID

#### Update Document
- **PATCH /api/knowledgebase/{kb_id}/documents/{doc_id}**
- Path parameters:
  - `kb_id`: Knowledge base ID
  - `doc_id`: Document ID
- Request body (all optional):
  - `name` (string): New document name
  - `parser_id` (string): New chunk method
  - `parser_config` (object): Parsing configuration updates
    - `chunk_token_num` (number): Chunk size
    - `delimiter` (string): Delimiter for text
    - `auto_keywords` (number): Auto-keyword setting
    - `auto_questions` (number): Auto-question setting
    - `raptor.use_raptor` (boolean): Whether to use RAPTOR

### Chat Assistant Management (Admin Only)

#### Create or Update Assistant
- **POST /api/assistant**
- Required parameters:
  - `name` (string): Assistant name
  - `knowledge_bases` (array): Array of knowledge base IDs
  - `system_prompt` (string): System prompt
- Optional parameters:
  - `description` (string): Description
  - `empty_response` (string): Message when no answer is found
  - `opening_greeting` (string): Initial greeting message
  - `show_quote` (boolean, default: true)
  - `keyword_analysis` (boolean, default: false)
  - `text_to_speech` (boolean, default: false)
  - `tavily_api_key` (string)
  - `similarity_threshold` (number, default: 0.2)
  - `keyword_similarity_weight` (number, default: 0.7)
  - `top_n` (number, default: 8)
  - `multi_turn_optimization` (boolean, default: false)
  - `use_knowledge_graph` (boolean, default: false)
  - `reasoning` (boolean, default: false)
  - `rerank_model` (string)
  - `variable` (object, default: `{key: "knowledge", enabled: true}`)
  - `model` (string): Chat model
  - `temperature` (number, default: 0.10)
  - `top_p` (number, default: 0.30)
  - `presence_penalty` (number, default: 0.40)
  - `frequency_penalty` (number, default: 0.70)
  - `id` (string): Required when updating an existing assistant

#### List Assistants
- **GET /api/assistant**
- Returns all assistants with their configuration

#### Set Default Assistant
- **POST /api/assistant/{assistant_id}/set-default**
- Path parameters:
  - `assistant_id`: Assistant ID to set as default

### Default Settings (Admin Only)

#### Set Default Models
- **POST /api/defaults**
- Request body (all optional):
  - `embedding_model` (string): Default embedding model
  - `chat_model` (string): Default chat model

#### Get Default Settings
- **GET /api/defaults**
- Returns current default settings

### Chat (User & Admin)

#### Chat with Assistant
- **POST /api/chat**
- Request body:
  - `message` (string, required): User message
  - `session_id` (string, optional): Session ID for chat continuity
  - `assistant_id` (string, optional, admin only): ID of assistant to use
- Returns:
  - Assistant's response
  - References used in the response
  - Session ID for continued conversation

## Usage Examples

### Admin: Create a Knowledge Base

```bash
curl -X POST http://localhost:8000/api/knowledgebase \
  -H "Authorization: Bearer admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Product Documentation",
    "description": "Knowledge base for product documentation",
    "parser_id": "naive",
    "parser_config": {
      "chunk_token_num": 500,
      "delimiter": "\\n"
    },
    "embd_id": "text-embedding-3-large@OpenAI"
  }'
```

### Admin: Upload a Document

```bash
curl -X POST http://localhost:8000/api/knowledgebase/{kb_id}/documents \
  -H "Authorization: Bearer admin-token" \
  -F "file=@/path/to/document.pdf"
```

### Admin: Create a Chat Assistant

```bash
curl -X POST http://localhost:8000/api/assistant \
  -H "Authorization: Bearer admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Product Support Assistant",
    "description": "Helps with product support questions",
    "knowledge_bases": ["kb_id_1", "kb_id_2"],
    "system_prompt": "You are a helpful product support assistant. Use the knowledge base to answer questions accurately.",
    "opening_greeting": "Hello! How can I help with your product questions today?",
    "model": "gpt-4o@OpenAI",
    "temperature": 0.1
  }'
```

### Admin: Set Default Assistant

```bash
curl -X POST http://localhost:8000/api/assistant/{assistant_id}/set-default \
  -H "Authorization: Bearer admin-token"
```

### User: Chat with Default Assistant

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I reset my password?"
  }'
```

### Admin: Chat with Specific Assistant

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I reset my password?",
    "assistant_id": "specific_assistant_id"
  }'
```

## Notes

- This API uses RagFlow's core services but provides a centralized interface with strict permission separation.
- The API maintains all of RagFlow's functionality while providing a simplified interface.
- For security, set the `RAGFLOW_ADMIN_TOKEN` environment variable to a strong, unique value. 