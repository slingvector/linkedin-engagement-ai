# Root Cause Analysis: v1.1.2 Production Hardening

## Incident Summary
The local production docker swarm was experiencing multiple cascading failures:
1. `core_api` and `ai_engine` missing API keys (`OPENAI_API_KEY`, `JWT_SECRET_KEY`)
2. [web](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/app/controllers/idea_controller.py#19-42) Next.js frontend failing to proxy requests with `500 Internal Server Error (ECONNREFUSED)`
3. `ingestion_worker` stuck in an infinite restart loop.

## Root Causes & Resolutions

### 1. Missing Environment Variables (`env_file`)
**Root Cause**: The [docker-compose.prod.yml](file:///Users/cortex/ventures/linkedin-as-a-service/docker-compose.prod.yml) explicitly mapped individual variables (like `DATABASE_URL`) but lacked the standard `env_file: .env` block. The application code depends on many keys like `OPENAI_API_KEY`, `JWT_SECRET_KEY`, and `LINKEDIN_CLIENT_ID`, which were undefined.
**Resolution**: Appended `env_file: - .env` to the `core_api`, `ai_engine`, [web](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/app/controllers/idea_controller.py#19-42), and `ingestion_worker` services. This ensures secrets are safely passed to the docker containers without hardcoding.

### 2. Next.js `ECONNREFUSED` Proxy Error
**Root Cause**: The Next.js [next.config.ts](file:///Users/cortex/ventures/linkedin-as-a-service/apps/web/next.config.ts) had a [rewrites()](file:///Users/cortex/ventures/linkedin-as-a-service/apps/web/next.config.ts#4-12) function with a fallback destination of `http://localhost:8000/api/v1/:path*`. Inside Docker, `localhost` points strictly to the [web](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/app/controllers/idea_controller.py#19-42) container itself, not the backend API! The proxy crashed when it found no listener on port 8000.
**Resolution**: Modified [next.config.ts](file:///Users/cortex/ventures/linkedin-as-a-service/apps/web/next.config.ts) fallback destination to properly map the internal docker network address `http://core_api:8000/api/v1/:path*`.

### 3. Ingestion Worker Restart Loop
**Root Cause**: [app/workers/ingestion_worker.py](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/workers/ingestion_worker.py) defined classes and functions but lacked a `__main__` entrypoint to actually run the background polling loop. Docker executed `python -m app.workers.ingestion_worker`, which instantly exited with code 0, triggering the `restart: unless-stopped` policy infinitely.
**Resolution**: Added `if __name__ == "__main__": asyncio.run(safe_ingest_mock_posts())` to the bottom of the worker script.

### 4. AI Engine Module Not Found
**Root Cause**: The Pyproject dependencies for `ai_engine` were missing `aiofiles`, causing an instant fatal crash on boot. 
**Resolution**: Tagged `aiofiles>=23.2.1` in the Pyproject requirements and rebuilt the frozen image.

### 5. Empty AI Generation & Ollama Fallback Failure
**Root Cause**: When the ideas generation endpoint was invoked, Gemini occasionally returned malformed JSON, successfully triggering the fallback logic. However, the fallback to the local Ollama instance failed because [llm_service.py](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/app/services/llm_service.py) had a hardcoded `base_url="http://localhost:11434/v1"`. Inside Docker, `localhost` points to the AI Engine container itself, not the host machine running Ollama. This caused a connection failure, and the API degraded to returning an empty array `{"items": []}`.
**Resolution**: Modified [llm_service.py](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/app/services/llm_service.py) to use `os.getenv("OLLAMA_API_BASE")` instead of `localhost`, injected `OLLAMA_API_BASE=http://host.docker.internal:11434` into [docker-compose.prod.yml](file:///Users/cortex/ventures/linkedin-as-a-service/docker-compose.prod.yml), and removed empty-string API key overrides. Fallback generation now routes perfectly to the host machine's Ollama instance.
