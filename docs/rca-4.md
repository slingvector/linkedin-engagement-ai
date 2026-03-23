# Root Cause Analysis: Job Discovery Hang

## Problem Statement
The Job Discovery feature in the frontend web application failed to load data during end-to-end testing, hanging indefinitely on loading skeletons.

## Root Cause
The `fetch` request in [src/app/jobs/page.tsx](file:///Users/cortex/ventures/linkedin-as-a-service/apps/web/src/app/jobs/page.tsx) (and several other pages) was hardcoded to an internal IP and port: `http://192.168.31.242:8000/api/v1/career/jobs`. This internal IP was unreachable from the test environment, causing the network request to hang pending a timeout.

## Previous Fix vs. Production Standard
The initial fix replaced `192.168.31.242` with `localhost`. While this unblocked local testing, a mass find-and-replace of raw connection strings directly into individual React components is an anti-pattern. Industry standards mandate extracting base URLs and API configurations into centralized network layers using Environment Variables (`.env`) and configured API clients.

## Corrective Actions
1. **Define Environment Variables**: Set `NEXT_PUBLIC_CORE_API_URL` (or equivalent) in [.env.local](file:///Users/cortex/ventures/linkedin-as-a-service/apps/web/.env.local) to point to `http://localhost:8000/api/v1` for local development.
2. **Centralize API Client**: Utilize or upgrade the centralized client (e.g., [src/lib/api.ts](file:///Users/cortex/ventures/linkedin-as-a-service/apps/web/src/lib/api.ts)) to read the base URL from the environment automatically.
3. **Refactor Components**: Replace raw `fetch("http://localhost:8000/api/v1/...")` calls in over 10 [.tsx](file:///Users/cortex/ventures/linkedin-as-a-service/apps/web/src/app/ats/page.tsx) files with calls mapping to the centralized API client or an environment-aware fetch wrapper. This decouples the UI components from the deployment topology.
