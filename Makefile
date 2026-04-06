# Variables
GCP_REGISTRY ?= us-central1-docker.pkg.dev/mcr-relay-1772228380/linkedin-saas
IMAGE_TAG ?= 2.0.0

# Local Development Commands
.PHONY: dev build-local
dev:
	docker compose up --build

build-local:
	docker compose -f docker-compose.local.yml build

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
