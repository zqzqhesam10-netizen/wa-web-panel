from flask import Flask, request, render_template, jsonify
import sqlite3
import requests

app = Flask(__name__)

# ================= CONFIG =================
ACCESS_TOKEN = "EAAjZAQBZBWhDQBRv60Nz1iH9ZAZCJcHZCAujRZAgmbS4hbqZCgcJjMW3wvRQMJiCJrAndojed3ii4qlRnOYPLBW0gQoBFgVPYuZAnOdaeS4Q0Vemprx2IuXgvwcQvVEqZBWRLIipy71RFRGZARO4QZAPzq5X1bzdDnBfiZBwUV0Vnx6437wCnDP4bZC9Uh5JqcXd6yTv9kJ2ZBrHPrUNM9xTKrcI33qRJakyjStuozrdaQHp9GR6f3SzUxdUjQf4q1tL5AqKMPUCTmIbNfspZBhDDw2bfut"
PHONE_NUMBER_ID = "1156014094256129"
VERIFY_TOKEN = "mytoken123"

# ================= DB =================
def db():
    conn = sqlite3.connect("chat.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        phone TEXT PRIMARY KEY
    )
    """)
    # إضافة حقلين جديدين: msg_id (لمعرفة الرسالة وتحديث حالتها) و status (لحالة التسليم والقراءة)
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        msg_id TEXT UNIQUE,
        phone TEXT,
        message TEXT,
        sender TEXT DEFAULT 'them',
        status TEXT DEFAULT 'sent'
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ================= SEND WHATSAPP =================
def send_message(phone, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message}
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        res_data = response.json()
        # إرجاع معرّف الرسالة القادم من فيسبوك لربطه بالحالة لاحقاً
        if "messages" in res_data:
            return res_data["messages"][0]["id"]
    except Exception as e:
        print(f"Error sending message: {e}")
    return None

# ================= ROUTES =================
@app.route("/chat")
def chat():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return render_template("chat.html", users=users)

@app.route("/api/users")
def get_users():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return jsonify({"users": [dict(u) for u in users]})

@app.route("/messages/<phone>")
def messages(phone):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM messages WHERE phone=? ORDER BY id ASC", (phone,))
    msgs = c.fetchall()
    conn.close()
    return jsonify({"messages": [dict(m) for m in msgs]})

@app.route("/send", methods=["POST"])
def send():
    phone = request.form["phone"]
    message = request.form["message"]

    # إرسال الرسالة وجلب الـ ID الخاص بها من فيسبوك
    wamid = send_message(phone, message)

    conn = db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
    
    # حفظ الرسالة مع معرّفها الخاص لمراقبة حالتها
    c.execute("""
    INSERT INTO messages (msg_id, phone, message, sender, status)
    VALUES (?, ?, ?, 'me', 'sent')
    """, (wamid, phone, message))
    
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "message": message})

# ================= WEBHOOK MUPDATING STATUS =================
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "error", 403

    try:
        data = request.json
        value = data["entry"][0]["changes"][0]["value"]

        conn = db()
        c = conn.cursor()

        # 1. إذا كان التحديث عبارة عن تغيير في حالة الرسالة (استلم / قرأ)
        if "statuses" in value:
            status_obj = value["statuses"][0]
            msg_id = status_obj["id"]      # معرف الرسالة
            status_type = status_obj["status"]  # قد تكون delivered أو read

            # تحديث حالة الرسالة في قاعدة البيانات
            c.execute("""
            UPDATE messages SET status = ? WHERE msg_id = ?
            """, (status_type, msg_id))
            conn.commit()

        # 2. إذا كان التحديث عبارة عن رسالة جديدة قادمة من العميل
        elif "messages" in value:
            msg = value["messages"][0]
            phone = msg["from"]
            text = msg["text"]["body"]
            msg_id = msg["id"]

            c.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
            c.execute("""
            INSERT OR IGNORE INTO messages (msg_id, phone, message, sender, status)
            VALUES (?, ?, ?, 'them', 'read')
            """, (msg_id, phone, text, ))
            conn.commit()

        conn.close()
    except Exception as e:
        print("Webhook Error:", e)

    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
