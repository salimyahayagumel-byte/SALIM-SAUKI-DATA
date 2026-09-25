import unittest

from ai.scoring import AIScoring
from services.auto_signal import AutoSignalEngine
from services.final_signal import FinalSignalEngine


class V10SignalIntegrityTests(unittest.TestCase):
    def test_ai_scoring_never_uses_buy_watch_label(self):
        result = AIScoring.calculate({
            "liquidity": 100_000,
            "market_cap": 50_000,
            "volume_24h": 100_000,
            "price_change_24h": 25,
            "buys24h": 800,
            "sells24h": 200,
        })
        self.assertNotIn("BUY WATCH", result["signal"].upper())
        self.assertEqual(result["signal_source"], "ai_scoring")

    def test_final_engine_accepts_security_69_as_pass(self):
        token = {
            "chain": "robinhood",
            "marketcap": 100_000,
            "liquidity": 50_000,
            "volume_ratio": 0.5,
            "total_txns": 100,
            "buy_ratio": 0.70,
            "ai_score": 90,
            "gem_score": 90,
        }
        result = FinalSignalEngine.evaluate(token, {
            "security_score": 69,
            "should_pass": True,
        })
        self.assertTrue(result["should_signal"])
        self.assertIn(
            result["signal"],
            {"🔥 STRONG GEM", "🚀 GEM SIGNAL", "👀 EARLY GEM"},
        )
        self.assertEqual(result["final_signal"], result["signal"])

    def test_auto_signal_allows_early_gem_delivery(self):
        token = {
            "final_should_signal": True,
            "final_status": "EARLY GEM",
            "final_signal": "👀 EARLY GEM",
            "confirmed_gem": False,
            "false_signal_penalty": 0,
            "is_recommended": True,
            "security_should_pass": True,
            "security_score": 69,
            "recommendation_score": 70,
            "final_score": 65,
        }
        self.assertEqual(
            AutoSignalEngine._signal_rejection_reason(token),
            "",
        )

    def test_auto_signal_rejects_mismatched_final_status(self):
        token = {
            "final_should_signal": True,
            "final_status": "WATCH",
            "final_signal": "🔥 STRONG GEM",
        }
        self.assertEqual(
            AutoSignalEngine._signal_rejection_reason(token),
            "final_status",
        )

    def test_auto_signal_rejects_mismatched_final_signal(self):
        token = {
            "final_should_signal": True,
            "final_status": "STRONG GEM",
            "final_signal": "🔥 STRONG BUY WATCH",
        }
        self.assertEqual(
            AutoSignalEngine._signal_rejection_reason(token),
            "final_signal_integrity",
        )


if __name__ == "__main__":
    unittest.main()
