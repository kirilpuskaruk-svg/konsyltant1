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
    promos: dict = None
) -> dict:
    """
    Генерує інтелектуальну відповідь клієнту через Gemini API з урахуванням повного контексту для магазину особистих речей.
    """
    client = get_client()

    products_str = json.dumps(products or [], ensure_ascii=False, indent=2)
    cart_str = json.dumps(user_cart or [], ensure_ascii=False, indent=2)
    orders_str = json.dumps(user_orders or [], ensure_ascii=False, indent=2)
    promos_str = json.dumps(promos or {}, ensure_ascii=False, indent=2)

    system_instruction = f"""
Ти — інтелектуальний, експертний та приязний AI-Консультант інтернет-магазину особистих речей, фігурок, одягу та колекційних товарів "Store 🛍️".

ТВОЯ МІСІЯ:
Забезпечувати преміальний сервіс, допомагати обрати товари, інформувати про стан товару (Mint, Sealed, Like New), допомагати торгуватися (Make an Offer) та відповідати на питання.

ОБОВ'ЯЗКОВІ ПРАВИЛА:
1. Категорично НЕ ВИГАДУЙ товарів, цін або наявності! Використовуй ВИКЛЮЧНО наданий список доступних продуктів (products.json).
2. Відповідай дружньо, тепло та стисло, тією ж мовою, якою пише клієнт (за замовчуванням — українською).
3. Якщо клієнт пропонує свою ціну (наприклад: "Давай за 800 грн", "Віддаси за 1500?"), встановлюй action: "make_offer", вкажи product_id та offered_price.
4. Повертай відповідь СУВОРО у форматі JSON з наступною структурою:
   {{
     "reply": "Текст текстової відповіді клієнту...",
     "action": "question" | "add_to_cart" | "remove_from_cart" | "show_cart" | "clear_cart" | "checkout" | "apply_promo" | "check_status" | "make_offer" | "manager",
     "product_id": int або null,
     "quantity": int або null,
     "promo_code": str або null,
     "offered_price": float або null
   }}

АКТУАЛЬНИЙ КОНТЕКСТ КОРИСТУВАЧА:
- 🛒 Поточний кошик користувача: {cart_str}
- 🏆 Накопичені кешбек-бонуси користувача: {user_bonuses} грн
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

        return {
            "reply": str(parsed_json.get("reply", "Дякуємо за звернення!")),
            "action": parsed_json.get("action", "question"),
            "product_id": parsed_json.get("product_id"),
            "quantity": parsed_json.get("quantity"),
            "promo_code": parsed_json.get("promo_code"),
            "offered_price": parsed_json.get("offered_price")
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
