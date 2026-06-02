import time, requests, psycopg2, os
from bs4 import BeautifulSoup
from psycopg2.extras import RealDictCursor
from datetime import datetime

# إعدادات الاتصال (تأكد من وجود DATABASE_URL في متغيرات البيئة)
DATABASE_URL = os.environ.get("DATABASE_URL")
ACCESS_TOKEN = "EAASpVwBgGpABRpjv02OZAli1ypyLaetqfucvpZCfGa5iFw20N36oHhZCuJaOYZAQvBkSzyYeYaG7wo6t2i7Anm8lPUzqnEwQOtZAAeTLj3hUlxu0flt2D1KOfEgBfW52qcObwWWxRPsG2q4z064shcTjfOAVa4bg4rw2caZAK61vXiCN3EZApnZCaBZBRW1dANEtZBVQZDZD"
PHONE_NUMBER_ID = "1171944939327803"

def db(): return psycopg2.connect(DATABASE_URL)

def send_image_message(phone, image_url, caption):
    try:
        requests.post(f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages",
                      headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"},
                      json={
                          "messaging_product": "whatsapp",
                          "to": phone,
                          "type": "image",
                          "image": {"link": image_url, "caption": caption}
                      })
    except: pass

def check_updates():
    try:
        conn = db(); cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT phone FROM users")
        users = cur.fetchall()
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"}
        sites_to_check = [
            {"url": "https://web6112x.faselhdx.bid/recent_series", "sel": ".post-title a"},
            {"url": "https://tuktukhd.com/recent/", "sel": "h3 a"} 
        ]

        for site in sites_to_check:
            try:
                res = requests.get(site["url"], headers=headers, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                link = soup.select_one(site["sel"])
                
                if link:
                    title = link.get('title') or link.text.strip()
                    if title:
                        img_tag = link.find_previous('img') or link.find_next('img') or link.find('img')
                        img_url = img_tag.get('data-src') or img_tag.get('src') if img_tag else None
                        
                        cur.execute("SELECT id FROM messages WHERE message = %s LIMIT 1", (title,))
                        if not cur.fetchone():
                            msg = f"📺 {title}\n🔥 متاح الآن للمشاهدة!"
                            for u in users:
                                send_image_message(u['phone'], img_url, msg)
                            cur.execute("INSERT INTO messages(phone,message,sender,msg_time) VALUES('system', %s, 'system', %s)", 
                                        (title, datetime.now().strftime("%H:%M")))
                            conn.commit()
            except Exception as e:
                print(f"DEBUG: خطأ في فحص {site['url']}: {e}")
                
        cur.close(); conn.close()
    except Exception as e:
        print(f"DEBUG: خطأ عام في الفحص: {e}")

if __name__ == "__main__":
    print("Worker started...")
    while True:
        check_updates()
        time.sleep(60) # الفحص كل دقيقة