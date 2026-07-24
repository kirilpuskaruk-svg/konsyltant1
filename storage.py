import json
import os
import csv

ORDERS_FILE = "orders.json"
CARTS_FILE = "carts.json"
HISTORY_FILE = "history.json"


def _read_json(filename, default_val):
    if not os.path.exists(filename):
        return default_val
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default_val


def _write_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --- Order Storage ---

def save_order(order):
    """
    Saves an order to orders.json.
    """
    orders = _read_json(ORDERS_FILE, [])

    if "order_id" not in order or not order["order_id"]:
        existing_ids = [o.get("order_id", 0) for o in orders if isinstance(o.get("order_id"), int)]
        order["order_id"] = max(existing_ids, default=0) + 1

    if "status" not in order:
        order["status"] = "new"

    orders.append(order)
    _write_json(ORDERS_FILE, orders)
    return order


def get_orders(user_id=None, status=None):
    """
    Retrieves orders, optionally filtered by user_id or status.
    """
    orders = _read_json(ORDERS_FILE, [])
    if user_id is not None:
        user_str = str(user_id)
        orders = [o for o in orders if str(o.get("user_id")) == user_str]
    if status is not None and status != "all":
        orders = [o for o in orders if o.get("status") == status]
    return orders


def get_order_by_id(order_id):
    """
    Finds order by order_id.
    """
    orders = _read_json(ORDERS_FILE, [])
    for o in orders:
        if str(o.get("order_id")) == str(order_id):
            return o
    return None


import bonuses


def update_order_status(order_id, new_status):
    """
    Updates status for a specific order.
    Returns updated order dict or None if not found.
    """
    orders = _read_json(ORDERS_FILE, [])
    updated = None
    for o in orders:
        if str(o.get("order_id")) == str(order_id):
            prev_status = o.get("status")
            o["status"] = new_status
            updated = o
            
            # Award 5% cashback bonuses when completing order
            if new_status == "completed" and prev_status != "completed":
                user_id = o.get("user_id")
                total_price = float(o.get("total_price", 0))
                cashback = round(total_price * 0.05, 2)
                if user_id and cashback > 0:
                    bonuses.add_user_bonuses(user_id, cashback)
            break
    if updated:
        _write_json(ORDERS_FILE, orders)
    return updated


def export_orders_csv(filepath="orders_export.csv"):
    """
    Exports all orders to a CSV file.
    """
    orders = _read_json(ORDERS_FILE, [])
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Order ID", "User ID", "Name", "Phone", "Address", "Items Count", "Total Price", "Status"])
        for o in orders:
            items_str = ", ".join([f"{item.get('name', 'Product')} x{item.get('quantity', 1)}" for item in o.get("items", [])])
            writer.writerow([
                o.get("order_id"),
                o.get("user_id"),
                o.get("name"),
                o.get("phone"),
                o.get("address"),
                items_str,
                o.get("total_price"),
                o.get("status")
            ])
    return filepath


def export_orders_txt(filepath="orders_export.txt"):
    """
    Exports all orders to a formatted TXT file.
    """
    orders = _read_json(ORDERS_FILE, [])
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("=== ЗВІТ ЗАМОВЛЕНЬ COOKIE SHOP ===\n\n")
        if not orders:
            f.write("Замовлень не знайдено.\n")
        for o in orders:
            f.write(f"Замовлення #{o.get('order_id')}\n")
            f.write(f"Клієнт: {o.get('name')} (User ID: {o.get('user_id')})\n")
            f.write(f"Телефон: {o.get('phone')}\n")
            f.write(f"Адреса: {o.get('address')}\n")
            f.write(f"Статус: {o.get('status')}\n")
            f.write("Товари:\n")
            for item in o.get("items", []):
                p_name = item.get("name") or f"Печиво #{item.get('product_id')}"
                qty = item.get("quantity", 1)
                price = item.get("price", 0)
                f.write(f"  - {p_name} x{qty} ({price * qty} грн)\n")
            f.write(f"Загальна сума: {o.get('total_price')} грн\n")
            f.write("-" * 40 + "\n\n")
    return filepath


def get_analytics_summary():
    """
    Calculates shop analytics summary.
    """
    orders = _read_json(ORDERS_FILE, [])
    total_orders = len(orders)
    completed_orders = [o for o in orders if o.get("status") == "completed"]
    total_revenue = sum(float(o.get("total_price", 0)) for o in completed_orders)
    avg_check = (total_revenue / len(completed_orders)) if completed_orders else 0.0

    users = get_all_user_ids()
    unique_users_count = len(users)

    # Popular products count
    product_counts = {}
    for o in orders:
        for item in o.get("items", []):
            name = item.get("name") or f"Item #{item.get('product_id')}"
            qty = item.get("quantity", 1)
            product_counts[name] = product_counts.get(name, 0) + qty

    top_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        "total_orders": total_orders,
        "completed_orders": len(completed_orders),
        "total_revenue": total_revenue,
        "avg_check": round(avg_check, 2),
        "unique_users": unique_users_count,
        "top_products": top_products
    }


def get_all_user_ids():
    """
    Returns list of all unique user IDs across history, carts, and orders.
    """
    user_ids = set()

    # From history
    history = _read_json(HISTORY_FILE, {})
    for uid in history.keys():
        user_ids.add(str(uid))

    # From carts
    carts = _read_json(CARTS_FILE, {})
    for uid in carts.keys():
        user_ids.add(str(uid))

    # From orders
    orders = _read_json(ORDERS_FILE, [])
    for o in orders:
        if "user_id" in o:
            user_ids.add(str(o["user_id"]))

    return list(user_ids)


# --- Message History Storage ---

def get_user_history(user_id):
    history_data = _read_json(HISTORY_FILE, {})
    user_str = str(user_id)
    return history_data.get(user_str, [])


def save_message(user_id, role, text):
    history_data = _read_json(HISTORY_FILE, {})
    user_str = str(user_id)
    if user_str not in history_data:
        history_data[user_str] = []
    
    history_data[user_str].append({
        "role": role,
        "text": text
    })
    _write_json(HISTORY_FILE, history_data)


def clear_history(user_id):
    history_data = _read_json(HISTORY_FILE, {})
    user_str = str(user_id)
    if user_str in history_data:
        history_data[user_str] = []
        _write_json(HISTORY_FILE, history_data)


# --- Cart Storage Helpers ---

def get_raw_carts():
    return _read_json(CARTS_FILE, {})


def save_raw_carts(carts_data):
    _write_json(CARTS_FILE, carts_data)
