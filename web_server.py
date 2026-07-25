import os
import json
import asyncio
import aiohttp
from aiohttp import web
import storage
import cart
import bonuses
import reviews


def load_products():
    return storage._read_json("products.json", [])



async def start_bot_task(app):
    try:
        import main as bot_main
        await bot_main.bot.delete_webhook(drop_pending_updates=True)
        asyncio.create_task(bot_main.dp.start_polling(bot_main.bot))
    except Exception as e:
        print(f"[Start Bot Task Error]: {e}")

PROMOS_FILE = "promos.json"


def load_promos():
    if os.path.exists(PROMOS_FILE):
        try:
            with open(PROMOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_promos(promos):
    try:
        with open(PROMOS_FILE, "w", encoding="utf-8") as f:
            json.dump(promos, f, ensure_ascii=False, indent=2)
    except OSError:
        import tempfile
        tmp_path = os.path.join(tempfile.gettempdir(), PROMOS_FILE)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(promos, f, ensure_ascii=False, indent=2)


async def handle_index(request):
    return web.FileResponse(os.path.join("webapp", "index.html"))


async def handle_css(request):
    return web.FileResponse(os.path.join("webapp", "style.css"))


async def handle_js(request):
    return web.FileResponse(os.path.join("webapp", "app.js"))


async def handle_get_products(request):
    prods = cart._load_products()
    return web.json_response(prods)


async def handle_get_bonuses(request):
    user_id = request.query.get("user_id", "")
    bonus_balance = bonuses.get_user_bonuses(user_id)
    return web.json_response({"bonuses": bonus_balance})


async def handle_validate_promo(request):
    try:
        data = await request.json()
        promo_code = data.get("promo", "").strip().upper()
        promos = load_promos()
        
        if promo_code in promos and promos[promo_code].get("active", True):
            return web.json_response({
                "valid": True,
                "discount_percent": promos[promo_code].get("discount_percent", 10)
            })
    except Exception:
        pass
    return web.json_response({"valid": False, "discount_percent": 0})


async def handle_checkout(request):
    try:
        data = await request.json()
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
            promos = load_promos()
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

        # Notify all admins via Telegram
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
                f"📦 Адреса: <b>{address}</b>\n"
                f"🆔 Telegram ID: <code>{user_id}</code>\n\n"
                f"🛍 Товари:\n{items_text}\n\n"
                f"💰 Сума: <b>{final_total} ₴</b>"
            )
            if discount + bonus_deducted > 0:
                notify_text += f"\n🎁 Знижка: -{round(discount + bonus_deducted, 2)} ₴"

            try:
                async with aiohttp.ClientSession() as session:
                    for admin_id in admin_id_env.split(","):
                        admin_id = admin_id.strip()
                        if not admin_id.lstrip("-").isdigit():
                            continue
                        tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                        await session.post(tg_url, json={
                            "chat_id": int(admin_id),
                            "text": notify_text,
                            "parse_mode": "HTML"
                        })
            except Exception as notify_err:
                print(f"[Checkout Notify Error]: {notify_err}")

        return web.json_response({"success": True, "order_id": saved.get("order_id")})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=400)


async def handle_add_review(request):
    try:
        data = await request.json()
        rev = reviews.add_review(
            product_id=data.get("product_id"),
            user_id=data.get("user_id"),
            user_name=data.get("user_name"),
            rating=data.get("rating", 5),
            text=data.get("text", "")
        )
        return web.json_response({"success": True, "review": rev})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=400)
import categories


async def handle_get_categories(request):
    cats = categories.load_categories()
    return web.json_response(cats)


def create_app():
    app = web.Application()
    app.on_startup.append(start_bot_task)
    app.router.add_get("/", handle_index)
    app.router.add_get("/style.css", handle_css)
    app.router.add_get("/app.js", handle_js)
    app.router.add_get("/api/products", handle_get_products)
    app.router.add_get("/api/categories", handle_get_categories)
    app.router.add_get("/api/user_bonuses", handle_get_bonuses)
    app.router.add_post("/api/validate_promo", handle_validate_promo)
    app.router.add_post("/api/checkout", handle_checkout)
    app.router.add_post("/api/add_review", handle_add_review)
    return app


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=port)
