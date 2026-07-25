import json
import os
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def get_client():
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in environment variables.")
    return genai.Client(api_key=GEMINI_API_KEY)


def fallback_reply(message: str, products: list, is_admin: bool, promos: dict = None) -> dict:
    msg_lower = message.lower().strip()

    # Admin actions
    if is_admin:
        if "адмін" in msg_lower or "права" in msg_lower or "статус" in msg_lower:
            return {
                "reply": "Так, я підтверджую ваші адмін-права! 👑 Я можу керувати товарами, категоріями, промокодами та замовленнями.",
                "action": "question"
            }

    # Product search / inventory query
    matching_prods = []
    for p in products:
        p_name = (p.get("name") or "").lower()
        p_desc = (p.get("description") or "").lower()
        p_cat = (p.get("category") or "").lower()
        if any(w in p_name or w in p_desc or w in p_cat for w in msg_lower.split() if len(w) > 2):
            matching_prods.append(p)

    if matching_prods:
        lines = ["🛍️ **Знайдено товари за вашим запитом:**\n"]
        for p in matching_prods[:3]:
            lines.append(f"• **{p.get('name')}** — {p.get('price')} ₴ ({p.get('condition', 'New')})\n  _{p.get('description')}_")
        return {
            "reply": "\n\n".join(lines) + "\n\nВи можете відкрити Mini App для зручного замовлення! 🛒",
            "action": "question"
        }

    # General store products overview
    if any(k in msg_lower for k in ["товари", "що є", "асортимент", "каталог", "покажи", "наявність", "продукція"]):
        lines = ["✨ **Наш актуальний асортимент:**\n"]
        for p in products[:5]:
            lines.append(f"• **{p.get('name')}** — `{p.get('price')} ₴`")
        return {
            "reply": "\n".join(lines) + "\n\nСкористайтеся Mini App кнопку внизу для перегляду з фото! 🧸",
            "action": "question"
        }

    # Promos query
    if any(k in msg_lower for k in ["промокод", "знижк", "акція", "купон"]):
        if promos:
            p_list = [f"• `{code}` ({info.get('discount_percent', 10)}%)" for code, info in promos.items() if info.get("active", True)]
            if p_list:
                return {
                    "reply": "🏷️ **Активні промокоди нашого магазину:**\n\n" + "\n".join(p_list) + "\n\nВводьте їх при оформленні в Mini App!",
                    "action": "question"
                }
        return {
            "reply": "🏷️ Акційні промокоди можна дізнатися у розсилочних анонсах або при підписці на наш канал!",
            "action": "question"
        }

    # Default friendly consultant reply
    return {
        "reply": "Вітаю у нашому магазині Store & Collectibles! 🧸✨ Надішліть будь-яке запитання про наші фігурки, мерч чи колекційні речі, або відкрийте Mini App у меню нижче! 🛍️",
        "action": "question"
    }


def generate_reply(
    message: str,
    history: list,
    products: list,
    user_cart: list = None,
    user_bonuses: float = 0.0,
    user_orders: list = None,
    promos: dict = None,
    is_admin: bool = False
) -> dict:
    """
    Генерує відповідь клієнту через Gemini API з надійним смарт-фолбеком при вичерпанні лімітів API.
    """
    products_str = json.dumps(products or [], ensure_ascii=False, indent=2)
    cart_str = json.dumps(user_cart or [], ensure_ascii=False, indent=2)
    orders_str = json.dumps(user_orders or [], ensure_ascii=False, indent=2)
    promos_str = json.dumps(promos or {}, ensure_ascii=False, indent=2)

    system_instruction = f"""
Ти — інтелектуальний, експертний та приязний AI-Консультант і головний Керуючий інтернет-магазину особистих речей, фігурок, одягу та колекційних товарів "Store 🛍️".

ТВОЯ МІСІЯ:
Забезпечувати преміальний сервіс, допомагати обрати товари, інформувати про стан товару (Mint, Sealed, Like New) та керувати магазином.

ОБОВ'ЯЗКОВІ ПРАВИЛА:
1. Категорично НЕ ВИГАДУЙ товарів, цін або наявності! Використовуй ВИКЛЮЧНО наданий список доступних продуктів (products.json).
2. Відповідай дружньо, тепло та розгорнуто, тією ж мовою, якою пише користувач (за замовчуванням — українською або російською).
3. ЗАВЖДИ пиши повноцінне, приємне та змістовне повідомлення у полі "reply".
4. Повертай відповідь СУВОРО у форматі JSON.
"""

    if is_admin:
        system_instruction += """
👑 АДМІНІСТРАТИВНІ МОЖЛИВОСТІ (КОРИСТУВАЧ — АДМІНІСТРАТОР ВАШОГО МАГАЗИНУ):
Зараз ви спілкуєтеся з АДМІНІСТРАТОРОМ магазину!
Якщо він запитує про свій статус, адмінку чи права (наприклад "ти видишь у меня админку?"), обов'язково підтверди у полі "reply", що ти бачиш його адмін-права (👑) та напиши, що ти готовий виконувати його вказівки щодо товарів, категорій, замовлень і промокодів.

Якщо він просить виконати конкретну дію у текстовій формі (наприклад: "Додай товар Наруто за 1500 грн в категорію Фігурки", "Видали товар ID 2", "Створи новий розділ Іграшки", "Видали категорію Одяг", "Додай промокод SALE10 на 10%", "Зміни статус замовлення 3 на completed"):
Ти повинен відповісти ствердно в "reply" та встановити відповідний action і параметри:

- Додати товар: action: "admin_add_product", "product_name": str, "product_price": float, "category_name": str, "condition": str, "description": str
- Видалити товар: action: "admin_delete_product", "product_id": int або "product_name": str
- Додати категорію/розділ: action: "admin_add_category", "category_name": str
- Видалити категорію/розділ: action: "admin_delete_category", "category_name": str
- Додати промокод: action: "admin_add_promo", "promo_code": str, "discount_percent": int
- Змінити статус замовлення: action: "admin_update_order", "order_id": int, "new_status": str ("new", "processing", "completed", "cancelled")
"""

    system_instruction += f"""
АКТУАЛЬНИЙ КОНТЕКСТ КОРИСТУВАЧА:
- 🛒 Поточний кошик користувача: {cart_str}
- 💰 Накопичені кешбек-бонуси користувача: {user_bonuses} грн
- 📦 Минулі замовлення користувача: {orders_str}
- 🏷️ Активні промокоди магазину: {promos_str}

СПИСОК ДОСТУПНИХ ТОВАРІВ (products.json):
{products_str}
"""

    try:
        client = get_client()
        contents = []
        for item in history[-10:]:
            role = item.get("role")
            text = item.get("text", "")
            genai_role = "user" if role == "user" else "model"
            contents.append(types.Content(role=genai_role, parts=[types.Part.from_text(text=text)]))

        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))

        # Try gemini models in order of preference
        response = None
        for m_name in ["gemini-3.5-flash-lite", "gemini-2.0-flash-lite", "gemini-2.5-flash-lite"]:
            try:
                response = client.models.generate_content(
                    model=m_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        temperature=0.2,
                    )
                )
                if response and response.text:
                    break
            except Exception as m_err:
                print(f"[Gemini Model {m_name} Error]: {m_err}")

        if response and response.text:
            response_text = response.text.strip()
            parsed_json = json.loads(response_text)
            return {
                "reply": str(parsed_json.get("reply") or "Вітаю! Чим можу допомогти?"),
                "action": str(parsed_json.get("action") or "question"),
                "product_id": parsed_json.get("product_id"),
                "quantity": parsed_json.get("quantity"),
                "product_name": parsed_json.get("product_name"),
                "product_price": parsed_json.get("product_price"),
                "category_name": parsed_json.get("category_name"),
                "condition": parsed_json.get("condition"),
                "description": parsed_json.get("description"),
                "discount_percent": parsed_json.get("discount_percent"),
                "new_status": parsed_json.get("new_status")
            }
    except Exception as e:
        print(f"[AI Manager Exception]: {e}")

    # Seamless Smart Fallback if Gemini quota is exhausted
    return fallback_reply(message, products, is_admin, promos)
