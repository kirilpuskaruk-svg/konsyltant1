import json
import os

REVIEWS_FILE = "reviews.json"


def _read_reviews():
    if not os.path.exists(REVIEWS_FILE):
        return []
    try:
        with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _write_reviews(data):
    with open(REVIEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_reviews(product_id=None):
    reviews = _read_reviews()
    if product_id is not None:
        return [r for r in reviews if r.get("product_id") == int(product_id)]
    return reviews


def add_review(product_id, user_id, user_name, rating, text):
    reviews = _read_reviews()
    new_rev = {
        "review_id": len(reviews) + 1,
        "product_id": int(product_id),
        "user_id": str(user_id),
        "user_name": str(user_name),
        "rating": min(5, max(1, int(rating))),
        "text": str(text)
    }
    reviews.append(new_rev)
    _write_reviews(reviews)
    return new_rev


def get_average_rating(product_id):
    product_reviews = get_reviews(product_id)
    if not product_reviews:
        return 5.0
    ratings = [r.get("rating", 5) for r in product_reviews]
    return round(sum(ratings) / len(ratings), 1)
