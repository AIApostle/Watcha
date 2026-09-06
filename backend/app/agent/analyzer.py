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

SYSTEM_PROMPT = """You are TheWatcher, an elite AI market intelligence analyst. Your job is to analyze 
financial market data, macroeconomic calendar releases (ForexFactory), breaking financial news, 
and political statements (especially Donald Trump's posts on Truth Social and X) to assess their 
impact on specific watched assets.

You MUST respond with valid JSON matching this exact schema:
{
  "alerts": [
    {
      "impact_score": <1-10 integer>,
      "sentiment": "<bullish|bearish|neutral>",
      "severity": "<critical|warning|info>",
      "affected_assets": ["<SYMBOL/PAIR>"],
      "title": "<short headline — max 80 chars>",
      "summary": "<2-3 sentence analysis explaining WHY this matters for the asset>",
      "alert_type": "<price_move|news|social|calendar|composite>"
    }
  ],
  "market_mood": "<bullish|bearish|neutral|mixed>",
  "mood_summary": "<1-2 sentence overall market assessment>"
}

Key Analysis Rules:
1. ForexFactory Economic Releases: Pay special attention to High/Medium impact events (NFP, CPI, interest rates, GDP, central bank decisions). Explain the directional impact on the affected currency or gold.
2. Political Statements & Tariffs: Analyze Donald Trump's direct statements on Truth Social / X regarding tariffs, trade imbalances, currency wars (e.g. Dollar/CAD, USD/EUR, China), sanctions, or the Federal Reserve. Tariffs typically strengthen the USD short-term and drive safe-haven demand for Gold (XAU/USD).
3. Severity and Impact Scoring:
   - 1-3: Low impact — minor commentary, routine announcements
   - 4-6: Medium impact — notable calendar releases, policy hints, trade rhetoric
   - 7-8: High impact — major surprise in NFP/CPI, tariff threats/enactments, unexpected rate moves
   - 9-10: Critical — emergency rate decisions, severe trade sanctions, black swan events

Only generate alerts for items that are genuinely relevant to the user's watched assets.
If nothing significant is found, return {"alerts": [], "market_mood": "neutral", "mood_summary": "No significant market-moving events detected."}.
"""


async def analyze_market_data(
    prices: list[PriceData],
    news_items: list[CollectedItem],
    social_items: list[CollectedItem],
    user_assets: list[str],
    sensitivity: str = "medium",
    calendar_items: list[CollectedItem] | None = None,
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
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://thewatcher.app",
                    "X-Title": "TheWatcher Market Agent",
                },
                json={
                    "model": settings.openrouter_model,
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
                f"AI Analysis: {len(result.get('alerts', []))} alerts, "
                f"mood={result.get('market_mood', 'unknown')}"
            )
            return result

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
) -> str:
    """Construct the analysis prompt from collected data."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    parts = [
        f"## Analysis Request — {now}",
        f"**User's Watched Assets:** {', '.join(user_assets)}",
        f"**Alert Sensitivity:** {sensitivity} (generate {'all' if sensitivity == 'high' else 'significant' if sensitivity == 'medium' else 'only critical'} alerts)",
        "",
    ]

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
        parts.append(f"## Financial News ({len(news_items)} items)")
        for i, item in enumerate(news_items[:12], 1):  # Cap at 12
            pub = item.published_at.strftime("%H:%M") if item.published_at else "?"
            summary_str = f" — {item.summary[:140]}" if item.summary else ""
            parts.append(f"{i}. [{item.source}] {item.title}{summary_str} ({pub})")
        parts.append("")

    # Social / political items (Truth Social + X + Political feeds)
    if social_items:
        parts.append(f"## Political Statements & Social Posts ({len(social_items)} items)")
        for i, item in enumerate(social_items[:12], 1):  # Cap at 12
            keywords = item.raw_data.get("matched_keywords", [])
            kw_str = f" [keywords: {', '.join(keywords)}]" if keywords else ""
            parts.append(f"{i}. [{item.source}] {item.title}{kw_str}")
            if item.summary:
                parts.append(f"   > {item.summary[:200]}")
        parts.append("")

    if not news_items and not social_items and not calendar_items:
        parts.append("No news, calendar, or social items collected in this cycle.")

    return "\n".join(parts)

