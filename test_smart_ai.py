import unittest
import os
import json
import ai_manager


class TestSmartAIManager(unittest.TestCase):

    def setUp(self):
        self.sample_products = [
            {"id": 1, "name": "Шоколадне печиво", "price": 120.0, "in_stock": True, "category": "Шоколадне"},
            {"id": 2, "name": "Вівсяне печиво", "price": 95.0, "in_stock": True, "category": "Вівсяне"}
        ]

    def test_smart_context_reply(self):
        user_cart = [{"product_id": 1, "name": "Шоколадне печиво", "quantity": 2, "price": 120.0, "subtotal": 240.0}]
        user_bonuses = 50.0
        user_orders = [{"order_id": 1, "status": "processing", "total_price": 240.0}]
        promos = {"COOKIE10": {"discount_percent": 10, "active": True}}

        # Test context awareness for cart query
        reply = ai_manager.generate_reply(
            message="Що в мене зараз у кошику і скільки з мене?",
            history=[],
            products=self.sample_products,
            user_cart=user_cart,
            user_bonuses=user_bonuses,
            user_orders=user_orders,
            promos=promos
        )

        self.assertIn("action", reply)
        self.assertIn("reply", reply)
        self.assertIsInstance(reply["reply"], str)

    def test_smart_recommendation(self):
        reply = ai_manager.generate_reply(
            message="Порай печиво до подвійного еспресо",
            history=[],
            products=self.sample_products
        )
        self.assertIn("reply", reply)
        self.assertTrue(len(reply["reply"]) > 5)


if __name__ == "__main__":
    unittest.main()
