# Implementation Plan - Intelligent Viral Discovery Engine

## Vision Alignment
After reviewing the master PDFs (*2026-03-19-Ok-1.pdf*, etc.), it is clear that aggressive, headless browser automation (Playwright/n8n) is the foundational execution layer for this entire ecosystem. 

Therefore, building a live scraper is **not a detour from the technical blueprint**. The actual "detour" is a **product strategy shift**:
- **Old Flow:** User manually pastes a LinkedIn URL -> System tracks that specific creator.
- **New Flow (Discovery Engine):** System autonomously browses LinkedIn feeds -> Identifies viral posts (last 72 hrs) -> Evaluates engagement thresholds -> Automatically adds high-performing creators to the user's Radar.

## Proposed Architecture (Playwright Execution Layer)

### Component 1: Engine Dependencies
#### [MODIFY] [pyproject.toml](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/pyproject.toml)
- Add `playwright` and `beautifulsoup4`.
- Run `playwright install chromium` in the container/environment.

### Component 2: The Autonomous Discovery Worker
#### [REWRITE] [ingestion_worker.py](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/workers/ingestion_worker.py)
- **Session Injection:** Authenticate Playwright using a provided LinkedIn `li_at` cookie.
- **Feed Traversal:** Navigate to target LinkedIn feeds (e.g., specific hashtags, home feed, or search results) and scroll to load historical posts (up to 72 hours).
- **DOM Extraction:** Parse the GraphQL/XHR intercept or raw DOM to extract:
  - Post Content & Timestamps
  - Author Name & Profile URL
  - Viewer Activity (Likes, Comments, Reposts)
- **Viral Heuristics (The Detour Logic):**
  - Evaluate extracted posts against dynamic thresholds (e.g., > 100 likes, > 20 comments).
  - If a post qualifies, automatically invoke `CreatorRepository.add_tracked_creator` to save the author to the Radar.
  - Inject the viral post into the `ingested_posts` table to populate the Action Desk Feed.

### Component 3: LLMOps Feedback Completeness
#### [MODIFY] [comment_controller.py](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/controllers/comment_controller.py)
- Connect `/comments/feedback` to the [ShadowActionLog](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/models/llmops.py#8-27) table.
- Calculate stringent edit-distance scores comparing the AI draft to the human edit, persisting this into the DPO flywheel.

## Verification
1. Export a valid `li_at` cookie to the `.env`.
2. Run the [ingestion_worker.py](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/workers/ingestion_worker.py) and monitor terminal logs as it drives the headless browser, scrolls, and extracts DOM nodes.
3. Verify the database [tracked_creators](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/controllers/creator_controller.py#55-63) and `ingested_posts` tables mathematically populate based strictly on engagement thresholds.
