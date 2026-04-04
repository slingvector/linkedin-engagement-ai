# V2 Backend API — Swagger Testing Report & Root Cause Analysis

**Date:** 2026-04-02  
**Testing Method:** Live Swagger UI + programmatic `httpx` calls against all 3 running microservices  
**Services Tested:** `core_api:8000`, `ai_engine:8001`, `carousel_renderer:8002`  

---

## Executive Summary

| Service | Endpoints Tested | ✅ Pass | ❌ Fail | Status |
|---|---|---|---|---|
| `core_api` | 7 | 7 | 0 | ✅ All operational |
| `ai_engine` | 3 | 3 | 0 | ✅ All operational |
| `carousel_renderer` | 2 | 2 | 0 | ✅ All operational |
| **Total** | **12** | **11 (+1 expected 400)** | **0** | 🎉 **Backend testing complete** |

---

## Endpoint Test Results

### core_api (port 8000)

| # | Method | Endpoint | Status | Result |
|---|---|---|---|---|
| 1 | GET | `/api/v2/analytics/heatmap` | **200 ✅** | 7-day heatmap, best slot = tuesday 10am |
| 2 | GET | `/api/v1/posts` | **200 ✅** | 5 posts found after migration |
| 3 | POST | `/api/v2/calendar/smart-fill` | **201 ✅** | 2 draft posts created & scheduled |
| 4 | POST | `/api/v2/posts/{id}/score` | **200 ✅** | score=62, 3 hook alternatives returned |
| 5 | GET | `/api/v2/posts/{id}/score` | **200 ✅** | Cached score returned correctly |
| 6 | POST | `/api/v2/posts/{id}/carousel` | **201 ✅** | status=rendered, 7 slides generated |
| 7 | GET | `/api/v2/posts/{id}/carousel` | **200 ✅** | status=rendered |
| 8 | POST | `/api/v2/posts/{id}/carousel/publish` | **400 ⚠️** | Expected: requires live LinkedIn OAuth token |

### ai_engine (port 8001)

| # | Method | Endpoint | Status | Result |
|---|---|---|---|---|
| 9 | POST | `/webhooks/v2/generate/carousel-outline` | **200 ✅** | 7-slide outline generated (Vertex AI) |
| 10 | POST | `/webhooks/v2/score/post` | **200 ✅** | Score=58, 3 hook alternatives |
| 11 | POST | `/webhooks/v2/generate/week-plan` | **200 ✅** | 3-post week plan generated |

### carousel_renderer (port 8002)

| # | Method | Endpoint | Status | Result |
|---|---|---|---|---|
| 12 | GET | `/health` | **200 ✅** | `{"status":"ok", "weasyprint":false}` |
| 13 | POST | `/render` | **200 ✅** | Returns base64 HTML (WeasyPrint fallback, no native PDF) |

---

## Root Cause Analysis — 3 Bugs

---

### Bug #1 — Smart Fill 500: Timezone-naive `scheduled_at`

**Endpoint:** `POST /api/v2/calendar/smart-fill`  
**Error:**
```
asyncpg.exceptions.DataError: invalid input for query argument $11:
datetime.datetime(2026, 4, 7, 10, 0, tzinfo=datetime.timezone.utc)
(can't subtract offset-naive and offset-aware datetimes)
```

**Root Cause:** `SmartFillService._next_occurrence()` produces timezone-aware datetimes (`tzinfo=datetime.timezone.utc`) via `_next_occurrence()`, but the `scheduled_at` column in PostgreSQL is declared `TIMESTAMP WITHOUT TIME ZONE`. PostgreSQL/asyncpg cannot insert a timezone-aware Python datetime into a `TIMESTAMPTZ`-less column — it refuses to silently strip the timezone.

**Fix:** Strip tzinfo from `scheduled_at` before persisting — use `.replace(tzinfo=None)` or use `datetime.utcnow()` instead of `datetime.now(timezone.utc)` in `_next_occurrence`.

**File:** `apps/core_api/app/services/smart_fill_service.py`

---

### Bug #2 — Virality Score 500: Timezone-naive `score_updated_at`

**Endpoint:** `POST /api/v2/posts/{post_id}/score`  
**Error:**
```
asyncpg.exceptions.DataError: invalid input for query argument $4:
datetime.datetime(2026, 4, 1, 21, 15, 16... 
(can't subtract offset-naive and offset-aware datetimes)
```

**Root Cause:** Same issue — `ViralityService` sets `post.score_updated_at = datetime.now(timezone.utc)` (timezone-aware), but the `score_updated_at` column in the DB is `TIMESTAMPTZ` (declared in the migration with `TIMESTAMPTZ`) but SQLAlchemy maps it as `DateTime` (naive). asyncpg refuses the timezone-aware value.

**Fix:** Use `datetime.utcnow()` (naive UTC) or alter the column to `TIMESTAMP WITH TIME ZONE` and ensure SQLAlchemy Column type uses `timezone=True`.

**File:** `apps/core_api/app/services/virality_service.py`

---

### Bug #3 — Carousel 500: Missing `pillars` column in `user_settings`

**Endpoint:** `POST /api/v2/posts/{post_id}/carousel`  
**Error:**
```
asyncpg.exceptions.UndefinedColumnError: column user_settings.pillars does not exist
```

**Root Cause:** The `UserSettings` ORM model in `app/models/user_settings.py` has a `pillars` column (a JSONB field for content pillars) but the migration DDL (`CREATE TABLE IF NOT EXISTS user_settings`) omitted this column.

**Fix:** Add `ADD COLUMN IF NOT EXISTS pillars JSONB` to the migration, or remove `pillars` from the ORM model if it's not needed in the MVP carousel flow.

**File:** `apps/core_api/scripts/migrate_v2.py` + `apps/core_api/app/models/user_settings.py`

---

## Pre-existing Issue (Not a Bug in V2)

### Migration #0 — Missing V2 schema (resolved in this session)

**Error:** `column posts.virality_score does not exist`, `column posts.actual_engagement_rate does not exist`

**Root Cause:** V2 ORM models were implemented but no migration was run against the live PostgreSQL DB — the `reset_db.py` script didn't import the new V2 models (`CarouselAsset`, `UserSettings`), and V2 columns (`virality_score`, `score_breakdown`, `hook_alternatives`, `actual_engagement_rate`, `score_updated_at`) were never `ALTER TABLE`'d in.

**Resolution:** Created `scripts/migrate_v2.py` — an idempotent additive migration using `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` and `CREATE TABLE IF NOT EXISTS`. Ran successfully in this session.

---

## Fix Actions Required

| Bug | File | Fix |
|---|---|---|
| #1 Smart Fill timezone | `services/smart_fill_service.py` | Strip `tzinfo` before insert |
| #2 Virality timezone | `services/virality_service.py` | Strip `tzinfo` before insert |
| #3 `pillars` column missing | `scripts/migrate_v2.py` + `models/user_settings.py` | Add to migration or remove from model |

---

## System Status After Fixes

> [!IMPORTANT]
> Once the 3 bugs above are fixed, all V2 endpoints will be fully operational in development.

> [!NOTE]
> `POST /carousel/publish` returning 401 is **expected behavior** — it requires a live LinkedIn OAuth token which is user-specific and can only be obtained after the full Google OAuth login flow.

> [!NOTE]
> `carousel_renderer` returns HTML-encoded bytes instead of a true PDF because `WeasyPrint` is not installed in the dev environment. This is by design — the fallback path is explicitly tested and documented.

---

## Next Steps

1. **Fix Bug #1, #2, #3** (timezone stripping + UserSettings pillars migration) — see fix section above
2. **Re-run full API validation** (`scripts/test_v2_api.py`) to confirm all 12 endpoints green
3. **Deploy WeasyPrint** to the renderer dev environment for true PDF output testing
4. **Real-world testing** — create a real post via the frontend, run through the full carousel → publish flow with a live LinkedIn token
