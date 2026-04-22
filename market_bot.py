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

# ---------- WEB SERVER ----------
@app.route("/")
def home():
    return "Trading Bot Running!"

# ---------- PAIRS ----------
pairs = {
    "EURUSD": ("EUR", "USD"),
    "USDJPY": ("USD", "JPY"),
    "NZDUSD": ("NZD", "USD"),
    "GBPJPY": ("GBP", "JPY"),
}

trade = {}

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

# ---------- PARSE TRADE ----------
def parse_trade(text):
    pattern = r"(BUY|SELL)\s+([A-Z]{6})\s+([\d\.]+)\s+TP\s+([\d\.]+)\s+SL\s+([\d\.]+)"
    match = re.match(pattern, text)

    if not match:
        return None

    return {
        "type": match.group(1),
        "pair": match.group(2),
        "entry": float(match.group(3)),
        "tp": float(match.group(4)),
        "sl": float(match.group(5)),
    }

# ---------- ANALYZE ----------
def analyze(tr, current):
    entry = tr["entry"]
    tp = tr["tp"]
    sl = tr["sl"]

    if tr["type"] == "BUY":
        profit = current - entry
        tp_total = tp - entry
    else:
        profit = entry - current
        tp_total = entry - tp

    pips = profit * 10000
    progress = (profit / tp_total * 100) if tp_total != 0 else 0

    status = "Neutral"
    if profit > 0:
        status = "In Profit 📈"
    if progress >= 100:
        status = "TP HIT 🎯"

    if tr["type"] == "BUY" and current <= sl:
        status = "SL HIT 🛑"

    if tr["type"] == "SELL" and current >= sl:
        status = "SL HIT 🛑"

    return pips, progress, status

# ---------- BOT LOOP ----------
def bot_loop():
    global trade
    offset = None

    print("Telegram trading bot started...")

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

                    # SAVE TRADE
                    parsed = parse_trade(text)
                    if parsed:
                        trade = parsed
                        send(chat_id, f"✅ Trade saved: {parsed['pair']} {parsed['type']}")
                        continue

                    # BTC
                    if text == "BTCUSD":
                        price = btc_price()
                        send(chat_id, f"📊 BTCUSD\n💰 Price: {price}")
                        continue

                    # FOREX PAIRS
                    if text in pairs:
                        frm, to = pairs[text]
                        current = forex_price(frm, to)

                        if trade and trade["pair"] == text:
                            pips, prog, status = analyze(trade, current)

                            msg = f"""📊 {text} {trade['type']}

Entry: {trade['entry']}
Current: {current}

💰 Profit: {pips:.1f} pips
🎯 TP Progress: {prog:.1f}%

Status: {status}"""
                        else:
                            msg = f"""📊 {text}
💰 Price: {current}"""

                        send(chat_id, msg)
                        continue

                    send(chat_id, "Send pair (EURUSD) or trade:\nBUY EURUSD 1.0850 TP 1.0900 SL 1.0800")

        except Exception as e:
            print("Error:", e)

        time.sleep(1)

# ---------- START ----------
if __name__ == "__main__":
    threading.Thread(target=bot_loop, daemon=True).start()

    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
