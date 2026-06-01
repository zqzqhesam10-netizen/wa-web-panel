from flask import Flask, request, jsonify, render_template
import os
import threading
import time
from datetime import datetime
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from bs4 import BeautifulSoup # أضفنا هذه المكتبة

app = Flask(__name__)

# CONFIG
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "1171944939327803"
VERIFY_TOKEN = "mytoken123"
DATABASE_URL = os.environ.get("DATABASE_URL")

# إعدادات المراقبة
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
last_items = {site["url"]: "" for site in TARGET_SITES}

# ================= DB & WHATSAPP FUNCTIONS (كودك الأصلي) =================
def db(): return psycopg2.connect(DATABASE_URL)

def send_message(phone, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": message}}
    requests.post(url, headers=headers, json=data)

# ================= دالة البث التلقائي الجديدة =================
def broadcast_to_all(message):
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT phone FROM users")
    users = cur.fetchall()
    for u in users:
        send_message(u["phone"], message)
    conn.close()

# ================= نظام المراقبة =================
def check_updates():
    headers = {'User-Agent': 'Mozilla/5.0'}
    for site in TARGET_SITES:
        try:
            res = requests.get(site["url"], headers=headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            item = soup.select_one(site["selector"])
            if item:
                title = item.text.strip()
                link = item['href']
                if last_items.get(site["url"]) != title:
                    last_items[site["url"]] = title
                    broadcast_to_all(f"🆕 جديد من {site['url'].split('/')[2]}:\n{title}\n🔗 {link}")
        except: continue

def loop():
    while True:
        check_updates()
        time.sleep(600) # فحص كل 10 دقائق

# ================= ROUTES (كودك الأصلي) =================
@app.route("/api/users")
def users():
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM users ORDER BY phone")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify(rows)

# [أضف هنا بقية دوالك الأصلية: add_user, messages, send, broadcast, webhook]
@app.route("/")
def home(): return render_template("chat.html")

# ================= START =================
if __name__ != "__main__":
    threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
