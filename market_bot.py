import os
import threading
import time
import requests
import re
from flask import Flask

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

@app.route("/")
def home():
    return "Trading Bot Running!"

pairs = {
    "EURUSD": ("EUR", "USD"),
    "USDJPY": ("USD", "JPY"),
    "NZDUSD": ("NZD", "USD"),
    "GBPJPY": ("GBP", "JPY"),
}

trade = {}
alerts = []

# ---------- TELEGRAM ----------
def get_updates(offset=None):
    return requests.get(
        BASE_URL + "/getUpdates",
        params={"timeout": 100, "offset": offset}
    ).json()

def send(chat_id, text):
    requests.post(BASE_URL + "/sendMessage", data={
        "chat_id": chat_id,
        "text": text
    })

# ---------- PRICE ----------
def forex_price(frm, to):
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={frm}&to_currency={to}&apikey={API_KEY}"
    data = requests.get(url).json()
    return float(data["Realtime Currency Exchange Rate"]["5. Exchange Rate"])

def btc_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    return float(requests.get(url).json()["price"])

def get_price(pair):
    if pair == "BTCUSD":
        return btc_price()

    if pair in pairs:
        frm, to = pairs[pair]
        return forex_price(frm, to)

    return None

# ---------- ALERTS ----------
def check_alerts():
    global alerts

    triggered = []

    for alert in alerts:
        current = get_price(alert["pair"])

        if current is None:
            continue

        hit = False

        if alert["direction"] == "above" and current >= alert["target"]:
            hit = True

        if alert["direction"] == "below" and current <= alert["target"]:
            hit = True

        if hit:
            send(
                alert["chat_id"],
                f"🚨 {alert['pair']} reached {alert['target']}\nCurrent: {current}"
            )
            triggered.append(alert)

    for item in triggered:
        alerts.remove(item)

# ---------- MAIN LOOP ----------
def bot_loop():
    offset = None
    print("Trading bot started...")

    while True:
        try:
            updates = get_updates(offset)

            if "result" in updates:
                for u in updates["result"]:
                    offset = u["update_id"] + 1

                    if "message" not in u:
                        continue

                    chat_id = u["message"]["chat"]["id"]
                    text = u["message"].get("text", "").upper().strip()

                    # ----- SET ALERT -----
                    if text.startswith("ALERT"):
                        parts = text.split()

                        if len(parts) == 3:
                            pair = parts[1]
                            target = float(parts[2])

                            current = get_price(pair)

                            if current is None:
                                send(chat_id, "❌ Invalid pair")
                                continue

                            direction = "above" if target > current else "below"

                            alerts.append({
                                "chat_id": chat_id,
                                "pair": pair,
                                "target": target,
                                "direction": direction
                            })

                            send(
                                chat_id,
                                f"✅ Alert set for {pair} at {target}"
                            )
                            continue

                    # ----- VIEW ALERTS -----
                    if text == "ALERTS":
                        if not alerts:
                            send(chat_id, "No active alerts.")
                        else:
                            msg = "📌 Active Alerts:\n"
                            for a in alerts:
                                if a["chat_id"] == chat_id:
                                    msg += f"{a['pair']} @ {a['target']}\n"
                            send(chat_id, msg)
                        continue

                    # ----- CLEAR ALERTS -----
                    if text == "CLEAR ALERTS":
                        alerts = [a for a in alerts if a["chat_id"] != chat_id]
                        send(chat_id, "🗑 Alerts cleared.")
                        continue

                    # ----- PRICE CHECK -----
                    price = get_price(text)

                    if price:
                        send(chat_id, f"📊 {text}\n💰 Price: {price}")
                        continue

                    send(chat_id, "Send:\nEURUSD\nALERT EURUSD 1.0900")

            check_alerts()

        except Exception as e:
            print("Error:", e)

        time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=bot_loop, daemon=True).start()

    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
