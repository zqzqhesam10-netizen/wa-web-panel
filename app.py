from flask import Flask, request, jsonify, render_template_string
import sqlite3
import requests
import os
import threading
import time
from datetime import datetime
from bs4 import BeautifulSoup

app = Flask(__name__)

# ================= CONFIG =================
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "1171944939327803"
VERIFY_TOKEN = "mytoken123"

# ================= DB =================
def db():
    conn = sqlite3.connect("chat.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (phone TEXT PRIMARY KEY)")
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        msg_id TEXT UNIQUE,
        phone TEXT,
        message TEXT,
        sender TEXT DEFAULT 'them',
        status TEXT DEFAULT 'sent',
        msg_time TEXT,
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
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": clean_phone, "type": "text", "text": {"body": message}}
    try:
        r = requests.post(url, headers=headers, json=data)
        res = r.json()
        return res["messages"][0]["id"] if "messages" in res else None
    except Exception as e: print("Send Error:", e)
    return None

# ================= MONITORING (المراقب التلقائي) =================
def monitor_site():
    last_link = ""
    while True:
        try:
            response = requests.get("https://web53118x.faselhdx.bid/most_recent", headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.text, 'html.parser')
            item = soup.find('a', class_='post-link')
            if item and item.get('href'):
                current_link = item['href']
                if current_link != last_link:
                    last_link = current_link
                    conn = db()
                    users = conn.execute("SELECT phone FROM users").fetchall()
                    for user in users:
                        send_message(user["phone"], f"📢 تحديث جديد من الموقع:\n{current_link}")
                    conn.close()
        except Exception as e: print("Monitor Error:", e)
        time.sleep(300) # فحص كل 5 دقائق

threading.Thread(target=monitor_site, daemon=True).start()

# ================= HTML & ROUTES =================
# تم دمج الواجهة الأصلية والمسارات (Routes) كما هي في طلبك السابق
# تأكد فقط من إضافة مكتبة BeautifulSoup في ملف الـ requirements.txt
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>واتساب ويب - لوحة التحكم</title>
    <style>
        * { box-sizing: border-box; }
        body { margin: 0; font-family: sans-serif; display: flex; height: 100vh; background: #dadbd3; }
        .sidebar { width: 380px; background: #fff; border-left: 1px solid #ccc; display: flex; flex-direction: column; }
        .chat-area { flex: 1; display: flex; flex-direction: column; background: #efeae2; }
        .messages-container { flex: 1; overflow-y: auto; padding: 20px; }
        .msg-row { margin-bottom: 10px; display: flex; }
        .me { justify-content: flex-start; }
        .them { justify-content: flex-end; }
        .bubble { padding: 10px; border-radius: 8px; background: #fff; }
        .modal { display: none; position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.5); justify-content:center; align-items:center; }
        .modal-content { background: #fff; padding: 20px; width: 300px; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div style="padding:15px;">
            <button onclick="document.getElementById('broadcastModal').style.display='flex'">📢 بث للكل</button>
            <button onclick="document.getElementById('newChatModal').style.display='flex'">➕ رقم جديد</button>
        </div>
        <div class="user-list" id="userList"></div>
    </div>
    <div class="chat-area" id="chatArea" style="display: none;">
        <div class="messages-container" id="messagesContainer"></div>
        <form onsubmit="sendMessage(event)" style="padding:10px;">
            <input type="hidden" id="activePhone">
            <input type="text" id="messageInput" placeholder="اكتب رسالة..." style="width:80%; padding:10px;">
            <button type="submit">إرسال</button>
        </form>
    </div>
    <div id="broadcastModal" class="modal"><div class="modal-content"><textarea id="broadcastMessageInput" style="width:100%"></textarea><button onclick="sendBroadcast()">إرسال للجميع</button></div></div>
    <div id="newChatModal" class="modal"><div class="modal-content"><input id="newPhoneInput" style="width:100%"><button onclick="createNewChat()">إضافة</button></div></div>
    <script>
        function openChat(phone) { document.getElementById('activePhone').value = phone; document.getElementById('chatArea').style.display = 'flex'; fetchMessages(phone); }
        function fetchMessages(phone) {
            fetch('/messages/'+phone).then(r=>r.json()).then(d=>{
                document.getElementById('messagesContainer').innerHTML = d.messages.map(m=>`<div class="msg-row ${m.sender=='me'?'me':'them'}"><div class="bubble">${m.message}</div></div>`).join('');
            });
        }
        function sendMessage(e) {
            e.preventDefault();
            const p = document.getElementById('activePhone').value;
            const m = document.getElementById('messageInput').value;
            fetch('/send', {method:'POST', body: new URLSearchParams({phone:p, message:m})}).then(()=>fetchMessages(p));
        }
        function sendBroadcast() {
            const m = document.getElementById('broadcastMessageInput').value;
            fetch('/api/broadcast', {method:'POST', body: new URLSearchParams({message:m})}).then(()=>location.reload());
        }
        function createNewChat() {
            const p = document.getElementById('newPhoneInput').value;
            fetch('/api/add_user', {method:'POST', body: new URLSearchParams({phone:p})}).then(()=>location.reload());
        }
        fetch('/api/users').then(r=>r.json()).then(d=>{
            document.getElementById('userList').innerHTML = d.users.map(u=>`<div onclick="openChat('${u.phone}')" style="padding:15px; border-bottom:1px solid #eee; cursor:pointer">${u.phone}</div>`).join('');
        });
    </script>
</body>
</html>
"""

@app.route("/")
def index(): return render_template_string(HTML_TEMPLATE)

@app.route("/api/users")
def get_users():
    conn = db()
    return jsonify({"users": [dict(u) for u in conn.execute("SELECT * FROM users").fetchall()]})

@app.route("/api/add_user", methods=["POST"])
def add_user():
    conn = db()
    conn.execute("INSERT OR IGNORE INTO users VALUES (?)", (request.form.get("phone"),))
    conn.commit()
    return jsonify({"status": "ok"})

@app.route("/api/broadcast", methods=["POST"])
def broadcast():
    msg = request.form.get("message")
    for u in db().execute("SELECT phone FROM users").fetchall(): send_message(u["phone"], msg)
    return jsonify({"status": "ok"})

@app.route("/messages/<phone>")
def get_msgs(phone):
    conn = db()
    return jsonify({"messages": [dict(m) for m in conn.execute("SELECT * FROM messages WHERE phone=? ORDER BY id ASC", (phone,)).fetchall()]})

@app.route("/send", methods=["POST"])
def send():
    p, m = request.form["phone"], request.form["message"]
    wamid = send_message(p, m)
    conn = db()
    conn.execute("INSERT INTO messages (msg_id, phone, message, sender) VALUES (?, ?, ?, 'me')", (wamid, p, m))
    conn.commit()
    return jsonify({"status": "ok"})

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET": return request.args.get("hub.challenge")
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
