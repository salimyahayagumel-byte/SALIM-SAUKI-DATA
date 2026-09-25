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
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return int(default)


def _env_float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return float(default)


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./salim_sauki_data.db",
).strip() or "sqlite:///./salim_sauki_data.db"


# =========================================================
# TELEGRAM BOT
# =========================================================

BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    "",
)


# =========================================================
# TELEGRAM CHAT IDs
# =========================================================

ADMIN_ID = os.getenv(
    "ADMIN_ID",
    "",
)

GROUP_ID = os.getenv(
    "GROUP_ID",
    "",
)

AUTO_SIGNAL_CHAT_ID = os.getenv(
    "AUTO_SIGNAL_CHAT_ID",
    GROUP_ID,
)


# =========================================================
# APIs
# =========================================================

BIRDEYE_API_KEY = os.getenv(
    "BIRDEYE_API_KEY",
    "",
)

RUGCHECK_API_KEY = os.getenv(
    "RUGCHECK_API_KEY",
    "",
)

HELIUS_API_KEY = os.getenv(
    "HELIUS_API_KEY",
    "",
)

FLUXRPC_API_KEY = os.getenv(
    "FLUXRPC_API_KEY",
    "",
).strip()


# FluxRPC Solana endpoint.
# If FLUXRPC_RPC_URL is not supplied, build the official endpoint
# from FLUXRPC_API_KEY without exposing the key in logs.
FLUXRPC_RPC_URL = os.getenv(
    "FLUXRPC_RPC_URL",
    "",
).strip()

if not FLUXRPC_RPC_URL and FLUXRPC_API_KEY:
    FLUXRPC_RPC_URL = (
        "https://cdn.fluxrpc.com"
        f"?key={FLUXRPC_API_KEY}"
    )


# =========================================================
# AUTO SIGNAL SETTINGS
# =========================================================

AUTO_SIGNAL_ENABLED = _env_bool("AUTO_SIGNAL_ENABLED", True)

AUTO_SIGNAL_INTERVAL = _env_int("AUTO_SIGNAL_INTERVAL", 60)

AUTO_SIGNAL_MIN_SCORE = _env_int("AUTO_SIGNAL_MIN_SCORE", 65)

AUTO_SIGNAL_MIN_RECOMMENDATION = _env_int("AUTO_SIGNAL_MIN_RECOMMENDATION", 65)

AUTO_SIGNAL_REQUIRE_SECURITY = _env_bool("AUTO_SIGNAL_REQUIRE_SECURITY", True)

AUTO_SIGNAL_MIN_SECURITY = _env_int("AUTO_SIGNAL_MIN_SECURITY", 69)

AUTO_SIGNAL_REQUIRE_FINAL_SIGNAL = _env_bool("AUTO_SIGNAL_REQUIRE_FINAL_SIGNAL", True)

AUTO_SIGNAL_MAX_SIGNALS_PER_SCAN = _env_int("AUTO_SIGNAL_MAX_SIGNALS_PER_SCAN", 8)

AUTO_SIGNAL_MAX_SIGNALS_PER_CHAIN = _env_int("AUTO_SIGNAL_MAX_SIGNALS_PER_CHAIN", 2)


# =========================================================
# PNL TRACKER
# =========================================================

PNL_TRACKER_ENABLED = _env_bool("PNL_TRACKER_ENABLED", True)
PNL_TRACKER_INTERVAL = _env_int("PNL_TRACKER_INTERVAL", 60)
PNL_TRACKER_MAX_TRACKED = _env_int("PNL_TRACKER_MAX_TRACKED", 500)
PNL_TRACKER_DRAWDOWN_ALERT = _env_int("PNL_TRACKER_DRAWDOWN_ALERT", 20)


# =========================================================
# SCANNER SETTINGS
# =========================================================

SCAN_INTERVAL = _env_int("SCAN_INTERVAL", 60)

MAX_RESULTS = _env_int("MAX_RESULTS", 10)

MIN_MARKETCAP = _env_float("MIN_MARKETCAP", 10000)

MAX_MARKETCAP = _env_float("MAX_MARKETCAP", 1000000)

MIN_LIQUIDITY = _env_float("MIN_LIQUIDITY", 10000)

MIN_VOLUME_24H = _env_float("MIN_VOLUME_24H", 5000)

MIN_TXNS = _env_int("MIN_TXNS", 20)

MIN_BUY_RATIO = float(
    os.getenv(
        "MIN_BUY_RATIO",
        "0.50",
    )
)


# =========================================================
# GEM DETECTION
# =========================================================

MIN_GEM_SCORE = _env_int("MIN_GEM_SCORE", 70)

STRONG_GEM_SCORE = _env_int("STRONG_GEM_SCORE", 80)

EARLY_GEM_SCORE = _env_int("EARLY_GEM_SCORE", 60)

WATCH_SCORE = _env_int("WATCH_SCORE", 50)

MIN_GEM_SIGNAL = _env_int("MIN_GEM_SIGNAL", 65)

MIN_STRONG_GEM = _env_int("MIN_STRONG_GEM", 72)


# =========================================================
# AI SCORING
# =========================================================

MIN_AI_SIGNAL = _env_int("MIN_AI_SIGNAL", 60)

AI_STRONG_BUY_SCORE = _env_int("AI_STRONG_BUY_SCORE", 85)

AI_BUY_SCORE = _env_int("AI_BUY_SCORE", 75)

AI_WATCH_SCORE = int(
    os.getenv(
        "AI_WATCH_SCORE",
        "65",
    )
)


# =========================================================
# SECURITY
# =========================================================

MIN_SECURITY_SCORE = int(
    os.getenv(
        "MIN_SECURITY_SCORE",
        "69",
    )
)

AUTO_SIGNAL_MIN_SECURITY = _env_int("AUTO_SIGNAL_MIN_SECURITY", 69)

REQUIRE_MINT_AUTHORITY_DISABLED = os.getenv(
    "REQUIRE_MINT_AUTHORITY_DISABLED",
    "true",
).lower() == "true"

REQUIRE_FREEZE_AUTHORITY_DISABLED = os.getenv(
    "REQUIRE_FREEZE_AUTHORITY_DISABLED",
    "true",
).lower() == "true"

REQUIRE_INITIALIZED = os.getenv(
    "REQUIRE_INITIALIZED",
    "true",
).lower() == "true"


# =========================================================
# LIQUIDITY / VOLUME SAFETY
# =========================================================

FINAL_MIN_LIQUIDITY = float(
    os.getenv(
        "FINAL_MIN_LIQUIDITY",
        "10000",
    )
)

FINAL_MIN_MARKET_CAP = float(
    os.getenv(
        "FINAL_MIN_MARKET_CAP",
        "10000",
    )
)

FINAL_MAX_MARKET_CAP = float(
    os.getenv(
        "FINAL_MAX_MARKET_CAP",
        "1000000",
    )
)

FINAL_MIN_BUY_RATIO = float(
    os.getenv(
        "FINAL_MIN_BUY_RATIO",
        "0.50",
    )
)

FINAL_MIN_VOLUME_RATIO = float(
    os.getenv(
        "FINAL_MIN_VOLUME_RATIO",
        "0.03",
    )
)

FINAL_MIN_TXNS = int(
    os.getenv(
        "FINAL_MIN_TXNS",
        "20",
    )
)

MAX_SAFE_VOLUME_RATIO = float(
    os.getenv(
        "MAX_SAFE_VOLUME_RATIO",
        "15",
    )
)

EXTREME_VOLUME_RATIO = float(
    os.getenv(
        "EXTREME_VOLUME_RATIO",
        "25",
    )
)


# =========================================================
# RECOMMENDATION ENGINE
# =========================================================

RECOMMENDATION_STRONG_BUY = int(
    os.getenv(
        "RECOMMENDATION_STRONG_BUY",
        "80",
    )
)

RECOMMENDATION_BUY = int(
    os.getenv(
        "RECOMMENDATION_BUY",
        "65",
    )
)

RECOMMENDATION_WATCH = int(
    os.getenv(
        "RECOMMENDATION_WATCH",
        "55",
    )
)

RECOMMENDATION_HIGH_RISK = int(
    os.getenv(
        "RECOMMENDATION_HIGH_RISK",
        "45",
    )
)

RECOMMENDATION_MIN_SECURITY = int(
    os.getenv(
        "RECOMMENDATION_MIN_SECURITY",
        "70",
    )
)

RECOMMENDATION_MIN_LIQUIDITY = float(
    os.getenv(
        "RECOMMENDATION_MIN_LIQUIDITY",
        "10000",
    )
)

RECOMMENDATION_MIN_VOLUME = float(
    os.getenv(
        "RECOMMENDATION_MIN_VOLUME",
        "5000",
    )
)

RECOMMENDATION_MIN_TXNS = int(
    os.getenv(
        "RECOMMENDATION_MIN_TXNS",
        "20",
    )
)


# =========================================================
# WHALE / SMART MONEY
# =========================================================

WHALE_ANALYSIS_ENABLED = os.getenv(
    "WHALE_ANALYSIS_ENABLED",
    "true",
).lower() == "true"

SMART_MONEY_ENABLED = os.getenv(
    "SMART_MONEY_ENABLED",
    "true",
).lower() == "true"

WALLET_REPEAT_WINNER_TRACKING = os.getenv(
    "WALLET_REPEAT_WINNER_TRACKING",
    "true",
).lower() == "true"


# =========================================================
# V9 GEM INTELLIGENCE
# =========================================================

GEM_V9_ENABLED = _env_bool("GEM_V9_ENABLED", True)
GEM_V9_CONFIRMATION_SCANS = _env_int("GEM_V9_CONFIRMATION_SCANS", 3)
GEM_V9_REQUIRE_CONFIRMATION_FOR_AUTO = _env_bool(
    "GEM_V9_REQUIRE_CONFIRMATION_FOR_AUTO",
    True,
)
GEM_V9_MIN_SCORE = _env_int("GEM_V9_MIN_SCORE", 70)
GEM_V9_MIN_CONFIDENCE = _env_int("GEM_V9_MIN_CONFIDENCE", 65)
GEM_V9_MAX_FALSE_SIGNAL_PENALTY = _env_int(
    "GEM_V9_MAX_FALSE_SIGNAL_PENALTY",
    24,
)

# =========================================================
# HTTP
# =========================================================

HTTP_TIMEOUT = int(
    os.getenv(
        "HTTP_TIMEOUT",
        "30",
    )
)

HTTP_RETRIES = int(
    os.getenv(
        "HTTP_RETRIES",
        "3",
    )
)


# =========================================================
# BOT INFORMATION
# =========================================================

BOT_NAME = os.getenv(
    "BOT_NAME",
    "SALIM SAUKI DATA",
)

ADMIN_USERNAME = os.getenv(
    "ADMIN_USERNAME",
    "",
)

GROUP_USERNAME = os.getenv(
    "GROUP_USERNAME",
    "",
)

CHANNEL_USERNAME = os.getenv(
    "CHANNEL_USERNAME",
    "",
)


# =========================================================
# SOLANA RPC
# =========================================================

SOLANA_RPC_URL = os.getenv(
    "SOLANA_RPC_URL",
    "https://api.mainnet-beta.solana.com",
)

SOLANA_RPC_URL_2 = os.getenv(
    "SOLANA_RPC_URL_2",
    "https://solana-rpc.publicnode.com",
)

SOLANA_RPC_URL_3 = os.getenv(
    "SOLANA_RPC_URL_3",
    "https://api.mainnet-beta.solana.com",
)


# =========================================================
# BASE / EVM SECURITY
# Additional EVM chains supported by the scanner.
ROBINHOOD_RPC_URL = os.getenv(
    "ROBINHOOD_RPC_URL",
    "https://rpc.mainnet.chain.robinhood.com",
)
ARC_RPC_URL = os.getenv(
    "ARC_RPC_URL",
    "https://rpc.mainnet.arc.io",
)

# =========================================================

BASE_RPC_URL = os.getenv(
    "BASE_RPC_URL",
    "https://mainnet.base.org",
)

BASE_RPC_URL_2 = os.getenv(
    "BASE_RPC_URL_2",
    "https://base-rpc.publicnode.com",
)

BASE_HONEYPOT_ENABLED = os.getenv(
    "BASE_HONEYPOT_ENABLED",
    "true",
).lower() == "true"

BASE_HONEYPOT_REQUIRED = os.getenv(
    "BASE_HONEYPOT_REQUIRED",
    "true",
).lower() == "true"

BASE_HONEYPOT_TIMEOUT = float(
    os.getenv(
        "BASE_HONEYPOT_TIMEOUT",
        "15",
    )
)

BASE_HONEYPOT_CACHE_SECONDS = int(
    os.getenv(
        "BASE_HONEYPOT_CACHE_SECONDS",
        "300",
    )
)


# =========================================================
# DEXSCREENER
# =========================================================

DEXSCREENER_API = os.getenv(
    "DEXSCREENER_API",
    "https://api.dexscreener.com/latest/dex/search",
)


# =========================================================
# ENVIRONMENT
# =========================================================

ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    "production",
)

DEBUG = os.getenv(
    "DEBUG",
    "false",
).lower() == "true"


# =========================================================
# LOGGING
# =========================================================

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO",
)


# =========================================================
# GROUP AUTO-CLEANUP BOT
# =========================================================

# Separate Telegram bot token used only for group cleanup.
CLEANUP_BOT_TOKEN = os.getenv(
    "CLEANUP_BOT_TOKEN",
    "",
).strip()

# Group/supergroup chat ID whose messages should be deleted.
# Keep this set to one specific group to avoid accidental deletion elsewhere.
CLEANUP_CHAT_ID = os.getenv(
    "CLEANUP_CHAT_ID",
    "",
).strip()

# 300 seconds = 5 minutes.
CLEANUP_DELETE_AFTER_SECONDS = _env_int(
    "CLEANUP_DELETE_AFTER_SECONDS",
    300,
)

CLEANUP_CHECK_INTERVAL = _env_int(
    "CLEANUP_CHECK_INTERVAL",
    15,
)

CLEANUP_DATABASE_PATH = os.getenv(
    "CLEANUP_DATABASE_PATH",
    "./cleanup_messages.db",
).strip() or "./cleanup_messages.db"
