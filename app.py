from flask import Flask, render_template, request
import requests
import sqlite3

app = Flask(__name__)

TOKEN = "EAAjZAQBZBWhDQBRvhhf97owU0uUDcmJkqcsNbBPZC7fnCXRw7q57njtrShlZCQN9RCYZB5TZCmL0viOWTxNcdaYDP4p8L8LOSDqDryVba06ZCaNjZCXyBOwCoZBLkHzzg6ZADZBX8I2ZC1XoOyPGAV5VITC5mBPXJTpiN2XHh0VZBTNQKs62d1wqg5ZAos1ZCSJx5yaVOiCiFLsw39QpLBZCnRxk6YtusnTw8ZA2CJHbZCF8BCLSz2rHsoqM1kMzpNBsf9ZAceXZAp3RlR8sEPziiND0HVhtZCZCtiBwZDZD"
PHONE_NUMBER_ID = "1156014094256129"

# DB
def db():
    return sqlite3.connect("chat.db")

def init():
    conn = db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS msgs (phone TEXT, msg TEXT)")
    conn.commit()
    conn.close()

init()

# SEND MESSAGE
def send(to, text):
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }

    requests.post(url, headers=headers, json=data)

# WEBHOOK
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        phone = msg["from"]
        text = msg["text"]["body"]

        conn = db()
        c = conn.cursor()
        c.execute("INSERT INTO msgs VALUES (?,?)", (phone, text))
        conn.commit()
        conn.close()
    except:
        pass

    return "ok"

# UI
@app.route("/")
def home():
    conn = db()
    c = conn.cursor()

    c.execute("SELECT DISTINCT phone FROM msgs")
    contacts = c.fetchall()

    c.execute("SELECT phone,msg FROM msgs ORDER BY rowid DESC LIMIT 20")
    messages = c.fetchall()

    return render_template("index.html", contacts=contacts, messages=messages)

# SEND FROM UI
@app.route("/send", methods=["POST"])
def send_msg():
    phone = request.form["phone"]
    msg = request.form["msg"]

    send(phone, msg)

    conn = db()
    c = conn.cursor()
    c.execute("INSERT INTO msgs VALUES (?,?)", (phone, msg))
    conn.commit()
    conn.close()

    return home()

app.run(host="0.0.0.0", port=5000)