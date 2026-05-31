from flask import Flask, request, jsonify, render_template_string
import sqlite3
import requests
import os
import threading
import time
from datetime import datetime
from bs4 import BeautifulSoup

app = Flask(__name__)

# ================= CONFIG =================
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "1171944939327803"
VERIFY_TOKEN = "mytoken123"

# ================= DB =================
def db():
    conn = sqlite3.connect("chat.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (phone TEXT PRIMARY KEY)")
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

# ================= FUNCTIONS =================
def send_message(phone, message):
    clean_phone = str(phone).replace("+", "").strip()
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": clean_phone, "type": "text", "text": {"body": message}}
    try:
        r = requests.post(url, headers=headers, json=data)
        res = r.json()
        return res["messages"][0]["id"] if "messages" in res else None
    except:
        return None

# دالة المراقب التلقائي (الدمج)
def monitor_site():
    last_link = ""
    while True:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get("https://web53118x.faselhdx.bid/most_recent", headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            # ملاحظة: قم بتغيير 'a' والكلاس حسب هيكلية الموقع الحقيقية
            item = soup.find('a', class_='post-link') 
            if item and item.get('href'):
                current_link = item['href']
                if current_link != last_link:
                    last_link = current_link
                    # إرسال التحديث لجميع المستخدمين
                    conn = db()
                    users = conn.execute("SELECT phone FROM users").fetchall()
                    for user in users:
                        send_message(user["phone"], f"تحديث جديد من الموقع: {current_link}")
                    conn.close()
        except Exception as e:
            print("Monitor Error:", e)
        time.sleep(300) # فحص كل 5 دقائق

# تشغيل المراقب في الخلفية
threading.Thread(target=monitor_site, daemon=True).start()

# ================= HTML & ROUTES =================
HTML_TEMPLATE = """ ... (ضع كود HTML الخاص بك هنا كاملاً) ... """

@app.route("/")
@app.route("/chat")
def chat_panel():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/users")
def get_users():
    conn = db()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return jsonify({"users": [dict(u) for u in users]})

@app.route("/api/add_user", methods=["POST"])
def add_user():
    phone = request.form.get("phone", "").strip()
    conn = db()
    conn.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/send", methods=["POST"])
def send():
    phone, message = request.form["phone"], request.form["message"]
    wamid = send_message(phone, message)
    now_time = datetime.now().strftime("%I:%M %p")
    conn = db()
    conn.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
    conn.execute("INSERT INTO messages (msg_id, phone, message, sender, msg_time) VALUES (?, ?, ?, 'me', ?)", 
                 (wamid, phone, message, now_time))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "error", 403
    # ... باقي منطق الويب هوك ...
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
