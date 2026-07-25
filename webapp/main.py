import os
import re
import json
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import ai_manager
import cart
import storage
import admin
import bonuses
import categories
import web_server

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables.")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class AutoRegisterMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user and user.id:
            storage.register_user(user.id)
        return await handler(event, data)


dp.message.outer_middleware(AutoRegisterMiddleware())
dp.callback_query.outer_middleware(AutoRegisterMiddleware())
dp.include_router(admin.router)


class CheckoutState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()


def load_products():
    return storage._read_json("products.json", [])


WEB_APP_URL = os.getenv("WEB_APP_URL", "").strip()


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    storage.register_user(user_id)
    
    welcome_text = (
        "Вітаю у магазині Store & Collectibles! 🧸✨\n\n"
        "Я ваш особистий AI-консультант. Ви можете запитати у мене про асортимент, "
        "попросити порадити щось цікаве або відразу додати товар до кошика.\n\n"
        "Доступні команди:\n"
        "/cart - Переглянути кошик\n"
        "/clear_cart - Очистити кошик\n"
        "/checkout - Оформити замовлення"
    )

    if admin.is_admin(user_id):
        welcome_text += "\n/admin - Панель адміністратора ⚙️"

    if WEB_APP_URL and WEB_APP_URL.startswith("https://"):
        inline_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🛍️ Відкрити Магазин (Mini App)", web_app=types.WebAppInfo(url=WEB_APP_URL))]
        ])
        storage.save_message(user_id, "assistant", welcome_text)
        await message.answer(welcome_text, reply_markup=inline_kb)
    else:
        storage.save_message(user_id, "assistant", welcome_text)
        await message.answer(welcome_text)


@dp.message(Command("admin"))
async def cmd_admin_main(message: types.Message, state: FSMContext):
    await admin.cmd_admin(message, state)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "Як зі мною спілкуватися?\n"
        "• Просто напишіть, що ви шукаете (наприклад: 'Які фігурки є в наявності?').\n"
        "• Вкажіть бажання купити (наприклад: 'Хочу замовити фігурку Ані').\n"
        "• Або скористайтеся Mini App кнопку внизу для швидкого замовлення! 🛒"
    )
    await message.answer(help_text)


@dp.message(Command("cart"))
async def cmd_cart(message: types.Message):
    user_id = message.from_user.id
    products = load_products()
    cart_info = cart.get_cart_total(user_id, products)

    if not cart_info["items"]:
        await message.answer("Ваш кошик порожній 🛒. Напишіть мені, який товар бажаєте додати!")
        return

    text = "🛒 **Ваш поточний кошик:**\n\n"
    for item in cart_info["items"]:
        text += f"• **{item['name']}** x{item['quantity']} = {item['subtotal']} грн\n"

    text += f"\n💰 **Загальна сума:** {cart_info['total_price']} грн"

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🚀 Оформити замовлення", callback_data="checkout")],
        [types.InlineKeyboardButton(text="🗑️ Очистити кошик", callback_data="clear_cart")]
    ])

    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@dp.callback_query(F.data == "checkout")
async def cb_checkout(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await cmd_checkout(callback.message, state)


@dp.callback_query(F.data == "clear_cart")
async def cb_clear_cart_callback(callback: types.CallbackQuery):
    await callback.answer("Кошик очищено!")
    user_id = callback.from_user.id
    cart.clear_cart(user_id)
    await callback.message.edit_text("Ваш кошик очищено 🗑️.")


@dp.message(Command("clear_cart"))
async def cmd_clear_cart(message: types.Message):
    user_id = message.from_user.id
    cart.clear_cart(user_id)
    await message.answer("Ваш кошик очищено 🗑️.")


@dp.message(Command("checkout"))
async def cmd_checkout(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    products = load_products()
    user_cart = cart.get_cart(user_id)

    if not user_cart:
        await message.answer("Ваш кошик порожній. Спочатку додайте товар в кошик! 🛍️")
        return

    await state.set_state(CheckoutState.waiting_for_name)
    await message.answer("Чудово! Давайте оформимо замовлення 📝.\nБудь ласка, введіть ваші **ПІБ / Ім'я**:")


# Хендлери покрокового оформлення замовлення
@dp.message(CheckoutState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(CheckoutState.waiting_for_phone)
    await message.answer("Дякую! Тепер введіть ваш **номер телефону** (наприклад, +380123456789):")


@dp.message(CheckoutState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(CheckoutState.waiting_for_address)
    await message.answer("Прийнято! Вкажіть **адресу доставки** (Місто, відділення Нової Пошти):")


@dp.message(CheckoutState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await state.get_data()
    address = message.text

    products = load_products()
    cart_summary = cart.get_cart_total(user_id, products)

    order = {
        "user_id": user_id,
        "name": user_data.get("name"),
        "phone": user_data.get("phone"),
        "address": address,
        "items": cart_summary["items"],
        "total_price": cart_summary["total_price"],
        "status": "new"
    }

    saved_order = storage.save_order(order)
    cart.clear_cart(user_id)
    await state.clear()

    order_success_msg = (
        f"🎉 **Замовлення №{saved_order['order_id']} успішно створено!**\n\n"
        f"👤 Отримувач: {saved_order['name']}\n"
        f"📞 Телефон: {saved_order['phone']}\n"
        f"📍 Адреса: {saved_order['address']}\n"
        f"💰 Загальна сума: {saved_order['total_price']} грн\n\n"
        f"Дякуємо, що обираєте наш магазин! Наш менеджер скоро зв'яжеться з вами. 🛍️✨"
    )
    await message.answer(order_success_msg, parse_mode="Markdown")


def save_products(products):
    storage._write_json("products.json", products)


@dp.message(F.text)
async def handle_user_text(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        return

    user_id = message.from_user.id
    user_text = message.text
    storage.register_user(user_id)

    if user_text and user_text.startswith("/"):
        return

    is_user_admin = admin.is_admin(user_id)

    # 1. Зберігаємо повідомлення користувача
    storage.save_message(user_id, "user", user_text)

    # 2. Отримуємо повний контекст користувача
    history = storage.get_user_history(user_id)
    products = load_products()
    cart_info = cart.get_cart_total(user_id, products)
    user_b_val = bonuses.get_user_bonuses(user_id)
    user_orders = storage.get_orders(user_id=user_id)
    promos = web_server.load_promos()

    # 3. Викликаємо AI-менеджера з підтримкою адмін-команд
    ai_response = ai_manager.generate_reply(
        message=user_text,
        history=history,
        products=products,
        user_cart=cart_info["items"],
        user_bonuses=user_b_val,
        user_orders=user_orders,
        promos=promos,
        is_admin=is_user_admin
    )

    reply_text = ai_response.get("reply") or "Дію опрацьовано!"
    action = str(ai_response.get("action") or "question")
    product_id = ai_response.get("product_id")
    quantity = ai_response.get("quantity") or 1
    promo_code = ai_response.get("promo_code")

    # 4. Обробка розширених дій (actions)
    if action == "add_to_cart" and product_id:
        try:
            qty_int = int(re.sub(r"\D", "", str(quantity))) if quantity else 1
        except Exception:
            qty_int = 1
        success, cart_msg = cart.add_to_cart(user_id, product_id, qty_int, products)
        if not success:
            reply_text += f"\n\n⚠️ ({cart_msg})"

    elif action == "remove_from_cart" and product_id:
        cart.remove_from_cart(user_id, product_id)

    elif action == "show_cart":
        storage.save_message(user_id, "assistant", reply_text)
        await message.answer(reply_text)
        await cmd_cart(message)
        return

    elif action == "clear_cart":
        cart.clear_cart(user_id)

    elif action == "checkout":
        user_cart = cart.get_cart(user_id)
        if not user_cart:
            reply_text += "\n\n(Ваш кошик наразі порожній, додайте щось перед оформленням!)"
        else:
            storage.save_message(user_id, "assistant", reply_text)
            await message.answer(reply_text)
            await state.set_state(CheckoutState.waiting_for_name)
            await message.answer("Давайте оформимо замовлення! 📝 Введіть ваші **ПІБ / Ім'я**:")
            return

    elif action == "apply_promo" and promo_code:
        p_code = promo_code.strip().upper()
        if p_code in promos and promos[p_code].get("active", True):
            pct = promos[p_code].get("discount_percent", 0)
            reply_text += f"\n\n🎉 Промокод `{p_code}` дійсний! Ви отримуєте знижку **{pct}%** при оформленні!"

    elif action == "check_status":
        if user_orders:
            last_order = user_orders[-1]
            st_map = {"new": "🆕 Нове", "processing": "⏳ В обробці", "completed": "✅ Виконано", "cancelled": "❌ Скасовано"}
            st_str = st_map.get(last_order.get("status"), last_order.get("status"))
            reply_text += f"\n\n📦 Замовлення #{last_order.get('order_id')}: статус **{st_str}** (сума: {last_order.get('total_price')} грн)."

    # --- AUTOMATIC AI ADMIN ACTIONS ---
    elif is_user_admin and action.startswith("admin_"):
        if action == "admin_add_product":
            p_name = ai_response.get("product_name") or "Новий товар"
            raw_p = str(ai_response.get("product_price") or "0")
            clean_p = re.sub(r"[^\d.]", "", raw_p.replace(",", "."))
            p_price = float(clean_p) if clean_p else 0.0

            cat_name = ai_response.get("category_name") or "Фігурки"
            cond = ai_response.get("condition") or "Mint 10/10"
            desc = ai_response.get("description") or "Якісний колекційний товар"
            new_id = max([p["id"] for p in products], default=0) + 1
            new_p = {
                "id": new_id,
                "name": p_name,
                "description": desc,
                "price": p_price,
                "in_stock": True,
                "category": cat_name,
                "condition": cond,
                "rating": 5.0,
                "image_url": "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?auto=format&fit=crop&w=600&q=80"
            }
            products.append(new_p)
            save_products(products)
            categories.add_category(cat_name)
            reply_text += f"\n\n✅ [AI Admin]: Товар **«{p_name}»** ({p_price} грн) успішно додано!"

        elif action == "admin_delete_product":
            p_id = ai_response.get("product_id")
            p_name = ai_response.get("product_name")
            target = None
            if p_id:
                target = next((p for p in products if p.get("id") == p_id or str(p.get("id")) == str(p_id)), None)
            elif p_name:
                target = next((p for p in products if p_name.lower() in (p.get("name") or "").lower()), None)
            
            if target:
                products.remove(target)
                save_products(products)
                reply_text += f"\n\n🗑️ [AI Admin]: Товар **«{target['name']}»** (ID: {target['id']}) видалено!"
            else:
                reply_text += "\n\n⚠️ [AI Admin]: Товар не знайдено."

        elif action == "admin_add_category":
            c_name = ai_response.get("category_name")
            if c_name and categories.add_category(c_name):
                reply_text += f"\n\n🗂️ [AI Admin]: Новий розділ **«{c_name}»** створено!"
            else:
                reply_text += f"\n\n⚠️ Розділ вже існує або назву не вказано."

        elif action == "admin_delete_category":
            c_name = ai_response.get("category_name")
            if c_name and categories.delete_category(c_name):
                reply_text += f"\n\n❌ [AI Admin]: Розділ **«{c_name}»** видалено!"
            else:
                reply_text += f"\n\n⚠️ Розділ не знайдено."

        elif action == "admin_add_promo":
            pr_code = (ai_response.get("promo_code") or "").strip().upper()
            raw_pct = str(ai_response.get("discount_percent") or "10")
            clean_pct = re.sub(r"\D", "", raw_pct)
            pct = int(clean_pct) if clean_pct else 10

            if pr_code:
                promos = web_server.load_promos()
                promos[pr_code] = {"discount_percent": pct, "active": True}
                web_server.save_promos(promos)
                reply_text += f"\n\n🏷️ [AI Admin]: Промокод `{pr_code}` на **{pct}%** активовано!"

        elif action == "admin_update_order":
            o_id = ai_response.get("order_id")
            n_st = ai_response.get("new_status") or "completed"
            if o_id:
                updated = storage.update_order_status(o_id, n_st)
                if updated:
                    reply_text += f"\n\n📦 [AI Admin]: Статус замовлення #{o_id} змінено на **{n_st}**!"
                else:
                    reply_text += f"\n\n⚠️ [AI Admin]: Замовлення #{o_id} не знайдено."
            else:
                reply_text += "\n\n⚠️ [AI Admin]: Не вказано ID замовлення."

        elif action == "admin_broadcast":
            b_text = ai_response.get("broadcast_text") or user_text
            cleaned_b_text = re.sub(
                r"^(?:/broadcast|/send|зделай розсилку с таким текстом|сделай рассылку с текстом|зроби розсилку з текстом|зроби розсилку|зделай розсилку|сделай рассылку)\s*",
                "",
                b_text,
                flags=re.IGNORECASE
            ).strip()
            if cleaned_b_text:
                b_text = cleaned_b_text

            u_ids = storage.get_all_user_ids()
            await message.answer(f"⏳ [AI Admin]: Запускаю масову розсилку для {len(u_ids)} користувачів...")

            reply_markup = None
            if "|" in b_text:
                parts = [p.strip() for p in b_text.rsplit("|", 2)]
                if len(parts) == 3:
                    btn_label = parts[1]
                    btn_url = parts[2]
                    if btn_url.startswith(("http://", "https://", "tg://")):
                        b_text = parts[0]
                        reply_markup = types.InlineKeyboardMarkup(inline_keyboard=[
                            [types.InlineKeyboardButton(text=btn_label, url=btn_url)]
                        ])

            succ = 0
            fail = 0
            for uid in u_ids:
                try:
                    await bot.send_message(chat_id=int(uid), text=b_text, reply_markup=reply_markup, parse_mode="Markdown")
                    succ += 1
                except Exception:
                    try:
                        await bot.send_message(chat_id=int(uid), text=b_text, reply_markup=reply_markup)
                        succ += 1
                    except Exception:
                        fail += 1
            reply_text += f"\n\n📢 **[AI Admin]: Розсилку завершено!**\n✅ Успішно: **{succ}** | ❌ Помилок: **{fail}**"

    elif action == "manager":
        reply_text += "\n\n🔔 (Повідомлення передано менеджеру-людині)."

    # Зберігаємо та відправляємо відповідь бота
    storage.save_message(user_id, "assistant", reply_text)
    try:
        await message.answer(reply_text, parse_mode="Markdown")
    except Exception:
        await message.answer(reply_text)


async def main():
    print("Cookie Shop Bot starting polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print(f"[Delete Webhook Warning]: {e}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
