# Real-World E2E Testing: Readiness Checklist

To transition from the initial isolated mock-data phase to a real-world "LinkedIn-as-a-Service" test, we need to replace simulated data boundaries with live integrations. Here is the step-by-step framework to achieve system readiness from scratch.

## 1. Authentication & Identity
- [ ] **Auth Strategy:** Integrate a real frontend authentication provider (e.g., NextAuth, Supabase, or Clerk).
- [ ] **Data Wiping:** Run [init_master_db.py](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/scripts/init_master_db.py) to completely wipe and recreate the database schema, removing all randomly generated mock users and posts.
- [ ] **User Registration Flow:** Test registering a fresh, real user in the Next.js frontend and asserting their profile persists in the `core_api` database.

## 2. Real LinkedIn Ingestion (Tier 1 Network Interceptor)
Currently, [apps/core_api/app/workers/ingestion_worker.py](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/workers/ingestion_worker.py) loops and generates random text.
- [ ] **Scraping Worker:** Build or integrate a real headless browser worker (Playwright/Puppeteer) or a 3rd party API (like Proxycurl/Phantombuster) to fetch a creator's real recent posts.
- [ ] **Credentials Vault:** Determine how we are storing the real LinkedIn session cookie (`li_at`) to authenticate the scraper, or if we are using generic proxy accounts.
- [ ] **Redis Queueing:** Ensure the real ingestion worker pushes raw JSON payloads into our Redis instance, which `core_api` will consume.

## 3. Real LLM Generation (AI Engine)
Currently, the AI Engine might be configured to fail or return static text if keys are missing.
- [ ] **OpenAI / VertexAI Keys:** Inject a valid, billed LLM API Key into [apps/ai_engine/.env](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/.env).
- [ ] **Prompt Tuning:** Review the underlying generation prompts inside the AI Engine to ensure they are equipped to handle completely arbitrary real-world LinkedIn posts without hallucinating.

## 4. Full Pipeline Verification Flow
Once the above is configured, the Real-World E2E Test will follow this exact script:
1. **Login:** User authenticates into the Next.js app.
2. **Add Radar Target:** User pastes a *real* LinkedIn Profile URL in the Radar page.
3. **Trigger Scrape:** The frontend sends a POST request. The Playwright worker wakes up, navigates to that profile, and scrapes the 5 most recent posts.
4. **Action Desk Feed:** The UI polls and ultimately displays real post data.
5. **AI Copilot:** User clicks "Generate Comment Strategies". The AI Engine processes the real post text using OpenAI/VertexAI and returns 3 diverse, context-aware comment drafts.
6. **Publishing / Copy & Track:** User edits a drafted comment, clicks "Copy & Track Feedback", and the data flows back into the LLMOps tracking schema securely.

### Pending Architecture Decision:
*Should we write our own Python-based Playwright scraper in a new microservice, use an existing Node.js tool, or pay for a 3rd-party LinkedIn JSON API?*
