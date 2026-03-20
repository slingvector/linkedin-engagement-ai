# Master Project Blueprint: LinkedIn-as-a-Service
## The AI-Powered Professional Graph Ecosystem

> **Core Philosophy:** AI is a compressor of decision workflows. Distribution first → Product second → Automation last.

> **End Vision:** "HubSpot + LinkedIn + AI Agents" — An AI Career + Growth Operating System

---

## Team Structure (3 People, 6–12 Months)

| Role | Owner | Scope |
|------|-------|-------|
| **Lead / AI Architect** | You | LLM orchestration, prompt engineering, AI webhook microservice, agentic workflows |
| **Dev 1 (Frontend)** | Hire | Next.js (App Router), TypeScript, Tailwind + shadcn/ui, TanStack Query, Zustand |
| **Dev 2 (Backend)** | Hire | Go or FastAPI, PostgreSQL, Redis, OAuth, CI/CD, queues, infra |

---

## Architecture Overview

```
┌──────────────┐      ┌──────────────┐      ┌──────────────────┐
│  Dev 1       │      │  Dev 2       │      │  Lead            │
│  Next.js     │─────▶│  Core API    │─────▶│  AI Engine       │
│  (Vercel)    │      │  (Render)    │      │  (FastAPI+LLM)   │
└──────────────┘      └──────┬───────┘      └────────┬─────────┘
                             │                       │
                      ┌──────▼───────┐        ┌──────▼─────────┐
                      │  PostgreSQL  │        │  OpenAI / Local │
                      │  + pgvector  │        │  LLM (Ollama)   │
                      │  + Redis     │        └────────────────┘
                      └──────────────┘
```

**Monorepo** (Turborepo):
```
/linkedin-as-a-service
├── /apps
│   ├── /web           # Next.js Frontend (Dev 1)
│   ├── /core-api      # Go/FastAPI Backend (Dev 2)
│   └── /ai-engine     # Python/FastAPI LLM Orchestrator (Lead)
├── /packages
│   ├── /shared-types  # Shared TypeScript interfaces
│   ├── /ui            # shadcn/ui shared components
│   └── /eslint-config # Linting rules
├── package.json
└── turbo.json
```

---

## 7-Phase Product Evolution

| Phase | Timeline | Target | Core Focus | Revenue |
|-------|----------|--------|------------|---------|
| **1** | Month 1–2 | Individual Creators | Content & Comment Copilot | Free/Early adoption |
| **2** | Month 2–4 | Creators | Growth System + Audience Intelligence | ₹1.5K–₹5K/mo |
| **3** | Month 4–6 | Job Seekers | AI Career Agent | $20–$50/mo |
| **4** | Month 6–8 | Sales/Founders | Conversation Intelligence & Lead Gen | $100–$500/mo |
| **5** | Month 8–10 | HR/Recruiters | Talent Intelligence (B2B) | ₹50K–₹5L/year |
| **6** | Month 10–12 | Enterprise | Signal Engine & Multi-Channel Sales | $500–$5K/mo |
| **7** | Advanced | All | Cognitive Infrastructure (GraphRAG, LoRA, MCP) | Enterprise tier |

---

## Cross-Cutting: The Intelligent Ingestion Engine (IIE)

> The **core brain** of the platform. All phases reuse this. Only the Pydantic schema changes.

**Two-Tier Architecture:**
1. **Tier 1 — Network Interceptor** (Primary): Playwright listens to GraphQL/XHR responses (e.g., LinkedIn Voyager `/voyager/api/`). Cost: $0 LLM tokens. Accuracy: 100%.
2. **Tier 2 — AI Semantic Parser** (Fallback): HTML → Markdown sanitizer → LLM structured extraction via Pydantic schemas.

**SOLID Pipeline:**
1. **Dispatcher** (Redis queue) — rate limits per domain
2. **Fetchers** (abstract `BaseFetcher`) — `APIFetcher`, `StealthBrowserFetcher`
3. **Sanitizer** — HTML → clean Markdown
4. **AI Parser** — Pydantic schema + LLM structured output

| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-S01 | Dev 2 | Distributed Dispatcher (Redis + rate limiting) | 5 |
| TKT-S02 | Dev 2 | `BaseFetcher` interface (Open/Closed) | 3 |
| TKT-S03 | Dev 2 | Smart Proxy & Identity Management | 5 |
| TKT-S04 | Lead | HTML-to-Markdown Sanitizer | 2 |
| TKT-S05 | Lead | Dynamic LLM Parser Engine | 5 |
| TKT-S06 | Dev 1 | "Radar" Rule Builder UI | 5 |
| TKT-S07 | Dev 2 | Playwright Network Interceptor | 5 |
| TKT-S08 | Lead | GraphQL/JSON Schema Normalization | 3 |

---

## Phase 1: Content & Comment Engine (Weeks 1–8)

### Sprint 1: Foundation & Identity (Week 1)
| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-101 | Dev 1 | Scaffold Turborepo & Next.js | 3 |
| TKT-102 | Dev 1 | Design System (Tailwind + shadcn/ui) | 2 |
| TKT-103 | Dev 1 | Login UI & Auth State | 3 |
| TKT-104 | Dev 2 | Provision DBs & Initial Migrations | 3 |
| TKT-105 | Dev 2 | Scaffold Core API & CI/CD | 5 |
| TKT-106 | Dev 2 | LinkedIn OAuth 2.0 Flow | 5 |
| TKT-107 | Lead | Scaffold AI Webhook (FastAPI + Pydantic) | 3 |
| TKT-108 | Lead | LLM Observability & ENV Routing | 2 |
| TKT-109 | Lead | Initial System Prompts & Blocklists | 2 |
| TKT-110 | Shared | E2E Playwright Baseline Test | 3 |

### Sprint 2: AI Post Generation (Week 2)
| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-201 | Dev 1 | Post Creator Config Sidebar | 3 |
| TKT-202 | Dev 1 | Modular Editor Canvas (Hook/Body/CTA) | 5 |
| TKT-203 | Dev 1 | Wire UI → API via React Query | 3 |
| TKT-204 | Dev 2 | Post Generation API + Webhook Proxy | 5 |
| TKT-205 | Dev 2 | CRUD for Post Drafts | 3 |
| TKT-206 | Dev 2 | Rate Limiting & Timeouts | 2 |
| TKT-207 | Lead | LLM Structured Output Calls | 5 |
| TKT-208 | Lead | Dynamic Prompt Injection per Framework | 3 |
| TKT-209 | Lead | Retry Logic (Tenacity) | 2 |
| TKT-210 | Shared | E2E Test: Post Generation | 3 |

### Sprint 3: Comment Copilot & Creator Radar (Week 3)
| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-301 | Dev 1 | Creator Radar Settings UI | 2 |
| TKT-302 | Dev 1 | Comment Action Desk (Feed) | 3 |
| TKT-303 | Dev 1 | AI Comment Workspace + "Copy & Go" | 5 |
| TKT-304 | Dev 2 | Creator Tracking CRUD & Ingestion | 3 |
| TKT-305 | Dev 2 | Safe Post Ingestion Worker | 5 |
| TKT-306 | Dev 2 | Comment Generation API Route | 2 |
| TKT-307 | Lead | Comment Copilot Prompt Engineering | 5 |
| TKT-308 | Lead | Comment Webhook + Pydantic | 3 |
| TKT-309 | Shared | E2E Test: "Copy & Go" | 2 |

> **Week 4:** UI polish, edge-case bugs, security audit, beta prep.

### DB Schema (Phase 1)

**Tables:** `users`, `posts`, `tracked_creators`, `ingested_posts`, `comment_drafts`

Key indexes: `posts(user_id, status)`, `comment_drafts(user_id, status)`, `ingested_posts(tracked_creator_id, posted_at DESC)`

### AI Architecture (Phase 1)

**Post Generator:** System prompt (elite ghostwriter) → Negative blocklist → Framework-specific template → JSON output: `{hook, body_content, call_to_action}`

**Comment Copilot:** System prompt (seasoned peer) → Context ingestion → 3 strategies: `{comment_insightful, comment_contrarian, comment_supportive}`

**Webhook Contract:**
- `POST /webhooks/generate/post` → `PostGenerationResponse`
- `POST /webhooks/generate/comments` → `CommentGenerationResponse`
- Secured via `X-AI-API-Key` header, internal VPC only

---

## Phase 2: Growth System & Audience Intelligence (Months 2–4)

### Sprint 4: Idea Engine & Scheduler
| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-401 | Dev 1 | Content Calendar UI (drag-and-drop) | 5 |
| TKT-402 | Dev 1 | Idea Generator UI | 3 |
| TKT-403 | Dev 2 | LinkedIn Publishing API (UGC) | 5 |
| TKT-404 | Dev 2 | CRON Publishing Worker | 5 |
| TKT-405 | Lead | Idea Engine Prompt Chain | 3 |

### Sprint 5: Analytics & Audience Intelligence
| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-501 | Dev 1 | Analytics Dashboard (Recharts) | 5 |
| TKT-502 | Dev 1 | Audience Demographics UI | 3 |
| TKT-503 | Dev 2 | Post Metrics Ingestion Worker | 3 |
| TKT-504 | Dev 2 | Audience Graph Schema (`engagers` + `engager_classifications`) | 3 |
| TKT-505 | Lead | Audience Intelligence Classifier | 5 |
| TKT-506 | Shared | E2E Test: Scheduling + Analytics | 3 |

### The Data Flywheel (Cross-Phase Epic)
| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-F01 | Dev 1 | Implicit Feedback (Delta Capture) | 3 |
| TKT-F02 | Dev 1 | Explicit Feedback (Thumbs/Regenerate) | 2 |
| TKT-F03 | Dev 2 | `generation_telemetry` table | 3 |
| TKT-F04 | Dev 2 | Async Edit Distance Worker | 2 |
| TKT-F05 | Lead | Dynamic Few-Shot Prompt Injection | 5 |
| TKT-F06 | Lead | LLM-as-a-Judge Preference Updater | 5 |

---

## Phase 3: AI Career Agent (Months 4–6)

### Sprint 6: Job Discovery
| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-601 | Dev 2 | Point IIE Network Interceptor at Job Boards | 5 |
| TKT-602 | Dev 2 | `jobs` table + Match Scoring API | 3 |
| TKT-603 | Lead | JobSchema Semantic Parser | 3 |
| TKT-604 | Dev 1 | Job Discovery Feed UI | 5 |

### Sprint 7: Resume Intelligence
| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-701 | Dev 1 | Profile & PDF Upload UI | 3 |
| TKT-702 | Dev 1 | Tailored Application Workspace (split-screen) | 5 |
| TKT-703 | Dev 2 | PDF Text Extraction Pipeline | 2 |
| TKT-704 | Lead | Resume Optimization Prompt Chain | 8 |

### Sprint 8: Application CRM
| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-801 | Lead | Contextual Cover Letter Generator | 3 |
| TKT-802 | Dev 1 | Job Tracker Kanban Board | 5 |
| TKT-803 | Dev 1 | Semi-Automated "Apply" Helper | 3 |
| TKT-804 | Dev 2 | Job CRM API Endpoints | 2 |

---

## Phase 4: Conversation Intelligence & Lead Gen (Months 6–8)

### Sprint 9: Lead Detection & Intent Inbox
| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-901 | Dev 2 | Event-Driven Comment Processing Pipeline | 5 |
| TKT-902 | Dev 2 | Lead/`prospects` DB Schema | 3 |
| TKT-903 | Lead | Intent & Buying Signal Classifier | 5 |
| TKT-904 | Dev 1 | Lead Inbox UI (Superhuman-style) | 5 |

### Sprint 10: DM Copilot & Conversation CRM
| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-1001 | Lead | Comment-to-DM Transition Prompt | 5 |
| TKT-1002 | Dev 1 | DM Copilot Workspace | 5 |
| TKT-1003 | Dev 1 | Conversation CRM Kanban | 5 |
| TKT-1004 | Dev 2 | Pipeline State Management API | 3 |
| TKT-1005 | Dev 2 | Follow-Up Nudge Worker | 2 |

### Sprint 11: Deal Closing & Context Augmentation
| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-1101 | Dev 2 | Prospect Context Enrichment | 5 |
| TKT-1102 | Lead | Objection Handling Copilot | 5 |
| TKT-1103 | Dev 1 | Mid-Funnel Chat Interface | 3 |
| TKT-1104 | Dev 1 | Revenue ROI Dashboard | 3 |

---

## Phase 5: HR & Recruiter Layer (Months 8–10)

### Sprint 12: Talent Intelligence Engine
| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-1201 | Dev 2 | Vector Search (pgvector) Migration | 5 |
| TKT-1202 | Dev 2 | B2B Recruiter Account Architecture | 3 |
| TKT-1203 | Lead | Bi-Directional Candidate Scoring | 5 |
| TKT-1204 | Dev 1 | Talent Discovery Dashboard | 5 |

### Sprint 13: AI Sourcing Copilot
| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-1301 | Lead | Anti-Spam Sourcing Prompt | 5 |
| TKT-1302 | Dev 1 | Candidate ATS Kanban | 5 |
| TKT-1303 | Dev 1 | Safe Outreach UI | 3 |
| TKT-1304 | Dev 2 | Privacy & Opt-In Layer | 3 |

---

## Phase 6: Enterprise Signal Engine (Months 10–12)

### Sprint 14: Company Signal Detection
| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-1401 | Dev 2 | Company Data Ingestion Pipeline | 5 |
| TKT-1402 | Dev 2 | Event Trigger System | 5 |
| TKT-1403 | Lead | Signal-to-Need Mapping Prompt | 5 |
| TKT-1404 | Dev 1 | ABM Radar UI | 5 |

### Sprint 15: Multi-Channel Orchestration
| Ticket | Owner | Task | SP |
|--------|-------|------|----|
| TKT-1501 | Lead | Multi-Touch Sequence Generator | 5 |
| TKT-1502 | Dev 1 | Campaign Execution Workspace | 5 |
| TKT-1503 | Dev 1 | Enterprise Revenue Dashboard | 3 |
| TKT-1504 | Dev 2 | Email Integration (SendGrid) | 3 |

---

## Phase 7: Advanced Cognitive Infrastructure

### 1. Silicon-Optimized Local Compute
- **MLX Framework** on Apple Silicon (M4 Mac Mini)
- **Dynamic LoRA Swapping** — load tiny expert adapters per task:
  - `Viral-Creator-LoRA` → Post drafting
  - `Sales-Closer-LoRA` → DM generation
  - `Tech-Recruiter-LoRA` → Resume scoring

### 2. Semantic Memory
- **pgvector** — text embeddings (`all-MiniLM-L6-v2`, 384-dim) for Content RAG
- **GraphRAG** (Neo4j) — entity extraction + multi-hop relationship queries. Eliminates hallucinated connections.

### 3. Neuro-Symbolic AI
- **"Neuro" Layer** (LLM): Perception only — unstructured text → clean JSON
- **"Symbolic" Layer** (Golang): Deterministic DAG + business rules → execution decisions. Zero black-box actions.

### 4. Vision-Driven Automation
- Multimodal "Computer Use" models see the screen → calculate X/Y click coordinates → CSS selectors never break

### 5. LLMOps & Shadow Mode
- **Shadow Mode**: AI generates actions in "Pending" state. Humans approve/edit. System logs diffs.
- **DPO (Direct Preference Optimization)**: Train edge models on approved vs. rejected outputs
- **Automated Evals**: LLM-as-a-Judge scores against 500 historical interactions. Build fails if < 98% accuracy.

### 6. Model Context Protocol (MCP)
- Universal API layer for multi-agent ↔ tool communication (PostgreSQL, Neo4j, Playwright)
- Best for Phase 7+ when agents autonomously query GraphRAG and trigger Appium/Playwright

---

## Critical Rules

| Rule | Detail |
|------|--------|
| **Human-in-the-Loop** | Every automated action requires human approval (Copy & Go, not auto-send) |
| **No Aggressive Scraping** | Use official APIs, Proxycurl, or Network Interceptor. Never mass-scrape. |
| **Safety Scoring** | Backend enforces daily action limits even on paid tiers |
| **Zero Console Errors** | Frontend must be perfectly clean |
| **State Resilience** | Page refresh must recover all state |
| **Strict JSON Mode** | All LLM calls use structured outputs (never "please return JSON") |
| **Retry Logic** | Tenacity-based 3x retries on all LLM calls |
| **15s Timeout** | LLM calls fail fast; UI shows clean error toast |

---

## Revenue Model

| Tier | Target | Price |
|------|--------|-------|
| Free | Individual | 5 generations, 2 tracked creators |
| Creator Pro | Founders/Creators | ₹1.5K–₹5K/mo |
| Career Agent | Job Seekers | $20–$50/mo |
| Sales Copilot | Founders/Sales | $100–$500/mo |
| Recruiter | HR Teams | ₹50K–₹5L/year |
| Enterprise | Sales Teams | $500–$5K/mo per seat |

---

## IIE Progression (Same Architecture, Different Schemas)

| Phase | IIE Target | Schema | User Gets |
|-------|------------|--------|-----------|
| 1–2 | Creator Posts | `CreatorPost` | Audience & Content |
| 3 | Job Descriptions | `JobProfile` | Interviews |
| 4–5 | Resumes & Comments | `CandidateProfile` | Leads / Candidates |
| 6 | Company Signals | `LeadSignalSchema` | Enterprise Pipeline |

> *You never changed the core architecture. You just changed the Pydantic schemas and the target URLs.*
