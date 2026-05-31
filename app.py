from flask import Flask, request, render_template, jsonify
import sqlite3
import requests
import os

app = Flask(__name__)

# ================= CONFIG =================
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "61590587787681"
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
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        msg_id TEXT UNIQUE,
        phone TEXT,
        message TEXT,
        sender TEXT DEFAULT 'them',
        status TEXT DEFAULT 'sent',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ================= SEND MESSAGE =================
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
        res = r.json()
        print("SEND RESPONSE:", res)
        if "messages" in res:
            return res["messages"][0]["id"]
    except Exception as e:
        print("Send Error:", e)
    return None

# ================= ROUTES =================
@app.route("/")
def home():
    return "WhatsApp Panel is Running 🚀"

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
    # إرجاع البيانات في مصفوفة مباشرة لتتوافق مع معالجة فرونت اند النظيفة
    return jsonify([dict(u) for u in users])

@app.route("/api/add_user", methods=["POST"])
def add_user():
    phone = request.form.get("phone", "").strip()
    if not phone:
        return jsonify({"status": "error", "message": "الرقم مطلوب"}), 400
    conn = db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "phone": phone})

@app.route("/api/broadcast", methods=["POST"])
def broadcast():
    message = request.form.get("message", "").strip()
    if not message:
        return jsonify({"status": "error", "message": "الرسالة فارغة"}), 400

    conn = db()
    c = conn.cursor()
    c.execute("SELECT phone FROM users")
    users = c.fetchall()

    sent_count = 0
    for user in users:
        phone = user["phone"]
        wamid = send_message(phone, message)
        c.execute("""
        INSERT OR IGNORE INTO messages (msg_id, phone, message, sender, status)
        VALUES (?, ?, ?, 'me', 'sent')
        """, (wamid, phone, message))
        sent_count += 1
        
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "sent_count": sent_count})

@app.route("/messages/<phone>")
def messages(phone):
    conn = db()
    c = conn.cursor()
    c.execute("""
    SELECT id, msg_id, phone, message, sender, status, 
           strftime('%H:%M', datetime(timestamp, 'localtime')) as msg_time 
    FROM messages 
    WHERE phone=? 
    ORDER BY id ASC
    """, (phone,))
    msgs = c.fetchall()
    conn.close()
    return jsonify({"messages": [dict(m) for m in msgs]})

@app.route("/send", methods=["POST"])
def send():
    phone = request.form["phone"]
    message = request.form["message"]
    wamid = send_message(phone, message)

    conn = db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
    c.execute("""
    INSERT INTO messages (msg_id, phone, message, sender, status)
    VALUES (?, ?, ?, 'me', 'sent')
    """, (wamid, phone, message))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# ================= WEBHOOK =================
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        return "error", 403

    try:
        data = request.json
        value = data["entry"][0]["changes"][0]["value"]
        conn = db()
        c = conn.cursor()

        if "statuses" in value:
            status = value["statuses"][0]
            c.execute("UPDATE messages SET status=? WHERE msg_id=?", (status["status"], status["id"]))
            conn.commit()

        elif "messages" in value:
            msg = value["messages"][0]
            phone = msg["from"]
            text = msg.get("text", {}).get("body", "[وسائط]")
            msg_id = msg["id"]

            c.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
            c.execute("""
            INSERT OR IGNORE INTO messages (msg_id, phone, message, sender, status)
            VALUES (?, ?, ?, 'them', 'read')
            """, (msg_id, phone, text))
            conn.commit()
        conn.close()
    except Exception as e:
        print("Webhook Error:", e)

    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
