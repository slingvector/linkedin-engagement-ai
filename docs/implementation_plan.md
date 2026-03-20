# Phase 1 Sprint 1: Foundation & Identity

The goal is to scaffold a production-grade monorepo with three apps (backend, AI engine, frontend), set up the database, implement LinkedIn OAuth 2.0, and establish the CI/testing baseline — all following SOLID principles, snake_case naming, YAML config, and no hardcoding.

## User Review Required

> [!IMPORTANT]
> **Tech Stack Confirmation:** The plan uses **Python FastAPI** for both `core_api` and `ai_engine` (not Golang). This keeps the stack homogeneous for a solo/small team. If you prefer Golang for `core_api`, let me know before I proceed.

> [!IMPORTANT]
> **Frontend Deferral:** Per the project plan, Dev 1 owns frontend. Sprint 1 focuses primarily on backend scaffolding and AI engine. I'll create a minimal Next.js shell but defer heavy UI work. Confirm if you want full frontend scaffolding now or lean backend-first.

> [!WARNING]
> **LinkedIn OAuth:** Requires a LinkedIn Developer App with `openid`, `profile`, `email`, and `w_member_social` scopes. You'll need to create this at [developer.linkedin.com](https://developer.linkedin.com) and provide the Client ID/Secret as env vars.

---

## Proposed Changes

### Monorepo Root

#### [NEW] [turbo.json](file:///Users/cortex/ventures/linkedin-as-a-service/turbo.json)
Turborepo pipeline config for build/dev/lint/test across all packages.

#### [NEW] [package.json](file:///Users/cortex/ventures/linkedin-as-a-service/package.json)
Root package.json with Turborepo workspace configuration.

#### [NEW] [docker-compose.yml](file:///Users/cortex/ventures/linkedin-as-a-service/docker-compose.yml)
Local dev environment: PostgreSQL 16 + Redis 7. No hardcored connection strings — reads from `.env`.

#### [NEW] [.env.example](file:///Users/cortex/ventures/linkedin-as-a-service/.env.example)
Template for all environment variables (DB, Redis, LinkedIn OAuth, LLM keys).

---

### Backend: `apps/core_api/` (Dev 2 — FastAPI)

Layered architecture following BACKEND_STANDARDS.md: Controller → Service → Repository.

#### [NEW] [pyproject.toml](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/pyproject.toml)
Dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `asyncpg`, `alembic`, `pydantic-settings`, `python-jose[cryptography]`, `httpx`, `redis`, `pyyaml`, `structlog`.

#### [NEW] [config.yaml](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/config.yaml)
All business logic parameters in YAML (rate limits, timeouts, OAuth scopes). **Zero hardcoding.**

#### [NEW] [Dockerfile](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/Dockerfile)
Multi-stage Python 3.12 image for portability/determinism.

#### Directory structure:
```
apps/core_api/
├── config.yaml                    # All configurable params (NO HARDCODING)
├── pyproject.toml
├── Dockerfile
├── alembic/                       # DB migrations
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py  # users + posts tables
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app factory + lifespan
│   ├── config.py                  # Pydantic Settings (reads YAML + .env)
│   ├── dependencies.py            # DI: db session, current_user, etc.
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── error_handler.py       # Global exception handler
│   ├── models/                    # SQLAlchemy models (Repository layer)
│   │   ├── __init__.py
│   │   ├── base.py                # Base model (UUID PK, created_at, soft_delete)
│   │   └── user.py                # users table
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── auth.py
│   ├── repositories/              # Data access (Repository layer)
│   │   ├── __init__.py
│   │   └── user_repository.py
│   ├── services/                  # Business logic (Service layer)
│   │   ├── __init__.py
│   │   ├── auth_service.py        # OAuth flow + JWT token management
│   │   └── user_service.py
│   ├── controllers/               # Route handlers (Controller layer)
│   │   ├── __init__.py
│   │   ├── auth_controller.py     # /api/v1/auth/linkedin, /callback
│   │   └── health_controller.py   # /health, /readiness
│   └── utils/
│       ├── __init__.py
│       ├── logger.py              # structlog config with correlation IDs
│       └── security.py            # JWT encode/decode, token encryption
└── tests/
    ├── __init__.py
    ├── conftest.py                # Shared fixtures (test db, test client)
    ├── test_health.py             # Health check tests
    └── test_auth.py               # OAuth flow unit tests
```

#### Key DB Schema (`001_initial_schema.py`):
```python
# users table
class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, default=uuid4)
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=True)
    linkedin_id = Column(String, unique=True, nullable=False)
    profile_picture_url = Column(String, nullable=True)
    access_token_encrypted = Column(Text, nullable=True)  # Fernet encrypted
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    subscription_tier = Column(String, default="free")
    preferences = Column(JSONB, default={})
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)          # Soft delete
```

---

### AI Engine: `apps/ai_engine/` (Lead)

#### Directory structure:
```
apps/ai_engine/
├── config.yaml                    # LLM model routing, timeouts, blocklists
├── pyproject.toml
├── Dockerfile
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app + security middleware
│   ├── config.py                  # Pydantic Settings
│   ├── dependencies.py            # API key verification
│   ├── schemas/                   # Strict Pydantic contracts (API boundary)
│   │   ├── __init__.py
│   │   ├── post_schemas.py        # PostGenerationRequest/Response
│   │   └── comment_schemas.py     # CommentGenerationRequest/Response
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── post_controller.py     # /webhooks/generate/post
│   │   ├── comment_controller.py  # /webhooks/generate/comments
│   │   └── health_controller.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_service.py         # LLM call abstraction (OpenAI/local routing)
│   │   ├── post_service.py        # Post generation orchestration
│   │   └── comment_service.py     # Comment generation orchestration
│   ├── prompts/                   # Version-controlled prompt templates
│   │   ├── system_post.txt
│   │   ├── framework_story.txt
│   │   ├── framework_contrarian.txt
│   │   ├── framework_playbook.txt
│   │   ├── framework_lessons.txt
│   │   └── blocklist.yaml         # Negative word list
│   └── utils/
│       ├── __init__.py
│       └── logger.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── test_schemas.py            # Schema validation tests
```

#### Key Pydantic Contracts:
```python
# Inbound
class PostGenerationRequest(BaseModel):
    user_id: str
    topic: str = Field(..., max_length=200)
    audience: str = Field(..., max_length=100)
    framework: str = Field(..., description="story, contrarian, playbook, or lessons")
    tone: str | None = "professional_but_conversational"

# Outbound
class PostGenerationResponse(BaseModel):
    hook: str
    body_content: str
    call_to_action: str
```

---

### Frontend: `apps/web/` (Dev 1 — Minimal Shell)

#### [NEW] Next.js App Router scaffolded via `create-next-app`
Minimal shell with login page and dashboard layout. Full UI deferred to Sprint 2.

```
apps/web/
├── package.json
├── tsconfig.json
├── next.config.ts
├── app/
│   ├── layout.tsx          # Global shell + sidebar skeleton
│   ├── page.tsx            # Landing / redirect
│   ├── (auth)/
│   │   └── login/
│   │       └── page.tsx    # "Sign in with LinkedIn" button
│   └── (dashboard)/
│       └── page.tsx        # Authenticated dashboard shell
├── components/
│   └── ui/                 # shadcn/ui primitives (Button, Card, etc.)
└── lib/
    └── api.ts              # API client (base URL from env)
```

---

### Shared Config

#### [NEW] [.gitignore](file:///Users/cortex/ventures/linkedin-as-a-service/.gitignore)
Python, Node, Docker, IDE ignores. Excludes `.env`, `.venv`, `node_modules`, `__pycache__`.

---

## Verification Plan

### Automated Tests

**1. Core API Unit Tests**
```bash
cd apps/core_api
python -m pytest tests/ -v
```
Tests:
- `test_health.py`: GET `/health` returns 200 with `{"status": "healthy"}`
- `test_auth.py`: Validates OAuth URL construction, JWT encode/decode, token encryption/decryption (mocked, no real LinkedIn calls)

**2. AI Engine Schema Tests**
```bash
cd apps/ai_engine
python -m pytest tests/ -v
```
Tests:
- `test_schemas.py`: Validates Pydantic schema accepts valid payloads and rejects invalid ones (missing fields, over max_length, wrong framework values)

**3. Docker Compose Smoke Test**
```bash
docker-compose up -d
curl http://localhost:8000/health   # core_api
curl http://localhost:8001/health   # ai_engine
docker-compose down
```
Both should return `{"status": "healthy"}`.

### Manual Verification
1. Run `docker-compose up` — PostgreSQL + Redis + both Python services start cleanly
2. Visit `http://localhost:8000/docs` — FastAPI Swagger UI loads showing all endpoints
3. Visit `http://localhost:8001/docs` — AI Engine Swagger UI loads showing webhook endpoints
4. Send a mock POST to AI Engine webhook and verify 422 if schema mismatches
5. Confirm `config.yaml` values are loaded (visible in `/health` response or logs)
6. Confirm structured JSON logging in terminal output with correlation IDs
