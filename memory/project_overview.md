# Project Overview — Watcha (TheWatcher) 👁️

## 1. What is Watcha?
**Watcha** (formerly TheWatcher) is an **AI-powered financial market intelligence and real-time alert system**. It monitors macroeconomic data releases, financial news, live market prices, and presidential/geopolitical statements (Truth Social & X / Twitter) to detect high-impact market-moving events. 

When significant volatility triggers or breaking developments occur, the engine analyzes them using AI (via OpenRouter), determines asset impact (Gold, EUR/USD, Crypto, etc.), calculates directional bias, and immediately dispatches actionable alert digests to users via **Telegram** and the **Web Dashboard**.

---

## 2. Core Value Proposition
- **Automated Macro & Geopolitical Vigilance**: Eliminates manual refreshes of economic calendars and social media feeds.
- **Multimodal Intelligence Synthesis**: Correlates economic events (NFP, CPI, interest rates) and political rhetoric (tariffs, sanctions, currency comments) against real-time market prices.
- **Actionable AI Scoring**: Rates every event from 1–10 on market impact, identifies affected assets, and assigns directional bias (`BULLISH`, `BEARISH`, `NEUTRAL`, `VOLATILE`).
- **Instant Telegram Delivery**: Direct push notifications with clean formatting, key takeaways, and asset implications.

---

## 3. High-Level Architecture

```
                                  ┌───────────────────────────────┐
                                  │      External Data Sources     │
                                  │  - Finnhub (Live Prices/News)  │
                                  │  - ForexFactory (Econ Calendar)│
                                  │  - Truth Social (@realDonaldTrump)
                                  │  - X / Twitter (@realDonaldTrump)
                                  │  - Marketaux (Financial News)  │
                                  │  - Major Financial RSS Feeds  │
                                  └──────────────┬────────────────┘
                                                 │
                                                 ▼
┌───────────────────────────────┐        ┌───────────────────────────────┐
│     Watcha Web Frontend       │        │     Watcha FastAPI Backend    │
│  - React 18 + TypeScript      │ ◄────► │  - FastAPI REST Endpoints     │
│  - Tailwind CSS + Lucide      │ (HTTP) │  - APScheduler Background Jobs│
│  - Mobile Responsive Drawer   │        └──────────────┬────────────────┘
│  - Deployed on Vercel         │                       │
└───────────────────────────────┘                       │
                ▲                                       ▼
                │                        ┌───────────────────────────────┐
                │                        │        OpenRouter AI          │
                │                        │  - Impact Scoring (1-10)      │
                │                        │  - Directional Bias           │
                │                        │  - Summary & Affected Assets  │
                │                        └──────────────┬────────────────┘
                │                                       │
                ▼                                       ▼
┌───────────────────────────────┐        ┌───────────────────────────────┐
│      Supabase PostgreSQL      │        │       Telegram Bot API        │
│  - Auth & User Profiles       │ ◄──────┤  - Real-time Alert Dispatch   │
│  - Alerts & News Cache        │        │  - Formatted Markdown Alerts  │
│  - Agent Run Execution Logs   │        └───────────────────────────────┘
└───────────────────────────────┘
```

---

## 4. Technology Stack

| Layer | Technologies Used |
|---|---|
| **Frontend** | React 18, TypeScript, Tailwind CSS, Vite, Lucide React, Axios |
| **Backend** | Python 3.12 / 3.11, FastAPI, Uvicorn, APScheduler, Pydantic |
| **Data Scraping & Ingestion** | HTTPX (Async), BeautifulSoup4, Lxml, Feedparser |
| **Database & Auth** | Supabase (PostgreSQL, Row Level Security, Auth triggers) |
| **AI Analysis** | OpenRouter API (deepseek / gemini / llama models) |
| **Alerts & Messaging** | `python-telegram-bot` (Telegram Bot API) |
| **Hosting & Deployments** | **Frontend**: Vercel (`watcha-plum.vercel.app`)<br>**Backend**: Render (`watcha-backend.onrender.com`) |
| **Package Management** | `uv` (Python fast package manager) & `npm` (Node.js) |
