from telegram.ext import (
    Application,
    CommandHandler,
)

from config import BOT_TOKEN
from handlers.start import start
from handlers.scan import scan


def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN bai cika ba.")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))

    print("✅ SALIM SAUKI DATA AI Bot Started")

    app.run_polling()


if __name__ == "__main__":
    main()
