import sys
import unittest
import app

# Ensure proper Unicode encoding in stdout for Windows
sys.stdout.reconfigure(encoding="utf-8")


class SakhiGuideTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.app.test_client()

    def test_home_page(self):
        """Verify the main Tamil landing page loads correctly with zero digital literacy elements."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("மகளிர் திட்டம் | Women Scheme", html)
        self.assertIn("பேசுங்கள்", html)
        self.assertIn("எழுதுங்கள்", html)
        self.assertIn("நான் தகுதியானவளா?", html)
        self.assertIn("1800-266-6696", html)

    def test_static_files(self):
        """Verify static CSS and JS are served properly."""
        with self.client.get("/static/style.css") as res_css:
            self.assertEqual(res_css.status_code, 200)
            self.assertTrue(len(res_css.get_data()) > 0)
        with self.client.get("/static/script.js") as res_js:
            self.assertEqual(res_js.status_code, 200)
            self.assertTrue(len(res_js.get_data()) > 0)

    def test_health_endpoint(self):
        """Verify health check returns healthy status."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("intents_available", data)

    def test_topics_endpoint(self):
        """Verify topics endpoint returns verified starter questions."""
        res = self.client.get("/api/topics")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("quick_questions", data)
        self.assertGreaterEqual(len(data["quick_questions"]), 6)

    def test_chat_intents(self):
        """Verify intent detection and verified response generation for all core scenarios."""
        test_queries = [
            ("வணக்கம்", "greeting"),
            ("ஆம்", "yes_interested"),
            ("இல்லை", "no_not_interested"),
            ("நான் தகுதியானவளா?", "eligibility"),
            ("என்ன ஆவணங்கள் வேண்டும்?", "documents"),
            ("என்ன நன்மைகள் கிடைக்கும்?", "benefits"),
            ("எப்படி விண்ணப்பிப்பது?", "how_to_apply"),
            ("எங்கு விண்ணப்பிப்பது?", "where_to_apply"),
            ("கட்டணம் ஏதும் உண்டா?", "cost_fee"),
            ("உதவி எண் என்ன?", "helpline_official"),
            ("எனக்கு கேஸ் அடுப்பு இலவசமா வேணும்", "benefits"),
            ("documents enna vendum", "documents")
        ]

        for query, expected_intent in test_queries:
            with self.subTest(query=query):
                res = self.client.post("/api/chat", json={"message": query, "language": "ta"})
                self.assertEqual(res.status_code, 200)
                data = res.get_json()
                self.assertEqual(data["status"], "success")
                self.assertEqual(data["intent"], expected_intent)
                self.assertTrue(len(data.get("summary", "")) > 0)
                self.assertTrue(len(data.get("points", [])) > 0)
                self.assertIn("next_steps", data)
                self.assertIn("suggested_questions", data)
                self.assertIn("official_info", data)

    def test_chat_validation_empty_input(self):
        """Verify empty input is handled safely with a friendly Tamil prompt."""
        res = self.client.post("/api/chat", json={"message": ""})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("தயவுசெய்து", data["message_tamil"])


if __name__ == "__main__":
    unittest.main()
