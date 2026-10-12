# How Watcha Works — End-to-End System Flow

## 1. The Autonomous Agent Lifecycle (`worker.py`)

The heart of Watcha is the **Agent Worker** (`backend/app/agent/worker.py`), managed by Python's `APScheduler` (`AsyncIOScheduler`).

### Step-by-Step Scan Cycle (`_run_scan_cycle`):
1. **User Profile Retrieval**:
   - The worker fetches user profiles from Supabase where the agent is enabled (`agent_enabled = true`).
   - Dynamically verifies the user's `polling_interval` (5, 15, 30, or 60 minutes) and auto-aligns the active scheduler job if there was a discrepancy.
2. **Data Collection (Async Parallel)**:
   - Queries all active collectors concurrently:
     - **Finnhub Client**: Live asset quotes (XAU/USD, EUR/USD, GBP/USD, USD/JPY, BTC, SPY) + company news.
     - **ForexFactory Client**: Weekly economic calendar. Checks CDN JSON with fallback to CSV export, scraping, and cached fallback feeds.
     - **Truth Social Monitor**: Scrapes `@realDonaldTrump` posts using public web endpoints with custom user agents and Cloudflare/HTTP 403 handling.
     - **X (Twitter) Monitor**: Scrapes Trump tweets via syndicated timeline APIs.
     - **Marketaux Client**: Financial market news API.
     - **RSS Collector**: Major financial RSS feeds (Reuters, Bloomberg, CNBC, ForexLive, FXStreet).
3. **Filtering & De-duplication**:
   - Raw items are normalized into `RawFeedItem` objects.
   - Items previously analyzed or older than a configurable threshold are discarded using URLs/hashes.
4. **AI Market Intelligence Analysis (`analyzer.py`)**:
   - The filtered batch of news/events is sent to OpenRouter API.
   - The LLM assesses:
     - **Impact Score**: 1 to 10 scale (where 7+ is high volatility).
     - **Affected Assets**: e.g., `XAU/USD`, `DXY`, `EUR/USD`.
     - **Directional Bias**: `BULLISH`, `BEARISH`, `NEUTRAL`, or `VOLATILE`.
     - **Key Insight**: 1-2 sentence high-conviction breakdown.
5. **Persistence**:
   - Run results are saved to the `agent_runs` table in Supabase.
   - Identified high-impact items are saved to the `alerts` table.
6. **Telegram Dispatch (`dispatcher.py`)**:
   - If an alert meets or exceeds the user's configured sensitivity threshold (`min_impact_score`), an instant Markdown-formatted notification is sent via the Telegram Bot to their `telegram_chat_id`.

---

## 2. Dynamic Polling & Interval Scheduling

- Each user has their own scheduler job ID (`scan_{user_id}`).
- When a user updates their polling interval in Settings (5, 15, 30, or 60 mins), `PUT /api/settings` calls `agent_worker.update_user_interval(user.id, new_interval)`.
- The scheduler dynamically reschedules the job in RAM immediately without restarting the backend process.
- Additionally, on every scan cycle, self-healing code checks if the active job's interval matches `profile["polling_interval"]` and auto-reschedules if needed.

---

## 3. Data Ingestion Resilience & Fallbacks

| Data Source | Primary Method | Fallback Strategy |
|---|---|---|
| **ForexFactory** | Official JSON CDN feed | 1. CSV export (`/forex_calendar.csv`)<br>2. HTML table scraper<br>3. ForexLive RSS feed<br>4. FXStreet calendar feed<br>5. 1-hour in-memory cache to prevent 429 rate limits |
| **Finnhub** | REST quote endpoints (`/quote?symbol=...`) | Live fallback quotes when symbols return 403/restricted |
| **Truth Social** | Public Mastodon API | Web scraper with fallback and silent non-blocking error handling for Cloudflare challenges |
| **X / Twitter** | Syndication timeline endpoints | HTML timeline parser |
| **RSS Feeds** | Direct feedparser on financial feeds | Fallback feed rotation |

---

## 4. Frontend & Backend Interaction

- **API Base URL Resolution**:
  - In development: Frontend proxies requests to `http://localhost:8000`.
  - In production: Defaults to `VITE_API_BASE_URL` (configured as `https://watcha-backend.onrender.com` on Vercel).
- **Authentication**:
  - Handled via Supabase Auth (Email + Password).
  - JWT tokens are passed in `Authorization: Bearer <token>` to FastAPI.
  - FastAPI validates the token against Supabase Auth.
- **Real-Time UI Updates**:
  - Live agent status (`/api/agent/status`)
  - Execution history & log metrics (`/api/agent/runs`)
  - Alerts feed with impact badges and asset tags (`/api/alerts`)
  - Market news feed (`/api/news`)
  - User preferences & notification settings (`/api/settings`)
