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
        
import cloudscraper
import re

def check_updates():
    try:
        conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT phone FROM users")
        users = cur.fetchall()
        
        scraper = cloudscraper.create_scraper()
        res = scraper.get("https://www.fasel-hd.cam/most_recent", timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        links = list(soup.select('.post-title a'))
        
        # --- إضافة سجل تتبع ---
        print(f"DEBUG: تم العثور على {len(links)} رابط في الصفحة.") 
        
        for link in reversed(links):
            raw_title = link.get('title') or link.text.strip()
            title = " ".join(raw_title.split())
            
            # فلترة
            is_match = any(k in title for k in ["مسلسل", "انمي", "فيلم"])
            has_digit = any(char.isdigit() for char in title)
            
            if is_match and has_digit:
                cur.execute("SELECT id FROM messages WHERE message = %s LIMIT 1", (title,))
                if not cur.fetchone():
                    # الحفظ والإرسال
                    cur.execute("INSERT INTO messages(phone,message,sender,msg_time) VALUES('system', %s, 'system', %s)", 
                                (title, datetime.now().strftime("%H:%M")))
                    conn.commit()
                    
                    img_tag = link.find('img') or link.find_previous('img')
                    img_url = img_tag.get('data-src') or img_tag.get('src') if img_tag else "https://i.imgur.com/example.jpg"
                    msg = f"📺 {title}\n🔥 متاح الآن في الاستراحة!"
                    for u in users: send_image_message(u['phone'], img_url, msg)
            else:
                # هذا السطر سيخبرنا في الـ Logs لماذا تم تجاهل العناوين
                print(f"DEBUG: تم تجاهل العنوان: {title} (Match: {is_match}, Digit: {has_digit})")
        
        cur.close(); conn.close()
    except Exception as e: print(f"DEBUG: Error: {e}")
        
def loop():
    print("DEBUG: Loop started...") # للتأكد في الـ Logs
    time.sleep(30) 
    while True:
        try:
            print("DEBUG: Checking for updates...")
            check_updates()
        except Exception as e:
            print(f"DEBUG: Error in loop: {e}")
        
        # الفحص كل 15 دقيقة (900 ثانية)
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

@app.route("/api/force_check", methods=["GET", "POST"])
def force_check():
    check_updates()
    return jsonify({"status": "تم الفحص بنجاح"})

@app.route("/api/clear_messages", methods=["GET"])
def clear_messages():
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("DELETE FROM messages;") 
        conn.commit(); cur.close(); conn.close()
        return "<h1>✅ تم حذف جميع الرسائل من قاعدة البيانات بنجاح!</h1><p>الآن البوت سيعتبر كل شيء جديداً وسيرسل التحديثات فوراً.</p>"
    except Exception as e:
        return f"<h1>❌ حدث خطأ: {e}</h1>"

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
    # تشغيل الفحص في خيط منفصل لضمان عدم توقف السيرفر
    threading.Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
