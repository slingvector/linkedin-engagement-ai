# Root Cause Analysis (RCA): LinkedIn AI Engine Fix

**Date:** 2026-04-01  
**Status:** Resolved  
**Objective:** Resolve `404 NOT_FOUND` in LinkedIn idea generation and stabilize the background ingestion worker.

## 1. Vertex AI Model 404 (The "Magic String" Issue)
*   **Problem:** Initial calls to Vertex AI using `gemini-1.5-flash` in `us-central1` returned a hard 404.
*   **Root Cause:** Google Cloud project `mcr-relay-1772228380` is restricted or only provisioned for the **Gemini 2.0 Flash** series (`gemini-2.0-flash-001`). Model strings in Vertex AI are physically bound to their region/project registry; the 1.5 endpoints were unavailable for this specific identity.
*   **Resolution:** Identified the working model version by inspecting the user's existing Instagram project and confirmed it was `gemini-2.0-flash-001`. Applied this to [apps/ai_engine/.env](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/.env).

## 2. Authentication Failures (IAM/ADC)
*   **Problem:** `gcloud auth application-default login` initially pointed to a Service Account (`modernos-edge-agent`) rather than the User.
*   **Root Cause:** This service account lacked the mandatory **`Vertex AI User`** IAM role, causing Vertex to return 401/404 errors because it couldn't map the identity to the model.
*   **Resolution:** Moved the explicit production Service Account JSON key ([modernos-edge-agent-key.json](file:///Users/cortex/ventures/instagram-dirty-page-automation/modernos-edge-agent-key.json)) to the project root and hard-linked the `AI Engine` to use it via the `GOOGLE_APPLICATION_CREDENTIALS` environment variable.

## 3. LinkedIn Ingestion Worker Crashes
*   **Problem:** Bulk ingestion would stop or crash with `AttributeError` or `ConnectionPool` errors.
*   **Root Cause:** 
    1.  **Null-Safety:** The [Voyager](file:///Users/cortex/ventures/linkedin-as-a-service/linkedin_read_flow/read_flow/clients/voyager_client.py#29-384) client was attempting to read social graph edges (likes/comments) that were `null` for certain profiles.
    2.  **Event Loop:** The worker's `asyncio` loop was detaching from SQLAlchemy's `asyncpg` pool after the first execution.
*   **Resolution:** Upgraded to **`linkedin-read-flow v1.0.1`** (with graph-edge null checking) and re-architected [bulk_ingestion_worker.py](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/workers/bulk_ingestion_worker.py) to use a persistent `asyncio.run()` loop that manages session scope correctly.

## 🚦 Final Verified Stack
*   **AI Engine:** `gemini-2.0-flash-001` (Active)
*   **Auth:** Service Account JSON Key (Active)
*   **Ingestion:** v1.0.1 Null-Safe (Active)
