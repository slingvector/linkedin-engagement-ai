# Root Cause Analysis (RCA) Index

All production incidents, crashes, and architectural defects are documented here.
Each RCA follows the format: **Problem → Root Cause → Resolution → Lessons Learned**.

---

## Index

| File | Incident | Area | Status |
|------|----------|------|--------|
| [rca-docker-registry-arch.md](./rca-docker-registry-arch.md) | Docker image name mismatch + ARM64/AMD64 architecture failure | Docker / CI | ✅ Resolved |
| [rca-docker-ai-connectivity.md](./rca-docker-ai-connectivity.md) | AI Engine 502 + env var mismatch + LLM crash on startup | Docker / AI Engine | ✅ Resolved |
| [rca-hardcoded-localhost-urls.md](./rca-hardcoded-localhost-urls.md) | Hardcoded `localhost:8000` URLs breaking proxied deployments | Frontend / Config | ✅ Resolved |
| [rca-ingestion-hardening.md](./rca-ingestion-hardening.md) | 502 tunnel failures + BeautifulSoup data loss + wrong model ID | Ingestion / AI | ✅ Resolved |
| [rca-post-generation-crash-v1.md](./rca-post-generation-crash-v1.md) | Post generation API 500/crash on first run | Core API | ✅ Resolved |
| [rca-llm-timeout-asyncpg-hang.md](./rca-llm-timeout-asyncpg-hang.md) | Vertex AI hang (no timeout) + asyncpg infinite connect wait | AI Engine / DB | ✅ Resolved |
| [rca-radar-undefined-map.md](./rca-radar-undefined-map.md) | Radar page crash: `Cannot read properties of undefined (reading 'map')` | Frontend | ✅ Resolved |
| [rca-vertexai-model-auth.md](./rca-vertexai-model-auth.md) | Vertex AI 404 wrong model + IAM/ADC auth failure | AI Engine / GCP | ✅ Resolved |
| [rca-ui-ingestion-blocker.md](./rca-ui-ingestion-blocker.md) | LinkedIn UI ingestion breakdown + API routing conflicts | Ingestion / API | ✅ Resolved |
| [rca-v1.1.2-publishing.md](./rca-v1.1.2-publishing.md) | LinkedIn publishing pipeline failure (v1.1.2) | Publishing | ✅ Resolved |
| [rca-v1.1.2.1-publishing.md](./rca-v1.1.2.1-publishing.md) | LinkedIn publishing follow-up fix (v1.1.2.1) | Publishing | ✅ Resolved |
| [rca-v1.1.2.2-publishing.md](./rca-v1.1.2.2-publishing.md) | LinkedIn OAuth token refresh edge case (v1.1.2.2) | Auth / Publishing | ✅ Resolved |
| [rca-v2-carousel-routing.md](./rca-v2-carousel-routing.md) | V2 carousel API routing mismatch (Next.js proxy + prefix conflict) | API / V2 | ✅ Resolved |
| [rca-stuck-commands-fernet.md](./rca-stuck-commands-fernet.md) | Fernet token injection + stuck background processes | Auth / Workers | ✅ Resolved |

---

## Quick Reference: Recurring Patterns

### 1. Environment Variable Mismatches
Always verify that Docker Compose `environment:` keys match exactly what the application reads. Use `.env.example` as the single source of truth.

### 2. asyncpg Infinite Timeouts
Always set `connect_args={"timeout": 10}` on `create_async_engine`. asyncpg defaults to `None` (infinite), which causes invisible hangs on auth failures.

### 3. LLM Calls Without Timeouts
Always wrap async LLM calls with `asyncio.wait_for(..., timeout=N)`. SDKs (Vertex AI, Gemini) do not enforce wall-clock timeouts by default.

### 4. Hardcoded localhost URLs
Never use absolute `localhost:PORT` URLs in frontend code. Always use relative paths (`/api/v1/...`) or environment-aware config. See `apps/web/src/lib/api.ts`.

### 5. React Query Unsafe Mapping
Always guard with `!data || data.length === 0` instead of `data?.length === 0`. Optional chaining returns `undefined`, not `false`, breaking ternary fallthrough.
