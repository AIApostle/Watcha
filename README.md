# TheWatcher 👁️

**AI-powered market intelligence agent** that monitors financial markets, economic calendar releases, financial news, and presidential statements (Truth Social & X) — then delivers AI-analyzed alerts straight to your Telegram.

## Architecture

```
Frontend (React + TS + Tailwind) ←→ Backend (FastAPI + Python) ←→ Supabase (PostgreSQL)
                                          ↕
                                    Agent Worker
                                    ├── Finnhub (prices + news)
                                    ├── ForexFactory (economic calendar & events)
                                    ├── Truth Social (@realDonaldTrump scraper)
                                    ├── X / Twitter (@realDonaldTrump scraper)
                                    ├── Marketaux (financial news API)
                                    ├── Financial RSS (Reuters, CNBC, Bloomberg, etc.)
                                    ├── OpenRouter (AI analysis engine)
                                    └── Telegram Bot (alert dispatcher)
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- API Keys (see `.env.example`)

### 1. Setup Environment

```bash
cp .env.example backend/.env
# Edit backend/.env with your API keys
```

### 2. Setup Database

1. Create a free project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** and execute the migration script in `backend/scripts/init_db.py`
3. Copy your project URL, anon key, and service role key into `backend/.env`

### 3. Start Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### 4. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. Services & Free Tiers

| Service | Purpose | URL | Free Tier |
|---------|---------|-----|-----------|
| Supabase | Database & Auth | https://supabase.com | 500MB DB, 50K auth users |
| ForexFactory | Economic Calendar | https://forexfactory.com | 100% Free (CDN JSON/CSV + Fallbacks) |
| Truth Social | Trump Statements | https://truthsocial.com | 100% Free (Public Mastodon API) |
| X (Twitter) | Trump Tweets | https://x.com | 100% Free (Syndication Timeline) |
| Finnhub | Live Market Prices | https://finnhub.io | 60 calls/min |
| Marketaux | News API | https://marketaux.com | 100 req/day |
| OpenRouter | AI Analysis | https://openrouter.ai | Free / Pay-per-token models |
| Telegram Bot | Push Notifications | https://t.me/botfather | Free |

## Features

- 📊 **Live market prices** — Gold (XAU/USD), Forex pairs, Crypto via Finnhub
- 📅 **ForexFactory Calendar** — High & medium-impact macroeconomic event tracking (NFP, CPI, interest rates, GDP) with automatic rate-limit caching
- 🗣️ **Truth Social Trump Scraper** — Real-time presidential statements, tariff threats, and currency remarks
- 🐦 **X (Twitter) Trump Scraper** — Real-time presidential tweets via syndication timeline
- 📰 **News aggregation** — Multi-source financial news from APIs and major RSS feeds
- 🤖 **AI analysis engine** — OpenRouter-powered correlation, directional bias, and impact scoring (1-10)
- 📱 **Telegram alerts** — Instant push alerts with actionable summaries and market context
- 🎛️ **Modern Dashboard** — Premium dark-theme UI with live price charts, news feed filters, and worker status controls
- ⚙️ **Per-user personalization** — Configurable watchlists, polling intervals, and alert sensitivity thresholds

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Tailwind CSS, Vite, Lucide Icons |
| Backend | Python 3.11, FastAPI, Uvicorn, APScheduler |
| Collectors | Httpx, BeautifulSoup4, Lxml, Feedparser |
| Database | Supabase (PostgreSQL + RLS + Triggers) |
| AI Engine | OpenRouter API |
| Notifications | python-telegram-bot |
| Package Mgmt | uv (Python), npm (Node) |
