from telegram import Update
from telegram.ext import ContextTypes

from config import (
    AUTO_SIGNAL_CHAT_ID,
    AUTO_SIGNAL_ENABLED,
    AUTO_SIGNAL_INTERVAL,
)
from services.auto_signal import AutoSignalEngine


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    engine = context.application.bot_data.get("auto_signal_engine")
    if engine is None:
        # bot_data is a dict in python-telegram-bot; this fallback keeps
        # the command safe if an older application object is used.
        engine = None

    if engine is None:
        text = (
            "🤖 SALIM SAUKI DATA STATUS\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ Auto Signal: {'ON' if AUTO_SIGNAL_ENABLED else 'OFF'}\n"
            f"📡 Chat ID: {'SET' if AUTO_SIGNAL_CHAT_ID else 'NOT SET'}\n"
            f"⏱️ Interval: {AUTO_SIGNAL_INTERVAL}s\n"
            "🟢 Telegram: ONLINE\n"
            "ℹ️ Engine statistics: not available yet."
        )
    else:
        text = (
            "🤖 SALIM SAUKI DATA STATUS\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ Auto Signal: {'ON' if engine.running else 'OFF'}\n"
            f"🔎 Scans: {engine.scan_count}\n"
            f"🚀 Signals sent: {engine.signals_sent}\n"
            f"⏭️ Duplicates: {engine.duplicates_skipped}\n"
            f"⏳ Cooldown: {engine.cooldown_skipped}\n"
            f"🚫 Filtered: {engine.filtered_out}\n"
            f"❌ Telegram errors: {engine.telegram_errors}\n"
            f"💾 Persistent history: {engine.history_store.count()}"
        )

    await update.message.reply_text(text)
