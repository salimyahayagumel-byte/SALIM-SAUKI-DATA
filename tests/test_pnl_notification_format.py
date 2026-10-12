import asyncio
import os
import tempfile
import unittest

from services.pnl_tracker import PNLTracker


class CaptureBot:
    def __init__(self):
        self.messages = []
        self.photos = []

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)

    async def send_photo(self, **kwargs):
        self.photos.append(kwargs)


class TestPNLNotificationFormat(unittest.TestCase):
    def test_default_milestones_start_at_50_percent_and_continue_beyond_10x(self):
        tracker = object.__new__(PNLTracker)
        tracker._use_standard_milestones = True
        self.assertEqual(tracker._highest_reached(49.9), 0)
        self.assertEqual(tracker._highest_reached(50), 50)
        self.assertEqual(tracker._highest_reached(100), 100)  # 1X profit
        self.assertEqual(tracker._highest_reached(200), 200)  # 2X profit
        self.assertEqual(tracker._highest_reached(1000), 1000)  # 10X profit
        self.assertEqual(tracker._highest_reached(1700), 1700)  # 17X profit

    def test_5_4x_market_cap_sends_formatted_update(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        bot = CaptureBot()
        tracker = PNLTracker(bot=bot, chat_id="-100", database_url=path)
        async def no_image(_row):
            return None
        tracker._get_token_image_url = no_image
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
        self.assertIn("ALOIS is up 4X", message)
        self.assertIn("from ⚡", message)
        self.assertIn("<b>$27.0K → $147.0K</b>", message)
        self.assertIn("📄 CA: <code>Token111</code>", message)
        self.assertNotIn("PNL DETAILS", message)
        self.assertNotIn("DRAWDOWN ALERT", message)
        self.assertIn("\n", message)  # actual line breaks, not literal slash-n
        self.assertNotIn("\\n", message)

    def test_money_emojis_follow_x_multiplier(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        bot = CaptureBot()
        tracker = PNLTracker(bot=bot, chat_id="-100", database_url=path)
        async def no_image(_row):
            return None
        tracker._get_token_image_url = no_image
        tracker.add_signal({
            "chain": "solana",
            "address": "TokenEmoji",
            "symbol": "EMOJI",
            "price": 0.01,
            "pair": "PairEmoji",
            "marketcap": 10000,
        })
        row = tracker.get_tracked("solana:TokenEmoji")[0]

        # 1X means two emojis.
        asyncio.run(tracker._send_update(row, 10000, 0.01, 0, 0, 0))
        self.assertEqual(bot.messages[-1]["text"].count("💸"), 2)

        # A 10.5X total market-cap multiple still gives 21 emojis.
        asyncio.run(tracker._send_update(row, 105000, 0.105, 950, 900, 950))
        self.assertEqual(bot.messages[-1]["text"].count("💸"), 21)
        emoji_lines = [
            line for line in bot.messages[-1]["text"].splitlines()
            if "💸" in line
        ]
        self.assertEqual([line.count("💸") for line in emoji_lines], [10, 10, 1])


    def test_pnl_milestone_sends_token_photo_with_ca_at_bottom(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        bot = CaptureBot()
        tracker = PNLTracker(bot=bot, chat_id="-100", database_url=path)

        async def token_image(_row):
            return "https://example.com/token-logo.png"
        tracker._get_token_image_url = token_image

        tracker.add_signal({
            "chain": "solana",
            "address": "TokenPhotoCA",
            "symbol": "PHOTO",
            "price": 0.01,
            "pair": "PairPhoto",
            "marketcap": 10000,
        })
        row = tracker.get_tracked("solana:TokenPhotoCA")[0]
        asyncio.run(tracker._send_update(row, 15000, 0.015, 50, 50, 50))

        self.assertEqual(len(bot.photos), 1)
        self.assertEqual(len(bot.messages), 0)
        photo = bot.photos[0]
        self.assertEqual(photo["photo"], "https://example.com/token-logo.png")
        self.assertIn("PHOTO is up 50%", photo["caption"])
        self.assertTrue(photo["caption"].endswith("<code>TokenPhotoCA</code>"))

    def test_drawdown_does_not_send_telegram_alert(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        bot = CaptureBot()
        tracker = PNLTracker(bot=bot, chat_id="-100", database_url=path)
        async def no_image(_row):
            return None
        tracker._get_token_image_url = no_image
        tracker.add_signal({
            "chain": "solana",
            "address": "TokenDrawdown",
            "symbol": "DRAWDOWN",
            "price": 0.01,
            "pair": "PairDrawdown",
            "marketcap": 10000,
        })
        row = tracker.get_tracked("solana:TokenDrawdown")[0]

        # First rise sends milestone updates as normal.
        asyncio.run(tracker._process_market_cap(row, 30000, 0.03))
        messages_after_rise = len(bot.messages)
        self.assertGreater(messages_after_rise, 0)

        # A large fall from the recorded peak must not send a drawdown alert.
        asyncio.run(tracker._process_market_cap(row, 20000, 0.02))
        self.assertEqual(len(bot.messages), messages_after_rise)
        self.assertNotIn(
            "DRAWDOWN ALERT",
            "\\n".join(message["text"] for message in bot.messages),
        )


if __name__ == "__main__":
    unittest.main()
