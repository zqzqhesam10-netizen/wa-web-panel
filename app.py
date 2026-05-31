from flask import Flask, request, jsonify, render_template_string
import sqlite3
import requests
import os
import threading
import time
from bs4 import BeautifulSoup

app = Flask(__name__)

# ================= CONFIG =================
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "1171944939327803"
VERIFY_TOKEN = "mytoken123"

TARGET_URL = "https://web53118x.faselhdx.bid/recent_series"

# ================= DB =================
def db():
    conn = sqlite3.connect("chat.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        phone TEXT PRIMARY KEY
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        message TEXT,
        sender TEXT DEFAULT 'them',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= SCRAPER =================
def fetch_page():
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(TARGET_URL, headers=headers, timeout=20)
    return r.text


def extract_last_item(html):
    soup = BeautifulSoup(html, "html.parser")
    items = soup.find_all("div")

    for item in reversed(items):
        text = item.get_text(strip=True)
        if text and len(text) > 15:
            return text

    return None


# ================= WHATSAPP =================
def send_message(phone, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message}
    }

    requests.post(url, headers=headers, json=data)


# ================= MONITOR =================
def check_updates():
    try:
        html = fetch_page()
        last_item = extract_last_item(html)

        if not last_item:
            return

        print("🔥 Latest:", last_item)

        conn = db()
        c = conn.cursor()
        c.execute("SELECT phone FROM users")
        users = [u["phone"] for u in c.fetchall()]
        conn.close()

        message = f"🔥 آخر إضافة:\n\n{last_item}"

        for phone in users:
            send_message(phone, message)

    except Exception as e:
        print("Monitor error:", e)


def loop():
    while True:
        check_updates()
        time.sleep(180)


def start_monitor():
    threading.Thread(target=loop, daemon=True).start()


# ================= ROUTES =================
@app.route("/")
def home():
    return "WhatsApp Panel Running"


@app.route("/api/users")
def users():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    data = c.fetchall()
    conn.close()
    return jsonify([dict(u) for u in data])


@app.route("/api/add_user", methods=["POST"])
def add_user():
    phone = request.form.get("phone")
    conn = db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/send", methods=["POST"])
def send():
    phone = request.form["phone"]
    message = request.form["message"]

    send_message(phone, message)

    conn = db()
    c = conn.cursor()
    c.execute("INSERT INTO messages (phone, message, sender) VALUES (?, ?, 'me')",
              (phone, message))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})


@app.route("/messages/<phone>")
def messages(phone):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM messages WHERE phone=? ORDER BY id ASC", (phone,))
    data = c.fetchall()
    conn.close()
    return jsonify({"messages": [dict(m) for m in data]})


@app.route("/webhook", methods=["GET"])
def webhook_verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "error", 403


# ================= START =================
if __name__ == "__main__":
    start_monitor()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
