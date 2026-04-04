#!/bin/bash
# =============================================================================
# health_check.sh — Verify Mac Mini Deployment (v1.2.6)
# =============================================================================

echo "🏥 Checking LinkedIn AI Services (v1.2.6)..."

# 1. Container Status
echo "🐳 1. Docker Containers:"
docker compose -f docker-compose.prod.yml ps

# 2. Redis Connection
echo "🔴 2. Redis Ping:"
docker compose -f docker-compose.prod.yml exec redis redis-cli ping || echo "❌ Redis Not Reachable"

# 3. Postgres Connection  
echo "🐘 3. Postgres Status:"
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U postgres || echo "❌ Postgres Not Reachable"

# 4. Core API Health
echo "🐍 4. Core API Status:"
docker compose -f docker-compose.prod.yml exec core_api python3 -c "import urllib.request, json; print(json.load(urllib.request.urlopen('http://localhost:8000/health'))['status'])" | grep -q 'healthy' && echo "✅ Healthy" || echo "❌ Core API Not Reachable"

# 5. Renderer Health
echo "🎨 5. Carousel Renderer Status:"
curl -s http://localhost:8002/health | grep '"status":"ok"' || echo "❌ Renderer Not Reachable"

echo "✅ Health check complete."
