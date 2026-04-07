# GCP Account Setup & Migration Checklist

This guide provides a professional, step-by-step checklist to initialize a new Google Cloud Platform (GCP) account and prepare it seamlessly for deploying the LinkedIn Automation SaaS architecture. 

**Active Project:** `linkedin-saas-prod-451909` (Number: `123554610061`)  
**gcloud Active Config:** `linkedin-saas-prod-451909` ✅

---

## Phase 1: Account Setup & Billing

- [x] **1. Create Project:** `linkedin-saas-prod-451909` — `LinkedIn SaaS Prod` — ACTIVE.
- [ ] **2. Enable Billing:** Attach a billing account to your project.
  - *Note:* Ensure your $300 Free Trial credits are activated. Standard infrastructure costs will draw from this pool first.

---

## Phase 2: API Initialization

You must explicitly enable the APIs for the microservices we use. Search for the following in the console or run this from Google Cloud Shell:

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com
```

- [x] **1. Cloud Run API** (`run.googleapis.com`) — ✅ Enabled
- [x] **2. Cloud SQL Admin API** (`sqladmin.googleapis.com`) — ✅ Enabled
- [x] **3. Artifact Registry API** (`artifactregistry.googleapis.com`) — ✅ Enabled
- [x] **4. Secret Manager API** (`secretmanager.googleapis.com`) — ✅ Enabled
- [x] **5. Vertex AI API** (`aiplatform.googleapis.com`) — ✅ Enabled (2026-04-07)

---

## Phase 3: Infrastructure Provisioning

### A. Artifact Registry
- [x] **1. Create Repository:** `linkedin-saas` — Docker — `us-central1` ✅

### B. Cloud SQL Database
- [x] **1. Create PostgreSQL Instance:** `linkedin-saas-db` — PostgreSQL 15 — `us-central1` — RUNNABLE ✅
- [ ] **2. Create User:** Confirm database user (`postgres`) exists and password is known.
- [ ] **3. Create Database:** Confirm logical database (`linkedin_saas`) exists.

### C. Vertex AI Authentication (Service Account)
- [x] **1. Create Service Account:** `linkedin-ai-agent@linkedin-saas-prod-451909.iam.gserviceaccount.com` ✅
- [x] **2. Assign Role:** `roles/aiplatform.user` granted ✅
- [x] **3. Generate JSON Key:** Saved to `./modernos-edge-agent-key.json` (key ID: `e85d8d3c2b9b2c3194ca9ccc92d4a98ea03006b9`) ✅

### D. Secret Manager — Existing Secrets
The following secrets exist in the project:
- [x] `LINKEDIN_CLIENT_ID`
- [x] `LINKEDIN_CLIENT_SECRET`
- [x] `POSTGRES_HOST`
- [x] `POSTGRES_PORT`
- [ ] `GEMINI_API_KEY` — **Action required:** Get a new key from [AI Studio](https://aistudio.google.com/app/apikey) for this project and update `.env` + Secret Manager.

---

## Phase 4: Local Configuration

- [x] **1. Authenticate CLI:**
  ```bash
  gcloud config set project linkedin-saas-prod-451909
  gcloud auth configure-docker us-central1-docker.pkg.dev
  ```
  Both completed ✅

- [x] **2. Update `.env`:** `apps/ai_engine/.env` updated:
  ```text
  GCP_PROJECT_ID=linkedin-saas-prod-451909
  GCP_LOCATION=us-central1
  VERTEX_MODEL=gemini-2.0-flash-001
  GOOGLE_APPLICATION_CREDENTIALS=/Users/cortex/ventures/linkedin-as-a-service/modernos-edge-agent-key.json
  ```

- [ ] **3. Update `GEMINI_API_KEY`:** The current key in `.env` is from the **old account** (`mcr-relay-1772228380`). 
  - Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) and create a new key linked to project `linkedin-saas-prod-451909`.
  - Update `GEMINI_API_KEY=` in `apps/ai_engine/.env`.

---

## Phase 5: Build & Deploy

### 6. Network Edge & Identity Configuration (CRITICAL)
To enable user login and secure API access across different environments (Staging/Prod), you must synchronize your network origins:

- [ ] **LinkedIn Developer Portal**: Add your public URL (e.g., `https://myapp.com/auth/callback`) to the "Authorized Redirect URLs" in your LinkedIn App settings.
- [ ] **CORS Settings**: Update `CORS_ALLOWED_ORIGINS` in `.env` to include your public URL. Use the JSON list format for multiple origins: `CORS_ALLOWED_ORIGINS='["https://myapp.com", "http://localhost:3000"]'`
- [ ] **Frontend Environment**: Ensure `FRONTEND_URL` in your deployment matches the public ingress URL exactly.

### 7. Cloud Run Deployment (Not yet done)
- [ ] Deploy all services: `make deploy-all`
- [ ] Verify health: `gcloud run services list`
- [ ] Test end-to-end: Access the public URL and confirm login, ingestion, and AI engagement loops.

---

## Summary of Changes Made (2026-04-07)

| Action | Result |
|--------|--------|
| `GCP_PROJECT_ID` in `apps/ai_engine/.env` | Updated to `linkedin-saas-prod-451909` |
| `GCP_PROJECT_ID` in `Makefile` | Updated to `linkedin-saas-prod-451909` |
| Vertex AI API enabled | `aiplatform.googleapis.com` ✅ |
| Service Account created | `linkedin-ai-agent@linkedin-saas-prod-451909.iam.gserviceaccount.com` ✅ |
| SA JSON key generated | `./modernos-edge-agent-key.json` (replaces old key) ✅ |
| `gcloud` CLI active project | `linkedin-saas-prod-451909` ✅ |
| Docker auth configured | `us-central1-docker.pkg.dev` ✅ |
