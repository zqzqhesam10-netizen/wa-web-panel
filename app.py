from flask import Flask, request, jsonify, render_template
import os, threading, time, psycopg2, cloudscraper
from psycopg2.extras import RealDictCursor
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

# CONFIG
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "1171944939327803"
VERIFY_TOKEN = "mytoken123"
DATABASE_URL = os.environ.get("DATABASE_URL")

TARGET_SITE = {"url": "https://tuktukhd.com/recent/", "selector": ".post-title a"}

def db(): return psycopg2.connect(DATABASE_URL)

def get_site_content(url):
    try:
        # إنشاء scraper يتجاوز الحماية
        scraper = cloudscraper.create_scraper()
        return scraper.get(url, timeout=15)
    except:
        return None

def send_message(phone, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    requests.post(url, headers=headers, json={"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": message}})

# MONITORING LOOP
def loop():
    while True:
        try:
            conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
            res = get_site_content(TARGET_SITE["url"])
            if res and res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                item = soup.select_one(TARGET_SITE["selector"])
                if item:
                    title = item.text.strip(); link = item.get('href', '')
                    cur.execute("SELECT id FROM messages WHERE message = %s LIMIT 1", (title,))
                    if not cur.fetchone():
                        cur.execute("SELECT phone FROM users")
                        users = cur.fetchall()
                        for u in users:
                            try: send_message(u["phone"], f"🚨 جديد:\n{title}\n{link}")
                            except: pass
                        cur.execute("INSERT INTO messages(phone,message,sender,msg_time) VALUES('system',%s,'system',%s)", (title, datetime.now().strftime("%H:%M")))
                        conn.commit()
            cur.close(); conn.close()
        except Exception as e: print(f"Loop Error: {e}")
        time.sleep(600)

if __name__ == "__main__":
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
