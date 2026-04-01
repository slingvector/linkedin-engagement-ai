# V2 Testing Plan

This plan outlines a rigorous unit and integration testing strategy for all V2 features (Sprints 1-4). We will write tests across `core_api`, `ai_engine`, and `carousel_renderer` using `pytest` and `pytest-asyncio`. We will use `unittest.mock` to isolate dependencies (e.g. database, HTTP requests to AI engine / LinkedIn API).

## Proposed Changes

### 1. `core_api` Tests (Backend Business Logic)

#### [NEW] `apps/core_api/tests/test_v2_heatmap.py`
- **Happy Path:** `HeatmapService.get_heatmap()` with ≥ 5 posts computes relative engagement rates perfectly.
- **Decision Logic:** When posts < 5, service falls back to `_build_benchmark_heatmap()`.
- **Edge Cases:** Posts with 0 impressions avoid divide-by-zero (`avg_rate` = 0). Very high engagement scales correctly (max rate normalisation = 1.0).

#### [NEW] `apps/core_api/tests/test_v2_smart_fill.py`
- **Happy Path:** End-to-end `SmartFillService.smart_fill()` successfully requests posts from AI Engine, requests slots from `HeatmapService`, pairs them, and creates `Post` objects.
- **Edge Cases:**
  - AI Engine returns fewer posts than requested.
  - Heatmap has overlapping slots, verifying time exhaustion.
  - Fallback logic when no heatmap slots are available (distributes across next N days at 10 AM).
- **Error Handling:** AI Engine HTTP timeout/500 does not crash the service, returns gracefully (empty list).

#### [NEW] `apps/core_api/tests/test_v2_virality.py`
- **Happy Path:** `ViralityService.score_post()` correctly formats the prompt with top hooks, calls AI Engine, parses JSON, and updates Post model.
- **Caching:** Validation that `/api/v2/posts/{id}/score` GET endpoint returns immediately when cached.
- **Worker Logic (`engagement_sync_worker`):**
  - Formula computation `_compute_engagement_rate()` is exact.
  - Worker correctly parses LinkedIn `/v2/shares/` vs `/v2/socialActions/` endpoints.
  - Triggers a rescore ONLY IF shift is `>= RESCORE_THRESHOLD` (50).
  - Skips gracefully on LinkedIn API 401/403 (expired tokens).

#### [NEW] `apps/core_api/tests/test_v2_carousel.py`
- **Happy Path:** `CarouselService.create_carousel()` fetches AI outline, fetches PDF from Renderer, and persists `CarouselAsset`.
- **Publisher Flow:** `publish_to_linkedin` correctly executes the 3-step Document Upload (`initializeUpload` → `PUT` → create post) with mocked `httpx` flows.
- **Edge Cases:**
  - Rendering microservice unreachable (saves as `status="draft"`).
  - LinkedIn `initializeUpload` fails.
  - Uses default `UserSettings` if user has none.

### 2. `ai_engine` Tests (LLM Wrappers)

#### [NEW] `apps/ai_engine/tests/test_v2_week_plan.py`
- **Structure Validation:** Evaluates `WeekPlanService` builds the exact `user_prompt` formatting from pillars, formats, and `top_posts_sample`.
- **Parsing:** Ensures returning JSON strictly conforms to Pydantic `WeekPlanResponse`.

#### [NEW] `apps/ai_engine/tests/test_v2_carousel_outline.py`
- **Structure Validation:** Evaluates `CarouselOutlineService` prompt injection and parsing the complex 7-slide format into `CarouselOutlineResponse`.

### 3. `carousel_renderer` Tests (Microservice)

#### [NEW] `apps/carousel_renderer/tests/test_rendering.py`
*(Need to initialize tests folder here)*
- **Validation:** Endpoints reject invalid or missing slides.
- **Execution:** Valid execution logic runs correctly whether WeasyPrint is installed (checks for PDF base64 bytes) or falls back.

## Open Questions

> [!IMPORTANT]
> - Do you want me to write full database-backed integration tests (using a local testing sqlite/asyncpg database), or stick to pure mocked unit tests to ensure fast execution? Sticking to `unittest.mock` for `AsyncSession`, `httpx`, and internal services will produce faster, less flaky tests.
> - Shall I run the test suite as I write them to ensure they pass the current code implementation?

## Verification Plan

### Automated Tests
1. I will execute `pytest apps/core_api/tests -k v2`
2. I will execute `pytest apps/ai_engine/tests -k v2`
3. All coverage requirements for V2 logic should pass flawlessly without side-effects on V1 testing.
