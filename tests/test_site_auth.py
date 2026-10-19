import os
import tempfile
import unittest
from unittest.mock import patch
import bot

class SiteAuthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "SITE_AUTH_DB": os.path.join(self.tmp.name, "users.db"),
            "SITE_ADMIN_EMAIL": "salimyahayagumel@gmail.com",
            "SITE_ADMIN_PASSWORD": "test-admin-password-2026",
        }, clear=False)
        self.env.start()
        bot.app_web.secret_key = "test-session-secret-key-long-enough"
        bot.app_web.config["TESTING"] = True
        self.client = bot.app_web.test_client()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_register_and_login_user(self):
        response = self.client.post("/register", data={"name":"Test User", "email":"user@example.com", "password":"user-password-123"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/account", response.headers["Location"])
        self.client.post("/logout")
        response = self.client.post("/login", data={"email":"user@example.com", "password":"user-password-123"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/account", response.headers["Location"])

    def test_user_cannot_open_admin(self):
        self.client.post("/register", data={"name":"User", "email":"user@example.com", "password":"user-password-123"})
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_admin_login_uses_server_password(self):
        response = self.client.post("/login", data={"email":"salimyahayagumel@gmail.com", "password":"test-admin-password-2026"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin", response.headers["Location"])
        self.assertEqual(self.client.get("/admin").status_code, 200)

    def test_admin_email_cannot_register_with_arbitrary_password(self):
        response = self.client.post("/register", data={"name":"Attacker", "email":"salimyahayagumel@gmail.com", "password":"not-the-admin-password"})
        self.assertEqual(response.status_code, 403)

if __name__ == "__main__":
    unittest.main()
