# Phase 2: Feedback Capture & Core Intelligence

## 1. Network & Setup Fixes
- [x] Fix Uvicorn API binding to `0.0.0.0` so the Next.js frontend can connect reliably without timeout errors.
- [x] Shut down background seeders for paused modules (ATS, Career Agent, ABM, Analytics) to save resources.

## 2. Feedback Capture Component (Step 4)
- [x] **Database Model:** Create an SQLAlchemy model to store feedback (original comment, user edits, chosen comment, engagement results).
- [x] **API Endpoint:** Create a `POST /feedback/comments` endpoint in `core_api`.
- [x] **LLMOps Integration:** Pipe captured feedback to the existing LLMOps logs.
- [ ] **Frontend Integration:** Update the Comment Generator UI to send the feedback payload when a user copies, posts, or edits a generated comment.

## 3. GCP / Vertex AI / Ollama Mock Data
- [ ] Investigate and plan integration of Vertex AI or local Ollama for generating high-quality mock data (optional/later step).
