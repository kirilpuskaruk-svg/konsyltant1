import json
import os
import storage

PRODUCTS_FILE = "products.json"


def _load_products():
    return storage._read_json(PRODUCTS_FILE, [])


def _save_products(products):
    storage._write_json(PRODUCTS_FILE, products)


def toggle_product_stock(product_id):
    """
    Toggles the in_stock status of a product by ID.
    Returns updated product dict or None.
    """
    products = _load_products()
    updated = None
    for p in products:
        if p.get("id") == product_id or p.get("product_id") == product_id:
            p["in_stock"] = not p.get("in_stock", True)
            updated = p
            break
    if updated:
        _save_products(products)
    return updated


def update_product_price(product_id, new_price):
    """
    Updates price of a product by ID.
    """
    products = _load_products()
    updated = None
    for p in products:
        if p.get("id") == product_id or p.get("product_id") == product_id:
            p["price"] = float(new_price)
            updated = p
            break
    if updated:
        _save_products(products)
    return updated


def add_product(name, description, price, in_stock=True):
    """
    Adds a new product to products.json.
    """
    products = _load_products()
    existing_ids = [p.get("id", 0) for p in products if isinstance(p.get("id"), int)]
    new_id = max(existing_ids, default=0) + 1

    new_prod = {
        "id": new_id,
        "name": name,
        "description": description,
        "price": float(price),
        "in_stock": in_stock
    }
    products.append(new_prod)
    _save_products(products)
    return new_prod


def delete_product(product_id):
    """
    Deletes a product by ID from products.json.
    """
    products = _load_products()
    new_products = [p for p in products if p.get("id") != product_id and p.get("product_id") != product_id]
    if len(new_products) < len(products):
        _save_products(new_products)
        return True
    return False


def get_cart(user_id):
    carts = storage.get_raw_carts()
    user_str = str(user_id)
    return carts.get(user_str, [])


def add_to_cart(user_id, product_id, quantity=1, products=None):
    if quantity <= 0:
        return False, "Кількість повинна бути більшою за 0."

    if products is None:
        products = _load_products()

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

    in_stock = product.get("in_stock", True)
    stock_count = product.get("stock", None)
    if in_stock is False or (stock_count is not None and stock_count <= 0):
        return False, "Товару немає в наявності."

    carts = storage.get_raw_carts()
    user_str = str(user_id)
    user_cart = carts.get(user_str, [])

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
    carts = storage.get_raw_carts()
    user_str = str(user_id)
    user_cart = carts.get(user_str, [])

    updated_cart = [item for item in user_cart if item.get("product_id") != product_id]

    carts[user_str] = updated_cart
    storage.save_raw_carts(carts)
    return updated_cart


def get_cart_total(user_id, products=None):
    if products is None:
        products = _load_products()

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
    carts = storage.get_raw_carts()
    user_str = str(user_id)
    carts[user_str] = []
    storage.save_raw_carts(carts)
    return True
