import unittest
import os
import json
import storage
import cart


class TestCartAndStorage(unittest.TestCase):

    def setUp(self):
        # Sample products
        self.sample_products = [
            {"id": 1, "name": "Шоколадне печиво", "price": 100, "in_stock": True},
            {"id": 2, "name": "Вівсяне печиво з родзинками", "price": 85, "in_stock": True},
            {"id": 3, "name": "Печиво з кокосом", "price": 90, "in_stock": False},
        ]
        # Clean test JSON files if exist
        for fname in [storage.ORDERS_FILE, storage.CARTS_FILE, storage.HISTORY_FILE, cart.PRODUCTS_FILE]:
            if os.path.exists(fname):
                os.remove(fname)

        with open(cart.PRODUCTS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.sample_products, f, ensure_ascii=False, indent=2)

    def tearDown(self):
        for fname in [storage.ORDERS_FILE, storage.CARTS_FILE, storage.HISTORY_FILE, cart.PRODUCTS_FILE]:
            if os.path.exists(fname):
                os.remove(fname)

    def test_cart_operations(self):
        user_id = 12345

        # Initial cart should be empty
        self.assertEqual(cart.get_cart(user_id), [])

        # Add valid in-stock product
        success, msg = cart.add_to_cart(user_id, product_id=1, quantity=2, products=self.sample_products)
        self.assertTrue(success)
        self.assertEqual(len(cart.get_cart(user_id)), 1)

        # Add same product again (should increment quantity)
        cart.add_to_cart(user_id, product_id=1, quantity=1, products=self.sample_products)
        user_cart = cart.get_cart(user_id)
        self.assertEqual(user_cart[0]["quantity"], 3)

        # Try adding out of stock product (id 3)
        success, msg = cart.add_to_cart(user_id, product_id=3, quantity=1, products=self.sample_products)
        self.assertFalse(success)
        self.assertIn("наявності", msg)

        # Try adding non-existent product
        success, msg = cart.add_to_cart(user_id, product_id=999, quantity=1, products=self.sample_products)
        self.assertFalse(success)

        # Test get_cart_total
        cart.add_to_cart(user_id, product_id=2, quantity=1, products=self.sample_products)
        total_info = cart.get_cart_total(user_id, products=self.sample_products)
        # Item 1: 3 * 100 = 300; Item 2: 1 * 85 = 85. Total = 385
        self.assertEqual(total_info["total_price"], 385)
        self.assertEqual(len(total_info["items"]), 2)

        # Test remove_from_cart
        cart.remove_from_cart(user_id, product_id=1)
        user_cart_after_remove = cart.get_cart(user_id)
        self.assertEqual(len(user_cart_after_remove), 1)
        self.assertEqual(user_cart_after_remove[0]["product_id"], 2)

        # Test clear_cart
        cart.clear_cart(user_id)
        self.assertEqual(cart.get_cart(user_id), [])

    def test_storage_operations(self):
        user_id = 98765

        # Test history
        storage.save_message(user_id, "user", "Привіт! Хочу печиво")
        storage.save_message(user_id, "assistant", "Вітаю! Яке саме печиво вас цікавить?")

        history = storage.get_user_history(user_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")

        storage.clear_history(user_id)
        self.assertEqual(storage.get_user_history(user_id), [])

        # Test save_order
        order_data = {
            "user_id": user_id,
            "name": "Ярослав",
            "phone": "+380991234567",
            "address": "Київ, Нова пошта #1",
            "items": [{"product_id": 1, "quantity": 2}],
            "total_price": 200
        }
        saved = storage.save_order(order_data)
        self.assertIn("order_id", saved)
        self.assertEqual(saved["order_id"], 1)
        self.assertEqual(saved["status"], "new")

        orders = storage.get_orders(user_id)
        self.assertEqual(len(orders), 1)


if __name__ == "__main__":
    unittest.main()
