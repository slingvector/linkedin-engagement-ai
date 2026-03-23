# Root Cause Analysis (RCA)

## 1. Registry Image Name Mismatch

### **Problem**
The command `docker compose -f docker-compose.prod.yml up` failed because it could not find the image `ghcr.io/slingvector/linkedin-as-a-service-ingestion_worker:v1.1.5`.

### **Root Cause**
The GitHub Actions workflow ([release.yml](file:///Users/cortex/ventures/linkedin-as-a-service/.github/workflows/release.yml)) uses the repository name (`github.repository`) to tag images. The repository is named `linkedin-engagement-ai`. However, the [docker-compose.prod.yml](file:///Users/cortex/ventures/linkedin-as-a-service/docker-compose.prod.yml) file used `linkedin-as-a-service`, which was likely the local folder name where the project was initialized.

### **Impact**
Docker could not pull the images from the GitHub Container Registry because the name in the manifest did not match the name in the compose file.

### **Resolution**
Updated all image references in [docker-compose.prod.yml](file:///Users/cortex/ventures/linkedin-as-a-service/docker-compose.prod.yml) to use the correct repository name: `ghcr.io/slingvector/linkedin-engagement-ai-*`.

---

## 2. Architecture Mismatch (ARM64 vs. AMD64)

### **Problem**
After fixing the name mismatch, the deployment failed with the error: 
`no matching manifest for linux/arm64/v8 in the manifest list entries`.

### **Root Cause**
- The user is running on an Apple Silicon Mac (`Anujs-Mac-mini`), which uses the `linux/arm64` architecture.
- The GitHub Actions workflow was building images using the default `ubuntu-latest` runner without specifying multi-platform support, resulting in `linux/amd64` only images.
- By default, Docker on Mac attempts to pull the native `linux/arm64` version of an image. Since only `linux/amd64` existed in GHCR, the pull failed.

### **Impact**
The production stack could not be started on local Mac hardware.

### **Resolution**
1. **Immediate Fix:** Added `platform: linux/amd64` to all services in [docker-compose.prod.yml](file:///Users/cortex/ventures/linkedin-as-a-service/docker-compose.prod.yml). This instructs Docker Desktop to use Rosetta 2 to emulate the AMD64 architecture, allowing the current images to run on Mac.
2. **Long-term Fix:** Updated [.github/workflows/release.yml](file:///Users/cortex/ventures/linkedin-as-a-service/.github/workflows/release.yml) to use `docker/setup-qemu-action` and configured `docker/build-push-action` to build for both `linux/amd64` and `linux/arm64` platforms.

---

## 3. AI Engine Connectivity & LLM Initialization

### **Problem**
Idea generation was failing with a `502 Bad Gateway` from `core_api`. Logs showed `ValueError: No API key was provided` in `ai_engine`.

### **Root Cause**
1.  **Environment Variable Mismatch:** [docker-compose.prod.yml](file:///Users/cortex/ventures/linkedin-as-a-service/docker-compose.prod.yml) used `X_AI_API_KEY` for the `ai_engine` service, whereas the application code expected `AI_ENGINE_API_KEY` to authenticate internal requests.
2.  **LLM Client Initialization Crash:** The [LLMService](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/app/services/llm_service.py#18-140) in `ai_engine` was instantiating the Gemini client `google.genai.Client` in the [__init__](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/app/services/idea_service.py#28-31) constructor without checking if the `GEMINI_API_KEY` was provided. This caused a crash on application startup, preventing the Ollama fallback from executing.

### **Impact**
The `ai_engine` was unavailable for any requests, breaking content generation.

### **Resolution**
1.  **Synced Names:** Harmonized environment variable names across [docker-compose.prod.yml](file:///Users/cortex/ventures/linkedin-as-a-service/docker-compose.prod.yml) and the codebase (`AI_ENGINE_API_KEY`).
2.  **Graceful Fallback:** Modified [LLMService](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/app/services/llm_service.py#18-140) to only initialize the Gemini client if an API key is present. If missing, it now logs a warning and correctly falls back to using local Ollama.

---

## **Lessons Learned**
1. **Repository Naming:** Ensure that the local development folder name and the remote GitHub repository name are consistent, or use the exact remote name in deployment manifests.
2. **Multi-Arch Strategy:** For teams developing on Mac (ARM) but deploying to Cloud (AMD), multi-architecture builds should be enabled in CI/CD from day one to ensure dev/prod parity and local testing compatibility.
3. **Resilient Service Initialization:** Don't crash in constructors for missing optional services (like an LLM provider). Use lazy loading or guards to allow fallbacks to function.
