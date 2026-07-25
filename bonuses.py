import storage

BONUSES_FILE = "bonuses.json"


def _read_bonuses():
    return storage._read_json(BONUSES_FILE, {})


def _write_bonuses(data):
    storage._write_json(BONUSES_FILE, data)


def get_user_bonuses(user_id):
    if not user_id:
        return 0.0
    storage.register_user(user_id)
    data = _read_bonuses()
    return float(data.get(str(user_id), 0.0))


def add_user_bonuses(user_id, amount):
    if not user_id or amount <= 0:
        return get_user_bonuses(user_id)
    storage.register_user(user_id)
    data = _read_bonuses()
    user_str = str(user_id)
    current = float(data.get(user_str, 0.0))
    data[user_str] = round(current + amount, 2)
    _write_bonuses(data)
    return data[user_str]


def use_user_bonuses(user_id, amount):
    if not user_id or amount <= 0:
        return False, get_user_bonuses(user_id)
    storage.register_user(user_id)
    data = _read_bonuses()
    user_str = str(user_id)
    current = float(data.get(user_str, 0.0))
    if amount > current:
        return False, current
    data[user_str] = round(current - amount, 2)
    _write_bonuses(data)
    return True, data[user_str]
