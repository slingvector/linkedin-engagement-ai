# Gemini API Integration Guide

This document captures the architectural decisions surrounding our integration with Google Gemini, specifically outlining the pitfalls of mixing the Consumer and Enterprise SDKs.

## The Two Distinct Gemini SDKs

Google currently hosts two completely separate onboarding paths for their AI models. Understanding the difference is critical to avoid `404 Not Found` or authentication errors.

### 1. Developer API (Google AI Studio) - **Active Implementation**
- **SDK Name:** `google-genai` (Imports via `from google import genai`)
- **Key Prefix:** `AIzaSy...`
- **Authentication:** Straightforward API Key.
- **Why we chose this:** We chose this SDK because you had a direct API Key (starting with `AIza`) generated from MakerSuite/AI Studio rather than a billed Google Cloud Project.
- **Setup in `.env`:**
  ```env
  GEMINI_API_KEY="AIzaSy...your_key_here"
  ```

### 2. Enterprise API (Google Cloud Vertex AI) - **Not Used**
- **SDK Name:** `google-cloud-aiplatform` (Imports via `import vertexai`)
- **Key Prefix:** Doesn't use keys. Uses Google Cloud IAM Service Accounts / ADC.
- **Why we abandoned this:** Vertex AI explicitly requires an active, billed Google Cloud Project (`my-company-project-1234`), a specified region (`us-central1`), and OAuth JSONs or Application Default Credentials (`gcloud auth application-default login`).
- **Setup in `.env` (If you ever migrate here in the future):**
  ```env
  VERTEX_AI_PROJECT_ID="your-gcp-project-123"
  VERTEX_AI_LOCATION="us-central1"
  ```
  *(Note: You would also need to run `pip install google-cloud-aiplatform` and swap the initializers inside `llm_service.py`.)*

## Deprecation Notice for Legacy Apps
Many internet tutorials reference an old package named `google-generativeai` (used prior to 2025). **Do not use this package.** It is fully deprecated and will fail when attempting to query modern Gemini 2.x models.

We strictly use the unified `google-genai` package.

## Current Supported Models
As of 2026, the standard models to query directly via the Developer API include:
- `gemini-2.5-flash` (Lightning fast, primary choice)
- `gemini-2.5-pro` (Deep reasoning, used for complex analysis)

You can always review the `test_genai_models.py` script in the `/tmp/` directory of the server to natively list the models your specific API key has authorized access to.
