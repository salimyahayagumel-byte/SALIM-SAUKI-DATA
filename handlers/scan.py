from telegram import Update
from telegram.ext import ContextTypes

from services.dexscreener import DexScreener


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) == 0:
        await update.message.reply_text(
            "Amfani:\n/scan SOL\nko\n/scan BONK"
        )
        return

    query = " ".join(context.args)

    dex = DexScreener()

    try:
        pairs = await dex.search(query)

        if not pairs:
            await update.message.reply_text(
                "Ba a sami token ba."
            )
            return

        pair = pairs[0]

        text = (
            f"🪙 {pair['baseToken']['name']}\n"
            f"Symbol: {pair['baseToken']['symbol']}\n"
            f"Price: {pair.get('priceUsd','N/A')}$\n"
            f"DEX: {pair.get('dexId','Unknown')}"
        )

        await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(
            f"Kuskure:\n{e}"
        )
