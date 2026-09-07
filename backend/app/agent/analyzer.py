"""
AI Analysis Engine — OpenRouter integration.

Receives aggregated market data (prices + news + social posts),
analyzes correlation and impact, and produces structured alert summaries.
"""

import json
import logging
from datetime import datetime, timezone

import httpx

from app.collectors.base import CollectedItem, PriceData
from app.config import get_settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """You are Watcha, an elite AI market intelligence analyst. Your job is to analyze 
financial market data, macroeconomic calendar releases (ForexFactory), breaking financial news, 
and political/institutional statements to assess their impact on specific watched assets, key leaders, 
and organizations.

You MUST respond with valid JSON matching this exact schema:
{
  "alerts": [
    {
      "impact_score": <1-10 integer>,
      "sentiment": "<bullish|bearish|neutral>",
      "severity": "<critical|warning|info>",
      "affected_assets": ["<SYMBOL/PAIR or ENTITY>"],
      "title": "<short headline — max 80 chars>",
      "summary": "<2-3 sentence analysis explaining WHY this matters for the asset/entity>",
      "alert_type": "<price_move|news|social|calendar|composite>"
    }
  ],
  "market_mood": "<bullish|bearish|neutral|mixed>",
  "mood_summary": "<1-2 sentence overall market assessment>"
}

Key Analysis Rules:
1. ForexFactory Economic Releases: Pay special attention to High/Medium impact events (NFP, CPI, interest rates, GDP, central bank decisions). Explain the directional impact on the affected currency or gold.
2. Watched People & Leaders (e.g. Donald Trump, Jerome Powell, Christine Lagarde, Elon Musk): Carefully inspect speeches, press conferences, Truth Social / X posts, or executive commentary. Directly correlate their words or actions to their market impact (e.g. Powell's interest rate stance, Trump's tariffs/trade rhetoric).
3. Watched Organizations & Institutions (e.g. Federal Reserve, OPEC, ECB, SEC, US Treasury): Analyze official policy decisions, quota announcements, rate guidance, or regulatory actions. Explain how they affect commodities (Gold, Oil) and currency pairs.
4. Freshness & Breaking News: Focus STRICTLY on breaking news and developments from the past 24 hours. Ignore stale historical context or already-digested news from previous cycles.
5. Severity and Impact Scoring:
   - 1-3: Low impact — minor commentary, routine announcements
   - 4-6: Medium impact — notable calendar releases, policy hints, trade rhetoric
   - 7-8: High impact — major surprise in NFP/CPI, tariff threats/enactments, unexpected rate moves
   - 9-10: Critical — emergency rate decisions, severe trade sanctions, black swan events

Only generate alerts for items that are genuinely relevant to the user's watched assets, leaders, or organizations.
If nothing significant is found, return {"alerts": [], "market_mood": "neutral", "mood_summary": "No significant market-moving events detected."}.
"""


async def analyze_market_data(
    prices: list[PriceData],
    news_items: list[CollectedItem],
    social_items: list[CollectedItem],
    user_assets: list[str],
    sensitivity: str = "medium",
    calendar_items: list[CollectedItem] | None = None,
    watched_people: list[str] | None = None,
    watched_orgs: list[str] | None = None,
) -> dict:
    """
    Send aggregated data to OpenRouter for AI analysis.

    Args:
        prices: Current price data for user's watched assets
        news_items: News articles from RSS + API collectors
        social_items: Political/social posts from Trump (Truth Social, X) and political monitor
        user_assets: List of asset symbols the user watches
        sensitivity: Alert sensitivity level (high/medium/low)
        calendar_items: Economic calendar events from ForexFactory
        watched_people: Key people being monitored (e.g. Jerome Powell, Donald Trump)
        watched_orgs: Organizations being monitored (e.g. Federal Reserve, OPEC)

    Returns:
        Parsed JSON response with alerts and market mood.
    """
    settings = get_settings()

    # Build the user prompt with all collected data
    user_prompt = _build_prompt(
        prices=prices,
        news_items=news_items,
        social_items=social_items,
        calendar_items=calendar_items or [],
        user_assets=user_assets,
        sensitivity=sensitivity,
        watched_people=watched_people or [],
        watched_orgs=watched_orgs or [],
    )

    models_to_try = [settings.openrouter_model]
    if "google/gemini-2.5-flash" not in models_to_try:
        models_to_try.append("google/gemini-2.5-flash")
    if "google/gemini-2.5-flash-lite" not in models_to_try:
        models_to_try.append("google/gemini-2.5-flash-lite")

    last_error = None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for model_name in models_to_try:
                try:
                    response = await client.post(
                        OPENROUTER_URL,
                        headers={
                            "Authorization": f"Bearer {settings.openrouter_api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://watcha.app",
                            "X-Title": "Watcha Market Agent",
                        },
                        json={
                            "model": model_name,
                            "messages": [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": user_prompt},
                            ],
                            "temperature": 0.3,
                            "max_tokens": 2000,
                            "response_format": {"type": "json_object"},
                        },
                    )

                    response.raise_for_status()
                    data = response.json()

                    # Extract the assistant's message content
                    content = data["choices"][0]["message"]["content"]
                    result = json.loads(content)

                    logger.info(
                        f"AI Analysis using {model_name}: {len(result.get('alerts', []))} alerts, "
                        f"mood={result.get('market_mood', 'unknown')}"
                    )
                    return result
                except httpx.HTTPStatusError as err:
                    last_error = err
                    logger.warning(f"OpenRouter model {model_name} failed: {err.response.status_code} {err.response.text}")
                    continue

        if last_error:
            raise last_error

    except json.JSONDecodeError as e:
        logger.error(f"AI response was not valid JSON: {e}")
        return {"alerts": [], "market_mood": "unknown", "mood_summary": "Analysis failed — invalid response."}
    except httpx.HTTPStatusError as e:
        logger.error(f"OpenRouter API error: {e.response.status_code} — {e.response.text}")
        return {"alerts": [], "market_mood": "unknown", "mood_summary": f"API error: {e.response.status_code}"}
    except Exception as e:
        logger.error(f"AI analysis error: {e}")
        return {"alerts": [], "market_mood": "unknown", "mood_summary": f"Analysis error: {str(e)}"}


def _build_prompt(
    prices: list[PriceData],
    news_items: list[CollectedItem],
    social_items: list[CollectedItem],
    calendar_items: list[CollectedItem],
    user_assets: list[str],
    sensitivity: str,
    watched_people: list[str] | None = None,
    watched_orgs: list[str] | None = None,
) -> str:
    """Construct the analysis prompt from collected data."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    parts = [
        f"## Analysis Request — {now}",
        f"**Alert Sensitivity:** {sensitivity} (generate {'all' if sensitivity == 'high' else 'significant' if sensitivity == 'medium' else 'only critical'} alerts)",
    ]
    if user_assets:
        parts.append(f"**User's Watched Assets:** {', '.join(user_assets)}")
    if watched_people:
        parts.append(f"**Watched Key People / Leaders:** {', '.join(watched_people)}")
    if watched_orgs:
        parts.append(f"**Watched Organizations / Institutions:** {', '.join(watched_orgs)}")
    parts.append("")

    # Price data
    if prices:
        parts.append("## Current Prices")
        for p in prices:
            change_str = ""
            if p.change_percent is not None:
                arrow = "↑" if p.change_percent >= 0 else "↓"
                change_str = f" {arrow} {p.change_percent:+.2f}%"
            parts.append(f"- **{p.symbol}**: ${p.current_price:,.2f}{change_str}")
        parts.append("")

    # Economic Calendar (ForexFactory)
    if calendar_items:
        parts.append(f"## ForexFactory Economic Calendar ({len(calendar_items)} events)")
        for i, item in enumerate(calendar_items[:10], 1):
            parts.append(f"{i}. {item.title}")
            if item.summary:
                parts.append(f"   > {item.summary[:180]}")
        parts.append("")

    # News items (batched to save tokens)
    if news_items:
        parts.append(f"## Latest Financial News ({len(news_items)} items)")
        for i, item in enumerate(news_items[:12], 1):  # Cap at 12
            pub = item.published_at.strftime("%m/%d %H:%M UTC") if item.published_at else "Recent"
            summary_str = f" — {item.summary[:140]}" if item.summary else ""
            parts.append(f"{i}. [{item.source}] {item.title}{summary_str} ({pub})")
        parts.append("")

    # Social / political items (Truth Social + X + Political feeds)
    if social_items:
        parts.append(f"## Recent Political Statements & Social Posts ({len(social_items)} items)")
        for i, item in enumerate(social_items[:12], 1):  # Cap at 12
            keywords = item.raw_data.get("matched_keywords", [])
            kw_str = f" [keywords: {', '.join(keywords)}]" if keywords else ""
            pub = item.published_at.strftime("%m/%d %H:%M UTC") if item.published_at else "Recent"
            parts.append(f"{i}. [{item.source}] {item.title}{kw_str} ({pub})")
            if item.summary:
                parts.append(f"   > {item.summary[:200]}")
        parts.append("")

    if not news_items and not social_items and not calendar_items:
        parts.append("No news, calendar, or social items collected in this cycle.")

    return "\n".join(parts)

