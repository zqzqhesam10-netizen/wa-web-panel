from flask import Flask, request, render_template
import sqlite3
import requests
from bs4 import BeautifulSoup

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
        link TEXT UNIQUE,
        category TEXT,
        image TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= SEND WHATSAPP =================

def send_message(phone, text, image_url=None):

    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # صورة + نص
    if image_url:

        data = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "image",
            "image": {
                "link": image_url,
                "caption": text
            }
        }

    # نص فقط
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

    message = f"""🔥 حلقة جديدة

🎬 {title}
📺 {category}
"""

    for u in users:
        send_message(u["phone"], message, image)

    conn.close()

# ================= SAVE CONTENT =================

def save_content(title, link, category, image):

    conn = db()
    c = conn.cursor()

    # منع التكرار
    c.execute("SELECT link FROM content WHERE link=?", (link,))
    exists = c.fetchone()

    if not exists:

        c.execute("""
        INSERT INTO content (title, link, category, image)
        VALUES (?,?,?,?)
        """, (title, link, category, image))

        conn.commit()

        # 🔥 إرسال تلقائي
        broadcast(title, category, image)

    conn.close()

# ================= SCRAPER =================

def scrape(url, category):

    try:

        r = requests.get(url, timeout=15)

        soup = BeautifulSoup(r.text, "html.parser")

        # أول عنصر
        item = soup.select_one("a")

        # أول صورة
        img = soup.select_one("img")

        if item:

            title = item.text.strip()
            link = item.get("href")

            image = None

            if img:
                image = img.get("src")

            # صورة افتراضية
            if not image:
                image = "https://via.placeholder.com/500x700.png?text=Netflix"

            if title and link:
                save_content(title, link, category, image)

    except Exception as e:
        print("SCRAPER ERROR:", e)

# ================= SOURCES =================

SOURCES = [

    {
        "url": "https://w1.anime4up.rest/episode/",
        "category": "Anime"
    },

    {
        "url": "https://m.asd.ink/category/foreign-series-7/",
        "category": "Foreign Series"
    },

    {
        "url": "https://5tv.lol/new-episodes/",
        "category": "Asian Series"
    },

    {
        "url": "https://m.asd.ink/category/wwe-shows-1/",
        "category": "WWE"
    },

    {
        "url": "https://m.asd.ink/movies-3/",
        "category": "Movies"
    },

    {
        "url": "https://m.asd.ink/category/turkish-series-2/",
        "category": "Turkish Series"
    },

    {
        "url": "https://m.asd.ink/category/arabic-series-14/",
        "category": "Arabic Series"
    },

    {
        "url": "https://akwam.it/series?section=0&category=71&rating=0&year=0&language=0&formats=0&quality=0",
        "category": "Dubbed Series"
    }

]

# ================= RUN SCRAPER =================

@app.route("/run")
def run():

    for s in SOURCES:
        scrape(s["url"], s["category"])

    return {"status": "done"}

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

        conn = db()
        c = conn.cursor()

        # حفظ المستخدم
        c.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))

        conn.commit()
        conn.close()

    except Exception as e:
        print("WEBHOOK ERROR:", e)

    return "ok", 200

# ================= HOME =================

@app.route("/")
def home():

    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT * FROM content
    ORDER BY id DESC
    """)

    items = c.fetchall()

    conn.close()

    
    return render_template("index.html", items=items)
    
    @app.route("/chat")
def chat():

    conn = db()
    c = conn.cursor()

    c.execute("SELECT * FROM users")

    users = c.fetchall()

    conn.close()

    return render_template("chat.html", users=users)
    
    html = """
    <html>
    <head>
    <title>Netflix Clone</title>

    <style>

    body{
        background:#111;
        color:white;
        font-family:Arial;
    }

    .card{
        width:220px;
        background:#222;
        display:inline-block;
        margin:10px;
        border-radius:10px;
        overflow:hidden;
    }

    img{
        width:100%;
        height:320px;
        object-fit:cover;
    }

    .info{
        padding:10px;
    }

    </style>
    </head>
    <body>

    <h1>🎬 Netflix Clone</h1>
    """

    for i in items:

        html += f"""
        <div class="card">

            <img src="{i['image']}">

            <div class="info">
                <h3>{i['title']}</h3>
                <p>{i['category']}</p>
            </div>

        </div>
        """

    html += "</body></html>"

    conn.close()

    return html

# ================= START =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
