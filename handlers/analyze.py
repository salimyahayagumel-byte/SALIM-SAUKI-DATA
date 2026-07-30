from telegram import Update
from telegram.ext import ContextTypes

from services.dexscreener import DexScreener


async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) == 0:
        await update.message.reply_text(
            "Amfani:\n/analyze <token name>\n\nMisali:\n/analyze bonk"
        )
        return

    query = context.args[0]

    dex = DexScreener()

    try:
        pairs = await dex.search(query)

        if not pairs:
            await update.message.reply_text("❌ Ba a sami token ba.")
            return

        pair = pairs[0]

        text = (
            "🧠 SALIM SAUKI DATA AI\n\n"
            f"🪙 Name: {pair['baseToken']['name']}\n"
            f"🔖 Symbol: {pair['baseToken']['symbol']}\n"
            f"🌐 Chain: {pair['chainId']}\n"
            f"💰 Price: ${pair.get('priceUsd','N/A')}\n"
            f"💧 Liquidity: ${pair.get('liquidity',{}).get('usd','N/A')}\n"
            f"🏦 FDV: ${pair.get('fdv','N/A')}\n"
            f"📈 24H Volume: ${pair.get('volume',{}).get('h24','N/A')}\n"
            f"🏪 DEX: {pair.get('dexId','N/A')}"
        )

        await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(f"❌ Error:\n{e}")
