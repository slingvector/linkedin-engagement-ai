# Creator Radar - Test Plan & Verification Strategy

## Objective
To systemically verify the Creator Radar's migration to an Autonomous Discovery Engine, its AI Strategy generation, and its integration into the LLMOps data flywheel (ShadowActionLogs). We will progressively test the backend primitives via Swagger before validating the complete end-to-end (E2E) frontend user flow.

---

## 1. Backend Verification (Swagger API)

### A. Intelligent Ingestion Engine (Live Playwright Scraper)
*Note: This runs autonomously as a background worker off the main FastAPI event loop, but its results can be verified via the database.*
1. **Pre-requisite:** Export a valid `linkedin_li_at_cookie` in `.env` or [config.yaml](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/config.yaml).
2. **Action:** Start the FastAPI application.
3. **Observation:** Monitor the terminal logs for:
   - `[viral_discovery_navigating]`
   - `[viral_discovery_posts_found]`
   - `[viral_post_injected]`
4. **Verification:** Inspect the Postgres database using pgAdmin/DataGrip or your ORM viewer.
   - `users` table: Verify an admin exists.
   - [tracked_creators](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/controllers/creator_controller.py#55-63) table: Verify new rows are auto-generated with `discovered-XXXX` identifiers.
   - `ingested_posts` table: Verify the scraped content is successfully inserted mapped to the new creator.

### B. AI Comment Copilot Generation
1. **Setup:** Open Swagger UI (`http://localhost:8000/docs`).
2. **Endpoint:** `POST /api/v1/copilot/generate`
3. **Action:** Construct a payload providing an ingested `post_url` and raw `post_content`.
4. **Verification:**
   - Execute the request.
   - Assert the HTTP response matches the strict Pydantic JSON schema containing array outputs for `insightful`, `contrarian`, and `supportive`.
   - Monitor the log payload to confirm Gemini was the underlying router, passing safely to Ollama if API keys were missing.

### C. The LLMOps Data Flywheel (ShadowActionLog)
1. **Endpoint:** `POST /api/v1/comments/feedback`
2. **Action:** Assuming the AI generated: `"Great thoughts on Go vs Python!"`
   - Build a JSON body where `original_generated_comment` = `"Great thoughts on Go vs Python!"`
   - Build `final_user_edited_comment` = `"Great thoughts on Go vs Python! I actually prefer Rust for speed."` (Simulating a human altering the draft).
   - `was_used` = `true`.
3. **Verification:**
   - Ensure you receive a `200 Success` response.
   - Immediately query the `shadow_action_logs` database table.
   - Look for the newest row where `action_type = "comment_generation"`.
   - **Crucial Metric:** Assert that `edit_similarity_score` is a decimal between `0.0` and `1.0` (it should accurately represent the sequence matching delta between the two strings above).

---

## 2. Frontend / End-to-End Verification

### A. The Radar Interface
1. **Action:** Navigate the Next.js React app to the `/radar` or `/dashboard` route.
2. **Verification:**
   - The UI feed successfully mounts `ingested_posts`.
   - Since we shifted away from hardcoded targets, you should see dynamically scraped Viral Posts displaying organic Engagement Metrics (Mocked from the HTML structural pass).

### B. Copilot Interactions
1. **Action:** Click "Draft Comment" or "Generate Strategy" on the first organic post in the timeline.
2. **Verification:**
   - Wait for the Loading State. 
   - Verify the modal populates precisely 3 distinct comment strategy buttons without React hydration crashes.

### C. Human-in-the-Loop Flywheel completion
1. **Action:** Click one of the proposed drafts to populate the Text Area.
2. **Action:** Manually type an additional sentence into the text box (emulating human review).
3. **Action:** Click the "Copy & Track" / "Post to LinkedIn" button.
4. **Verification:** 
   - Open your browser's Network Tab -> XHR. 
   - Confirm a `POST` request fires to `/api/v1/comments/feedback` containing your edited text.
   - Confirm the API returns `200 OK`. 
   - (The LLMOps dashboard will now automatically ingest this telemetry).
