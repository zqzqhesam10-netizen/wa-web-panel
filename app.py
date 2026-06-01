from flask import Flask, request, jsonify, render_template
import sqlite3
import requests
import os
import threading
import time
from datetime import datetime

app = Flask(__name__)

# ================= CONFIG =================
ACCESS_TOKEN = os.getenv("EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD")
PHONE_NUMBER_ID = os.getenv("1171944939327803")
VERIFY_TOKEN = os.getenv("mytoken123")

TARGET_URL = "https://web53118x.faselhdx.bid/recent_series"

# ================= STORAGE PATH (FIXED FOR RENDER) =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

DB_PATH = os.path.join(DATA_DIR, "chat.db")
STATE_FILE = os.path.join(DATA_DIR, "state.txt")


# ================= INIT =================
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)

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
        msg_time TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ================= WHATSAPP API =================def send_message(phone, message):
    print("🚀 SENDING MESSAGE...")
    print("TO:", phone)
    print("TOKEN:", ACCESS_TOKEN)
    print("PHONE_ID:", PHONE_NUMBER_ID)

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

    r = requests.post(url, headers=headers, json=data)

    print("STATUS:", r.status_code)
    print("RESPONSE:", r.text)


# ================= MONITOR SYSTEM =================
def fetch_page():
    return requests.get(TARGET_URL, timeout=20).text


def fingerprint(html):
    return str(hash(html[:2000]))


def get_state():
    if not os.path.exists(STATE_FILE):
        return ""
    with open(STATE_FILE, "r") as f:
        return f.read()


def save_state(s):
    with open(STATE_FILE, "w") as f:
        f.write(s)


def check_updates():
    try:
        html = fetch_page()
        new_fp = fingerprint(html)
        old_fp = get_state()

        if new_fp != old_fp:
            print("🔥 Update detected")
            save_state(new_fp)

            conn = db()
            c = conn.cursor()
            c.execute("SELECT phone FROM users")
            users = c.fetchall()
            conn.close()

            for u in users:
                send_message(u["phone"], "🔥 تم اكتشاف تحديث جديد في الموقع")

    except Exception as e:
        print("monitor error:", e)


def loop():
    while True:
        check_updates()
        time.sleep(180)


def start_monitor():
    threading.Thread(target=loop, daemon=True).start()


# ================= ROUTES =================
@app.route("/")
@app.route("/chat")
def chat():
    return render_template("chat.html")


@app.route("/api/users")
def users():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    data = c.fetchall()
    conn.close()
    return jsonify([dict(x) for x in data])


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
    c.execute("""
        INSERT INTO messages (phone, message, sender, msg_time)
        VALUES (?, ?, 'me', ?)
    """, (phone, message, datetime.now().strftime("%H:%M")))
    conn.commit()
    conn.close()

    conn = db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
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
    return jsonify({"messages": [dict(x) for x in data]})


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "error", 403

    try:
        data = request.json
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        phone = msg["from"]
        text = msg["text"]["body"]

        conn = db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO messages (phone, message, sender, msg_time)
            VALUES (?, ?, 'them', ?)
        """, (phone, text, datetime.now().strftime("%H:%M")))
        conn.commit()
        conn.close()

        conn = db()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
        conn.commit()
        conn.close()

    except Exception as e:
        print("webhook error:", e)

    return "ok"


# ================= START =================
if __name__ == "__main__":
    start_monitor()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
