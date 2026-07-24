import unittest
import categories


class TestCategoryManagement(unittest.TestCase):

    def test_add_and_delete_category(self):
        cat_name = "Тестовий Розділ 123"

        # Add category
        added = categories.add_category(cat_name)
        self.assertTrue(added)

        cats = categories.load_categories()
        self.assertIn(cat_name, cats)

        # Delete category
        deleted = categories.delete_category(cat_name)
        self.assertTrue(deleted)

        cats_after = categories.load_categories()
        self.assertNotIn(cat_name, cats_after)


if __name__ == "__main__":
    unittest.main()
