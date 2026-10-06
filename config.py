"""
SALIM SAUKI DATA
DEX ANALYSIS BOT
CENTRAL CONFIGURATION

Production-safe configuration:
- Secrets are loaded only from .env / environment variables.
- No API keys are hardcoded.
- Multi-chain RPC support:
    Solana
    Base
    Robinhood
    Arc
- FluxRPC preferred for Solana when configured.
- Auto Signal:
    maximum 8 signals per scan
    maximum 2 signals per chain
- Security:
    Solana minimum: 90
    Base/Robinhood/Arc minimum: 69
- Market cap:
    minimum: $10,000
    maximum: $1,000,000
"""

import os

from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# SAFE ENVIRONMENT PARSING
# =========================================================

def _env_bool(name, default=False):
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _env_int(name, default):
    try:
        return int(
            os.getenv(
                name,
                str(default),
            )
        )
    except (TypeError, ValueError):
        return int(default)


def _env_float(name, default):
    try:
        return float(
            os.getenv(
                name,
                str(default),
            )
        )
    except (TypeError, ValueError):
        return float(default)


# =========================================================
# DATABASE
# =========================================================

DATABASE_URL = (
    os.getenv(
        "DATABASE_URL",
        "sqlite:///./salim_sauki_data.db",
    ).strip()
    or "sqlite:///./salim_sauki_data.db"
)


# =========================================================
# TELEGRAM BOT
# =========================================================

BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    "",
).strip()

BOT_USERNAME = (
    os.getenv(
        "BOT_USERNAME",
        "",
    )
    .strip()
    .lstrip("@")
)


# =========================================================
# TELEGRAM CHAT IDs
# =========================================================

ADMIN_ID = os.getenv(
    "ADMIN_ID",
    "",
).strip()

GROUP_ID = os.getenv(
    "GROUP_ID",
    "",
).strip()

# AUTO_SIGNAL_CHAT_ID takes priority.
# If missing/blank, safely fall back to GROUP_ID.
AUTO_SIGNAL_CHAT_ID = (
    os.getenv(
        "AUTO_SIGNAL_CHAT_ID",
        "",
    ).strip()
    or GROUP_ID
)


# =========================================================
# API KEYS
# =========================================================
# NEVER hardcode real keys here.
# Put them in .env.

BIRDEYE_API_KEY = os.getenv(
    "BIRDEYE_API_KEY",
    "",
).strip()

RUGCHECK_API_KEY = os.getenv(
    "RUGCHECK_API_KEY",
    "",
).strip()

HELIUS_API_KEY = os.getenv(
    "HELIUS_API_KEY",
    "",
).strip()


# =========================================================
# FLUXRPC — SOLANA
# =========================================================

FLUXRPC_API_KEY = os.getenv(
    "FLUXRPC_API_KEY",
    "",
).strip()

# Explicit URL has priority.
FLUXRPC_RPC_URL = os.getenv(
    "FLUXRPC_RPC_URL",
    "",
).strip()

# Build the official FluxRPC endpoint from the private API key
# when an explicit endpoint is not supplied.
if FLUXRPC_API_KEY:
    if not FLUXRPC_RPC_URL:
        FLUXRPC_RPC_URL = (
            "https://eu.fluxrpc.com"
            f"?key={FLUXRPC_API_KEY}"
        )
    elif "key=" not in FLUXRPC_RPC_URL:
        separator = "&" if "?" in FLUXRPC_RPC_URL else "?"
        FLUXRPC_RPC_URL = (
            f"{FLUXRPC_RPC_URL}"
            f"{separator}key={FLUXRPC_API_KEY}"
        )
# If no explicit URL exists, build the official EU endpoint
# from the private API key.
#
# IMPORTANT:
# The API key is never printed by this configuration.
if not FLUXRPC_RPC_URL and FLUXRPC_API_KEY:
    FLUXRPC_RPC_URL = (
        "https://eu.fluxrpc.com"
        f"?key={FLUXRPC_API_KEY}"
    )


# =========================================================
# AUTO SIGNAL ENGINE
# =========================================================

AUTO_SIGNAL_ENABLED = _env_bool(
    "AUTO_SIGNAL_ENABLED",
    True,
)

AUTO_SIGNAL_INTERVAL = _env_int(
    "AUTO_SIGNAL_INTERVAL",
    60,
)

# Final-score threshold.
AUTO_SIGNAL_MIN_SCORE = _env_int(
    "AUTO_SIGNAL_MIN_SCORE",
    75,
)

# Recommendation threshold.
AUTO_SIGNAL_MIN_RECOMMENDATION = _env_int(
    "AUTO_SIGNAL_MIN_RECOMMENDATION",
    75,
)

AUTO_SIGNAL_REQUIRE_SECURITY = _env_bool(
    "AUTO_SIGNAL_REQUIRE_SECURITY",
    True,
)

# Global configured security threshold.
# Chain-specific security remains authoritative in
# services/auto_signal.py:
#
# Solana     = 90
# Base       = 69
# Robinhood  = 69
# Arc        = 69
AUTO_SIGNAL_MIN_SECURITY = _env_int(
    "AUTO_SIGNAL_MIN_SECURITY",
    90,
)

AUTO_SIGNAL_REQUIRE_FINAL_SIGNAL = _env_bool(
    "AUTO_SIGNAL_REQUIRE_FINAL_SIGNAL",
    True,
)

# Maximum signals across ALL chains per scan.
AUTO_SIGNAL_MAX_SIGNALS_PER_SCAN = _env_int(
    "AUTO_SIGNAL_MAX_SIGNALS_PER_SCAN",
    8,
)

# Maximum signals from one chain per scan.
AUTO_SIGNAL_MAX_SIGNALS_PER_CHAIN = _env_int(
    "AUTO_SIGNAL_MAX_SIGNALS_PER_CHAIN",
    2,
)


# =========================================================
# PNL TRACKER
# =========================================================

PNL_TRACKER_ENABLED = _env_bool(
    "PNL_TRACKER_ENABLED",
    True,
)

PNL_TRACKER_INTERVAL = _env_int(
    "PNL_TRACKER_INTERVAL",
    60,
)

PNL_TRACKER_MAX_TRACKED = _env_int(
    "PNL_TRACKER_MAX_TRACKED",
    500,
)

PNL_TRACKER_DRAWDOWN_ALERT = _env_int(
    "PNL_TRACKER_DRAWDOWN_ALERT",
    20,
)


# =========================================================
# SCANNER
# =========================================================

SCAN_INTERVAL = _env_int(
    "SCAN_INTERVAL",
    60,
)

MAX_RESULTS = _env_int(
    "MAX_RESULTS",
    10,
)


# =========================================================
# MARKET CAP / BASIC SCANNER FILTERS
# =========================================================
#
# IMPORTANT:
# Do NOT change the market-cap range without explicit approval.
#
# $10,000 <= Market Cap <= $1,000,000

MIN_MARKETCAP = _env_float(
    "MIN_MARKETCAP",
    10_000,
)

MAX_MARKETCAP = _env_float(
    "MAX_MARKETCAP",
    1_000_000,
)

MIN_LIQUIDITY = _env_float(
    "MIN_LIQUIDITY",
    10_000,
)

MIN_VOLUME_24H = _env_float(
    "MIN_VOLUME_24H",
    5_000,
)

MIN_TXNS = _env_int(
    "MIN_TXNS",
    20,
)

MIN_BUY_RATIO = _env_float(
    "MIN_BUY_RATIO",
    0.50,
)


# =========================================================
# GEM DETECTION
# =========================================================

MIN_GEM_SCORE = _env_int(
    "MIN_GEM_SCORE",
    70,
)

STRONG_GEM_SCORE = _env_int(
    "STRONG_GEM_SCORE",
    80,
)

EARLY_GEM_SCORE = _env_int(
    "EARLY_GEM_SCORE",
    60,
)

WATCH_SCORE = _env_int(
    "WATCH_SCORE",
    50,
)

MIN_GEM_SIGNAL = _env_int(
    "MIN_GEM_SIGNAL",
    65,
)

MIN_STRONG_GEM = _env_int(
    "MIN_STRONG_GEM",
    72,
)


# =========================================================
# AI SCORING
# =========================================================

MIN_AI_SIGNAL = _env_int(
    "MIN_AI_SIGNAL",
    60,
)

AI_STRONG_BUY_SCORE = _env_int(
    "AI_STRONG_BUY_SCORE",
    85,
)

AI_BUY_SCORE = _env_int(
    "AI_BUY_SCORE",
    75,
)

AI_WATCH_SCORE = _env_int(
    "AI_WATCH_SCORE",
    65,
)


# =========================================================
# SECURITY
# =========================================================

MIN_SECURITY_SCORE = _env_int(
    "MIN_SECURITY_SCORE",
    69,
)

REQUIRE_MINT_AUTHORITY_DISABLED = _env_bool(
    "REQUIRE_MINT_AUTHORITY_DISABLED",
    True,
)

REQUIRE_FREEZE_AUTHORITY_DISABLED = _env_bool(
    "REQUIRE_FREEZE_AUTHORITY_DISABLED",
    True,
)

REQUIRE_INITIALIZED = _env_bool(
    "REQUIRE_INITIALIZED",
    True,
)


# =========================================================
# FINAL SIGNAL SAFETY
# =========================================================

FINAL_MIN_LIQUIDITY = _env_float(
    "FINAL_MIN_LIQUIDITY",
    10_000,
)

FINAL_MIN_MARKET_CAP = _env_float(
    "FINAL_MIN_MARKET_CAP",
    10_000,
)

FINAL_MAX_MARKET_CAP = _env_float(
    "FINAL_MAX_MARKET_CAP",
    1_000_000,
)

FINAL_MIN_BUY_RATIO = _env_float(
    "FINAL_MIN_BUY_RATIO",
    0.50,
)

FINAL_MIN_VOLUME_RATIO = _env_float(
    "FINAL_MIN_VOLUME_RATIO",
    0.03,
)

FINAL_MIN_TXNS = _env_int(
    "FINAL_MIN_TXNS",
    20,
)

MAX_SAFE_VOLUME_RATIO = _env_float(
    "MAX_SAFE_VOLUME_RATIO",
    15,
)

EXTREME_VOLUME_RATIO = _env_float(
    "EXTREME_VOLUME_RATIO",
    25,
)


# =========================================================
# RECOMMENDATION ENGINE
# =========================================================

RECOMMENDATION_STRONG_BUY = _env_int(
    "RECOMMENDATION_STRONG_BUY",
    80,
)

RECOMMENDATION_BUY = _env_int(
    "RECOMMENDATION_BUY",
    65,
)

RECOMMENDATION_WATCH = _env_int(
    "RECOMMENDATION_WATCH",
    55,
)

RECOMMENDATION_HIGH_RISK = _env_int(
    "RECOMMENDATION_HIGH_RISK",
    45,
)

RECOMMENDATION_MIN_SECURITY = _env_int(
    "RECOMMENDATION_MIN_SECURITY",
    70,
)

RECOMMENDATION_MIN_LIQUIDITY = _env_float(
    "RECOMMENDATION_MIN_LIQUIDITY",
    10_000,
)

RECOMMENDATION_MIN_VOLUME = _env_float(
    "RECOMMENDATION_MIN_VOLUME",
    5_000,
)

RECOMMENDATION_MIN_TXNS = _env_int(
    "RECOMMENDATION_MIN_TXNS",
    20,
)


# =========================================================
# WHALE / SMART MONEY
# =========================================================

WHALE_ANALYSIS_ENABLED = _env_bool(
    "WHALE_ANALYSIS_ENABLED",
    True,
)

SMART_MONEY_ENABLED = _env_bool(
    "SMART_MONEY_ENABLED",
    True,
)

WALLET_REPEAT_WINNER_TRACKING = _env_bool(
    "WALLET_REPEAT_WINNER_TRACKING",
    True,
)


# =========================================================
# GEM V9 INTELLIGENCE
# =========================================================

GEM_V9_ENABLED = _env_bool(
    "GEM_V9_ENABLED",
    True,
)

GEM_V9_CONFIRMATION_SCANS = _env_int(
    "GEM_V9_CONFIRMATION_SCANS",
    3,
)

GEM_V9_REQUIRE_CONFIRMATION_FOR_AUTO = _env_bool(
    "GEM_V9_REQUIRE_CONFIRMATION_FOR_AUTO",
    True,
)

GEM_V9_MIN_SCORE = _env_int(
    "GEM_V9_MIN_SCORE",
    70,
)

GEM_V9_MIN_CONFIDENCE = _env_int(
    "GEM_V9_MIN_CONFIDENCE",
    65,
)

GEM_V9_MAX_FALSE_SIGNAL_PENALTY = _env_int(
    "GEM_V9_MAX_FALSE_SIGNAL_PENALTY",
    24,
)


# =========================================================
# DEXSCREENER
# =========================================================

DEXSCREENER_ENABLED = _env_bool(
    "DEXSCREENER_ENABLED",
    True,
)

DEXSCREENER_CONNECT_TIMEOUT = _env_int(
    "DEXSCREENER_CONNECT_TIMEOUT",
    20,
)

DEXSCREENER_READ_TIMEOUT = _env_int(
    "DEXSCREENER_READ_TIMEOUT",
    40,
)

DEXSCREENER_MIN_REQUEST_INTERVAL = _env_float(
    "DEXSCREENER_MIN_REQUEST_INTERVAL",
    0.20,
)

DEXSCREENER_RETRIES = _env_int(
    "DEXSCREENER_RETRIES",
    3,
)


# =========================================================
# HTTP
# =========================================================

HTTP_TIMEOUT = _env_int(
    "HTTP_TIMEOUT",
    30,
)

HTTP_RETRIES = _env_int(
    "HTTP_RETRIES",
    3,
)


# =========================================================
# SOLANA RPC
# =========================================================
#
# Priority is handled by the security/scanner layer.
#
# FluxRPC is preferred when configured.
# Additional public RPCs remain available as fallbacks.
#
# The .env value always overrides these defaults.

SOLANA_RPC_URL = os.getenv(
    "SOLANA_RPC_URL",
    "https://api.mainnet-beta.solana.com",
).strip()

SOLANA_RPC_URL_2 = os.getenv(
    "SOLANA_RPC_URL_2",
    "https://solana-rpc.publicnode.com",
).strip()

SOLANA_RPC_URL_3 = os.getenv(
    "SOLANA_RPC_URL_3",
    "https://api.mainnet-beta.solana.com",
).strip()


# =========================================================
# BASE RPC
# =========================================================

BASE_RPC_URL = os.getenv(
    "BASE_RPC_URL",
    "https://mainnet.base.org",
).strip()

BASE_RPC_URL_2 = os.getenv(
    "BASE_RPC_URL_2",
    "https://base-rpc.publicnode.com",
).strip()


# =========================================================
# ROBINHOOD CHAIN RPC
# =========================================================

ROBINHOOD_RPC_URL = os.getenv(
    "ROBINHOOD_RPC_URL",
    "https://rpc.mainnet.chain.robinhood.com",
).strip()


# =========================================================
# ARC RPC
# =========================================================
#
# The user's working Arc URL in .env has priority.
# Do NOT overwrite it from this file.

ARC_RPC_URL = os.getenv(
    "ARC_RPC_URL",
    "https://rpc.mainnet.arc.io",
).strip()


# =========================================================
# BASE HONEYPOT
# =========================================================

BASE_HONEYPOT_ENABLED = _env_bool(
    "BASE_HONEYPOT_ENABLED",
    True,
)

BASE_HONEYPOT_REQUIRED = _env_bool(
    "BASE_HONEYPOT_REQUIRED",
    True,
)

BASE_HONEYPOT_TIMEOUT = float(
    os.getenv(
        "BASE_HONEYPOT_TIMEOUT",
        "15",
    )
)

BASE_HONEYPOT_CACHE_SECONDS = _env_int(
    "BASE_HONEYPOT_CACHE_SECONDS",
    300,
)


# =========================================================
# DEXSCREENER API
# =========================================================

DEXSCREENER_API = os.getenv(
    "DEXSCREENER_API",
    "https://api.dexscreener.com/latest/dex/search",
).strip()


# =========================================================
# ENVIRONMENT
# =========================================================

ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    "production",
).strip()

DEBUG = _env_bool(
    "DEBUG",
    False,
)


# =========================================================
# LOGGING
# =========================================================

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO",
).strip().upper()


# =========================================================
# BOT INFORMATION
# =========================================================

BOT_NAME = os.getenv(
    "BOT_NAME",
    "SALIM SAUKI DATA",
).strip()

ADMIN_USERNAME = os.getenv(
    "ADMIN_USERNAME",
    "",
).strip()

GROUP_USERNAME = os.getenv(
    "GROUP_USERNAME",
    "",
).strip()

CHANNEL_USERNAME = os.getenv(
    "CHANNEL_USERNAME",
    "",
).strip()


# =========================================================
# GROUP AUTO-CLEANUP
# =========================================================

# Optional separate cleanup bot.
CLEANUP_BOT_TOKEN = os.getenv(
    "CLEANUP_BOT_TOKEN",
    "",
).strip()

CLEANUP_CHAT_ID = os.getenv(
    "CLEANUP_CHAT_ID",
    "",
).strip()

CLEANUP_DELETE_AFTER_SECONDS = _env_int(
    "CLEANUP_DELETE_AFTER_SECONDS",
    300,
)

CLEANUP_CHECK_INTERVAL = _env_int(
    "CLEANUP_CHECK_INTERVAL",
    15,
)

CLEANUP_DATABASE_PATH = (
    os.getenv(
        "CLEANUP_DATABASE_PATH",
        "./cleanup_messages.db",
    ).strip()
    or "./cleanup_messages.db"
)


# =========================================================
# DEPLOYMENT / POLLING
# =========================================================
#
# These are used by the cloud-neutral bot architecture.
#
# Render:
#   Web service  -> TELEGRAM_POLLING_ENABLED=false
#   Worker       -> TELEGRAM_POLLING_ENABLED=true
#
# Local/Termux:
#   TELEGRAM_POLLING_ENABLED=true

TELEGRAM_POLLING_ENABLED = _env_bool(
    "TELEGRAM_POLLING_ENABLED",
    True,
)

CLEANUP_POLLING_ENABLED = _env_bool(
    "CLEANUP_POLLING_ENABLED",
    False,
)


# =========================================================
# OPTIONAL DEPLOYMENT PORT
# =========================================================

PORT = _env_int(
    "PORT",
    5000,
)


# =========================================================
# CONFIGURATION SUMMARY
# =========================================================

def configuration_summary():
    """
    Return a safe configuration summary.

    Secrets/API keys are intentionally NOT returned.
    """

    return {
        "environment": ENVIRONMENT,
        "auto_signal_enabled": AUTO_SIGNAL_ENABLED,
        "auto_signal_interval": AUTO_SIGNAL_INTERVAL,
        "auto_signal_min_score": AUTO_SIGNAL_MIN_SCORE,
        "auto_signal_min_recommendation": AUTO_SIGNAL_MIN_RECOMMENDATION,
        "auto_signal_require_security": AUTO_SIGNAL_REQUIRE_SECURITY,
        "auto_signal_min_security": AUTO_SIGNAL_MIN_SECURITY,
        "auto_signal_require_final_signal": AUTO_SIGNAL_REQUIRE_FINAL_SIGNAL,
        "auto_signal_max_per_scan": AUTO_SIGNAL_MAX_SIGNALS_PER_SCAN,
        "auto_signal_max_per_chain": AUTO_SIGNAL_MAX_SIGNALS_PER_CHAIN,
        "marketcap_min": MIN_MARKETCAP,
        "marketcap_max": MAX_MARKETCAP,
        "final_marketcap_min": FINAL_MIN_MARKET_CAP,
        "final_marketcap_max": FINAL_MAX_MARKET_CAP,
        "solana_rpc_configured": bool(SOLANA_RPC_URL),
        "solana_rpc_2_configured": bool(SOLANA_RPC_URL_2),
        "solana_rpc_3_configured": bool(SOLANA_RPC_URL_3),
        "fluxrpc_configured": bool(
            FLUXRPC_RPC_URL or FLUXRPC_API_KEY
        ),
        "base_rpc_configured": bool(BASE_RPC_URL),
        "base_rpc_2_configured": bool(BASE_RPC_URL_2),
        "robinhood_rpc_configured": bool(
            ROBINHOOD_RPC_URL
        ),
        "arc_rpc_configured": bool(
            ARC_RPC_URL
        ),
        "helius_configured": bool(
            HELIUS_API_KEY
        ),
        "birdeye_configured": bool(
            BIRDEYE_API_KEY
        ),
        "telegram_configured": bool(
            BOT_TOKEN
        ),
        "auto_signal_chat_configured": bool(
            AUTO_SIGNAL_CHAT_ID
        ),
        "telegram_polling_enabled": TELEGRAM_POLLING_ENABLED,
        "cleanup_polling_enabled": CLEANUP_POLLING_ENABLED,
    }
