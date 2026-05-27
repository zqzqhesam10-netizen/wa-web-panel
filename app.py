from flask import Flask, render_template, request
import sqlite3
import requests

app = Flask(__name__)

# ================= WHATSAPP =================

ACCESS_TOKEN = "EAAjZAQBZBWhDQBRv60Nz1iH9ZAZCJcHZCAujRZAgmbS4hbqZCgcJjMW3wvRQMJiCJrAndojed3ii4qlRnOYPLBW0gQoBFgVPYuZAnOdaeS4Q0Vemprx2IuXgvwcQvVEqZBWRLIipy71RFRGZARO4QZAPzq5X1bzdDnBfiZBwUV0Vnx6437wCnDP4bZC9Uh5JqcXd6yTv9kJ2ZBrHPrUNM9xTKrcI33qRJakyjStuozrdaQHp9GR6f3SzUxdUjQf4q1tL5AqKMPUCTmIbNfspZBhDDw2bfut"
PHONE_NUMBER_ID = "1156014094256129"
VERIFY_TOKEN = "mytoken123"

# ================= DATABASE =================

def db():

    conn = sqlite3.connect("chat.db")
    conn.row_factory = sqlite3.Row

    return conn

# ================= INIT DB =================

def init_db():

    conn = db()
    c = conn.cursor()

    # المستخدمين
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        phone TEXT PRIMARY KEY
    )
    """)

    # المحتوى
    c.execute("""
    CREATE TABLE IF NOT EXISTS content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        category TEXT,
        image TEXT
    )
    """)

    # رسائل
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        message TEXT
    )
    """)

    conn.commit()

    # بيانات تجريبية
    c.execute("SELECT * FROM content")

    if not c.fetchone():

        c.execute("""
        INSERT INTO content
        (title, category, image)

        VALUES (?,?,?)
        """, (

            "Attack on Titan",
            "Anime",
            "https://upload.wikimedia.org/wikipedia/en/7/70/Attack_on_Titan_S1_DVD.jpg"

        ))

        c.execute("""
        INSERT INTO content
        (title, category, image)

        VALUES (?,?,?)
        """, (

            "Breaking Bad",
            "Series",
            "https://upload.wikimedia.org/wikipedia/en/6/61/Breaking_Bad_title_card.png"

        ))

        conn.commit()

    conn.close()

init_db()

# ================= SEND WHATSAPP =================

def send_message(phone, text):

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
            "body": text
        }
    }

    requests.post(url, headers=headers, json=data)

# ================= HOME =================

@app.route("/")
def home():

    conn = db()
    c = conn.cursor()

    c.execute("SELECT * FROM content ORDER BY id DESC")

    items = c.fetchall()

    conn.close()

    return render_template("index.html", items=items)

# ================= CHAT PAGE =================

@app.route("/chat")
def chat():

    conn = db()
    c = conn.cursor()

    c.execute("SELECT * FROM users")

    users = c.fetchall()

    conn.close()

    return render_template("chat.html", users=users)

# ================= SEND FROM PANEL =================

@app.route("/send", methods=["POST"])
def send():

    phone = request.form["phone"]
    message = request.form["message"]

    send_message(phone, message)

    conn = db()
    c = conn.cursor()

    c.execute("""
    INSERT INTO messages (phone, message)
    VALUES (?,?)
    """, (phone, message))

    conn.commit()
    conn.close()

    # يرجعك للشات بدل sent
    return render_template("chat.html")

# ================= WEBHOOK =================

@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    # VERIFY
    if request.method == "GET":

        token = request.args.get("hub.verify_token")

        if token == VERIFY_TOKEN:
            return request.args.get("hub.challenge")

        return "error", 403

    # RECEIVE
    try:

        data = request.json

        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]

        phone = msg["from"]

        text = msg["text"]["body"]

        conn = db()
        c = conn.cursor()

        # حفظ المستخدم
        c.execute("""
        INSERT OR IGNORE INTO users
        (phone)

        VALUES (?)
        """, (phone,))

        # حفظ الرسالة
        c.execute("""
        INSERT INTO messages
        (phone, message)

        VALUES (?,?)
        """, (phone, text))

        conn.commit()
        conn.close()

    except Exception as e:
        print(e)

    return "ok", 200

# ================= START =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
