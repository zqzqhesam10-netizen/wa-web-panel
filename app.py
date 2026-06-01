from flask import Flask, request, jsonify, render_template
import os, threading, time, requests, psycopg2
from psycopg2.extras import RealDictCursor
from bs4 import BeautifulSoup
from datetime import datetime
import cloudscraper # تأكد من إضافتها لـ requirements.txt

# إنشاء كائن الـ scraper مرة واحدة
scraper = cloudscraper.create_scraper()

# دالة فحص الحالة المحدثة
@app.route("/api/monitor-status")
def monitor_status():
    status_list = []
    for site in TARGET_SITES:
        try:
            # استخدام scraper بدل requests
            res = scraper.get(site["url"], timeout=10)
            status = "OK" if res.status_code == 200 else f"Error ({res.status_code})"
        except Exception as e:
            status = "Offline"
        status_list.append({"name": site['url'].split('/')[2], "status": status})
    return jsonify(status_list)

# دالة المراقبة التلقائية المحدثة
def check_updates():
    for site in TARGET_SITES:
        try:
            # استخدام scraper بدل requests
            res = scraper.get(site["url"], timeout=15)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                item = soup.select_one(site["selector"])
                if item:
                    # منطق الإرسال هنا
                    print(f"Scraped: {item.text.strip()}")
        except: continue

app = Flask(__name__)

# CONFIG
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "1171944939327803"
VERIFY_TOKEN = "mytoken123"
DATABASE_URL = os.environ.get("DATABASE_URL")

TARGET_SITES = [
    {"url": "https://web6112x.faselhdx.bid/recent_series", "selector": ".post-title a"},
    {"url": "https://w1.anime4up.rest/episode/", "selector": ".eposhi a"},
    {"url": "https://m.asd.ink/category/foreign-movies-14/", "selector": ".post-title a"},
    {"url": "https://m.asd.ink/category/asian-movies-2/", "selector": ".post-title a"},
    {"url": "https://m.asd.ink/category/turkish-movies/", "selector": ".post-title a"},
    {"url": "https://m.asd.ink/category/arabic-movies-14/", "selector": ".post-title a"},
    {"url": "https://m.asd.ink/category/indian-movies-2/", "selector": ".post-title a"},
    {"url": "https://5tv.lol/new-episodes/", "selector": ".entry-title a"}
]

# DB FUNCTIONS
def db(): return psycopg2.connect(DATABASE_URL)

def send_message(phone, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    requests.post(url, headers=headers, json={"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": message}})

# MONITORING
def check_updates():
    headers = {'User-Agent': 'Mozilla/5.0'}
    for site in TARGET_SITES:
        try:
            res = requests.get(site["url"], headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            item = soup.select_one(site["selector"])
            if item:
                # يمكنك إضافة شرط هنا للتحقق من التكرار إذا أردت
                print(f"Checking {site['url']}...")
        except: continue

def loop():
    while True:
        check_updates()
        time.sleep(600)

# ROUTES
@app.route("/")
def home(): return render_template("chat.html")

@app.route("/api/users")
def users():
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM users ORDER BY phone")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify(rows)

@app.route("/api/add_user", methods=["POST"])
def add_user():
    phone = request.form.get("phone")
    conn = db(); cur = conn.cursor()
    cur.execute("INSERT INTO users(phone) VALUES(%s) ON CONFLICT DO NOTHING", (phone,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/messages/<phone>")
def messages(phone):
    conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM messages WHERE phone=%s ORDER BY id ASC", (phone,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify({"messages": rows})

@app.route("/send", methods=["POST"])
def send():
    phone = request.form.get("phone"); message = request.form.get("message")
    send_message(phone, message)
    conn = db(); cur = conn.cursor()
    cur.execute("INSERT INTO messages(phone,message,sender,msg_time) VALUES(%s,%s,'me',%s)", (phone, message, datetime.now().strftime("%H:%M")))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/broadcast", methods=["POST"])
def broadcast():
    message = request.form.get("message")
    conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT phone FROM users"); users = cur.fetchall()
    for u in users: send_message(u["phone"], message)
    cur.close(); conn.close()
    return jsonify({"status": "ok", "sent_count": len(users)})
    
@app.route("/api/monitor-status")
def monitor_status():
    status_list = []
    # إضافة User-Agent لتبدو كأنها زيارة من متصفح حقيقي
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    for site in TARGET_SITES:
        try:
            res = requests.get(site["url"], headers=headers, timeout=10)
            status = "OK" if res.status_code == 200 else f"Error ({res.status_code})"
        except Exception as e:
            status = "Offline"
        status_list.append({"name": site['url'].split('/')[2], "status": status})
    return jsonify(status_list)

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN: return request.args.get("hub.challenge")
        return "error", 403
    return "ok"

# START
if __name__ != "__main__":
    threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
