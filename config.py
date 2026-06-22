import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")

# Parse comma-separated admin IDs
_admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = []
if _admin_ids_str:
    try:
        ADMIN_IDS = [int(id_str.strip()) for id_str in _admin_ids_str.split(",") if id_str.strip()]
    except ValueError:
        print("Warning: ADMIN_IDS contains invalid integer values.")

import json

# --- QUEST CONFIGURATION ---

# Load quests configuration from JSON file
try:
    with open("quests.json", "r", encoding="utf-8") as f:
        QUESTS_DATA = json.load(f)
except FileNotFoundError:
    print("Warning: quests.json not found. Using empty config.")
    QUESTS_DATA = {}
