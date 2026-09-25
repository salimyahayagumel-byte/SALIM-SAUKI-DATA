from telegram import Update
from telegram.ext import ContextTypes


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    await update.message.reply_text(
        "🤖 SALIM SAUKI DATA\n"
        "🧠 Multi-chain DEX Analysis Bot\n\n"
        "📌 Commands:\n"
        "/start — Fara bot\n"
        "/help — Nuna dukkan commands\n"
        "/scan solana — Scan Solana gems\n"
        "/scan base — Scan Base gems\n"
        "/scan <token> — Search/analyze token\n"
        "/analyze <token/address> — Cikakken analysis\n"
        "/pnl — Nuna PNL na duk tracked tokens\n"
        "/pnl <contract> — Nuna PNL na token daya\n"
        "/status — Duba bot status\n"
        "/health — Duba API/scanner health\n\n"
        "⚠️ Analysis ba financial guarantee ba ne. DYOR."
    )


# V10: /autostatus is registered in bot.py for live auto-signal diagnostics.
