# Roadmap & Next Steps for Next Session

When resuming work on **Watcha**, check these items first:

---

## 1. Pending / Immediate Tasks

1. **Git Remote Push (`origin/main`)**:
   - The latest commit (`20308ff`: *"enable dynamic rescheduling and auto-sync of polling interval"*) is committed locally on `main`.
   - Run `git push origin main` using your credentials or SSH keys to trigger the latest automatic deployment on Render and Vercel.

2. **ForexFactory Feed Monitoring**:
   - The user noted a 429 response earlier on ForexFactory's CDN endpoint and instructed: *"don't fix it yet, is it a big problem"*.
   - We verified it is safe due to multi-tier fallbacks (CSV, HTML, ForexLive, FXStreet) + 1-hour in-memory cache.
   - If the user wishes to revisit in the future, consider rotating User-Agents or testing an alternative public mirror if rate limits persist.

3. **Production Render Environment Variables**:
   - Verify on the Render Dashboard (`https://dashboard.render.com`) that all environment variables listed in `backend/.env` (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENROUTER_API_KEY`, `TELEGRAM_BOT_TOKEN`, `FINNHUB_API_KEY`, etc.) are configured in the Render Web Service settings so the cloud backend operates identically to local.

---

## 2. Potential Feature Extensions

- **Custom User Watchlists**: Allow users to define custom stock tickers, commodities, and crypto tokens beyond the core defaults.
- **Telegram Bot Two-Way Commands**: Allow users to query the bot directly on Telegram (e.g., `/status`, `/gold`, `/latest`) to get on-demand market snapshots.
- **Historic Analytics & Performance Tracking**: Add charts to evaluate the accuracy of previous AI impact predictions against actual post-event market volatility.
- **Multiple AI Providers / Fallbacks**: Support fallback model routing on OpenRouter (e.g. if one model endpoint experiences latency or downtime).
