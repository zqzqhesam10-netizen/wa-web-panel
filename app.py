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
        message TEXT
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
        "text": {
            "body": message
        }
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

# ================= SEND MESSAGE (FIXED) =================

@app.route("/send", methods=["POST"])
def send():

    phone = request.form["phone"]
    message = request.form["message"]

    # إرسال واتساب
    send_message(phone, message)

    conn = db()
    c = conn.cursor()

    c.execute("""
    INSERT INTO messages (phone, message)
    VALUES (?,?)
    """, (phone, message))

    conn.commit()
    conn.close()

    # مهم: رجّع JSON وليس صفحة
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
        INSERT INTO messages (phone, message)
        VALUES (?,?)
        """, (phone, text))

        conn.commit()
        conn.close()

    except:
        pass

    return "ok", 200

# ================= RUN =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
