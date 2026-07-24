import json
import os

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
    Order format expected:
    {
      "order_id": int (optional, generated if missing),
      "user_id": int/str,
      "name": str,
      "phone": str,
      "address": str,
      "items": list,
      "total_price": float/int,
      "status": "new"
    }
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


def get_orders(user_id=None):
    """
    Retrieves orders, optionally filtered by user_id.
    """
    orders = _read_json(ORDERS_FILE, [])
    if user_id is not None:
        user_str = str(user_id)
        return [o for o in orders if str(o.get("user_id")) == user_str]
    return orders


# --- Message History Storage ---

def get_user_history(user_id):
    """
    Gets the conversation history for a given user_id.
    Returns list of dicts: [{"role": role, "text": text}, ...]
    """
    history_data = _read_json(HISTORY_FILE, {})
    user_str = str(user_id)
    return history_data.get(user_str, [])


def save_message(user_id, role, text):
    """
    Saves a single message (role and text) for a given user_id.
    """
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
    """
    Clears message history for a given user_id.
    """
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
