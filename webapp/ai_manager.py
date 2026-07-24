import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def get_client():
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in environment variables.")
    return genai.Client(api_key=GEMINI_API_KEY)


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
    Генерує інтелектуальну відповідь клієнту або адміну через Gemini API з підтримкою автоматичних адмін-дій.
    """
    client = get_client()

    products_str = json.dumps(products or [], ensure_ascii=False, indent=2)
    cart_str = json.dumps(user_cart or [], ensure_ascii=False, indent=2)
    orders_str = json.dumps(user_orders or [], ensure_ascii=False, indent=2)
    promos_str = json.dumps(promos or {}, ensure_ascii=False, indent=2)

    system_instruction = f"""
Ти — інтелектуальний, експертний та приязний AI-Консультант і головний Керуючий інтернет-магазину особистих речей, фігурок, одягу та колекційних товарів "Store 🛍️".

ТВОЯ МІСІЯ:
Забезпечувати преміальний сервіс, допомагати обрати товари, інформувати про стан товару (Mint, Sealed, Like New), допомагати торгуватися (Make an Offer) та керувати магазином.

ОБОВ'ЯЗКОВІ ПРАВИЛА:
1. Категорично НЕ ВИГАДУЙ товарів, цін або наявності! Використовуй ВИКЛЮЧНО наданий список доступних продуктів (products.json).
2. Відповідай дружньо, тепло та розгорнуто, тією ж мовою, якою пише користувач (за замовчуванням — українською або російською).
3. ЗАВЖДИ пиши повноцінне, приємне та змістовне повідомлення у полі "reply".
4. Якщо клієнт пропонує свою ціну (наприклад: "Давай за 800 грн", "Віддаси за 1500?"), встановлюй action: "make_offer", вкажи product_id та offered_price.
5. Повертай відповідь СУВОРО у форматі JSON.
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

    contents = []
    
    for item in history[-10:]:
        role = item.get("role")
        text = item.get("text", "")
        genai_role = "user" if role == "user" else "model"
        contents.append(types.Content(role=genai_role, parts=[types.Part.from_text(text=text)]))

    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.2,
            )
        )

        response_text = response.text.strip()
        parsed_json = json.loads(response_text)

        default_reply = (
            "Так, я бачу ваші адмін-права! 👑 Чим можу допомогти по управлінню магазином (додати товар, видалити розділ, створити промокод тощо)?"
            if is_admin
            else "Вітаю! Чим можу допомогти?"
        )

        return {
            "reply": str(parsed_json.get("reply") or default_reply),
            "action": str(parsed_json.get("action") or "question"),
            "product_id": parsed_json.get("product_id"),
            "quantity": parsed_json.get("quantity"),
            "promo_code": parsed_json.get("promo_code"),
            "offered_price": parsed_json.get("offered_price"),
            "product_name": parsed_json.get("product_name"),
            "product_price": parsed_json.get("product_price"),
            "category_name": parsed_json.get("category_name"),
            "condition": parsed_json.get("condition"),
            "description": parsed_json.get("description"),
            "discount_percent": parsed_json.get("discount_percent"),
            "new_status": parsed_json.get("new_status")
        }

    except Exception as e:
        print(f"[AI Manager Error]: {e}")
        return {
            "reply": "Вибачте, виникла невеличка технічна запинка. Передаю ваш запит нашому менеджеру, він зв'яжеться з вами найближчим часом! 🛍️",
            "action": "manager",
            "product_id": None,
            "quantity": None,
            "promo_code": None,
            "offered_price": None
        }
