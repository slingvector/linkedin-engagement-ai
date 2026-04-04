# Technical Summary: LinkedIn Carousel Studio Stabilization

This document provides a comprehensive technical recap of the issues encountered during the Sprint 4 stabilization phase and outlines the architectural path toward a robust production solution.

## 1. Problems Encountered & Root Cause Analysis (RCA)

### 🚨 Issue A: LinkedIn OAuth Redirect URI Mismatch
- **Symptom**: User encounters an "OAuth Error" on the LinkedIn consent screen or a 404 after authorization.
- **Root Cause**: LinkedIn requires an **exact string match** for the `redirect_uri`. The local configuration used `http://localhost:8000`, but the browser was accessing the app via a **Cloudflare Tunnel (`trycloudflare.com`)**.
- **Fix**: Implemented a dynamic URI resolver in `v2/auth_controller.py` that detects the incoming `Host` header and adjusts the `redirect_uri` to match the tunnel origin.

### 🚨 Issue B: "PDF Not Found" & Asset Volatility
- **Symptom**: The renderer returns success, but the "Publish" step fails with a `FileNotFoundError`.
- **Root Cause**: Rendered PDFs were stored in the container's ephemeral `/tmp` directory. Rebuilding the API (to apply code changes) wiped the directory, "forgetting" all generated carousels.
- **Fix**: Mounted a persistent Docker volume mapping `./tmp/carousel_pdfs` (host) to `/tmp/carousel_pdfs` (container) in `docker-compose.local.yml`.

### 🚨 Issue C: VERSION_MISSING (LinkedIn Rest API)
- **Symptom**: The `initializeUpload` request to LinkedIn fails with a `400 Bad Request`.
- **Root Cause**: LinkedIn's modern `/rest/` endpoints now mandate a `LinkedIn-Version` header (Standardized Versioning).
- **Fix**: Injected the `LinkedIn-Version: 202603` header into the `CarouselService` publishing pipeline.

### 🚨 Issue D: Internal Service Networking
- **Symptom**: `core_api` reports `Connection Refused` when calling `carousel_renderer` or `ai_engine`.
- **Root Cause**: The `.env` used `localhost:8002`. Within Docker, `localhost` refers to the container itself. 
- **Fix**: Updated all internal service URLs in `.env` to use Docker service names (e.g., `http://carousel_renderer:8002`).

---

## 2. Integrated Fixes & Verification
| Service | Change Made | Status |
|---|---|---|
| **Core API** | Dynamic OAuth Redirect, API Version Headers | ✅ Stable |
| **Carousel Renderer** | Integrated into `docker-compose.local.yml` | ✅ Live |
| **Infrastructure** | Persistent PDF Volumes, Docker Networking | ✅ Verified |
| **Frontend** | Added "Connect LinkedIn Publishing" UI path | ✅ Operational |

---

## 3. Future Architecture for Robust Solutions

To move from "local verification" to a **highly resilient production system**, we propose the following architectural evolution:

### ☁️ Distributed Asset Management
- **Current**: Local File System (`/tmp`).
- **Target**: **Google Cloud Storage (GCS)** or **AWS S3**.
- **Rationale**: Local volumes fail to scale across multiple API pods/servers. Moving to GCS ensures that a PDF rendered on "Pod A" can be published by "Pod B."

### 🔄 Asynchronous Pipeline (Event-Driven)
- **Current**: Synchronous API calls (Outline → Render → Store).
- **Target**: **Temporal.io** or **RabbitMQ/Celery**.
- **Rationale**: Generating a PDF can take 5–10 seconds. An async workflow prevents timeout issues and allows for automatic retries if the LinkedIn API is momentarily down.

### 🔐 Token Lifecycle Service
- **Current**: Tokens stored directly on `User` model.
- **Target**: **Dedicated Vault/Credential Service**.
- **Rationale**: LinkedIn tokens expire every 60 days. A background worker should proactively check expiry dates and trigger "Refresh Token" flows (or notify the user) *before* a publish attempt fails.

### 🌐 Universal Proxy / Gateway
- **Current**: Manual `redirect_uri` logic in controllers.
- **Target**: **Centralized Identity Proxy**.
- **Rationale**: Consolidating all LinkedIn OAuth flows (Read vs. Write) into a single gateway will simplify redirect management and ensure consistent security headers across all environments (Dev, Staging, Prod).

---

### 🏁 Final Verification Summary
In the final test, the system successfully:
1. Identified the tunnel origin.
2. Generated a pixel-perfect PDF via the renderer.
3. Authenticated as **Account B** but used **Account A's** token.
4. Complied with LinkedIn's versioning requirements.
5. Successfully created **urn:li:ugcPost:7446033266148700161**.
