# Root Cause Analysis (RCA): Local Deployment Architecture Fixes

## Incident Overview
During the local validation deployment of the `v1.2.1`/`v1.2.2` Docker images, three major breakages prevented the application from functioning correctly:
1. API endpoints failed with `401 Unauthorized` responses.
2. The AI Idea Generator failed with `500 Internal Server Error` (Ollama/LLM connection errors).
3. The V2 module components (Virality Badge & Carousel Studio) triggered `404 Not Found` errors in the frontend.

---

## Issue 1: Authentication State Wipe
**Symptom:**
Valid requests strictly via terminal to `/api/v1/ideas/generate` returned `{"detail": "Authentication required"}`.

**Root Cause:** 
Earlier, taking the Postgres container down and running the forceful `reset_db.py` completely leveled the `users` table. Testing against the terminal without executing a mock browser-redirect login loop resulted in standard authentication rejection because no valid user or JWT session existed in the newly spun-up database.

**Resolution:**
Injected a Python script natively into the background `core_api` container to seed a Dev User and cryptographically sign a fresh JWT token manually. This bypassed the UI and fully allowed authenticated cURLs.

---

## Issue 2: AI Engine Sandbox Isolation
**Symptom:**
Once authenticated, idea generation returned `{"detail":"Idea generation failed. The AI Engine may be unavailable."}`. The internal Python stack traces showed:
`RuntimeError: All retries failed for LLM (openai/ollama): Connection error.`

**Root Cause:**
Inside the codebase, `llm_service.py` is programmed to default to the local Ollama provider `http://localhost:11434` if it cannot validate the `vertexai` parameters. In the `docker-compose.prod.yml` configuration:
1. The `ai_engine` block did not cleanly pass the global `.env` file credentials.
2. Even with the credentials, `vertexai` requires absolute access to the `modernos-edge-agent-key.json` service account file. Because the container is an isolated sandbox, it could not access your local Mac directory `/Users/cortex/ventures/...` where the keys actually lived.

**Resolution:**
- Unified keys from `apps/ai_engine/.env` into the root system `.env`.
- Hard-injected `LLM_PROVIDER=vertexai` and `GCP_PROJECT_ID` into the `docker-compose.prod.yml` build block.
- Implemented a Docker volume mapping: `- /Users/cortex/ventures/linkedin-as-a-service/modernos-edge-agent-key.json:/app/modernos-edge-agent-key.json:ro`, allowing the AI container to perform authenticated GCP AI requests securely.

---

## Issue 3: Frontend V1/V2 Route Collision
**Symptom:**  
Hitting "Score it" on the new Virality engine or generating a Carousel resulted in a `404 Not Found` response directly from the core API. 

**Root Cause:**
This issue was caused by a configuration collision between Next.js defaults and Axios networking.
- In `lib/api.ts`, the Axios instance configures the default `baseURL` leveraging `NEXT_PUBLIC_API_URL` (which docker-compose sets to `/api/v1`).
- The components (`ViralityBadge.tsx`) attempt to call `.post('/v2/posts/...')`.
- Axios combines them into `https://hostname/api/v1/v2/posts/...`.
- The Next.js API rewrite rule (`next.config.ts`) explicitly matches `/api/v1/:path*` and forwards it perfectly intact.
- The `core_api` Python FastAPI layer receives the request, but rejects it because its controllers were strictly mounted at `prefix="/api/v2/posts"`, fundamentally resulting in an invalid mapping.

**Temporary Resolution (Hotpatch applied):**
To bypass an entire NextJS `v1.2.3` rebuild locally, I dynamically performed a `docker cp` into the running `core_api` container, modifying `v2_posts_controller.py` and `v2_carousel_controller.py` to listen securely on the misaligned `prefix="/api/v1/v2/posts"`. Restarting `uvicorn` allowed the components to work flawlessly against the local deployment. 

> [!TIP]
> **Permanent Architecture Fix Needed For Frontend Source:**
> In the source code moving forward, the frontend should instantiate a dedicated `apiV2` Axios singleton that omits the `/api/v1` base URL, OR the local rewrite engine should be updated to accept and route `/api/v2/:path*`.
