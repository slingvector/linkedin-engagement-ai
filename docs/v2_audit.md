# V2 Architecture — Implementation Audit

> Audited against `/docs/ideas/v2_architecture.md` on 2026-04-01

---

## Sprint 1 — Posting Time Heatmap ✅ COMPLETE

| Spec Item | File | Status |
|---|---|---|
| `GET /api/v2/analytics/heatmap` endpoint | `v2_analytics_controller.py` | ✅ |
| `HeatmapService` with SQL query + global benchmarks fallback | `heatmap_service.py` | ✅ |
| `best_slots` + `worst_slots` response | `heatmap_service.py` | ✅ |
| `useHeatmap()` hook | `hooks/useHeatmap.ts` | ✅ |
| `HeatmapGrid` — color-coded cells, hover tooltip | `calendar/page.tsx` (inline) | ✅ |
| `BestSlotsPanel` — top windows cards | `calendar/page.tsx` (inline) | ✅ |
| `HeatLegend` component | `calendar/page.tsx` (inline) | ✅ |
| Benchmark fallback badge ("Global LinkedIn benchmarks") | `calendar/page.tsx` | ✅ |
| **Missing from spec:** `CalendarHeatmapOverlay.tsx` (named component) | — | ⚠️ Implemented differently — grid is inline in `calendar/page.tsx` rather than a named component. Functionally equivalent. |

---

## Sprint 2 — Smart Fill Calendar ✅ COMPLETE

| Spec Item | File | Status |
|---|---|---|
| `POST /api/v2/calendar/smart-fill` endpoint | `v2_calendar_controller.py` | ✅ |
| `SmartFillService` — HeatMap slots + AI Engine + bulk post creation | `smart_fill_service.py` | ✅ |
| AI Engine: `POST /webhooks/v2/generate/week-plan` | `week_plan_controller.py` | ✅ |
| `WeekPlanService` — pillar/format-balanced week plan prompt | `week_plan_service.py` | ✅ |
| `SmartFillDrawer.tsx` — pillar inputs, posts/week stepper, format toggles | `SmartFillDrawer.tsx` | ✅ |
| "🤖 AI Fill My Week" button in calendar header | `calendar/page.tsx` | ✅ |
| Draft preview strip after generation | `calendar/page.tsx` | ✅ |
| Registered in both `main.py` files | `core_api/main.py`, `ai_engine/main.py` | ✅ |

---

## Sprint 3 — Virality Scoring Engine ✅ COMPLETE

| Spec Item | File | Status |
|---|---|---|
| `POST /api/v2/posts/{id}/score` endpoint | `v2_posts_controller.py` | ✅ |
| `GET /api/v2/posts/{id}/score` endpoint (cached) | `v2_posts_controller.py` | ✅ |
| Post model: `virality_score`, `score_breakdown`, `hook_alternatives`, `actual_engagement_rate`, `score_updated_at` | `models/post.py` | ✅ |
| `ViralityService` — top-hook calibration + AI Engine call + persist | `virality_service.py` | ✅ |
| AI Engine: `POST /webhooks/v2/score/post` | `virality_score_controller.py` | ✅ |
| `ViralityScoreService` — 4-dim rubric + 3 hook alternatives | `virality_score_service.py` | ✅ |
| `ViralityBadge.tsx` — score ring, breakdown bars, hook alternatives (click-to-copy) | `ViralityBadge.tsx` | ✅ |
| Badge wired into `posts/page.tsx` | `posts/page.tsx` | ✅ |
| Registered in both `main.py` files | ✅ (wired this session) | ✅ |
| DB migration script | `scripts/migrate_virality_columns.py` | ✅ |
| **Missing from spec:** `engagement_sync_worker.py` — 6-hour background worker pulling live LinkedIn metrics | — | ❌ NOT BUILT |
| **Missing from spec:** DPO data flywheel — compare predicted vs actual, feed training dataset | — | ❌ NOT BUILT (long-term / post-30-day feature) |

---

## Sprint 4 — Carousel Studio ❌ NOT STARTED

| Spec Item | File | Status |
|---|---|---|
| `POST /api/v2/posts/{post_id}/carousel` endpoint | — | ❌ |
| `CarouselAsset` DB model | — | ❌ |
| `CarouselService` — AI outline → renderer → GCS → LinkedIn upload | — | ❌ |
| AI Engine: `POST /webhooks/v2/generate/carousel-outline` | — | ❌ |
| Carousel Renderer microservice (Puppeteer/WeasyPrint) | — | ❌ |
| `CarouselPreviewPanel` UI — swipeable slides, editable per-slide | — | ❌ |
| LinkedIn Document Upload API 3-step flow | — | ❌ |
| "✨ Make Carousel" button on idea cards | — | ❌ |

---

## Shared Infrastructure

| Spec Item | Status | Notes |
|---|---|---|
| All V2 routes under `/api/v2/` | ✅ | Consistently versioned |
| V1 routes untouched | ✅ | No regressions |
| DB migration `003_post_virality` | ✅ | Via `migrate_virality_columns.py` |
| DB migration `002_carousel_assets` | ❌ | Carousel not built |
| DB migration `004_user_settings` | ❌ | `user_settings` table not created |
| `CAROUSEL_RENDERER_URL` env var | ❌ | Carousel not built |
| `GCS_BUCKET_NAME` env var | ❌ | Carousel not built |
| Feature flags in `config.yaml` | ⚠️ | Not explicitly gated — services are always-on |

---

## Summary

| Sprint | Feature | Status |
|---|---|---|
| Sprint 1 | Posting Time Heatmap | ✅ Complete |
| Sprint 2 | Smart Fill Calendar | ✅ Complete |
| Sprint 3 | Virality Scoring Engine | ✅ Complete (minus engagement sync worker) |
| Sprint 4 | Carousel Studio | ❌ Not started |

### What's left to build:
1. **`engagement_sync_worker.py`** (Sprint 3 tail) — 6-hour cron, pulls live LinkedIn metrics, updates `likes/comments/impressions`, triggers virality recalibration
2. **Sprint 4: Carousel Studio** — the biggest remaining sprint (renderer microservice + GCS + LinkedIn Document Upload API + full frontend)
3. **`user_settings` table** — needed for Carousel's brand kit (logo, color, font)
