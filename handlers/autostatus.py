from telegram import Update
from telegram.ext import ContextTypes


def _fmt_rejections(rejections):
    if not rejections:
        return "none"
    return " | ".join(
        f"{key}={value}"
        for key, value in sorted(rejections.items())
    )


async def autostatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show live Auto Signal Engine diagnostics without exposing secrets."""
    if update.message is None:
        return

    engine = context.application.bot_data.get("auto_signal_engine")

    if engine is None:
        await update.message.reply_text(
            "🤖 AUTO SIGNAL STATUS\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔴 Engine: NOT RUNNING / NOT INITIALIZED"
        )
        return

    summary = getattr(engine, "last_scan_summary", {}) or {}
    last_scan = summary.get("scan", getattr(engine, "scan_count", 0))

    text = (
        "🤖 AUTO SIGNAL STATUS — V10\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 Engine: {'RUNNING' if engine.running else 'STOPPED'}\n"
        f"🔎 Scans: {engine.scan_count}\n"
        f"🕒 Last scan: #{last_scan}\n"
        f"🟣 Solana candidates: {summary.get('solana_candidates', 0)}\n"
        f"🔵 Base candidates: {summary.get('base_candidates', 0)}\n"
        f"📊 Total candidates: {summary.get('total_candidates', 0)}\n"
        f"🏆 Ranked: {summary.get('ranked_candidates', 0)}\n"
        f"🎯 Selected: {summary.get('selected_candidates', 0)}\n"
        f"🚀 Sent this scan: {summary.get('signals_sent_this_scan', 0)}\n"
        f"📨 Sent total: {engine.signals_sent}\n"
        f"⏭️ Duplicates: {engine.duplicates_skipped}\n"
        f"⏳ Cooldown: {engine.cooldown_skipped}\n"
        f"❌ Telegram errors: {engine.telegram_errors}\n"
        f"🚫 Rejections: {_fmt_rejections(summary.get('rejections', {}))}"
    )

    await update.message.reply_text(text)
