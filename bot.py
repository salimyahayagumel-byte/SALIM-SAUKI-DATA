import asyncio
import logging
import os
import threading
import sqlite3
import time
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from telegram.request import HTTPXRequest

from config import (
    BOT_TOKEN,
    BOT_USERNAME,
    CLEANUP_BOT_TOKEN,
    CLEANUP_CHAT_ID,
    CLEANUP_DELETE_AFTER_SECONDS,
    CLEANUP_CHECK_INTERVAL,
    CLEANUP_DATABASE_PATH,
    AUTO_SIGNAL_CHAT_ID,
    AUTO_SIGNAL_ENABLED,
    AUTO_SIGNAL_INTERVAL,
    AUTO_SIGNAL_MAX_SIGNALS_PER_SCAN,
    AUTO_SIGNAL_MAX_SIGNALS_PER_CHAIN,
    PNL_TRACKER_ENABLED,
    PNL_TRACKER_INTERVAL,
    PNL_TRACKER_MAX_TRACKED,
    DATABASE_URL,
)

from handlers.start import start
from handlers.scan import scan
from handlers.analyze import analyze
from handlers.help import help_command
from handlers.status import status
from handlers.health import health
from handlers.pnl import pnl
from handlers.autostatus import autostatus

from services.auto_signal import AutoSignalEngine
from services.history import SignalHistory
from services.group_cleanup import (
    GroupCleanupService,
    add_cleanup_handler,
)

from web.dashboard import load_dashboard, perform_scan

# =========================================
# CLOUD WEB SERVER / HEALTH ENDPOINTS
# =========================================
app_web = Flask(__name__)
signal_history_store = SignalHistory(DATABASE_URL)

# Dashboard HTML
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>SALIM SAUKI DATA - LIVE</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="30">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Segoe UI',Arial;background:#070a12;color:#e0ffe0;min-height:100vh;padding:15px}
       .header{text-align:center;padding:20px;background:linear-gradient(135deg,#0f1b2e,#1a3a2a);border-radius:20px;border:1px solid #00ff88;margin-bottom:20px}
       .header h1{font-size:28px;color:#00ff88}
       .live{color:#00ff88;animation:blink 1.5s infinite}
        @keyframes blink{0%,100%{opacity:1}50%{opacity:0.3}}
       .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:15px;margin-bottom:20px}
       .card{background:#111a2b;border:1px solid #1f3a5f;border-radius:15px;padding:20px}
       .card h3{color:#00ff88;margin-bottom:12px;font-size:16px}
       .stat{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #1a2a40}
       .stat:last-child{border:none}
       .val{color:#ffd700;font-weight:bold}
       .online{color:#00ff88}.offline{color:#ff4444}
       .btn{display:inline-block;margin:5px;padding:10px 18px;background:#00ff88;color:#000;border-radius:10px;text-decoration:none;font-weight:bold;font-size:14px}
       .btn2{background:#1a2a40;color:#00ff88;border:1px solid #00ff88}
       .footer{text-align:center;padding:20px;color:#666;font-size:12px}
    </style>
</head>
<body>
    <div class="header">
        <h1>💎 SALIM SAUKI DATA</h1>
        <p><span class="live">● LIVE</span> - Bot is running 24/7</p>
        <p style="font-size:12px;margin-top:8px;opacity:0.7">Last Update: __TIME__ | Auto-Refresh 30s</p>
    </div>

    <div class="grid">
        <div class="card">
            <h3>🤖 BOT STATUS</h3>
            <div class="stat"><span>Telegram Bot</span><span class="val online">● ONLINE</span></div>
            <div class="stat"><span>Web Server</span><span class="val online">● LIVE</span></div>
            <div class="stat"><span>UptimeRobot</span><span class="val online">● KEEPING ALIVE</span></div>
            <div class="stat"><span>Environment</span><span class="val">Production</span></div>
        </div>

        <div class="card">
            <h3>📡 AUTO SIGNAL ENGINE</h3>
            <div class="stat"><span>Enabled</span><span class="val">__AUTO_ENABLED__</span></div>
            <div class="stat"><span>Interval</span><span class="val">__INTERVAL__s</span></div>
            <div class="stat"><span>Max/Scan</span><span class="val">__MAX_SCAN__</span></div>
            <div class="stat"><span>Chat ID</span><span class="val" style="font-size:10px">__CHAT_ID__</span></div>
        </div>

        <div class="card">
            <h3>📈 PNL TRACKER</h3>
            <div class="stat"><span>Enabled</span><span class="val">__PNL_ENABLED__</span></div>
            <div class="stat"><span>Interval</span><span class="val">__PNL_INTERVAL__s</span></div>
            <div class="stat"><span>Max Tracked</span><span class="val">__PNL_MAX__</span></div>
            <div class="stat"><span>Tracked Tokens</span><span class="val">__PNL_COUNT__</span></div>
        </div>

        <div class="card">
            <h3>🧹 CLEANUP SERVICE</h3>
            <div class="stat"><span>Status</span><span class="val">__CLEANUP_STATUS__</span></div>
            <div class="stat"><span>Delete After</span><span class="val">__CLEANUP_AFTER__s</span></div>
            <div class="stat"><span>Messages in DB</span><span class="val">__CLEANUP_COUNT__</span></div>
            <div class="stat"><span>Database</span><span class="val" style="font-size:10px">cleanup_messages.db</span></div>
        </div>
    </div>

    <div class="card" style="text-align:center">
        <h3>⚡ QUICK ACTIONS</h3>
        <br>
        <a class="btn" href="/health">Health Check</a>
        <a class="btn btn2" href="/api/status">API Status (JSON)</a>
        <a class="btn btn2" href="__BOT_URL__" __BOT_TARGET__>Telegram Bot</a>
        <a class="btn btn2" href="https://dashboard.render.com">Render Dashboard</a>
        <br><br>
        <p style="font-size:12px;color:#888">Bot Owner: Salim Sauki | Built with 💎 DEX Analysis Engine V10</p>
    </div>

    <div class="footer">
        SALIM SAUKI DATA © 2026 - Running 24/7 on Render.com
    </div>
</body>
</html>
"""

def get_db_counts():
    cleanup_count = 0
    pnl_count = 0
    try:
        if os.path.exists("./cleanup_messages.db"):
            conn = sqlite3.connect("./cleanup_messages.db")
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM messages")
            cleanup_count = cur.fetchone()[0]
            conn.close()
    except:
        pass
    try:
        if os.path.exists("./salim_sauki_data.db"):
            conn = sqlite3.connect("./salim_sauki_data.db")
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cur.fetchall()
            for t in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {t[0]}")
                    pnl_count += cur.fetchone()[0]
                except:
                    pass
            conn.close()
    except:
        pass
    return cleanup_count, pnl_count

@app_web.route('/')
def home():
    """Primary public page: the live GEM terminal."""
    return load_dashboard(), 200, {"Cache-Control": "no-cache, no-store, must-revalidate"}


@app_web.route('/status')
def status_page():
    cleanup_count, pnl_count = get_db_counts()
    html = DASHBOARD_HTML
    html = html.replace("__TIME__", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    html = html.replace("__AUTO_ENABLED__", "✅ YES" if AUTO_SIGNAL_ENABLED else "❌ NO")
    html = html.replace("__INTERVAL__", str(AUTO_SIGNAL_INTERVAL))
    html = html.replace("__MAX_SCAN__", str(AUTO_SIGNAL_MAX_SIGNALS_PER_SCAN))
    html = html.replace("__CHAT_ID__", "CONFIGURED" if AUTO_SIGNAL_CHAT_ID else "NOT CONFIGURED")
    bot_url = f"https://t.me/{BOT_USERNAME}" if BOT_USERNAME else "#"
    html = html.replace("__BOT_URL__", bot_url)
    html = html.replace("__BOT_TARGET__", "target=\"_blank\" rel=\"noopener noreferrer\"" if BOT_USERNAME else "aria-disabled=\"true\"")
    html = html.replace("__PNL_ENABLED__", "✅ YES" if PNL_TRACKER_ENABLED else "❌ NO")
    html = html.replace("__PNL_INTERVAL__", str(PNL_TRACKER_INTERVAL))
    html = html.replace("__PNL_MAX__", str(PNL_TRACKER_MAX_TRACKED))
    html = html.replace("__PNL_COUNT__", str(pnl_count))
    html = html.replace("__CLEANUP_STATUS__", "✅ ACTIVE" if CLEANUP_BOT_TOKEN and CLEANUP_CHAT_ID else "⚠️ DISABLED")
    html = html.replace("__CLEANUP_AFTER__", str(CLEANUP_DELETE_AFTER_SECONDS))
    html = html.replace("__CLEANUP_COUNT__", str(cleanup_count))
    return html

@app_web.route("/dashboard")
def dashboard_page():
    """Serve the full live scanner dashboard from the same web service."""
    return load_dashboard(), 200, {"Cache-Control": "no-cache, no-store, must-revalidate"}


@app_web.route("/ready")
def readiness_check():
    """Lightweight readiness endpoint for cloud load balancers."""
    return jsonify({
        "success": True,
        "ready": True,
        "service": "SALIM SAUKI DATA",
    }), 200


@app_web.route("/api/signals")
def live_signals():
    """Return recently delivered Telegram signals for the live terminal."""
    try:
        limit = max(1, min(int(request.args.get("limit", 100)), 100))
    except (TypeError, ValueError):
        limit = 100
    chain = request.args.get("chain", "").strip().lower()
    signals = signal_history_store.recent_signals(limit=limit)
    if chain and chain != "all":
        signals = [s for s in signals if str(s.get("chain", "")).lower() == chain]
    return jsonify({
        "success": True,
        "signals": signals,
        "count": len(signals),
        "updated_at": datetime.now().isoformat(),
    }), 200


@app_web.route("/api/signals/<chain>/<address>")
def signal_detail(chain, address):
    """Return one recently delivered signal snapshot."""
    signals = signal_history_store.recent_signals(limit=500)
    chain = str(chain).lower().strip()
    match = next((s for s in signals if str(s.get("chain", "")).lower() == chain and str(s.get("address", "")) == address), None)
    if not match:
        return jsonify({"success": False, "error": "Signal not found"}), 404
    return jsonify({"success": True, "signal": match}), 200


@app_web.route("/api/health")
def dashboard_health_check():
    """Compatibility health endpoint used by the dashboard/API layer."""
    return jsonify({
        "success": True,
        "status": "online",
        "bot": "SALIM SAUKI DATA",
        "scanner": "online",
    }), 200


@app_web.route("/api/scan", methods=["GET", "POST"])
def dashboard_scan():
    """Run the real scanner through the cloud-hosted Flask service."""
    query = (
        request.args.get("q")
        or request.args.get("query")
        or "sol"
    ).strip() or "sol"

    client_ip = request.remote_addr or "unknown"
    now = time.monotonic()
    with _dashboard_scan_lock:
        last_request = _dashboard_scan_last_request.get(client_ip, 0.0)
        if now - last_request < _DASHBOARD_SCAN_RATE_LIMIT_SECONDS:
            retry_after = max(1, int(_DASHBOARD_SCAN_RATE_LIMIT_SECONDS - (now - last_request)))
            return jsonify({
                "success": False,
                "error": "Dashboard scan rate limit reached.",
                "retry_after_seconds": retry_after,
                "tokens": [],
            }), 429
        _dashboard_scan_last_request[client_ip] = now

    result = perform_scan(query=query)

    if result.get("success"):
        return jsonify(result.get("tokens", [])), 200

    error = result.get("error", "Scan failed.")
    status = 409 if error == "A scan is already running." else 500
    return jsonify(result), status


@app_web.route("/static/<path:filename>")
def dashboard_static(filename):
    """Serve dashboard assets without exposing files outside static/."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return send_from_directory(static_dir, filename, max_age=0)


@app_web.route('/health')
def health_check():
    return "OK", 200

@app_web.route('/api/status')
def api_status():
    cleanup_count, pnl_count = get_db_counts()
    return jsonify({
        "bot": "SALIM SAUKI DATA",
        "status": "LIVE",
        "timestamp": datetime.now().isoformat(),
        "auto_signal": {
            "enabled": AUTO_SIGNAL_ENABLED,
            "interval": AUTO_SIGNAL_INTERVAL,
            "chat_configured": bool(AUTO_SIGNAL_CHAT_ID),
        },
        "pnl_tracker": {
            "enabled": PNL_TRACKER_ENABLED,
            "tracked_tokens": pnl_count,
        },
        "cleanup": {
            "enabled": bool(CLEANUP_BOT_TOKEN and CLEANUP_CHAT_ID),
            "messages_in_db": cleanup_count,
        },
        "uptime_robot": "KEEPING ALIVE"
    })

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host='0.0.0.0', port=port)

# =========================================
# LOGGING
# =========================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

auto_signal_engine = None
auto_signal_task = None
cleanup_app = None
cleanup_service = None
cleanup_uses_main_app = False

# Public dashboard scan endpoint protection.
_dashboard_scan_lock = threading.Lock()
_dashboard_scan_last_request = {}
_DASHBOARD_SCAN_RATE_LIMIT_SECONDS = max(1, int(os.getenv("DASHBOARD_SCAN_RATE_LIMIT_SECONDS", "15")))

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Telegram update error:", exc_info=context.error)

async def start_auto_signals(application: Application):
    global auto_signal_engine
    if not AUTO_SIGNAL_CHAT_ID:
        print("⚠️ AUTO_SIGNAL_CHAT_ID ba a saita ba.")
        return
    print("========================================")
    print("💎 DEX ANALYSIS BOT — AUTO SIGNAL")
    print("========================================")
    print(f"📡 Chat ID: {AUTO_SIGNAL_CHAT_ID}")
    print(f"⏱️ Interval: {AUTO_SIGNAL_INTERVAL}s")
    auto_signal_engine = AutoSignalEngine(
        bot=application.bot,
        chat_id=AUTO_SIGNAL_CHAT_ID,
        interval=AUTO_SIGNAL_INTERVAL,
        max_signals_per_scan=AUTO_SIGNAL_MAX_SIGNALS_PER_SCAN,
        max_signals_per_chain=AUTO_SIGNAL_MAX_SIGNALS_PER_CHAIN,
    )
    if PNL_TRACKER_ENABLED:
        auto_signal_engine.pnl_tracker.interval = max(15, PNL_TRACKER_INTERVAL)
        auto_signal_engine.pnl_tracker.max_tracked = max(50, PNL_TRACKER_MAX_TRACKED)
    application.bot_data["auto_signal_engine"] = auto_signal_engine
    await auto_signal_engine.start()

async def run_bot():
    global auto_signal_task, auto_signal_engine, cleanup_app, cleanup_service, cleanup_uses_main_app
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN baya cikin.env")
    telegram_httpx_kwargs = {"trust_env": False, "http2": False}
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=60.0, write_timeout=60.0, pool_timeout=30.0, http_version="1.1", httpx_kwargs=telegram_httpx_kwargs)
    get_updates_request = HTTPXRequest(connect_timeout=30.0, read_timeout=60.0, write_timeout=60.0, pool_timeout=30.0, http_version="1.1", httpx_kwargs=telegram_httpx_kwargs)
    app = Application.builder().token(BOT_TOKEN).request(request).get_updates_request(get_updates_request).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.add_handler(CommandHandler("analyze", analyze))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("health", health))
    app.add_handler(CommandHandler("pnl", pnl))
    app.add_handler(CommandHandler("autostatus", autostatus))
    app.add_error_handler(error_handler)
    print("========================================")
    print("🧠 DEX ANALYSIS BOT")
    print("💎 DEX ANALYSIS BOT")
    print("========================================")
    print("🤖 Bot yana farawa...")
    await app.initialize()
    print("✅ Telegram API connected")
    await app.start()
    print("✅ Application started")
    await app.updater.start_polling(drop_pending_updates=True)
    print("🚀 BOT YANA AIKI!")
    print("📡 Waiting for Telegram messages...")
    if CLEANUP_BOT_TOKEN and CLEANUP_CHAT_ID:
        print("🧹 Starting Group Cleanup...")
        if CLEANUP_BOT_TOKEN == BOT_TOKEN:
            cleanup_uses_main_app = True
            cleanup_service = GroupCleanupService(bot=app.bot, chat_id=CLEANUP_CHAT_ID, delete_after_seconds=CLEANUP_DELETE_AFTER_SECONDS, check_interval_seconds=CLEANUP_CHECK_INTERVAL, database_path=CLEANUP_DATABASE_PATH)
            add_cleanup_handler(app, cleanup_service)
            await cleanup_service.diagnose()
            await cleanup_service.start()
        else:
            cleanup_request = HTTPXRequest(connect_timeout=30.0, read_timeout=60.0, write_timeout=60.0, pool_timeout=30.0, http_version="1.1", httpx_kwargs=telegram_httpx_kwargs)
            cleanup_get_updates_request = HTTPXRequest(connect_timeout=30.0, read_timeout=60.0, write_timeout=60.0, pool_timeout=30.0, http_version="1.1", httpx_kwargs=telegram_httpx_kwargs)
            cleanup_app = Application.builder().token(CLEANUP_BOT_TOKEN).request(cleanup_request).get_updates_request(cleanup_get_updates_request).build()
            cleanup_service = GroupCleanupService(bot=cleanup_app.bot, chat_id=CLEANUP_CHAT_ID, delete_after_seconds=CLEANUP_DELETE_AFTER_SECONDS, check_interval_seconds=CLEANUP_CHECK_INTERVAL, database_path=CLEANUP_DATABASE_PATH)
            add_cleanup_handler(cleanup_app, cleanup_service)
            cleanup_app.add_error_handler(error_handler)
            await cleanup_app.initialize()
            await cleanup_app.start()
            if cleanup_app.updater:
                await cleanup_app.updater.start_polling(drop_pending_updates=True)
            await cleanup_service.start()
        print("🧹 Cleanup Bot is ACTIVE")
    else:
        print("⚠️ Group Cleanup Bot disabled.")
    if AUTO_SIGNAL_ENABLED and AUTO_SIGNAL_CHAT_ID:
        print("🚀 Starting Auto Signal Engine...")
        auto_signal_task = asyncio.create_task(start_auto_signals(app))
    else:
        print("⚠️ Auto Signal Engine disabled.")
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        print("🛑 Bot task cancelled.")
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user.")
    finally:
        print("⏳ Shutting down...")
        if auto_signal_engine:
            auto_signal_engine.stop()
        if auto_signal_task and not auto_signal_task.done():
            auto_signal_task.cancel()
            try:
                await auto_signal_task
            except:
                pass
        if cleanup_service:
            await cleanup_service.stop()
        if cleanup_app and not cleanup_uses_main_app:
            if cleanup_app.updater and cleanup_app.updater.running:
                await cleanup_app.updater.stop()
            if cleanup_app.running:
                await cleanup_app.stop()
            await cleanup_app.shutdown()
        if app.updater and app.updater.running:
            await app.updater.stop()
        if app.running:
            await app.stop()
        await app.shutdown()
        print("✅ Bot shutdown complete.")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    print("🌐 Flask web server started on PORT", os.environ.get("PORT", 10000))
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped.")
