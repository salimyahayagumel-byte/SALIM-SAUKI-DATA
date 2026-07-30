import asyncio

from telegram.ext import (
    Application,
    CommandHandler,
)

from config import BOT_TOKEN
from handlers.start import start
from handlers.scan import scan


async def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))

    print("✅ SALIM SAUKI DATA AI Bot Started")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(run_bot())
