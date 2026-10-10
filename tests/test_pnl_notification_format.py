import asyncio
import os
import tempfile
import unittest

from services.pnl_tracker import PNLTracker


class CaptureBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)


class TestPNLNotificationFormat(unittest.TestCase):
    def test_default_milestones_include_5x_and_10x(self):
        self.assertIn(400, PNLTracker.DEFAULT_MILESTONES)
        self.assertIn(900, PNLTracker.DEFAULT_MILESTONES)

    def test_5_4x_market_cap_sends_formatted_update(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        bot = CaptureBot()
        tracker = PNLTracker(bot=bot, chat_id="-100", database_url=path)
        tracker.add_signal({
            "chain": "solana",
            "address": "Token111",
            "symbol": "ALOIS",
            "price": 0.01,
            "pair": "Pair111",
            "marketcap": 27000,
        })
        row = tracker.get_tracked("solana:Token111")[0]
        asyncio.run(tracker._process_market_cap(row, 147000, 0.0544))
        self.assertEqual(len(bot.messages), 1)
        message = bot.messages[0]["text"]
        self.assertIn("ALOIS is up 5.44X from Entry Signal", message)
        self.assertIn("PNL: +444.4%", message)
        self.assertIn("Best MC: <b>$147.0K</b>", message)
        self.assertIn("\n", message)  # actual line breaks, not literal slash-n
        self.assertNotIn("\\n", message)


if __name__ == "__main__":
    unittest.main()
