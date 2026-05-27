from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
import requests
import sqlite3

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

VERIFY_TOKEN = "mytoken123"
PHONE_NUMBER_ID = "1156014094256129"
ACCESS_TOKEN = "EAAjZAQBZBWhDQBRv60Nz1iH9ZAZCJcHZCAujRZAgmbS4hbqZCgcJjMW3wvRQMJiCJrAndojed3ii4qlRnOYPLBW0gQoBFgVPYuZAnOdaeS4Q0Vemprx2IuXgvwcQvVEqZBWRLIipy71RFRGZARO4QZAPzq5X1bzdDnBfiZBwUV0Vnx6437wCnDP4bZC9Uh5JqcXd6yTv9kJ2ZBrHPrUNM9xTKrcI33qRJakyjStuozrdaQHp9GR6f3SzUxdUjQf4q1tL5AqKMPUCTmIbNfspZBhDDw2bfut"

# ================= DB =================
def db():
    conn = sqlite3.connect("chat.db")
    return conn

# ================= UI =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= WEBHOOK =================
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json

        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]

        phone = msg["from"]
        text = msg["text"]["body"]

        conn = db()
        c = conn.cursor()
        c.execute("INSERT INTO messages (phone, message, direction) VALUES (?,?,?)",
                  (phone, text, "in"))
        conn.commit()
        conn.close()

        # 🔥 إرسال مباشر للواجهة
        socketio.emit("new_message", {
            "phone": phone,
            "message": text,
            "direction": "in"
        })

    except Exception as e:
        print("ERR:", e)

    return "ok", 200

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

    requests.post(url, headers=headers, json=data)

    # 🔥 إرسال مباشر للواجهة
    socketio.emit("new_message", {
        "phone": phone,
        "message": message,
        "direction": "out"
    })

# ================= SEND API =================
@app.route("/send", methods=["POST"])
def send():
    data = request.json

    phone = data["phone"]
    message = data["message"]

    send_message(phone, message)

    return jsonify({"ok": True})

# ================= RUN =================
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
