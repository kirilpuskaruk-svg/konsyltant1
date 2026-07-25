import storage
from typing import List

CATEGORIES_FILE = "categories.json"
DEFAULT_CATEGORIES = ["Фігурки", "Одяг та Мерч", "Колекційне"]

def load_categories() -> List[str]:
    cats = storage._read_json(CATEGORIES_FILE, None)
    if cats is None or not isinstance(cats, list):
        save_categories(DEFAULT_CATEGORIES)
        return DEFAULT_CATEGORIES
    return cats


def save_categories(categories: List[str]):
    storage._write_json(CATEGORIES_FILE, categories)


def add_category(category_name: str) -> bool:
    name = category_name.strip()
    if not name:
        return False
    categories = load_categories()
    if name not in categories:
        categories.append(name)
        save_categories(categories)
        return True
    return False


def delete_category(category_name: str) -> bool:
    categories = load_categories()
    if category_name in categories:
        categories.remove(category_name)
        save_categories(categories)
        return True
    return False


def reset_default_products() -> bool:
    """Видаляє всі стандартні дефолтні товари та очищає категорійний склад."""
    try:
        with open("products.json", "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        save_categories(["Загальне"])
        return True
    except Exception as e:
        print(f"[Reset Default Products Error]: {e}")
        return False
