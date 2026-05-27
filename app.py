from flask import Flask, render_template, request
import sqlite3
import requests

app = Flask(__name__)

# ================= WHATSAPP =================

ACCESS_TOKEN = "EAAjZAQBZBWhDQBRv60Nz1iH9ZAZCJcHZCAujRZAgmbS4hbqZCgcJjMW3wvRQMJiCJrAndojed3ii4qlRnOYPLBW0gQoBFgVPYuZAnOdaeS4Q0Vemprx2IuXgvwcQvVEqZBWRLIipy71RFRGZARO4QZAPzq5X1bzdDnBfiZBwUV0Vnx6437wCnDP4bZC9Uh5JqcXd6yTv9kJ2ZBrHPrUNM9xTKrcI33qRJakyjStuozrdaQHp9GR6f3SzUxdUjQf4q1tL5AqKMPUCTmIbNfspZBhDDw2bfut"
PHONE_NUMBER_ID = "1156014094256129"
VERIFY_TOKEN = "mytoken123"

ADMIN_PHONE = "967780331040"  # رقمك أنت

# ================= DB =================

def db():
    conn = sqlite3.connect("chat.db")
    conn.row_factory = sqlite3.Row
    return conn

# ================= INIT =================

def init_db():

    conn = db()
    c = conn.cursor()

    # users
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        phone TEXT PRIMARY KEY
    )
    """)

    # content
    c.execute("""
    CREATE TABLE IF NOT EXISTS content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        category TEXT,
        image TEXT
    )
    """)

    # messages
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

# ================= WHATSAPP SEND =================

def send_message(phone, text, image=None):

    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    if image:

        data = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "image",
            "image": {
                "link": image,
                "caption": text
            }
        }

    else:

        data = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {
                "body": text
            }
        }

    requests.post(url, headers=headers, json=data)

# ================= BROADCAST =================

def broadcast(title, category, image):

    conn = db()
    c = conn.cursor()

    c.execute("SELECT phone FROM users")
    users = c.fetchall()

    msg = f"""🔥 New Release

🎬 {title}
📺 {category}
"""

    # لكل المستخدمين
    for u in users:
        send_message(u["phone"], msg, image)

    # لك أنت
    send_message(ADMIN_PHONE, "📢 محتوى جديد:\n" + title, image)

    conn.close()

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

# ================= SEND MESSAGE =================

@app.route("/send", methods=["POST"])
def send():

    phone = request.form["phone"]
    message = request.form["message"]

    # إرسال واتساب
    send_message(phone, message)

    # حفظ الرسالة
    conn = db()
    c = conn.cursor()

    c.execute("""
    INSERT INTO messages (phone, message)
    VALUES (?,?)
    """, (phone, message))

    conn.commit()
    conn.close()

    # يرجع نفس الصفحة (بدون sent)
    return render_template("chat.html")

# ================= ADD CONTENT =================

@app.route("/add", methods=["POST"])
def add():

    title = request.form["title"]
    category = request.form["category"]
    image = request.form["image"]

    conn = db()
    c = conn.cursor()

    c.execute("""
    INSERT INTO content (title, category, image)
    VALUES (?,?,?)
    """, (title, category, image))

    conn.commit()
    conn.close()

    # 🔥 إشعارات تلقائية
    broadcast(title, category, image)

    return "ok"

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

# ================= START =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
