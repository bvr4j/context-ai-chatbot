# ContextAI — Stateful LLM Chatbot Frontend

A minimal, professional, ChatGPT-inspired frontend for **ContextAI**, a stateful conversational assistant powered by an LLM backend and a FastAPI server with SQLite persistence.

---

## Architecture Overview

```
┌─────────────────────────────────┐
│     ContextAI React Client      │  (Port 3000)
│   • Dark ChatGPT Aesthetic      │
│   • Markdown + Code Copy        │
│   • Context / Memory Indicator  │
│   • Conversation Management     │
└────────────────┬────────────────┘
                 │ REST API (JSON)
                 ▼
┌─────────────────────────────────┐
│        FastAPI Backend          │  (Port 8000, configurable)
│   • SQLite Database             │
│   • Stateful Context Memory     │
│   • LLM Service Handling        │
└─────────────────────────────────┘
```

---

## Features

- **ChatGPT-Inspired UI**: Neutral dark theme (`#212121` canvas, `#171717` sidebar, `#303030` composer, subtle `#3A3A3A` borders, clean typography).
- **Persistent Conversation History**: Conversations are persisted in the backend database and remain available across browser refreshes and sessions.
- **Context & Memory Visualization**: Unobtrusive context indicator displaying active retained messages (`messages_in_context`) and conversation memory summaries (`context_summary`) received from the backend.
- **Rich Markdown & Code Blocks**: Full markdown rendering with headers, lists, blockquotes, tables, inline code, and syntax-styled code blocks with a one-click copy button.
- **Three Intelligence Modes**:
  - **Swift**: Fast responses and low latency (`gpt-6-luna`, low reasoning effort, 1024 output tokens).
  - **Balanced** (Default): Everyday intelligence with optimal speed/quality balance (`gpt-6-luna`, medium reasoning effort, 2048 output tokens).
  - **Deep**: Advanced reasoning and complex analysis (`gpt-6-luna`, high reasoning effort, 4096 output tokens).
- **Zero Dummy Data Policy**: Only displays verified data retrieved from the backend. When backend is offline or empty, displays real diagnostic connection states and clean empty placeholders.
- **Robust Error Handling**: Non-intrusive backend diagnostic alerts, retry controls for failed messages, and automatic connection health verification.
- **Configurable Backend Endpoint**: Easily switch or test backend URLs via the Settings panel (`VITE_API_BASE_URL`).
- **Responsive Layout**: Collapsible sidebar on desktop with slide-over drawer navigation on mobile viewports.

---

## Backend API Specification

ContextAI communicates with the following endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Check backend availability and health status |
| `POST` | `/api/conversations` | Create a new conversation (`{ "title"?: string, "mode"?: "swift" \| "balanced" \| "deep" }`) |
| `GET` | `/api/conversations` | Retrieve all conversations sorted by recency |
| `GET` | `/api/conversations/{id}` | Retrieve conversation message history, mode, and context summary |
| `PATCH` | `/api/conversations/{id}/mode` | Update conversation intelligence mode (`{ "mode": "swift" \| "balanced" \| "deep" }`) |
| `DELETE` | `/api/conversations/{id}` | Delete a conversation and its persisted history |
| `POST` | `/api/chat` | Send user message with selected mode and receive stateful AI response |

### Example Chat Request / Response

**Request:** `POST /api/chat`
```json
{
  "conversation_id": "7b2e1d84-...",
  "message": "Explain how transformers work.",
  "mode": "deep"
}
```

**Response:**
```json
{
  "conversation_id": "7b2e1d84-...",
  "reply": "Transformers are neural network architectures based on self-attention mechanisms...",
  "mode": "deep",
  "model_label": "Deep",
  "context_summary": "User asked for explanation of transformer neural network architectures.",
  "messages_in_context": 2
}
```

---

## Installation & Setup

### 1. Prerequisites
- Node.js 18+
- npm or bun

### 2. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Ensure `VITE_API_BASE_URL` points to your running FastAPI backend:
```env
VITE_API_BASE_URL=http://localhost:8000
```

### 3. Install Dependencies
```bash
npm install
```

### 4. Run Development Server
```bash
npm run dev
```
The app will be accessible at `http://localhost:3000`.

### 5. Production Build
```bash
npm run build
```

---

## Security Model

- **No Frontend Keys**: Model API keys and credentials are never stored or exposed in client-side code.
- **Server-Side LLM Execution**: All LLM calls and context summarization are conducted exclusively on the FastAPI backend.
- **Safe Markdown Rendering**: AI responses are sanitized and safely parsed through ReactMarkdown components without `dangerouslySetInnerHTML`.
