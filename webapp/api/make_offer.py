import os
import sys
import json
import requests
from http.server import BaseHTTPRequestHandler

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(parent_dir, ".env"))

import cart

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            user_id = data.get("user_id")
            product_id = data.get("product_id")
            offered_price = data.get("offered_price")

            admin_id = os.getenv("ADMIN_ID")
            bot_token = os.getenv("BOT_TOKEN")

            if admin_id and bot_token and product_id and offered_price:
                products = cart._load_products()
                p_obj = next((p for p in products if p["id"] == int(product_id)), None)
                p_title = p_obj["name"] if p_obj else f"Товар #{product_id}"
                p_price = p_obj["price"] if p_obj else 0.0

                text = (
                    f"📥 **Нова пропозиція ціни (Торг у Mini App)!**\n\n"
                    f"👤 Покупець ID: `{user_id}`\n"
                    f"🛍️ Товар: **{p_title}**\n"
                    f"🏷️ Оригінальна ціна: **{p_price} грн**\n"
                    f"💰 Запропоновано: **{offered_price} грн**"
                )

                first_admin = admin_id.split(",")[0].strip()
                tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = {
                    "chat_id": int(first_admin),
                    "text": text,
                    "parse_mode": "Markdown",
                    "reply_markup": {
                        "inline_keyboard": [
                            [
                                {"text": f"✅ Прийняти ({offered_price} грн)", "callback_data": f"offer_acc:{user_id}:{product_id}:{offered_price}"},
                                {"text": "❌ Відхилити", "callback_data": f"offer_rej:{user_id}:{product_id}:{offered_price}"}
                            ]
                        ]
                    }
                }
                requests.post(tg_url, json=payload, timeout=5)

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "message": "Пропозицію успішно передано продавцю!"}).encode('utf-8'))
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
