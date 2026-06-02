from flask import Flask, request, jsonify, render_template
import os, threading, time, requests, psycopg2
from psycopg2.extras import RealDictCursor
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

# ضع بياناتك الحقيقية هنا
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

# دالة إرسال النص (للرسائل العادية)
def send_message(phone, message):
    try:
        requests.post(f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages", 
                      headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"},
                      json={"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": message}})
    except: pass

# دالة إرسال الصورة (جديدة)
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
    try:
        # فحص TuktukHD
        check_tuktukhd()
        # يمكنك إضافة استدعاءات أخرى هنا
    except Exception as e:
        print(f"DEBUG: خطأ في الدالة الرئيسية للتشغيل: {e}")

from playwright.sync_api import sync_playwright

def check_tuktukhd():
    try:
        # تأكد من أن هذا المسار هو المسار الصحيح للمتصفح على سيرفر Render
        browser_path = "/opt/render/project/src/.playwright/chromium-1223/chrome-linux64/chrome"
        
        print("DEBUG: جاري إطلاق المتصفح الحقيقي...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=browser_path, args=["--no-sandbox", "--disable-setuid-sandbox"])
            page = browser.new_page()
            
            print("DEBUG: جاري الانتقال للموقع...")
            page.goto("https://tuktukhd.com/recent/", timeout=60000)
            
            # الانتظار قليلاً حتى يتم تحميل المحتوى الديناميكي
            page.wait_for_timeout(5000) 
            
            # استخراج محتوى الصفحة بعد تحميل الجافاسكريبت
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            browser.close()
            
            # الآن نبحث عن الروابط كما فعلنا سابقاً
            items = soup.select('div.post-item a, div.card a, a.img-link')
            
            if not items:
                items = soup.find_all('a', href=True)

            for link in items:
                title = link.get('title') or link.text.strip()
                if title and len(title) > 10:
                    item_url = link['href']
                    print(f"DEBUG: تم العثور بنجاح على: {title}")
                    # الإرسال للمستخدمين...
                    # (يمكنك إضافة كود الإرسال هنا بنفس منطقك السابق)
                    return 
            
            print("DEBUG: لم يجد أي روابط حتى مع المتصفح.")
            
    except Exception as e:
        print(f"DEBUG: خطأ فادح في Playwright: {e}")
        
def loop():
    while True:
        check_updates()
        time.sleep(60)

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
        # تأكد من أن دالة الاتصال بقاعدة البيانات لديك تسمى db()
        conn = db() 
        cur = conn.cursor()
        cur.execute("INSERT INTO users(phone) VALUES(%s) ON CONFLICT DO NOTHING", (phone,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

@app.route("/api/force_check", methods=["POST"])
def force_check():
    # استدعاء دالة الفحص فوراً
    check_updates()
    return jsonify({"status": "تم الفحص والإرسال بنجاح"})

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
