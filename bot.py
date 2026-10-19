import asyncio
import html
import hmac
import logging
import os
import re
import threading
import sqlite3
import time
import uuid
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, render_template, redirect, url_for, session, flash
from telegram import Bot

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
from services.dashboard_report import report_if_due, restore_report
from services.history import SignalHistory
from services.group_cleanup import (
    GroupCleanupService,
    add_cleanup_handler,
)

from web.dashboard import load_dashboard, perform_scan
from services.dexscreener import DexScreener

# =========================================
# CLOUD WEB SERVER / HEALTH ENDPOINTS
# =========================================
app_web = Flask(__name__)
# Website authentication: set a long random SITE_SECRET_KEY in the hosting environment.
app_web.secret_key = os.getenv("SITE_SECRET_KEY", "")
app_web.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "true").lower() not in {"0", "false", "no"})

# User accounts live in a separate SQLite file by default, independent of bot history.
_AUTH_DB = os.getenv("SITE_AUTH_DB", os.path.join(os.path.dirname(__file__), "site_users.db"))
_ADMIN_EMAIL = os.getenv("SITE_ADMIN_EMAIL", "salimyahayagumel@gmail.com").strip().lower()

def _auth_connect():
    # Resolve the database path at connection time so tests and deployments
    # can override SITE_AUTH_DB without reusing a path captured at import.
    db_path = os.getenv("SITE_AUTH_DB") or _AUTH_DB
    conn = sqlite3.connect(db_path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS site_users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    return conn

def _auth_admin_configured():
    return bool(app_web.secret_key and os.getenv("SITE_ADMIN_PASSWORD"))

def _site_admin():
    return session.get("user_email", "").lower() == _ADMIN_EMAIL and session.get("role") == "admin"

class _LazySignalHistory:
    """Defer database connections until signal history is actually requested."""
    def __init__(self, database_url):
        self.database_url = database_url
        self._instance = None
        self._lock = threading.Lock()

    def __getattr__(self, name):
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    self._instance = SignalHistory(self.database_url)
        return getattr(self._instance, name)

signal_history_store = _LazySignalHistory(DATABASE_URL)
DASHBOARD_BOOT_ID = uuid.uuid4().hex

# Dashboard HTML
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>MASFOX - LIVE</title>
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
        <h1>💎 MASFOX</h1>
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
        MASFOX © 2026 - Running 24/7 on Render.com
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

@app_web.route("/register", methods=["GET", "POST"])
def site_register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()[:100]
        email = request.form.get("email", "").strip().lower()[:254]
        password = request.form.get("password", "")
        if not name or not email or "@" not in email or len(password) < 10:
            flash("Cika bayanai daidai; password ya zama aƙalla haruffa 10.", "danger")
            return render_template("auth.html", mode="register"), 400
        # Admin email is reserved: only the password configured privately on the server can create its session.
        if email == _ADMIN_EMAIL:
            admin_password = os.getenv("SITE_ADMIN_PASSWORD", "")
            if not admin_password or not hmac.compare_digest(password, admin_password):
                flash("Ba a iya ƙirƙirar wannan account ta wannan fom ba.", "danger")
                return render_template("auth.html", mode="register"), 403
        from werkzeug.security import generate_password_hash
        try:
            with _auth_connect() as conn:
                conn.execute("INSERT INTO site_users(name,email,password_hash) VALUES(?,?,?)", (name, email, generate_password_hash(password)))
        except sqlite3.IntegrityError:
            flash("An riga an yi rajista da wannan imel.", "warning")
            return render_template("auth.html", mode="register"), 409
        session.clear()
        session["user_email"] = email
        session["user_name"] = name
        session["role"] = "admin" if email == _ADMIN_EMAIL and _auth_admin_configured() else "user"
        return redirect(url_for("site_admin" if _site_admin() else "site_account"))
    return render_template("auth.html", mode="register")

@app_web.route("/login", methods=["GET", "POST"])
def site_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()[:254]
        password = request.form.get("password", "")
        from werkzeug.security import check_password_hash, generate_password_hash
        # Admin authentication is checked against a server-side environment secret, never browser storage.
        if email == _ADMIN_EMAIL and _auth_admin_configured() and hmac.compare_digest(password, os.getenv("SITE_ADMIN_PASSWORD", "")):
            with _auth_connect() as conn:
                row = conn.execute("SELECT name FROM site_users WHERE email=?", (email,)).fetchone()
                if row is None:
                    conn.execute("INSERT INTO site_users(name,email,password_hash) VALUES(?,?,?)", ("Site Admin", email, generate_password_hash(password)))
            session.clear()
            session["user_email"] = email
            session["user_name"] = "Admin"
            session["role"] = "admin"
            return redirect(url_for("site_admin"))
        with _auth_connect() as conn:
            row = conn.execute("SELECT * FROM site_users WHERE email=?", (email,)).fetchone()
        if row and email != _ADMIN_EMAIL and check_password_hash(row["password_hash"], password):
            session.clear()
            session["user_email"] = row["email"].lower()
            session["user_name"] = row["name"]
            session["role"] = "user"
            return redirect(url_for("site_account"))
        flash("Imel ko kalmar sirri ba daidai ba ne.", "danger")
        return render_template("auth.html", mode="login"), 401
    return render_template("auth.html", mode="login")

@app_web.route("/logout", methods=["POST"])
def site_logout():
    session.clear()
    return redirect(url_for("site_login"))

@app_web.route("/account")
def site_account():
    if not session.get("user_email"):
        return redirect(url_for("site_login"))
    if _site_admin():
        return redirect(url_for("site_admin"))
    return render_template("account.html", name=session.get("user_name", "User"), email=session["user_email"])

@app_web.route("/admin")
def site_admin():
    if not _site_admin():
        return redirect(url_for("site_login"))
    with _auth_connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM site_users").fetchone()[0]
        users = conn.execute("SELECT name,email,created_at FROM site_users ORDER BY id DESC LIMIT 100").fetchall()
    return render_template("admin.html", email=session["user_email"], user_count=count, users=users)

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


@app_web.route("/api/dashboard-cycle")
def dashboard_cycle_status():
    """Expose only this process boot ID so the browser can clear dashboard-only state after restart."""
    return jsonify({"success": True, "boot_id": DASHBOARD_BOOT_ID}), 200, {"Cache-Control": "no-store"}


@app_web.route("/ready")
def readiness_check():
    """Lightweight readiness endpoint for cloud load balancers."""
    return jsonify({
        "success": True,
        "ready": True,
        "service": "MASFOX",
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
        "bot": "MASFOX",
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


# =========================================================
# ADMIN-ONLY MANUAL TELEGRAM SIGNALS
# =========================================================
MANUAL_SIGNAL_KEY_ENV = "DASHBOARD_MANUAL_SIGNAL_KEY"
MANUAL_SIGNAL_CHAT_ID = AUTO_SIGNAL_CHAT_ID
_MANUAL_SEND_LOCK = threading.Lock()
_MANUAL_LAST_SENT_AT = 0.0
_MANUAL_SEND_COOLDOWN = max(3, int(os.getenv("DASHBOARD_MANUAL_SIGNAL_COOLDOWN", "10")))
_MANUAL_ALLOWED_CHAINS = {"solana", "base", "robinhood", "arc"}
_MANUAL_SIGNAL_TYPES = {"MANUAL BUY", "MANUAL GEM", "WATCHLIST", "HIGH RISK — DYOR"}


def _manual_admin_authorized():
    configured = os.getenv(MANUAL_SIGNAL_KEY_ENV, "").strip()
    supplied = request.headers.get("X-Manual-Signal-Key", "").strip()
    # Fail closed: no key means the feature remains disabled.
    return bool(configured and supplied and hmac.compare_digest(configured, supplied))


def _manual_chain_matches(pair, requested_chain):
    actual = str(pair.get("chainId") or "").strip().lower()
    aliases = {"solana": {"solana"}, "base": {"base"},
               "robinhood": {"robinhood", "robinhood-chain"}, "arc": {"arc"}}
    return actual in aliases.get(requested_chain, {requested_chain})


def _manual_pair_contains_address(pair, address):
    target = str(address or "").lower()
    base = str((pair.get("baseToken") or {}).get("address") or "").lower()
    quote = str((pair.get("quoteToken") or {}).get("address") or "").lower()
    return bool(target and target in {base, quote})


def _manual_token_snapshot(pair, address):
    base = pair.get("baseToken") or {}
    quote = pair.get("quoteToken") or {}
    address_lower = address.lower()
    token = base if str(base.get("address") or "").lower() == address_lower else quote
    liquidity = pair.get("liquidity") or {}
    volume = pair.get("volume") or {}
    txns = pair.get("txns") or {}
    h24 = txns.get("h24") or {}
    return {
        "name": str(token.get("name") or "Unknown token")[:100],
        "symbol": str(token.get("symbol") or "N/A")[:30],
        "address": str(token.get("address") or address)[:120],
        "chain": str(pair.get("chainId") or "unknown").lower(),
        "price_usd": str(pair.get("priceUsd") or "0")[:40],
        "marketcap": pair.get("marketCap") or pair.get("fdv") or 0,
        "liquidity": liquidity.get("usd") or 0,
        "volume24h": volume.get("h24") or 0,
        "buys24h": h24.get("buys") or 0,
        "sells24h": h24.get("sells") or 0,
        "pair_address": str(pair.get("pairAddress") or "")[:120],
        "url": str(pair.get("url") or "")[:500],
        "dex": str(pair.get("dexId") or "DEX")[:60],
        "image_url": str(((pair.get("info") or {}).get("imageUrl")) or "")[:500],
    }


@app_web.route("/api/manual-signal/status", methods=["GET"])
def manual_signal_status():
    enabled = bool(os.getenv(MANUAL_SIGNAL_KEY_ENV, "").strip() and BOT_TOKEN and MANUAL_SIGNAL_CHAT_ID)
    return jsonify({"success": True, "enabled": enabled, "admin_only": True,
                    "chat_configured": bool(MANUAL_SIGNAL_CHAT_ID)}), 200


@app_web.route("/api/manual-signal/lookup", methods=["POST"])
def manual_signal_lookup():
    if not _manual_admin_authorized():
        return jsonify({"success": False, "error": "Admin authorization failed or manual signals are disabled."}), 403
    payload = request.get_json(silent=True) or {}
    address = str(payload.get("address") or "").strip()
    chain = str(payload.get("chain") or "").strip().lower()
    if not (20 <= len(address) <= 120) or not re.fullmatch(r"[A-Za-z0-9]+", address):
        return jsonify({"success": False, "error": "Enter a valid contract address."}), 400
    if chain not in _MANUAL_ALLOWED_CHAINS:
        return jsonify({"success": False, "error": "Unsupported chain selection."}), 400

    async def lookup_pairs():
        dex = DexScreener()
        try:
            return await dex.tokens([address], retries=1)
        finally:
            await dex.close()
    try:
        pairs = asyncio.run(lookup_pairs())
    except Exception as exc:
        logger.warning("Manual signal token lookup failed: %s", exc)
        return jsonify({"success": False, "error": "Token lookup failed. Please retry."}), 502
    matching = [p for p in pairs if _manual_chain_matches(p, chain) and _manual_pair_contains_address(p, address)]
    if not matching:
        return jsonify({"success": False, "error": "Token not found on DexScreener for the selected chain. Confirm the address and chain."}), 404
    matching.sort(key=lambda p: float(((p.get("liquidity") or {}).get("usd") or 0)), reverse=True)
    token = _manual_token_snapshot(matching[0], address)
    return jsonify({"success": True, "token": token,
                    "warning": "Manual signal bypasses Auto Signal eligibility gates. Data may be incomplete; verify token risks independently."}), 200


@app_web.route("/api/manual-signal/send", methods=["POST"])
def manual_signal_send():
    global _MANUAL_LAST_SENT_AT
    if not _manual_admin_authorized():
        return jsonify({"success": False, "error": "Admin authorization failed or manual signals are disabled."}), 403
    payload = request.get_json(silent=True) or {}
    address = str(payload.get("address") or "").strip()
    chain = str(payload.get("chain") or "").strip().lower()
    signal_type = str(payload.get("signal_type") or "MANUAL GEM").strip().upper()
    reason = str(payload.get("reason") or "").strip()
    if not (20 <= len(address) <= 120) or not re.fullmatch(r"[A-Za-z0-9]+", address):
        return jsonify({"success": False, "error": "Enter a valid contract address."}), 400
    if chain not in _MANUAL_ALLOWED_CHAINS or signal_type not in _MANUAL_SIGNAL_TYPES:
        return jsonify({"success": False, "error": "Invalid chain or signal type."}), 400
    if not reason or len(reason) > 500:
        return jsonify({"success": False, "error": "Reason must be between 1 and 500 characters."}), 400
    if not BOT_TOKEN or not MANUAL_SIGNAL_CHAT_ID:
        return jsonify({"success": False, "error": "Telegram bot token or AUTO_SIGNAL_CHAT_ID is not configured."}), 503

    # Always fetch market data again at send-time; never trust browser-supplied prices.
    async def lookup_pairs():
        dex = DexScreener()
        try:
            return await dex.tokens([address], retries=1)
        finally:
            await dex.close()
    try:
        pairs = asyncio.run(lookup_pairs())
    except Exception as exc:
        logger.warning("Manual signal pre-send lookup failed: %s", exc)
        return jsonify({"success": False, "error": "Could not refresh token data. Signal was not sent."}), 502
    matching = [p for p in pairs if _manual_chain_matches(p, chain) and _manual_pair_contains_address(p, address)]
    if not matching:
        return jsonify({"success": False, "error": "Token no longer appears on DexScreener for the selected chain. Signal was not sent."}), 404
    matching.sort(key=lambda p: float(((p.get("liquidity") or {}).get("usd") or 0)), reverse=True)
    token = _manual_token_snapshot(matching[0], address)
    with _MANUAL_SEND_LOCK:
        now = time.monotonic()
        if now - _MANUAL_LAST_SENT_AT < _MANUAL_SEND_COOLDOWN:
            wait = max(1, int(_MANUAL_SEND_COOLDOWN - (now - _MANUAL_LAST_SENT_AT)))
            return jsonify({"success": False, "error": f"Please wait {wait}s before sending another manual signal."}), 429
        _MANUAL_LAST_SENT_AT = now

    esc = lambda value: html.escape(str(value if value is not None else "—"), quote=True)
    explorer = (f"https://solscan.io/token/{token['address']}" if chain == "solana" else
                f"https://basescan.org/token/{token['address']}" if chain == "base" else token["url"])
    message = (
        f"🖐️ <b>SALIM SAUKI DATA — {esc(signal_type)}</b>\n"
        f"⚠️ <b>MANUAL SIGNAL · NOT AUTO-APPROVED</b>\n\n"
        f"🪙 <b>${esc(token['symbol'])}</b> — {esc(token['name'])}\n"
        f"⛓️ Chain: <b>{esc(token['chain'].title())}</b>\n"
        f"💵 Price: <b>${esc(token['price_usd'])}</b>\n"
        f"🏦 Market Cap / FDV: <b>${esc(token['marketcap'])}</b>\n"
        f"💧 Liquidity: <b>${esc(token['liquidity'])}</b>\n"
        f"📊 Volume 24H: <b>${esc(token['volume24h'])}</b>\n"
        f"🛒 Buys / Sells 24H: <b>{esc(token['buys24h'])} / {esc(token['sells24h'])}</b>\n"
        f"📝 Admin note: {esc(reason)}\n\n"
        f"📍 CA: <code>{esc(token['address'])}</code>\n"
        f"📈 <a href=\"{esc(token['url'])}\">Chart</a> · "
        f"🔍 <a href=\"{esc(explorer)}\">Explorer</a>\n\n"
        "🛡️ <b>Risk warning:</b> This manual signal bypasses Auto Signal eligibility gates. Security is not guaranteed. DYOR; not financial advice."
    )
    try:
        async def send_message():
            async with Bot(token=BOT_TOKEN) as telegram_bot:
                return await telegram_bot.send_message(
                    chat_id=MANUAL_SIGNAL_CHAT_ID, text=message,
                    parse_mode="HTML", disable_web_page_preview=True,
                )
        sent = asyncio.run(send_message())
        logger.info("Manual signal sent by dashboard admin: chain=%s address=%s message_id=%s", chain, address, getattr(sent, "message_id", "unknown"))
        return jsonify({"success": True, "message": "Manual signal sent to the configured Telegram group.",
                        "message_id": getattr(sent, "message_id", None), "symbol": token["symbol"]}), 200
    except Exception as exc:
        logger.exception("Manual Telegram signal send failed")
        with _MANUAL_SEND_LOCK:
            _MANUAL_LAST_SENT_AT = 0.0
        return jsonify({"success": False, "error": "Telegram delivery failed. Check bot permissions and AUTO_SIGNAL_CHAT_ID."}), 502


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
        "bot": "MASFOX",
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


TELEGRAM_POLLING_ENABLED = os.getenv("TELEGRAM_POLLING_ENABLED", "true").strip().lower() in {"1","true","yes","on"}
CLEANUP_POLLING_ENABLED = os.getenv("CLEANUP_POLLING_ENABLED", "false").strip().lower() in {"1","true","yes","on"}
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()

def run_web():
    if ENVIRONMENT == "production":
        print("ℹ️ Production mode: dashboard should run via gunicorn (bot:app_web).")
        return
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

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

async def dashboard_report_loop(bot, chat_id):
    """Send persisted aggregate report every 24h without deleting bot history."""
    while True:
        await asyncio.sleep(30)
        report = report_if_due()
        if not report:
            continue
        started = datetime.fromtimestamp(float(report["started_at"])).strftime("%Y-%m-%d %H:%M:%S")
        message = (
            "📊 <b>MASFOX — 24-HOUR REPORT</b>\n\n"
            f"🔎 Auto scans completed: <b>{int(report['scans'])}</b>\n"
            f"🪙 Candidates found: <b>{int(report['candidates_found'])}</b>\n"
            f"📨 Signals sent: <b>{int(report['signals_sent'])}</b>\n"
            f"🚀 STRONG GEM: <b>{int(report['strong_gem'])}</b>\n"
            f"💎 GEM SIGNAL: <b>{int(report['gem_signal'])}</b>\n"
            f"🌱 EARLY GEM: <b>{int(report['early_gem'])}</b>\n\n"
            f"🕒 Cycle started: {started}\n"
            "🔄 A new 24-hour reporting cycle has started.\n"
            "Dashboard-only history resets separately; bot signal and PNL databases are preserved."
        )
        try:
            await bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as exc:
            restore_report(report)
            logging.error("24-hour dashboard report Telegram send failed; counters restored: %s", exc)
            await asyncio.sleep(60)


async def run_bot():
    global auto_signal_task, auto_signal_engine, cleanup_app, cleanup_service, cleanup_uses_main_app
    dashboard_report_task = None
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
    if TELEGRAM_POLLING_ENABLED:
        await app.updater.start_polling(drop_pending_updates=True)
        print("🚀 BOT YANA AIKI!")
    else:
        print("ℹ️ Telegram polling disabled; this process is web-only.")
    print("📡 Waiting for Telegram messages...")
    if CLEANUP_BOT_TOKEN and CLEANUP_CHAT_ID:
        print("🧹 Starting Group Cleanup...")
        if CLEANUP_BOT_TOKEN == BOT_TOKEN:
            cleanup_uses_main_app = True
            cleanup_service = GroupCleanupService(bot=app.bot, chat_id=CLEANUP_CHAT_ID, delete_after_seconds=CLEANUP_DELETE_AFTER_SECONDS, check_interval_seconds=CLEANUP_CHECK_INTERVAL, database_path=CLEANUP_DATABASE_PATH)
            add_cleanup_handler(app, cleanup_service)
            await cleanup_service.diagnose()
            await cleanup_service.start()
        elif CLEANUP_POLLING_ENABLED:
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
        else:
            print("⚠️ Separate cleanup polling disabled; use same BOT_TOKEN for single-instance cleanup.")
        if cleanup_service:
            print("🧹 Cleanup Bot is ACTIVE")
    else:
        print("⚠️ Group Cleanup Bot disabled.")
    if AUTO_SIGNAL_CHAT_ID:
        dashboard_report_task = asyncio.create_task(dashboard_report_loop(app.bot, AUTO_SIGNAL_CHAT_ID))
        print("📊 24-hour Telegram report scheduler started.")
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
        if dashboard_report_task and not dashboard_report_task.done():
            dashboard_report_task.cancel()
            try:
                await dashboard_report_task
            except asyncio.CancelledError:
                pass
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
