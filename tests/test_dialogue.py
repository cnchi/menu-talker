import unittest
from unittest.mock import patch

from menutalker.dialogue import FINAL_ORDER_MESSAGE, format_meal, respond


class DialogueTests(unittest.TestCase):
    def test_format_meal_splits_items_and_total(self):
        meal = "1 Cheeseburger, 1 California Beach Tacos, 1 Handcrafted Beer. Total: $45.00"

        self.assertEqual(
            format_meal(meal),
            "1 Cheeseburger,\n1 California Beach Tacos,\n1 Handcrafted Beer.\nTotal: $45.00",
        )

    def test_respond_hides_meal_tags_from_chat_and_sets_final_meal(self):
        menu = {
            "categories": [
                {
                    "name": "Chef's Favorites/Main Course",
                    "items": [{"name": "Cheeseburger", "price": 20.0}],
                }
            ]
        }
        state = {
            "menu": menu,
            "llm": {
                "provider": "google",
                "model": "gemini-flash-latest",
                "base_url": "",
                "api_key": "fake-key",
                "include_images": False,
            },
            "meal": "",
        }
        history = [
            {"role": "assistant", "content": "What would you like?"},
            {"role": "user", "content": "I will take 1 order of California Beach Tacos."},
            {"role": "assistant", "content": "Added 1 order of California Beach Tacos."},
        ]
        llm_answer = (
            "Thank you. Your order is complete.\n"
            "<MEAL>\n"
            "1 Cheeseburger, 1 California Beach Tacos, 1 Handcrafted Beer. Total: $45.00\n"
            "</MEAL>"
        )

        with patch("menutalker.dialogue.call_chat_completion", return_value=llm_answer):
            updated_history, updated_state, meal = respond("That's it.", history, state)

        expected_meal = "1 Cheeseburger,\n1 California Beach Tacos,\n1 Handcrafted Beer.\nTotal: $45.00"
        self.assertEqual(meal, expected_meal)
        self.assertEqual(updated_state["meal"], expected_meal)
        self.assertEqual(updated_history[-1]["content"], FINAL_ORDER_MESSAGE)
        self.assertNotIn("<MEAL>", updated_history[-1]["content"])


if __name__ == "__main__":
    unittest.main()
