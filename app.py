from flask import Flask, request, jsonify, render_template
import os
import threading
import time
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

# ================= CONFIG =================
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "1171944939327803"
VERIFY_TOKEN = "mytoken123"

DATABASE_URL = os.environ.get("DATABASE_URL")

TARGET_URL = "https://tuktukhd.com/recent/"

last_post = None
MONITOR_STATUS = [{"name": "TuktukHD", "status": "WAIT"}]

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

    try:
        r = requests.post(url, headers=headers, json=data)
        return r.status_code == 200
    except:
        return False


# ================= USERS =================
@app.route("/api/users")
def users():
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM users")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rows)

@app.route("/api/add_user", methods=["POST"])
def add_user():
    phone = request.form.get("phone")

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO users(phone) VALUES(%s) ON CONFLICT DO NOTHING", (phone,))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "ok"})

# ================= BROADCAST =================
@app.route("/api/broadcast", methods=["POST"])
def broadcast():
    message = request.form.get("message")

    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT phone FROM users")
    users = cur.fetchall()

    success = 0

    for u in users:
        if send_message(u["phone"], message):
            success += 1
        time.sleep(1)

    return jsonify({"sent": success})


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

        # حفظ المستخدم
        cur.execute("""
            INSERT INTO users(phone)
            VALUES(%s)
            ON CONFLICT DO NOTHING
        """, (phone,))

        # 🔥 حفظ الرسالة (مهم)
        cur.execute("""
            INSERT INTO messages(phone,message,sender,msg_time)
            VALUES(%s,%s,'them',%s)
        """, (phone, text, datetime.now().strftime("%H:%M")))

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print("webhook error:", e)

    return "ok"


# ================= SCRAPER =================
def get_latest():
    try:
        r = requests.get(TARGET_URL, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")

        post = soup.select_one("article a")

        if not post:
            return None

        title = post.get_text(strip=True)
        link = post["href"]

        img = soup.select_one("article img")
        img_url = img["src"] if img else ""

        return {
            "title": title,
            "link": link,
            "image": img_url
        }

    except:
        return None


# ================= MONITOR =================
def check_updates():
    global last_post, MONITOR_STATUS

    data = get_latest()

    if not data:
        MONITOR_STATUS = [{"name": "TuktukHD", "status": "ERROR"}]
        return

    MONITOR_STATUS = [{"name": "TuktukHD", "status": "OK"}]

    if last_post != data["link"]:
        last_post = data["link"]

        message = f"""🎬 حلقة جديدة

📺 {data['title']}

🔗 {data['link']}"""

        conn = db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT phone FROM users")
        users = cur.fetchall()

        for u in users:
            send_message(u["phone"], message)
            time.sleep(1)

        cur.close()
        conn.close()


def loop():
    while True:
        check_updates()
        time.sleep(120)


def start_monitor():
    threading.Thread(target=loop, daemon=True).start()


# ================= MONITOR API =================
@app.route("/api/monitor-status")
def monitor_status():
    return jsonify(MONITOR_STATUS)


# ================= FRONT =================
@app.route("/")
def home():
    return render_template("chat.html")


# ================= START =================
if __name__ == "__main__":
    start_monitor()
    app.run(host="0.0.0.0", port=10000)
