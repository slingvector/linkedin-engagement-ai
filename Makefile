# Load .env automatically if present
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Variables (These act as fallbacks if missing from .env)
GCP_PROJECT_ID ?= universal-trail-492511-i7
GCP_REGION ?= us-central1
GCP_REPO_NAME ?= linkedin-saas

# Dynamic Registry Resolution
GCP_REGISTRY = $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT_ID)/$(GCP_REPO_NAME)
IMAGE_TAG ?= 2.0.0

# Internal Helpers
check-docker:
	@docker info > /dev/null 2>&1 || (echo "Error: Docker is not running. Please start Docker Desktop." && exit 1)

# Local Development Commands
.PHONY: dev build-local
dev:
	docker compose up --build

build-local: check-docker
	docker compose -f docker-compose.local.yml build

staging: check-docker
	@echo "Starting LinkedIn SaaS Staging Environment (GHCR-based)..."
	docker compose -f docker-compose.local.yml pull
	docker compose -f docker-compose.local.yml up -d
	@echo "🚀 Staging services are booting up!"
	@echo "🔗 Run 'docker compose -f docker-compose.local.yml logs tunnel' to find your public URL."

# Safe Platform-Independent Cloud Deployment Commands
.PHONY: deploy-gcp-core-api deploy-gcp-ai-engine deploy-gcp-carousel deploy-gcp-web deploy-all

deploy-gcp-core-api:
	@echo "Building and pushing core-api natively for GCP (amd64)..."
	docker buildx build --platform linux/amd64 -t $(GCP_REGISTRY)/core-api:$(IMAGE_TAG) --push ./apps/core_api

deploy-gcp-ai-engine:
	@echo "Building and pushing ai_engine natively for GCP (amd64)..."
	docker buildx build --platform linux/amd64 -t $(GCP_REGISTRY)/ai-engine:$(IMAGE_TAG) --push ./apps/ai_engine

deploy-gcp-carousel:
	@echo "Building and pushing carousel_renderer natively for GCP (amd64)..."
	docker buildx build --platform linux/amd64 -t $(GCP_REGISTRY)/carousel-renderer:$(IMAGE_TAG) --push ./apps/carousel_renderer

deploy-gcp-web:
	@echo "Building and pushing web natively for GCP (amd64)..."
	docker buildx build --platform linux/amd64 -t $(GCP_REGISTRY)/web:$(IMAGE_TAG) --push ./apps/web

deploy-all: deploy-gcp-core-api deploy-gcp-ai-engine deploy-gcp-carousel deploy-gcp-web
	@echo "All services successfully built for linux/amd64 and pushed to Artifact Registry!"
