# Environment Consistency Testing Guide

To verify that the system boots consistently across `local`, `staging`, and `production` environments, run the following commands. These sequentially test each Docker Compose topology, ensuring both the web stack and the background ingestion worker start safely.

---

## 1. Local Development (`docker-compose.yml`)
Builds directly from the source code on your machine. Excellent for verifying hot-reloading and source code integrity.

**Command to start (with worker):**
```bash
docker compose --profile ingestion up --build
```
*Wait for the containers to settle, browse to `http://localhost:3000`, test login flow.*

**Command to teardown:**
```bash
docker compose down -v
```
*(The `-v` flag removes the local volume to guarantee a clean slate for the next test)*

---

## 2. Staging / Pre-Prod (`docker-compose.local.yml`)
Pulls the pre-built `ghcr.io` images but connects to your local development environment architecture (host exposing ports like 8000, 8001, 8002).

**Command to start (with worker):**
```bash
IMAGE_TAG=latest docker compose -f docker-compose.local.yml --profile ingestion up
```
*The image tag will pull the latest pushed build. Watch the core_api logs for the Alembic baseline schema migration applying cleanly on boot.*

**Command to teardown:**
```bash
docker compose -f docker-compose.local.yml down -v
```

---

## 3. Production Readiness (`docker-compose.prod.yml`)
The hardened deployment architecture. Internal microservices (AI Engine, Core API, Renderer) are isolated on the Docker bridge network. Only the Web/Frontend container exposes a port to the host.

**Command to start (with worker):**
```bash
IMAGE_TAG=latest docker compose -f docker-compose.prod.yml --profile ingestion up
```
*In production, you will NOT be able to reach `localhost:8000`. You must test the system exclusively through the Web frontend (`localhost:3000`). This proves internal routing through Next.js API Rewrites is working.*

**Command to teardown:**
```bash
docker compose -f docker-compose.prod.yml down -v
```

---

## Things to Look For in the Logs 👀

- **Alembic:** Look for `[entrypoint] Running database migrations...` in the `core_api` container.
- **Bulk Ingestion Worker:** Look for `bulk_ingestion_starting mode='trial-run'` to confirm the worker booted successfully alongside the API.
- **AI Engine:** Confirm the `modernos-edge-agent-key.json` mounts properly without permissions errors in both staging and prod environments.
- **Authentication:** With the fresh database, test the LinkedIn write-flow connection to verify the new Token Refresh storage schema is working properly.
