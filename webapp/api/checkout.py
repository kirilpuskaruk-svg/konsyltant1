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

import storage
import cart
import bonuses


def load_promos():
    return storage._read_json("promos.json", {})


class handler(BaseHTTPRequestHandler):
    def send_cors_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self.send_cors_headers(200)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode('utf-8'))
            user_id = data.get("user_id")
            name = data.get("name")
            phone = data.get("phone")
            address = data.get("address")
            items = data.get("items", [])
            promo_code = data.get("promo_code")
            use_bonuses_flag = data.get("use_bonuses", False)

            if user_id:
                storage.register_user(user_id)

            subtotal = sum(float(item.get("price", 0)) * item.get("quantity", 1) for item in items)
            discount = 0.0

            if promo_code:
                promos = load_promos()
                if promo_code in promos and promos[promo_code].get("active", True):
                    disc_pct = promos[promo_code].get("discount_percent", 0)
                    discount = (subtotal * disc_pct) / 100.0

            bonus_deducted = 0.0
            if use_bonuses_flag and user_id:
                user_b = bonuses.get_user_bonuses(user_id)
                rem = max(0.0, subtotal - discount)
                bonus_deducted = min(user_b, rem)
                if bonus_deducted > 0:
                    bonuses.use_user_bonuses(user_id, bonus_deducted)

            final_total = max(0.0, round(subtotal - discount - bonus_deducted, 2))

            order_data = {
                "user_id": user_id,
                "name": name,
                "phone": phone,
                "address": address,
                "items": items,
                "total_price": final_total,
                "discount_applied": round(discount + bonus_deducted, 2),
                "status": "new"
            }

            saved = storage.save_order(order_data)
            cart.clear_cart(user_id)

            # Notify all admins via Telegram Bot API
            admin_id_env = os.getenv("ADMIN_ID", "")
            bot_token = os.getenv("BOT_TOKEN", "")
            if admin_id_env and bot_token:
                items_text = "\n".join(
                    f"  • {item.get('name', '?')} x{item.get('quantity', 1)} = {float(item.get('price', 0)) * item.get('quantity', 1)} ₴"
                    for item in items
                )
                notify_text = (
                    f"🛒 <b>Нове замовлення #{saved.get('order_id')}!</b>\n\n"
                    f"👤 Клієнт: <b>{name}</b>\n"
                    f"📞 Телефон: <b>{phone}</b>\n"
                    f"📍 Адреса: <b>{address}</b>\n"
                    f"🆔 Telegram ID: <code>{user_id}</code>\n\n"
                    f"🛍️ Товари:\n{items_text}\n\n"
                    f"💰 Сума: <b>{final_total} ₴</b>"
                )
                if discount + bonus_deducted > 0:
                    notify_text += f"\n🎁 Знижка: -{round(discount + bonus_deducted, 2)} ₴"

                tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                for a_id in admin_id_env.split(","):
                    a_id = a_id.strip()
                    if not a_id.lstrip("-").isdigit():
                        continue
                    try:
                        requests.post(tg_url, json={
                            "chat_id": int(a_id),
                            "text": notify_text,
                            "parse_mode": "HTML"
                        }, timeout=5)
                    except Exception as notify_err:
                        print(f"[Checkout Notify Error]: {notify_err}")

            self.send_cors_headers(200)
            self.wfile.write(json.dumps({"success": True, "order_id": saved.get("order_id")}, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_cors_headers(400)
            self.wfile.write(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False).encode('utf-8'))
