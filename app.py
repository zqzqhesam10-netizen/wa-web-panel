from flask import Flask, request, jsonify, render_template
import os
import threading
import time
from datetime import datetime
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# ================= CONFIG =================
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "1171944939327803"
VERIFY_TOKEN = "mytoken123"
DATABASE_URL = os.environ.get("DATABASE_URL")

TARGET_URL = "https://web53118x.faselhdx.bid/recent_series"


# ================= DB =================
def db():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        phone TEXT PRIMARY KEY
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        phone TEXT,
        message TEXT,
        sender TEXT,
        msg_time TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    cur.close()
    conn.close()


init_db()


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


# ================= USERS =================
@app.route("/api/users")
def users():
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM users ORDER BY phone")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(rows)


@app.route("/api/add_user", methods=["POST"])
def add_user():
    phone = request.form.get("phone")

    if not phone:
        return jsonify({"status": "error"})

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users(phone)
        VALUES(%s)
        ON CONFLICT (phone) DO NOTHING
    """, (phone,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "ok"})


# ================= MESSAGES =================
@app.route("/api/messages/<phone>")
def messages(phone):
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT *
        FROM messages
        WHERE phone=%s
        ORDER BY id ASC
    """, (phone,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify({"messages": rows})


@app.route("/send", methods=["POST"])
def send():
    phone = request.form.get("phone")
    message = request.form.get("message")

    send_message(phone, message)

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO messages(phone,message,sender,msg_time)
        VALUES(%s,%s,'me',%s)
    """, (phone, message, datetime.now().strftime("%H:%M")))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "ok"})


# ================= BROADCAST (FIX BUTTON) =================
@app.route("/api/broadcast", methods=["POST"])
def broadcast():

    message = request.form.get("message")

    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT phone FROM users")
    users = cur.fetchall()

    sent = 0

    for u in users:
        phone = u["phone"]

        send_message(phone, message)

        cur2 = conn.cursor()
        cur2.execute("""
            INSERT INTO messages(phone,message,sender,msg_time)
            VALUES(%s,%s,'me',%s)
        """, (phone, message, datetime.now().strftime("%H:%M")))

        conn.commit()
        sent += 1

    cur.close()
    conn.close()

    return jsonify({"status": "ok", "sent_count": sent})


# ================= WEBHOOK =================
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
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO messages(phone,message,sender,msg_time)
            VALUES(%s,%s,'them',%s)
        """, (phone, text, datetime.now().strftime("%H:%M")))

        cur.execute("""
            INSERT INTO users(phone)
            VALUES(%s)
            ON CONFLICT DO NOTHING
        """, (phone,))

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print("webhook error:", e)

    return "ok"


# ================= MONITOR =================
def check_updates():
    try:
        html = requests.get(TARGET_URL, timeout=20).text
        print("monitor OK")
    except Exception as e:
        print(e)


def loop():
    while True:
        check_updates()
        time.sleep(180)


def start_monitor():
    threading.Thread(target=loop, daemon=True).start()


# ================= FRONT =================
@app.route("/")
def home():
    return render_template("chat.html")


@app.route("/chat")
def chat():
    return render_template("chat.html")


# ================= START =================
if __name__ == "__main__":
    start_monitor()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
