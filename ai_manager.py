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

def generate_reply(message: str, history: list, products: list) -> dict:
    """
    Генерує відповідь клієнту через Gemini API.

    Параметри:
    - message (str): Нове повідомлення клієнта.
    - history (list): Історія діалогу [{"role": "user"/"assistant", "text": "..."}, ...]
    - products (list): Список товарів з products.json

    Повертає dict в форматі:
    {
      "reply": "Текст відповіді клієнту...",
      "action": "question" | "add_to_cart" | "remove_from_cart" | "checkout" | "manager",
      "product_id": int або None,
      "quantity": int або None
    }
    """
    client = get_client()

    products_str = json.dumps(products, ensure_ascii=False, indent=2)

    system_instruction = f"""
Ти — ввічливий, приязний та розумний AI-менеджер інтернет-магазину печива "Cookie Shop 🍪".

ОСНОВНІ ПРАВИЛА:
1. Категорично НЕ ВИГАДУЙ товарів, цін, складу або наявності! Всі товари беруться ВИКЛЮЧНО зі списку доступних продуктів.
2. Радити тільки те печиво, яке є у наданому списку (products.json). Якщо товару немає в наявності (in_stock = false), попередь про це клієнта.
3. Відповідай коротко, дружньо, тією ж мовою, якою пише клієнт (за замовчуванням — українською).
4. Якщо незрозуміло, який саме товар потрібен клієнту або яка кількість — ставай уточнювальне питання ("reply") і зазначай action "question".
5. Якщо запит НЕ стосується печива, асортименту або доставки печива (наприклад, питання про політику, програмування, сторонні товари чи незрозумілий спам) — встанови action: "manager".
6. Повертай БУДЬ-ЯКУ відповідь СУВОРО у форматі JSON з наступними полями:
   - "reply": Текстова відповідь клієнту.
   - "action": Одне з п'яти значень:
       * "question" — якщо клієнт просто щось запитує, уточнює або ти ставиш уточнювальне питання.
       * "add_to_cart" — якщо клієнт висловив бажання додати певний товар у кошик.
       * "remove_from_cart" — якщо клієнт хоче прибрати товар з кошика.
       * "checkout" — якщо клієнт висловив бажання оформити/завершити замовлення (наприклад, "оформлюємо", "хочу замовити", "купити вміст кошика").
       * "manager" — якщо бот не знає відповіді, запит не по темі або потрібна допомога людини.
   - "product_id": ID товару (ціле число), до якого застосовується action "add_to_cart" чи "remove_from_cart". Якщо action інший або product_id невизначений — null.
   - "quantity": Кількість товару (ціле число), яку бажає додати/видалити клієнт. За замовчуванням 1, якщо не вказано інше. Якщо action інший — null.

СПИСОК ДОСТУПНИХ ТОВАРІВ (products.json):
{products_str}
"""

    contents = []
    
    # Формування історії діалогу
    for item in history:
        role = item.get("role")
        text = item.get("text", "")
        # Перетворення ролей на зрозумілі для Gemini
        genai_role = "user" if role == "user" else "model"
        contents.append(types.Content(role=genai_role, parts=[types.Part.from_text(text=text)]))

    # Додавання поточного повідомлення
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.2,
            )
        )

        response_text = response.text.strip()
        parsed_json = json.loads(response_text)

        # Валідація структури JSON
        return {
            "reply": str(parsed_json.get("reply", "Дякуємо за звернення!")),
            "action": parsed_json.get("action", "question"),
            "product_id": parsed_json.get("product_id"),
            "quantity": parsed_json.get("quantity")
        }

    except Exception as e:
        # У разі помилки виклику або парсингу повертаємо безпечний фолбек з передачею менеджеру
        return {
            "reply": "Вибачте, виникла невеличка технічна запинка. Передаю ваше запит нашому менеджеру, він зв'яжеться з вами найближчим часом! 🍪",
            "action": "manager",
            "product_id": None,
            "quantity": None
        }
