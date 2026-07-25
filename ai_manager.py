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

    # Admin actions fallback
    if is_admin:
        if "адмін" in msg_lower or "права" in msg_lower or "статус" in msg_lower:
            return {
                "reply": "Так, я підтверджую ваші адмін-права! 👑 Я можу керувати товарами, категоріями, промокодами та замовленнями.",
                "action": "question"
            }

    # Product search / inventory query
    matching_prods = []
    stop_words = {"про", "для", "які", "хто", "чем", "що", "або", "при", "від"}
    words = [w for w in msg_lower.split() if len(w) > 2 and w not in stop_words]

    for p in products:
        p_name = (p.get("name") or "").lower()
        p_desc = (p.get("description") or "").lower()
        p_cat = (p.get("category") or "").lower()
        if any(w in p_name or w in p_desc or w in p_cat for w in words):
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
    Генерує відповідь клієнту через Gemini API з підтримкою автоматичних адмін-розсилок та дій.
    """
    products_str = json.dumps(products or [], ensure_ascii=False, indent=2)
    cart_str = json.dumps(user_cart or [], ensure_ascii=False, indent=2)
    orders_str = json.dumps(user_orders or [], ensure_ascii=False, indent=2)
    promos_str = json.dumps(promos or {}, ensure_ascii=False, indent=2)

    system_instruction = f"""
Ти — інтелектуальний AI-Консультант та Керуючий інтернет-магазину "Store & Collectibles 🛍️".

ТВОЯ МІСІЯ:
Допомагати клієнтам обирати товари (фігурки, одяг, колекційні товари), відповідати на питання та обробляти команди.

МОЖЛИВІ ДІЇ КОРИСТУВАЧА (action):
- "question": Звичайне запитання або консультація.
- "add_to_cart": Додати товар в кошик (product_id: int, quantity: int).
- "remove_from_cart": Видалити товар з кошика (product_id: int).
- "checkout": Оформити замовлення.
- "apply_promo": Застосувати промокод (promo_code: str).

ОБОВ'ЯЗКОВІ ПРАВИЛА:
1. Категорично НЕ ВИГАДУЙ товарів чи цін! Використовуй ВИКЛЮЧНО наданий список доступних продуктів (products.json).
2. Відповідай дружньо, тепло та розгорнуто, тією ж мовою, якою пише користувач (українською або англійською/російською).
3. ЗАВЖДИ повертай JSON об'єкт з обов'язковими полями: "reply" та "action".
"""

    if is_admin:
        system_instruction += """
👑 АДМІНІСТРАТИВНІ МОЖЛИВОСТІ (КОРИСТУВАЧ — АДМІНІСТРАТОР ВАШОГО МАГАЗИНУ):
Зараз ви спілкуєтеся з АДМІНІСТРАТОРОМ магазину!
Доступні адмін-дії:
- Додати товар: action: "admin_add_product", product_name: str, product_price: float, category_name: str, condition: str, description: str
- Видалити товар: action: "admin_delete_product", product_id: int, product_name: str
- Додати категорію: action: "admin_add_category", category_name: str
- Видалити категорію: action: "admin_delete_category", category_name: str
- Додати промокод: action: "admin_add_promo", promo_code: str, discount_percent: int
- Змінити статус замовлення: action: "admin_update_order", order_id: int, new_status: str ("new", "processing", "completed", "cancelled")
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

        response = None
        for m_name in ["gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-1.5-flash"]:
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
            cleaned_text = re.sub(r'^```json\s*|^```\s*|```$', '', response.text.strip(), flags=re.MULTILINE).strip()
            parsed_json = json.loads(cleaned_text)

            p_id = parsed_json.get("product_id")
            if p_id is not None:
                try:
                    p_id = int(p_id)
                except (ValueError, TypeError):
                    pass

            o_id = parsed_json.get("order_id")
            if o_id is not None:
                try:
                    o_id = int(o_id)
                except (ValueError, TypeError):
                    pass

            return {
                "reply": str(parsed_json.get("reply") or "Вітаю! Чим можу допомогти?"),
                "action": str(parsed_json.get("action") or "question"),
                "broadcast_text": parsed_json.get("broadcast_text"),
                "product_id": p_id,
                "order_id": o_id,
                "quantity": parsed_json.get("quantity", 1),
                "product_name": parsed_json.get("product_name"),
                "product_price": parsed_json.get("product_price"),
                "category_name": parsed_json.get("category_name"),
                "condition": parsed_json.get("condition"),
                "description": parsed_json.get("description"),
                "promo_code": parsed_json.get("promo_code"),
                "discount_percent": parsed_json.get("discount_percent"),
                "new_status": parsed_json.get("new_status")
            }
    except Exception as e:
        print(f"[AI Manager Exception]: {e}")

    return fallback_reply(message, products, is_admin, promos)
