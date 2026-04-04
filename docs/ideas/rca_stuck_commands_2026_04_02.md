# RCA — Two Stuck Commands (2026-04-02)

## Incident Summary

Two successive terminal commands hung indefinitely (9m+ each):

1. `curl POST /api/v1/posts/generate` — **hung for 14+ minutes**
2. `python -c "asyncio.run(main())"` inserting a Post via DB — **hung for 9+ minutes**

Both were cancelled manually with no output.

---

## Bug 1 — `curl POST /api/v1/posts/generate` hangs indefinitely

### Call Graph

```
curl → Core API (:8000) POST /api/v1/posts/generate
         └─ PostService.generate_post()
               └─ httpx.AsyncClient(timeout=15)  ← config.yaml "timeouts.ai_engine_seconds"
                     └─ AI Engine (:8001) POST /webhooks/generate/post
                           └─ LLMService.generate_structured_json()
                                 └─ Vertex AI genai.Client.aio.models.generate_content()
                                       └─ ⚠️ NO httpx timeout — uses Vertex AI SDK directly
                                             └─ tenacity: retry 3 times on ANY exception
```

### Root Cause 1A — Vertex AI SDK call has no timeout

**File:** `apps/ai_engine/app/services/llm_service.py` line 93–97

```python
# VertexAI path — NO timeout passed
response = await self._vertex_client.aio.models.generate_content(
    model=model_name,
    contents=user_prompt,
    config=config          # ← GenerateContentConfig has no timeout field
)
```

The `LLM_PROVIDER=vertexai` is set in `apps/ai_engine/.env`. The `_get_timeout()` method (line 50–51) reads from YAML but **is only used in the Ollama branch** (line 121) — the VertexAI branch on line 93 ignores it entirely. The Google `genai` SDK has its own internal retry/backoff, and if the Vertex endpoint is unreachable, returns a token, is rate-limited, or the ADC credential is expired, the call can hang for several minutes before a gRPC deadline.

### Root Cause 1B — `retry_if_exception_type((Exception,))` catches everything

**File:** `apps/ai_engine/app/services/llm_service.py` line 53–57

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type((Exception,)),   # ← catches ALL exceptions incl. timeouts
    reraise=True,
)
```

Even if the Vertex AI call eventually raises a timeout exception after e.g. 5 minutes, tenacity will immediately retry it **up to 3 times**. With a 5-minute hang per attempt × 3 retries = potentially 15 minutes of blocking.

### Root Cause 1C — Core API's httpx timeout doesn't help

**File:** `apps/core_api/app/services/post_service.py` line 70

```python
async with httpx.AsyncClient(timeout=timeout) as client:   # timeout=15s
    resp = await client.post(f"{ai_engine_url}/webhooks/generate/post", ...)
```

The Core API correctly sets a 15-second httpx timeout for the **HTTP connection to the AI Engine**. But this timeout fires at the HTTP transport layer — if the AI Engine *accepts* the connection and holds it open while waiting for Vertex AI, the httpx client sees an open, responsive connection and does **not** time out. The 15s timeout only fires if the connection itself is refused or silent (no bytes received). Since the AI Engine's FastAPI server is alive, the connection is established successfully, so Core API waits indefinitely.

### Timeline

```
t=0s    curl connects to Core API → Core API connects to AI Engine → accepted
t=0.1s  AI Engine connects to Vertex AI → accepted (gRPC stream open)
t=∞     Vertex AI model hangs (rate limit / ADC expired / cold start)
t=15s   Core API httpx timeout does NOT fire (connection is open, just silent)
t=5m    Vertex AI eventually errors → tenacity retries attempt 2
t=10m   tenacity retries attempt 3
t=14m+  User cancels
```

---

## Bug 2 — `python -c "asyncio.run(main())"` hangs inserting a Post

### What the script did

```python
from app.models.post import Post
from app.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

async def main():
    engine = create_async_engine(settings.database_url)
    Session = sessionmaker(engine, class_=AsyncSession, ...)
    async with Session() as db:
        post = Post(user_id=..., ...)
        db.add(post)
        await db.commit()   # ← stuck here
```

### Root Cause 2A — lru_cache Settings loaded in subprocess from wrong .env path

**File:** `apps/core_api/app/config.py` line 77

```python
model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
```

`env_file: ".env"` is a **relative** path. `pydantic-settings` resolves it relative to the **current working directory** at the time `Settings()` is instantiated. The script was run with `Cwd=/Users/cortex/ventures/linkedin-as-a-service` (project root), but the `.env` file that has `DATABASE_URL` is in:

- `apps/core_api/.env` → `FERNET_KEY=kR_eli6...` ← contains real key
- `.env` (project root) → `DATABASE_URL=postgresql+asyncpg://postgres:changeme_local_only@...`

Since the script was launched from the project root, `get_settings()` loaded the root `.env` which uses `POSTGRES_PASSWORD=changeme_local_only`. If that password doesn't match the running Postgres instance, asyncpg will hang on the connection handshake rather than immediately refusing — this is because asyncpg's default connect timeout is `None` (infinite).

### Root Cause 2B — asyncpg connect timeout defaults to None

Unlike `psycopg2`, `asyncpg.connect()` with an invalid password does not immediately raise `InvalidPasswordError` in all configurations. On macOS with a local Postgres accepting peer/md5, an incorrect password causes the TCP handshake to complete but the auth negotiation to stall until Postgres closes the connection — this can take 30–120 seconds per attempt. SQLAlchemy's `create_async_engine` also uses a **connection pool** that attempts multiple connections at startup.

### Root Cause 2C — Running a second asyncpg pool while Core API is running

Core API is already running with `asyncpg` connected to the same Postgres. SQLAlchemy's asyncpg pool uses Postgres's `max_connections` limit. On a default local Postgres install, `max_connections=100`. The Core API's pool uses several connections for background workers (engagement_sync_loop, publishing_scheduler_loop etc.). The subprocess creating its own full pool didn't inherit any existing connections, so it competed for slots. This alone doesn't hard-hang, but combined with auth failure, it compounded the delay.

---

## Fixes

### Fix 1 — Add timeout to Vertex AI calls

**File:** `apps/ai_engine/app/services/llm_service.py`

```python
# Add http_options with timeout to the Vertex AI genai.Client
from google.genai import types as genai_types

config = genai_types.GenerateContentConfig(
    system_instruction=system_prompt,
    response_mime_type="application/json",
    temperature=temperature,
    max_output_tokens=max_tokens,
)
# Use asyncio.wait_for to enforce wall-clock timeout on the async Vertex call
import asyncio
response = await asyncio.wait_for(
    self._vertex_client.aio.models.generate_content(
        model=model_name,
        contents=user_prompt,
        config=config,
    ),
    timeout=self._get_timeout()   # YAML llm.timeout_seconds (default 30)
)
```

### Fix 2 — Narrow tenacity retry scope

```python
# Only retry on transient network/timeout errors, not all Exception
from tenacity import retry_if_exception_type
import httpx, asyncio

@retry(
    stop=stop_after_attempt(2),          # reduce retries: 2 max
    wait=wait_exponential(min=1, max=4),
    retry=retry_if_exception_type((asyncio.TimeoutError, ConnectionError)),
    reraise=True,
)
```

### Fix 3 — Add asyncpg connect_timeout

In the Core API config, pass `connect_args={"timeout": 10}`:

```python
engine = create_async_engine(
    settings.database_url,
    connect_args={"timeout": 10},   # asyncpg connect timeout in seconds
)
```

### Fix 4 — Use psql for direct test data insertion (not Python subprocesses)

Instead of `python -c "asyncio.run(...)"` for quick test data insertion, always use psql:

```bash
psql postgresql://postgres:changeme_local_only@localhost:5432/linkedin_saas -c "
INSERT INTO posts (id, user_id, hook, body_content, topic, status, created_at, updated_at)
VALUES (
  gen_random_uuid(),
  'f79ce8bb-06bd-47b9-9bc9-34e9eefaff7f',
  '5 ways AI changed my startup',
  'Body content...',
  'AI Automation',
  'draft',
  NOW(), NOW()
);
"
```

### Fix 5 — Use inject_test_posts.py (it already exists)

```bash
cd apps/core_api && source .venv/bin/activate && export PYTHONPATH=.
python scripts/inject_test_posts.py
```

---

## Summary Table

| Bug | Root Cause | Symptom | Fix |
|---|---|---|---|
| curl /generate hangs | Vertex AI SDK has no timeout; only Ollama branch uses `_get_timeout()` | 14m+ hang | `asyncio.wait_for()` wrapping the aio call |
| curl /generate hangs | tenacity retries ALL exceptions × 3 | Multiplies hang by 3x | Narrow `retry_if_exception_type` |
| curl /generate hangs | Core API's httpx 15s timeout fires on *connect*, not *read* | 15s guard doesn't help | Set httpx `timeout=httpx.Timeout(connect=5, read=30)` |
| python -c hangs | `.env` relative path resolves from project root, loads wrong DB password | asyncpg auth stall | Run scripts with `cd apps/core_api` first, OR use `psql` |
| python -c hangs | asyncpg `connect_args.timeout` defaults to None | Infinite wait on auth failure | Add `connect_args={"timeout": 10}` |

> [!IMPORTANT]
> The most impactful fix is **Fix 1** — wrapping the Vertex AI `aio.models.generate_content()` call in `asyncio.wait_for()`. This is the single change that prevents all future hangs in any AI-powered endpoint.
