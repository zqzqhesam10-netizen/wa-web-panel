from flask import Flask, request, jsonify, render_template_string
import sqlite3
import requests
import os
from datetime import datetime

app = Flask(__name__)

# ================= CONFIG =================
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "61590587787681"
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
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": clean_phone,
        "type": "text",
        "text": {"body": message}
    }
    try:
        r = requests.post(url, headers=headers, json=data)
        res = r.json()
        print("SEND RESPONSE:", res)
        if "messages" in res:
            return res["messages"][0]["id"]
    except Exception as e:
        print("Send Error:", e)
    return None

# ================= HTML CODE (WITH TEXT BUTTONS) =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>واتساب ويب - لوحة التحكم</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        body { display: flex; height: 100vh; background-color: #dadbd3; overflow: hidden; }
        
        .sidebar { width: 380px; min-width: 380px; background: #fff; display: flex; flex-direction: column; border-left: 1px solid #e9edef; }
        
        .sidebar-header { height: 60px; background: #f0f2f5; display: flex; align-items: center; padding: 0 16px; justify-content: space-between; direction: rtl; }
        .header-right-side { display: flex; align-items: center; gap: 10px; }
        .avatar { width: 40px; height: 40px; background: #dfe5e7; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #54656f; font-weight: bold; font-size: 14px; }
        
        /* أزرار نصية واضحة ومباشرة تجبر المتصفح على إظهارها رغماً عنه */
        .header-actions { display: flex; align-items: center; gap: 8px; margin-right: auto; }
        .text-btn { border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: bold; color: white; display: inline-flex; align-items: center; justify-content: center; transition: opacity 0.2s; }
        .text-btn:hover { opacity: 0.9; }
        .text-btn.broadcast { background-color: #0284c7; }
        .text-btn.new-chat { background-color: #00a884; }

        .search-box { padding: 8px 12px; background: #fff; border-bottom: 1px solid #f0f2f5; }
        .search-inner { background: #f0f2f5; border-radius: 8px; padding: 6px 12px; display: flex; align-items: center; gap: 10px; color: #667781; }
        .search-inner input { background: transparent; border: none; outline: none; width: 100%; font-size: 14px; color: #111b21; }
        
        .user-list { flex: 1; overflow-y: auto; background: #fff; }
        .user-item { display: flex; align-items: center; padding: 12px 16px; cursor: pointer; border-bottom: 1px solid #f0f2f5; height: 72px; }
        .user-item:hover { background: #f5f6f6; }
        .user-item.active { background: #eaebeb; }
        .user-info { margin-right: 15px; flex: 1; display: flex; flex-direction: column; justify-content: center; }
        .user-name { font-weight: 500; color: #111b21; font-size: 16px; text-align: right; }
        .user-status { font-size: 13px; color: #667781; margin-top: 4px; text-align: right; }

        .chat-area { flex: 1; display: flex; flex-direction: column; background: #efeae2 url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png'); background-repeat: repeat; }
        .chat-header { height: 60px; background: #f0f2f5; display: flex; align-items: center; padding: 0 16px; border-bottom: 1px solid #e9edef; }
        
        .messages-container { flex: 1; overflow-y: auto; padding: 20px 5%; display: flex; flex-direction: column; gap: 8px; }
        .msg-row { display: flex; width: 100%; }
        .msg-row.me { justify-content: flex-start; } 
        .msg-row.them { justify-content: flex-end; }
        
        .bubble { max-width: 65%; padding: 6px 12px; border-radius: 8px; font-size: 14.5px; line-height: 1.4; box-shadow: 0 1px 0.5px rgba(11,20,26,.13); word-wrap: break-word; display: flex; flex-direction: column; }
        .msg-row.me .bubble { background: #d9fdd3; color: #111b21; }
        .msg-row.them .bubble { background: #ffffff; color: #111b21; }

        .meta-container { align-self: flex-end; display: flex; align-items: center; gap: 4px; margin-top: 2px; font-size: 11px; color: #8696a0; user-select: none; }
        .meta-container .time-text { font-size: 10.5px; }

        .input-area { height: 62px; background: #f0f2f5; display: flex; align-items: center; padding: 5px 15px; }
        .input-area form { display: flex; width: 100%; gap: 10px; align-items: center; }
        .input-box { flex: 1; background: #fff; border-radius: 8px; padding: 10px 15px; border: none; outline: none; font-size: 15px; }
        .btn-send { background: #00a884; border: none; color: white; font-size: 14px; font-weight: bold; cursor: pointer; padding: 10px 20px; border-radius: 6px; }

        .welcome-screen { display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1; background: #f8f9fa; color: #667781; text-align: center; border-bottom: 6px solid #00a884; padding: 20px; }
        .welcome-screen h2 { color: #41525d; font-weight: 300; margin-bottom: 10px; font-size: 32px; }

        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); justify-content: center; align-items: center; z-index: 999; }
        .modal-content { background: white; padding: 24px; border-radius: 8px; width: 380px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); border-top: 5px solid #00a884; }
        .modal-content.broadcast-modal { border-top: 5px solid #0284c7; }
        .modal-content h3 { margin-bottom: 15px; color: #111b21; font-size: 19px; }
        .modal-content input, .modal-content textarea { width: 100%; padding: 10px; border: 1px solid #e9edef; border-radius: 6px; margin-bottom: 15px; font-size: 15px; outline: none; background: #f0f2f5; }
        .modal-content textarea { height: 110px; resize: none; background: #fff; border: 1px solid #ccc; }
        .modal-actions { display: flex; justify-content: flex-end; gap: 12px; }
        .modal-btn { padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: 500; }
        .modal-btn.confirm { background: #00a884; color: white; }
        .modal-btn.broadcast-confirm { background: #0284c7; color: white; }
        .modal-btn.cancel { background: white; color: #54656f; border: 1px solid #e9edef; }
    </style>
</head>
<body>

    <div class="modal" id="newChatModal">
        <div class="modal-content">
            <h3>بدء محادثة جديدة</h3>
            <input type="text" id="newPhoneInput" placeholder="اكتب الرقم بمفتاحه الدولي (مثال: 96777000000)" autocomplete="off" style="direction: ltr; text-align: left;">
            <div class="modal-actions">
                <button class="modal-btn cancel" onclick="closeNewChatModal()">إلغاء</button>
                <button class="modal-btn confirm" onclick="createNewChat()">إضافة وفتح</button>
            </div>
        </div>
    </div>

    <div class="modal" id="broadcastModal">
        <div class="modal-content broadcast-modal">
            <h3>إرسال رسالة جماعية (برودكاست) 📢</h3>
            <p style="font-size: 13px; color: #667781; margin-bottom: 12px;">سيتم بث هذه الرسالة دفعة واحدة لجميع جهات الاتصال المسجلة في لوحتك.</p>
            <textarea id="broadcastMessageInput" placeholder="اكتب نص الرسالة الجماعية هنا..."></textarea>
            <div class="modal-actions">
                <button class="modal-btn cancel" onclick="closeBroadcastModal()">إلغاء</button>
                <button class="modal-btn broadcast-confirm" onclick="sendBroadcast()">إرسال الآن للجميع</button>
            </div>
        </div>
    </div>

    <div class="sidebar">
        <div class="sidebar-header">
            <div class="header-right-side">
                <div class="avatar">WA</div>
                <span style="font-weight: bold; color: #111b21; margin-right: 5px;">المحادثات</span>
            </div>
            <div class="header-actions">
                <button class="text-btn broadcast" onclick="openBroadcastModal()">📢 بث للكل</button>
                <button class="text-btn new-chat" onclick="openNewChatModal()">➕ رقم جديد</button>
            </div>
        </div>
        
        <div class="search-box">
            <div class="search-inner">
                <input type="text" id="searchInput" placeholder="البحث عن دردشة..." oninput="filterUsers()">
            </div>
        </div>
        
        <div class="user-list"></div>
    </div>

    <div class="chat-area" id="chatArea" style="display: none;">
        <div class="chat-header">
            <div class="avatar" style="margin-left: 15px;">User</div>
            <div>
                <div class="user-name" id="currentChatUser">جاري التحميل...</div>
                <div style="font-size: 12px; color: #667781;">متصل الآن</div>
            </div>
        </div>
        
        <div class="messages-container" id="messagesContainer"></div>

        <div class="input-area">
            <form id="sendForm" onsubmit="sendMessage(event)">
                <input type="hidden" id="activePhone">
                <input type="text" id="messageInput" class="input-box" placeholder="اكتب رسالتك هنا..." autocomplete="off" required>
                <button type="submit" class="btn-send">إرسال</button>
            </form>
        </div>
    </div>

    <div class="welcome-screen" id="welcomeScreen">
        <h2>واتساب ويب للمسؤول</h2>
        <p>استخدم أزرار [بث للكل] و [رقم جديد] في القائمة الجانبية لبدء التحكم والعمل المباشر.</p>
    </div>

    <script>
        let currentPhone = "";
        let chatIntervalId = null;
        let rawUsersList = [];

        document.addEventListener("DOMContentLoaded", () => {
            fetchUsersList();
            setInterval(fetchUsersList, 4000);
        });

        function fetchUsersList() {
            fetch('/api/users')
                .then(res => res.json())
                .then(data => {
                    rawUsersList = data.users ? data.users : data;
                    renderUsers(rawUsersList);
                }).catch(err => console.error("Error fetching users:", err));
        }

        function renderUsers(users) {
            const container = document.querySelector('.user-list');
            let htmlContent = "";
            users.forEach(user => {
                const isActive = user.phone === currentPhone ? 'active' : '';
                htmlContent += `
                    <div class="user-item ${isActive}" onclick="openChat('${user.phone}', this)">
                        <div class="avatar">💬</div>
                        <div class="user-info">
                            <div class="user-name">${user.phone}</div>
                            <div class="user-status">اضغط لعرض الدردشة...</div>
                        </div>
                    </div>
                `;
            });
            container.innerHTML = htmlContent;
        }

        function filterUsers() {
            const q = document.getElementById('searchInput').value.trim().toLowerCase();
            renderUsers(rawUsersList.filter(u => u.phone.toLowerCase().includes(q)));
        }

        function openNewChatModal() { document.getElementById('newChatModal').style.display = 'flex'; document.getElementById('newPhoneInput').focus(); }
        function closeNewChatModal() { document.getElementById('newChatModal').style.display = 'none'; document.getElementById('newPhoneInput').value = ''; }
        function openBroadcastModal() { document.getElementById('broadcastModal').style.display = 'flex'; document.getElementById('broadcastMessageInput').focus(); }
        function closeBroadcastModal() { document.getElementById('broadcastModal').style.display = 'none'; document.getElementById('broadcastMessageInput').value = ''; }

        function sendBroadcast() {
            const message = document.getElementById('broadcastMessageInput').value.trim();
            if(!message) return alert("الرجاء كتابة نص الرسالة أولاً!");
            const formData = new FormData();
            formData.append('message', message);
            fetch('/api/broadcast', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                if(data.status === 'ok') {
                    alert(`تم إرسال الرسالة الجماعية بنجاح إلى ${data.sent_count} رقم! 🚀`);
                    closeBroadcastModal();
                    fetchUsersList();
                }
            });
        }

        function createNewChat() {
            const phone = document.getElementById('newPhoneInput').value.trim();
            if(!phone) return alert("الرجاء كتابة الرقم بشكل صحيح!");
            const formData = new FormData();
            formData.append('phone', phone);
            fetch('/api/add_user', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                if(data.status === 'ok') {
                    closeNewChatModal();
                    fetchUsersList();
                    openChat(phone, null);
                }
            });
        }

        function openChat(phone, element) {
            currentPhone = phone;
            document.getElementById('activePhone').value = phone;
            document.getElementById('currentChatUser').innerText = phone;
            document.getElementById('welcomeScreen').style.display = 'none';
            document.getElementById('chatArea').style.display = 'flex';
            document.querySelectorAll('.user-item').forEach(item => item.classList.remove('active'));
            if(element) element.classList.add('active');
            fetchMessages();
            if(chatIntervalId) clearInterval(chatIntervalId);
            chatIntervalId = setInterval(fetchMessages, 2000);
        }

        function fetchMessages() {
            if (!currentPhone) return;
            fetch(`/messages/${currentPhone}`)
                .then(res => res.json())
                .then(data => {
                    const container = document.getElementById('messagesContainer');
                    const isScrolledToBottom = container.scrollHeight - container.clientHeight <= container.scrollTop + 50;
                    container.innerHTML = "";
                    data.messages.forEach(msg => {
                        const row = document.createElement('div');
                        row.className = `msg-row ${msg.sender === 'me' ? 'me' : 'them'}`;
                        row.innerHTML = `
                            <div class="bubble">
                                <span>${msg.message}</span>
                                <div class="meta-container">
                                    <span class="time-text">${msg.msg_time || ''}</span>
                                </div>
                            </div>
                        `;
                        container.appendChild(row);
                    });
                    if (isScrolledToBottom) container.scrollTop = container.scrollHeight;
                });
        }

        function sendMessage(event) {
            event.preventDefault();
            const input = document.getElementById('messageInput');
            const message = input.value;
            const phone = document.getElementById('activePhone').value;
            if(!message.trim()) return;
            const formData = new FormData();
            formData.append('phone', phone);
            formData.append('message', message);
            fetch('/send', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => { input.value = ""; fetchMessages(); });
        }
    </script>
</body>
</html>
"""

# ================= ROUTES =================
@app.route("/")
@app.route("/chat")
def chat_panel():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/users")
def get_users():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return jsonify({"users": [dict(u) for u in users]})

@app.route("/api/add_user", methods=["POST"])
def add_user():
    phone = request.form.get("phone", "").strip()
    if not phone:
        return jsonify({"status": "error"}), 400
    conn = db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/broadcast", methods=["POST"])
def broadcast():
    message = request.form.get("message", "").strip()
    if not message:
        return jsonify({"status": "error"}), 400
    conn = db()
    c = conn.cursor()
    c.execute("SELECT phone FROM users")
    users = c.fetchall()
    sent_count = 0
    now_time = datetime.now().strftime("%I:%M %p")
    for user in users:
        phone = user["phone"]
        wamid = send_message(phone, message)
        c.execute("""
        INSERT OR IGNORE INTO messages (msg_id, phone, message, sender, status, msg_time)
        VALUES (?, ?, ?, 'me', 'sent', ?)
        """, (wamid, phone, message, now_time))
        sent_count += 1
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "sent_count": sent_count})

@app.route("/messages/<phone>")
def messages(phone):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM messages WHERE phone=? ORDER BY id ASC", (phone,))
    msgs = c.fetchall()
    conn.close()
    return jsonify({"messages": [dict(m) for m in msgs]})

@app.route("/send", methods=["POST"])
def send():
    phone = request.form["phone"]
    message = request.form["message"]
    wamid = send_message(phone, message)
    now_time = datetime.now().strftime("%I:%M %p")
    conn = db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
    c.execute("""
    INSERT INTO messages (msg_id, phone, message, sender, status, msg_time) 
    VALUES (?, ?, ?, 'me', 'sent', ?)
    """, (wamid, phone, message, now_time))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "error", 403
    try:
        data = request.json
        value = data["entry"][0]["changes"][0]["value"]
        if "messages" in value:
            msg = value["messages"][0]
            phone = msg["from"]
            text = msg.get("text", {}).get("body", "[وسائط]")
            msg_id = msg["id"]
            now_time = datetime.now().strftime("%I:%M %p")
            conn = db()
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users VALUES (?)", (phone,))
            c.execute("""
            INSERT OR IGNORE INTO messages (msg_id, phone, message, sender, status, msg_time) 
            VALUES (?, ?, ?, 'them', 'read', ?)
            """, (msg_id, phone, text, now_time))
            conn.commit()
            conn.close()
    except Exception as e:
        print("Webhook Error:", e)
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
