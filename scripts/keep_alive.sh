#!/bin/bash
# =============================================================================
# keep_alive.sh — 24/7 Mac Mini Service Management
# Usage: ./keep_alive.sh [NGROK_DOMAIN]
# =============================================================================

# 1. Parse Arguments
COMPOSE_FILE="docker-compose.prod.yml"
case "$1" in
    --prod) COMPOSE_FILE="docker-compose.prod.yml"; shift ;;
    --local) COMPOSE_FILE="docker-compose.local.yml"; shift ;;
    *) echo "💡 Defaulting to --prod. Use --local for pre-prod.";;
esac

NGROK_DOMAIN=$1

if [ -z "$NGROK_DOMAIN" ]; then
    echo "❌ Error: Please provide your Ngrok Static Domain as an argument."
    echo "Usage: ./keep_alive.sh [--prod|--local] my-fixed-name.ngrok-free.app"
    exit 1
fi

echo "🚀 Setting up 24/7 Persistence (${COMPOSE_FILE}) for: ${NGROK_DOMAIN}"

# 2. Install PM2 globally if missing
if ! command -v pm2 &> /dev/null; then
    echo "🏗️ Installing PM2 Process Manager..."
    npm install -g pm2
fi

# 3. Start Docker Compose Stack via PM2
echo "🐳 Starting Docker Stack (${COMPOSE_FILE})..."
pm2 start "docker compose -f ${COMPOSE_FILE} up" --name "linkedin-ai-stack"

# 3. Start Ngrok Static Tunnel via PM2
echo "🌐 Starting Permanent Tunnel..."
pm2 start "ngrok http --domain=${NGROK_DOMAIN} 8000" --name "linkedin-ai-tunnel"

# 4. Save & Setup Startup
pm2 save
echo "✅ Persistence Layer Activated."
echo "👉 YOUR STABLE URL: https://${NGROK_DOMAIN}"
echo "👉 Use 'pm2 status' to view your services."
echo "👉 Use 'pm2 logs' to see real-time updates."
