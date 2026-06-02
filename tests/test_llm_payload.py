import unittest
from unittest.mock import patch

from menutalker.llm import LLMSettings, call_chat_completion, find_meal, normalize_text_content


class FakeResponse:
    ok = True

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}


class LLMPayloadTests(unittest.TestCase):
    def test_normalize_text_content_flattens_gradio_rich_content(self):
        content = [{"text": "First line"}, {"content": ["Second", {"text": "line"}]}]

        self.assertEqual(normalize_text_content(content), "First line\nSecond\nline")

    def test_google_history_payload_uses_plain_text_parts(self):
        captured = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured["payload"] = json
            return FakeResponse()

        settings = LLMSettings(
            provider="google",
            model="gemini-flash-latest",
            api_key="fake-key",
        )
        history = [
            {"role": "assistant", "content": "Initial assistant greeting is skipped."},
            {"role": "user", "content": [{"text": "Tell me about Chef's favorites."}]},
            {"role": "assistant", "content": [{"text": "Cheeseburger is available."}]},
        ]

        with patch("menutalker.llm.requests.post", fake_post):
            answer = call_chat_completion(
                settings,
                system_prompt="System prompt",
                user_prompt="I will take Cheeseburger.",
                history=history,
            )

        self.assertEqual(answer, "ok")
        contents = captured["payload"]["contents"]
        self.assertEqual(contents[0]["parts"][0]["text"], "Tell me about Chef's favorites.")
        self.assertEqual(contents[1]["parts"][0]["text"], "Cheeseburger is available.")
        self.assertEqual(contents[2]["parts"][0]["text"], "I will take Cheeseburger.")

    def test_find_meal_ignores_instructional_tag_mentions_and_uses_final_block(self):
        text = (
            "Then output the final order enclosed exactly in `<MEAL>` and `</MEAL>`.\n\n"
            "Thank you. Your order is complete.\n"
            "<MEAL>\n"
            "1 Cheeseburger, 1 California Beach Tacos, 1 Handcrafted Beer. Total: $45.00\n"
            "</MEAL>"
        )

        self.assertEqual(
            find_meal(text),
            "1 Cheeseburger, 1 California Beach Tacos, 1 Handcrafted Beer. Total: $45.00",
        )


if __name__ == "__main__":
    unittest.main()
