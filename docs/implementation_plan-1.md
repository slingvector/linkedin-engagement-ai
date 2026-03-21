# End-to-End Testing with Mock Data Plan

The goal is to perform a full system spin-up and verify that mock data is correctly generated, processed, and displayed correctly on the frontend.

## Proposed Changes / Steps

1. **Start System Dependencies**:
   - Run `docker-compose up -d` to launch PostgreSQL and Redis.
2. **Initialize Databases**:
   - Run the DB setup scripts in `apps/core_api/scripts/` to ensure all schemas are created (`init_master_db.py`, `init_talent_db.py`, `init_career_db.py`, `init_analytics_db.py`, `init_sales_db.py`).
3. **Start Backend Services**:
   - Start the **Core API**: This will automatically trigger the background worker tasks (`job_seeder`, `lead_seeder`, `candidate_seeder`, `signal_seeder`, etc.) which seed mock data.
   - Start the **AI Engine API**.
4. **Start Frontend App**:
   - Install dependencies and start the Next.js app in development mode (`npm run dev`) inside `apps/web`.
5. **UI Verification (E2E Test)**:
   - Use the browser subagent to open `http://localhost:3000`.
   - Verify that the seeded data (e.g., Candidates, Leads, Jobs) is rendering correctly in the various dashboards.

## Verification Plan

### Automated Tests
- Run `pytest` within `apps/core_api/` and `apps/ai_engine/` to confirm unit tests pass.

### Manual Verification
- We will use the automated browser subagent to capture a recording of the application at `http://localhost:3000` interacting with the mock data, or we can have the user manually verify if necessary.
