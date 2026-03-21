# Admin & Operator Guide: Real-World Testing

Welcome to the internal operations guide for the LinkedIn-as-a-Service platform. This guide explains how to administer the backend services, prepare the environment for live data execution, and manage ingestion credentials.

## 1. Environment Preparation (Zero-State)
To prepare the system for real human users and prevent polluted test data from interfering with LLM results, always run the database reset script before beginning a new testing epoch.
```bash
cd apps/core_api
source .venv/bin/activate
export PYTHONPATH=.
python scripts/reset_db.py
```
> [!WARNING]
> This command will permanently drop all tables and recreate them. Only execute this in a development or staging environment!

## 2. API Key Configuration
The `AI Engine` requires valid LLM credentials to process LinkedIn posts and generate comment strategies.
1. Navigate to [apps/ai_engine/.env](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/.env).
2. Ensure you have populated the `OPENAI_API_KEY` variable with an active, billed key.
3. If leveraging Vertex AI for internal tools, ensure `VERTEX_AI_PROJECT_ID` is set (optional).

## 3. Starting the Microservices
After configuring the database and [.env](file:///Users/cortex/ventures/linkedin-as-a-service/.env) files, you must start the two backend microservices on distinct ports so the Next.js application can route correctly. Open two separate terminals:

**Terminal 1 (Core API):**
```bash
cd apps/core_api
source .venv/bin/activate
export PYTHONPATH=.
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 (AI Engine):**
```bash
cd apps/ai_engine
source .venv/bin/activate
export PYTHONPATH=.
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## 4. Provisioning the Root User & LinkedIn Cookies
Because our architecture separates the frontend OAuth flow from backend headless scraping, you must manually tie a real LinkedIn session cookie (`li_at`) to the test user's profile.

1. In Chrome, log into a dummy or real LinkedIn account.
2. Open DevTools (F12) > Application > Cookies > `https://www.linkedin.com`.
3. Copy the value of the `li_at` cookie.
4. Run the user provisioning script:
   ```bash
   cd apps/core_api
   python scripts/create_test_user.py
   ```
5. Follow the CLI prompts. Paste your copied `li_at` cookie when asked. The system will encrypt it via Fernet and associate it with the new user UUID.

## 4. Running the Playwright Scraper
With a provisioned root user, the system can bypass LinkedIn's public hurdles.
The [apps/core_api/app/workers/playwright_scraper.py](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/workers/playwright_scraper.py) acts as the Tier 1 Network Interceptor.
- In production, this executes as a background cron or a Redis queue consumer.
- For manual E2E Testing, you can invoke it via CLI directly by passing the target profile URL and the decrypted `li_at` cookie.

## 5. Monitoring Feedback Loops (LLMOps)
When an end-user copies a generated comment from the frontend, a payload is POST'd to `/api/v1/comments/feedback`. 
- Monitor the standard output of `core_api` for `comment_feedback_received` logs.
- Regularly export the `comment_feedbacks` SQL table to gather human-edited comments. This dataset will form the "training data moat" necessary for future fine-tuning of localized Ollama models or Vertex AI instances.
