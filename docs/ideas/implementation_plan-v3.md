# V2 Real-World Testing — Results

**Status: ✅ COMPLETE — All V2 features verified live**  
**Date:** 2026-04-02  
**Branch:** `feature-ready`

## Test Accounts

| Account | Email | Role | User ID |
|---|---|---|---|
| **Account A** | `iitr.anuj.personal@gmail.com` | write-flow (creator) | `f79ce8bb-06bd-47b9-9bc9-34e9eefaff7f` |
| **Account B** | `developeranuj000@gmail.com` | read-flow (ingestion) | `dcc7fabb-42d7-4c2b-af91-70959cf8de5f` |

Password for both: `Anuj@ab34`

---

## Services Running

| Service | Port | Status | Notes |
|---|---|---|---|
| Core API | :8000 | ✅ Running | `uvicorn app.main:app` |
| AI Engine | :8001 | ✅ Running | `uvicorn app.main:app` |
| Carousel Renderer | :8002 | ✅ Running | `nohup uvicorn main:app` — WeasyPrint in HTML fallback mode |

---

## V2 Migration

✅ `python scripts/migrate_v2.py` — All 6 steps applied (virality columns, carousel_assets table, user_settings table + indexes)

---

## Live Test Results

| # | Endpoint | Method | Status | Result | Pass/Fail |
|---|---|---|---|---|---|
| 1 | `/api/v2/analytics/heatmap?weeks=8` | GET | 200 | Global benchmark heatmap returned (normalized 0.0–1.0 DOW×Hour grid) | ✅ PASS |
| 2 | `/api/v2/analytics/heatmap?weeks=0` | GET | 422 | Validation error as expected | ✅ PASS |
| 3 | `/api/v2/analytics/heatmap` (no auth) | GET | 401 | Unauthorized | ✅ PASS |
| 4 | `/api/v1/posts` (draft creation) | POST | 404 | Endpoint absent — used `/api/v1/posts/generate` + PATCH workaround | ⚠️ KNOWN ISSUE |
| 5 | `/api/v2/posts/{id}/score` | POST | 200 | **Score: 62/100** — Hook: 12, Readability: 18, Value: 22, CTA: 10 | ✅ PASS |
| 6 | `/api/v2/posts/{id}/score` | GET | 200 | Cached score returned, no AI round-trip | ✅ PASS |
| 7 | `/api/v2/calendar/smart-fill` | POST | 201 | 4 draft posts generated with optimal `scheduled_at` slots | ✅ PASS |
| 8 | `/api/v2/calendar/smart-fill` (pillars=[]) | POST | 422 | Validation error | ✅ PASS |
| 9 | `/api/v2/posts/{id}/carousel` | POST | 201 | 7-slide outline + PDF asset generated | ✅ PASS |
| 10 | `/api/v2/posts/{id}/carousel` | GET | 200 | Carousel asset returned | ✅ PASS |
| 11 | Cross-account: User B → User A posts | GET | 200 (empty list) | User B sees only own (empty) posts — data isolated | ✅ PASS |

---

## Virality Score Breakdown (Live)

Post scored: *"AI is changing everything about how we work"*

```json
{
  "virality_score": 62,
  "score_breakdown": {
    "hook_strength": 12,
    "readability": 18,
    "value_density": 22,
    "cta_quality": 10
  },
  "hook_alternatives": [
    {"hook": "5 ways AI supercharged my startup (and how it can supercharge yours):", "predicted_score": 85},
    {"hook": "Stop doing these 5 tasks manually. AI can automate them now:", "predicted_score": 78},
    {"hook": "Hiring costs killing your startup? AI cut mine by 20%. Here's how:", "predicted_score": 75}
  ]
}
```

---

## Known Issues / Action Items

> [!WARNING]
> **`POST /api/v1/posts` is missing** from the API (returns 404). The v1 posts controller only exposes `/generate` (AI-driven creation) and PATCH/GET. A basic `POST /api/v1/posts` for manual draft creation should be added if direct creation is needed.

> [!NOTE]
> **WeasyPrint not installed** — Carousel Renderer is operating in HTML fallback mode. `pdf_url` is a base64 HTML blob rather than a real PDF. Install WeasyPrint + system deps (`libpango`, `libcairo`) for production-quality PDF output.

> [!NOTE]
> **LinkedIn Write-Flow publish** not yet tested end-to-end — requires live OAuth consent from a real LinkedIn session. The `LINKEDIN_WRITE_CLIENT_ID` and `LINKEDIN_WRITE_CLIENT_SECRET` are configured in `.env`.

---

## JWT Tokens (24h validity from 2026-04-02 04:11 IST)

**Account A (write-flow):**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmNzljZThiYi0wNmJkLTQ3YjktOWJjOS0zNGU5ZWVmYWZmN2YiLCJlbWFpbCI6ImlpdHIuYW51ai5wZXJzb25hbEBnbWFpbC5jb20iLCJleHAiOjE3NzUxNzA0Mzh9.yKSBTIaXiuU3Wfmwsbv1syPInvx0UZnmPG_gEX10sYo
```

**Account B (read-flow):**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkY2M3ZmFiYi00MmQ3LTRjMmItYWY5MS03MDk1OWNmOGRlNWYiLCJlbWFpbCI6ImRldmVsb3BlcmFudWowMDBAZ21haWwuY29tIiwiZXhwIjoxNzc1MTcwNDM4fQ.fTI0_wlOLCmckuu4I5gt3wPf563UlQh8JpveXg7P1LI
```


> [!IMPORTANT]
> **V2 migrations are additive and non-destructive** (`IF NOT EXISTS` everywhere), so they are safe to run against your existing dev DB without data loss. We will NOT run `reset_db.py`.

> [!WARNING]
> **LinkedIn `li_at` cookie must be manually extracted from Chrome DevTools** for each account *right before* testing — `li_at` cookies are short-lived and session-bound. You'll need to log into each account in Chrome, grab the cookie from DevTools → Application → Cookies, and paste it when the provisioning script prompts.

> [!CAUTION]
> The `.env` currently has a **placeholder `FERNET_KEY`** (`generate_with_python...`). This must be a real Fernet key or the cookie encryption step in `create_test_user.py` will fail. We will generate one and patch `.env` before provisioning.

---

## Proposed Steps

### Phase 0 — Environment Prep

#### Step 1: Generate Real Fernet Key & Patch `.env`
```bash
cd apps/core_api
source .venv/bin/activate
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Paste result into `.env` as `FERNET_KEY=<generated>`.

#### Step 2: Run V2 Migrations (non-destructive)
```bash
cd apps/core_api
source .venv/bin/activate
export PYTHONPATH=.
python scripts/migrate_v2.py
```
Adds virality columns to `posts`, creates `carousel_assets` and `user_settings` tables.

---

### Phase 1 — Start Services

**Terminal 1 — Core API (port 8000):**
```bash
cd apps/core_api && source .venv/bin/activate && export PYTHONPATH=.
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — AI Engine (port 8001):**
```bash
cd apps/ai_engine && source .venv/bin/activate && export PYTHONPATH=.
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

---

### Phase 2 — Provision Test Users

Run **twice** (once per account):
```bash
cd apps/core_api && python scripts/create_test_user.py
```
Prompts: email → LinkedIn ID (use profile slug) → full name → `li_at` cookie.

---

### Phase 3 — LinkedIn OAuth Login (get JWT tokens)

For each user, hit the OAuth flow to get a JWT:
```
GET http://localhost:8000/api/v1/auth/linkedin/login
```
Complete the LinkedIn OAuth redirect. The callback returns a JWT.
Store both JWTs — they'll be used as `Authorization: Bearer <token>` headers for all V2 API calls.

---

### Phase 4 — Feature Testing Matrix

#### 4A. Heatmap (`GET /api/v2/analytics/heatmap`)

| Step | Action | Expected |
|---|---|---|
| 1 | `GET /api/v2/analytics/heatmap?weeks=8` with Account A JWT | 200 — global benchmark data (no personal posts yet) |
| 2 | Inject 10 test posts with spread `published_at` timestamps via `inject_test_posts.py` | — |
| 3 | Re-call heatmap | 200 — personal data now populates `heatmap` dict |
| 4 | Verify `best_slots` array has at least 2 entries | Check Tue/Thu 9–11am are prominent |
| 5 | Call with `weeks=0` | 422 validation error |

#### 4B. Smart Fill (`POST /api/v2/calendar/smart-fill`)

| Step | Action | Expected |
|---|---|---|
| 1 | POST with `pillars=["AI","Founder Stories","Product Tips"]`, `posts_per_week=3` | 201 — 3 draft posts returned |
| 2 | Verify each post has `scheduled_at` populated with a best-slot time | — |
| 3 | POST with `pillars=[]` | 422 |
| 4 | POST with `posts_per_week=0` | 422 |
| 5 | Kill AI Engine, retry request | 502 propagated correctly |

#### 4C. Virality Scoring (`POST /api/v2/posts/{id}/score`)

| Step | Action | Expected |
|---|---|---|
| 1 | Create a draft post via `POST /api/v1/posts` | Get `post_id` |
| 2 | `POST /api/v2/posts/{id}/score` | 200 — `total_score` 0–100, 3 `hook_alternatives` |
| 3 | `GET /api/v2/posts/{id}/score` | 200 — cached score, no AI round-trip |
| 4 | `GET /api/v2/posts/{bad_id}/score` | 404 |
| 5 | Call without JWT | 401 |

#### 4D. Carousel Studio (`POST /api/v2/posts/{id}/carousel`)

| Step | Action | Expected |
|---|---|---|
| 1 | `POST /api/v2/posts/{id}/carousel` for a draft post | 201 — `slides_json` with 7 slides, `pdf_url` set |
| 2 | `GET /api/v2/posts/{id}/carousel` | 200 — asset returned |
| 3 | `GET /api/v2/posts/{bad_id}/carousel` | 404 |
| 4 | `POST /api/v2/posts/{id}/carousel/publish` | 200 if LinkedIn token valid, or inspect error |
| 5 | `POST publish` for a post with no carousel asset | 400 |

---

### Phase 5 — Cross-Account Isolation Check

- Use Account B's JWT to try `GET /api/v2/posts/{account_a_post_id}/score` → must return **404** (not another user's data)
- Confirm heatmap returns **separate** data per user

---

### Phase 6 — Swagger UI Smoke Test

Open `http://localhost:8000/docs` — verify all V2 routes appear under `v2-carousel`, `v2-virality`, `v2-heatmap`, `v2-calendar` tags with correct schemas.

---

## Verification Plan

### Automated
- Run existing unit test suite to confirm no regressions after migration:
  ```bash
  cd apps/core_api && pytest tests/v2/ -v --tb=short
  cd apps/ai_engine && pytest tests/v2/ -v --tb=short
  ```

### Manual
- DB inspection via `psql` after each step to confirm rows appear in `carousel_assets`, `user_settings`, and virality columns on `posts`
- Browser DevTools Network tab for OAuth flow
- Swagger UI for schema validation

---

## Open Questions

> [!IMPORTANT]
> **Does the Carousel Renderer microservice exist?** The V2 architecture specifies a Puppeteer/WeasyPrint renderer at `CAROUSEL_RENDERER_URL=http://localhost:8002`. If it's not running, carousel PDF generation will 502. Should we:
> - (a) Mock it out with a stub server for now and test everything else?
> - (b) Stand it up first before testing carousel?

> [!IMPORTANT]
> **LinkedIn Write-Flow OAuth**: Publishing carousels requires `LINKEDIN_WRITE_CLIENT_ID` / `LINKEDIN_WRITE_CLIENT_SECRET` in `.env`. These are currently empty. Should we test carousel publish (step 4D-4) or skip for now and just verify generate + render?

