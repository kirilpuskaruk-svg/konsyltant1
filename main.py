import os
import json
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import ai_manager
import cart
import storage
import admin

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables.")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(admin.router)


class CheckoutState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()


def load_products():
    if os.path.exists("products.json"):
        with open("products.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []


WEB_APP_URL = os.getenv("WEB_APP_URL", "").strip()


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    welcome_text = (
        "Вітаю у крафтовому магазині печива Cookie Shop! 🍪✨\n\n"
        "Я ваш особистий AI-консультант. Ви можете запитати у мене про асортимент, "
        "попросити порадити щось смачненьке або відразу додати печиво до кошика.\n\n"
        "Доступні команди:\n"
        "/cart - Переглянути кошик\n"
        "/clear_cart - Очистити кошик\n"
        "/checkout - Оформити замовлення"
    )

    if admin.is_admin(user_id):
        welcome_text += "\n/admin - Панель адміністратора ⚙️"

    if WEB_APP_URL and WEB_APP_URL.startswith("https://"):
        inline_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🍪 Відкрити Магазин (Mini App)", web_app=types.WebAppInfo(url=WEB_APP_URL))]
        ])
        reply_kb = types.ReplyKeyboardMarkup(keyboard=[
            [types.KeyboardButton(text="🍪 Відкрити Магазин", web_app=types.WebAppInfo(url=WEB_APP_URL))]
        ], resize_keyboard=True)

        storage.save_message(user_id, "assistant", welcome_text)
        await message.answer(welcome_text, reply_markup=inline_kb)
        await message.answer("Або скористайтеся кнопкою внизу екрану 👇", reply_markup=reply_kb)
    else:
        storage.save_message(user_id, "assistant", welcome_text)
        await message.answer(welcome_text)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "Як зі мною спілкуватися?\n"
        "• Просто напишіть, що ви шукаєте (наприклад: 'Яке печиво з горіхами є?').\n"
        "• Вкажіть бажання купити (наприклад: 'Хочу дві коробки шоколадного печива').\n"
        "• Напишіть 'Оформлюємо' або опустіть команду /checkout для завершення замовлення."
    )
    await message.answer(help_text)


@dp.message(Command("cart"))
async def cmd_cart(message: types.Message):
    user_id = message.from_user.id
    products = load_products()
    cart_info = cart.get_cart_total(user_id, products)

    if not cart_info["items"]:
        await message.answer("Ваш кошик порожній 🛒. Напишіть мені, яке печиво бажаєте додати!")
        return

    text = "🛒 **Ваш кошик:**\n\n"
    for idx, item in enumerate(cart_info["items"], 1):
        text += f"{idx}. {item['name']} — {item['quantity']} шт. x {item['price']} грн = {item['subtotal']} грн\n"
    
    text += f"\n**Загальна сума:** {cart_info['total_price']} грн\n"
    text += "\nЩоб оформити замовлення, напишіть 'Оформлюємо' або викличте команду /checkout."
    await message.answer(text, parse_mode="Markdown")


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
        await message.answer("Ваш кошик порожній. Спочатку додайте печиво в кошик! 🍪")
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
        f"Дякуємо, що обираєте Cookie Shop! Наш менеджер скоро зв'яжеться з вами. 🍪✨"
    )
    await message.answer(order_success_msg, parse_mode="Markdown")


import bonuses


@dp.message(F.text)
async def handle_user_text(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        return

    user_id = message.from_user.id
    user_text = message.text

    if user_text and user_text.startswith("/"):
        return

    # 1. Зберігаємо повідомлення користувача
    storage.save_message(user_id, "user", user_text)

    # 2. Отримуємо повний контекст користувача
    history = storage.get_user_history(user_id)
    products = load_products()
    cart_info = cart.get_cart_total(user_id, products)
    user_b_val = bonuses.get_user_bonuses(user_id)
    user_orders = storage.get_orders(user_id=user_id)
    promos = web_server.load_promos()

    # 3. Викликаємо Сверхрозумного AI-менеджера
    ai_response = ai_manager.generate_reply(
        message=user_text,
        history=history,
        products=products,
        user_cart=cart_info["items"],
        user_bonuses=user_b_val,
        user_orders=user_orders,
        promos=promos
    )

    reply_text = ai_response.get("reply", "")
    action = ai_response.get("action", "question")
    product_id = ai_response.get("product_id")
    quantity = ai_response.get("quantity") or 1
    promo_code = ai_response.get("promo_code")

    # 4. Обробка розширених дій (actions)
    if action == "add_to_cart" and product_id:
        success, cart_msg = cart.add_to_cart(user_id, product_id, quantity, products)
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

    elif action == "make_offer":
        offered_price = ai_response.get("offered_price")
        admin_id = os.getenv("ADMIN_ID")
        if admin_id and product_id and offered_price:
            p_obj = next((p for p in products if p["id"] == product_id), None)
            p_title = p_obj["name"] if p_obj else f"Товар #{product_id}"
            p_price = p_obj["price"] if p_obj else 0.0

            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [
                    types.InlineKeyboardButton(text=f"✅ Прийняти ({offered_price} грн)", callback_data=f"offer_acc:{user_id}:{product_id}:{offered_price}"),
                    types.InlineKeyboardButton(text="❌ Відхилити", callback_data=f"offer_rej:{user_id}:{product_id}:{offered_price}")
                ]
            ])
            try:
                await bot.send_message(
                    chat_id=int(admin_id),
                    text=f"📥 **Нова пропозиція ціни (Торг)!**\n\n"
                         f"👤 Покупець ID: `{user_id}` (@{message.from_user.username or 'немає'})\n"
                         f"🛍️ Товар: **{p_title}**\n"
                         f"🏷️ Початкова ціна: **{p_price} грн**\n"
                         f"💰 Запропонована ціна: **{offered_price} грн**",
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
                reply_text += f"\n\n🤝 Дякуємо! Вашу пропозицію **{offered_price} грн** передано продавцю. Бот сповістить вас одразу після рішення!"
            except Exception as e:
                print(f"[Send Offer Error]: {e}")

    elif action == "manager":
        reply_text += "\n\n🔔 (Повідомлення передано менеджеру-людині)."

    # Зберігаємо та відправляємо відповідь бота
    storage.save_message(user_id, "assistant", reply_text)
    await message.answer(reply_text, parse_mode="Markdown")


async def main():
    print("Cookie Shop Bot starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
