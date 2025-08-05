import os
import yaml

CHAT_HISTORY_PATH = os.path.join("config", "chat_history.yaml")

def load_chat_history():
    if not os.path.exists(CHAT_HISTORY_PATH):
        return []

    with open(CHAT_HISTORY_PATH, "r") as f:
        data = yaml.safe_load(f) or {}
        return data.get("chats", [])

def save_chat_history(chats):
    os.makedirs(os.path.dirname(CHAT_HISTORY_PATH), exist_ok=True)
    with open(CHAT_HISTORY_PATH, "w") as f:
        yaml.safe_dump({"chats": chats}, f)
