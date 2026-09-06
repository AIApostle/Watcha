"""
Telegram Alert Dispatcher.

Sends formatted alert messages to users via the Telegram Bot API.
Uses python-telegram-bot (async).
"""

import logging
from datetime import datetime, timezone

from telegram import Bot
from telegram.constants import ParseMode

from app.config import get_settings

logger = logging.getLogger(__name__)

# Lazy-initialized bot instance
_bot: Bot | None = None


def _get_bot() -> Bot:
    """Get or create the Telegram Bot instance."""
    global _bot
    if _bot is None:
        settings = get_settings()
        _bot = Bot(token=settings.telegram_bot_token)
    return _bot


def _format_alert_message(alert: dict) -> str:
    """
    Format an alert dict into a rich Telegram message.

    Expected alert keys:
        impact_score, sentiment, severity, affected_assets,
        title, summary, alert_type
    """
    # Severity icons
    severity_icons = {
        "critical": "🔴",
        "warning": "🟡",
        "info": "🟢",
    }
    severity = alert.get("severity", "info")
    icon = severity_icons.get(severity, "🔵")

    # Sentiment arrow
    sentiment = alert.get("sentiment", "neutral")
    sentiment_emoji = {
        "bullish": "📈",
        "bearish": "📉",
        "neutral": "➡️",
    }.get(sentiment, "❓")

    impact = alert.get("impact_score", "?")
    assets = ", ".join(alert.get("affected_assets", ["—"]))
    title = alert.get("title", "Market Alert")
    summary = alert.get("summary", "")
    alert_type = alert.get("alert_type", "composite")
    now = datetime.now(timezone.utc).strftime("%b %d, %Y · %H:%M UTC")

    # Type label
    type_labels = {
        "price_move": "💰 Price Movement",
        "news": "📰 News Alert",
        "social": "🗣️ Political/Social",
        "composite": "🔗 Composite Alert",
    }
    type_label = type_labels.get(alert_type, "📢 Alert")

    return (
        f"{icon} <b>{severity.upper()} ALERT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{type_label}\n\n"
        f"📊 <b>Assets:</b> {assets}\n\n"
        f"<b>{title}</b>\n\n"
        f"🤖 <b>AI Analysis:</b>\n"
        f"{summary}\n\n"
        f"Impact: <b>{impact}/10</b> {sentiment_emoji} {sentiment.capitalize()}\n\n"
        f"⏰ {now}"
    )


async def send_alert(chat_id: str, alert: dict) -> bool:
    """
    Send a formatted alert to a Telegram chat.

    Args:
        chat_id: Telegram chat ID
        alert: Alert dict with impact_score, sentiment, severity, etc.

    Returns:
        True if sent successfully, False otherwise.
    """
    bot = _get_bot()
    message = _format_alert_message(alert)

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
        )
        logger.info(f"Telegram alert sent to {chat_id}: {alert.get('title', '?')}")
        return True
    except Exception as e:
        logger.error(f"Telegram send error to {chat_id}: {e}")
        return False


async def send_test_message(chat_id: str) -> bool:
    """
    Send a test verification message to a Telegram chat.

    Args:
        chat_id: Telegram chat ID to verify

    Returns:
        True if the message was delivered.
    """
    bot = _get_bot()

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "✅ <b>TheWatcher Connected!</b>\n\n"
                "Your Telegram is now linked to TheWatcher.\n"
                "You'll receive market alerts here when the agent detects "
                "significant events affecting your watched assets.\n\n"
                "🤖 <i>Stay sharp. Stay informed.</i>"
            ),
            parse_mode=ParseMode.HTML,
        )
        logger.info(f"Test message sent to {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Test message error to {chat_id}: {e}")
        return False


async def send_digest(chat_id: str, mood: str, mood_summary: str, alert_count: int) -> bool:
    """
    Send a brief scan cycle summary (no critical alerts).

    Only sent if the user's sensitivity is set to 'high'.
    """
    bot = _get_bot()

    mood_emoji = {"bullish": "📈", "bearish": "📉", "neutral": "😐", "mixed": "🔄"}.get(
        mood, "❓"
    )

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"{mood_emoji} <b>Market Scan Complete</b>\n\n"
                f"<b>Mood:</b> {mood.capitalize()}\n"
                f"{mood_summary}\n\n"
                f"Alerts generated: {alert_count}\n"
                f"⏰ {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
            ),
            parse_mode=ParseMode.HTML,
        )
        return True
    except Exception as e:
        logger.error(f"Digest send error: {e}")
        return False
