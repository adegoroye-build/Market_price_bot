import requests
import time
import re

BOT_TOKEN = "8782771956:AAFUVrFz7vUMhMNvYI5ax1keLcPhsriZ2VU"
API_KEY = "7WCZVEJHOHDK86QM"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

pairs = {
    "EURUSD": ("EUR", "USD"),
    "USDJPY": ("USD", "JPY"),
    "NZDUSD": ("NZD", "USD"),
    "GBPJPY": ("GBP", "JPY"),
}

# STORE ONE ACTIVE TRADE (simple version)
trade = {}

# ---------- PRICE ----------


def price(frm, to):
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={frm}&to_currency={to}&apikey={API_KEY}"
    data = requests.get(url).json()
    return float(data["Realtime Currency Exchange Rate"]["5. Exchange Rate"])

# ---------- TELEGRAM ----------


def get_updates(offset=None):
    return requests.get(
        BASE_URL + "/getUpdates",
        params={"timeout": 100, "offset": offset}
    ).json()


def send(chat_id, text):
    requests.post(BASE_URL + "/sendMessage",
                  data={"chat_id": chat_id, "text": text})

# ---------- PARSE TRADE ----------


def parse_trade(text):
    # BUY EURUSD 1.0850 TP 1.0900 SL 1.0800
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

# ---------- TRADE STATUS ----------


def analyze(trade_data, current):
    entry = trade_data["entry"]
    tp = trade_data["tp"]
    sl = trade_data["sl"]

    direction = trade_data["type"]

    if direction == "BUY":
        profit = (current - entry)
        tp_dist = tp - entry
        sl_dist = entry - sl
    else:
        profit = (entry - current)
        tp_dist = entry - tp
        sl_dist = sl - entry

    profit_pips = profit * 10000

    tp_progress = (profit / tp_dist * 100) if tp_dist != 0 else 0

    status = "Neutral"
    if profit > 0:
        status = "In Profit 📈"
    if (direction == "BUY" and current >= tp) or (direction == "SELL" and current <= tp):
        status = "TP HIT 🎯"
    if (direction == "BUY" and current <= sl) or (direction == "SELL" and current >= sl):
        status = "SL HIT 🛑"

    return profit_pips, tp_progress, status

# ---------- LOOP ----------


def run():
    global trade
    offset = None

    print("Trade Bot Running...")

    while True:
        updates = get_updates(offset)

        if "result" in updates:
            for u in updates["result"]:
                offset = u["update_id"] + 1

                if "message" not in u:
                    continue

                chat_id = u["message"]["chat"]["id"]
                text = u["message"].get("text", "").upper().strip()

                try:

                    # SAVE TRADE
                    parsed = parse_trade(text)
                    if parsed:
                        trade = parsed
                        send(
                            chat_id, f"Trade saved: {parsed['pair']} {parsed['type']}")
                        continue

                    # CHECK STATUS
                    if text in pairs and trade and trade["pair"] == text:
                        frm, to = pairs[text]
                        current = price(frm, to)

                        profit, tp_prog, status = analyze(trade, current)

                        msg = f"""📊 {text} {trade['type']}

Entry: {trade['entry']}
Current: {current}

💰 Profit: {profit:.1f} pips
🎯 TP Progress: {tp_prog:.1f}%
🛑 SL: {trade['sl']}

Status: {status}"""

                        send(chat_id, msg)

                    else:
                        send(
                            chat_id, "Send trade like: BUY EURUSD 1.0850 TP 1.0900 SL 1.0800")

                except Exception as e:
                    send(chat_id, f"Error: {e}")

        time.sleep(1)


run()
