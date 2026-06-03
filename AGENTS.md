# AGENTS.md — Autonomous UI Builder · Backend

> Loaded automatically by Antigravity 2.0 and Claude Code at session start.
> This is the backend repo. Frontend lives in ui-builder-frontend (separate repo).

---

## Project identity

| Field | Value |
|---|---|
| Project name | Autonomous UI Builder Agent — Backend |
| Repo name | ui-builder-backend |
| Author | Ekta Tiwari |
| Current phase | Phase 2 — Backend API + AI Orchestrator |
| Frontend repo | ui-builder-frontend (already deployed on Vercel) |
| Status | Active development |

---

## What this service does

A FastAPI backend that receives user prompts from the frontend, orchestrates
AI agents (Gemini for planning, OpenAI for code generation), validates output,
and streams React + Tailwind component code back to the client.

**Core flow:**
```
Frontend prompt → POST /generate-ui → Prompt Parser → Planner Agent (Gemini)
→ Component Generator (OpenAI) → Validator → SSE stream back to frontend
```

---

## Repository structure

```
ui-builder-backend/
│
├── app/
│   ├── main.py                  # FastAPI app entry point, CORS, router registration
│   ├── config.py                # Settings via pydantic-settings (.env loader)
│   │
│   ├── api/                     # Route handlers (thin — logic lives in services/)
│   │   ├── __init__.py
│   │   ├── generate.py          # POST /generate-ui  (SSE streaming)
│   │   ├── improve.py           # POST /improve-ui
│   │   ├── projects.py          # GET /projects, GET /project/:id, DELETE /project/:id
│   │   └── export.py            # POST /export-project
│   │
│   ├── services/                # Business logic — all AI orchestration lives here
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # LangGraph agent graph — wires planner → generator → validator
│   │   ├── planner.py           # Gemini API — UI architecture planning
│   │   ├── generator.py         # OpenAI API — React/Tailwind code generation
│   │   ├── validator.py         # Syntax check, safety filter, accessibility hints
│   │   └── prompt_parser.py     # Normalize input, extract intent, classify style
│   │
│   ├── models/                  # Pydantic models (request/response shapes)
│   │   ├── __init__.py
│   │   ├── project.py           # Project, Generation schemas
│   │   └── requests.py          # GenerateUIRequest, ImproveUIRequest, ExportRequest
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   └── supabase.py          # Supabase client init, CRUD helpers
│   │
│   └── middleware/
│       ├── __init__.py
│       ├── auth.py              # JWT validation via Supabase Auth
│       └── rate_limit.py        # Per-user rate limiting (free: 10/day, premium: 100/day)
│
├── tests/
│   ├── test_generate.py
│   ├── test_planner.py
│   ├── test_validator.py
│   └── conftest.py
│
├── .env.example                 # Template — never commit .env
├── requirements.txt
├── Dockerfile
├── railway.toml                 # Railway deployment config
└── README.md
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Framework | FastAPI (Python 3.11+) |
| AI — planning | Google Gemini API (`gemini-1.5-pro`) |
| AI — code gen | OpenAI API (`gpt-4o`) |
| Agent orchestration | LangGraph + LangChain |
| Database | PostgreSQL via Supabase |
| Auth | Supabase Auth (JWT) |
| Streaming | Server-Sent Events (SSE) via `sse-starlette` |
| Testing | Pytest + pytest-asyncio |
| Deploy | Railway |
| Config | pydantic-settings |

---

## Environment variables (.env)

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key

# AI APIs
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...

# App
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000
SECRET_KEY=your-secret-key
```

**Rules:**
- Never hardcode secrets. Always read from environment via `config.py`.
- Never log API keys, user prompts, or generated code in production.
- `.env` is gitignored. Only `.env.example` is committed.

---

## Database schema (Supabase / PostgreSQL)

```sql
CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  name TEXT,
  subscription_plan TEXT DEFAULT 'free',
  generations_today INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  prompt TEXT NOT NULL,
  generated_code TEXT,
  preview_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE generations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  ai_model TEXT,
  prompt_tokens INT,
  response_tokens INT,
  generation_status TEXT DEFAULT 'pending',
  latency_ms INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category TEXT,
  template_name TEXT,
  metadata JSONB
);

-- Indexes
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);
CREATE INDEX idx_generations_project_id ON generations(project_id);
CREATE INDEX idx_projects_prompt_fts ON projects USING gin(to_tsvector('english', prompt));
```

---

## API contract

### POST /generate-ui
```json
// Request
{
  "prompt": "Build a SaaS pricing page with 3 tiers",
  "style": "minimal",
  "framework": "react-tailwind"
}

// Response — SSE stream
data: {"type": "plan", "content": "Planning UI architecture..."}
data: {"type": "chunk", "content": "export function PricingSection() {"}
data: {"type": "done", "project_id": "uuid", "total_tokens": 1240}
data: {"type": "error", "message": "Generation failed"}
```

### POST /improve-ui
```json
{ "project_id": "uuid", "instruction": "Make the hero section larger" }
// Same SSE stream format
```

### GET /projects
```json
[{ "id": "uuid", "title": "...", "prompt": "...", "created_at": "..." }]
```

### GET /project/:id
```json
{ "id": "uuid", "title": "...", "prompt": "...", "generated_code": "...", "created_at": "..." }
```

### DELETE /project/:id
```json
{ "success": true }
```

### POST /export-project
```json
// Request: { "project_id": "uuid" }
// Response: { "download_url": "https://..." }
```

---

## AI agent pipeline

```
1. prompt_parser.py    — sanitize, normalize, extract intent + style
2. planner.py          — Gemini 1.5 Pro → JSON layout plan
3. generator.py        — GPT-4o → JSX string, streamed
4. validator.py        — syntax check, safety filter, export check
5. orchestrator.py     — LangGraph wires 1–4, retry logic (max 2)
```

---

## Code conventions

- Python 3.11+ — modern typing, `async def` everywhere
- Pydantic v2 for all models
- No business logic in route handlers — thin handlers only
- Docstrings on all public functions (Google style)
- Never let raw exceptions reach the client
- Use `logging` module, never `print()`

```python
# Route handler — thin
@router.post("/generate-ui")
async def generate_ui(request: GenerateUIRequest, user=Depends(get_current_user)):
    return StreamingResponse(
        orchestrator.run(request, user_id=user.id),
        media_type="text/event-stream"
    )

# Service — all logic here
async def run(request: GenerateUIRequest, user_id: str) -> AsyncGenerator[str, None]:
    """Orchestrate the full UI generation pipeline."""
    ...
```

---

## Performance targets

| Metric | Target |
|---|---|
| AI generation (total) | < 20 seconds |
| First SSE chunk | < 3 seconds |
| Non-AI API routes | < 500ms |
| Export generation | < 10 seconds |

---

## Security rules

- All routes require valid JWT except `/health`
- Rate limit: free = 10 generations/day, premium = 100/day
- Sanitize all prompt input before sending to AI
- CORS: only allow `FRONTEND_URL` — never `*` in production
- Prevent prompt injection via locked system prompts

---

## Session build order

| Session | Task |
|---|---|
| 1 | Project scaffold + FastAPI entry + config |
| 2 | Supabase setup + CRUD helpers |
| 3 | Pydantic models + API route stubs |
| 4 | Prompt parser service |
| 5 | Planner agent (Gemini) |
| 6 | Generator agent (OpenAI) + SSE streaming |
| 7 | Validator service |
| 8 | LangGraph orchestrator |
| 9 | Auth middleware + rate limiting |
| 10 | Pytest test suite |
| 11 | Dockerfile + Railway deployment |

---

## Out of scope for Phase 2

- Frontend changes (separate repo)
- Full-stack code generation
- Real-time collaboration / websockets
- Custom model fine-tuning
- Figma integration
- GitHub export
- Voice prompts
