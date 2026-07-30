from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# ==========================
# Telegram
# ==========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = os.getenv("ADMIN_ID", "")
GROUP_ID = os.getenv("GROUP_ID", "")

# ==========================
# API Keys
# ==========================
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY", "")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
FLUXRPC_API_KEY = os.getenv("FLUXRPC_API_KEY", "")

# ==========================
# Database
# ==========================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///salim_sauki_data.db"
)

# ==========================
# Logging
# ==========================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
