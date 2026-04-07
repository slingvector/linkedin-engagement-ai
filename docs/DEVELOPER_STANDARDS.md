# Developer Standards — LinkedIn-as-a-Service

Guidelines for all contributors. Backend and frontend in one place.

---

## Backend Standards

### Architecture
- **Controller → Service → Repository** layered pattern. No business logic in controllers. No DB calls in controllers.
- **SOLID principles**: Single responsibility, open/closed for extension, dependency inversion via FastAPI `Depends`.
- Group code by **feature domain**, not by technical layer.

### Code Rules
- All endpoints use **Pydantic schemas** for input/output — never raw dicts.
- All LLM calls use **structured JSON output mode** — never string-parse LLM responses.
- All LLM calls wrapped in `asyncio.wait_for(..., timeout=N)` — no open-ended waits.
- All retry logic uses **Tenacity** with `retry_if_exception_type` on specific transient errors only (not bare `Exception`).
- All config from **environment variables or `config.yaml`** — zero hardcoding.
- **snake_case** everywhere in Python.

### Database
- Use **SQLAlchemy async** (`AsyncSession`) for all DB operations.
- Always set `connect_args={"timeout": 10}` on `create_async_engine` — asyncpg defaults to `None` (infinite).
- Background workers use `AsyncSessionLocal` directly, not `get_db()` FastAPI dependency.
- Never run dev servers pointed at the `postgres_prod_data` volume.

### Fault Tolerance
- Graceful degradation: reduced functionality > crash.
- Structured logging via `structlog` with JSON format.
- Health check endpoints: `/health` (liveness) and `/readiness` (startup).
- Circuit-break patterns on LLM calls — fail fast at defined timeout.

### Docker & Deployment
- All services containerized. "Runs on my machine" is not acceptable.
- Multi-arch builds: `linux/amd64` + `linux/arm64` in CI/CD.
- Image tags always use the **GitHub repo name** (`linkedin-engagement-ai`), not the local folder name.

### Testing
- Unit tests mock all dependencies.
- Integration tests test service ↔ DB interactions.
- No tests that require a live external service (LinkedIn API, Vertex AI) in the main suite.

---

## Frontend Standards

### Architecture
- **Next.js App Router** with TypeScript.
- API calls via centralized `apiV2` client (`apps/web/src/lib/api.ts`) — **never** raw `fetch("http://localhost:8000/...")`.
- Always use **relative paths** (`/api/v1/...`) — proxied through Next.js rewrites. Absolute URLs break tunnel/production deployments.
- Server Components for data fetching, Client Components for interactivity.

### State Management
- **TanStack Query (React Query)** for server state. Local `useState` for UI-only state.
- Always guard nullable data: use `!data || data.length === 0` — **not** `data?.length === 0` (optional chaining returns `undefined`, not `false`).
- Never mutate state directly.

### Performance
- Lazy load non-critical components with `dynamic()`.
- Memoize expensive renders with `useMemo` / `useCallback` — but don't premature-optimize.
- Zero console errors in production.

### Error Handling
- Error boundaries at page level — crash one section, not the whole app.
- React Query `isError` states always render a user-friendly toast or inline message.
- No silent failures — log all API errors to `structlog` compatible output.

### Accessibility
- Semantic HTML5 elements throughout.
- All interactive elements keyboard-navigable.
- Sufficient color contrast ratios.

### Testing
- Component tests via Jest + React Testing Library.
- All critical user flows covered (post generation, radar, calendar).

---

## Critical Non-Negotiables

| Rule | Detail |
|------|--------|
| Human-in-the-Loop | Every automated LinkedIn action requires explicit user approval |
| No Aggressive Scraping | Use official APIs or `linkedin-read-flow` only |
| Strict JSON Mode | All LLM calls use structured outputs |
| 30s LLM Timeout | Wrap all AI calls in `asyncio.wait_for()` |
| Retry Scope | Only retry `asyncio.TimeoutError`, `ConnectionError` — not bare `Exception` |
| Safety Limits | Backend enforces daily action limits on all tiers |
| Page Refresh Recovery | All UI state must survive a hard refresh |
