# Work Done & Changelog History

This document records the exact milestones, problems solved, and changes implemented during this pairing session.

---

### 1. Render Cloud Deployment Configuration
- **Problem**: Deploying the backend to Render failed due to missing Python environment / uvicorn not found, Python version incompatibility, and missing port bindings.
- **Solution**:
  - Created `render.yaml` blueprint declaring the `watcha-backend` service.
  - Added `backend/requirements.txt` generated from dependencies for standard pip-based cloud deployments.
  - Specified Python `3.12.0` in `render.yaml` and set build command to `pip install -r requirements.txt`.
  - Set start command to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
  - Removed `.python-version` conflict files that blocked Render's native runtime resolution.

### 2. Frontend & Backend Production Linkage
- **Problem**: When accessing the deployed Vercel frontend (`https://watcha-plum.vercel.app`), API requests were either failing or routing to `localhost:8000`.
- **Solution**:
  - Created `frontend/src/lib/apiConfig.ts` to dynamically resolve API URLs using `import.meta.env.VITE_API_BASE_URL` with fallback to `https://watcha-backend.onrender.com` in production and `http://localhost:8000` in dev.
  - Updated `axios` instances and WebSocket endpoints to use this centralized config.
  - Ensured backend CORS in `main.py` explicitly allows both Vercel production domains and localhost origins.

### 3. Password Visibility Toggle (Show / Hide Eye)
- **Problem**: Users were unable to verify typed passwords on login and registration pages.
- **Solution**:
  - Added interactive toggle buttons with `Eye` and `EyeOff` icons from `lucide-react` on both `LoginPage.tsx` and `RegisterPage.tsx`.
  - Maintained sleek dark-mode input styling and focus ring aesthetics.

### 4. Truth Social & Scraper Resilience
- **Problem**: Truth Social and Cloudflare returned HTTP 403 blocks that generated noisy terminal tracebacks.
- **Solution**:
  - In `truthsocial_scraper.py`, caught 403 status responses gracefully and handled them without crashing or spamming stdout.
  - Preserved continuous pipeline execution across all other collectors even when one feed encounters Cloudflare checks.

### 5. ForexFactory Rate Limit Resilience
- **Problem**: ForexFactory CDN returned 429 (rate limit).
- **Solution**:
  - Built a multi-tier fallback mechanism: CDN JSON -> CSV export -> HTML scrape -> ForexLive RSS -> FXStreet calendar.
  - Added a 1-hour in-memory cache to prevent frequent external hitting of ForexFactory servers.
  - Confirmed to the user that 429 on ForexFactory does NOT break the agent because secondary feeds and cache immediately step in.

### 6. Settings Page Cleanup
- **Problem**: An unwanted "Configure API Server" section was visible in the Settings UI. The user indicated that backend connection endpoints must remain transparent and not configured by end-users.
- **Solution**:
  - Removed the API server configuration card and state management from `SettingsPage.tsx`.
  - Cleaned up the Settings UI to focus strictly on Watchlists, Alert Sensitivity, Polling Interval, and Notification channels.

### 7. Dynamic Polling Interval & In-Memory Scheduler Synchronization
- **Problem**: The user changed their polling interval from 5 minutes to 60 minutes in Settings, but Telegram alerts were still firing every 5 minutes.
- **Root Cause**: `APScheduler` was initialized once at backend boot with `minutes=5`. Changing the database field in Supabase did not notify the running scheduler in memory.
- **Solution**:
  - Added `update_user_interval(user_id, new_interval)` in `backend/app/agent/worker.py` using `self._scheduler.reschedule_job(..., trigger="interval", minutes=new_interval)`.
  - Linked `PUT /api/settings` in `backend/app/settings/router.py` to trigger `agent_worker.update_user_interval` immediately upon saving.
  - Added self-healing in `_run_scan_cycle`: if the in-memory job trigger minutes don't match the database `polling_interval`, the worker automatically reschedules the job to the database value.
  - Verified local Uvicorn `--reload` picked up changes and aligned to the user's 60-minute interval.
