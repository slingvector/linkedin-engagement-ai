# Local-Prod Operations & Best Practices
An operator checklist and administration guide for safely running, stopping, and maintaining the production Docker ecosystem on your local Mac Mini server.

---

## 🟢 Safe Start Procedures (Booting Up)

When you are ready to boot up the application for external traffic or your own long-term usage:

- [ ] **Pull Latest Code**: Ensure your Mac Mini is up-to-date with your latest GitHub commits using `git pull`.
- [ ] **Rebuild the Swarm**: Always boot using the build flag to ensure Next.js and FastAPI compile your latest code changes into their frozen image snapshots.
  ```bash
  docker compose -f docker-compose.prod.yml up -d --build
  ```
- [ ] **Verify Initialization**: If this is your very first time running the deployment or you completely wiped your volumes, initialize the production database schema:
  ```bash
  docker compose -f docker-compose.prod.yml exec core_api python -m scripts.init_master_db
  ```
- [ ] **Check Swarm Health**: Verify that all 6 containers show a status of [Up](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/schemas/post.py#64-73) and haven't instantly exited.
  ```bash
  docker compose -f docker-compose.prod.yml ps -a
  ```
- [ ] **Expose Traffic**: Start your remote Cloudflare tunnel (e.g., `cloudflared tunnel --url http://localhost:3000`) so the application is publicly accessible.

---

## 🛑 Safe Shutdown Procedures (Spinning Down)

If you need to update the Mac Mini, migrate physical servers, or halt operations:

- [ ] **Stop Traffic First**: Close or terminate your Cloudflare Tunnel `cloudflared` process. This immediately stops incoming requests so users don't face mid-request crashes.
- [ ] **Graceful Swarm Teardown**: Issue the down command rather than force-killing Docker Desktop.
  ```bash
  docker compose -f docker-compose.prod.yml down
  ```
  *(**Why?** This sends a polite `SIGTERM` signal to all containers. The database gets time to flush data to the disk, and the background ingestion workers cleanly save their current web-scraping progress before shutting off).*
- [ ] **Confirm Shutdown**: Run `docker ps` to ensure no orphaned containers are clinging to your system ports.

---

## ⚠️ Cautionary Steps & Best Practices

### 1. Database Isolation
- **Rule**: Never run your local development servers (`npm run dev` or local FastAPI) pointed at the `postgres_prod_data` volume.
- **Why**: You want absolute separation between your experimental sandbox data and your live production system. Test things locally on the default `linkedin_os` database, and let Docker exclusively handle `linkedin_os_prod`.

### 2. Handling Environment Variables
- **Rule**: If you add new API keys (like a new `X_AI_API_KEY`), you must inject them into the Docker network.
- **How**: Update the `environment` blocks in [docker-compose.prod.yml](file:///Users/cortex/ventures/linkedin-as-a-service/docker-compose.prod.yml), or pass them from a `.env.production` file at the root.

### 3. Log Management
- **Rule**: Always launch Docker with the `-d` (detached) flag.
- **Why**: Running it in the foreground prints all logs to your terminal and paralyzes your bash session. Because we configured JSON Rotators, the logs are perfectly safe in the background. Check them cleanly whenever you want using:
  ```bash
  docker compose -f docker-compose.prod.yml logs --tail=50
  ```

### 4. Background Worker Monitoring
- **Rule**: Routinely check the `ingestion_worker` logs.
- **Why**: The ingestion worker runs 24/7 pulling in LinkedIn data for the Content Calendar and Creator Radar. If social APIs change, rate limits are hit, or a proxy fails, this container will be the absolute first to throw warnings.
  ```bash
  docker compose -f docker-compose.prod.yml logs -f ingestion_worker
  ```
