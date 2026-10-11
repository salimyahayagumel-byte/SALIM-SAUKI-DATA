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

    def test_money_emojis_follow_x_multiplier(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        bot = CaptureBot()
        tracker = PNLTracker(bot=bot, chat_id="-100", database_url=path)
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

        # 10.5X means 21 emojis.
        asyncio.run(tracker._send_update(row, 105000, 0.105, 950, 900, 950))
        self.assertEqual(bot.messages[-1]["text"].count("💸"), 21)


    def test_drawdown_does_not_send_telegram_alert(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        bot = CaptureBot()
        tracker = PNLTracker(bot=bot, chat_id="-100", database_url=path)
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
