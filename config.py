import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Не задан TELEGRAM_BOT_TOKEN в .env")

GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))
MESSAGE_THREAD_ID = int(os.getenv("MESSAGE_THREAD_ID", "2"))
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "60"))
DB_PATH = "tasks_state.db"
ATASH_TOKEN_PATH = "Atash_token.json"
MOLDIR_TOKEN_PATH = "Moldir_token.json"
CREDENTIALS_PATH = "credentials.json"
