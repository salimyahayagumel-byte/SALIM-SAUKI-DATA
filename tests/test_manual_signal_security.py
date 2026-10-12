import os
import unittest
from unittest.mock import patch

import bot


class ManualSignalSecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = bot.app_web.test_client()

    def test_manual_signal_disabled_without_admin_key(self):
        with patch.dict(os.environ, {"DASHBOARD_MANUAL_SIGNAL_KEY": ""}, clear=False):
            response = self.client.post("/api/manual-signal/send", json={
                "address": "So11111111111111111111111111111111111111112",
                "chain": "solana", "signal_type": "MANUAL GEM", "reason": "test"
            })
        self.assertEqual(response.status_code, 403)

    def test_manual_signal_rejects_wrong_admin_key(self):
        with patch.dict(os.environ, {"DASHBOARD_MANUAL_SIGNAL_KEY": "correct-secret"}, clear=False):
            response = self.client.post("/api/manual-signal/send", headers={"X-Manual-Signal-Key": "wrong"}, json={
                "address": "So11111111111111111111111111111111111111112",
                "chain": "solana", "signal_type": "MANUAL GEM", "reason": "test"
            })
        self.assertEqual(response.status_code, 403)

    def test_manual_signal_requires_reason_and_allowed_type(self):
        with patch.dict(os.environ, {"DASHBOARD_MANUAL_SIGNAL_KEY": "correct-secret"}, clear=False):
            no_reason = self.client.post("/api/manual-signal/send", headers={"X-Manual-Signal-Key": "correct-secret"}, json={
                "address": "So11111111111111111111111111111111111111112",
                "chain": "solana", "signal_type": "MANUAL GEM", "reason": ""
            })
            bad_type = self.client.post("/api/manual-signal/send", headers={"X-Manual-Signal-Key": "correct-secret"}, json={
                "address": "So11111111111111111111111111111111111111112",
                "chain": "solana", "signal_type": "STRONG BUY", "reason": "reviewed"
            })
        self.assertEqual(no_reason.status_code, 400)
        self.assertEqual(bad_type.status_code, 400)

    def test_manual_status_does_not_reveal_key(self):
        with patch.dict(os.environ, {"DASHBOARD_MANUAL_SIGNAL_KEY": "secret-never-return"}, clear=False):
            response = self.client.get("/api/manual-signal/status")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"secret-never-return", response.data)


if __name__ == "__main__":
    unittest.main()
