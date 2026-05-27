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
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        message TEXT,
        sender TEXT DEFAULT 'them' 
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
    requests.post(url, headers=headers, json=data)

# ================= CHAT PAGE =================
@app.route("/chat")
def chat():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return render_template("chat.html", users=users)

# ================= GET USERS (API) =================
@app.route("/api/users")
def get_users():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return jsonify({"users": [dict(u) for u in users]})

# ================= ADD NEW USER MANUALLY =================
# هذا المسار يسمح لك بإضافة رقم هاتف جديد من لوحة التحكم مباشرة دون تكرار
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

# ================= GET MESSAGES =================
@app.route("/messages/<phone>")
def messages(phone):
    conn = db()
    c = conn.cursor()
    c.execute("""
    SELECT * FROM messages
    WHERE phone=?
    ORDER BY id ASC
    """, (phone,))
    msgs = c.fetchall()
    conn.close()
    return jsonify({"messages": [dict(m) for m in msgs]})

# ================= SEND MESSAGE =================
@app.route("/send", methods=["POST"])
def send():
    phone = request.form["phone"]
    message = request.form["message"]

    send_message(phone, message)

    conn = db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
    c.execute("""
    INSERT INTO messages (phone, message, sender)
    VALUES (?, ?, 'me')
    """, (phone, message))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "message": message})

# ================= WEBHOOK =================
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "error", 403

    try:
        data = request.json
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        phone = msg["from"]
        text = msg["text"]["body"]

        conn = db()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
        c.execute("""
        INSERT INTO messages (phone, message, sender)
        VALUES (?, ?, 'them')
        """, (phone, text))
        conn.commit()
        conn.close()
    except:
        pass

    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
