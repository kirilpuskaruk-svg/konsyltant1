import unittest
import os
import json
import storage
import cart


class TestAdminPanel(unittest.TestCase):

    def setUp(self):
        # Clean up files before test
        for fname in [storage.ORDERS_FILE, storage.CARTS_FILE, storage.HISTORY_FILE, cart.PRODUCTS_FILE, "orders_export.csv", "orders_export.txt"]:
            if os.path.exists(fname):
                os.remove(fname)

        self.sample_products = [
            {"id": 1, "name": "Шоколадне печиво", "description": "Смачне печиво", "price": 100.0, "in_stock": True},
            {"id": 2, "name": "Вівсяне печиво", "description": "З родзинками", "price": 80.0, "in_stock": True}
        ]
        with open(cart.PRODUCTS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.sample_products, f, ensure_ascii=False, indent=2)

    def tearDown(self):
        for fname in [storage.ORDERS_FILE, storage.CARTS_FILE, storage.HISTORY_FILE, cart.PRODUCTS_FILE, "orders_export.csv", "orders_export.txt"]:
            if os.path.exists(fname):
                os.remove(fname)

    def test_order_status_update_and_filtering(self):
        order1 = storage.save_order({
            "user_id": 101,
            "name": "Іван",
            "phone": "+380991112233",
            "address": "Київ",
            "items": [{"product_id": 1, "name": "Шоколадне печиво", "quantity": 2, "price": 100}],
            "total_price": 200
        })
        order2 = storage.save_order({
            "user_id": 102,
            "name": "Марія",
            "phone": "+380994445566",
            "address": "Львів",
            "items": [{"product_id": 2, "name": "Вівсяне печиво", "quantity": 1, "price": 80}],
            "total_price": 80
        })

        self.assertEqual(order1["status"], "new")
        updated = storage.update_order_status(order1["order_id"], "completed")
        self.assertEqual(updated["status"], "completed")

        completed_orders = storage.get_orders(status="completed")
        self.assertEqual(len(completed_orders), 1)
        self.assertEqual(completed_orders[0]["order_id"], order1["order_id"])

    def test_analytics_and_export(self):
        storage.save_order({
            "user_id": 101,
            "name": "Олексій",
            "phone": "+380991112233",
            "address": "Одеса",
            "items": [{"product_id": 1, "name": "Шоколадне печиво", "quantity": 3}],
            "total_price": 300,
            "status": "completed"
        })

        stats = storage.get_analytics_summary()
        self.assertEqual(stats["total_orders"], 1)
        self.assertEqual(stats["completed_orders"], 1)
        self.assertEqual(stats["total_revenue"], 300)
        self.assertEqual(stats["avg_check"], 300)

        csv_file = storage.export_orders_csv("orders_export.csv")
        self.assertTrue(os.path.exists(csv_file))

        txt_file = storage.export_orders_txt("orders_export.txt")
        self.assertTrue(os.path.exists(txt_file))

    def test_product_management(self):
        # Toggle stock
        toggled = cart.toggle_product_stock(1)
        self.assertFalse(toggled["in_stock"])

        # Update price
        updated_price = cart.update_product_price(1, 150.0)
        self.assertEqual(updated_price["price"], 150.0)

        # Add new product
        new_p = cart.add_product("Горіхове печиво", "З фундуком", 130.0, True)
        self.assertEqual(new_p["id"], 3)
        self.assertEqual(len(cart._load_products()), 3)

        # Delete product
        deleted = cart.delete_product(3)
        self.assertTrue(deleted)
        self.assertEqual(len(cart._load_products()), 2)


if __name__ == "__main__":
    unittest.main()
