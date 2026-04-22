import os
import threading
import time
import requests
from flask import Flask

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def get_updates(offset=None):
    return requests.get(
        BASE_URL + "/getUpdates",
        params={"timeout": 100, "offset": offset}
    ).json()

def send(chat_id, text):
    requests.post(BASE_URL + "/sendMessage", data={"chat_id": chat_id, "text": text})

def bot_loop():
    offset = None
    print("Telegram bot started...")

    while True:
        try:
            updates = get_updates(offset)

            if "result" in updates:
                for u in updates["result"]:
                    offset = u["update_id"] + 1

                    if "message" not in u:
                        continue

                    chat_id = u["message"]["chat"]["id"]
                    text = u["message"].get("text", "")

                    send(chat_id, f"You sent: {text}")

        except Exception as e:
            print("Bot error:", e)

        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=bot_loop, daemon=True).start()

    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
