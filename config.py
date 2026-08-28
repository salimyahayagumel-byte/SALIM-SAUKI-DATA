import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# APIs
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY", "")
RUGCHECK_API_KEY = os.getenv("RUGCHECK_API_KEY", "")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
FLUXRPC_API_KEY = os.getenv("FLUXRPC_API_KEY", "")

# Telegram IDs
ADMIN_ID = os.getenv("ADMIN_ID", "")
GROUP_ID = os.getenv("GROUP_ID", "")
