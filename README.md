# AI Chatbot API

A RESTful backend for AI-powered chatbot conversations, built with **FastAPI**, **MongoDB**, **JWT auth**, and **OpenAI**.

## Features

- JWT-based user registration & login
- Chat endpoint that calls an AI model (OpenAI GPT by default) and returns context-aware replies
- Persistent conversation history stored in MongoDB, scoped per user
- Auto-generated interactive docs (Swagger UI + ReDoc)
- Clean, modular structure ready to extend (rate limiting, streaming, sentiment analysis, etc.)

## Project Structure

```
ai_chatbot_api/
├── app/
│   ├── main.py              # FastAPI app, CORS, startup
│   ├── config.py            # Settings loaded from .env
│   ├── database.py          # MongoDB (motor) client + indexes
│   ├── schemas.py           # Pydantic request/response models
│   ├── auth.py              # Password hashing, JWT, current-user dependency
│   ├── routers/
│   │   ├── auth.py          # /auth/register, /auth/login
│   │   └── chat.py          # /chat, /chat/conversations, ...
│   └── services/
│       └── ai_service.py    # OpenAI integration
├── requirements.txt
└── .env.example
```

## Setup

1. **Install dependencies** (Python 3.10+ recommended):
   ```bash
   pip install -r requirements.txt
   ```

2. **Run MongoDB** locally, or use a hosted instance (e.g. MongoDB Atlas free tier).

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env`:
   - `MONGO_URI` — your MongoDB connection string
   - `OPENAI_API_KEY` — your OpenAI API key
   - `JWT_SECRET_KEY` — a long random string (e.g. `openssl rand -hex 32`)

4. **Run the server**:
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Open the interactive docs**: http://localhost:8000/docs

## API Overview

### Auth

| Method | Endpoint         | Description                     |
|--------|------------------|----------------------------------|
| POST   | `/auth/register` | Create an account, returns JWT   |
| POST   | `/auth/login`    | Log in, returns JWT              |

### Chat (all require `Authorization: Bearer <token>`)

| Method | Endpoint                                       | Description                                  |
|--------|-------------------------------------------------|-----------------------------------------------|
| POST   | `/chat`                                         | Send a message; creates a conversation if `conversation_id` is omitted |
| GET    | `/chat/conversations`                           | List the current user's conversations         |
| GET    | `/chat/conversations/{conversation_id}/messages`| Get full message history for a conversation    |
| DELETE | `/chat/conversations/{conversation_id}`         | Delete a conversation and its messages         |

## Example Usage

**Register:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com", "password": "secret123"}'
```
Response:
```json
{ "access_token": "eyJhbGciOi...", "token_type": "bearer" }
```

**Send a chat message:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer eyJhbGciOi..." \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of France?"}'
```
Response:
```json
{
  "conversation_id": "665f1c2e...",
  "reply": "The capital of France is Paris.",
  "history": [
    { "role": "user", "content": "What is the capital of France?", "created_at": "..." },
    { "role": "assistant", "content": "The capital of France is Paris.", "created_at": "..." }
  ]
}
```

**Continue the same conversation** by passing the returned `conversation_id` in the next request.

## Notes on Design Choices

- **Passwords** are hashed with bcrypt via `passlib`, never stored in plaintext.
- **JWTs** are signed with HS256 and expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60).
- **Conversation context**: the last 20 messages of a conversation are sent to the AI model on each turn, so replies stay context-aware without unbounded token growth.
- **MongoDB** was chosen for flexible, document-shaped chat history; swapping to MySQL/Postgres would mean replacing `database.py` and the raw dict access in the routers with an ORM (e.g. SQLAlchemy models).

## Extending This Project

Ideas to build on top of this base, as called out in the original spec:
- **Multi-language support**: detect language and pass a locale hint into the system prompt.
- **Conversation summarization**: periodically summarize older messages instead of truncating them, to keep long chats cheap.
- **Sentiment analysis**: run each user message through a classifier and store the result alongside the message.
- **File uploads**: accept documents/images and pass them to a multimodal model.
- **Voice input/output**: integrate speech-to-text (e.g. Whisper) and text-to-speech.
- **Role-based access control**: add a `role` field to users and guard admin-only endpoints (e.g. viewing all conversations).
- **Rate limiting**: add `slowapi` or a Redis-backed limiter to protect the `/chat` endpoint from abuse.
- **Streaming responses**: use OpenAI's streaming API + FastAPI `StreamingResponse` for token-by-token replies.

## Swapping AI Providers

`app/services/ai_service.py` is the only file that talks to the AI provider. To use Hugging Face Transformers or another provider instead of OpenAI, replace the contents of `generate_reply()` while keeping its signature (`history`, `user_message` in → `str` reply out) — the rest of the app doesn't need to change.
