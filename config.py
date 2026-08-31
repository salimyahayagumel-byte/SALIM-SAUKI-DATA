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

AUTO_SIGNAL_MIN_SECURITY = int(
    os.getenv(
        "AUTO_SIGNAL_MIN_SECURITY",
        "90",
    )
)


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
    "DEX ANALYSIS BOT",
)

ADMIN_USERNAME = os.getenv(
    "ADMIN_USERNAME",
    "",
)

GROUP_USERNAME = os.getenv(
    "GROUP_USERNAME",
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
