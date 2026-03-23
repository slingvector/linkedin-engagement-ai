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

## **Lessons Learned**
1. **Repository Naming:** Ensure that the local development folder name and the remote GitHub repository name are consistent, or use the exact remote name in deployment manifests.
2. **Multi-Arch Strategy:** For teams developing on Mac (ARM) but deploying to Cloud (AMD), multi-architecture builds should be enabled in CI/CD from day one to ensure dev/prod parity and local testing compatibility.
