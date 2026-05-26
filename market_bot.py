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
    return "Trading Bot Running!"

# ---------- PAIRS ----------
pairs = {
    "EURUSD": ("EUR", "USD"),
    "GBPUSD": ("GBP", "USD"),
    "USDJPY": ("USD", "JPY"),
    "USDCHF": ("USD", "CHF"),
    "USDCAD": ("USD", "CAD"),
    "AUDUSD": ("AUD", "USD"),
    "NZDUSD": ("NZD", "USD"),

    "EURJPY": ("EUR", "JPY"),
    "GBPJPY": ("GBP", "JPY"),
    "EURGBP": ("EUR", "GBP"),
    "EURAUD": ("EUR", "AUD"),
    "EURCAD": ("EUR", "CAD"),
    "GBPAUD": ("GBP", "AUD"),
    "AUDJPY": ("AUD", "JPY"),
    "CADJPY": ("CAD", "JPY"),
    "NZDJPY": ("NZD", "JPY"),
}

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
    try:
        url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={frm}&to_currency={to}&apikey={API_KEY}"
        data = requests.get(url, timeout=10).json()
        rate = data["Realtime Currency Exchange Rate"]["5. Exchange Rate"]
        return float(rate)
    except Exception as e:
        print("FX error:", e)
        return None

def btc_price():
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        return float(requests.get(url, timeout=10).json()["price"])
    except Exception as e:
        print("BTC error:", e)
        return None

def eth_price():
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT"
        return float(requests.get(url, timeout=10).json()["price"])
    except Exception as e:
        print("ETH error:", e)
        return None

def get_price(pair):
    if pair == "BTCUSD":
        return btc_price()

    if pair == "ETHUSD":
        return eth_price()

    if pair in pairs:
        frm, to = pairs[pair]
        return forex_price(frm, to)

    return None

# ---------- MARKET DASHBOARD ----------
def market_dashboard():
    watchlist = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "EURJPY", "GBPJPY", "BTCUSD", "ETHUSD"]

    msg = "📊 MARKET DASHBOARD\n\n"

    for p in watchlist:
        price = get_price(p)
        if price:
            msg += f"{p}: {price}\n"
        else:
            msg += f"{p}: N/A\n"

    return msg

# ---------- BOT LOOP ----------
def bot_loop():
    offset = None
    print("Trading bot running...")

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

                    # ---------- MARKET DASHBOARD ----------
                    if text == "MARKET":
                        send(chat_id, market_dashboard())
                        continue

                    # ---------- PRICE CHECK ----------
                    price = get_price(text)

                    if price:
                        send(chat_id, f"📊 {text}\n💰 Price: {price}")
                    else:
                        send(chat_id, "Commands:\nMARKET\nEURUSD\nGBPJPY\nBTCUSD")

        except Exception as e:
            print("Bot error:", e)

        time.sleep(3)

# ---------- START ----------
if __name__ == "__main__":
    threading.Thread(target=bot_loop, daemon=True).start()

    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
