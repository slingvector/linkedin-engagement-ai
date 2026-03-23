# LinkedIn-as-a-Service: Cloud Deployment Strategy
This document outlines the production-ready infrastructure plan to sustain background workers, AI webhook orchestration, and robust UI delivery across the LinkedIn OS ecosystem.

---

## 🏗️ 1. Platform Infrastructure Strategy

Because your application is highly decoupled across three main layers, a **hybrid deployment** allows you to leverage the strengths of specialized providers while keeping costs extremely low.

### A. Next.js Frontend (`apps/web`) ➔ **Vercel**
* **Why**: Native support for Next.js App Router, global edge caching, and seamless Turborepo cache sharing.
* **Mechanism**: Connects directly to your GitHub repository. Vercel automatically deploys every push to Git and provides instant preview URLs for Pull Requests.

### B. Core API & PostgreSQL/Redis (`apps/core_api`) ➔ **Render or Railway**
* **Why**: You need a unified environment for both your `uvicorn` FastAPI server and long-running `asyncio` ingestion/publishing workers. Render and Railway both offer zero-devops Docker builds in addition to fully managed Postgres (`pgvector` compatible) and Redis out of the box.
* **Services**:
  1. Web Service (The API Endpoints)
  2. Background Worker (The `ingestion_worker.py` and publication loops)
  3. Managed PostgreSQL (Phase 1 DB)
  4. Managed Redis Server (For future Task Queues / Rate Limits)

### C. AI Engine (`apps/ai_engine`) ➔ **Modal / Fly.io / Bare Metal GPU**
* **Why**: The deployment of this service depends heavily on your LLM strategy. 
* **If API-Bound (OpenAI/Anthropic)**: Deploy this perfectly identically to the Core API on Render/Railway. It just acts as a stateless webhook orchestrator.
* **If Local Models (Ollama/LoRA)**: You will need dedicated GPU access. Deploying this custom Docker container to **Modal** (serverless GPU scaling) or renting a persistent GPU droplet from providers like RunPod or Hetzner is essential.

---

## ⚙️ 2. The Role of GitHub (CI/CD Orchestration)

GitHub is not just for version control; it becomes the neurological center of your deployments.

1. **Automated Testing**: Create a `.github/workflows/test.yml` file. Before any code is merged to `main`, GitHub Actions will automatically spin up isolated environments, run your `pytest` suite for the AI Engine and Core API, and ensure 100% test passing before deployment.
2. **Environment Synchronization**: You can define your production secrets (e.g., `SUPABASE_KEY`, `OPENAI_API_KEY`) securely inside GitHub Secrets. Your deployment platforms (Render, Vercel) natively read these securely upon building.
3. **Monorepo Build Strategies**: By integrating Turborepo with GitHub Actions, your CI pipeline will intelligently skip rebuilding `apps/ai_engine` if you only modified `apps/web`, saving you immense compilation time and costs.
4. **Issue Tracking for LLMOps**: As your AI generates user-facing draft errors, you can pipe these directly into GitHub Issues for your team to handle using GitHub webhooks.

---

## 🛠️ 3. Execution Plan (Next Steps)

If you're ready to spin this up, we would take the following path:
- [ ] 1. Define distinct `.env.production` secrets for your target environments.
- [ ] 2. Containerize the Python applications (`Dockerfile` for Core API + Background Workers).
- [ ] 3. Create the Database migrations schema (e.g. Alembic) to run on the managed database.
- [ ] 4. Link Vercel to your Monorepo to deploy the `apps/web` package.
- [ ] 5. Link Render/Railway to the Monorepo to deploy `apps/core_api`.

---

## ☁️ 4. Google Cloud Platform (GCP) Alternative

GCP is highly attractive because of its robust **"Always Free" Tier** and its ecosystem for developers (like the Google for Startups Cloud Program). If you want to centralize on GCP, here is how the architecture splits and what it costs.

### The Maximum "Free Tier" Architecture ($0 / month)
You can actually run this entire system for free if you are willing to do slightly more manual DevOps for the databases.

| Service | GCP Product | Free Tier Limits | Strategy |
|---------|-------------|------------------|----------|
| **Frontend (Next.js)** | **Cloud Run** | 2M requests/mo, 180k vCPU-seconds | Cloud Run natively scales to zero. Your Next.js App Router API and SSR pages will run entirely within the free limits. |
| **Core API (FastAPI)** | **Cloud Run** | (Shared with Frontend) | Webhook traffic and REST APIs will scale to zero, staying 100% free. |
| **AI Engine** *(If using OpenAI)* | **Cloud Run** | (Shared with Frontend) | Same as Core API. Fast response times ensure minimal vCPU usage. |
| **Database (PostgreSQL)** | **Compute Engine (e2-micro)** | 1 Non-preemptible `e2-micro` VM per month | Cloud SQL (Managed Postgres) **does not** have a free tier. To stay at $0, you deploy PostgreSQL directly onto your 1 perpetually free `e2-micro` Linux VM. |
| **Redis Queue** | **Compute Engine (e2-micro)** | Shared with DB VM | Memorystore (Managed Redis) is expensive. Install Redis via Docker on the same free `e2-micro` VM. |
| **Background Ingestion Worker** | **Compute Engine (e2-micro)** | Shared with DB VM | Cloud Run background jobs that never sleep will exceed the free tier. Run `ingestion_worker.py` alongside your DB on the free VM. |

### The "Managed" Production Architecture (~$25 - $40 / month)
If you want GCP to manage backups, scaling, and database maintenance natively:

*   **Cloud Run (Frontend + APIs)**: Still **$0/month** due to generous scaling-to-zero allowances.
*   **Cloud SQL (PostgreSQL + pgvector)**: A shared-core `db-f1-micro` instance costs roughly **$10–$15/month**.
*   **Cloud Run (Always-On Worker)**: Allocating constant CPU for `ingestion_worker.py` prevents it from sleeping. Running 1 vCPU 24/7 costs roughly **$10–$20/month**.
*   **Redis**: Use a Serverless Redis like Upstash (Third-party, generous $0 free tier), or host it on the free e2-micro VM to avoid GCP Memorystore's ~$35/mo minimum.

**What about GPU Models for the AI Engine?**
If you plan to run open-source models (like Llama 3 via Ollama) locally in Phase 7, GCP does **not** offer a free tier for GPUs. A basic Nvidia T4 attached to a VM will cost around ~$250/month. 
*Note: New GCP accounts receive a standard **$300 credit** covering 90 days, which you can burn through to test GPUs and Cloud SQL for free initially.*
