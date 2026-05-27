from flask import Flask, request, jsonify
import requests
import sqlite3

app = Flask(__name__)

# =========================
# 🔐 إعدادات واتساب
# =========================
VERIFY_TOKEN = "mytoken123"
PHONE_NUMBER_ID = "1156014094256129"
ACCESS_TOKEN = "EAAjZAQBZBWhDQBRvhhf97owU0uUDcmJkqcsNbBPZC7fnCXRw7q57njtrShlZCQN9RCYZB5TZCmL0viOWTxNcdaYDP4p8L8LOSDqDryVba06ZCaNjZCXyBOwCoZBLkHzzg6ZADZBX8I2ZC1XoOyPGAV5VITC5mBPXJTpiN2XHh0VZBTNQKs62d1wqg5ZAos1ZCSJx5yaVOiCiFLsw39QpLBZCnRxk6YtusnTw8ZA2CJHbZCF8BCLSz2rHsoqM1kMzpNBsf9ZAceXZAp3RlR8sEPziiND0HVhtZCZCtiBwZDZD"

# =========================
# 🗄️ قاعدة البيانات
# =========================
def init_db():
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
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

# =========================
# 🟢 إرسال رسالة
# =========================
def send_message(to, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }

    return requests.post(url, headers=headers, json=data).text


# =========================
# 🟢 Webhook Verification (GET)
# =========================
@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "error", 403


# =========================
# 🟢 استقبال الرسائل (POST)
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json

        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        phone = msg["from"]
        text = msg["text"]["body"]

        conn = sqlite3.connect("chat.db")
        c = conn.cursor()
        c.execute("INSERT INTO messages (phone, message) VALUES (?,?)", (phone, text))
        conn.commit()
        conn.close()

        print("New message:", phone, text)

    except Exception as e:
        print("Error:", e)

    return "ok", 200


# =========================
# 🟢 عرض الرسائل (API)
# =========================
@app.route("/messages")
def messages():
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("SELECT phone, message FROM messages ORDER BY id DESC")
    data = c.fetchall()
    conn.close()

    return jsonify(data)


# =========================
# 🟢 إرسال رسالة من المتصفح
# =========================
@app.route("/send", methods=["POST"])
def send():
    phone = request.json.get("phone")
    message = request.json.get("message")

    result = send_message(phone, message)

    return jsonify({"status": "sent", "result": result})


# =========================
# 🟢 الصفحة الرئيسية
# =========================
@app.route("/")
def home():
    return "WhatsApp Panel is Running 🚀"


# =========================
# 🟢 تشغيل السيرفر
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
