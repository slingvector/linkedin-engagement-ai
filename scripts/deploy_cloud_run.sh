#!/bin/bash
set -e

echo "=========================================="
echo "🚀 LinkedIn SaaS Cloud Run Deployment Orchestrator"
echo "=========================================="

# Automatically load vars if .env exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

export PROJECT_ID=${GCP_PROJECT_ID:-"universal-trail-492511-i7"}
export REGION=${GCP_LOCATION:-"us-central1"}
export SQL_INSTANCE="${PROJECT_ID}:${REGION}:linkedin-saas-db"
export REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/linkedin-saas"
export SERVICE_ACCOUNT="linkedin-ai-agent@${PROJECT_ID}.iam.gserviceaccount.com"
export IMAGE_TAG=${IMAGE_TAG:-"2.0.0"}

echo "[System Check] Verifying essential secrets before deployment..."
# Required secrets
for secret in DATABASE_URL LINKEDIN_CLIENT_ID LINKEDIN_CLIENT_SECRET; do
  if ! gcloud secrets describe $secret --project="$PROJECT_ID" >/dev/null 2>&1; then
      echo "❌ ERROR: $secret not found in Secret Manager."
      echo "Please create it first:"
      echo "  echo -n 'YOUR_VALUE' | gcloud secrets create $secret --data-file=- --project=$PROJECT_ID"
      exit 1
  fi
done
echo "✅ Secrets verified."

echo "--------------------------------------------------------"
echo "🏗️ Phase 1: Deploy Background Engines (No URL Dependencies)"
echo "--------------------------------------------------------"

echo "Deploying Carousel Renderer..."
gcloud run deploy carousel-renderer \
  --image="${REGISTRY}/carousel-renderer:${IMAGE_TAG}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --allow-unauthenticated \
  --format="value(status.url)" > /tmp/cr_url.txt
CAROUSEL_URL=$(cat /tmp/cr_url.txt)
echo "✅ Carousel Renderer URL: $CAROUSEL_URL"

echo "Deploying AI Engine..."
gcloud run deploy ai-engine \
  --image="${REGISTRY}/ai-engine:${IMAGE_TAG}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --service-account="${SERVICE_ACCOUNT}" \
  --set-env-vars="LLM_PROVIDER=vertexai,GCP_PROJECT_ID=${PROJECT_ID},GCP_LOCATION=${REGION},VERTEX_MODEL=${VERTEX_MODEL:-gemini-2.5-flash},AI_ENGINE_API_KEY=${AI_ENGINE_API_KEY:-internal_service_key_789}" \
  --allow-unauthenticated \
  --format="value(status.url)" > /tmp/ai_url.txt
AI_ENGINE_URL=$(cat /tmp/ai_url.txt)
echo "✅ AI Engine URL: $AI_ENGINE_URL"

echo "--------------------------------------------------------"
echo "🏗️ Phase 2: Deploy Core API (First Pass)"
echo "--------------------------------------------------------"
# In this pass, we connect the database and background services,
# but we leave CORS wide open because we don't know the Web URL yet.

echo "Deploying Core API..."
gcloud run deploy core-api \
  --image="${REGISTRY}/core-api:${IMAGE_TAG}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --add-cloudsql-instances="${SQL_INSTANCE}" \
  --client-name="linkedin-saas" \
  --set-secrets="DATABASE_URL=DATABASE_URL:latest,LINKEDIN_CLIENT_ID=LINKEDIN_CLIENT_ID:latest,LINKEDIN_CLIENT_SECRET=LINKEDIN_CLIENT_SECRET:latest" \
  --set-env-vars="AI_ENGINE_URL=${AI_ENGINE_URL},CAROUSEL_RENDERER_URL=${CAROUSEL_URL},CORS_ALLOWED_ORIGINS=[\"*\"],AI_ENGINE_API_KEY=${AI_ENGINE_API_KEY:-internal_service_key_789},JWT_SECRET=${JWT_SECRET:-fallback_secret_xyz}" \
  --allow-unauthenticated \
  --format="value(status.url)" > /tmp/core_url.txt
CORE_API_URL=$(cat /tmp/core_url.txt)
echo "✅ Core API URL: $CORE_API_URL"

echo "--------------------------------------------------------"
echo "🏗️ Phase 3: Deploy Frontend Web App"
echo "--------------------------------------------------------"

echo "Deploying Web..."
gcloud run deploy web \
  --image="${REGISTRY}/web:${IMAGE_TAG}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --set-env-vars="NEXT_PUBLIC_API_URL=${CORE_API_URL}/api/v1,NEXT_PUBLIC_CORE_API_URL=${CORE_API_URL}" \
  --allow-unauthenticated \
  --format="value(status.url)" > /tmp/web_url.txt
WEB_URL=$(cat /tmp/web_url.txt)
echo "✅ Web Frontend URL: $WEB_URL"

echo "--------------------------------------------------------"
echo "🔄 Phase 4: Full Synchronization (Chicken-and-Egg Fix)"
echo "--------------------------------------------------------"

echo "Syncing Core API CORS Origin to match $WEB_URL..."
gcloud run deploy core-api \
  --image="${REGISTRY}/core-api:${IMAGE_TAG}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --set-env-vars="AI_ENGINE_URL=${AI_ENGINE_URL},CAROUSEL_RENDERER_URL=${CAROUSEL_URL},CORS_ALLOWED_ORIGINS=[\"${WEB_URL}\"],LINKEDIN_REDIRECT_URI=${WEB_URL}/auth/callback,FRONTEND_URL=${WEB_URL},AI_ENGINE_API_KEY=${AI_ENGINE_API_KEY:-internal_service_key_789},JWT_SECRET=${JWT_SECRET:-fallback_secret_xyz}" \
  --update-secrets="DATABASE_URL=DATABASE_URL:latest,LINKEDIN_CLIENT_ID=LINKEDIN_CLIENT_ID:latest,LINKEDIN_CLIENT_SECRET=LINKEDIN_CLIENT_SECRET:latest" \
  --allow-unauthenticated

echo "Syncing Web FRONTEND_URL to $WEB_URL..."
gcloud run deploy web \
  --image="${REGISTRY}/web:${IMAGE_TAG}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --set-env-vars="NEXT_PUBLIC_API_URL=${CORE_API_URL}/api/v1,NEXT_PUBLIC_CORE_API_URL=${CORE_API_URL},FRONTEND_URL=${WEB_URL},LINKEDIN_REDIRECT_URI=${WEB_URL}/auth/callback" \
  --allow-unauthenticated

echo "=========================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "=========================================="
echo "Public Web App: ${WEB_URL}"
echo "Important: Head over to LinkedIn Developer Portal and whitelist this OAuth Callback URI:"
echo "    -->  ${WEB_URL}/auth/callback"
echo "=========================================="
