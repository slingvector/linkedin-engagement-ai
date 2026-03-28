# Creator Radar & Comment Copilot: Deep Dive

Based on the [Master Project Blueprint](file:///Users/cortex/ventures/linkedin-as-a-service/docs/master_project_blueprint.md) and [Walkthrough](file:///Users/cortex/ventures/linkedin-as-a-service/docs/walkthrough.md), the Creator Radar feature is the foundation of the Phase 1 goal: moving from simple content generation to a true "Growth System & Audience Intelligence" tool. It represents the realization of the platform's core philosophy: *"Distribution first → Product second → Automation last."*

Here is a deep architectural breakdown of how it works under the hood.

---

## 1. The Intelligent Ingestion Engine (IIE)

The Radar is powered by the **IIE**, which is the central "brain" of the platform that scales across all 7 phases.

*   **Asynchronous Background Ingestion:** Instead of the frontend making slow scraping calls, the user simply registers a `TrackedCreator`. The `ingestion_worker.py` (a long-running `asyncio` loop) acts as a distributed dispatcher that continuously polls for new posts.
*   **Two-Tier Architecture Constraint:** The blueprint specifies a 2-tier design:
    *   **Tier 1 (Target):** A Playwright-based Network Interceptor capturing clean `GraphQL/XHR` responses straight from the browser (0 LLM overhead, 100% accuracy).
    *   **Tier 2 (Fallback):** An AI Semantic Parser that converts raw HTML to clean markdown, then uses Pydantic + LLMs to extract structured posts gracefully.
*   **Data Models:** The ingestion populates the `ingested_posts` table via `CreatorRepository` utilizing `JOIN` logic against the master [tracked_creators](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/controllers/creator_controller.py#55-63) list, generating the "Action Desk" feed.

## 2. The AI Comment Copilot

When a user clicks "Generate Comment Strategies" on an ingested post, they trigger the Copilot Webhook.

*   **Strict Webhook APIs:** The UI hits `core_api` (`/api/v1/copilot/generate`), which securely proxies the request to the `ai_engine` via a private VPC internal webhook (`POST /webhooks/generate/comments`) authenticated by an `X-AI-API-Key`.
*   **The Trinity Strategy:** The AI Engine leverages `system_comment.txt`. It structurally ignores free-text responses and utilizes "Strict JSON Mode" (`response_format={"type": "json_object"}`) to force the LLM to return exactly three strategic angles:
    1.  **Insightful:** Adding an authoritative perspective.
    2.  **Contrarian:** Respectfully disagreeing or showing an alternative edge case.
    3.  **Supportive:** Purely driving engagement and applause.
*   **Resiliency:** The AI Engine uses the `Tenacity` library to automatically retry failed LLM extractions (up to 3x with exponential backoff) and utilizes a dual-model LLM router (Gemini → Local Ollama fallback).

## 3. The LLMOps "Data Flywheel" (Copy & Go)

The most advanced segment of Creator Radar is the **Phase 7 LLMOps Cognitive Infrastructure** built into its feedback loops.

*   **Shadow Action Logs (DPO Data Sink):** When a user edits an AI-generated strategy (e.g., changes the wording to be more authentic) and clicks "Select & Track," the `/api/v1/copilot/posts/{id}/drafts` endpoint records a crucial event in PostgreSQL.
*   **Capturing the Delta:** The system records both the `[AI Draft]` and the `[Human Final Edit]`.
*   **Why? (Direct Preference Optimization):** The goal isn't just to save a comment. By recording the exact edit distance (what the AI got wrong VS what the human fixed), you are creating a perfect dataset. A background `LLM-as-a-Judge` worker scores these delta diffs. This powers "Dynamic Few-Shot Prompt Injection," meaning the more you use Creator Radar, the more the AI learns your exact writing style to inject into future generations dynamically.

---

## Technical Summary
The Creator Radar is not just an interface; it's a closed-loop supervised learning pipeline. It seamlessly connects an asynchronous data scraper (`ingestion_worker`), a strictly typed LLM microservice (`ai_engine`), and an active user feedback layer to continuously build high-value context for organic LinkedIn growth.
