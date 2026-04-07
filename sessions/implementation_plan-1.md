# Infrastructure Hardening — 6 Priority Fixes

## Overview
Addressing 6 infrastructure gaps in priority order. All changes are backward-compatible and targeted.

---

## Fix 1 — `datetime.utcnow()` → `datetime.now(UTC)` (XS)
**Files:** `models/sales.py`, `models/llmops.py`, `models/enterprise.py`, `models/talent.py`, `models/analytics.py`, `models/career.py`, `services/virality_service.py`, `services/creator_service.py`, `workers/`

Replace `datetime.utcnow` with `lambda: datetime.now(timezone.utc)` in all ORM column defaults, and direct calls with `datetime.now(timezone.utc)`.

---

## Fix 2 — Structured Error Codes (S)
**Files:** `middleware/error_handler.py`, `controllers/v2_carousel_controller.py`, new `schemas/errors.py`

Create an `AppError` exception class that carries a machine-readable `code` string alongside the human message. Update the global error handler to emit `{ "code": "WRITE_TOKEN_EXPIRED", "detail": "..." }`. Define an enum of all error codes.

---

## Fix 3 — LinkedIn OAuth Token Refresh (M)
**Files:** `services/auth_service.py`, `services/carousel_service.py`, `models/user.py`

- Store `refresh_token_encrypted` and `token_expires_at` during the OAuth callback
- `auth_service.py`: add `refresh_linkedin_token(user)` method
- `carousel_service.py`: pre-flight check before publish — if `token_expires_at < now + 5min`, call refresh; if no refresh token, raise `AppError("WRITE_TOKEN_EXPIRED")`

---

## Fix 4 — Alembic Migration Setup (M)
**Files:** `apps/core_api/alembic.ini`, `apps/core_api/alembic/`, `apps/core_api/app/db.py` (new engine module)

- `pip install alembic` (already in pyproject or add it)
- `alembic init` → configure `env.py` to use the async engine
- Generate initial baseline migration from current models
- Add `alembic upgrade head` to docker container startup

---

## Fix 5 — Ingestion Worker in Docker Compose (S)
**Files:** `docker-compose.yml`, `docker-compose.prod.yml`, `docker-compose.local.yml`

The `bulk_ingestion_worker.py` already exists in `apps/core_api/app/workers/`. Add it as a separate service using the same `core_api` image but with a different command override: `python -m app.workers.bulk_ingestion_worker`. Uses the same DB and env, just runs as a worker process.

---

## Fix 6 — PDF Storage: Host Volume (persistent) + GCS prep (S)
**Files:** `apps/core_api/app/services/carousel_service.py`, `apps/core_api/app/config.py`, `.env.example`

- The `docker-compose.yml` already mounts `./tmp/carousel_pdfs:/tmp/carousel_pdfs` ✅
- `docker-compose.prod.yml` also already has it ✅
- **Gap**: the mount is bind-mount to `./tmp/` on the host — this IS persistent across container restarts. The issue was the analysis was wrong about this.
- **Real gap**: `GCS_BUCKET_NAME` not configured, and `_store_pdf` doesn't have a GCS path. Add an optional GCS upload path: if `GCS_BUCKET_NAME` is set → upload to GCS and return `gs://` URL; else fall back to the local volume.

---

## Verification
Run `python -m pytest tests/ -q` — expect 129 passed, 0 warnings about utcnow.
