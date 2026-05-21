# LinkedIn Engagement AI - Frontend

The Next.js 14 web interface for the LinkedIn Engagement AI platform. This is the user-facing control center for automated LinkedIn content generation and engagement.

## 🎨 Features

- **Post Generator Canvas** - Create AI-powered LinkedIn posts with Contrarian/Story frameworks
- **Idea Brainstorm Dashboard** - Generate 50+ post ideas from a single prompt using Gemini AI
- **Scheduled Post Timeline** - Visualize and manage your posting schedule
- **Comment Generation Radar** - Auto-generate contextual comments for engagement tracking
- **Real-time Sync** - Live WebSocket connection to backend for instant updates
- **OAuth Authentication** - LinkedIn OAuth integration via NextAuth.js

## 🛠️ Tech Stack

- **Framework**: Next.js 14 (App Router)
- **UI Library**: React 18 + Radix UI
- **Styling**: TailwindCSS
- **State Management**: React Query (TanStack Query)
- **Authentication**: NextAuth.js + LinkedIn OAuth
- **Validation**: Pydantic models from backend API

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn
- Backend API running on `http://localhost:8000`

### Installation

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## 📁 Project Structure

```
src/
├── components/        # Reusable React components
│   ├── PostCanvas.tsx
│   ├── IdeaGenerator.tsx
│   ├── CommentRadar.tsx
│   └── ScheduleTimeline.tsx
├── pages/            # App Router pages
│   ├── dashboard/
│   ├── generate/
│   └── schedule/
├── hooks/            # Custom React hooks
├── utils/            # Helper functions
└── styles/           # Global styles
```

## 🔐 Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key
LINKEDIN_CLIENT_ID=your-client-id
LINKEDIN_CLIENT_SECRET=your-client-secret
```

## 🚢 Building for Production

```bash
npm run build
npm run start
```

## 📚 API Integration

This frontend connects to the Core API at `http://localhost:8000`. Key endpoints:

- `POST /api/generate-post` - Generate LinkedIn post
- `POST /api/generate-ideas` - Generate post ideas
- `POST /api/schedule-post` - Schedule a post
- `GET /api/posts` - Fetch user's posts

See the main [LinkedIn Engagement AI README](../../README.md) for full architecture details.

## 🎯 Key Features Explained

### Post Generator Canvas
Smart editor with AI suggestions based on LinkedIn engagement patterns.

### Idea Brainstorm
Leverage Gemini 2.5 to generate 50+ contextual post ideas in seconds.

### Comment Generation
Auto-generate contextual comments to boost post engagement.

## 🤝 Contributing

See main project [CONTRIBUTING.md](../../CONTRIBUTING.md)

## 📄 License

Proprietary - Part of LinkedIn Engagement AI platform
