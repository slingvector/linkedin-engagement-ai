# Docker Build & Deployment Best Practices

This document outlines the industry-standard best practices adopted in this repository for seamless multi-architecture Docker container workflows, specifically dealing with Apple Silicon (ARM64) local development and GCP Cloud Run (AMD64) production deployments.

## The Core Challenge
When developing on a local Apple Silicon (`arm64`) machine and deploying to GCP Cloud Run or AWS ECS (`amd64`), developers often encounter architectures mismatch errors (e.g., `Container manifest type must support amd64/linux`). Addressing this incorrectly can ruin local development performance or break production.

---

## 1. Local Emulation vs Build Time Specification

### Approach A: Hardcoding Platform in `Dockerfile` (Anti-Pattern)
*Example:* `FROM --platform=linux/amd64 python:3.12-slim`

| Pros | Cons |
|---|---|
| **Simple** - Guarantees the image is always `amd64`, regardless of which tool is used to build it. | **Performance Hit** - Forcing `amd64` on an `arm64` Macbook forces Docker Desktop to run Apple's Rosetta 2 emulation. |
| **Fail-Safe for Prod** - Prevents `arm64` deployments from reaching production by accident. | **Failing Native Compiles** - Low-level C-extensions or Python packages (like `weasyprint` or `grpcio`) run 2x-5x slower locally or may fail to compile entirely under emulation. |

### Approach B: Build-time Platform Targets (Industry Standard & Adopted)
*Example:* `FROM python:3.12-slim` + `docker buildx build --platform linux/amd64 ...`

| Pros | Cons |
|---|---|
| **Native Speed** - `docker compose up --build` evaluates on your Mac natively (`arm64`), granting lightning-fast rebuilds. | **Requires Tooling** - You must remember to use `docker buildx build --platform` specifically when pushing to GCP manually. |
| **CI/CD Friendly** - GitHub Actions (`ubuntu-latest`) runs natively on `amd64`. You don't have to change anything for CI workflows. | |

---

## 2. Adopted Best Practices 

### A. Implementing `.dockerignore` Universally
**Why?** Docker sends the entire directory payload ("context") to the Docker daemon on every build.
* **Security Risk:** Accidentally copying `.env` files can leak API keys onto public repositories or container registries.
* **Bloat:** Transferring `node_modules/`, `.git/`, and `__pycache__` increases image sizes by hundreds of megabytes.
* **Standard:** Every microservice in this repository maintains a dedicated `.dockerignore` file.

### B. CI/CD Over Manual Terminal Deployments
**Why?** CI pipelines guarantee determinism.
* The `.github/workflows/release.yml` utilizes `docker/setup-buildx-action` which natively constructs both `linux/amd64` and `linux/arm64` variants.
* By using a pipeline, we decouple the build artifact from our local laptop's operating system quirks.

### C. Standardized Makefile for Emergency Terminal Overrides
**Why?** We still need a path to rapidly push targeted fixes without waiting on CI queues.
* Using a central `Makefile` eliminates human error.
* Executing `make deploy-gcp-core-api` enforces the `docker buildx build --platform linux/amd64 --push` requirement seamlessly to the Artifact Registry.

---

## Summary Workflow
1. **Local Dev:** Use `make dev` or `docker compose up --build` (Builds natively `arm64` for maximum speed).
2. **Production Release:** Merge PR to `main` with a release tag. Let GitHub actions compile `amd64` via `release.yml`.
3. **Emergency Hotfix to GCP:** Run `make deploy-gcp-core-api` from your Mac terminal to safely cross-compile and push.
