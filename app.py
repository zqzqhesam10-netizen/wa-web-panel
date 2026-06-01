from flask import Flask, request, jsonify, render_template
import os, threading, time, requests, psycopg2
from psycopg2.extras import RealDictCursor
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

# CONFIGURATION
SCRAPER_API_KEY = "0d4cd1bb9dc081ed9ecc41394e232b20"
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "1171944939327803"
DATABASE_URL = os.environ.get("DATABASE_URL")

TARGET_SITES = [
    {"url": "https://web6112x.faselhdx.bid/recent_series", "selector": ".post-title a"},
    {"url": "https://w1.anime4up.rest/episode/", "selector": ".eposhi a"},
    {"url": "https://m.asd.ink/category/foreign-movies-14/", "selector": ".post-title a"},
    {"url": "https://5tv.lol/new-episodes/", "selector": ".entry-title a"}
]

# DATABASE & TOOLS
def db(): return psycopg2.connect(DATABASE_URL)

def send_message(phone, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    requests.post(url, headers=headers, json={"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": message}})

def check_and_send():
    print("--- بدأ الفحص الدوري ---")
    try:
        conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
        for site in TARGET_SITES:
            res = requests.get('http://api.scraperapi.com/', params={'api_key': SCRAPER_API_KEY, 'url': site["url"], 'render': 'false'}, timeout=30)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                item = soup.select_one(site["selector"])
                if item:
                    title = item.text.strip()
                    link = item.get('href', '')
                    cur.execute("SELECT id FROM messages WHERE message = %s LIMIT 1", (title,))
                    if not cur.fetchone():
                        print(f"✅ جديد: {title}")
                        cur.execute("SELECT phone FROM users")
                        for u in cur.fetchall():
                            try: send_message(u["phone"], f"🚨 حلقة جديدة:\n{title}\n{link}")
                            except: pass
                        cur.execute("INSERT INTO messages(phone,message,sender,msg_time) VALUES('system',%s,'system',%s)", (title, datetime.now().strftime("%H:%M")))
                        conn.commit()
        cur.close(); conn.close()
    except Exception as e: print(f"Error: {e}")

# BACKGROUND TASK
def loop():
    while True:
        check_and_send()
        time.sleep(300) # فحص كل 5 دقائق

if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    threading.Thread(target=loop, daemon=True).start()

# ROUTES
@app.route("/")
def home(): return render_template("chat.html")

@app.route("/api/users")
def users():
    conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM users"); rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify(rows)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
