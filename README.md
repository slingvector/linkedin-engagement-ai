# LinkedIn-as-a-Service (LinkedIn Engagement AI) 🚀

LinkedIn-as-a-Service is an open-source, fully automated, ultra-scale LinkedIn growth AI platform. The system operates as a tripartite microservice mesh designed to securely scrape engagement data, ideate trending content using Google DeepMind's Gemini 2.5 Flash models, simulate "organic" human-level comments, and automatically schedule ghostwritten posts—all completely natively, without triggering LinkedIn's anti-bot infrastructure.

## 🏗️ High-Level Design (HLD) Architecture

The application is segregated into three primary isolated components:

```mermaid
flowchart TD
    subgraph ClientTier [Client Tier]
        UI["Next.js + Tailwind React Frontend"]
    end

    subgraph StateTier [State and Proxy Tier]
        CoreAPI["Core API (FastAPI)"]
        DB[("PostgreSQL")]
        Worker["Celery + Redis Scheduler"]
        Playwright["Playwright Headless Scraper"]
    end

    subgraph IntelligenceTier [AI Proxy Mesh]
        AIEngine["AI Engine (FastAPI)"]
        Google["Google Developer API (Gemini 2.5)"]
        Ollama["Local Ollama Inference"]
    end

    UI -- "OAuth JWT / NextAuth" --> CoreAPI
    CoreAPI -- "FastAPI SQLAlchemy" --> DB
    CoreAPI -- "Triggers Jobs" --> Worker
    Worker -- "Secure Proxies" --> Playwright
    Playwright -- "Headless Browser" --> LinkedIn(("LinkedIn Servers"))
    CoreAPI -- "X-AI-API-Key Webhook JSON" --> AIEngine
    AIEngine -- "Pydantic SDK Output" --> Google
    AIEngine -- "Safe Fallback" -.-> Ollama
```

---

## 🧩 Core Ecosystem Components

### 1. `apps/web` (The Next.js Client)
A stunning, responsive frontend built with React 18, Next.js 14, TailwindCSS, Radix UI, and React Query.
* **Role:** The control center for the user.
* **Features:** Idea Generation dashboard, Post Creator Canvas (with Contrarian/Story framework integrations), Scheduled Post timelines, and Comment Generation Radar.
* **Resiliency:** Handles Pydantic validation trace arrays gracefully and uses optimistic UI updates to simulate rapid load times against AI bottlenecks.

### 2. `apps/core_api` (The Stateful Brain)
A robust FastAPI backend using SQLAlchemy 2.0 (Async) mapped directly into a PostgreSQL database.
* **Role:** Secure proxy handling user authentications (LinkedIn OAuth), saving generated posts/ideas into the database, and issuing commands to background scrapers.
* **Features:** Strict UUID schema enforcement, background background worker delegation via Celery, and API security token validation.

### 3. `apps/ai_engine` (The Intelligence Layer)
A stateless, blazingly fast secondary FastAPI microservice connected to Google's DeepMind Gemini models and local Ollama deployments.
* **Role:** Sits behind a VPC firewall (accessed via `X-AI-API-Key`) receiving raw text prompts from the Core API and outputting perfectly formatted, string-escaped structured JSON files.
* **Features:**
  * **Native Pydantic Structure:** Enforces `PostGenerationResponse` via the Google SDK to strictly guarantee un-escaped LLM tokenizer crashes never happen natively.
  * **Local AI Fallback:** If the external LLM models (e.g., `gemini-2.5-flash`) suffer a catastrophic outage, the node silently fails over to `llama3.2:latest` running locally in Docker/Ollama to guarantee uptime.

---

## 🛠️ Local Development Boot Sequence

You can launch all 3 primary environments simultaneously in your terminal via our background daemon bootscript.

### 1. Booting The Full Stack
Instead of juggling 3 terminals, you can daemonize the entire stack to seamlessly run silently.
```bash
./tmp/start_all.sh # Or run them individually via the lines below
```

### 2. Individual Boot Commands

**Start the Next.js Frontend:**
```bash
cd apps/web
npm install
npm run dev
# App runs on http://localhost:3000
```

**Start the Core API:**
```bash
cd apps/core_api
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Swagger Docs available at http://localhost:8000/docs
```

**Start the AI Engine:**
```bash
cd apps/ai_engine
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
# Swagger Docs available at http://localhost:8001/docs
```

---

## 🔐 Environment Setup

Each respective app directory contains a `.env.example` file. Make sure to duplicate these into `.env` files and inject your keys.

**Crucial Variables (`apps/ai_engine/.env`):**
```env
GEMINI_API_KEY="AIzaSyBhO...your_key_here"
AI_ENGINE_PORT=8001
AI_ENGINE_API_KEY="change_this_internal_microservice_key" # Syncs with apps/core_api/.env
```

---

## 📈 Release Milestones
* **v1.0.0 (Current):** Stable migration spanning full Google Developer GenAI API arrays, Next.js frontend schema safeties, and full Post/Idea execution stability. 

*Designed recursively with Agentic coding assistance.*
