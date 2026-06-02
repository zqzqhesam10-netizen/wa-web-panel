from flask import Flask, request, jsonify, render_template
import os, threading, time, requests, psycopg2, glob
from psycopg2.extras import RealDictCursor
from bs4 import BeautifulSoup
from datetime import datetime
import cloudscraper
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# الإعدادات
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "1171944939327803"
VERIFY_TOKEN = "mytoken123"
DATABASE_URL = os.environ.get("DATABASE_URL")

SITES = [
    {"url": "https://web6112x.faselhdx.bid/recent_series", "sel": ".post-title a"},
    {"url": "https://w1.anime4up.rest/episode/", "sel": ".eposhi a"},
    {"url": "https://m.asd.ink/category/foreign-movies-14/", "sel": ".post-title a"},
    {"url": "https://5tv.lol/new-episodes/", "sel": ".entry-title a"}
]

def db(): return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = db(); cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (phone TEXT PRIMARY KEY);")
    cur.execute("CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, phone TEXT, message TEXT, sender TEXT, msg_time TEXT);")
    conn.commit(); cur.close(); conn.close()

def send_message(phone, message):
    try:
        requests.post(f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages", 
                      headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"},
                      json={"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": message}})
    except: pass

def send_image_message(phone, image_url, caption):
    try:
        requests.post(f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages",
                      headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"},
                      json={
                          "messaging_product": "whatsapp",
                          "to": phone,
                          "type": "image",
                          "image": {"link": image_url, "caption": caption}
                      })
    except: pass
        
   def check_updates():
    # هذا السطر يضمن تشغيل الفحص في الخلفية بالكامل
    try:
        print("DEBUG: بدء الفحص في الخلفية...")
        browser_path = "/opt/render/project/src/.playwright/chromium-1223/chrome-linux64/chrome"
        
        with sync_playwright() as p:
            print("DEBUG: جاري إطلاق المتصفح...")
            browser = p.chromium.launch(headless=True, executable_path=browser_path, args=["--no-sandbox"])
            page = browser.new_page()
            
            print("DEBUG: جاري الانتقال للموقع...")
            page.goto("https://w1.anime4up.rest/episode/", timeout=60000)
            page.wait_for_timeout(5000)
            
            soup = BeautifulSoup(page.content(), 'html.parser')
            browser.close()
            
            # استخراج البيانات
            items = soup.select('div.anime-card a') 
            if items:
                latest_ep = items[0].get_text(strip=True)
                latest_link = items[0]['href']
                print(f"DEBUG: تم العثور على: {latest_ep}")
                
                # هنا يتم الإرسال
                # ... (كود إرسال الواتساب) ...
            else:
                print("DEBUG: لم يتم العثور على حلقات.")
    except Exception as e:
        print(f"DEBUG: خطأ في الفحص: {e}")

@app.route("/api/force_check", methods=["POST"])
def force_check():
    # تشغيل الفحص في Thread منفصل لضمان استمرار السيرفر
    threading.Thread(target=check_updates, daemon=True).start()
    return jsonify({"status": "تم بدء الفحص في الخلفية"})

def loop():
    while True:
        try:
            check_updates()
        except Exception as e:
            print(f"DEBUG: خطأ في حلقة التكرار: {e}")
        time.sleep(3600)

@app.route("/")
def home(): return render_template("chat.html")

@app.route("/api/status")
def status(): return jsonify({"message": "النظام يعمل والمراقبة نشطة"})

@app.route("/api/users")
def get_users():
    conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT phone FROM users ORDER BY phone"); rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify({"users": rows})

@app.route("/api/messages/<phone>")
def get_messages(phone):
    conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM messages WHERE phone=%s ORDER BY id ASC", (phone,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify({"messages": rows})

@app.route("/send", methods=["POST"])
def send():
    phone, message = request.form.get("phone"), request.form.get("message")
    send_message(phone, message)
    conn = db(); cur = conn.cursor()
    cur.execute("INSERT INTO messages(phone,message,sender,msg_time) VALUES(%s,%s,'me',%s)", (phone, message, datetime.now().strftime("%H:%M")))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/add_user", methods=["POST"])
def add_user():
    phone = request.form.get("phone")
    if phone:
        conn = db(); cur = conn.cursor()
        cur.execute("INSERT INTO users(phone) VALUES(%s) ON CONFLICT DO NOTHING", (phone,))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

@app.route("/api/force_check", methods=["POST"])
def force_check():
    threading.Thread(target=check_updates).start()
    return jsonify({"status": "تم بدء الفحص"})

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET": return request.args.get("hub.challenge") if request.args.get("hub.verify_token") == VERIFY_TOKEN else "error", 403
    try:
        data = request.json
        if "messages" in data["entry"][0]["changes"][0]["value"]:
            msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
            phone, text = msg["from"], msg["text"]["body"]
            conn = db(); cur = conn.cursor()
            cur.execute("INSERT INTO messages(phone,message,sender,msg_time) VALUES(%s,%s,'them',%s)", (phone, text, datetime.now().strftime("%H:%M")))
            cur.execute("INSERT INTO users(phone) VALUES(%s) ON CONFLICT DO NOTHING", (phone,))
            conn.commit(); cur.close(); conn.close()
    except: pass
    return "ok"

if __name__ == "__main__":
    init_db()
    threading.Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
