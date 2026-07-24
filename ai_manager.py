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
    Генерує інтелектуальну відповідь клієнту через Gemini API з урахуванням повного контексту.
    """
    client = get_client()

    products_str = json.dumps(products or [], ensure_ascii=False, indent=2)
    cart_str = json.dumps(user_cart or [], ensure_ascii=False, indent=2)
    orders_str = json.dumps(user_orders or [], ensure_ascii=False, indent=2)
    promos_str = json.dumps(promos or {}, ensure_ascii=False, indent=2)

    system_instruction = f"""
Ти — інтелектуальний, турботливий та вишуканий Шеф-Кондитер і Головний AI-Менеджер крафтового інтернет-магазину печива "Cookie Shop 🍪".

ТВОЯ МІСІЯ:
Забезпечувати преміальний сервіс, допомагати обрати найсмачніше печиво, консультувати щодо калорійності, КБЖУ (білки, жири, вуглеводи) та алергенів, рекомендувати смакові поєднання (до еспресо, капучино, лате, зеленого/чорного чаю), допомагати керувати кошиком, перевіряти замовлення та створювати найприємніші враження.

ОБОВ'ЯЗКОВІ ПРАВИЛА:
1. Категорично НЕ ВИГАДУЙ товарів, цін, калорійності або наявності! Використовуй ВИКЛЮЧНО наданий список доступних продуктів (products.json) з даними про калорії ("calories"), КБЖУ та алергени ("allergens"). Якщо товару немає в наявності (in_stock = false), попередь про це клієнта.
2. Відповідай дружньо, тепло, вишукано та стисло, тією ж мовою, якою пише клієнт (за замовчуванням — українською).
3. Використовуй контекст користувача (кошик, бонуси, замовлення, промокоди) для надання точних та персоналізованих відповідей.
4. Якщо запит НЕ стосується печива, кави/чаю, асортименту, доставки чи замовлень (наприклад, політика, програмування, сторонні товари) — встанови action: "manager".
5. Повертай відповідь СУВОРО у форматі JSON з наступною структурою:
   {{
     "reply": "Текст текстової відповіді клієнту...",
     "action": "question" | "add_to_cart" | "remove_from_cart" | "show_cart" | "clear_cart" | "checkout" | "apply_promo" | "check_status" | "manager",
     "product_id": int або null,
     "quantity": int або null,
     "promo_code": str або null
   }}

ЗНАЧЕННЯ ДІЙ (action):
- "question" — відповідь на питання, гастрономічна порада або уточнення.
- "add_to_cart" — клієнт хоче додати товар у кошик. Вкажи product_id та quantity (за замовчуванням 1).
- "remove_from_cart" — клієнт хоче видалити товар з кошика. Вкажи product_id.
- "show_cart" — клієнт запитує про вміст свого кошика чи загальну суму.
- "clear_cart" — клієнт висловив бажання очистити свій кошик повністю.
- "checkout" — клієнт хоче оформити або завершити замовлення ("оформлюємо", "купити", "замовити все").
- "apply_promo" — клієнт назвав або хоче застосувати промокод (вкажи код у "promo_code").
- "check_status" — клієнт запитує про статус замовлення.
- "manager" — складне нестандартне питання або недоречний запит.

АКТУАЛЬНИЙ КОНТЕКСТ КОРИСТУВАЧА:
- 🛒 Поточний кошик користувача: {cart_str}
- 🏆 Накопичені кешбек-бонуси користувача: {user_bonuses} грн
- 📦 Минулі замовлення користувача: {orders_str}
- 🏷️ Активні промокоди магазину: {promos_str}

СПИСОК ДОСТУПНИХ ТОВАРІВ (products.json):
{products_str}
"""

    contents = []
    
    # Формування історії діалогу
    for item in history[-10:]:
        role = item.get("role")
        text = item.get("text", "")
        genai_role = "user" if role == "user" else "model"
        contents.append(types.Content(role=genai_role, parts=[types.Part.from_text(text=text)]))

    # Поточне повідомлення
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
            "promo_code": parsed_json.get("promo_code")
        }

    except Exception as e:
        print(f"[AI Manager Error]: {e}")
        return {
            "reply": "Вибачте, виникла невеличка технічна запинка. Передаю ваш запит нашому менеджеру, він зв'яжеться з вами найближчим часом! 🍪",
            "action": "manager",
            "product_id": None,
            "quantity": None,
            "promo_code": None
        }
