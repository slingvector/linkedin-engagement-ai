# LinkedIn-as-a-Service V2 — Developer & AI Agent Reference

> **Scope:** This document is the authoritative technical reference for all V2 features.
> Written for developers and AI agents who need to understand, extend, or debug any part of the V2 system.
> Cross-references the original spec at `docs/ideas/v2_architecture.md`.

---

## System Overview

V2 adds four AI-powered features on top of the existing V1 post generation infrastructure. All V2 routes live under `/api/v2/` on **Core API** (port 8000) and `/webhooks/v2/` on **AI Engine** (port 8001). A new **Carousel Renderer** microservice runs on port 8002.

```
Browser (Next.js :3000)
      │
      ▼
Core API (:8000)  ──── AI Engine (:8001)    ← internal, API-key gated
      │                   │
      │            AI Engine calls Vertex AI / Gemini for LLM work
      │
Carousel Renderer (:8002)  ← called by CarouselService only
      │
      └── WeasyPrint → PDF → stored at /tmp/carousel_pdfs/
```

### Key principle: V1 is untouched
All `/api/v1/` routes and models remain unchanged. V2 adds new controllers, new DB columns, and two new tables. Zero regressions.

---

## Sprint 1 — Posting Time Heatmap

### What it does
Analyzes when the user's historically published posts got the most engagement (impressions, likes, comments) and maps that to a day-of-week × hour grid — colour-coded in the calendar UI. New users with no data get LinkedIn global benchmark data (Tue/Thu 9–11am being highest).

### API

```
GET /api/v2/analytics/heatmap?weeks=8
Authorization: Bearer <jwt>
```

**Response shape:**
```json
{
  "heatmap": {
    "monday":    { "9": 0.72, "10": 0.85 },
    "tuesday":   { "9": 0.94, "10": 0.98 },
    "wednesday": { "9": 0.88 },
    "thursday":  { "9": 0.94, "10": 0.96 },
    "friday":    { "9": 0.75 },
    "saturday":  { "9": 0.20 },
    "sunday":    { "9": 0.15 }
  },
  "best_slots":  [{ "day": "tuesday",  "hour": 10, "avg_engagement_rate": 0.98 }, ...],
  "worst_slots": [{ "day": "saturday", "hour": 21, "avg_engagement_rate": 0.04 }],
  "data_source": "personal" | "global_benchmark",
  "sample_size": 14
}
```

All values are normalised **0.0–1.0** (1.0 = the user's best-performing slot). Raw absolute rates are not exposed.

### Files

| File | Role |
|---|---|
| `core_api/app/controllers/v2_analytics_controller.py` | `GET /api/v2/analytics/heatmap` |
| `core_api/app/services/heatmap_service.py` | Query + normalise + fallback logic |
| `web/src/hooks/useHeatmap.ts` | React Query hook (`queryKey: ["heatmap"]`) |
| `web/src/app/calendar/page.tsx` | `HeatmapGrid`, `BestSlotsPanel`, `HeatLegend` components (inline) |

### HeatmapService internals

**Threshold:** `MIN_DATA_POSTS = 5`. Fewer than 5 published posts with `impressions > 0` → global benchmarks.

**SQL (personal data path):**
```sql
SELECT
    EXTRACT(ISODOW FROM published_at)::int - 1 AS dow,   -- 0=Mon..6=Sun
    EXTRACT(HOUR  FROM published_at)::int       AS hour,
    COUNT(*)                                    AS post_count,
    AVG(
        CASE WHEN impressions > 0
             THEN (likes + comments_count * 3.0) / impressions
             ELSE 0 END
    )                                           AS avg_rate
FROM posts
WHERE user_id = :user_id
  AND status = 'published'
  AND published_at IS NOT NULL
  AND impressions > 0
  AND published_at > NOW() - INTERVAL '{weeks} weeks'
GROUP BY dow, hour
ORDER BY avg_rate DESC
```

**Engagement weight formula:** `likes + comments × 3`. Comments weight 3× because they signal deeper interaction than passive likes.

**Normalisation:** each slot's `avg_rate` is divided by `max(avg_rate)` across all slots, giving a 0-1 relative value.

**Global benchmarks:** hardcoded in `heatmap_service._GLOBAL_BENCHMARKS` — sourced from Sprout Social / Sprinklr 2025 industry data. Tue/Wed/Thu 9–11am dominate.

### Frontend

`calendar/page.tsx` renders its own `HeatmapGrid`, `BestSlotsPanel`, `HeatLegend` components inline (not a separate file). The grid is 7 days × 13 hours (7am–7pm), with CSS color classes mapped as:

| Rate | Class |
|---|---|
| ≥ 0.85 | `bg-emerald-500/80` |
| 0.70–0.84 | `bg-emerald-400/60` |
| 0.50–0.69 | `bg-yellow-400/50` |
| 0.30–0.49 | `bg-orange-400/40` |
| 0.10–0.29 | `bg-red-400/30` |
| < 0.10 | `bg-muted/20` |

Hover tooltip shows `"{Day} {Hour} — X% relative engagement score"`.

---

## Sprint 2 — Smart Fill Calendar

### What it does
User defines up to 5 content pillars (e.g. "AI Automation", "Founder Stories") and a posts-per-week count → clicks "AI Fill My Week" → Gemini generates a full week of draft posts → each is auto-slotted at the user's best available heatmap times → all appear in the calendar immediately.

### API

```
POST /api/v2/calendar/smart-fill
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "pillars": ["AI Automation", "Founder Stories", "Product Tips"],
  "posts_per_week": 4,
  "preferred_formats": ["text", "carousel"],
  "top_posts_sample": []   // optional: hook lines for voice calibration
}
```

**Response:** `{ posts: PostResponse[], message: string }` — posts are fully created DB records with `status: "draft"` and `scheduled_at` pre-set.

### Flow

```
SmartFillService.smart_fill()
  │
  ├── 1. HeatmapService.get_heatmap() → get best N+3 slots as buffer
  │
  ├── 2. POST {ai_engine_url}/webhooks/v2/generate/week-plan
  │        Payload: { user_id, pillars, posts_per_week, preferred_formats, top_posts_sample }
  │        Response: { posts: [{ pillar, format, topic, hook, body, cta }] }
  │
  ├── 3. For each AI post:
  │        - Find next unused slot from heatmap best_slots
  │        - _next_occurrence(weekday, hour, now) → concrete datetime
  │        - Create Post(status="draft", scheduled_at=slot_time, generation_metadata={pillar, format, source:"smart_fill_v2", heatmap_slot})
  │
  └── 4. Return all created Post records
```

**Slot assignment:** slots are consumed in priority order from `best_slots`. If all slots are used (more posts than slots), falls back to distributing across weekdays at 10am.

### AI Engine webhook

```
POST /webhooks/v2/generate/week-plan
X-AI-API-Key: {INTERNAL_KEY}

{
  "user_id": "uuid",
  "pillars": ["..."],
  "posts_per_week": 4,
  "preferred_formats": ["text", "carousel"],
  "top_posts_sample": ["hook line 1", "hook line 2"]
}
```

**Prompt rules:**
- Max 2 plain text posts per week; prefer carousels
- Every hook ≤ 15 words, must create curiosity gap
- Body = 3–5 bullet points, no markdown headers
- CTA = open-ended question (no "like if you agree")
- Match tone/voice of `top_posts_sample` if provided

### Files

| File | Role |
|---|---|
| `core_api/app/controllers/v2_calendar_controller.py` | `POST /api/v2/calendar/smart-fill` |
| `core_api/app/services/smart_fill_service.py` | Orchestration: heatmap → AI → bulk create |
| `ai_engine/app/controllers/week_plan_controller.py` | `POST /webhooks/v2/generate/week-plan` |
| `ai_engine/app/services/week_plan_service.py` | Gemini structured JSON week plan prompt |
| `web/src/components/SmartFillDrawer.tsx` | Slide-in drawer UI |
| `web/src/app/calendar/page.tsx` | Drawer trigger + new-drafts preview strip |

### Frontend

`SmartFillDrawer.tsx` — fixed-position right-side drawer (max-w-md):
- **Pillar inputs:** up to 5 text inputs (dynamic add via "+ Add pillar")
- **Posts/week stepper:** `-` / `+` buttons, range 1–7
- **Format toggles:** `text` (blue) / `carousel` (purple) / `video` (orange) — toggle on/off
- **Generate button:** fires `POST /api/v2/calendar/smart-fill`, shows spinner
- **Results view:** replaces form with `DraftPostCard` list showing format badge, pillar badge, schedule time, hook preview, body preview

Drawer is opened by the `"✨ AI Fill My Week"` button in the calendar page header.

---

## Sprint 3 — Virality Scoring Engine

### What it does
Every generated post draft can be scored 0–100 by Gemini across four dimensions. Returns 3 alternative hooks ranked by predicted engagement. Score + breakdown + alternatives are persisted to the post record. A background worker syncs real LinkedIn engagement metrics every 6 hours and re-scores posts whose actual performance diverges from prediction (data flywheel).

### API

```
POST /api/v2/posts/{post_id}/score   → trigger scoring (or re-score)
GET  /api/v2/posts/{post_id}/score   → return cached score (no LLM call)
Authorization: Bearer <jwt>
```

**Response:**
```json
{
  "post_id": "uuid",
  "virality_score": 74,
  "score_breakdown": {
    "hook_strength": 22,
    "readability": 18,
    "value_density": 24,
    "cta_quality": 10
  },
  "hook_alternatives": [
    { "hook": "AI Automation: The Great Equalizer...?", "predicted_score": 87 },
    { "hook": "I Almost Lost My Startup to AI...",        "predicted_score": 79 },
    { "hook": "The Dirty Little Secret of AI...",         "predicted_score": 82 }
  ],
  "score_updated_at": "2026-04-01T15:30:00Z",
  "message": "Virality score: 74/100"
}
```

### Post model columns added (V2)

```python
virality_score       = Column(Integer, nullable=True)   # 0-100
score_breakdown      = Column(JSONB, nullable=True)      # {hook_strength, readability, value_density, cta_quality}
hook_alternatives    = Column(JSONB, nullable=True)      # [{hook, predicted_score}]
actual_engagement_rate = Column(Integer, nullable=True)  # rate * 1000 (int for indexing)
score_updated_at     = Column(DateTime, nullable=True)
```

> `actual_engagement_rate` stores the real post-publish metric as `int * 1000` to avoid float columns while still being indexable. Value of `1050` means `1.050` = 105% weighted engagement rate.

### Scoring flow

```
ViralityService.score_post(post_id, user_id)
  │
  ├── 1. PostRepository.get_by_id() — validates ownership
  ├── 2. _get_top_hooks(user_id) — fetch hook lines of top 3 published posts by impressions
  │        (used as few-shot tone calibration examples for Gemini)
  ├── 3. POST {ai_engine_url}/webhooks/v2/score/post
  │        Payload: { user_id, post_id, draft_text, top_posts_sample }
  │        Response: { total_score, breakdown, hook_alternatives, reasoning }
  └── 4. Persist: post.virality_score, post.score_breakdown, post.hook_alternatives, post.score_updated_at
```

### AI Engine scoring rubric

| Dimension | Max | What Gemini evaluates |
|---|---|---|
| `hook_strength` | 30 | Curiosity gap, contrarian stat, pattern interrupt in first line |
| `readability` | 20 | Short sentences, line breaks every 2–3 lines, mobile-friendly |
| `value_density` | 30 | Every sentence teaches something actionable; no filler |
| `cta_quality` | 20 | Open-ended question that invites genuine debate |
| **Total** | **100** | |

Hook alternatives: exactly 3, each ≤ 15 words, each with a `predicted_score`.

### Files

| File | Role |
|---|---|
| `core_api/app/controllers/v2_posts_controller.py` | `POST/GET /api/v2/posts/{id}/score` |
| `core_api/app/services/virality_service.py` | Orchestration: top hooks → AI → persist |
| `ai_engine/app/controllers/virality_score_controller.py` | `POST /webhooks/v2/score/post` |
| `ai_engine/app/services/virality_score_service.py` | Gemini 4-dimension scoring prompt |
| `web/src/components/ViralityBadge.tsx` | Score ring + breakdown bars + hook alternatives |
| `web/src/app/posts/page.tsx` | Badge wired below schedule button |
| `core_api/app/workers/engagement_sync_worker.py` | 6-hour data flywheel worker |
| `core_api/scripts/migrate_virality_columns.py` | Idempotent migration script |

### ViralityBadge UI

Two states:
- **Pre-score:** Purple "⚡ Score it →" card. Clicking fires `POST /api/v2/posts/{id}/score`.
- **Scored:** Animated SVG ring (colored by tier: 🔥 Viral ≥ 80, ✨ Strong ≥ 60, ⚡ Average ≥ 40, 🔧 Needs Work < 40). Expandable via click.

Expanded view shows:
- Four dimensional bars (`hook_strength/30`, `readability/20`, `value_density/30`, `cta_quality/20`)
- Three hook alternatives — click to copy to clipboard
- "↻ Re-score" button

### Engagement Sync Worker (data flywheel)

`engagement_sync_worker.engagement_sync_loop()` — registered in `main.py` lifespan as an asyncio task.

**Cycle:** every 6 hours (`SYNC_INTERVAL_SECONDS = 21600`)

**Algorithm:**
```
For each user with access_token_encrypted:
  decrypt access_token (Fernet)
  query published posts < 7 days old, published_at NOT NULL, deleted_at IS NULL

  for each post with generation_metadata["linkedin_post_urn"]:
    GET /v2/socialActions/{share_urn}           ← tries social actions first
    GET /v2/shares/{share_id}/statistics        ← fallback to shares endpoint

    actual_rate = (likes + comments*3 + shares*5) / impressions * 1000

    update: post.likes, post.comments_count, post.impressions, post.actual_engagement_rate

    if post.virality_score is not None
       AND abs(new_rate - old_rate) >= RESCORE_THRESHOLD (50 = 5% shift):
         ViralityService.score_post(post.id, user.id)  ← re-score with updated top performers
```

**LinkedIn post URN:** stored in `post.generation_metadata["linkedin_post_urn"]` when published via write-flow. Posts published via simulated publishing (the `publishing_worker`) do not have a URN and are skipped silently.

**Token expiry:** a 401/403 from LinkedIn causes that user to be skipped gracefully (logged as `linkedin_token_expired`).

### DB migration

```bash
cd apps/core_api
source .venv/bin/activate
python -m scripts.migrate_virality_columns
```

Adds 5 columns to `posts` table using `IF NOT EXISTS` guards (idempotent).

---

## Sprint 4 — Carousel Studio

### What it does
Converts any post draft into a 7-slide LinkedIn carousel. AI generates the slide outline; a renderer microservice converts it to a branded 1080×1080 PDF; the PDF can be published directly to LinkedIn via the Document Upload API (3-step flow). User can preview each slide individually before publishing.

### API

```
POST /api/v2/posts/{post_id}/carousel
    → Generate 7-slide outline + render PDF → returns CarouselAsset

GET  /api/v2/posts/{post_id}/carousel
    → Return most recent CarouselAsset for this post (no LLM call)

POST /api/v2/posts/{post_id}/carousel/publish
    Body: { "post_text": "..." }
    → LinkedIn 3-step Document Upload → returns { linkedin_post_urn }

Authorization: Bearer <jwt>
```

### Data model — `CarouselAsset`

Table: `carousel_assets`

```python
post_id              → FK posts.id (CASCADE)
slides_json          JSONB   # [{slide_number, headline, body, visual_suggestion}]
pdf_url              TEXT    # file:///tmp/carousel_pdfs/{post_id}.pdf  (dev)
                             # gs://bucket/...  (prod — GCS)
slide_count          INT     # default 7
status               TEXT    # draft | rendered | published
linkedin_asset_urn   TEXT    # urn:li:document:...  (set after LinkedIn upload)
brand_kit_snapshot   JSONB   # snapshot of brand kit at render time
```

### Data model — `UserSettings`

Table: `user_settings` (one row per user, unique on `user_id`)

```python
user_id              → FK users.id (CASCADE, UNIQUE)
# Brand kit
primary_color        VARCHAR(7)    # hex, default "#0A66C2"
logo_url             TEXT
font_family          VARCHAR(100)  # Google Font name, default "Inter"
author_name          VARCHAR(200)  # shown on carousel footer
author_tagline       VARCHAR(300)
# Posting prefs (Smart Fill defaults)
pillars              JSONB
posts_per_week       INT
preferred_formats    JSONB
# Feature flags
auto_score_drafts    BOOL          # default true
```

### Full pipeline

```
POST /api/v2/posts/{post_id}/carousel
  │
CarouselService.create_carousel(post_id, user_id)
  │
  ├── 1. PostRepository.get_by_id() — ownership check
  │
  ├── 2. _get_brand_kit(user_id)
  │       SELECT * FROM user_settings WHERE user_id = :uid
  │       → defaults: { primary_color: "#0A66C2", font_family: "Inter" }
  │
  ├── 3. POST {ai_engine_url}/webhooks/v2/generate/carousel-outline
  │       Payload: { user_id, topic: "{post.topic}: {post.hook}", audience, tone, slide_count: 7 }
  │       Response: { slides: [{slide_number, headline, body, visual_suggestion}],
  │                   cover_hook, cta_slide_text }
  │
  ├── 4. POST {carousel_renderer_url}/render
  │       Payload: { slides, brand_kit, cover_hook, cta_text }
  │       Response: { pdf_base64: "...", page_count: 7 }
  │       → If renderer unavailable: pdf_bytes = None, asset saved as status="draft"
  │
  ├── 5. _store_pdf(pdf_bytes, post_id)
  │       Dev:  writes to /tmp/carousel_pdfs/{post_id}.pdf → returns "file://..." URL
  │       Prod: upload to GCS → return signed URL (not yet implemented)
  │
  └── 6. CarouselAsset saved to DB (status: "rendered" if PDF exists, "draft" if not)
```

### LinkedIn 3-step Document Upload

Triggered by `POST /api/v2/posts/{post_id}/carousel/publish`:

```
Step 1: POST https://api.linkedin.com/rest/documents?action=initializeUpload
        Body: { initializeUploadRequest: { owner: "urn:li:person:{user_id}" } }
        → { value: { uploadUrl, document: "urn:li:document:..." } }

Step 2: PUT {uploadUrl}
        Body: <PDF binary>
        Authorization: Bearer {access_token}

Step 3: POST https://api.linkedin.com/rest/posts
        Body: { author, commentary: post_text, visibility: "PUBLIC",
                content: { media: { id: "urn:li:document:...", title } },
                lifecycleState: "PUBLISHED" }
        → x-restli-id header = LinkedIn post URN

→ Updates: asset.linkedin_asset_urn = document_urn, asset.status = "published"
```

User's LinkedIn `access_token_encrypted` is decrypted via `decrypt_token()` (Fernet) to authenticate the upload.

### Carousel Renderer microservice

**Location:** `apps/carousel_renderer/main.py`
**Port:** 8002
**Start:** `uvicorn main:app --port 8002 --reload`

**Endpoint:**
```
POST /render
Body: { slides: [Slide], brand_kit: BrandKit, cover_hook, cta_text }
Response: { pdf_base64: string, page_count: int }
```

**Rendering pipeline:**
1. Each slide rendered through `app/templates/slide.html` (Jinja2 template) — 1080×1080px dark card
2. All slides concatenated into one HTML document
3. WeasyPrint converts HTML → PDF (one `@page 1080px 1080px` per slide)
4. PDF returned as base64

**Slide template design:** `app/templates/slide.html`
- Dark background (`#0f172a`) with decorative accent circles
- Brand color bar across top (height: 6px / 8px on cover)
- Cover slide (slide 1): full gradient in brand color, title at 96px
- Content slides (2–6): numbered badge (top-left), headline at 72px, 30px body, italic visual hint
- CTA slide (7): solid brand color background, white text
- Footer: author name + tagline (left), logo or "in" fallback (right)
- "Swipe →" prompt positioned bottom-right (hidden on CTA slide)

**WeasyPrint fallback:** if `weasyprint` is not installed, HTML bytes are returned instead of PDF — allows functional testing without the WeasyPrint system dependency.

### AI Engine — carousel outline

```
POST /webhooks/v2/generate/carousel-outline
X-AI-API-Key: {INTERNAL_KEY}

{
  "user_id": "uuid",
  "topic": "AI Automation: How I replaced my entire ops team",
  "audience": "startup founders",
  "tone": "professional_but_conversational",
  "slide_count": 7
}
```

**Slide structure Gemini must follow:**
- **Slide 1 (Cover):** Scroll-stopping hook ≤ 8 words; curiosity gap or contrarian stat
- **Slides 2–6 (Content):** One actionable insight per slide; headline ≤ 8 words; body ≤ 40 words
- **Slide 7 (CTA):** Tell them what to do next + tease next carousel
- Each slide includes a `visual_suggestion` (one sentence describing ideal image/chart)

**Response schema:**
```json
{
  "cover_hook":     "...",
  "cta_slide_text": "Follow for more →",
  "slides": [{ "slide_number": 1, "headline": "...", "body": "...", "visual_suggestion": "..." }]
}
```

### Files

| File | Role |
|---|---|
| `core_api/app/models/carousel.py` | `CarouselAsset` SQLAlchemy model |
| `core_api/app/models/user_settings.py` | `UserSettings` SQLAlchemy model |
| `core_api/app/models/__init__.py` | Both models registered for `init_master_db.py` |
| `core_api/app/services/carousel_service.py` | Full pipeline + LinkedIn upload |
| `core_api/app/controllers/v2_carousel_controller.py` | `POST/GET /carousel`, `POST /carousel/publish` |
| `ai_engine/app/services/carousel_outline_service.py` | Gemini 7-slide outline prompt |
| `ai_engine/app/controllers/carousel_outline_controller.py` | `POST /webhooks/v2/generate/carousel-outline` |
| `apps/carousel_renderer/main.py` | PDF renderer FastAPI microservice |
| `apps/carousel_renderer/app/templates/slide.html` | Jinja2 slide HTML template |
| `apps/carousel_renderer/pyproject.toml` | Renderer dependencies |
| `web/src/components/CarouselPreviewPanel.tsx` | Slide filmstrip + detail + publish UI |
| `web/src/app/posts/page.tsx` | Carousel panel wired below ViralityBadge |
| `core_api/scripts/migrate_carousel_tables.py` | Creates `carousel_assets` + `user_settings` tables |

### CarouselPreviewPanel UI

**Pre-generation:** Blue "🎠 Carousel Studio" card. "✨ Make Carousel" button fires `POST /api/v2/posts/{id}/carousel`.

**Carousel view (after generation):**
- Horizontal filmstrip of `SlideCard` thumbnails (180×180, scrollable, active slide highlighted in brand color)
- `SlideDetail` panel: headline at 28px, body, italic visual hint, slide number badge
- Navigation dots (clicking or card tap changes active slide, active dot expands)
- Header: "Carousel Preview" + `{n} slides · {status}` badge + "↻ Regenerate" button
- Publish section:
  - Editable `<textarea>` pre-filled with `hook + "\n\n" + body_content + "\n\n" + call_to_action`
  - "🚀 Publish Carousel to LinkedIn" button → `POST /api/v2/posts/{id}/carousel/publish`
  - Shows "✅ Published to LinkedIn" when `asset.status === "published"`

### Config

`CAROUSEL_RENDERER_URL` — set in `core_api/app/config.py`:
```python
carousel_renderer_url: str = Field(default="http://localhost:8002")
```

Overridable via environment variable `CAROUSEL_RENDERER_URL`.

### DB migration

```bash
cd apps/core_api
source .venv/bin/activate
python -m scripts.migrate_carousel_tables
```

Creates `carousel_assets` and `user_settings` tables with `IF NOT EXISTS` (idempotent).

---

## Complete Route Map (V2)

### Core API (`localhost:8000`)

| Method | Path | Feature | Controller |
|---|---|---|---|
| `GET` | `/api/v2/analytics/heatmap` | Heatmap | `v2_analytics_controller` |
| `POST` | `/api/v2/calendar/smart-fill` | Smart Fill | `v2_calendar_controller` |
| `POST` | `/api/v2/posts/{id}/score` | Virality scoring | `v2_posts_controller` |
| `GET` | `/api/v2/posts/{id}/score` | Cached score | `v2_posts_controller` |
| `POST` | `/api/v2/posts/{id}/carousel` | Generate carousel | `v2_carousel_controller` |
| `GET` | `/api/v2/posts/{id}/carousel` | Fetch carousel | `v2_carousel_controller` |
| `POST` | `/api/v2/posts/{id}/carousel/publish` | Publish to LinkedIn | `v2_carousel_controller` |

### AI Engine (`localhost:8001`, internal — `X-AI-API-Key` required)

| Method | Path | Feature | Controller |
|---|---|---|---|
| `POST` | `/webhooks/v2/generate/week-plan` | Smart Fill content | `week_plan_controller` |
| `POST` | `/webhooks/v2/score/post` | Virality scoring | `virality_score_controller` |
| `POST` | `/webhooks/v2/generate/carousel-outline` | Carousel outline | `carousel_outline_controller` |

### Carousel Renderer (`localhost:8002`)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Health + WeasyPrint availability |
| `POST` | `/render` | Slides JSON + brand kit → base64 PDF |

---

## Background Workers (Core API)

| Worker | Interval | Purpose |
|---|---|---|
| `live_viral_ingestion_loop` | ~continuous | Ingest viral posts from LinkedIn feeds |
| `publishing_scheduler_loop` | 10s | Publish scheduled posts |
| `poll_metrics_and_classifications` | 20s | Mock metric bumps + engager classification |
| `seed_evals_loop` | Periodic | LLM evaluation seeding |
| **`engagement_sync_loop`** | **6 hours** | **V2: Sync real LinkedIn metrics + virality recalibration** |

All workers are registered in `core_api/app/main.py` lifespan and cancelled cleanly on shutdown.

---

## Full-Stack Data Flow Diagrams

### Generating + Scoring a Post

```
User visits /posts
  │
  ├── fills topic/audience/framework
  ├── POST /api/v1/posts/generate    → single post draft created
  │
  ├── ViralityBadge shows "⚡ Score it →"
  ├── User clicks → POST /api/v2/posts/{id}/score
  │       → ViralityService → GET top 3 hooks from DB
  │       → POST AI Engine /webhooks/v2/score/post
  │       → Gemini scores 4 dimensions + 3 hook alternatives
  │       → Score persisted: post.virality_score, post.score_breakdown, post.hook_alternatives
  │
  ├── Badge expands: ring + bars + hook alternatives
  │
  ├── CarouselPreviewPanel shows "✨ Make Carousel"
  ├── User clicks → POST /api/v2/posts/{id}/carousel
  │       → CarouselService → fetch brand kit
  │       → POST AI Engine /webhooks/v2/generate/carousel-outline
  │       → POST Carousel Renderer /render  → PDF
  │       → CarouselAsset saved to DB
  │
  └── User reviews slides → edits caption → "🚀 Publish Carousel"
          → LinkedIn 3-step Document Upload
          → asset.status = "published"
```

### Smart Fill Weekly Calendar

```
User visits /calendar
  │
  ├── useHeatmap() → GET /api/v2/analytics/heatmap
  │       → HeatmapService: SQL query OR global benchmarks → normalised grid
  │       → Calendar renders color-coded 7×13 grid
  │
  └── User clicks "✨ AI Fill My Week"
          → SmartFillDrawer opens (right-slide panel)
          → User enters pillars + posts/week + formats
          → POST /api/v2/calendar/smart-fill
                → SmartFillService:
                      1. HeatmapService.get_heatmap() → best N slots
                      2. POST AI Engine /webhooks/v2/generate/week-plan
                      3. Pair posts to slots, create Post records
                → Drawer shows draft post cards with format badges + schedule times
                → Calendar preview strip shows first 4 drafts
```

---

## Setup Checklist for New Environments

### 1. DB migrations (requires Docker/Postgres running)

```bash
cd apps/core_api && source .venv/bin/activate

# V1 schema (all original tables)
python -m scripts.init_master_db

# V2 Sprint 3 — virality columns on posts table
python -m scripts.migrate_virality_columns

# V2 Sprint 4 — carousel_assets + user_settings tables
python -m scripts.migrate_carousel_tables
```

### 2. Environment variables (add to `apps/core_api/.env`)

```env
# Already required for V1
AI_ENGINE_URL=http://localhost:8001
AI_ENGINE_API_KEY=your_internal_key
FERNET_KEY=your_fernet_key

# New for V2 Sprint 4
CAROUSEL_RENDERER_URL=http://localhost:8002
```

### 3. Start services

```bash
# Infrastructure
docker compose up -d   # Postgres + Redis

# Core API (port 8000)
cd apps/core_api && uvicorn app.main:app --reload --port 8000

# AI Engine (port 8001)
cd apps/ai_engine && uvicorn app.main:app --reload --port 8001

# Carousel Renderer (port 8002) — Sprint 4 only
cd apps/carousel_renderer && pip install -e . && uvicorn main:app --reload --port 8002

# Frontend (port 3000)
cd apps/web && npm run dev
```

### 4. Verify V2 routes are live

```bash
curl http://localhost:8000/docs   # Swagger UI — check for v2-analytics, v2-calendar, v2-posts, v2-carousel tags
curl http://localhost:8001/docs   # AI Engine — check for v2-carousel, v2-virality tags
curl http://localhost:8002/health # Carousel Renderer health
```

---

## Known Limitations & Future Work

| Item | Status | Notes |
|---|---|---|
| GCS PDF storage | ❌ Not implemented | Dev uses `/tmp/carousel_pdfs/`. `_store_pdf()` in `carousel_service.py` is the hook — swap in GCS upload logic there. |
| LinkedIn token refresh | ❌ Not implemented | `engagement_sync_worker` drops users with expired tokens. Need OAuth token refresh flow. |
| `user_settings` API | ❌ Not implemented | Model + table exist but no CRUD endpoints. Brand kit must be set directly in DB for now. |
| WeasyPrint system deps | ⚠️ macOS only | Requires `brew install pango libffi`. On Linux: `apt install libpango-1.0-0 libpangoft2-1.0-0`. |
| Feature flags in config.yaml | ⚠️ Not gated | V2 features are always-on. `config.yaml` has a `feature_flags` section but V2 is not wired to it. |
| DPO training queue | ❌ Not implemented | The engagement delta + virality delta pairing exists (engagements sync + re-score) but the downstream fine-tuning pipeline is a future Phase 3 item. |
| Carousel slide editor | ❌ Not implemented | Preview panel shows read-only slides. Per-slide text editing (spec: "editable headline/body per slide") needs `PATCH /api/v2/carousel/{asset_id}/slides/{n}`. |
