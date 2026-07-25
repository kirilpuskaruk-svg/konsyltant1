import os
import csv
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

import storage
import cart

router = Router()


class AdminAddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()


class AdminEditPrice(StatesGroup):
    product_id = State()
    price = State()


class AdminBroadcast(StatesGroup):
    text = State()


def get_admin_ids() -> list:
    admin_id_env = os.getenv("ADMIN_ID", "")
    if admin_id_env:
        return [x.strip() for x in str(admin_id_env).replace(";", ",").split(",") if x.strip()]
    return []


def is_admin(user_id: int) -> bool:
    admin_ids = get_admin_ids()
    if not admin_ids:
        # Fallback: if ADMIN_ID is not set in env, allow access for testing/setup
        return True
    return str(user_id) in admin_ids


def get_main_admin_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📦 Замовлення", callback_data="admin_orders_all"),
            InlineKeyboardButton(text="🛍️ Асортимент", callback_data="admin_products")
        ],
        [
            InlineKeyboardButton(text="🗂️ Керування Розділами", callback_data="admin_categories"),
            InlineKeyboardButton(text="📢 Розсилка", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="🏷️ Промокоди", callback_data="admin_promos")
        ],
        [
            InlineKeyboardButton(text="📄 Експорт TXT", callback_data="admin_export_txt"),
            InlineKeyboardButton(text="📁 Експорт CSV", callback_data="admin_export_csv")
        ]
    ])
    return keyboard


@router.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    try:
        await state.clear()
        user_id = message.from_user.id
        if not is_admin(user_id):
            await message.answer(
                f"⛔ У вас немає прав доступу до адмін-панелі.\n\n📍 Ваш Telegram ID: {user_id}\n\nЩоб отримати доступ, додайте цей ID у налаштування ADMIN_ID!"
            )
            return

        welcome_text = (
            "⚙️ Панель Адміністратора Store 🛍️\n\n"
            "Оберіть необхідний розділ для керування магазином:"
        )
        await message.answer(welcome_text, reply_markup=get_main_admin_keyboard())
    except Exception as e:
        print(f"[cmd_admin Error]: {e}")
        await message.answer("⚙️ Панель Адміністратора Store 🛍️", reply_markup=get_main_admin_keyboard())


@router.callback_query(F.data == "admin_menu")
async def cb_admin_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Немає доступу.", show_alert=True)
        return

    text = "⚙️ **Панель Адміністратора Cookie Shop** 🍪\n\nОберіть розділ:"
    await callback.message.edit_text(text, reply_markup=get_main_admin_keyboard(), parse_mode="Markdown")
    await callback.answer()


# ==================== 1. ЗАМОВЛЕННЯ ====================

@router.callback_query(F.data & F.data.startswith("admin_orders_"))
async def cb_admin_orders(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    status_filter = callback.data.replace("admin_orders_", "")
    orders = storage.get_orders(status=status_filter)

    status_titles = {
        "all": "Усі замовлення",
        "new": "Нові замовлення 🆕",
        "processing": "В обробці ⏳",
        "completed": "Виконані ✅",
        "cancelled": "Скасовані ❌"
    }
    title = status_titles.get(status_filter, "Замовлення")

    text = f"📦 **{title}** (Всього: {len(orders)}):\n\n"

    buttons = [
        [
            InlineKeyboardButton(text="Усі", callback_data="admin_orders_all"),
            InlineKeyboardButton(text="Нові 🆕", callback_data="admin_orders_new"),
            InlineKeyboardButton(text="В обробці ⏳", callback_data="admin_orders_processing")
        ],
        [
            InlineKeyboardButton(text="Виконані ✅", callback_data="admin_orders_completed"),
            InlineKeyboardButton(text="Скасовані ❌", callback_data="admin_orders_cancelled")
        ]
    ]

    if not orders:
        text += "Замовлень не знайдено."
    else:
        for o in orders[:8]: # Show top 8
            o_id = o.get("order_id")
            o_name = o.get("name", "Клієнт")
            o_total = o.get("total_price", 0)
            o_st = o.get("status", "new")

            st_emoji = {"new": "🆕", "processing": "⏳", "completed": "✅", "cancelled": "❌"}.get(o_st, "📌")
            btn_text = f"#{o_id} | {o_name} | {o_total} грн | {st_emoji}"
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"admin_order_detail_{o_id}")])

    buttons.append([InlineKeyboardButton(text="« Назад в меню", callback_data="admin_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data & F.data.startswith("admin_order_detail_"))
async def cb_order_detail(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    order_id = callback.data.replace("admin_order_detail_", "")
    order = storage.get_order_by_id(order_id)

    if not order:
        await callback.answer("Замовлення не знайдено.", show_alert=True)
        return

    items_text = ""
    for item in order.get("items", []):
        p_name = item.get("name") or f"Печиво #{item.get('product_id')}"
        qty = item.get("quantity", 1)
        subtotal = item.get("subtotal") or (item.get("price", 0) * qty)
        items_text += f"• {p_name} — {qty} шт. ({subtotal} грн)\n"

    status_labels = {
        "new": "🆕 Нове",
        "processing": "⏳ В обробці",
        "completed": "✅ Виконано",
        "cancelled": "❌ Скасовано"
    }

    text = (
        f"📝 **Замовлення #{order.get('order_id')}**\n"
        f"👤 **Клієнт**: {order.get('name')}\n"
        f"📞 **Телефон**: {order.get('phone')}\n"
        f"📍 **Адреса**: {order.get('address')}\n"
        f"Статус: **{status_labels.get(order.get('status'), order.get('status'))}**\n\n"
        f"🛒 **Товари**:\n{items_text}\n"
        f"💰 **Загальна сума**: {order.get('total_price')} грн"
    )

    buttons = [
        [
            InlineKeyboardButton(text="⏳ В обробку", callback_data=f"admin_set_status_{order_id}_processing"),
            InlineKeyboardButton(text="✅ Виконати", callback_data=f"admin_set_status_{order_id}_completed")
        ],
        [
            InlineKeyboardButton(text="❌ Скасувати", callback_data=f"admin_set_status_{order_id}_cancelled")
        ],
        [
            InlineKeyboardButton(text="« До замовлень", callback_data="admin_orders_all")
        ]
    ]

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data & F.data.startswith("admin_set_status_"))
async def cb_set_status(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return

    parts = callback.data.split("_")
    order_id = parts[3]
    new_status = parts[4]

    updated_order = storage.update_order_status(order_id, new_status)
    if updated_order:
        await callback.answer(f"Статус змінено на '{new_status}'!", show_alert=True)

        # Сповіщення покупця у Telegram
        user_id = updated_order.get("user_id")
        if user_id:
            status_msgs = {
                "processing": f"⏳ Ваше замовлення #{order_id} прийнято в обробку!",
                "completed": f"🎉 Ваше замовлення #{order_id} успішно виконано та прямує до вас!",
                "cancelled": f"❌ Ваше замовлення #{order_id} скасовано. Якщо у вас виникли питання, зв'яжіться з нами."
            }
            user_msg = status_msgs.get(new_status)
            if user_msg:
                try:
                    await bot.send_message(chat_id=user_id, text=user_msg)
                except Exception as e:
                    print(f"Could not notify user {user_id}: {e}")

        # Повертаємось до деталей замовлення
        callback.data = f"admin_order_detail_{order_id}"
        await cb_order_detail(callback)


# ==================== 2. АСОРТИМЕНТ ТОВАРІВ ====================

@router.callback_query(F.data == "admin_products")
async def cb_admin_products(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    products = cart._load_products()
    text = "🍪 **Керування Асортиментом Печива**:\n\nОберіть товар для редагування або додайте новий:"

    buttons = []
    for p in products:
        p_id = p.get("id")
        p_name = p.get("name")
        p_price = p.get("price")
        stock_icon = "🟢" if p.get("in_stock", True) else "🔴"
        btn_text = f"{stock_icon} #{p_id} {p_name} ({p_price} грн)"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"admin_prod_detail_{p_id}")])

    buttons.append([InlineKeyboardButton(text="➕ Додати нове печиво", callback_data="admin_add_product")])
    buttons.append([InlineKeyboardButton(text="« Назад в меню", callback_data="admin_menu")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data & F.data.startswith("admin_prod_detail_"))
async def cb_product_detail(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    prod_id = int(callback.data.replace("admin_prod_detail_", ""))
    products = cart._load_products()
    prod = next((p for p in products if p.get("id") == prod_id), None)

    if not prod:
        await callback.answer("Товар не знайдено.", show_alert=True)
        return

    stock_str = "🟢 В наявності" if prod.get("in_stock", True) else "🔴 Немає в наявності"

    text = (
        f"🍪 **{prod.get('name')}** (ID: #{prod.get('id')})\n\n"
        f"📝 **Опис**: {prod.get('description')}\n"
        f"💰 **Ціна**: {prod.get('price')} грн\n"
        f"📦 **Статус**: {stock_str}"
    )

    toggle_btn_text = "🔴 Позначити 'Немає'" if prod.get("in_stock", True) else "🟢 Позначити 'В наявності'"

    buttons = [
        [
            InlineKeyboardButton(text=toggle_btn_text, callback_data=f"admin_prod_toggle_{prod_id}"),
            InlineKeyboardButton(text="✏️ Змінити ціну", callback_data=f"admin_prod_editprice_{prod_id}")
        ],
        [
            InlineKeyboardButton(text="🗑️ Видалити товар", callback_data=f"admin_prod_delete_{prod_id}")
        ],
        [
            InlineKeyboardButton(text="« Назад до асортименту", callback_data="admin_products")
        ]
    ]

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data & F.data.startswith("admin_prod_toggle_"))
async def cb_toggle_stock(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    prod_id = int(callback.data.replace("admin_prod_toggle_", ""))
    cart.toggle_product_stock(prod_id)
    await callback.answer("Статус наявності успішно змінено!")

    callback.data = f"admin_prod_detail_{prod_id}"
    await cb_product_detail(callback)


@router.callback_query(F.data & F.data.startswith("admin_prod_delete_"))
async def cb_delete_product(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    prod_id = int(callback.data.replace("admin_prod_delete_", ""))
    cart.delete_product(prod_id)
    await callback.answer("Товар успішно видалено!", show_alert=True)

    callback.data = "admin_products"
    await cb_admin_products(callback)


# --- Додавання товару ---

@router.callback_query(F.data == "admin_add_product")
async def cb_start_add_product(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminAddProduct.name)
    await callback.message.edit_text(
        "➕ **Додавання нового печива**\n\nВведіть **назву** нового печива:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Скасувати", callback_data="admin_products")]]),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(AdminAddProduct.name)
async def process_add_prod_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminAddProduct.description)
    await message.answer("Тепер введіть **короткий опис** печива:")


@router.message(AdminAddProduct.description)
async def process_add_prod_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AdminAddProduct.price)
    await message.answer("Тепер введіть **ціну** печива (число у грн, наприклад: 120):")


@router.message(AdminAddProduct.price)
async def process_add_prod_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", ".").strip())
    except ValueError:
        await message.answer("Будь ласка, введіть коректну ціну числом (наприклад, 135):")
        return

    data = await state.get_data()
    cart.add_product(name=data["name"], description=data["description"], price=price, in_stock=True)
    await state.clear()

    await message.answer(f"🎉 **Нове печиво '{data['name']}' успішно додано до каталогу!**")


# --- Зміна ціни ---

@router.callback_query(F.data & F.data.startswith("admin_prod_editprice_"))
async def cb_start_edit_price(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    prod_id = int(callback.data.replace("admin_prod_editprice_", ""))
    await state.update_data(edit_product_id=prod_id)
    await state.set_state(AdminEditPrice.price)

    await callback.message.edit_text(
        f"✏️ **Зміна ціни для печива #{prod_id}**\n\nВведіть нову ціну (у грн):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Скасувати", callback_data=f"admin_prod_detail_{prod_id}")]])
    )
    await callback.answer()


@router.message(AdminEditPrice.price)
async def process_edit_price(message: types.Message, state: FSMContext):
    try:
        new_price = float(message.text.replace(",", ".").strip())
    except ValueError:
        await message.answer("Будь ласка, введіть ціну числом:")
        return

    data = await state.get_data()
    prod_id = data.get("edit_product_id")
    cart.update_product_price(prod_id, new_price)
    await state.clear()

    await message.answer(f"✅ **Ціну для товару #{prod_id} успішно змінено на {new_price} грн!**")


# ==================== 3. СТАТИСТИКА ====================

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    stats = storage.get_analytics_summary()

    top_text = ""
    for item_name, count in stats["top_products"]:
        top_text += f"• {item_name}: **{count} шт.**\n"
    if not top_text:
        top_text = "Даних поки немає\n"

    text = (
        "📊 **Аналітика та Статистика Магазину** 🍪\n\n"
        f"📦 **Всього замовлень**: {stats['total_orders']}\n"
        f"✅ **Виконаних замовлень**: {stats['completed_orders']}\n"
        f"💰 **Загальний виторг**: {stats['total_revenue']} грн\n"
        f"🏷️ **Середній чек**: {stats['avg_check']} грн\n"
        f"👥 **Унікальних клієнтів**: {stats['unique_users']}\n\n"
        f"🏆 **Топ-3 найпопулярніших товарів**:\n{top_text}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Назад в меню", callback_data="admin_menu")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


# ==================== 4. МАСОВА РОЗСИЛКА ====================

@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    users_count = len(storage.get_all_user_ids())
    await state.set_state(AdminBroadcast.text)

    text = (
        "📢 **Масова Розсилка Повідомлень**\n\n"
        f"Знайдено покупців у базі: **{users_count}**\n\n"
        "Надішліть текст розсилки, який отримають усі користувачі:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Скасувати", callback_data="admin_menu")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.message(AdminBroadcast.text)
async def process_broadcast(message: types.Message, state: FSMContext, bot: Bot):
    broadcast_text = message.text
    user_ids = storage.get_all_user_ids()
    await state.clear()

    await message.answer(f"⏳ Розсилка запущена для {len(user_ids)} користувачів...")

    success_count = 0
    fail_count = 0

    for uid in user_ids:
        try:
            await bot.send_message(chat_id=int(uid), text=broadcast_text)
            success_count += 1
        except Exception:
            fail_count += 1

    await message.answer(
        f"📢 **Розсилка завершена!**\n\n"
        f"✅ Успішно доставлено: **{success_count}**\n"
        f"❌ Помилок (заблокували бота): **{fail_count}**"
    )


# ==================== 5. ЕКСПОРТ (TXT / CSV) ====================

@router.callback_query(F.data == "admin_export_txt")
async def cb_export_txt(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    txt_file = storage.export_orders_txt()
    document = FSInputFile(txt_file, filename="orders_export.txt")

    await callback.message.answer_document(document, caption="📄 Ось експорт усіх замовлень у TXT файлі!")
    await callback.answer()


@router.callback_query(F.data == "admin_export_csv")
async def cb_export_csv(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    csv_file = storage.export_orders_csv()
    document = FSInputFile(csv_file, filename="orders_export.csv")

    await callback.message.answer_document(document, caption="📊 Ось експорт усіх замовлень у CSV файлі!")
    await callback.answer()


# ==================== 6. ПРОМОКОДИ ====================

@router.callback_query(F.data == "admin_promos")
async def cb_admin_promos(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    promos = {}
    if os.path.exists("promos.json"):
        try:
            with open("promos.json", "r", encoding="utf-8") as f:
                promos = json.load(f)
        except Exception:
            pass

    text = "🏷️ **Активні Промокоди Магазину**:\n\n"
    if not promos:
        text += "Промокодів не знайдено."
    else:
        for code, info in promos.items():
            st = "✅ Активний" if info.get("active", True) else "🔴 Неактивний"
            text += f"• **{code}**: знижка **{info.get('discount_percent', 0)}%** ({st})\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Назад в меню", callback_data="admin_menu")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()




# ==================== 8. КЕРУВАННЯ КАТЕГОРІЯМИ ====================

import categories


class CategoryState(StatesGroup):
    waiting_for_category_name = State()


@router.callback_query(F.data == "admin_categories")
async def cb_admin_categories(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    cats = categories.load_categories()
    products = load_products()

    text = "🗂️ **Керування Розділами/Категоріями Магазину**:\n\n"
    for cat in cats:
        count = sum(1 for p in products if p.get("category") == cat)
        text += f"• **{cat}** — {count} товар(ів)\n"

    kb_buttons = [
        [InlineKeyboardButton(text="➕ Додати новий розділ", callback_data="admin_cat_add")],
    ]

    for cat in cats:
        kb_buttons.append([
            InlineKeyboardButton(text=f"❌ Видалити «{cat}»", callback_data=f"admin_cat_del:{cat}")
        ])

    kb_buttons.append([InlineKeyboardButton(text="« Назад в меню", callback_data="admin_menu")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admin_cat_add")
async def cb_admin_cat_add(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(CategoryState.waiting_for_category_name)
    await callback.message.answer("✏️ Введіть назву нового розділу/категорії:")
    await callback.answer()


@router.message(CategoryState.waiting_for_category_name)
async def process_new_category_name(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    cat_name = message.text.strip()
    if categories.add_category(cat_name):
        await message.answer(f"🎉 Розділ **«{cat_name}»** успішно додано!", parse_mode="Markdown")
    else:
        await message.answer("⚠️ Такий розділ вже існує або введено некоректну назву.")

    await state.clear()


@router.callback_query(F.data & F.data.startswith("admin_cat_del:"))
async def cb_admin_cat_del(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    cat_name = callback.data.split(":", 1)[1]
    if categories.delete_category(cat_name):
        await callback.answer(f"Розділ «{cat_name}» видалено!")
    else:
        await callback.answer("Помилка видалення.")

    await cb_admin_categories(callback)
