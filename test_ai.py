import json
import os
import ai_manager
import cart
import storage

def test_ai_manager():
    print("=== Testing AI Manager ===")
    products = [
        {"id": 1, "name": "Шоколадне печиво", "price": 120, "in_stock": True},
        {"id": 2, "name": "Вівсяне з журавлиною", "price": 95, "in_stock": True}
    ]
    history = []
    message = "Хочу дві коробки шоколадного печива"
    
    response = ai_manager.generate_reply(message, history, products)
    print("Response:", json.dumps(response, ensure_ascii=False, indent=2))
    assert "reply" in response
    assert response["action"] in ["question", "add_to_cart", "remove_from_cart", "checkout", "manager"]
    print("AI Manager Test PASSED!\n")

if __name__ == "__main__":
    test_ai_manager()
