# LinkedIn-as-a-Service

> AI-powered LinkedIn growth platform — content generation, comment copilot, carousel studio, and virality scoring.

**Current version:** v1.2.7 | **Branch:** `fresh-start` | **Stack:** FastAPI · Next.js · PostgreSQL · Gemini · Docker

---

## Architecture

```
Browser (Next.js :3000)
      │  JWT auth
      ▼
Core API (:8000)  ──── AI Engine (:8001)        ← internal, X-AI-API-Key gated
      │                     │
      │              Vertex AI / Gemini
      │              Ollama (local fallback)
      │
      ├── PostgreSQL (primary store)
      ├── Carousel Renderer (:8002)              ← WeasyPrint PDF generation
      └── linkedin-read-flow                     ← read-only ingestion (background worker)
```

### Services

| Service | Port | Role |
|---------|------|------|
| `apps/web` | 3000 | Next.js frontend — post studio, radar, calendar, carousel |
| `apps/core_api` | 8000 | FastAPI backend — auth, CRUD, background workers, webhooks |
| `apps/ai_engine` | 8001 | LLM microservice — structured output via Gemini / Ollama |
| `apps/carousel_renderer` | 8002 | PDF generation via WeasyPrint |

---

## Features

### V1 — Content & Comment Engine
- **Post Generation** — AI ghostwriter with framework strategies (contrarian, story, listicle, etc.)
- **Creator Radar** — track creators, ingest their posts automatically
- **Comment Copilot** — 3 AI strategies per post: insightful / contrarian / supportive
- **LLMOps Flywheel** — edit similarity tracking → future DPO fine-tuning

### V2 — Growth Intelligence
- **Carousel Studio** — AI-generated swipeable PDF posts, published via LinkedIn API
- **Virality Scoring** — pre-post AI score 1–100 with hook alternatives + breakdown
- **Posting Time Heatmap** — smart time recommendations from real engagement data
- **Smart Fill Calendar** — auto-generate a full week of posts from content pillars

---

## Ingestion

Feed data is pulled via **`linkedin-read-flow`** (read-only dedicated account). The `bulk_ingestion_worker` runs as a background thread on app start, authenticating via:

1. `LINKEDIN_READ_LI_AT` cookie (preferred)
2. `LINKEDIN_READ_EMAIL` + `LINKEDIN_READ_PASSWORD` (auto-fallback)
3. Telegram alert sent on CAPTCHA/auth failure for manual intervention

---

## Local Development

### Prerequisites
- Python 3.12+
- Node.js 20+
- PostgreSQL running locally
- Ollama (optional, for local LLM fallback)

### Boot

```bash
# Core API
cd apps/core_api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# AI Engine
cd apps/ai_engine
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Carousel Renderer
cd apps/carousel_renderer
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# Frontend
cd apps/web
npm install && npm run dev
```

### Environment (`apps/core_api/.env`)

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/linkedin_saas
FERNET_KEY=your_fernet_key

# LinkedIn read-only account (ingestion)
LINKEDIN_READ_LI_AT=your_li_at_cookie
LINKEDIN_READ_EMAIL=readonly@email.com
LINKEDIN_READ_PASSWORD=your_password

# Telegram alerts (optional)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

```env
# apps/ai_engine/.env
GEMINI_API_KEY=your_key
AI_ENGINE_API_KEY=your_internal_key
VERTEX_PROJECT_ID=your_gcp_project
```

---

## Production (Docker)

```bash
# Build and start all services
docker compose -f docker-compose.prod.yml up -d --build

# First-time DB init
docker compose -f docker-compose.prod.yml exec core_api python -m scripts.init_master_db

# Check health
docker compose -f docker-compose.prod.yml ps -a
curl http://localhost:8000/health
```

> See `docs/local_prod_operations.md` for full operator runbook.

---

## Testing

```bash
cd apps/core_api
.venv/bin/python -m pytest tests/ -v
# 129 tests — auth, posts, creators, comment feedback, full V2 feature coverage
```

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [CHANGELOG.md](docs/CHANGELOG.md) | Version history & sprint log |
| [DEVELOPER_STANDARDS.md](docs/DEVELOPER_STANDARDS.md) | Backend & frontend engineering rules |
| [master_project_blueprint.md](docs/master_project_blueprint.md) | 7-phase product roadmap |
| [v2_developer_reference.md](docs/v2_developer_reference.md) | V2 authoritative technical reference |
| [v2_architecture.md](docs/v2_architecture.md) | V2 design spec |
| [deployment_strategy.md](docs/deployment_strategy.md) | Cloud & infra deployment |
| [local_prod_operations.md](docs/local_prod_operations.md) | Mac Mini operator runbook |
| [admin_operator_guide.md](docs/admin_operator_guide.md) | Admin guide |
| [end_user_guide.md](docs/end_user_guide.md) | End user guide |
| [docs/rca/README.md](docs/rca/README.md) | RCA index — all production incidents |

---

## Engineering Rules (Non-Negotiable)

| Rule | Detail |
|------|--------|
| No hardcoding | All config via `.env` or `config.yaml` |
| Strict JSON mode | All LLM calls use structured output |
| LLM timeout | All AI calls wrapped in `asyncio.wait_for(timeout=30)` |
| Human-in-the-loop | Every LinkedIn action requires user approval |
| No aggressive scraping | Only `linkedin-read-flow` for ingestion |
| asyncpg timeout | Always `connect_args={"timeout": 10}` |

---

## Archive & Safety

| Branch | Purpose |
|--------|---------|
| `fresh-start` | Active development (Appium/Playwright removed) |
| `archive/main-2026-04-04` | Frozen snapshot of main before cleanup |
| `archive/feature-ready-2026-04-04` | Frozen snapshot of feature-ready before cleanup |
