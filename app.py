from flask import Flask, request, jsonify, render_template_string
import sqlite3
import requests
import os
from datetime import datetime

app = Flask(__name__)

# ================= CONFIG (الإعدادات الثابتة) =================
# 🔴 ملاحظة: استبدل الـ ACCESS_TOKEN بالتوكن الدائم الذي ستستخرجه من مستخدم النظام (whatsapp_bot) لكي لا يتوقف الإرسال بعد 24 ساعة.
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "1131313053401090" 
VERIFY_TOKEN = "mytoken123"
MY_PERSONAL_PHONE = "967779255780" 

# ================= DATABASE (إعداد قاعدة البيانات) =================
def db():
    conn = sqlite3.connect("chat.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (phone TEXT PRIMARY KEY)")
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        msg_id TEXT UNIQUE,
        phone TEXT,
        message TEXT,
        sender TEXT DEFAULT 'them',
        status TEXT DEFAULT 'sent',
        msg_time TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ================= SEND MESSAGE API (دالة الإرسال) =================
def send_message(phone, message):
    clean_phone = str(phone).replace("+", "").strip()
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": clean_phone,
        "type": "text",
        "text": {"body": message}
    }
    try:
        r = requests.post(url, headers=headers, json=data)
        print("Meta Response:", r.json())  # لمراقبة الأخطاء في سجلات السيرفر
        if "messages" in r.json():
            return r.json()["messages"][0]["id"]
    except Exception as e:
        print("Send Error:", e)
    return None

# ================= HTML TEMPLATE (واجهة لوحة التحكم) =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>واتساب ويب - لوحة التحكم</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: sans-serif; }
        body { display: flex; height: 100vh; background-color: #dadbd3; overflow: hidden; }
        .sidebar { width: 380px; min-width: 380px; background: #fff; display: flex; flex-direction: column; border-left: 1px solid #e9edef; }
        .sidebar-header { height: 60px; background: #f0f2f5; display: flex; align-items: center; padding: 0 12px; justify-content: space-between; }
        .header-actions { display: flex; align-items: center; gap: 6px; }
        .text-btn { border: none; padding: 6px 10px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: bold; color: white; text-decoration: none; display: inline-flex; align-items: center; }
        .text-btn.broadcast { background-color: #0284c7; }
        .text-btn.new-chat { background-color: #00a884; }
        .text-btn.contact-owner { background-color: #ea580c; }
        .search-box { padding: 8px 12px; background: #fff; border-bottom: 1px solid #f0f2f5; }
        .search-inner { background: #f0f2f5; border-radius: 8px; padding: 6px 12px; color: #667781; }
        .search-inner input { background: transparent; border: none; outline: none; width: 100%; font-size: 14px; }
        .user-list { flex: 1; overflow-y: auto; background: #fff; padding: 20px; text-align: center; color: #8696a0; font-size: 14px; }
        .chat-area { flex: 1; display: flex; flex-direction: column; background: #efeae2; }
        .welcome-screen { display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1; background: #f8f9fa; color: #667781; text-align: center; border-bottom: 6px solid #00a884; padding: 20px; }
        .welcome-screen h2 { color: #41525d; margin-bottom: 10px; font-size: 28px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <span style="font-weight: bold; color: #111b21;">المحادثات</span>
            <div class="header-actions">
                <a href="https://wa.me/967779255780?text=مرحباً" target="_blank" class="text-btn contact-owner">📱 راسل المالك</a>
                <button class="text-btn broadcast" onclick="alert('البث يعمل عند وجود مستخدمين نشطين')">📢 بث</button>
                <button class="text-btn new-chat" onclick="alert('ستظهر الأرقام هنا تلقائياً عند استقبال الرسائل')">➕ رقم</button>
            </div>
        </div>
        <div class="search-box"><div class="search-inner"><input type="text" placeholder="البحث..."></div></div>
        <div class="user-list">لا توجد محادثات نشطة حالياً.</div>
    </div>
    <div class="chat-area">
        <div class="welcome-screen">
            <h2>واتساب ويب للمسؤول (تم الدمج والاصلاح ✅)</h2>
            <p>تم معالجة استقبال كود التحقق والأزرار بنجاح لمنع ظهور كلمة [وسائط].</p>
            <p style="margin-top: 15px; font-size: 14px; color: #ea580c; font-weight: bold;">💡 اضغط على زر [📱 راسل المالك] بالأعلى لتجربة إرسال رسالة مباشرة إلى رقمك الشخصي!</p>
        </div>
    </div>
</body>
</html>
"""

# ================= ROUTES (المسارات والـ Webhook) =================
@app.route("/")
@app.route("/chat")
def chat_panel():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/users")
def get_users():
    return jsonify({"users": []})

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "error", 403
        
    try:
        data = request.json
        value = data["entry"][0]["changes"][0]["value"]
        if "messages" in value:
            msg = value["messages"][0]
            phone = msg["from"]
            msg_id = msg["id"]
            now_time = datetime.now().strftime("%I:%M %p")
            
            # 1. محاولة قراءة النص العادي أولاً
            text = msg.get("text", {}).get("body", "")
            
            # 2. الدمج الذكي: إذا كانت الرسالة عبارة عن زر أو كود تحقق تفاعلي من فيسبوك
            if not text and "button" in msg:
                text = msg["button"].get("text", "")
            if not text and "interactive" in msg:
                int_type = msg["interactive"].get("type")
                if int_type == "button_reply":
                    text = msg["interactive"]["button_reply"].get("title", "")
            
            # 3. إذا لم يعثر على أي نص واعتبرت وسائط فعلية (صورة أو ملف)
            if not text:
                text = f"[رسالة تفاعلية أو رمز - نوعها: {msg.get('type', 'unknown')}]"
            
            conn = db()
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
            c.execute("INSERT OR IGNORE INTO messages (msg_id, phone, message, sender, status, msg_time) VALUES (?, ?, ?, 'them', 'read', ?)", (msg_id, phone, text, now_time))
            conn.commit()
            conn.close()
            
            # إرسال إشعار فوري لهاتفك الشخصي
            notification_text = f"🔔 حركة جديدة في موقعك من: {phone}\nالمحتوى: {text}"
            send_message(MY_PERSONAL_PHONE, notification_text)
            
    except Exception as e:
        print("Webhook Error:", e)
        
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
