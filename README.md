# LinkedIn Engagement AI - Enterprise Growth Platform 🚀

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.100+-009485.svg)](https://fastapi.tiangolo.com/)
[![Next.js 14](https://img.shields.io/badge/next.js-14-black.svg)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-15+-336791.svg)](https://www.postgresql.org/)
[![License: Proprietary](https://img.shields.io/badge/license-proprietary-red.svg)](#license)

> **Enterprise-grade, fully automated LinkedIn growth AI platform** - Generate unlimited content, schedule posts, engage audiences, and scale presence using Gemini AI and headless automation.

## 🎯 What It Does

**LinkedIn Engagement AI** is a tripartite microservice architecture that transforms LinkedIn growth into an automated, intelligent system:

1. **AI-Powered Content Generation** - Create data-driven posts using Gemini 2.5 with story/contrarian frameworks
2. **Headless Browser Automation** - Scrape engagement data, simulate human behavior, schedule posts via Playwright
3. **Background Job Orchestration** - Process 1000+ LinkedIn profiles, schedule posts, and track metrics via Celery + Redis
4. **Real-time Dashboard** - Monitor growth metrics, view scheduled posts, and adjust strategy on the fly

### 💡 Key Capabilities

✅ Generate 50+ post ideas from a single prompt  
✅ Create viral-ready posts with proven engagement patterns  
✅ Auto-generate contextual comments for engagement  
✅ Schedule posts across multiple accounts  
✅ Monitor engagement metrics in real-time  
✅ Local AI fallback (Ollama) for reliability  
✅ Enterprise-grade error handling & retry logic

---

## 🏗️ Architecture

LinkedIn Engagement AI is a **tripartite microservice mesh**:

```mermaid
flowchart TD
    subgraph ClientTier [Client Tier]
        UI["Next.js + Tailwind React Frontend"]
    end

    subgraph StateTier [State and Proxy Tier]
        CoreAPI["Core API (FastAPI)"]
        DB[("PostgreSQL")]
        Worker["Celery + Redis Scheduler"]
        Playwright["Playwright Headless Scraper"]
    end

    subgraph IntelligenceTier [AI Proxy Mesh]
        AIEngine["AI Engine (FastAPI)"]
        Google["Google Developer API (Gemini 2.5)"]
        Ollama["Local Ollama Inference"]
    end

    UI -- "OAuth JWT / NextAuth" --> CoreAPI
    CoreAPI -- "FastAPI SQLAlchemy" --> DB
    CoreAPI -- "Triggers Jobs" --> Worker
    Worker -- "Secure Proxies" --> Playwright
    Playwright -- "Headless Browser" --> LinkedIn(("LinkedIn Servers"))
    CoreAPI -- "X-AI-API-Key Webhook JSON" --> AIEngine
    AIEngine -- "Pydantic SDK Output" --> Google
    AIEngine -- "Safe Fallback" --> Ollama
```

---

## 📦 Core Components

### 1. **Frontend** (`apps/web`)
React 18 + Next.js 14 + TailwindCSS dashboard for content creation and analytics
- Post Generator Canvas with AI suggestions
- Idea Brainstorm Dashboard (50+ ideas in seconds)
- Scheduled Post Timeline
- Comment Generation Radar
- Real-time engagement tracking

**Tech Stack**: Next.js 14, React 18, TypeScript, TailwindCSS, Radix UI, React Query

### 2. **Core API** (`apps/core_api`)
Stateful FastAPI backend - the heart of the system
- OAuth LinkedIn authentication
- Content generation orchestration
- Post scheduling and publishing
- Engagement metric collection
- Background job delegation

**Tech Stack**: FastAPI, SQLAlchemy 2.0, PostgreSQL, Celery, Redis, Pydantic v2

### 3. **AI Engine** (`apps/ai_engine`)
Intelligent content generation microservice
- Gemini 2.5 Flash integration for ultra-fast inference
- Local Ollama fallback for reliability
- Structured JSON output via Pydantic
- Prompt injection defense
- Rate limiting and cost optimization

**Tech Stack**: FastAPI, Google GenAI SDK, Ollama, Pydantic

---

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** (recommended for full stack)
- **Python 3.9+** (for local development)
- **Node.js 18+** (for frontend)
- **PostgreSQL 15+** (or use Docker)
- **Redis 7+** (for job queue)
- **Playwright browsers** (auto-installed)
- **Google API key** (for Gemini access)
- **LinkedIn account** (for authentication)

### Option 1: Full Stack with Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/slingvector/linkedin-engagement-ai.git
cd linkedin-engagement-ai

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# - GEMINI_API_KEY
# - LINKEDIN_OAUTH_CLIENT_ID/SECRET
# - DATABASE_URL

# Start everything
docker-compose up -d

# Verify services
docker-compose ps

# Access:
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
# AI Engine: http://localhost:8001/docs
```

### Option 2: Local Development

**Start PostgreSQL & Redis:**
```bash
docker-compose up -d postgres redis
```

**Start Frontend:**
```bash
cd apps/web
npm install
npm run dev
# Runs on http://localhost:3000
```

**Start Core API:**
```bash
cd apps/core_api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Swagger UI: http://localhost:8000/docs
```

**Start AI Engine:**
```bash
cd apps/ai_engine
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
# Swagger UI: http://localhost:8001/docs
```

**Start Celery Workers:**
```bash
cd apps/core_api
celery -A app.celery worker --loglevel=info
```

---

## 🔐 Environment Setup

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/linkedin_ai
REDIS_URL=redis://localhost:6379

# Google Gemini API
GEMINI_API_KEY=AIzaSyBhO...your_key_here
GEMINI_MODEL=gemini-2.5-flash

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:3000/api/auth/callback

# AI Engine Security
AI_ENGINE_API_KEY=your_secure_internal_key
AI_ENGINE_PORT=8001

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_SECRET=your_nextauth_secret

# Optional: Local LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

---

## 📊 Usage Examples

### Generate Post Ideas
```bash
curl -X POST http://localhost:8000/api/generate-ideas \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AI and automation",
    "count": 50,
    "audience": "tech entrepreneurs"
  }'
```

### Create a Post
```bash
curl -X POST http://localhost:8000/api/generate-post \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "framework": "story",
    "idea": "How I automated LinkedIn with AI",
    "tone": "authentic"
  }'
```

### Schedule Post
```bash
curl -X POST http://localhost:8000/api/schedule-post \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "My post text...",
    "scheduled_for": "2024-06-01T09:00:00Z"
  }'
```

---

## 🧪 Testing

Run tests:
```bash
# Frontend tests
cd apps/web && npm test

# API tests
cd apps/core_api && pytest

# AI Engine tests
cd apps/ai_engine && pytest
```

---

## 📈 Performance Metrics

- **Post Generation**: <2 seconds (Gemini Flash)
- **Idea Generation**: <5 seconds (50 ideas)
- **Fallback Latency**: <10 seconds (Local Ollama)
- **API Response Time**: <100ms (p99)
- **Database Queries**: <50ms (average)

---

## 🔄 Workflow Pipeline

1. **User Input** → Create post idea or brainstorm request
2. **Content Generation** → AI Engine generates options using Gemini
3. **Validation** → Pydantic models ensure output quality
4. **Persistence** → Save to PostgreSQL
5. **Scheduling** → Celery queues publishing jobs
6. **Publication** → Playwright headless browser automates LinkedIn UI
7. **Monitoring** → Real-time metric tracking and analytics

---

## 🛠️ Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Next.js 14, TailwindCSS, TypeScript |
| **Backend API** | FastAPI, SQLAlchemy 2.0, PostgreSQL |
| **AI/ML** | Google Gemini 2.5, Ollama (local), Pydantic v2 |
| **Task Queue** | Celery, Redis |
| **Browser Automation** | Playwright, Headless Chrome |
| **Authentication** | LinkedIn OAuth, JWT, NextAuth.js |
| **Deployment** | Docker, Docker Compose, Vercel (Frontend) |

---

## 🚢 Deployment

### Deploy Frontend to Vercel
```bash
vercel deploy
```

### Deploy Backend to Heroku/Railway
```bash
git push heroku main
```

### Production Checklist
- [ ] Set all environment variables
- [ ] Configure LinkedIn OAuth for production domain
- [ ] Set up database backups
- [ ] Configure Redis persistence
- [ ] Enable CORS for production domain
- [ ] Set up monitoring/logging (Sentry, DataDog)
- [ ] Configure rate limiting

---

## 📚 Documentation

- [Architecture Specification](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Contributing Guidelines](CONTRIBUTING.md)

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

Proprietary - Internal use only. All rights reserved.

---

## 👨‍💻 Author

**Slingvector**
- GitHub: [@slingvector](https://github.com/slingvector)
- LinkedIn: [Slingvector](https://linkedin.com/in/slingvector)

---

## 🙏 Acknowledgments

Built with:
- Google DeepMind Gemini API
- Playwright for browser automation
- FastAPI ecosystem
- React/Next.js community

---

## 📞 Support

For issues and questions:
1. Check [Issues](https://github.com/slingvector/linkedin-engagement-ai/issues)
2. Review [Documentation](docs/)
3. Open a new issue with detailed information

---

## 🗺️ Roadmap

- [ ] Multi-account management
- [ ] Advanced analytics dashboard
- [ ] A/B testing framework
- [ ] Content calendar with AI suggestions
- [ ] Engagement rate predictions
- [ ] Influencer collaboration tools
- [ ] API rate limit optimization
- [ ] Self-healing automation via vision models

---

**⭐ If you find this useful, please star the repository!**
