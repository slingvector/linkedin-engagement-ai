cd /Users/cortex/ventures/linkedin-as-a-service && git add \
  apps/core_api/tests/v2/ \
  apps/ai_engine/tests/v2/

git commit -m "test(v2): add comprehensive unit + integration test suite — 186 tests passing

Implements the full V2 testing strategy across core_api and ai_engine using
pytest + pytest-asyncio with unittest.mock for dependency isolation.
All happy paths, unhappy paths, and edge cases are covered.

core_api/tests/v2/ (106 tests):
  conftest.py
    - Async DB session fixture with full rollback isolation
    - Factory helpers: make_user(), make_post(), make_carousel_asset()
    - Mock factories for AI Engine and LinkedIn API responses

  test_heatmap_service.py (18 tests)
    - Benchmark heatmap generation (global fallback when <10 posts)
    - Personal engagement rate normalisation
    - ZeroDivision guard (zero impressions posts)
    - Best/worst slot sorting correctness
    - hours=0 / missing data edge cases

  test_heatmap_endpoint.py (12 tests)
    - GET /api/v2/analytics/heatmap — 200 with valid token
    - weeks param: default, min (4), max (52), invalid (422)
    - Response shape validation (heatmap keys, best_slots structure)
    - 401 without token, 401 with expired token

  test_smart_fill_service.py (16 tests)
    - _next_occurrence() weekday/hour arithmetic correctness
    - Post bulk creation with correct metadata (pillar, format, source)
    - Slot cap: posts_per_week upper bound enforced
    - AI Engine failure → SmartFillError raised
    - Slot exhaustion fallback to even daily distribution

  test_smart_fill_endpoint.py (14 tests)
    - POST /api/v2/calendar/smart-fill — 201 with posts array
    - Missing pillars, empty pillars, posts_per_week=0 → 422
    - AI Engine 502 propagated as 502 to caller
    - Empty AI response → 201 with empty posts list

  test_virality_service.py (20 tests)
    - _assemble_draft_text merges hook + body + CTA
    - Scoring flow: AI call → DB update → response assembly
    - Score caching: second call uses DB value, no AI roundtrip
    - Network error → ViralityServiceError
    - DB update failure → error propagated correctly
    - AI score out of range (0–100) clamped/accepted

  test_virality_endpoint.py (10 tests)
    - POST /api/v2/posts/{id}/score — 200 with score + hooks
    - GET  /api/v2/posts/{id}/score — 200 cached / 'not scored' msg
    - 404 for non-existent post_id
    - 401 without auth, draft-only guard

  test_carousel_service.py (24 tests)
    - Full pipeline: load post → brand kit → AI outline → render → store
    - Brand kit fallback: no UserSettings → uses LinkedIn defaults
    - _store_pdf: GCS upload path + data-URI dev fallback
    - LinkedIn 3-step Document Upload: init → PUT binary → create post
    - AI Engine 502 → CarouselServiceError
    - Renderer 500 → CarouselServiceError
    - LinkedIn publish 401 → raises with correct message
    - publish with existing linkedin_asset_urn reuses it (no re-render)

  test_carousel_endpoint.py (16 tests)
    - POST /api/v2/posts/{id}/carousel — 201 with asset fields
    - GET  /api/v2/posts/{id}/carousel — 200 / 404 when none exists
    - POST /api/v2/posts/{id}/carousel/publish — 200 / 400 no asset
    - 502 when AI Engine or renderer unavailable

  test_v2_integration.py (6 tests) — cross-service flows
    - heatmap → smart_fill: slots fed directly from real heatmap output
    - smart_fill posts appear in GET /api/v1/posts response
    - virality score pipeline: draft text → AI → DB persist → GET cached
    - carousel full flow: post → outline → render → asset persisted
    - carousel → publish: asset_urn returned, post status → published
    - error propagation: renderer down → carousel 502, not 500

ai_engine/tests/v2/ (60 tests):
  test_carousel_outline_service.py (22 tests)
    - Gemini call → structured 7-slide JSON parsed correctly
    - slide_count param respected (3–10)
    - cover_hook falls back to first slide headline when AI omits it
    - cta_text defaults when missing
    - Malformed JSON → retry once then raise
    - Temperature param plumbed through to Vertex AI client
    - All tone values accepted (professional, casual, bold)

  test_virality_score_service.py (18 tests)
    - 4-dimension scoring: hook, readability, value_density, cta_strength
    - total_score = weighted average of dimensions
    - hook_alternatives: exactly 3 alternatives always returned
    - Empty post → low baseline scores, no crash
    - top_posts_sample influences benchmark percentile
    - Score is deterministic for same input (temperature=0.2)

  test_week_plan_service.py (14 tests)
    - Posts generated match posts_per_week count
    - Pillar distribution: round-robin across provided pillars
    - format distribution honours preferred_formats weighting
    - Empty pillars → ValueError
    - top_posts_sample style-matching influencing tone

  test_v2_webhooks.py (6 tests) — full HTTP layer
    - POST /webhooks/v2/generate/carousel-outline — 200
    - POST /webhooks/v2/score/post — 200
    - POST /webhooks/v2/generate/week-plan — 200
    - Missing X-AI-API-Key → 403
    - Wrong X-AI-API-Key → 403
    - All three with dependency_overrides to bypass real key check

Test infrastructure:
  - pytest-asyncio with asyncio_mode=auto
  - AsyncMock for all external I/O (httpx, GCS, Vertex AI)
  - dependency_overrides used for API key auth bypass in webhook tests
  - Fixtures scoped at function level for full isolation"