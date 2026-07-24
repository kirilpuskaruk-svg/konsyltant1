import os
import sys
import json
from http.server import BaseHTTPRequestHandler

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import storage
import cart
import bonuses
import web_server

class handler(BaseHTTPRequestHandler):
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
            use_bonuses = data.get("use_bonuses", False)

            subtotal = sum(float(item.get("price", 0)) * item.get("quantity", 1) for item in items)
            discount = 0.0

            if promo_code:
                promos = web_server.load_promos()
                if promo_code in promos and promos[promo_code].get("active", True):
                    disc_pct = promos[promo_code].get("discount_percent", 0)
                    discount = (subtotal * disc_pct) / 100.0

            bonus_deducted = 0.0
            if use_bonuses and user_id:
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

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "order_id": saved.get("order_id")}).encode('utf-8'))
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
