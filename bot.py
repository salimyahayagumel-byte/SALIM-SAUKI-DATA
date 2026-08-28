import asyncio
import logging
import os

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from telegram.request import HTTPXRequest

from config import BOT_TOKEN

from handlers.start import start
from handlers.scan import scan
from handlers.analyze import analyze

from services.auto_signal import AutoSignalEngine


# =========================================
# LOGGING
# =========================================

logging.basicConfig(
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================
# AUTO SIGNAL SETTINGS
# =========================================

AUTO_SIGNAL_CHAT_ID = os.getenv(
    "AUTO_SIGNAL_CHAT_ID",
    ""
).strip()

AUTO_SIGNAL_INTERVAL = int(
    os.getenv(
        "AUTO_SIGNAL_INTERVAL",
        "60"
    )
)


# =========================================
# GLOBAL AUTO SIGNAL ENGINE
# =========================================

auto_signal_engine = None
auto_signal_task = None


# =========================================
# ERROR HANDLER
# =========================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "Telegram update error:",
        exc_info=context.error,
    )


# =========================================
# AUTO SIGNAL STARTER
# =========================================

async def start_auto_signals(
    application: Application,
):

    global auto_signal_engine

    if not AUTO_SIGNAL_CHAT_ID:

        print(
            "⚠️ AUTO_SIGNAL_CHAT_ID ba a saita ba."
        )

        print(
            "⏭️ Auto signals ba za su aika Telegram ba."
        )

        return

    print(
        "========================================"
    )

    print(
        "💎 SALIM SAUKI DATA — AUTO SIGNAL"
    )

    print(
        "========================================"
    )

    print(
        f"📡 Chat ID: {AUTO_SIGNAL_CHAT_ID}"
    )

    print(
        f"⏱️ Interval: {AUTO_SIGNAL_INTERVAL}s"
    )

    auto_signal_engine = AutoSignalEngine(
        bot=application.bot,
        chat_id=AUTO_SIGNAL_CHAT_ID,
        interval=AUTO_SIGNAL_INTERVAL,
    )

    await auto_signal_engine.start()


# =========================================
# MAIN BOT
# =========================================

async def run_bot():

    global auto_signal_task
    global auto_signal_engine

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN baya cikin .env"
        )

    # =====================================
    # TELEGRAM NETWORK SETTINGS
    # =====================================

    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=60.0,
        write_timeout=60.0,
        pool_timeout=30.0,
    )

    get_updates_request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=60.0,
        write_timeout=60.0,
        pool_timeout=30.0,
    )

    # =====================================
    # APPLICATION
    # =====================================

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .get_updates_request(
            get_updates_request
        )
        .build()
    )

    # =====================================
    # COMMANDS
    # =====================================

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CommandHandler(
            "scan",
            scan,
        )
    )

    app.add_handler(
        CommandHandler(
            "analyze",
            analyze,
        )
    )

    # =====================================
    # ERROR HANDLER
    # =====================================

    app.add_error_handler(
        error_handler
    )

    # =====================================
    # STARTUP
    # =====================================

    print(
        "========================================"
    )

    print(
        "🧠 SALIM SAUKI DATA"
    )

    print(
        "💎 DEX ANALYSIS BOT"
    )

    print(
        "========================================"
    )

    print(
        "🤖 Bot yana farawa..."
    )

    # =====================================
    # INITIALIZE
    # =====================================

    await app.initialize()

    print(
        "✅ Telegram API connected"
    )

    # =====================================
    # START APPLICATION
    # =====================================

    await app.start()

    print(
        "✅ Application started"
    )

    # =====================================
    # START POLLING
    # =====================================

    await app.updater.start_polling(
        drop_pending_updates=True
    )

    print(
        "🚀 BOT YANA AIKI!"
    )

    print(
        "📡 Waiting for Telegram messages..."
    )

    # =====================================
    # START AUTO SIGNAL ENGINE
    # =====================================

    if AUTO_SIGNAL_CHAT_ID:

        print(
            "🚀 Starting Auto Signal Engine..."
        )

        auto_signal_task = asyncio.create_task(
            start_auto_signals(
                app
            )
        )

    else:

        print(
            "⚠️ Auto Signal Engine disabled."
        )

        print(
            "⚠️ Set AUTO_SIGNAL_CHAT_ID "
            "inside .env"
        )

    # =====================================
    # KEEP BOT ALIVE
    # =====================================

    try:

        while True:

            await asyncio.sleep(
                3600
            )

    except asyncio.CancelledError:

        print(
            "🛑 Bot task cancelled."
        )

    except KeyboardInterrupt:

        print(
            "\n🛑 Bot stopped by user."
        )

    finally:

        print(
            "⏳ Shutting down..."
        )

        # =================================
        # STOP AUTO SIGNAL ENGINE
        # =================================

        if auto_signal_engine:

            auto_signal_engine.stop()

        if auto_signal_task:

            if not auto_signal_task.done():

                auto_signal_task.cancel()

                try:

                    await auto_signal_task

                except asyncio.CancelledError:

                    pass

                except Exception as exc:

                    logger.error(
                        "Auto signal shutdown error: %s",
                        exc,
                    )

        # =================================
        # STOP TELEGRAM
        # =================================

        if app.updater:

            if app.updater.running:

                await app.updater.stop()

        if app.running:

            await app.stop()

        await app.shutdown()

        print(
            "✅ Bot shutdown complete."
        )


# =========================================
# ENTRY POINT
# =========================================

if __name__ == "__main__":

    try:

        asyncio.run(
            run_bot()
        )

    except KeyboardInterrupt:

        print(
            "\n🛑 Bot stopped."
        )
