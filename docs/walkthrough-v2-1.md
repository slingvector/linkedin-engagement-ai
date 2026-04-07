# Standardizing Docker Deployments

The following industry standards have been applied to seamlessly build and deploy the LinkedIn automation platform across both ARM (Apple Silicon) and AMD64 (Cloud Run) environments:

## 1. Security and Context Optmization
A common failure state within Docker build processes is mistakenly transmitting the local context (including repository data and local credential files) to the Docker Daemon, resulting in bloated images and key leakage.

We have fortified the ecosystem by adding explicit `.dockerignore` templates to all microservice directories:
- `[NEW]` [apps/core_api/.dockerignore](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/.dockerignore)
- `[NEW]` [apps/ai_engine/.dockerignore](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/.dockerignore)
- `[NEW]` [apps/carousel_renderer/.dockerignore](file:///Users/cortex/ventures/linkedin-as-a-service/apps/carousel_renderer/.dockerignore)
- `[NEW]` [apps/web/.dockerignore](file:///Users/cortex/ventures/linkedin-as-a-service/apps/web/.dockerignore)

This guarantees exclusions for `.env`, `__pycache__`, `node_modules`, `.next`, and `.git` caches.

## 2. Platform-Agnostic Build Wrapper
The root cause of your prior Cloud Run failures (`Container manifest type must support amd64/linux`) manifested precisely from attempting to leverage Google Cloud registry artifacts that were generated natively on Apple Silicon.

To guarantee all terminal operations build using explicit platform bindings without tainting the local Dockerfile ecosystem, a root `Makefile` was introduced:
- `[NEW]` [Makefile](file:///Users/cortex/ventures/linkedin-as-a-service/Makefile)

### New Standard Commands:
* `make dev` - Safe native local hot-reloading (ARM).
* `make deploy-gcp-core-api` - Wraps `buildx`, enforces `--platform linux/amd64`, tags properly, and pushes securely to the GCP container registry for `core_api`.
* `make deploy-all` - Executes synchronous remote artifact packaging for ALL containerized services targeting GCP.
