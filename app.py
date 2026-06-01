from flask import Flask, request, jsonify, render_template
import os
import threading
import time
from datetime import datetime
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from bs4 import BeautifulSoup

app = Flask(__name__)

# ================= CONFIG =================
ACCESS_TOKEN = "YOUR_TOKEN"
PHONE_NUMBER_ID = "YOUR_ID"
VERIFY_TOKEN = "mytoken123"
DATABASE_URL = os.environ.get("DATABASE_URL")

# ================= SOURCES =================
SOURCES = [
    "https://web6112x.faselhdx.bid/recent_series",
    "https://w1.anime4up.rest/episode/",
    "https://m.asd.ink/category/foreign-movies-14/",
    "https://m.asd.ink/category/asian-movies-2/",
    "https://m.asd.ink/category/turkish-movies/",
    "https://m.asd.ink/category/arabic-movies-14/",
    "https://m.asd.ink/category/indian-movies-2/",
    "https://5tv.lol/new-episodes/"
]

last_seen = {}

# ================= DB =================
def db():
    return psycopg2.connect(DATABASE_URL)


def get_all_users():
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT phone FROM users")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users


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


# ================= SCRAPER =================
def get_latest_item(url):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.find_all("a"):
            title = a.get_text(strip=True)
            href = a.get("href")

            if title and href:
                return f"{title} | {href}"

    except Exception as e:
        print("SCRAPER ERROR:", url, e)

    return None


# ================= INITIAL TEST =================
def send_initial_updates():
    users = get_all_users()

    print("INIT USERS:", len(users))

    if not users:
        print("NO USERS FOUND")
        return

    for url in SOURCES:
        latest = get_latest_item(url)

        print("INIT:", url, latest)

        if not latest:
            continue

        last_seen[url] = latest

        message = f"🧪 تجربة تشغيل:\n{latest}\n\n🌐 المصدر:\n{url}"

        for u in users:
            print("SEND TEST TO:", u["phone"])
            send_message(u["phone"], message)


# ================= MONITOR =================
def check_updates():
    users = get_all_users()

    print("CHECK USERS:", len(users))

    for url in SOURCES:
        latest = get_latest_item(url)

        print("CHECK:", url, latest)

        if not latest:
            continue

        if last_seen.get(url) != latest:
            last_seen[url] = latest

            message = f"📢 تحديث جديد:\n{latest}\n\n🌐 المصدر:\n{url}"

            for u in users:
                print("SEND:", u["phone"])
                send_message(u["phone"], message)


def loop():
    while True:
        check_updates()
        time.sleep(180)


def start_monitor():
    print("MONITOR STARTED")

    # 🔥 إرسال تجربة عند التشغيل
    send_initial_updates()

    # تشغيل المراقبة
    threading.Thread(target=loop, daemon=True).start()


# ================= WEB =================
@app.route("/debug_users")
def debug_users():
    return jsonify(get_all_users())


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
