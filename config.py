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
PERSON1_TOKEN_PATH = "Person1_token.json"
PERSON2_TOKEN_PATH = "Person2_token.json"
CREDENTIALS_PATH = "credentials.json"
