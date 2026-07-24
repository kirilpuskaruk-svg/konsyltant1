import json
import os
import storage

PRODUCTS_FILE = "products.json"


def _load_products():
    if os.path.exists(PRODUCTS_FILE):
        try:
            with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
    return []


def get_cart(user_id):
    """
    Returns list of cart items for user_id.
    Example: [{"product_id": 1, "quantity": 2}]
    """
    carts = storage.get_raw_carts()
    user_str = str(user_id)
    return carts.get(user_str, [])


def add_to_cart(user_id, product_id, quantity=1, products=None):
    """
    Adds a product to the user's cart.
    Checks if product exists in database and is in stock.
    Increments quantity if already in cart.
    Returns (bool, str) status tuple or updated cart list.
    """
    if quantity <= 0:
        return False, "Кількість повинна бути більшою за 0."

    if products is None:
        products = _load_products()

    # Find product in list
    product = None
    if isinstance(products, list):
        for p in products:
            if p.get("id") == product_id or p.get("product_id") == product_id:
                product = p
                break
    elif isinstance(products, dict):
        product = products.get(str(product_id)) or products.get(product_id)

    if not product:
        return False, "Товар не знайдено в базі."

    # Check stock availability
    # Checks either in_stock boolean or stock count > 0
    in_stock = product.get("in_stock", True)
    stock_count = product.get("stock", None)
    if in_stock is False or (stock_count is not None and stock_count <= 0):
        return False, "Товару немає в наявності."

    carts = storage.get_raw_carts()
    user_str = str(user_id)
    user_cart = carts.get(user_str, [])

    # Check if item is already in user's cart
    item_found = False
    for item in user_cart:
        if item.get("product_id") == product_id:
            item["quantity"] = item.get("quantity", 0) + quantity
            item_found = True
            break

    if not item_found:
        user_cart.append({
            "product_id": product_id,
            "quantity": quantity
        })

    carts[user_str] = user_cart
    storage.save_raw_carts(carts)
    return True, "Товар успішно додано в кошик."


def remove_from_cart(user_id, product_id):
    """
    Removes a product completely from the user's cart.
    """
    carts = storage.get_raw_carts()
    user_str = str(user_id)
    user_cart = carts.get(user_str, [])

    updated_cart = [item for item in user_cart if item.get("product_id") != product_id]

    carts[user_str] = updated_cart
    storage.save_raw_carts(carts)
    return updated_cart


def get_cart_total(user_id, products=None):
    """
    Calculates cart details and total price for user_id.
    Returns dict:
    {
       "items": [
           {
               "product_id": 1,
               "name": "Шоколадне печиво",
               "price": 120,
               "quantity": 2,
               "subtotal": 240
           }
       ],
       "total_price": 240
    }
    """
    if products is None:
        products = _load_products()

    # Map products by ID for fast lookup
    products_map = {}
    if isinstance(products, list):
        for p in products:
            p_id = p.get("id") if "id" in p else p.get("product_id")
            if p_id is not None:
                products_map[p_id] = p
    elif isinstance(products, dict):
        products_map = products

    user_cart = get_cart(user_id)
    detailed_items = []
    total_price = 0.0

    for item in user_cart:
        p_id = item.get("product_id")
        qty = item.get("quantity", 1)
        product_info = products_map.get(p_id, {})
        
        name = product_info.get("name", f"Печиво #{p_id}")
        price = product_info.get("price", 0.0)
        subtotal = price * qty

        detailed_items.append({
            "product_id": p_id,
            "name": name,
            "price": price,
            "quantity": qty,
            "subtotal": subtotal
        })
        total_price += subtotal

    return {
        "items": detailed_items,
        "total_price": total_price
    }


def clear_cart(user_id):
    """
    Empties the cart for user_id.
    """
    carts = storage.get_raw_carts()
    user_str = str(user_id)
    carts[user_str] = []
    storage.save_raw_carts(carts)
    return True
