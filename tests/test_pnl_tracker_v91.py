import asyncio
import os
import tempfile
import unittest

from services.pnl_tracker import PNLTracker


class FakeDex:
    def __init__(self, pairs):
        self.pairs = pairs

    async def tokens(self, addresses):
        return self.pairs


class FakeBot:
    async def send_message(self, **kwargs):
        return None


class TestPNLTrackerV91(unittest.TestCase):

    def make_tracker(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        tracker = PNLTracker(
            bot=FakeBot(),
            chat_id="-100",
            database_url=path,
            max_tracked=50,
        )
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return tracker

    def test_signal_stores_pair_address_and_chain_key(self):
        tracker = self.make_tracker()

        added = tracker.add_signal({
            "chain": "solana",
            "address": "Token111",
            "symbol": "TEST",
            "price": "0.01",
            "pair": "Pair111",
        })

        self.assertTrue(added)

        rows = tracker.get_tracked("solana:Token111")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["signal_key"], "solana:Token111")
        self.assertEqual(rows[0]["pair_address"], "Pair111")

    def test_current_price_prefers_entry_pair_not_highest_price_pool(self):
        tracker = self.make_tracker()

        tracker.add_signal({
            "chain": "base",
            "address": "0xToken",
            "symbol": "TEST",
            "price": 1.0,
            "pair": "entry-pair",
        })

        tracker.dex = FakeDex([
            {
                "chainId": "base",
                "pairAddress": "entry-pair",
                "baseToken": {"address": "0xToken"},
                "priceUsd": "1.20",
                "liquidity": {"usd": 100000},
            },
            {
                "chainId": "base",
                "pairAddress": "other-pair",
                "baseToken": {"address": "0xToken"},
                "priceUsd": "9.00",
                "liquidity": {"usd": 1000},
            },
        ])

        rows = tracker.get_tracked("base:0xToken")
        prices = asyncio.run(
            tracker._fetch_prices(rows, "base")
        )

        self.assertAlmostEqual(
            prices["base:0xToken"],
            1.20,
        )

    def test_fallback_uses_most_liquid_pool_not_highest_price(self):
        tracker = self.make_tracker()

        tracker.add_signal({
            "chain": "base",
            "address": "0xToken",
            "symbol": "TEST",
            "price": 1.0,
            "pair": "gone-pair",
        })

        tracker.dex = FakeDex([
            {
                "chainId": "base",
                "pairAddress": "thin-expensive",
                "baseToken": {"address": "0xToken"},
                "priceUsd": "10.00",
                "liquidity": {"usd": 1000},
            },
            {
                "chainId": "base",
                "pairAddress": "deep-pool",
                "baseToken": {"address": "0xToken"},
                "priceUsd": "1.50",
                "liquidity": {"usd": 100000},
            },
        ])

        rows = tracker.get_tracked("base:0xToken")
        prices = asyncio.run(
            tracker._fetch_prices(rows, "base")
        )

        self.assertAlmostEqual(
            prices["base:0xToken"],
            1.50,
        )

    def test_migration_adds_pair_address_to_old_database(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))

        import sqlite3

        db = sqlite3.connect(path)
        db.execute("""
            CREATE TABLE pnl_tracking (
                signal_key TEXT PRIMARY KEY,
                chain TEXT NOT NULL,
                address TEXT NOT NULL,
                symbol TEXT,
                entry_price REAL NOT NULL,
                current_price REAL NOT NULL,
                highest_price REAL NOT NULL,
                highest_pnl REAL DEFAULT 0,
                last_milestone REAL DEFAULT 0,
                drawdown_alerted_peak REAL DEFAULT 0,
                started_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        db.commit()
        db.close()

        tracker = PNLTracker(
            bot=FakeBot(),
            chat_id="-100",
            database_url=path,
        )

        db = sqlite3.connect(path)
        try:
            columns = {
                row[1]
                for row in db.execute(
                    "PRAGMA table_info(pnl_tracking)"
                ).fetchall()
            }
        finally:
            db.close()

        self.assertIn("pair_address", columns)
        self.assertIn("drawdown_alerted_peak", columns)


if __name__ == "__main__":
    unittest.main()
