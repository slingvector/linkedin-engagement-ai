# Root Cause Analysis (RCA): Deployment & Staging Failures
**Date:** 2026-04-06  
**Environment:** Local Staging (Docker + Cloudflare Tunnel)  
**Status:** Resolved

## 1. Executive Summary
During the migration and staging setup for the LinkedIn SaaS platform, several critical failures occurred that blocked application startup and user login. These spanned configuration parsing errors, service discovery failures, and environment-specific synchronization issues. All issues have been resolved with robust fixes to prevent recurrence in production.

---

## 2. Issue Overviews & Root Causes

### A. Pydantic Settings Parsing Error (`CORS_ALLOWED_ORIGINS`)
- **Symptoms:** `core_api` container crashed immediately with `pydantic_settings.exceptions.SettingsError`.
- **Root Cause:** In `pydantic-settings` v2+, fields with `List[str]` type hints in environment variables are expected to be JSON-encoded (e.g., `'["url1", "url2"]'`). A plain comma-separated string (`url1,url2`) fails to parse if the source is identified as an `EnvSettingsSource` before reaching the custom `@field_validator`.
- **Resolution:** Updated `.env` to use the explicit JSON list format.

### B. Service Discovery Failure (`ENOTFOUND core_api`)
- **Symptoms:** `web` container logs showed `getaddrinfo ENOTFOUND core_api`.
- **Root Cause:** This was a cascading failure. Because the `core_api` container crashed (due to Issue A), its hostname was no longer resolvable within the Docker network. The Next.js proxy could not reach the backend.
- **Resolution:** Fixed Issue A, which allowed `core_api` to stay healthy and discoverable.

### C. OAuth Redirect & CORS Mismatch (Login Error)
- **Symptoms:** Users reached the login page but failed after the LinkedIn handshake.
- **Root Cause:** The `LINKEDIN_REDIRECT_URI` and `FRONTEND_URL` were hardcoded to `http://localhost:3000`. When accessing via a Cloudflare Tunnel (`https://...trycloudflare.com`), the OAuth flow redirected to the wrong host, and the browser blocked requests due to CORS origin mismatch.
- **Resolution:** Synchronized all base URL variables (`REDIRECT_URI`, `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`) with the active tunnel URL.

### D. Docker Daemon Not Running
- **Symptoms:** `docker compose` commands failed with `Cannot connect to the Docker daemon`.
- **Root Cause:** The host machine (Mac) had Docker Desktop closed or not fully initialized.
- **Resolution:** Implemented automated daemon health checks and start commands (`open -a Docker`).

### E. Ingestion Worker Authentication Blocker
- **Symptoms:** `ingestion_worker` container fails with `read_flow_auth_failed` despite providing a fresh `li_at` cookie.
- **Root Cause:** LinkedIn's anti-scraping system detects the IP and device fingerprint mismatch between the Mac browser (home IP/MacOS) and the Docker container (container IP/Linux). This triggers a mandatory 2FA/CAPTCHA loop that cannot be solved by a headless worker.
- **Workaround (The "Local Bridge" Pattern):** Run the ingestion worker natively on the Mac host. Because it shares the same public IP and network environment as the authenticated browser, it is trusted by LinkedIn. The native worker connects to the Dockerized Postgres database (`localhost:5432`), successfully feeding the staging UI.
- **Robust Long-Term Fix:** 
    - Implement the `linkedin-read-flow` with support for full cookie set extraction (including `JSESSIONID`).
    - Use Resident Proxy services to mask the container IP.
    - Transition to a persistent session volume that is "warmed" once on the primary IP and then moved to the cloud.

---

## 3. Robustness Strategy (Long-Term Fixes)

1.  **Strict Configuration:** Enforce JSON format for all list variables in `.env.example` to avoid parsing ambiguity.
2.  **Environment-Agnostic URLs:** Replace all hardcoded `localhost` references with a single `BASE_PUBLIC_URL` variable that cascades to OAuth and CORS settings.
3.  **Persistence:** Transition from "Quick Tunnels" (random URLs) to **Named Persistent Tunnels** (stable URLs) for staging and production testing.
4.  **Makefile Orchestration:** Updated the `Makefile` to handle Docker health and image fallbacks (GHCR vs Local Build) automatically.
5.  **Local Hybrid Orchestration:** Modified the architecture to allow ingestion to run as a native "satellite" service when Docker IP-blocking occurs.

---

## 4. Verification
- [x] Backend boots successfully with multi-origin CORS.
- [x] Web container proxy resolves `core_api` consistently.
- [x] User login flow completes successfully via the tunnel (`trycloudflare.com`).
- [x] Ingestion worker successfully populating Docker DB from Mac host.
