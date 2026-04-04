# Implementation Plan - Local Production Build (v1.2.6)

Since the `v1.2.6` images are not yet available on GHCR, this plan enables local building within the production stack to ensure the trial run starts immediately.

## User Review Required

> [!IMPORTANT]
> **Build vs. Pull**: I am adding `build:` blocks to `docker-compose.prod.yml`. This means that instead of downloading images, your Mac Mini will compile them from your local source code. This ensures all today's fixes (LinkedIn versioning, etc.) are included.

## Proposed Changes

### Infrastructure (DevOps)

#### [MODIFY] [docker-compose.prod.yml](file:///Users/cortex/ventures/linkedin-as-a-service/docker-compose.prod.yml)
- Add `build:` contexts for:
  - `ai_engine` (`./apps/ai_engine`)
  - `core_api` (`./apps/core_api`)
  - `web` (`./apps/web`)
  - `ingestion_worker` (`./apps/core_api`, reuse Dockerfile/context)

---

## Verification Plan

### Automated Tests
1. Run `docker compose -f docker-compose.prod.yml build`.
2. Run `docker compose -f docker-compose.prod.yml up -d`.
3. Verify that the `v1.2.6` containers are running via `docker ps`.

### Manual Verification
- Access the stable URL (`nip.io` or `ngrok`) and confirm the app is live with all V2 features.
