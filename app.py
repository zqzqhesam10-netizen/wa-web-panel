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

def send_image_message(phone, image_url, caption):
    try:
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp",
            "to": phone.replace('+', '').strip(),
            "type": "image",
            "image": {"link": image_url, "caption": caption}
        }
        res = requests.post(url, headers=headers, json=payload)
        print(f"DEBUG: حالة الإرسال: {res.status_code}")
    except Exception as e:
        print(f"DEBUG: خطأ في الإرسال: {e}")
    
def check_updates():
    from bs4 import BeautifulSoup
    import cloudscraper
    print("===== بدأ فحص التحديثات الجديدة =====")
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("SELECT phone FROM users")
        users = cur.fetchall()
        
        scraper = cloudscraper.create_scraper()
        url = "https://tuktukhd.com/recent/"
        res = scraper.get(url, timeout=30)
        soup = BeautifulSoup(res.text, 'html.parser')

        # 1. طباعة كل الكلاسات الموجودة لنعرف اسم الكلاس الصحيح
        classes = set([tag.get('class')[0] for tag in soup.find_all(class_=True)])
        print(f"DEBUG: الكلاسات المكتشفة في الصفحة: {classes}")

        # 2. استهداف عام جداً (كل الروابط التي بداخلها صورة)
        items = soup.find_all("a")
        found_count = 0
        
        for item in items:
            img = item.find("img")
            if img:
                # هذا الجزء سيضمن أننا وجدنا شيئاً
                title = item.get("title") or (img.get("alt") if img else "لا يوجد عنوان")
                link_url = item.get("href")
                
                # طباعة أول 5 محاولات لنعرف لماذا لا يتم الإرسال
                if found_count < 5:
                    print(f"DEBUG: تم فحص رابط: {title} | الرابط: {link_url}")
                
                # التحقق من قاعدة البيانات
                cur.execute("SELECT id FROM messages WHERE message = %s LIMIT 1", (link_url,))
                if not cur.fetchone():
                    print(f"✅ محتوى جديد: {title}")
                    img_url = img.get("data-src") or img.get("src")
                    msg = f"📺 {title}\n🔥 متاح الآن في الاستراحة!"
                    
                    for u in users:
                        send_image_message(u[0], img_url, msg)
                    
                    cur.execute("INSERT INTO messages(phone, message, sender, msg_time) VALUES('system', %s, 'system', %s)", 
                                (link_url, datetime.now().strftime("%H:%M")))
                    conn.commit()
                    found_count += 1
        
        cur.close(); conn.close()
        print(f"===== تم الانتهاء: تم إرسال {found_count} تحديث =====")
    except Exception as e:
        print(f"DEBUG: خطأ في الفحص: {e}")
                
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
    subprocess.Popen([sys.executable, "-c", "from app import check_updates; check_updates()"])
    return jsonify({"status": "Started"})

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
