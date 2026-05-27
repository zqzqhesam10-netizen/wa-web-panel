from flask import Flask, request, jsonify, render_template
import requests
import sqlite3
from datetime import datetime

app = Flask(__name__)

VERIFY_TOKEN = "mytoken123"
PHONE_NUMBER_ID = "1156014094256129"
ACCESS_TOKEN = "EAAjZAQBZBWhDQBRv60Nz1iH9ZAZCJcHZCAujRZAgmbS4hbqZCgcJjMW3wvRQMJiCJrAndojed3ii4qlRnOYPLBW0gQoBFgVPYuZAnOdaeS4Q0Vemprx2IuXgvwcQvVEqZBWRLIipy71RFRGZARO4QZAPzq5X1bzdDnBfiZBwUV0Vnx6437wCnDP4bZC9Uh5JqcXd6yTv9kJ2ZBrHPrUNM9xTKrcI33qRJakyjStuozrdaQHp9GR6f3SzUxdUjQf4q1tL5AqKMPUCTmIbNfspZBhDDw2bfut"

# ================= DB =================
def db():
    conn = sqlite3.connect("chat.db")
    conn.row_factory = sqlite3.Row
    return conn

def init():
    conn = db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        message TEXT,
        direction TEXT,
        time TEXT
    )
    """)

    conn.commit()
    conn.close()

init()

# ================= UI =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= VERIFY =================
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "error", 403

# ================= RECEIVE =================
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]

        phone = msg["from"]
        text = msg["text"]["body"]

        conn = db()
        c = conn.cursor()

        c.execute("""
        INSERT INTO messages (phone, message, direction, time)
        VALUES (?, ?, 'in', ?)
        """, (phone, text, str(datetime.now())))

        conn.commit()
        conn.close()

    except Exception as e:
        print("ERR:", e)

    return "ok"

# ================= SEND =================
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

    return requests.post(url, headers=headers, json=data).text

@app.route("/send", methods=["POST"])
def send():
    phone = request.json["phone"]
    message = request.json["message"]

    send_message(phone, message)

    conn = db()
    c = conn.cursor()

    c.execute("""
    INSERT INTO messages (phone, message, direction, time)
    VALUES (?, ?, 'out', ?)
    """, (phone, message, str(datetime.now())))

    conn.commit()
    conn.close()

    return jsonify({"ok": True})

# ================= GET CHATS =================
@app.route("/messages")
def messages():
    conn = db()
    c = conn.cursor()

    c.execute("SELECT * FROM messages ORDER BY id DESC")
    rows = c.fetchall()

    conn.close()

    return jsonify([dict(r) for r in rows])

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
