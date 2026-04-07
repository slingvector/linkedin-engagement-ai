# LinkedIn Copilot — Operator Guide

> **Audience:** The person running and operating this system (self-hosted, single-operator trial deployment).
> This guide covers every feature, how to configure it, how to use it end-to-end, and what to watch for in production.

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [First-Time Setup](#2-first-time-setup)
3. [Authentication & Onboarding](#3-authentication--onboarding)
4. [Feature Guide](#4-feature-guide)
   - 4.1 [Idea Engine](#41-idea-engine)
   - 4.2 [Post Creator](#42-post-creator)
   - 4.3 [Content Calendar (Smart Fill)](#43-content-calendar-smart-fill)
   - 4.4 [Creator Radar](#44-creator-radar)
   - 4.5 [Carousel Studio](#45-carousel-studio)
   - 4.6 [Virality Scoring](#46-virality-scoring)
   - 4.7 [Analytics & Heatmap](#47-analytics--heatmap)
   - 4.8 [Career Agent](#48-career-agent)
   - 4.9 [Lead Inbox (Sales)](#49-lead-inbox-sales)
   - 4.10 [Deals Pipeline](#410-deals-pipeline)
   - 4.11 [Talent Discovery & ATS](#411-talent-discovery--ats)
   - 4.12 [Enterprise ABM Radar](#412-enterprise-abm-radar)
   - 4.13 [Campaign Orchestrator](#413-campaign-orchestrator)
   - 4.14 [LLMOps Safety Plane](#414-llmops-safety-plane)
5. [Environment Configuration Reference](#5-environment-configuration-reference)
6. [Docker Environments](#6-docker-environments)
7. [Monitoring & Logs](#7-monitoring--logs)
8. [Security Model](#8-security-model)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (Next.js)                    │
│              apps/web  — port 3000                      │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP (proxied via next.config rewrites)
┌───────────────────────▼─────────────────────────────────┐
│               Core API (FastAPI)                        │
│              apps/core_api — port 8000                  │
│  Auth · Posts · Creator · Analytics · Career · Sales    │
└────────────┬──────────────────────────┬─────────────────┘
             │ Internal HTTP            │ Internal HTTP
┌────────────▼──────────┐  ┌───────────▼─────────────────┐
│  AI Engine (FastAPI)  │  │  Carousel Renderer          │
│  apps/ai_engine       │  │  apps/carousel_renderer     │
│  port 8001            │  │  port 8002                  │
└───────────────────────┘  └─────────────────────────────┘
             │
┌────────────▼──────────┐
│  PostgreSQL            │
│  port 5432             │
└───────────────────────┘
```

**Data accounts in use:**
- **Read account** — a LinkedIn account used by the ingestion worker to scrape the feed. Never publishes.
- **Write account** — a LinkedIn account with `w_member_social` OAuth scope used to publish carousels.

---

## 2. First-Time Setup

### 2.1 Prerequisites

| Requirement | Version |
|---|---|
| Docker + Docker Compose | v2.x |
| Python | 3.12+ (for local dev only) |
| Node.js | 18+ (for local dev only) |
| A LinkedIn developer app | [linkedin.com/developers](https://www.linkedin.com/developers) |

### 2.2 LinkedIn Developer App Setup

You need **two LinkedIn apps** (or one app with all scopes):

| App | Purpose | Required Scopes |
|---|---|---|
| **Read App** | OAuth login + post ingestion | `openid`, `profile`, `email`, `w_member_social` |
| **Write App** | Carousel publish | `openid`, `profile`, `email`, `w_member_social` |

For each app:
1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/apps) → **Create app**
2. Under **Auth** tab, add redirect URLs:
   - `http://localhost:8000/api/v1/auth/linkedin/callback` (read/login)
   - `http://localhost:8000/api/v2/auth/linkedin/callback` (write/carousel)
3. Copy your **Client ID** and **Client Secret**

### 2.3 Generate Secrets

```bash
# JWT secret (64 chars)
python3 -c "import secrets; print(secrets.token_hex(32))"

# Fernet encryption key (for storing LinkedIn tokens at rest)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Internal API key (Core API → AI Engine)
python3 -c "import secrets; print(secrets.token_hex(24))"
```

### 2.4 Configure `.env`

Copy the example and fill in your values:

```bash
cp .env.example .env
```

**Minimum required values** to start the system:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:your_password@postgres:5432/linkedin_saas
POSTGRES_PASSWORD=your_password

# Security (MUST be changed from defaults)
JWT_SECRET_KEY=<64-char random hex from step above>
FERNET_KEY=<Fernet key from step above>

# LinkedIn Read App (login + feed ingestion)
LINKEDIN_CLIENT_ID=<your read app client id>
LINKEDIN_CLIENT_SECRET=<your read app client secret>
LINKEDIN_REDIRECT_URI=http://localhost:8000/api/v1/auth/linkedin/callback

# LinkedIn Write App (carousel publish)
LINKEDIN_WRITE_CLIENT_ID=<your write app client id>
LINKEDIN_WRITE_CLIENT_SECRET=<your write app client secret>
LINKEDIN_WRITE_REDIRECT_URI=http://localhost:8000/api/v2/auth/linkedin/callback

# AI Engine
AI_ENGINE_URL=http://ai_engine:8001
AI_ENGINE_API_KEY=<internal key from step above>

# CORS (add your production domain if deploying remotely)
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

### 2.5 Start the Stack

```bash
# Local development (builds from source)
docker compose up

# Pre-prod readiness test (uses tagged images)
IMAGE_TAG=v1.2.7 docker compose -f docker-compose.local.yml up

# Production
IMAGE_TAG=v1.2.7 docker compose -f docker-compose.prod.yml up -d
```

---

## 3. Authentication & Onboarding

### 3.1 First Login Flow

The system uses **LinkedIn OAuth 2.0** for authentication. There is no username/password.

1. Open `http://localhost:3000` in your browser
2. You will be automatically redirected to `/login`
3. Click **"Sign in with LinkedIn"**
4. You are redirected to LinkedIn's consent screen — approve the requested permissions
5. LinkedIn redirects back to `/auth/callback` — the system exchanges the code for a JWT
6. You land on the home dashboard, with your LinkedIn name and photo in the sidebar footer

> **Your JWT is valid for 24 hours.** After expiry, the system auto-redirects to `/login`. Simply sign in again.

### 3.2 Connecting the Write Account (Carousel Publish)

To publish carousels to LinkedIn, you need to separately authorize the write-flow app:

1. Navigate to **Settings** in the sidebar (or call `GET /api/v2/auth/linkedin` directly)
2. Click "Connect LinkedIn Write Account"
3. Approve `w_member_social` scope on the LinkedIn consent screen
4. You are returned to the app — the write account is now connected

> The write-flow OAuth token is encrypted with your `FERNET_KEY` and stored in the database. It is never sent to the browser.

### 3.3 Sign Out

Click the **logout icon** (→) at the bottom of the sidebar footer, next to your name.

---

## 4. Feature Guide

---

### 4.1 Idea Engine

**Route:** `/ideas` | **API:** `POST /api/v1/ideas/generate`

Generates a batch of LinkedIn content ideas tailored to your industry, audience, and content pillars.

**How to use:**
1. Navigate to **Idea Engine** in the sidebar
2. Enter your topic, audience, and preferred content formats
3. Click **Generate Ideas**
4. The AI returns a list of post concepts — click any to promote it to a draft in **Post Creator**

**What the AI does:**
- Reads your configured content pillars from the request
- Calls the AI Engine with audience + format preferences
- Returns 5–10 concrete post angles with suggested hooks

**Operator notes:**
- Rate limited: 10 idea generations/day (free tier config in `config.yaml`)
- No LinkedIn API calls — entirely AI-generated

---

### 4.2 Post Creator

**Route:** `/posts` | **API:** `POST /api/v1/posts/generate`, `PATCH /api/v1/posts/{id}`

The core content creation workflow. Generates a full LinkedIn post draft and lets you edit, schedule, and manage it.

**How to use:**

1. Navigate to **Post Creator**
2. Fill in: **Topic**, **Audience**, **Tone**, and optional **Hook**
3. Click **Generate** — the AI writes a full post with hook, body, and CTA
4. Edit directly in the text editor
5. Use **Schedule** to assign a publishing date/time
6. The draft is saved with status `draft` → `scheduled` → `published`

**Post lifecycle states:**

| Status | Meaning |
|---|---|
| `draft` | Created but not scheduled |
| `scheduled` | Publishing date assigned |
| `published` | Posted to LinkedIn |
| `archived` | Soft-deleted |

**API endpoints:**

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/posts/generate` | Generate a new post draft |
| `GET` | `/api/v1/posts` | List all posts (filterable) |
| `GET` | `/api/v1/posts/{id}` | Get a specific post |
| `PATCH` | `/api/v1/posts/{id}` | Edit content/status |
| `PATCH` | `/api/v1/posts/{id}/schedule` | Assign scheduled_at |
| `DELETE` | `/api/v1/posts/{id}` | Soft-delete |

**Operator notes:**
- Posts are stored per-user in `posts` table, scoped by `user_id`
- Rate limited: 5 generations/day (free), 50/day (pro)

---

### 4.3 Content Calendar (Smart Fill)

**Route:** `/calendar` | **API:** `POST /api/v2/calendar/smart-fill`

Generates a complete week of post drafts in one shot, pre-scheduled at your optimal posting times based on your historical engagement heatmap.

**How to use:**
1. Navigate to **Content Calendar**
2. Define your **Content Pillars** (e.g., "AI Automation", "Founder Stories", "SaaS Growth")
3. Set **Posts per week** (1–7)
4. Choose **Preferred formats** (text, carousel, poll)
5. Click **Fill My Week** — the AI generates N drafts, each pre-slotted at your best engagement windows

**What it does internally:**
1. Calls the **Engagement Heatmap** (4.7) to find your top posting windows by day/hour
2. Calls the AI Engine with your pillars and format preferences
3. Creates N post drafts in the DB with `scheduled_at` pre-filled
4. Returns the draft list — visible in the calendar view

**Fallback behavior:**
- If you have no posting history yet, it falls back to LinkedIn benchmark best-times (Tuesday/Thursday 9–11am)

**Operator notes:**
- Smart Fill is the recommended way to bootstrap content for a new week
- Each generated draft can then be individually edited in Post Creator

---

### 4.4 Creator Radar

**Route:** `/radar` | **API:** `POST /api/v1/creators/`, `GET /api/v1/creators/feed`

Tracks LinkedIn thought leaders in your space and auto-generates smart comment drafts for their posts. The core "social selling via comments" engine.

**How to use:**

**Step 1 — Add a creator to track:**
```
POST /api/v1/creators/
{ "linkedin_url": "https://www.linkedin.com/in/some-creator/", "name": "Creator Name" }
```
Or use the UI: click **+ Track Creator**, paste their LinkedIn URL.

**Step 2 — Run ingestion:**
The system's background ingestion worker (or `linkedin-read-flow` service) scrapes the creator's recent posts and stores them as `IngestedPost` records.

**Step 3 — Work the Action Desk:**
1. Navigate to `/radar` → **Action Desk**
2. Browse ingested posts from tracked creators
3. Click **Generate Comment** on any post
4. The AI writes 3 comment drafts with different tones (insightful, question, value-add)
5. Edit the draft you prefer → click **Send** (manual for now — copy to clipboard)

**API endpoints:**

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/creators/` | Add a creator to track |
| `GET` | `/api/v1/creators/` | List tracked creators |
| `DELETE` | `/api/v1/creators/{id}` | Stop tracking |
| `POST` | `/api/v1/creators/{id}/ingest` | Manually trigger ingestion |
| `GET` | `/api/v1/creators/feed` | Get paginated action desk feed |
| `POST` | `/api/v1/creators/comments/generate` | Generate comment drafts |
| `GET` | `/api/v1/creators/{id}/comments` | List comment drafts |
| `PATCH` | `/api/v1/creators/{id}/comments` | Edit/approve a draft |

**Operator notes:**
- The `linkedin-read-flow` service handles automated ingestion via Playwright
- Comment feedback is logged to `shadow_action_logs` for the LLMOps flywheel
- Ingestion frequency is configurable in `config.yaml` → `ingestion.scraper.loop_sleep_interval_seconds`

---

### 4.5 Carousel Studio

**Route:** `/posts` (per-post action) | **API:** `POST /api/v2/posts/{id}/carousel`

Converts any post draft into a branded 7-slide LinkedIn Document (carousel) and publishes it with one click.

**Prerequisites:**
- A post draft must exist (created via Post Creator)
- Write-flow LinkedIn account must be connected (see [3.2](#32-connecting-the-write-account-carousel-publish))
- `carousel_renderer` service must be running

**How to use:**

1. Open any post draft in **Post Creator**
2. Click **"Generate Carousel"** — the system:
   - Calls the AI Engine to generate a 7-slide outline (hook, content slides, CTA)
   - Sends the outline to the Carousel Renderer to produce a branded PDF
   - Stores the PDF and returns a preview URL
3. Preview the slides in the **Carousel Preview Panel**
4. When satisfied, click **"Publish to LinkedIn"**
   - Initiates LinkedIn's 3-step Document Upload API
   - Polls until upload is confirmed
   - Posts the document with your chosen caption

**API endpoints:**

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v2/posts/{id}/carousel` | Generate carousel (AI + render PDF) |
| `GET` | `/api/v2/posts/{id}/carousel` | Fetch current carousel asset |
| `POST` | `/api/v2/posts/{id}/carousel/publish` | Publish to LinkedIn |

**Carousel asset states:**

| Status | Meaning |
|---|---|
| `draft` | Outline generated but PDF render failed |
| `rendered` | PDF ready for preview and publish |
| `published` | Successfully posted to LinkedIn |

**Operator notes:**
- PDF files are stored at `/tmp/carousel_pdfs/` in dev; configure GCS for production
- If the Carousel Renderer is unavailable, the asset is saved as `draft` — regenerate once the renderer is back
- Brand kit (colors, fonts, logo) is configurable per-user in User Settings

---

### 4.6 Virality Scoring

**Route:** `/posts` (inline) | **API:** `POST /api/v2/posts/{id}/virality-score`

Scores any post draft for viral potential (0–100) before you publish it, with a breakdown by hook quality, value density, CTA strength, and emotional resonance.

**How to use:**
1. Open any post draft
2. Click **"Score This Post"**
3. The AI Engine evaluates the draft against your top-performing historical posts
4. Returns:
   - **Overall score** (0–100)
   - **Breakdown** by dimension
   - **3 alternative hook suggestions** to improve the score

**API endpoints:**

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v2/posts/{id}/virality-score` | Score a draft |
| `GET` | `/api/v2/posts/{id}/virality-score` | Get cached score |

**Operator notes:**
- Scores are cached on the post row — re-score after editing
- Hook alternatives are AI-generated based on your own top-performing hooks, not generic ones

---

### 4.7 Analytics & Heatmap

**Route:** `/analytics` | **API:** `GET /api/v1/analytics/dashboard`, `GET /api/v2/analytics/heatmap`

Two analytics views:

**Dashboard** (`/api/v1/analytics/dashboard`)
- Summary of posts created, scheduled, published
- Engagement totals (likes, comments, reposts) pulled from ingested post data

**Engagement Heatmap** (`/api/v2/analytics/heatmap`)
- A day × hour heat grid (Mon–Sun × 0–23h)
- Shows your average engagement rate and post volume per slot
- **Used by Smart Fill** to auto-schedule your next week's drafts

**How to read it:**
- Darker cells = higher engagement rate at that time slot
- Hover to see exact metrics
- This is personal to your account — computed from your own `published` posts' engagement data

**Operator notes:**
- Heatmap is computed from posts in the `posts` table with `status = 'published'`
- Requires at least ~5 published posts to produce meaningful signal; uses LinkedIn benchmark data as fallback

---

### 4.8 Career Agent

**Route:** `/jobs` | **API:** `GET /api/v1/career/jobs`, `POST /api/v1/career/upload-resume`

Surfaces relevant job listings and tracks your application status.

**How to use:**
1. Navigate to **Career Agent**
2. Upload your resume via `POST /api/v1/career/upload-resume`
3. Browse matched jobs via `GET /api/v1/career/jobs`
4. Click a job → view detail at `/jobs/{id}`
5. Update application status at `PUT /api/v1/career/applications/{id}/status`

**Application statuses:** `applied` → `screening` → `interview` → `offer` → `rejected`

**Operator notes:**
- Job sourcing is currently mocked/seed data; LinkedIn Jobs API integration is planned
- Applications are tracked in the `career_applications` table

---

### 4.9 Lead Inbox (Sales)

**Route:** `/inbox` | **API:** `GET /api/v1/sales/prospects`

Surfaces LinkedIn connection requests and profile visits as sales leads.

**How to use:**
1. Navigate to **Lead Inbox**
2. Browse incoming prospects
3. Update lead status at `PUT /api/v1/sales/prospects/{id}/status`

**Lead statuses:** `new` → `contacted` → `qualified` → `disqualified`

**Operator notes:**
- Prospect data is ingested by the read-flow worker from LinkedIn activity
- This is a lightweight CRM inbox, not a full pipeline tool — see Deals Pipeline for that

---

### 4.10 Deals Pipeline

**Route:** `/deals`

A kanban-style B2B deals pipeline built on top of the prospects from Lead Inbox. Tracks relationship stage from first contact to closed.

**Stages:** `Lead → Meeting Booked → Proposal Sent → Negotiation → Closed Won / Closed Lost`

**Operator notes:**
- Deals are created from qualified prospects
- Use in combination with the **Lead Inbox** as a two-stage funnel

---

### 4.11 Talent Discovery & ATS

**Routes:** `/talent`, `/ats`

**Talent Discovery** (`/talent`)
- Browse LinkedIn profiles matching your hiring criteria
- API: `GET /api/v1/talent/candidates`
- Update candidate stage at `PUT /api/v1/talent/candidates/{id}/stage`

**Applicant Tracking System** (`/ats`)
- Pipeline view for active job candidates
- Stages: `Applied → Screening → Interview → Offer → Hired`

**Operator notes:**
- Candidate data is sourced from the LinkedIn read-flow ingestion
- Both features are read-only + status tracking — no automated outreach

---

### 4.12 Enterprise ABM Radar

**Route:** `/abm` | **API:** `GET /api/v1/enterprise/signals`

Account-Based Marketing signals for enterprise sales. Monitors target companies for buying intent signals (hiring sprees, funding news, leadership changes).

**How to use:**
1. Navigate to **Enterprise ABM Radar**
2. Add target accounts at `POST /api/v1/enterprise/campaigns`
3. Monitor for signals at `GET /api/v1/enterprise/signals`

**Signal types:**
- Hiring surge in specific departments
- Leadership change (new VP/C-suite)
- Recent funding round
- Product launch announcements

**Operator notes:**
- Signals are ingested via the LinkedIn read-flow worker monitoring company pages
- Pairs with the **Campaign Orchestrator** to trigger outreach workflows

---

### 4.13 Campaign Orchestrator

**Route:** `/campaigns`

Orchestrates multi-touch LinkedIn outreach sequences. Combines ABM signals, Lead Inbox, and AI-drafted messages into a structured campaign.

**How to use:**
1. Navigate to **Campaign Orchestrator**
2. Create a campaign targeting a segment of prospects or ABM accounts
3. Define the message sequence (connection request → DM #1 → follow-up)
4. The system queues and sends messages according to the safety rate limits

**Safety limits** (configured in `config.yaml`):
```yaml
safety:
  max_comments_per_day: 30
  max_posts_per_day: 10
  min_delay_between_actions_seconds: 30
```

> [!CAUTION]
> LinkedIn aggressively detects automation. These rate limits are calibrated for safety. **Do not increase them** without understanding the risk of account restriction.

---

### 4.14 LLMOps Safety Plane

**Route:** `/llmops` | **API:** `GET /api/v1/llmops/metrics`

Monitors the quality and safety of all AI-generated content across the platform.

**What it tracks:**
| Metric | Description |
|---|---|
| **Hallucination Score** | 0–100; how factually grounded the output is |
| **Tone Adherence Score** | 0–100; how well output matches requested tone |
| **Safety Compliance Score** | 0–100; flags for harmful/spam content |
| **Edit Similarity** | How much the human edited the AI draft (DPO signal) |

**How it works:**
1. Every AI-generated comment/post that the user edits is logged to `shadow_action_logs`
2. An LLM-as-a-Judge evaluates the original AI output and stores scores in `llm_evaluations`
3. The `/llmops` dashboard shows aggregate quality metrics over time

**Operator notes:**
- This is your ongoing quality signal for the AI Engine
- Low hallucination rate + high edit similarity = model needs fine-tuning
- The `shadow_action_logs` dataset is the raw material for future DPO fine-tuning

---

## 5. Environment Configuration Reference

### Core Secrets (must set before first run)

| Variable | Description | Default |
|---|---|---|
| `JWT_SECRET_KEY` | Signs JWTs — **must be 64 random chars** | ❌ Insecure placeholder |
| `FERNET_KEY` | Encrypts stored LinkedIn tokens | ❌ Insecure placeholder |
| `AI_ENGINE_API_KEY` | Internal Core→AI auth key | ❌ Insecure placeholder |

> [!CAUTION]
> In `ENVIRONMENT=production`, the app **will refuse to start** if any of these three hold their default placeholder values. This is intentional — it prevents silent misconfiguration in prod.

### Database

| Variable | Default |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:changeme@localhost:5432/linkedin_saas` |
| `POSTGRES_PASSWORD` | `changeme_local_only` |

### LinkedIn OAuth

| Variable | Description |
|---|---|
| `LINKEDIN_CLIENT_ID` | Read app Client ID |
| `LINKEDIN_CLIENT_SECRET` | Read app Client Secret |
| `LINKEDIN_REDIRECT_URI` | e.g. `http://localhost:8000/api/v1/auth/linkedin/callback` |
| `LINKEDIN_WRITE_CLIENT_ID` | Write app Client ID |
| `LINKEDIN_WRITE_CLIENT_SECRET` | Write app Client Secret |
| `LINKEDIN_WRITE_REDIRECT_URI` | e.g. `http://localhost:8000/api/v2/auth/linkedin/callback` |

### AI & Rendering

| Variable | Default |
|---|---|
| `AI_ENGINE_URL` | `http://ai_engine:8001` |
| `CAROUSEL_RENDERER_URL` | `http://carousel_renderer:8002` |

### CORS

| Variable | Default | Notes |
|---|---|---|
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated for multiple origins |

### Tuning (optional)
| Variable | Default |
|---|---|
| `JWT_EXPIRY_MINUTES` | `1440` (24h) |
| `LOG_LEVEL` | `INFO` |
| `SENTRY_DSN` | (empty — Sentry disabled) |
| `ENVIRONMENT` | `development` |

---

## 6. Docker Environments

### `docker-compose.yml` — Local Development

Builds all services from local source code. Use this for feature development.

```bash
docker compose up
```
- Rebuilds on every `up` call
- DB volume: `postgres_dev_data`
- Hot-reload not enabled by default (add volume mount to enable)

### `docker-compose.local.yml` — Pre-prod Readiness

Uses GHCR-tagged images. Use this to validate a release before pushing to prod.

```bash
IMAGE_TAG=v1.2.7 docker compose -f docker-compose.local.yml up
```
- Exposes all internal ports for smoke testing
- DB volume: `postgres_staging_data` (isolated from dev)
- Requires `IMAGE_TAG` to be set explicitly

### `docker-compose.prod.yml` — Production

Hardened configuration. Uses tagged images, no internal port exposure, `restart: unless-stopped`.

```bash
IMAGE_TAG=v1.2.7 ENVIRONMENT=production docker compose -f docker-compose.prod.yml up -d
```
- DB volume: `postgres_prod_data`
- **`ENVIRONMENT=production` causes startup to fail-fast if secrets are insecure**

---

## 7. Monitoring & Logs

### View live logs

```bash
# All services
docker compose logs -f

# Just core API
docker compose logs -f core_api

# Just AI engine
docker compose logs -f ai_engine
```

### Key log events to watch

| Event | Level | Meaning |
|---|---|---|
| `oauth_initiated` | INFO | User started LinkedIn login |
| `oauth_complete` | INFO | Login succeeded |
| `oauth_failed` | ERROR | Login failed — check LinkedIn app config |
| `carousel_created` | INFO | Carousel generation succeeded |
| `linkedin_init_upload_failed` | ERROR | Write token may be expired — user needs to re-authorize |
| `write_flow_oauth_complete` | INFO | Write account connected |

### Health check

```
GET /health  →  { "status": "healthy", "database": "connected" }
```

---

## 8. Security Model

### Authentication
- **JWT bearer tokens** — 24h expiry, signed with `JWT_SECRET_KEY` (HS256)
- All JWT tokens include `iat` (issued-at) and `jti` (unique ID) claims
- No anonymous access — every protected endpoint returns `401` without a valid token

### LinkedIn Token Storage
- OAuth access tokens are **encrypted with Fernet** before DB storage
- The plaintext token never touches the database
- Revocation: delete the user's `write_access_token_encrypted` row

### CSRF Protection
- OAuth state tokens are stored in **PostgreSQL** (not in-memory)
- Tokens expire in 10 minutes and are deleted on first use (no replay)
- Multi-worker and restart-safe

### CORS
- Configurable via `CORS_ALLOWED_ORIGINS` (comma-separated)
- Never use `*` in production

### Production Startup Guard
If `ENVIRONMENT=production`:
- App refuses to start if `JWT_SECRET_KEY`, `FERNET_KEY`, or `AI_ENGINE_API_KEY` hold their default placeholder values
- Raises a clear `ValueError` with the offending variable names

---

## 9. Troubleshooting

### "Authentication required" on every request
→ JWT has expired. Sign in again at `/login`.

### Login redirects back to `/login` in a loop
→ Check that `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET` are correctly set. Check the Core API logs for `oauth_failed`.

### "Invalid or expired OAuth state"
→ The state token expired (10-minute window). Start the OAuth flow again from `/login`.

### Carousel publish fails with "LinkedIn write token expired"
→ The write-flow OAuth token (stored encrypted) has expired. User must re-authorize:
  navigate to Settings → "Connect LinkedIn Write Account".

### "Production startup blocked" on `docker compose up`
→ One or more secrets still hold their default placeholder value. Set `JWT_SECRET_KEY`, `FERNET_KEY`, and `AI_ENGINE_API_KEY` in `.env`.

### Carousel Renderer unavailable
→ Asset is saved as `draft` status. Once the renderer is running again, re-generate from the Post Creator. PDF renders are not cached.

### Heatmap returns benchmark data instead of personal data
→ You need at least 5 posts with `status = 'published'` in the database to generate personal heatmap data. The system falls back to LinkedIn benchmark times automatically.

### Database migration for `shadow_action_logs` FK
If you see `ForeignKeyViolationError` when deleting a user:
```sql
-- Apply the CASCADE constraint to an existing DB
ALTER TABLE shadow_action_logs
  DROP CONSTRAINT shadow_action_logs_user_id_fkey,
  ADD CONSTRAINT shadow_action_logs_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
```
