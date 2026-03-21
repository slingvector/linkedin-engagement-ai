# Feedback Capture & System Reprioritization Plan

## Goal Description
Following the successful E2E spin-up, the focus is now pivoted to strengthening the core intelligence loop. We are pausing the ATS, Career Agent, ABM Engine, and Analytics Deep Layer features. We will retain focus on **Radar, Comment Generation, and Feed Intelligence**. 
To build a "training data moat", we will implement a new **Feedback Capture** feature to track how users interact with generated comments.

## Proposed Changes

### [Backend] Network & Service Configuration
- Update the startup commands for `core_api` and `ai_engine` to bind to `0.0.0.0` to resolve macOS frontend-backend routing issues.
- Disable the background seeders for the paused apps (e.g., `candidate_seeder`, `signal_seeder`) to save local resources and reduce noise.

### [Backend] Database & Models
#### [NEW] `apps/core_api/app/models/feedback.py`
Create a `CommentFeedback` SQLAlchemy model that captures:
```python
- post_id (String)
- original_generated_comment (Text)
- final_user_edited_comment (Text)
- was_used (Boolean)
- engagement_likes (Integer, default=0)
- engagement_replies (Integer, default=0)
```
- Integrate this model into the master DB initialization.

### [Backend] API Controllers
#### [MODIFY] `apps/core_api/app/controllers/comment_controller.py`
- Add a new endpoint `POST /api/v1/comments/feedback` to ingest the feedback from the frontend.
- Pipe this feedback into the existing LLMOps logging system (so it can be exported for Vertex AI or local Ollama fine-tuning later).

### [Frontend] UI Component
#### [MODIFY] Comment Generator Component
- Intercept the "Copy" or "Post" actions inside the Comment Generator UI.
- Capture any manual edits the user makes to the AI-generated text.
- Dispatch an API request to `POST /api/v1/comments/feedback` with the original text, the edited text, and the usage status.

## Future Step: GCP/VertexAI & Ollama
Once the feedback loop is collecting data, this repository of successful comments vs. discarded comments will be piped to VertexAI or a local Ollama instance to fine-tune the `system_resume_optimizer` or the comment generation prompts.

## Verification Plan
1. Send a test feedback payload via Swagger UI and ensure it saves to the DB and LLMOps logs.
2. Edit a comment in the Next.js UI, click "Copy/Post", and verify the network request securely transmits the diff to the backend.
