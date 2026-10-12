# Watcha (TheWatcher) — Project Memory & Handover Index 🧠

This folder serves as the central memory dump and project state documentation for **Watcha**. Any agent or developer picking up this project can immediately resume from where we left off.

---

## 📑 Memory Documents Index

1. **[Project Overview](file:///home/ai-apostle/Projects/TheWatcher/memory/project_overview.md)**
   - What the project is about.
   - Core value proposition and problems it solves.
   - High-level architecture diagram.
   - Technology stack breakdown.

2. **[How It Works (System Architecture & Pipeline)](file:///home/ai-apostle/Projects/TheWatcher/memory/how_it_works.md)**
   - End-to-end flow: Ingestion -> Normalization -> AI Analysis -> Persistence -> Telegram Dispatch.
   - Autonomous agent lifecycle (`APScheduler` & `worker.py`).
   - Dynamic polling interval synchronization mechanism.
   - Data collector resilience and multi-tier fallbacks.
   - Frontend and backend communication.

3. **[Work Done & Changelog History](file:///home/ai-apostle/Projects/TheWatcher/memory/work_done_history.md)**
   - Comprehensive log of all bugs diagnosed, fixes made, and features implemented during the latest session.
   - Cloud deployment setup (Render & Vercel).
   - Password show/hide toggle.
   - Truth Social 403 handling & ForexFactory rate limit protection.
   - Dynamic scheduling bug diagnosis and auto-sync implementation.

4. **[Deployment & Environment Reference](file:///home/ai-apostle/Projects/TheWatcher/memory/deployment_and_env.md)**
   - Live production URLs (Vercel & Render).
   - Required environment variables (`backend/.env` & `frontend/.env`).
   - Commands to run both backend and frontend locally.
   - `render.yaml` configuration.

5. **[Roadmap & Next Steps](file:///home/ai-apostle/Projects/TheWatcher/memory/roadmap_and_next_steps.md)**
   - Immediate next steps upon resuming (git push, checking Render env vars).
   - Notes on ForexFactory 429 rate limits (kept intact as requested).
   - Ideas for future feature expansions.
