# Root Cause Analysis: Production Hardening Edge Cases

## 1. Next.js Static Export Failure (Suspense Boundary)
**Symptom:** 
Docker deployment failed during the `npm run build` step inside the `apps/web` container.
**Error Logs:** 
`useSearchParams() should be wrapped in a suspense boundary at page "/auth/callback".`

**Root Cause:**
In Next.js App Router (v13+), reading URL parameters via `useSearchParams()` during the build process forces the framework to de-optimize the route from static generation to dynamic rendering. Next.js actively prevents this build ambiguity by throwing a hard error if the hook is used outside of a React `<Suspense>` boundary, ensuring that the client-side hydration doesn't block the static shell.
**Resolution:**
Extracted the core logic into an internal `AuthCallbackContent` component and wrapped it entirely inside a `<Suspense>` boundary in the default exported `AuthCallbackPage`.

---

## 2. Alembic Startup Crash (Missing Relation)
**Symptom:**
The Core API container failed to start on fresh environments (like staging or prod).
**Error Logs:**
`asyncpg.exceptions.UndefinedTableError: relation "shadow_action_logs" does not exist`

**Root Cause:**
When Alembic was initialized on the developer's laptop, the `alembic revision --autogenerate` command was executed against an existing database where SQLAlchemy's `create_all()` had already built the tables. Consequently, Alembic generated a "delta" migration (only containing the *differences*, such as the new `oauth_states` table and a foreign key modification). When `entrypoint.sh` ran `alembic upgrade head` on a completely empty production database, the delta migration tried to `ALTER` a table that had never been created.
**Resolution:**
1. Dropped the illegitimate delta migration.
2. Spun up an isolated, completely empty Postgres database (`linkedin_empty`).
3. Ran `alembic revision --autogenerate` against the empty DB to generate a true `0001_initial_schema` baseline containing every `create_table` instruction.
4. Manually stamped the local developer database (`alembic stamp head`) so it safely bypasses the table creation step locally but initializes them globally.

---

## 3. Ingestion Worker Unrestrained Crash Loop
**Symptom:**
The LinkedIn scraping container spammed logs and continuously restarted every second.
**Error Logs:**
`read_flow_auth_failed: LinkedIn triggered a 2FA/CAPTCHA challenge.`

**Root Cause:**
The `linkedin-read-flow` package raised a `SystemExit` because the stored `li_at` authentication cookie was either expired or flagged by LinkedIn for a security check. The script caught the error, successfully dispatched a Telegram alarm, and then immediately `return`ed, terminating the python process. Because the server runs under Docker Compose with a `restart: unless-stopped` policy, Docker immediately restarted the container—resulting in a tight loop that aggressively hammered LinkedIn's auth endpoints, risking a total account ban.
**Resolution:**
Implemented a `time.sleep(3600)` blocking delay right before the `return` statement in the worker's failure trap. This forces the container to effectively "pause" for an hour when auth fails, giving the human operator ample time to manually clear the CAPTCHA in a browser and update the `.env` file without the system escalating the issue.
