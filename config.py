import os

from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT
# =========================================================

load_dotenv()


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
)


# =========================================================
# AUTO SIGNAL SETTINGS
# =========================================================

AUTO_SIGNAL_ENABLED = os.getenv(
    "AUTO_SIGNAL_ENABLED",
    "true",
).lower() == "true"

AUTO_SIGNAL_INTERVAL = int(
    os.getenv(
        "AUTO_SIGNAL_INTERVAL",
        "60",
    )
)

AUTO_SIGNAL_MIN_SCORE = int(
    os.getenv(
        "AUTO_SIGNAL_MIN_SCORE",
        "75",
    )
)

AUTO_SIGNAL_MIN_RECOMMENDATION = int(
    os.getenv(
        "AUTO_SIGNAL_MIN_RECOMMENDATION",
        "75",
    )
)

AUTO_SIGNAL_REQUIRE_SECURITY = os.getenv(
    "AUTO_SIGNAL_REQUIRE_SECURITY",
    "true",
).lower() == "true"

AUTO_SIGNAL_MIN_SECURITY = int(
    os.getenv(
        "AUTO_SIGNAL_MIN_SECURITY",
        "90",
    )
)

AUTO_SIGNAL_REQUIRE_FINAL_SIGNAL = os.getenv(
    "AUTO_SIGNAL_REQUIRE_FINAL_SIGNAL",
    "true",
).lower() == "true"


# =========================================================
# SCANNER SETTINGS
# =========================================================

SCAN_INTERVAL = int(
    os.getenv(
        "SCAN_INTERVAL",
        "60",
    )
)

MAX_RESULTS = int(
    os.getenv(
        "MAX_RESULTS",
        "10",
    )
)

MIN_MARKETCAP = float(
    os.getenv(
        "MIN_MARKETCAP",
        "10000",
    )
)

MAX_MARKETCAP = float(
    os.getenv(
        "MAX_MARKETCAP",
        "5000000",
    )
)

MIN_LIQUIDITY = float(
    os.getenv(
        "MIN_LIQUIDITY",
        "10000",
    )
)

MIN_VOLUME_24H = float(
    os.getenv(
        "MIN_VOLUME_24H",
        "5000",
    )
)

MIN_TXNS = int(
    os.getenv(
        "MIN_TXNS",
        "20",
    )
)

MIN_BUY_RATIO = float(
    os.getenv(
        "MIN_BUY_RATIO",
        "0.50",
    )
)


# =========================================================
# GEM DETECTION
# =========================================================

MIN_GEM_SCORE = int(
    os.getenv(
        "MIN_GEM_SCORE",
        "70",
    )
)

STRONG_GEM_SCORE = int(
    os.getenv(
        "STRONG_GEM_SCORE",
        "80",
    )
)

EARLY_GEM_SCORE = int(
    os.getenv(
        "EARLY_GEM_SCORE",
        "60",
    )
)

WATCH_SCORE = int(
    os.getenv(
        "WATCH_SCORE",
        "50",
    )
)

MIN_GEM_SIGNAL = int(
    os.getenv(
        "MIN_GEM_SIGNAL",
        "70",
    )
)

MIN_STRONG_GEM = int(
    os.getenv(
        "MIN_STRONG_GEM",
        "75",
    )
)


# =========================================================
# AI SCORING
# =========================================================

MIN_AI_SIGNAL = int(
    os.getenv(
        "MIN_AI_SIGNAL",
        "65",
    )
)

AI_STRONG_BUY_SCORE = int(
    os.getenv(
        "AI_STRONG_BUY_SCORE",
        "85",
    )
)

AI_BUY_SCORE = int(
    os.getenv(
        "AI_BUY_SCORE",
        "75",
    )
)

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
        "80",
    )
)

AUTO_SIGNAL_MIN_SECURITY = int(
    os.getenv(
        "AUTO_SIGNAL_MIN_SECURITY",
        "90",
    )
)

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
        "20000",
    )
)

FINAL_MIN_MARKET_CAP = float(
    os.getenv(
        "FINAL_MIN_MARKET_CAP",
        "30000",
    )
)

FINAL_MAX_MARKET_CAP = float(
    os.getenv(
        "FINAL_MAX_MARKET_CAP",
        "5000000",
    )
)

FINAL_MIN_BUY_RATIO = float(
    os.getenv(
        "FINAL_MIN_BUY_RATIO",
        "0.55",
    )
)

FINAL_MIN_VOLUME_RATIO = float(
    os.getenv(
        "FINAL_MIN_VOLUME_RATIO",
        "0.05",
    )
)

FINAL_MIN_TXNS = int(
    os.getenv(
        "FINAL_MIN_TXNS",
        "50",
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
        "85",
    )
)

RECOMMENDATION_BUY = int(
    os.getenv(
        "RECOMMENDATION_BUY",
        "75",
    )
)

RECOMMENDATION_WATCH = int(
    os.getenv(
        "RECOMMENDATION_WATCH",
        "60",
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
        "90",
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
# DATABASE
# =========================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./salim_sauki_data.db",
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
