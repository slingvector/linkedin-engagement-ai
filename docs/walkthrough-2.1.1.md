# Docker Architecture & Registry Name Fixes

I have addressed the two primary issues blocking your production deployment on Mac: image name mismatches and architecture incompatibility.

## Changes Made

### 1. Corrected GHCR Registry Names
The Docker Compose file was using the local folder name (`linkedin-as-a-service`) instead of the repository name (`linkedin-engagement-ai`) used in GitHub Actions.

#### [MODIFY] [docker-compose.prod.yml](file:///Users/cortex/ventures/linkedin-as-a-service/docker-compose.prod.yml)
- updated all image paths to `ghcr.io/slingvector/linkedin-engagement-ai-*`
- removed obsolete `version: '3.8'` attribute.

### 2. Fixed Architecture Mismatch
The GitHub Action only builds `linux/amd64` images, while your M-series Mac expects `linux/arm64`.

#### [MODIFY] [docker-compose.prod.yml](file:///Users/cortex/ventures/linkedin-as-a-service/docker-compose.prod.yml)
- added `platform: linux/amd64` to all services. This forces Docker Desktop on Mac to run the images using Rosetta 2 emulation.

#### [MODIFY] [.github/workflows/release.yml](file:///Users/cortex/ventures/linkedin-as-a-service/.github/workflows/release.yml)
- added `docker/setup-qemu-action` for cross-platform builds.
- enabled building both `linux/amd64` and `linux/arm64` for all future releases.

## Verification

### Local Fix
By adding `platform: linux/amd64` to the compose file, you can now run:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```
This will successfully pull and run the current AMD64 images.

### Future CI/CD
Once you push a new tag (e.g., `v1.1.6`), the updated GitHub Action will build native `linux/arm64` images, which will perform much faster on your Apple Silicon Mac without needing Rosetta.
