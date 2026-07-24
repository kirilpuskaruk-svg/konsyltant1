import unittest
import os
import json
import bonuses
import reviews
import storage
import cart


class TestMegaUpdate(unittest.TestCase):

    def setUp(self):
        for fname in [bonuses.BONUSES_FILE, reviews.REVIEWS_FILE, storage.ORDERS_FILE, storage.CARTS_FILE, storage.HISTORY_FILE]:
            if os.path.exists(fname):
                os.remove(fname)

    def tearDown(self):
        for fname in [bonuses.BONUSES_FILE, reviews.REVIEWS_FILE, storage.ORDERS_FILE, storage.CARTS_FILE, storage.HISTORY_FILE]:
            if os.path.exists(fname):
                os.remove(fname)

    def test_bonuses_system(self):
        user_id = 999
        self.assertEqual(bonuses.get_user_bonuses(user_id), 0.0)

        # Add bonuses
        bonuses.add_user_bonuses(user_id, 50.0)
        self.assertEqual(bonuses.get_user_bonuses(user_id), 50.0)

        # Use bonuses
        success, remaining = bonuses.use_user_bonuses(user_id, 20.0)
        self.assertTrue(success)
        self.assertEqual(remaining, 30.0)

        # Fail to use excessive bonuses
        success, remaining = bonuses.use_user_bonuses(user_id, 100.0)
        self.assertFalse(success)
        self.assertEqual(remaining, 30.0)

    def test_reviews_system(self):
        rev = reviews.add_review(product_id=1, user_id=101, user_name="Тарас", rating=5, text="Супер смачно!")
        self.assertEqual(rev["product_id"], 1)
        self.assertEqual(rev["rating"], 5)

        prod_reviews = reviews.get_reviews(product_id=1)
        self.assertEqual(len(prod_reviews), 1)

        avg_rating = reviews.get_average_rating(1)
        self.assertEqual(avg_rating, 5.0)

    def test_order_completion_cashback(self):
        order = storage.save_order({
            "user_id": 555,
            "name": "Олена",
            "phone": "+380995556677",
            "address": "Одеса, НП №3",
            "items": [{"product_id": 1, "name": "Шоколадне печиво", "quantity": 2, "price": 100}],
            "total_price": 200.0
        })

        # Complete order -> should award 5% of 200 = 10 грн bonus
        storage.update_order_status(order["order_id"], "completed")
        user_b = bonuses.get_user_bonuses(555)
        self.assertEqual(user_b, 10.0)


if __name__ == "__main__":
    unittest.main()
