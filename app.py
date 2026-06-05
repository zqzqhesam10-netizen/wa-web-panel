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

def send_whatsapp_message(phone, message_body, img_url=None):
    import requests
    
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}", 
        "Content-Type": "application/json"
    }
    
    # التحقق مما إذا كنا سنرسل صورة أم نصاً فقط
    if img_url:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone.replace('+', '').strip(),
            "type": "image",
            "image": {"link": img_url},
            "caption": message_body
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone.replace('+', '').strip(),
            "type": "text",
            "text": {"body": message_body}
        }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"DEBUG: حالة الإرسال ({'صورة' if img_url else 'نص'}): {response.status_code}")
    return response.status_code
    
def check_updates():
    from bs4 import BeautifulSoup
    import cloudscraper
    import hashlib
    import requests
    from datetime import datetime

    try:
        print("===== بدأ فحص التحديثات الجديدة =====")
        conn = db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # جلب قائمة المستخدمين
        cur.execute("SELECT phone FROM users")
        users = cur.fetchall()
        
        scraper = cloudscraper.create_scraper()
        url = "https://tuktukhd.com/recent/"
        response = scraper.get(url, timeout=30)
        soup = BeautifulSoup(response.text, "html.parser")

        # نختار أول 5 عناصر (أحدث 5 إضافات)
       items = soup.select(".recent-posts img")[:5] # إذا فشل، جرب soup.find_all("img")[:5] فقط
        if not items:
            # إذا لم يجد شيئاً، ابحث في كل الصور
            items = soup.find_all("img")[:5]

        sent_count = 0

        for img in items:
            # نحاول الوصول للأب الذي يحتوي على الرابط والعنوان
            parent = img.find_parent("a")
            title = (img.get("alt") or "").strip()
            
            # إذا لم نجد عنواناً في الـ alt، نبحث عنه في الـ title الخاص بالرابط
            if not title and parent:
                title = parent.get("title", "تحديث جديد").strip()
            
            if not title or not parent: continue
            
            # منع التكرار
            uid = hashlib.md5(title.encode("utf-8")).hexdigest()
            cur.execute("SELECT id FROM messages WHERE message=%s LIMIT 1", (uid,))
            if cur.fetchone(): continue
            
            # إعداد النص (بدون روابط كما طلبت)
            caption = f"📺 {title}\n🔥 متاح الآن في الاستراحة!"
            
            # الإرسال لجميع المستخدمين
            proxy_img_url = f"https://images.weserv.nl/?url={img_url}"
            for user in users:
                send_whatsapp_message(user["phone"], caption, img_url=proxy_img_url)
            
            # تسجيل الإرسال في القاعدة
            cur.execute("INSERT INTO messages (message, phone, sender, msg_time) VALUES (%s, 'system', 'system', %s)", 
                        (uid, datetime.now().strftime("%H:%M")))
            conn.commit()
            sent_count += 1
            
        print(f"===== انتهى الفحص: تم إرسال {sent_count} تحديث جديد =====")
        cur.close()
        conn.close()
        
    except Exception as e:
        print("خطأ في الفحص:", e)
                
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

@app.route("/clear_db")
def clear_db():
    try:
        conn = db()
        cur = conn.cursor()
        # حذف جميع المستخدمين
        cur.execute("DELETE FROM users;")
        conn.commit()
        cur.close()
        conn.close()
        return "✅ تم حذف جميع الأرقام بنجاح! يمكنك الآن بدء استقبال مشتركين جدد."
    except Exception as e:
        return f"❌ حدث خطأ: {e}"

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
