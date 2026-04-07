# Changelog — LinkedIn-as-a-Service

Chronological history of what was built and validated in each major sprint/version.

---

## v1.2.7 — Project Cleanup (2026-04-04)
- Removed all Appium and Playwright dependencies from `core_api`
- Deleted `appium_read_service`, `adb_client`, `ingestion_worker`, `viral_discovery_worker`, `playwright_scraper`, `viral_engine`
- Removed `playwright>=1.42.0` from `pyproject.toml` and `Dockerfile`
- Migrated read-flow ingestion exclusively to `linkedin-read-flow` (read-only account)
- Deleted `others/` directory (legacy Appium prototypes)
- Removed 3 obsolete test files; retained 129 clean tests
- Created archive branches: `archive/main-2026-04-04`, `archive/feature-ready-2026-04-04`
- Reorganized docs: RCA files moved to `docs/rca/`, standards merged, junk removed

---

## v1.2.6 — LinkedIn V2 Auth Stabilization (2026-04-04)
- Stabilized LinkedIn OAuth V2 token flow
- Fixed PDF persistence issue (ephemeral `/tmp` → persistent Docker volume)
- Fernet token injection scripts added for local dev
- PM2 configuration for 24/7 service persistence on Mac Mini

---

## v1.2.5 — Frontend API Path Fix
- Switched all frontend API calls to relative paths to avoid absolute URL collisions in proxied environments
- Fixed routing conflict between Next.js rewrites and direct API calls

---

## v1.2.4 — API Singleton & Proxy
- Introduced `apiV2` singleton in `apps/web/src/lib/api.ts`
- Added Next.js `/api/v2` proxy layer for strict routing
- Eliminated hardcoded `localhost:8000` references from frontend

---

## v1.2.3 — Docker Image Tags
- Corrected GHCR image tags to use `linkedin-engagement-ai` repository name
- Added multi-arch build support (`linux/amd64` + `linux/arm64`)

---

## v1.2.2 — Playwright Dependencies
- Added Playwright system dependencies to `core_api` Dockerfile *(now removed in v1.2.7)*

---

## v1.2.1 — Build Fixes
- Installed `git` in `core_api` Dockerfile to support pip git-based packages

---

## v1.2.0 — V2 Release
- Full V2 feature set released: Carousel Studio, Virality Scoring, Heatmap, Smart Fill
- LinkedIn OAuth V2 write flow integrated via `linkedin-write-flow-poc`
- New microservice: `carousel_renderer` (WeasyPrint PDF generation on port 8002)
- 186 tests passing

---

## V2 Sprint 4 — Carousel Studio Stabilization
- Fixed LinkedIn OAuth redirect URI mismatch (dynamic Host-based resolver)
- Fixed PDF not found error (persistent Docker volume mount)
- Fixed `VERSION_MISSING` LinkedIn API error (added `LinkedIn-Version: 202603` header)
- Fixed V2 API routing conflict (Next.js proxy + prefix collision)
- All 12 backend endpoints passing in Swagger tests

---

## V2 Sprint 3 — Virality Scoring Engine
- AI pre-scores every draft post 1–100 with hook alternatives and breakdown
- Background flywheel learning from real engagement metrics
- `POST /api/v2/posts/{id}/score` endpoint live

---

## V2 Sprint 2 — Smart Fill Calendar
- AI auto-generates a full week of draft posts from user-defined pillars
- Slots posts at optimal times from heatmap analysis
- `POST /api/v2/calendar/smart-fill` endpoint live

---

## V2 Sprint 1 — Posting Time Heatmap
- 7-day engagement heatmap from real post data (global benchmark fallback)
- `best_slots` and `worst_slots` recommendations
- `GET /api/v2/analytics/heatmap` endpoint live

---

## Phase 1 Complete — Core Platform (Sprints 1–3)

### Sprint 1: Foundation
- Monorepo scaffold: Next.js frontend, FastAPI `core_api`, FastAPI `ai_engine`
- PostgreSQL + `asyncpg` database with Alembic migrations
- JWT authentication (create/decode, secure endpoints)
- YAML-based config system (zero hardcoding)
- Docker Compose local and production stacks
- GitHub Actions CI/CD with GHCR image registry

### Sprint 2: AI Post Generation
- `POST /api/v1/posts/generate` → AI Engine webhook
- LLM structured output: `{hook, body_content, call_to_action}`
- Framework-specific prompts (story, contrarian, listicle, etc.)
- Tenacity retry with exponential backoff
- Post CRUD: create, list, get, update, delete
- Content Calendar UI with drag-and-drop scheduling

### Sprint 3: Comment Copilot & Creator Radar
- Creator tracking CRUD + ingestion pipeline
- Trinity strategy comments: insightful, contrarian, supportive
- `POST /api/v1/copilot/generate` → AI Engine webhook
- LLMOps Data Flywheel: edit similarity tracking via `difflib`
- Shadow Action Log for future DPO fine-tuning
- Action Desk feed UI (Copy & Go workflow)

### E2E Testing Results (Phase 1)
- `POST /posts/generate` + `GET /posts` → ✅ 201/200
- `POST /radar/creators` + `GET /copilot/feed` → ✅ 201/200
- JWT auth guard on all protected endpoints → ✅
- Docker multi-service stack → ✅
