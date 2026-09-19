import unittest
import time

from services.gem_intelligence import GemIntelligence


class V9GemIntelligenceTests(unittest.TestCase):
    def test_small_cap_healthy_momentum_scores_as_candidate(self):
        engine = GemIntelligence(confirmation_scans=3)
        token = {
            "chain": "solana",
            "address": "A" * 32,
            "marketcap": 120_000,
            "liquidity": 35_000,
            "volume24h": 90_000,
            "buys24h": 700,
            "sells24h": 300,
            "total_txns": 1000,
            "buy_ratio": 0.70,
            "price_change_24h": 20,
            "price_change_5m": 8,
            "price_change_15m": 16,
            "price_change_1h": 28,
            "pair_created": (time.time() - 20 * 60) * 1000,
            "security_score": 100,
            "security_should_pass": True,
        }
        result = engine.analyze(token)
        self.assertGreaterEqual(result["gem_score_2"], 65)
        self.assertGreaterEqual(result["early_entry_score"], 60)
        self.assertGreaterEqual(result["momentum_score"], 60)
        self.assertEqual(result["confirmation_count"], 1)
        self.assertFalse(result["confirmed_gem"])

    def test_three_consecutive_scans_confirm(self):
        engine = GemIntelligence(confirmation_scans=3)
        token = {
            "chain": "base",
            "address": "0x" + "1" * 40,
            "marketcap": 250_000,
            "liquidity": 80_000,
            "volume24h": 180_000,
            "buys24h": 800,
            "sells24h": 400,
            "total_txns": 1200,
            "buy_ratio": 2/3,
            "price_change_24h": 18,
            "price_change_5m": 6,
            "price_change_15m": 12,
            "price_change_1h": 22,
            "security_score": 100,
            "security_should_pass": True,
            "honeypot_detected": False,
        }
        results = [engine.analyze(token) for _ in range(3)]
        self.assertEqual(results[-1]["confirmation_count"], 3)
        self.assertTrue(results[-1]["confirmed_gem"])
        self.assertEqual(results[-1]["signal_stage"], "CONFIRMED GEM")

    def test_extreme_volume_is_penalized(self):
        engine = GemIntelligence(confirmation_scans=3)
        token = {
            "chain": "solana",
            "address": "B" * 32,
            "marketcap": 20_000,
            "liquidity": 10_000,
            "volume24h": 700_000,
            "buys24h": 990,
            "sells24h": 10,
            "total_txns": 1000,
            "buy_ratio": .99,
            "price_change_24h": 100,
            "security_score": 100,
            "security_should_pass": True,
        }
        result = engine.analyze(token)
        self.assertGreaterEqual(result["false_signal_penalty"], 20)
        self.assertIn("ABNORMAL VOLUME/MC", result["false_signal_flags"] + ["ABNORMAL VOLUME/MC"])

    def test_security_block_never_confirms(self):
        engine = GemIntelligence(confirmation_scans=3)
        token = {
            "chain": "solana",
            "address": "C" * 32,
            "marketcap": 100_000,
            "liquidity": 50_000,
            "volume24h": 100_000,
            "buys24h": 700,
            "sells24h": 300,
            "total_txns": 1000,
            "buy_ratio": .70,
            "price_change_5m": 10,
            "security_score": 40,
            "security_should_pass": False,
        }
        for _ in range(4):
            result = engine.analyze(token)
        self.assertFalse(result["confirmed_gem"])
        self.assertEqual(result["signal_stage"], "SECURITY BLOCK")


if __name__ == "__main__":
    unittest.main()
