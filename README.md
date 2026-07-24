# 🍪 Telegram-бот для магазину печива "Cookie Shop"

Інтелектуальний Telegram-бот для продажу печива з підтримкою AI-консультанта на базі **Gemini API**.

---

## 👥 Розподіл ролей розробки

1. **Киріл — AI-менеджер** (`feature/ai-manager`):
   - Модуль [`ai_manager.py`](file:///C:/Users/Alla/.gemini/antigravity/scratch/cookie-shop-telegram-bot/ai_manager.py).
   - Інтеграція з Gemini API, генерація відповіді у форматі JSON (`reply`, `action`, `product_id`, `quantity`).
   - Системні правила AI-консультанта (не вигадувати товари, радити за каталогом, відповідати мовою клієнта).

2. **Ярік — Кошик та оформлення замовлень** (`feature/cart-orders`):
   - Модулі [`cart.py`](file:///C:/Users/Alla/.gemini/antigravity/scratch/cookie-shop-telegram-bot/cart.py) та [`storage.py`](file:///C:/Users/Alla/.gemini/antigravity/scratch/cookie-shop-telegram-bot/storage.py).
   - Збереження даних у `orders.json`, `carts.json`, `history.json`.

3. **Базова частина**:
   - `products.json` — каталог із 6 видами печива.
   - `main.py` — обробник команд Telegram (`aiogram 3.x`).

---

## 🚀 Інструкція із запуску

### 1. Клонування репозиторію
```bash
git clone https://github.com/kirilpuskaruk-svg/konsyltant1.git
cd konsyltant1
```

### 2. Створення віртуального середовища
```bash
python -m venv venv
# Для Windows:
venv\Scripts\activate
# Для Linux / macOS:
source venv/bin/activate
```

### 3. Встановлення залежностей
```bash
pip install -r requirements.txt
```

### 4. Налаштування змінних оточення
Створіть файл `.env` у корінні проєкту (на основі `.env.example`):
```env
BOT_TOKEN=your_telegram_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5. Запуск бота
```bash
python main.py
```

---

## 🧪 Формат дій (Action) від Gemini API

| Action | Опис |
|---|---|
| `question` | Запити / уточнення клієнта щодо товарів |
| `add_to_cart` | Додавання товару у кошик за `product_id` та `quantity` |
| `remove_from_cart` | Видалення товару з кошика |
| `checkout` | Ініціалізація покрокового оформлення замовлення |
| `manager` | Передача запиту менеджеру-людині |