import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHAT_ID = int(os.getenv("CHAT_ID", "0"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID не задан")
if not CHAT_ID:
    raise ValueError("CHAT_ID не задан")