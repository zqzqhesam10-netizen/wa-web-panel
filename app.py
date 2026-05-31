from flask import Flask, request, jsonify, render_template_string
import sqlite3
import requests
import os
from datetime import datetime
import threading
import time
import hashlib
from bs4 import BeautifulSoup

app = Flask(__name__)

# ================= CONFIG =================
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "1171944939327803"
VERIFY_TOKEN = "mytoken123"

TARGET_URL = "https://web53118x.faselhdx.bid/recent_series"
STATE_FILE = "state.txt"

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
        msg_id TEXT UNIQUE,
        phone TEXT,
        message TEXT,
        sender TEXT DEFAULT 'them',
        status TEXT DEFAULT 'sent',
        msg_time TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= STATE =================
def get_state():
    if not os.path.exists(STATE_FILE):
        return ""
    return open(STATE_FILE, "r", encoding="utf-8").read()


def save_state(data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(data)

# ================= SCRAPER =================
def fetch_page():
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(TARGET_URL, headers=headers, timeout=20)
    return r.text


def get_fingerprint(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return hashlib.md5(text.encode()).hexdigest()

# ================= WHATSAPP SEND =================
def send_message(phone, message):
    clean_phone = str(phone).replace("+", "").strip()
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": clean_phone,
        "type": "text",
        "text": {"body": message}
    }

    requests.post(url, headers=headers, json=data)

# ================= إرسال آخر إضافة مرة واحدة =================
def send_last_item_once():
    try:
        html = fetch_page()
        soup = BeautifulSoup(html, "html.parser")

        items = soup.find_all("div")

        if not items:
            print("No items found")
            return

        last_item = items[-1].get_text(strip=True)

        if not last_item:
            last_item = "تم العثور على إضافة جديدة ولكن بدون نص واضح"

        conn = db()
        c = conn.cursor()
        c.execute("SELECT phone FROM users")
        users = [u["phone"] for u in c.fetchall()]
        conn.close()

        for phone in users:
            send_message(phone, f"🆕 آخر إضافة حالياً:\n\n{last_item}")

        print("✅ Last item sent successfully!")

    except Exception as e:
        print("❌ Error:", e)

# ================= MONITOR =================
def check_updates():
    try:
        html = fetch_page()
        new_fp = get_fingerprint(html)
        old_fp = get_state()

        if new_fp != old_fp:
            print("🔥 New update detected!")

            save_state(new_fp)

            soup = BeautifulSoup(html, "html.parser")
            items = soup.find_all("div")

            last_item = items[-1].get_text(strip=True) if items else "تحديث جديد"

            conn = db()
            c = conn.cursor()
            c.execute("SELECT phone FROM users")
            users = [u["phone"] for u in c.fetchall()]
            conn.close()

            for phone in users:
                send_message(phone, f"🔥 تحديث جديد:\n\n{last_item}")

    except Exception as e:
        print("Monitor error:", e)

# ================= LOOP =================
def loop():
    print("🔥 Monitor started...")
    while True:
        check_updates()
        time.sleep(120)

# ================= START =================
def start_monitor():
    threading.Thread(target=loop, daemon=True).start()

# ================= WEB =================
@app.route("/")
def home():
    return "Bot is running"

@app.route("/api/users")
def users():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    data = c.fetchall()
    conn.close()
    return jsonify([dict(i) for i in data])

@app.route("/api/add_user", methods=["POST"])
def add_user():
    phone = request.form.get("phone")
    conn = db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# ================= MAIN =================
if __name__ == "__main__":
    init_db()

    # 🔥 إرسال آخر إضافة مرة واحدة للتجربة
    send_last_item_once()

    # 🔥 تشغيل المراقبة
    start_monitor()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
