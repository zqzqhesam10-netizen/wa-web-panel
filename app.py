from flask import Flask, request, jsonify, render_template
import os, requests, psycopg2, subprocess, sys
from psycopg2.extras import RealDictCursor
from datetime import datetime

app = Flask(__name__)

# إعداداتك
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "1171944939327803"
VERIFY_TOKEN = "mytoken123"
DATABASE_URL = os.environ.get("DATABASE_URL")

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
    from bs4 import BeautifulSoup
    import cloudscraper
    from datetime import datetime
    
    scraper = cloudscraper.create_scraper()
    try:
        # قمنا بتغيير الرابط إلى الصفحة الرئيسية لأنها تحتوي على "البلاطات" مباشرة
        res = scraper.get("https://tuktukhd.com/", timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # استهداف الحاويات التي تحمل صور الأفلام (هذا هو الكود المعتمد في هذا التصميم)
        items = soup.select('div.poster') 
        
        print(f"DEBUG: تم العثور على {len(items)} بلاطة أفلام.")
        
        for item in items:
            link_tag = item.find('a')
            img_tag = item.find('img')
            
            if link_tag and img_tag:
                href = link_tag['href']
                title = link_tag.get('title') or img_tag.get('alt', 'بدون عنوان')
                img_url = img_tag.get('data-src') or img_tag.get('src')
                
                # فحص هل تم إرساله من قبل
                conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT id FROM messages WHERE message = %s LIMIT 1", (href,))
                if not cur.fetchone():
                    # الإرسال باستخدام دالتك الخاصة
                    cur.execute("SELECT phone FROM users WHERE phone LIKE '+%'")
                    users = cur.fetchall()
                    
                    for u in users:
                        try:
                            # إرسال الصورة والتعليق بدون رابط نصي
                            send_image_message(u['phone'], img_url, f"📺 {title}\n🔥 متاح الآن!")
                        except: pass
                    
                    cur.execute("INSERT INTO messages(phone, message, sender, msg_time) VALUES('system', %s, 'system', %s)", 
                                (href, datetime.now().strftime("%H:%M:%S")))
                    conn.commit()
                    print(f"🚀 تم إرسال: {title}")
                    cur.close(); conn.close()
                    break # إرسال أحدث فيلم فقط
                cur.close(); conn.close()
                
    except Exception as e:
        print(f"DEBUG_ERROR: {e}")
                
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
    # تم تحديث الإرسال هنا
    requests.post(f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages", headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}, json={"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": message}})
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

import subprocess

@app.route("/api/force_check", methods=["GET", "POST"])
def force_check():
    # تشغيل الفحص
    subprocess.Popen(["python3", "-c", "from app import check_updates; check_updates()"])
    return jsonify({"status": "Started as background process"})

@app.route("/api/test_send")
def test_send():
    send_template_message("967779255780", "https://i.imgur.com/example.jpg", "تجربة إرسال تجريبية")
    return "تم الإرسال"

@app.route("/api/clear_messages", methods=["GET"])
def clear_messages():
    conn = db(); cur = conn.cursor()
    cur.execute("DELETE FROM messages;"); conn.commit(); cur.close(); conn.close()
    return "تم الحذف"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET": return request.args.get("hub.challenge") if request.args.get("hub.verify_token") == VERIFY_TOKEN else "error", 403
    try:
        data = request.json
        if "messages" in data["entry"][0]["changes"][0]["value"]:
            msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
            phone, text = msg["from"], msg.get("text", {}).get("body", "")
            conn = db(); cur = conn.cursor()
            cur.execute("INSERT INTO messages(phone,message,sender,msg_time) VALUES(%s,%s,'them',%s)", (phone, text, datetime.now().strftime("%H:%M")))
            cur.execute("INSERT INTO users(phone) VALUES(%s) ON CONFLICT DO NOTHING", (phone,))
            conn.commit(); cur.close(); conn.close()
    except: pass
    return "ok"

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
