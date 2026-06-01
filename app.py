from flask import Flask, request, jsonify, render_template
import os, threading, time, requests, psycopg2
from psycopg2.extras import RealDictCursor
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

# CONFIG
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD")
PHONE_NUMBER_ID = "1171944939327803"
VERIFY_TOKEN = "mytoken123"
DATABASE_URL = os.environ.get("DATABASE_URL")

# قائمة المواقع الشاملة
SITES = [
    {"url": "https://web6112x.faselhdx.bid/recent_series", "sel": ".post-title a"},
    {"url": "https://w1.anime4up.rest/episode/", "sel": ".eposhi a"},
    {"url": "https://m.asd.ink/category/foreign-movies-14/", "sel": ".post-title a"},
    {"url": "https://m.asd.ink/category/asian-movies-2/", "sel": ".post-title a"},
    {"url": "https://m.asd.ink/category/turkish-movies/", "sel": ".post-title a"},
    {"url": "https://m.asd.ink/category/arabic-movies-14/", "sel": ".post-title a"},
    {"url": "https://m.asd.ink/category/indian-movies-2/", "sel": ".post-title a"},
    {"url": "https://5tv.lol/new-episodes/", "sel": ".entry-title a"}
]

def db(): return psycopg2.connect(DATABASE_URL)

def send_message(phone, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    requests.post(url, headers=headers, json={"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": message}})

# نظام المراقبة الشامل
def check_updates():
    try:
        conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
        for site in SITES:
            try:
                res = requests.get(site["url"], headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    item = soup.select_one(site["sel"])
                    if item:
                        title = item.text.strip()
                        link = item.get('href', '')
                        
                        cur.execute("SELECT id FROM messages WHERE message = %s LIMIT 1", (title,))
                        if not cur.fetchone():
                            cur.execute("SELECT phone FROM users")
                            for u in cur.fetchall():
                                send_message(u['phone'], f"🆕 تحديث جديد:\n{title}\n🔗 {link}")
                            
                            cur.execute("INSERT INTO messages(phone,message,sender,msg_time) VALUES('system', %s, 'system', %s)", 
                                        (title, datetime.now().strftime("%H:%M")))
                            conn.commit()
            except: continue
        cur.close(); conn.close()
    except Exception as e: print(f"Monitor Error: {e}")

def loop():
    while True:
        check_updates()
        time.sleep(900) # فحص كل 15 دقيقة لضمان عدم الحظر

@app.route("/")
def home(): return render_template("chat.html")

@app.route("/api/users")
def get_users():
    conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT phone FROM users"); res = cur.fetchall(); cur.close(); conn.close()
    return jsonify(res)

@app.route("/api/messages/<phone>")
def get_messages(phone):
    conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM messages WHERE phone=%s ORDER BY id ASC", (phone,))
    res = cur.fetchall(); cur.close(); conn.close()
    return jsonify({"messages": res})

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return request.args.get("hub.challenge") if request.args.get("hub.verify_token") == VERIFY_TOKEN else "Invalid", 403
    data = request.json
    try:
        if 'messages' in data["entry"][0]["changes"][0]["value"]:
            msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
            phone, text = msg["from"], msg["text"]["body"]
            conn = db(); cur = conn.cursor()
            cur.execute("INSERT INTO messages(phone,message,sender,msg_time) VALUES(%s,%s,'them',%s)", (phone, text, datetime.now().strftime("%H:%M")))
            cur.execute("INSERT INTO users(phone) VALUES(%s) ON CONFLICT DO NOTHING", (phone,))
            conn.commit(); cur.close(); conn.close()
    except: pass
    return "ok"

if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
