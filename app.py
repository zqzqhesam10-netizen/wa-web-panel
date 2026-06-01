from flask import Flask, request, jsonify, render_template
import os, threading, time, requests, psycopg2
from psycopg2.extras import RealDictCursor
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

# CONFIG
SCRAPER_API_KEY = "0d4cd1bb9dc081ed9ecc41394e232b20"
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

# FUNCTIONS
def db(): return psycopg2.connect(DATABASE_URL)

def get_site_content(url):
    payload = {'api_key': SCRAPER_API_KEY, 'url': url, 'render': 'false'}
    try: return requests.get('http://api.scraperapi.com/', params=payload, timeout=60)
    except: return None

# ROUTES - تعريف المسارات في الأعلى
@app.route("/")
def home(): return render_template("chat.html")

@app.route("/api/users")
def users():
    conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM users ORDER BY phone")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify(rows)

@app.route("/api/monitor-status")
def monitor_status():
    status_list = []
    for site in TARGET_SITES:
        res = get_site_content(site["url"])
        status = "OK" if res and res.status_code == 200 else f"Error ({res.status_code if res else 'Fail'})"
        status_list.append({"name": site['url'].split('/')[2], "status": status})
    return jsonify(status_list)

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN: return request.args.get("hub.challenge")
        return "error", 403
    return "ok"

# MONITORING - تشغيل المراقبة فقط إذا كنا في سيرفر الإنتاج
def loop():
    while True:
        time.sleep(600)
        print("--- فحص دوري ---")

# تشغيل الخيط (Thread) لمرة واحدة فقط عند بدء التشغيل
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
