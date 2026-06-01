from flask import Flask, request, jsonify, render_template
import os, threading, time, requests, psycopg2
from psycopg2.extras import RealDictCursor
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

# CONFIGURATION
SCRAPER_API_KEY = "0d4cd1bb9dc081ed9ecc41394e232b20"
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD")
PHONE_NUMBER_ID = "1171944939327803"
VERIFY_TOKEN = "mytoken123"
DATABASE_URL = os.environ.get("DATABASE_URL")

def db(): return psycopg2.connect(DATABASE_URL)

def send_message(phone, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    requests.post(url, headers=headers, json={"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": message}})

# نظام الفحص الدوري
def loop():
    while True:
        try:
            conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
            # مثال لموقع
            res = requests.get("https://5tv.lol/new-episodes/", headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                item = soup.select_one(".entry-title a")
                if item:
                    title = item.text.strip()
                    cur.execute("SELECT id FROM messages WHERE message = %s LIMIT 1", (title,))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO messages(phone,message,sender,msg_time) VALUES('system',%s,'system',%s)", (title, datetime.now().strftime("%H:%M")))
                        conn.commit()
            cur.close(); conn.close()
        except: pass
        time.sleep(600)

if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    threading.Thread(target=loop, daemon=True).start()

# ROUTES
@app.route("/")
def home(): return render_template("chat.html")

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Invalid token", 403
    elif request.method == "POST":
        data = request.json
        # هنا يتم معالجة الرسائل القادمة من واتساب وحفظها في القاعدة
        return "ok", 200

@app.route("/api/get-messages")
def get_messages():
    conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 20")
    data = cur.fetchall(); cur.close(); conn.close()
    return jsonify(data)

@app.route("/api/send-message", methods=["POST"])
def send_message_route():
    data = request.json
    send_message(data.get("phone"), data.get("message"))
    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
