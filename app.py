from flask import Flask, request, jsonify, render_template
import os, threading, time, requests, psycopg2
from psycopg2.extras import RealDictCursor
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

# CONFIG
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "1171944939327803"
VERIFY_TOKEN = "mytoken123"
DATABASE_URL = os.environ.get("DATABASE_URL")

# ... (باقي كود SITES ودالة db و check_updates و loop و send_message كما هي) ...

@app.route("/")
def home(): return render_template("chat.html")

@app.route("/api/users")
def get_users():
    try:
        conn = db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT phone FROM users ORDER BY phone")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({"users": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/messages/<phone>", methods=['GET'])
def get_messages(phone):
    try:
        conn = db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM messages WHERE phone=%s ORDER BY id ASC", (phone,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({"messages": rows})
    except Exception as e:
        return jsonify({"messages": []}), 500

# دالة الحذف المكتملة (تم دمجها مرة واحدة فقط)
@app.route('/api/delete_contact', methods=['POST'])
def delete_contact():
    phone = request.form.get('phone')
    if not phone:
        return jsonify({"status": "error", "message": "No phone provided"}), 400
    try:
        conn = db()
        cur = conn.cursor()
        cur.execute("DELETE FROM messages WHERE phone=%s", (phone,))
        cur.execute("DELETE FROM users WHERE phone=%s", (phone,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/send", methods=["POST"])
def send():
    phone, message = request.form.get("phone"), request.form.get("message")
    send_message(phone, message)
    conn = db(); cur = conn.cursor()
    cur.execute("INSERT INTO messages(phone,message,sender,msg_time) VALUES(%s,%s,'me',%s)", (phone, message, datetime.now().strftime("%H:%M")))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/delete_messages/<phone>", methods=['POST'])
def delete_messages(phone):
    conn = db(); cur = conn.cursor()
    cur.execute("DELETE FROM messages WHERE phone=%s", (phone,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"status": "deleted"})

@app.route("/api/broadcast", methods=["POST"])
def broadcast():
    message = request.form.get("message")
    conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT phone FROM users"); users = cur.fetchall()
    for u in users: send_message(u['phone'], message)
    cur.close(); conn.close()
    return jsonify({"status": "ok"})

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET": return request.args.get("hub.challenge") if request.args.get("hub.verify_token") == VERIFY_TOKEN else "error", 403
    try:
        data = request.json
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        phone, text = msg["from"], msg["text"]["body"]
        conn = db(); cur = conn.cursor()
        cur.execute("INSERT INTO messages(phone,message,sender,msg_time) VALUES(%s,%s,'them',%s)", (phone, text, datetime.now().strftime("%H:%M")))
        cur.execute("INSERT INTO users(phone) VALUES(%s) ON CONFLICT DO NOTHING", (phone,))
        conn.commit(); cur.close(); conn.close()
    except: pass
    return "ok"

if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
