from telegram import Update
from telegram.ext import ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start command
    """
    text = (
        "🤖 SALIM SAUKI DATA AI\n\n"
        "Assalamu Alaikum.\n"
        "Bot yana aiki lafiya.\n\n"
        "Version: 1.0.0"
    )

    await update.message.reply_text(text)
