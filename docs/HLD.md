# LinkedIn Copilot — High-Level Design (HLD)

> **Audience:** Engineers, technical stakeholders, and architects.
> This document describes the system's architecture, component boundaries, data model, request flows, and design decisions.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Service Inventory](#3-service-inventory)
4. [Component Design](#4-component-design)
   - 4.1 [Web (Next.js)](#41-web-nextjs)
   - 4.2 [Core API (FastAPI)](#42-core-api-fastapi)
   - 4.3 [AI Engine (FastAPI)](#43-ai-engine-fastapi)
   - 4.4 [Carousel Renderer](#44-carousel-renderer)
   - 4.5 [PostgreSQL](#45-postgresql)
5. [Data Model](#5-data-model)
6. [Key Request Flows](#6-key-request-flows)
   - 6.1 [LinkedIn OAuth Login](#61-linkedin-oauth-login)
   - 6.2 [Post Generation](#62-post-generation)
   - 6.3 [Carousel Studio — Generate & Publish](#63-carousel-studio--generate--publish)
   - 6.4 [Creator Radar — Comment Generation](#64-creator-radar--comment-generation)
   - 6.5 [Smart Fill Calendar](#65-smart-fill-calendar)
7. [Authentication & Security Architecture](#7-authentication--security-architecture)
8. [AI Subsystem Design](#8-ai-subsystem-design)
9. [LLMOps Feedback Loop](#9-llmops-feedback-loop)
10. [API Design Conventions](#10-api-design-conventions)
11. [Deployment Topology](#11-deployment-topology)
12. [Design Decisions & Trade-offs](#12-design-decisions--trade-offs)

---

## 1. System Overview

LinkedIn Copilot is a **multi-tenant SaaS platform** (currently in single-operator trial mode) that automates LinkedIn content creation, engagement, and pipeline management using LLMs.

### Core capability groups

| Group | Features |
|---|---|
| **Content Engine** | Idea Engine, Post Creator, Carousel Studio, Virality Scoring, Smart Fill Calendar |
| **Engagement Engine** | Creator Radar, Action Desk, AI Comment Generation, LLMOps Flywheel |
| **Pipeline Engine** | Lead Inbox, Deals Pipeline, Talent Discovery, ATS, Enterprise ABM |
| **Analytics** | Engagement Heatmap, Dashboard, LLMOps Safety Plane |
| **Auth** | LinkedIn OAuth 2.0, JWT, Write-flow OAuth |

### Design tenets
1. **LinkedIn-native** — all read/write is via LinkedIn APIs or controlled browser sessions; no brittle scraping hacks
2. **AI-first but human-in-the-loop** — every AI output is editable before use; no autonomous posting
3. **Single-writer safety** — rate limits and action delays prevent LinkedIn account restriction
4. **Operator-first** — designed for a single operator running all accounts from one deployment

---

## 2. Architecture Diagram

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                          BROWSER (localhost:3000)                           ║
║  Next.js App                                                                 ║
║  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  ║
║  │  /login  │ │ /posts   │ │ /radar   │ │ /calendar│ │ ...12 more pages │  ║
║  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┬─────────┘  ║
║       │            │            │            │                  │            ║
║  lib/api.ts — axios + Bearer interceptor + 401 auto-logout                  ║
║  lib/store.ts — zustand auth state (JWT in localStorage)                    ║
╚═══════════════════════╤══════════════════════════════════════════════╤═══════╝
    /api/v1/* /api/v2/* │ (Next.js rewrites — no CORS issue)           │
╔══════════════════════▼═══════════════════════════════════════════════╪═══════╗
║                    CORE API  (port 8000)                             │       ║
║  FastAPI · SQLAlchemy (async) · Pydantic v2                          │       ║
║                                                                      │       ║
║  ┌─────────────┐ ┌──────────────┐ ┌────────────────┐                │       ║
║  │ Auth        │ │ Post /       │ │ Creator /      │                │       ║
║  │ Controller  │ │ Idea /       │ │ Comment /      │                │       ║
║  │ /auth/me    │ │ Analytics    │ │ Calendar       │                │       ║
║  └──────┬──────┘ └──────┬───────┘ └───────┬────────┘                │       ║
║         │               │                 │                          │       ║
║  ┌──────▼───────────────▼─────────────────▼────────┐                │       ║
║  │              Service Layer                        │                │       ║
║  │  AuthService · PostService · CreatorService      │                │       ║
║  │  CarouselService · ViralityService               │                │       ║
║  │  HeatmapService · SmartFillService               │                │       ║
║  │  CareerService · SalesService · TalentService    │                │       ║
║  └──────┬───────────────────────────────────────────┘                │       ║
║         │ httpx (async)                                               │       ║
╚═════════╪═══════════════════════════════════════════╤════════════════╪═══════╝
          │                                           │                │
╔═════════▼════════════╗              ╔═══════════════▼══╗    ╔════════▼═══════╗
║  AI ENGINE           ║              ║ CAROUSEL RENDERER║    ║  POSTGRESQL    ║
║  (port 8001)         ║              ║ (port 8002)      ║    ║  (port 5432)   ║
║  FastAPI + LLM SDK   ║              ║ WeasyPrint/PDF   ║    ║                ║
║                      ║              ║                  ║    ║  18 tables     ║
║  Gemini / OpenAI /   ║              ║  HTML→PDF        ║    ║  UUID PKs      ║
║  Vertex AI / Ollama  ║              ║  Branded slides  ║    ║  Soft deletes  ║
║  (pluggable)         ║              ║                  ║    ║                ║
╚══════════════════════╝              ╚══════════════════╝    ╚════════════════╝
         │
╔════════▼═════════════╗
║  LLM PROVIDER        ║
║  (external)          ║
║  Google Gemini       ║
║  OpenAI GPT-4o       ║
║  Vertex AI           ║
║  Ollama (local)      ║
╚══════════════════════╝


LinkedIn APIs (external)
  ├── oauth/v2/authorization      — User login + write-flow consent
  ├── oauth/v2/accessToken        — Token exchange
  ├── v2/userinfo                 — Profile fetch (OpenID Connect)
  ├── rest/documents              — Carousel document upload (3-step)
  └── rest/posts                  — Document post creation
```

---

## 3. Service Inventory

| Service | Runtime | Port | Role |
|---|---|---|---|
| `web` | Next.js 14 | 3000 | Frontend — UI, routing, auth state, API proxy |
| `core_api` | FastAPI (Python 3.12) | 8000 | Business logic, auth, DB, LinkedIn API orchestration |
| `ai_engine` | FastAPI (Python 3.12) | 8001 | LLM inference — post gen, ideas, scoring, comments |
| `carousel_renderer` | FastAPI + WeasyPrint | 8002 | HTML-to-PDF branded slide rendering |
| `postgres` | PostgreSQL 16 | 5432 | Single source of truth for all persistent state |

**Communication patterns:**

```
Browser ──────────► web:3000 (HTTPS in prod, HTTP in dev)
web:3000 ──────────► core_api:8000 (Next.js reverse proxy rewrites)
core_api:8000 ──────► ai_engine:8001 (internal HTTP, X-AI-API-Key header)
core_api:8000 ──────► carousel_renderer:8002 (internal HTTP, no auth)
core_api:8000 ──────► postgres:5432 (asyncpg connection pool)
ai_engine:8001 ─────► LLM Provider (HTTPS, external network)
core_api:8000 ──────► LinkedIn APIs (HTTPS, external network)
```

---

## 4. Component Design

### 4.1 Web (Next.js)

**Framework:** Next.js 14 App Router  
**State:** Zustand (client-side auth state)  
**HTTP:** Axios with request/response interceptors  
**UI:** Tailwind CSS + shadcn/ui components  

**Key design choices:**

**API Proxy via `next.config.ts` rewrites**
```typescript
// All /api/v1/* and /api/v2/* requests are proxied to core_api
// This means the browser never directly talks to core_api — only to Next.js
// Benefit: no CORS issues, single origin, easier auth cookie migration later
rewrites: [
  { source: "/api/v1/:path*", destination: "http://core_api:8000/api/v1/:path*" },
  { source: "/api/v2/:path*", destination: "http://core_api:8000/api/v2/:path*" },
]
```

**Auth state machine**
```
localStorage has token?
    YES → call /auth/me → valid? → render app
                        → 401?  → clear token → /login
    NO  → redirect to /login
```

**Auth guard** (`RootLayoutClient.tsx`)
- Runs on every route change
- Public routes: `/login`, `/auth/callback`
- All other routes: token validated against `/auth/me` on mount
- On 401: global axios interceptor clears token and redirects

---

### 4.2 Core API (FastAPI)

**Framework:** FastAPI 0.115+  
**ORM:** SQLAlchemy 2.0 (async) with asyncpg driver  
**Validation:** Pydantic v2  
**Auth:** `python-jose` (JWT), `cryptography` (Fernet)  
**HTTP Client:** `httpx` (async)  
**Logging:** `structlog` (JSON structured logs)  

**Layer structure:**

```
app/
├── controllers/          # HTTP layer — routing, request/response only
│   ├── auth_controller.py
│   ├── post_controller.py
│   ├── creator_controller.py
│   └── v2/               # V2 versioned controllers
├── services/             # Business logic — pure Python, no HTTP concerns
│   ├── auth_service.py
│   ├── carousel_service.py
│   ├── virality_service.py
│   └── ...
├── repositories/         # DB query layer — SQLAlchemy queries
│   ├── user_repository.py
│   ├── post_repository.py
│   └── ...
├── models/               # SQLAlchemy ORM models
├── schemas/              # Pydantic request/response schemas
├── utils/                # security.py, oauth_state.py
├── middleware/           # error_handler.py
├── dependencies.py       # FastAPI DI — get_db, get_current_user
└── config.py             # Settings (pydantic-settings)
```

**Dependency injection flow:**

```python
# Every protected endpoint follows this DI chain:
get_db() → get_user_repository() → get_current_user()
              ↓
       AsyncSession from connection pool
```

**API versioning:**
- V1 (`/api/v1/`) — stable production endpoints
- V2 (`/api/v2/`) — newer features: carousel, virality, heatmap, smart fill

---

### 4.3 AI Engine (FastAPI)

The AI Engine is a **stateless inference service**. It receives structured prompts from Core API, calls an LLM, and returns structured JSON. It has no database access.

**Pluggable LLM provider system:**

| Provider | Config | When to use |
|---|---|---|
| `openai` | `OPENAI_API_KEY` | Default; GPT-4o or GPT-4o-mini |
| `gemini` | `GEMINI_API_KEY` | Google Gemini 2.0 Flash |
| `vertex` | `GCP_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS` | Managed Vertex AI (prod) |
| `ollama` | `OLLAMA_URL`, `OLLAMA_MODEL` | Local inference (dev/air-gapped) |

Switch provider by setting `LLM_PROVIDER=gemini` in `.env`.

**Endpoint groups:**

```
/webhooks/v1/
  POST /generate/post               ← Post generation
  POST /generate/ideas              ← Idea Engine
  POST /generate/comment            ← Comment drafts
  POST /generate/dm-draft           ← DM Copilot
  POST /generate/cover-letter       ← Career Agent
  POST /classify/intent             ← Lead intent classification
  POST /score/candidate             ← Talent scoring
  POST /generate/signal-map         ← Enterprise ABM signal mapping

/webhooks/v2/
  POST /generate/week-plan          ← Smart Fill Calendar
  POST /score/post                  ← Virality Scoring
  POST /generate/carousel-outline   ← Carousel Studio (7-slide outline)
  POST /evals/judge                 ← LLMOps LLM-as-a-Judge
```

**Authentication:** All requests must include `X-AI-API-Key: <AI_ENGINE_API_KEY>`. The AI Engine validates this against its own config. Core API is the only authorized caller.

**Prompt system:** System prompts are stored as plain `.txt` files in `app/prompts/`. This allows prompt iteration without code changes.

---

### 4.4 Carousel Renderer

A purpose-built microservice that converts slide data (JSON) + brand kit into a **branded PDF** suitable for LinkedIn Document Upload.

**Tech:** FastAPI + WeasyPrint (Python) + Pango/Cairo (system dependencies)

**Endpoint:**
```
POST /render
{
  "slides": [...],        ← From AI Engine carousel outline
  "brand_kit": {...},     ← User's colors, font, logo
  "cover_hook": "...",
  "cta_text": "..."
}
→ { "pdf_base64": "..." }
```

**Rendering pipeline:**
```
JSON → Jinja2 HTML template → WeasyPrint → PDF bytes → base64 → response
```

**No auth required** — only reachable from within the Docker network (`core_api` → `carousel_renderer:8002`).

---

### 4.5 PostgreSQL

Single Postgres 16 instance. **No Redis** — all state is DB-backed.

**Connection:** asyncpg via SQLAlchemy 2.0 async engine  
**Pool:** 10 connections, 20 overflow (configurable)  
**Schema management:** `Base.metadata.create_all()` on startup (no Alembic)  
**Soft deletes:** All major tables have `deleted_at` column (non-null = deleted)

---

## 5. Data Model

### Entity Relationship Overview

```
users (1) ──────────────────────────────────── (many) posts
         │                                            │
         ├── (many) tracked_creators                  ├── (1) carousel_assets
         │         │                                  └── (1) virality_scores (on post row)
         │         └── (many) ingested_posts
         │                    │
         │                    └── (many) comment_drafts
         │
         ├── (1) user_settings        ← brand kit, preferences
         ├── (many) shadow_action_logs  ← LLMOps DPO data
         │         └── (many) llm_evaluations
         │
         ├── (many) lead_prospects    ← Sales pipeline
         ├── (many) career_applications
         ├── (many) talent_candidates
         └── (many) oauth_states      ← CSRF tokens (expire in 10 min)
```

### Core Tables

| Table | Purpose | Key Columns |
|---|---|---|
| `users` | One row per authenticated user | `linkedin_id`, `email`, `access_token_encrypted`, `write_access_token_encrypted`, `subscription_tier` |
| `posts` | Post drafts and published posts | `user_id`, `topic`, `hook`, `body`, `status`, `scheduled_at`, `virality_score` |
| `carousel_assets` | Generated PDF carousels | `post_id`, `slides_json`, `pdf_url`, `status`, `linkedin_asset_urn` |
| `tracked_creators` | LinkedIn profiles being monitored | `user_id`, `linkedin_url`, `name` |
| `ingested_posts` | Creator posts scraped from LinkedIn | `creator_id`, `linkedin_url`, `content`, `likes`, `comments` |
| `comment_drafts` | AI-generated comment options | `ingested_post_id`, `user_id`, `content`, `tone`, `status` |
| `oauth_states` | CSRF state tokens for OAuth flows | `state_token` (unique), `user_id` (nullable), `expires_at` |
| `user_settings` | Brand kit and content preferences | `user_id`, `primary_color`, `font_family`, `logo_url`, `author_name` |
| `shadow_action_logs` | Human-vs-AI diff for DPO training | `user_id`, `ai_draft_content`, `human_final_content`, `edit_similarity_score` |
| `llm_evaluations` | LLM-as-Judge quality scores | `log_id`, `hallucination_score`, `tone_adherence_score`, `safety_compliance_score` |

### Notable Design Choices

- **UUID primary keys** across all tables (PostgreSQL `UUID` type, not `varchar`)
- **Soft deletes** via `deleted_at` — queries always filter `deleted_at IS NULL`
- **Fernet encryption** on all LinkedIn tokens at rest (`access_token_encrypted`, `write_access_token_encrypted`, `li_at_cookie_encrypted`)
- **JSONB** for flexible fields (`posts.slides_json`, `carousel_assets.brand_kit_snapshot`, `users.preferences`)
- **`oauth_states` replaces in-memory dicts** — multi-worker and restart-safe CSRF protection

---

## 6. Key Request Flows

### 6.1 LinkedIn OAuth Login

```
Browser                 Next.js              Core API              LinkedIn
   │                       │                     │                      │
   │── GET /login ─────────►│                     │                      │
   │                       │                     │                      │
   │── click "Sign in" ────►│                     │                      │
   │                       │── GET /api/v1/auth/linkedin ──────────────►│
   │                       │                     │                      │
   │                       │                  create oauth_state row    │
   │                       │                  (state_token, expires_at) │
   │                       │                     │                      │
   │                       │◄── { auth_url } ────│                      │
   │                       │                     │                      │
   │◄── redirect to auth_url ──────────────────────────────────────────►│
   │                       │                     │                      │
   │   [User approves on LinkedIn]               │                      │
   │                       │                     │                      │
   │◄── redirect /auth/callback?code=X&state=Y ──────────────────────────
   │                       │                     │
   │── GET /auth/callback ─►│                     │
   │                       │── GET /api/v1/auth/linkedin/callback ──────►│
   │                       │                     │                      │
   │                       │        consume_oauth_state(state)          │
   │                       │        (validates + deletes in 1 tx)       │
   │                       │                     │                      │
   │                       │        exchange code → LinkedIn token       │
   │                       │        fetch /v2/userinfo                  │
   │                       │        upsert user row                     │
   │                       │        create JWT (HS256, iat, jti, 24h)   │
   │                       │                     │
   │                       │◄── { access_token } ─│
   │                       │                     │
   │      store token in localStorage            │
   │      GET /api/v1/auth/me → load user profile│
   │── redirect to "/" ────►│                     │
```

### 6.2 Post Generation

```
Browser         Core API           AI Engine          PostgreSQL
   │                │                   │                  │
   │─ POST /api/v1/posts/generate ─────►│                  │
   │   Bearer: JWT                       │                  │
   │   { topic, audience, tone, hook }   │                  │
   │                │                   │                  │
   │           validate JWT             │                  │
   │           extract user_id          │                  │
   │                │                   │                  │
   │                │─ POST /webhooks/v1/generate/post ───►│
   │                │  X-AI-API-Key: ...│                  │
   │                │  { topic, audience, tone, hook,      │
   │                │    top_hooks[] }  │                  │
   │                │                   │                  │
   │                │           load system_post.txt prompt│
   │                │           call LLM (Gemini/OpenAI)  │
   │                │                   │                  │
   │                │◄── { hook, body, cta, hashtags } ───│
   │                │                   │                  │
   │                │── INSERT posts row ─────────────────►│
   │                │   status=draft                       │
   │                │   user_id=...                        │
   │                │                   │                  │
   │◄── 201 { post } ──────────────────│                  │
```

### 6.3 Carousel Studio — Generate & Publish

```
Browser         Core API              AI Engine         Carousel Renderer    LinkedIn
   │                │                     │                    │                │
   ├─ POST /carousel ──────────────────►  │                    │                │
   │                │                     │                    │                │
   │          load post from DB           │                    │                │
   │          load user brand_kit         │                    │                │
   │                │                     │                    │                │
   │                ├─ POST /webhooks/v2/generate/carousel-outline ───────────►│
   │                │                     │                    │                │
   │                │          LLM → 7-slide JSON outline       │                │
   │                │◄── { slides[], cover_hook, cta_text } ───│                │
   │                │                     │                    │                │
   │                ├── POST /render ─────────────────────────►│                │
   │                │   { slides, brand_kit, cover_hook }       │                │
   │                │                     │                    │                │
   │                │                     │      Jinja2 → HTML → WeasyPrint    │
   │                │◄── { pdf_base64 } ──────────────────────────────────────  │
   │                │                     │                    │                │
   │          store PDF at /tmp/carousel_pdfs/{post_id}.pdf                    │
   │          INSERT carousel_assets row (status=rendered)                     │
   │                │                     │                    │                │
   │◄── 201 { asset } ─────────────────────────────────────────────────────────│
   │                │                     │                    │                │
   │ [User previews carousel, clicks Publish]                                  │
   │                │                     │                    │                │
   ├─ POST /carousel/publish ────────────►│                    │                │
   │   { post_text }                      │                    │                │
   │                │                     │                    │                │
   │          decrypt write_access_token  │                    │                │
   │                │                                                           │
   │                ├── POST /rest/documents?action=initializeUpload ──────────►│
   │                │◄── { uploadUrl, document: "urn:li:document:XXX" } ────────│
   │                │                                                           │
   │                ├── PUT {uploadUrl} [PDF bytes] ─────────────────────────►│
   │                │◄── 201 OK ──────────────────────────────────────────────  │
   │                │                                                           │
   │                ├── POST /rest/posts { author, content.media.id, caption }►│
   │                │◄── 201 x-restli-id: "urn:li:share:YYY" ────────────────  │
   │                │                                                           │
   │          UPDATE carousel_assets SET status=published, linkedin_asset_urn  │
   │                │                                                           │
   │◄── 200 { linkedin_post_urn } ─────────────────────────────────────────────│
```

### 6.4 Creator Radar — Comment Generation

```
Browser         Core API              AI Engine              PostgreSQL
   │                │                     │                       │
   ├─ GET /creators/feed ───────────────►│                       │
   │                │                     │                       │
   │          SELECT ingested_posts       │                       │
   │          JOIN tracked_creators       │                       │
   │          WHERE user_id=... ORDER BY ingested_at DESC         │
   │◄── { posts[] } ──────────────────────────────────────────────│
   │                │                     │                       │
   ├─ POST /creators/comments/generate ──►│                       │
   │   { ingested_post_id, tones: [..] }  │                       │
   │                │                     │                       │
   │          load post content from DB   │                       │
   │          load user top hooks         │                       │
   │                │                     │                       │
   │                ├─ POST /webhooks/v1/generate/comment ───────►│
   │                │   { post_content, tone, context }           │
   │                │◄── { comment_text } ────────────────────────│
   │                │   (called once per tone)                    │
   │                │                                             │
   │          INSERT comment_drafts (3 rows, one per tone)       │
   │                │                                             │
   │◄── { drafts[] } ─────────────────────────────────────────────│
   │                │                                             │
   ├─ PATCH /creators/{id}/comments ────►│                       │
   │   { final_text }  ← user edits       │                       │
   │                │                     │                       │
   │          UPDATE comment_drafts       │                       │
   │          INSERT shadow_action_logs   ← DPO data capture      │
   │          (ai_draft vs human_final, edit_similarity_score)    │
   │◄── { draft } ────────────────────────────────────────────────│
```

### 6.5 Smart Fill Calendar

```
Browser         Core API           AI Engine          PostgreSQL
   │                │                   │                  │
   ├─ POST /calendar/smart-fill ───────►│                  │
   │   { pillars[], posts_per_week,      │                  │
   │     preferred_formats[] }           │                  │
   │                │                   │                  │
   │          SELECT posts WHERE user_id AND status='published'
   │          GROUP BY dow, hour         │                  │
   │          → personal heatmap data    │                  │
   │                │                   │ (or benchmark if < 5 posts)
   │                │                   │                  │
   │                ├─ POST /webhooks/v2/generate/week-plan ──────►│
   │                │  { pillars, formats, count, best_slots[] }   │
   │                │                   │                  │
   │                │       LLM → N post outlines          │
   │                │◄── { posts[] } ───│                  │
   │                │                   │                  │
   │          for each post draft:       │                  │
   │            INSERT posts row         │                  │
   │            scheduled_at = best_slot[i % len(best_slots)]
   │◄── 201 { posts[] } ───────────────────────────────────────────│
```

---

## 7. Authentication & Security Architecture

### JWT Flow

```
LinkedIn OAuth → Core API creates JWT:
  {
    "sub": "<user_uuid>",
    "iat": <unix_timestamp>,
    "exp": <iat + 86400>,    ← 24 hours
    "jti": "<uuid4>"         ← unique token ID
  }
  Signed with: HMAC-SHA256(JWT_SECRET_KEY)
```

**Token lifecycle:**
1. Issued at OAuth callback → sent to browser in JSON response body
2. Browser stores in `localStorage` (key: `linkedin_copilot_token`)
3. Every API request attaches `Authorization: Bearer <token>` via axios interceptor
4. Core API validates signature + expiry on every request
5. On 401 → axios response interceptor clears localStorage + redirects to `/login`

### Two-Account OAuth Architecture

```
Read Account (login + ingestion):
  App: read_app (client_id A)
  Scopes: openid, profile, email, w_member_social
  Token: stored as access_token_encrypted on User row
  Used by: AuthService, CreatorService (ingestion worker)

Write Account (carousel publish):
  App: write_app (client_id B)
  Scopes: openid, profile, email, w_member_social
  Token: stored as write_access_token_encrypted on User row
  Used by: CarouselService.publish_to_linkedin()
```

### CSRF Protection for OAuth

```
Browser calls GET /auth/linkedin
  → Core API generates state_token = secrets.token_urlsafe(32)
  → Inserts OAuthState { state_token, user_id=None, expires_at=now+10min }
  → Returns auth_url with state embedded

LinkedIn callback arrives: GET /auth/linkedin/callback?code=X&state=Y
  → Core API calls consume_oauth_state(state)
  → ATOMIC: SELECT + DELETE in one transaction
  → If missing or expired → 400 Bad Request
  → If valid → continues with code exchange
```

Key property: **the state token is single-use and DB-persisted** — not in memory, so it survives server restarts and works across multiple workers.

### Encryption at Rest

All LinkedIn tokens stored via Fernet symmetric encryption:

```python
# Write:
encrypted = Fernet(FERNET_KEY).encrypt(token.encode()).decode()
user.write_access_token_encrypted = encrypted

# Read (in CarouselService):
token = Fernet(FERNET_KEY).decrypt(user.write_access_token_encrypted.encode()).decode()
```

The plaintext token **never touches the database**.

### Internal Service Auth

```
Core API → AI Engine:
  Header: X-AI-API-Key: <AI_ENGINE_API_KEY>
  AI Engine validates in dependency: verify_api_key()
  Returns 403 if missing or wrong

Core API → Carousel Renderer:
  No auth — only reachable within Docker network
```

---

## 8. AI Subsystem Design

### AI Engine Internal Architecture

```
apps/ai_engine/app/
├── services/
│   ├── llm_service.py            ← Core LLM abstraction (provider-agnostic)
│   ├── post_service.py           ← Post generation logic
│   ├── comment_service.py        ← Comment draft logic
│   ├── idea_service.py           ← Idea generation
│   ├── virality_score_service.py ← Scoring rubric + parsing
│   ├── carousel_outline_service.py ← 7-slide structure generation
│   ├── week_plan_service.py      ← Smart Fill calendar planning
│   ├── extraction_service.py     ← LinkedIn post content extraction
│   └── classifier_service.py    ← Intent/lead classification
├── prompts/
│   ├── system_post.txt
│   ├── system_comment.txt
│   ├── system_idea.txt
│   ├── system_llm_judge.txt      ← LLMOps evaluator
│   └── ...                       ← 15 prompt files total
└── clients/                      ← LLM provider SDK wrappers
```

### LLM Provider Abstraction

```python
# llm_service.py — simplified
class LLMService:
    def __init__(self, settings):
        if settings.llm_provider == "gemini":
            self.client = GeminiClient(settings.gemini_api_key)
        elif settings.llm_provider == "vertex":
            self.client = VertexClient(settings.gcp_project_id, ...)
        elif settings.llm_provider == "ollama":
            self.client = OllamaClient(settings.ollama_url, settings.ollama_model)
        else:  # openai (default)
            self.client = OpenAIClient(settings.openai_api_key)

    async def complete(self, system_prompt, user_message) -> str:
        return await self.client.chat(system_prompt, user_message)
```

Switching LLM provider requires only an env var change — no code changes.

### Virality Scoring Rubric

The AI Engine scores post drafts across 5 dimensions:

| Dimension | Weight | Description |
|---|---|---|
| Hook Quality | 25% | First line distinctiveness, pattern-interrupt, specificity |
| Value Density | 25% | Insight-to-word ratio, actionability |
| Emotional Resonance | 20% | Story arc, vulnerability, relatability |
| CTA Strength | 15% | Clarity of desired action, urgency |
| Format Score | 15% | Whitespace, readability, hashtag usage |

Returns: `{ total_score: 82, breakdown: {...}, hook_alternatives: ["...", "...", "..."] }`

---

## 9. LLMOps Feedback Loop

The platform implements a **Direct Preference Optimization (DPO) data collection pipeline** for future model fine-tuning.

```
AI generates draft → User edits → Final version used
       │                  │               │
       └──────────────────┼───────────────┘
                          │
                 shadow_action_logs
                 {
                   user_id,
                   action_type: "comment_reply",
                   ai_draft_content: "original AI text",
                   human_final_content: "what the user sent",
                   edit_similarity_score: 0.82  ← Levenshtein ratio
                 }
                          │
                          ▼
              LLM-as-a-Judge (via AI Engine /evals/judge)
                 {
                   hallucination_score: 95,
                   tone_adherence_score: 88,
                   safety_compliance_score: 100,
                   judge_rationale: "..."
                 }
                          │
                    llm_evaluations table
                          │
                          ▼
              /llmops dashboard — aggregate quality metrics
```

**DPO dataset structure:**
- `edit_similarity_score = 1.0` → human approved without edits → preferred sample
- `edit_similarity_score = 0.0` → human completely rewrote → rejected sample
- This dataset is the raw material for fine-tuning a smaller edge model

---

## 10. API Design Conventions

### Versioning
- **V1** (`/api/v1/`) — stable, production-ready endpoints
- **V2** (`/api/v2/`) — newer capabilities (carousel, heatmap, virality, smart fill)
- V2 endpoints are additive — V1 is not modified

### Response shapes
```json
// List endpoint
{ "items": [...], "total": 42, "page": 1, "per_page": 20 }

// Single resource
{ "id": "uuid", "created_at": "ISO8601", ... }

// Error
{ "detail": "Human-readable error message" }
```

### HTTP status conventions
| Status | Meaning |
|---|---|
| `200` | Success (or update) |
| `201` | Created |
| `204` | Deleted (no body) |
| `400` | Bad request / invalid state |
| `401` | Not authenticated |
| `403` | Authenticated but not authorized |
| `404` | Resource not found |
| `502` | Upstream service (LinkedIn API or AI Engine) failed |

### Rate limits (configurable in `config.yaml`)
```yaml
rate_limits:
  post_generation:
    max_per_day_free: 5
    max_per_day_pro: 50
    max_per_minute: 10
  comment_generation:
    max_per_day_free: 10
    max_per_day_pro: 100
    max_per_minute: 15
```

---

## 11. Deployment Topology

### Development

```
Host machine
├── docker compose up
│   ├── web:3000         ← Next.js (builds from apps/web/)
│   ├── core_api:8000    ← FastAPI (builds from apps/core_api/)
│   ├── ai_engine:8001   ← FastAPI (builds from apps/ai_engine/)
│   ├── carousel_renderer:8002
│   └── postgres:5432 (volume: postgres_dev_data)
```

### Production

```
VPS / Cloud VM
├── docker compose -f docker-compose.prod.yml up -d
│   ├── web:3000         ← GHCR image (no port exposed to host)
│   ├── core_api:8000    ← GHCR image (no port exposed to host)
│   ├── ai_engine:8001   ← GHCR image (no port exposed to host)
│   ├── carousel_renderer:8002
│   └── postgres:5432 (volume: postgres_prod_data)
│
├── nginx / Cloudflare (external)
│   └── → proxy pass to web:3000
│
└── Cloudflare Tunnel (optional, for HTTPS without public IP)
    └── trycloudflare.com domain → web:3000
```

**Data isolation:** Each environment uses a dedicated named volume:

| Environment | Volume |
|---|---|
| `docker-compose.yml` (dev) | `postgres_dev_data` |
| `docker-compose.local.yml` (staging) | `postgres_staging_data` |
| `docker-compose.prod.yml` (prod) | `postgres_prod_data` |

### Image build & publish

```bash
# Build and push to GHCR
docker build -t ghcr.io/org/core_api:v1.2.7 apps/core_api/
docker push ghcr.io/org/core_api:v1.2.7

# Deploy
IMAGE_TAG=v1.2.7 docker compose -f docker-compose.prod.yml pull
IMAGE_TAG=v1.2.7 docker compose -f docker-compose.prod.yml up -d
```

---

## 12. Design Decisions & Trade-offs

### No Redis

**Decision:** Remove Redis from the stack. Use PostgreSQL for all state (sessions, oauth states, queues).

**Rationale:**
- Single-operator trial deployment — Redis adds operational overhead with minimal benefit
- OAuth states work fine in Postgres with TTL + periodic cleanup
- No background task queue needed yet (ingestion is a separate standalone service)

**Trade-off:** At very high scale (multi-tenant SaaS), Redis would be reintroduced for rate limiting, session caching, and task queues.

---

### No Alembic

**Decision:** Use `Base.metadata.create_all()` at startup instead of migration files.

**Rationale:**
- Single developer, rapid schema iteration phase
- Alembic migrations add friction during early product development

**Trade-off:** Schema changes require either manual DDL on a live DB or a full data wipe. For production data protection, this approach requires care. An Alembic migration system should be introduced before multi-user growth.

**Current workaround:** Document manually-required DDL changes (e.g., the `shadow_action_logs` FK CASCADE) in the Operator Guide's troubleshooting section.

---

### JWT in localStorage (not HttpOnly cookie)

**Decision:** Store JWT in `localStorage` and send as Bearer token.

**Rationale:**
- Internal tool — single operator, controlled environment
- Simpler frontend implementation
- No CSRF concerns (Bearer tokens are not auto-sent by browser)

**Trade-off:** Vulnerable to XSS exfiltration of the token. Acceptable for internal single-user tool; switch to HttpOnly cookie before multi-user public launch.

---

### Two LinkedIn Apps (Read + Write)

**Decision:** Maintain separate OAuth apps for read-flow (login/ingestion) and write-flow (carousel publish).

**Rationale:**
- LinkedIn API `w_member_social` scope is sensitive — minimize which accounts hold it
- Separation allows read and write tokens to expire, rotate, and be revoked independently
- Cleaner UX: user logs in with read app, separately consents to posting with write app

**Trade-off:** More configuration required (2 app client IDs/secrets).

---

### No Autonomous Posting

**Decision:** All content actions are human-triggered. No scheduled auto-publisher.

**Rationale:**
- LinkedIn detects and bans accounts that exhibit bot-like scheduled posting
- Human review before publish is a core product principle

**Safety limits enforced:**
```yaml
safety:
  max_posts_per_day: 10
  max_comments_per_day: 30
  min_delay_between_actions_seconds: 30
```

---

### Pluggable LLM Provider

**Decision:** Abstract all LLM calls behind a provider interface in the AI Engine.

**Rationale:**
- Provider pricing and capability landscape is evolving rapidly
- Allows instant switch: `LLM_PROVIDER=gemini` vs `openai` vs `vertex` vs `ollama`
- Ollama enables fully local inference for air-gapped or cost-sensitive deployments

**Current default:** Gemini 2.0 Flash (best cost/performance at time of writing)
