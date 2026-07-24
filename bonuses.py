import json
import os

BONUSES_FILE = "bonuses.json"


def _read_bonuses():
    if not os.path.exists(BONUSES_FILE):
        return {}
    try:
        with open(BONUSES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_bonuses(data):
    with open(BONUSES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user_bonuses(user_id):
    """
    Returns bonus points balance for user_id.
    """
    data = _read_bonuses()
    return float(data.get(str(user_id), 0.0))


def add_user_bonuses(user_id, amount):
    """
    Adds cashback bonus points to user_id.
    """
    if amount <= 0:
        return get_user_bonuses(user_id)
    data = _read_bonuses()
    user_str = str(user_id)
    current = float(data.get(user_str, 0.0))
    data[user_str] = round(current + amount, 2)
    _write_bonuses(data)
    return data[user_str]


def use_user_bonuses(user_id, amount):
    """
    Deducts bonus points from user_id.
    Returns (success: bool, remaining_balance: float).
    """
    data = _read_bonuses()
    user_str = str(user_id)
    current = float(data.get(user_str, 0.0))
    if amount > current:
        return False, current
    data[user_str] = round(current - amount, 2)
    _write_bonuses(data)
    return True, data[user_str]
