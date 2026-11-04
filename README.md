# ContextAI — Stateful LLM Chatbot with Persistent Memory

ContextAI is a production-grade, stateful multi-turn conversational AI backend built with **FastAPI**, **OpenAI Responses API** (using the official `openai` SDK with `AsyncOpenAI`), and **SQLite / Neon PostgreSQL with SQLAlchemy 2.x**.

It solves a fundamental problem in real-world LLM applications: maintaining conversational continuity and persistent long-term memory across server restarts, while dynamically managing context-window boundaries through rolling conversation summarization.

> **Internship Assignment**: LLM API Integration (AI-1)  
> **Repository**: [https://github.com/bvr4j/context-ai-chatbot](https://github.com/bvr4j/context-ai-chatbot)

---

## 1. System Architecture

```mermaid
flowchart TD
    Client["Client / Frontend UI\n(React / Vite / HTTP)"] -->|"POST /api/chat\nGET /api/conversations"| FastAPI["FastAPI Application\n(app/main.py)"]
    
    subgraph Backend ["ContextAI Backend"]
        FastAPI -->|"Dependency Injection"| Router["Chat Router\n(app/routes/chat.py)"]
        Router -->|"Input Validation"| Pydantic["Pydantic Schemas\n(app/schemas.py)"]
        Router -->|"Session & History"| SQLite[("Database\n(SQLite / Neon PostgreSQL)\nForeign Keys Enforced")]
        
        Router -->|"Build Bounded Context"| MemoryMgr["Context Window Manager\n(app/memory.py)"]
        MemoryMgr -->|"Rolling Memory"| SQLite
        MemoryMgr -->|"If history > trigger"| Summarizer["Rolling Summarizer\n(app/openai_client.py)"]
        
        Router -->|"Generate Reply"| OpenAIClient["OpenAI Client\n(app/openai_client.py)"]
    end

    Summarizer -->|"Responses API\n(reasoning: low, 512 tokens)"| OpenAIAPI["OpenAI API\n(gpt-6-luna)"]
    OpenAIClient -->|"Responses API\n(reasoning: low/med/high)"| OpenAIAPI
```

---

## 2. Key Features

- **Multi-Turn Stateful Conversations**: Maintains independent message histories across separate conversation sessions identified by UUIDs.
- **Persistent Conversation Memory**: All conversations, titles, summaries, and messages are persisted in SQLite/PostgreSQL using SQLAlchemy 2.x models with cascade deletion. Messages survive full backend reboots.
- **Rolling Context-Window Management**:
  - Dynamically retains recent messages within a configurable context budget (`MAX_CONTEXT_MESSAGES`).
  - When history exceeds the trigger threshold (`SUMMARY_TRIGGER_MESSAGES`), older turns are automatically summarized into a cumulative factual memory.
  - **Never splits user/assistant pairs**: Summarization strictly processes balanced `(user, assistant)` turns, preventing orphaned messages.
  - **Archival strategy**: Older messages are archived in the database rather than deleted, allowing full conversation history inspection in `GET /api/conversations/{id}` while keeping the active LLM context strictly bounded.
  - **Anti-Prompt-Injection Delimiters**: Summaries are structured as factual context and acknowledged by the model, preventing summaries from being interpreted as fresh user instructions.
- **Custom System Persona (`prompts.py`)**: Dedicated prompt defining an intelligent, technically accurate, concise assistant that acknowledges uncertainty and never hallucinates remembered facts, passed via OpenAI's `instructions` parameter.
- **Resilient Error Handling**:
  - Catches invalid API keys (401/403), rate limits (429), timeouts (504), service unavailability (500/502/503), and empty responses.
  - Reverts uncommitted user messages upon upstream failures to avoid orphaned state.
  - Never leaks API keys, raw exceptions, or stack traces in HTTP responses.
- **Security & Validation**:
  - API keys loaded exclusively from environment variables via Pydantic Settings.
  - Message size limits (`MAX_MESSAGE_CHARS`) enforced with HTTP 413.
  - Blank or whitespace-only messages rejected with HTTP 422.
  - Configurable CORS origin restriction.
- **Three Intelligence Modes (Swift, Balanced, Deep)**:
  - **Swift**: Fast latency responses powered by **GPT-6 Luna** (`gpt-6-luna`) with **low** reasoning effort and 1024 output tokens.
  - **Balanced**: Everyday intelligence powered by **GPT-6 Luna** (`gpt-6-luna`) with **medium** reasoning effort and 2048 output tokens.
  - **Deep**: Advanced reasoning and complex problem-solving powered by **GPT-6 Luna** (`gpt-6-luna`) with **high** reasoning effort and 4096 output tokens.
  - Mode persistence per conversation, seamless switching without memory fragmentation, and strict HTTP 422 rejection of unsupported modes.
- **Full React Frontend Integration**: Modern React 19 + Vite UI with dark/light themes, real-time mode selector, conversation sidebar, markdown rendering, and backend health status banner.
- **Automated Testing Suite**: 56 automated pytest unit and integration tests mocking OpenAI calls (zero API costs), plus a separate manual live integration smoke test script.

---

## 3. Technology Stack

| Component | Technology | Description |
|---|---|---|
| **Runtime** | Python 3.11+ | Python asynchronous backend environment |
| **API Framework** | FastAPI (0.115+) | High-performance ASGI framework with Pydantic v2 |
| **Server** | Uvicorn (0.30+) | Lightning-fast ASGI web server |
| **LLM SDK** | `openai` (1.60+) | Official OpenAI Python SDK (`AsyncOpenAI`) |
| **LLM API** | Responses API (`client.responses.create`) | OpenAI Responses API with native reasoning effort control |
| **LLM Model** | GPT-6 Luna (`gpt-6-luna`) | Fast, efficient reasoning model with tunable effort |
| **ORM & Database** | SQLAlchemy 2.x & SQLite / PostgreSQL | Relational database with cascade foreign keys |
| **Settings** | Pydantic Settings 2.x | Validated environment configuration |
| **Testing** | pytest & pytest-asyncio | Asynchronous test framework |
| **HTTP Client** | HTTPX (0.27+) | Async client for API testing and requests |

---

## 4. Repository Structure

```
context-ai-chatbot/
├── .gitignore                      # Git ignore rules (.env, *.db, .venv, etc.)
├── pytest.ini                      # Pytest runner configuration
├── README.md                       # Comprehensive documentation
├── backend/
│   ├── .env                        # Local environment variables (ignored by Git)
│   ├── .env.example                # Example configuration template
│   ├── requirements.txt            # Python dependencies
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application, CORS, lifespan, exception handlers
│   │   ├── config.py               # Pydantic Settings and environment resolution
│   │   ├── database.py             # SQLAlchemy 2.x engine, SQLite PRAGMA, SessionLocal
│   │   ├── models.py               # SQLAlchemy models (Conversation, Message)
│   │   ├── schemas.py              # Pydantic v2 request/response schemas
│   │   ├── prompts.py              # System instructions and memory condensation prompt
│   │   ├── openai_client.py        # Official OpenAI AsyncOpenAI client, Responses API & error mapping
│   │   ├── memory.py               # Context window manager, turn pairing, rolling summarizer
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── chat.py             # REST API endpoints (/api/conversations, /api/chat)
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py             # Test fixtures (in-memory SQLite, mock OpenAI)
│       ├── test_health.py          # /health and root endpoint tests
│       ├── test_conversations.py   # CRUD tests for conversations
│       ├── test_chat_validation.py # Edge cases (empty, invalid ID, oversized)
│       ├── test_chat_flow.py       # Message exchange and error recovery
│       ├── test_memory_and_context.py # Multi-conversation isolation and rolling summary
│       ├── test_five_turn_conversation.py # 5-turn multi-turn dialogue retention
│       ├── test_persistence_restart.py    # Database persistence across server reboots
│       ├── test_openai_client.py   # Comprehensive OpenAI client and mode routing tests
│       └── test_openai_live.py     # Standalone manual live smoke test with real OpenAI API key
└── frontend/                       # Reserved for frontend integration
```

---

## 5. Installation and Setup

### 5.1 Prerequisites
- Python 3.11 or higher
- An OpenAI API key from [OpenAI Platform](https://platform.openai.com/api-keys)

### 5.2 Clone Repository
```bash
git clone https://github.com/bvr4j/context-ai-chatbot.git
cd context-ai-chatbot
```

### 5.3 Virtual Environment Setup

**Windows PowerShell:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 5.4 Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 5.5 Environment Configuration
Copy `backend/.env.example` to `backend/.env`:

**Windows PowerShell:**
```powershell
Copy-Item backend/.env.example backend/.env
```

**macOS / Linux:**
```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` and insert your OpenAI API key:
```env
OPENAI_API_KEY=your_actual_openai_api_key_here
OPENAI_MODEL=gpt-6-luna
DATABASE_URL=sqlite:///./contextai.db
APP_ENV=development
FRONTEND_ORIGIN=http://localhost:5173
MAX_CONTEXT_MESSAGES=12
SUMMARY_TRIGGER_MESSAGES=16
MAX_MESSAGE_CHARS=8000
ARCHIVE_OLD_MESSAGES=true
```

---

## 6. Running the Backend

From the repository root:

```bash
python -m uvicorn app.main:app --reload --app-dir backend
```

- **Interactive API Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative API Documentation (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 7. API Specification

### 7.1 `GET /health`
Returns backend health status, active LLM provider and model, and environment.

**Response (200 OK):**
```json
{
  "status": "ok",
  "service": "contextai-api",
  "version": "0.1.0",
  "environment": "development",
  "database": "sqlite",
  "database_status": "healthy",
  "llm_provider": "openai",
  "llm_configured": true,
  "model": "gpt-6-luna",
  "supported_modes": ["swift", "balanced", "deep"]
}
```

---

### 7.2 `POST /api/conversations`
Creates a new conversation session.

**Request Body (Optional):**
```json
{
  "title": "Machine Learning Discussion"
}
```

**Response (201 Created):**
```json
{
  "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Machine Learning Discussion",
  "created_at": "2026-10-31T14:30:00Z"
}
```

---

### 7.3 `GET /api/conversations`
Lists all conversations ordered by most recently updated.

**Response (200 OK):**
```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "title": "Machine Learning Discussion",
    "summary": "User inquired about transformer architectures.",
    "message_count": 6,
    "created_at": "2026-10-31T14:30:00Z",
    "updated_at": "2026-10-31T14:35:10Z"
  }
]
```

---

### 7.4 `GET /api/conversations/{conversation_id}`
Returns conversation metadata, cumulative summary, and complete chronological message history.

**Response (200 OK):**
```json
{
  "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Machine Learning Discussion",
  "summary": "User discussed deep learning frameworks.",
  "created_at": "2026-10-31T14:30:00Z",
  "updated_at": "2026-10-31T14:35:10Z",
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "Hi, I am studying PyTorch.",
      "created_at": "2026-10-31T14:30:05Z"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "Hello! PyTorch is an excellent library for deep learning.",
      "created_at": "2026-10-31T14:30:08Z"
    }
  ]
}
```

---

### 7.5 `DELETE /api/conversations/{conversation_id}`
Deletes a conversation and its cascaded message history.

**Response:** `204 No Content`

---

### 7.6 `POST /api/chat`
Sends a user message within an existing conversation, invokes OpenAI with bounded context, and stores the response.

**Request Body:**
```json
{
  "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "message": "Can you explain attention mechanisms?"
}
```

**Response (200 OK):**
```json
{
  "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "reply": "Attention mechanisms allow neural networks to dynamically weigh the relevance of different input tokens...",
  "context_summary": "",
  "messages_in_context": 2
}
```

**Error Responses:**
- `404 Not Found`: If `conversation_id` does not exist.
- `413 Payload Too Large`: If message length exceeds `MAX_MESSAGE_CHARS`.
- `422 Unprocessable Content`: If message is empty or whitespace-only.
- `429 Too Many Requests`: If OpenAI API rate limit is exceeded.
- `502 Bad Gateway`: If OpenAI rejects the API key or returns an upstream network error.
- `504 Gateway Timeout`: If OpenAI times out.

---

## 8. Context-Window Management in Depth

### 8.1 The Challenge
Unbounded conversation transcripts cause exponential token cost growth, eventual context overflow errors, and model confusion. Conversely, naive truncations discard critical decisions, preferences, and project names stated early in the chat.

### 8.2 The ContextAI Solution

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Route as routes/chat.py
    participant Memory as memory.py
    participant DB as Database
    participant OpenAI as OpenAI API

    User->>Route: POST /api/chat (message)
    Route->>DB: Persist user message
    Route->>Memory: build_context(conversation)
    
    rect rgb(240, 248, 255)
        Note over Memory: Check active messages count
        alt active messages >= SUMMARY_TRIGGER_MESSAGES
            Memory->>Memory: Find balanced (user, assistant) turn boundary
            Memory->>OpenAI: summarize_text(existing_summary, older_turns)
            OpenAI-->>Memory: Updated cumulative summary
            Memory->>DB: Update conversation.summary
            Memory->>DB: Set older messages is_archived = True
        end
    end

    Memory->>Route: Formatted OpenAI context (Summary + Recent Turns)
    Route->>OpenAI: generate_reply(context, system_instruction)
    OpenAI-->>Route: Assistant reply text
    Route->>DB: Persist assistant message
    Route-->>User: ChatResponse (reply, summary, messages_in_context)
```

### 8.3 Invariants Maintained
1. **Never Split Turn Pairs**: Summarization checks `_find_balanced_turn_split()` to ensure that user prompts are never separated from their assistant responses. A pending user message is never summarized prematurely.
2. **Never Discard Important Information**: Older turns are marked `is_archived = True` in the database. When a user requests conversation history via `GET /api/conversations/{id}`, the complete audit log is available.
3. **Avoid Re-Summarizing**: Once messages are archived, they are excluded from future active message counts, preventing redundant summarization costs.
4. **Anti-Prompt-Injection Grounding**: The summary is passed as a dedicated system context block acknowledged by a simulated assistant response (`"Understood. I will use this background summary strictly as context..."`). This ensures the model treats remembered facts as background data rather than executable instructions.
5. **Token-Budgeting Strategy**: We provide message-count budgeting (`MAX_CONTEXT_MESSAGES`) coupled with heuristic token estimation (`estimate_tokens`). While token count can vary slightly across Unicode scripts, message-turn budgeting guarantees conversational integrity by preserving balanced turns.

---

## 9. Automated Testing

The backend includes a comprehensive pytest test suite with **58 automated unit and integration tests**. All tests use an in-memory SQLite database and mocked OpenAI endpoints, allowing the entire suite to run offline with zero API cost.

### 9.1 Run Automated Tests

```bash
.\.venv\Scripts\pytest -v
```

### 9.2 Running the Live OpenAI Integration Test
To run a real outbound test against OpenAI's API:
1. Ensure your `backend/.env` has a valid `OPENAI_API_KEY`.
2. Execute:
```bash
python backend/tests/test_openai_live.py
```

---

## 10. Example Five-Turn Conversation Walkthrough

Below is a verified 5-turn conversational sequence demonstrating persistent state retention:

| Turn | User Message | ContextAI Assistant Response | System Memory Behavior |
|:---:|:---|:---|:---|
| **1** | `"Hello! My name is Jordan and I am a backend engineer."` | `"Hello Jordan! Great to meet you. How can I assist you with backend engineering today?"` | Session initialized; title auto-set to `"Hello! My name is Jordan..."`. |
| **2** | `"I am designing a real-time event streaming pipeline using Apache Kafka."` | `"Apache Kafka is great for high-throughput distributed event streaming. Are you using schema registries?"` | Context contains 4 messages in SQLite. |
| **3** | `"We are using Python with FastAPI and SQLAlchemy."` | `"FastAPI with SQLAlchemy is a productive stack. You can run Kafka consumers asynchronously."` | 6 messages stored. Turn history preserved chronologically. |
| **4** | `"What is my name and what streaming tool did I say we are using?"` | `"Your name is Jordan, and you are using Apache Kafka for real-time event streaming."` | Model faithfully recalls Jordan and Kafka from active conversation history. |
| **5** | `"What database ORM did I specify?"` | `"You mentioned you are using SQLAlchemy alongside FastAPI."` | Model grounds answer in earlier turn facts without hallucinations. |

---

## 11. Database Configuration & Alembic Migrations

ContextAI supports dual-database architectures:
- **Production (Neon PostgreSQL)**: Neon Serverless PostgreSQL with connection pooling (`-pooler`) for low-latency serverless requests and autoscaling.
- **Local Development / Tests (SQLite)**: Standalone file or in-memory SQLite with isolated `PRAGMA foreign_keys = ON` handling.

### 11.1 Production Enforcement
If `APP_ENV=production` or `VERCEL` is detected, ContextAI strictly enforces `DATABASE_URL`. The application will fail to start rather than silently falling back to ephemeral SQLite.

### 11.2 Database Drivers
ContextAI uses **psycopg 3** (`psycopg[binary]`) exclusively. Connection URLs starting with `postgresql://` or `postgres://` are automatically normalized to `postgresql+psycopg://`.

### 11.3 Running Alembic Migrations with `DATABASE_URL_UNPOOLED`
Per Neon best practices, schema migrations (DDL operations) must use a **direct (unpooled)** connection rather than the connection pooler. The connection pooler operates in transaction mode and does not support statements that require session state or long-running exclusive locks during migrations.

1. **Verify your environment variables**:
   In `.env.local` (pulled via `neon deploy` or configured manually):
   ```env
   # Pooled connection string used for app queries (handles rapid function concurrency)
   DATABASE_URL="postgresql://user:pass@ep-xyz-pooler.region.neon.tech/neondb?sslmode=require"

   # Direct unpooled connection string used exclusively for Alembic migrations
   DATABASE_URL_UNPOOLED="postgresql://user:pass@ep-xyz.region.neon.tech/neondb?sslmode=require"
   ```

2. **Apply migrations**:
   Alembic automatically detects and prioritizes `DATABASE_URL_UNPOOLED` when running:
   ```bash
   alembic upgrade head
   ```

3. **Check current migration version**:
   ```bash
   alembic current
   ```

4. **Generate a new migration**:
   ```bash
   alembic revision --autogenerate -m "describe_changes"
   ```

---

## 12. Security Considerations for Production

1. **API Key Isolation**: `OPENAI_API_KEY` is loaded server-side only through Pydantic Settings and is never sent to the client or written into logs.
2. **CORS Hardening**: In production (`APP_ENV=production`), CORS restricts requests strictly to the configured `FRONTEND_ORIGIN`.
3. **Input Sanitization**: Content length is strictly capped at `MAX_MESSAGE_CHARS` (HTTP 413) to protect against buffer exhaustion and excessive token billing.
4. **Production Deployment Requirements**:
   - **User Authentication**: Implement JWT or OAuth2 bearer tokens.
   - **Authorization**: Add `user_id` foreign keys to `conversations` table to prevent cross-tenant access.
   - **Distributed Rate Limiting**: Implement Redis-backed token bucket rate limiters (e.g. `slowapi` or Redis cell) to defend against DDoS and API budget depletion.

---

## 13. License

ContextAI is developed for the LLM API Integration (AI-1) internship assignment.
Distributed under the MIT License.
