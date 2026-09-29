import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from profilekit.models import ProfileSession
from profilekit.web import SessionStore, app
import profilekit.web as web_module


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.original_store = web_module.store
        web_module.store = SessionStore(Path(self.directory.name) / "session.json")
        self.client = TestClient(app)

    def tearDown(self):
        web_module.store = self.original_store
        self.directory.cleanup()

    def test_home_page_contains_primary_workspace(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ProfileKit", response.text)
        self.assertIn("Personal Profile Record", response.text)

    def test_public_state_never_exposes_api_key(self):
        response = self.client.get("/api/session")
        self.assertEqual(response.status_code, 200)
        body = response.text
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            self.assertNotIn(openai_key, body)
        self.assertNotIn("DEEPSEEK_API_KEY", body)
        self.assertNotIn("GEMINI_API_KEY", body)

    def test_demo_loads_fictional_profile_record(self):
        response = self.client.post("/api/demo")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["stage"], "personal_profile_record")
        self.assertGreater(len(payload["record"]["items"]), 0)
        self.assertTrue(all("demo" in (item.get("source") or "").lower() for item in payload["record"]["items"]))

    def test_item_decision_is_saved_with_private_permissions(self):
        self.client.post("/api/demo")
        response = self.client.patch("/api/items/0", json={"decision": "include"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["record"]["items"][0]["user_decision"], "include")
        self.assertEqual(web_module.store.path.stat().st_mode & 0o777, 0o600)

    def test_reset_returns_to_intake(self):
        web_module.store.session = ProfileSession()
        self.client.post("/api/demo")
        response = self.client.post("/api/reset")
        self.assertEqual(response.json()["stage"], "intake")

    def test_text_upload_is_queued_for_source_review(self):
        response = self.client.post(
            "/api/upload",
            files={"files": ("notes.txt", b"Supported interview coding.", "text/plain")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["accepted"], ["notes.txt"])
        self.assertEqual(response.json()["session"]["pending_source_count"], 1)


if __name__ == "__main__":
    unittest.main()
