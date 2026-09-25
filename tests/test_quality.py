import asyncio
import time
import unittest

from services.auto_signal import AutoSignalEngine
from services.scanner import TokenScanner


class FakeDex:
    async def discover_solana(self, queries):
        return []

    async def discover_base(self, queries):
        return []


class ScannerQualityTests(unittest.TestCase):
    def test_contract_address_detection(self):
        self.assertTrue(
            TokenScanner._looks_like_contract_address(
                "0x4200000000000000000000000000000000000006"
            )
        )
        self.assertTrue(
            TokenScanner._looks_like_contract_address(
                "So11111111111111111111111111111111111111112"
            )
        )
        self.assertFalse(
            TokenScanner._looks_like_contract_address("bonk")
        )

    def test_scanner_rejects_tokens_older_than_48_hours(self):
        scanner = TokenScanner.__new__(TokenScanner)
        scanner.dex = FakeDex()
        scanner.security = None
        scanner.gem_detector = None

        old_pair = {
            "chainId": "solana",
            "baseToken": {"address": "OLDTOKEN", "name": "Old", "symbol": "OLD"},
            "liquidity": {"usd": 50000},
            "volume": {"h24": 20000},
            "txns": {"h24": {"buys": 70, "sells": 30}},
            "marketCap": 100000,
            "priceChange": {"h24": 2},
            "pairCreatedAt": (time.time() - 49 * 60 * 60) * 1000,
        }

        async def discovery(_):
            return [old_pair]

        scanner.dex.discover_solana = discovery
        scanner.security = type("Security", (), {"check": lambda self, token: {}})()
        scanner.gem_detector = type("Gem", (), {"analyze": lambda self, token: {}})()

        results = asyncio.run(scanner.scan("sol"))
        self.assertEqual(results, [])
        self.assertEqual(scanner.last_scan_stats["age_rejected"], 1)

    def test_scanner_keeps_best_pool_for_same_token(self):
        scanner = TokenScanner.__new__(TokenScanner)
        scanner.dex = FakeDex()
        scanner.security = None
        scanner.gem_detector = None

        pairs = [
            {
                "chainId": "solana",
                "baseToken": {"address": "TOKEN", "name": "T", "symbol": "T"},
                "liquidity": {"usd": 12000},
                "volume": {"h6": 10000, "h24": 15000},
                "txns": {
                    "h1": {"buys": 80, "sells": 70},
                    "h24": {"buys": 15, "sells": 15},
                },
                "marketCap": 150000,
                "priceChange": {"h24": 1},
                "pairCreatedAt": (time.time() - 6 * 60 * 60) * 1000,
            },
            {
                "chainId": "solana",
                "baseToken": {"address": "TOKEN", "name": "T", "symbol": "T"},
                "liquidity": {"usd": 50000},
                "volume": {"h6": 30000, "h24": 50000},
                "txns": {
                    "h1": {"buys": 80, "sells": 70},
                    "h24": {"buys": 70, "sells": 30},
                },
                "marketCap": 150000,
                "priceChange": {"h24": 2},
                "pairCreatedAt": (time.time() - 6 * 60 * 60) * 1000,
            },
        ]

        async def discovery(_):
            return pairs

        scanner.dex.discover_solana = discovery

        async def fake_security(self, _):
            return {
                "security_score": 100,
                "should_pass": True,
                "security_status": "PASS",
                "security_reasons": [],
            }

        scanner.security = type("Security", (), {"check": fake_security})()

        # The scoring engines are not under test here; use tiny fakes.
        scanner.gem_detector = type("Gem", (), {"analyze": lambda self, token: {
            "gem_score": 80, "level": "STRONG GEM", "signal": "🔥 STRONG GEM",
            "should_signal": True, "reasons": [], "liquidity_ratio": 0.5,
            "volume_ratio": 0.2, "buy_ratio": token["buy_ratio"], "total_txns": token["total_txns"],
        }})()

        # Avoid depending on the full scoring implementations.
        import services.scanner as scanner_module

        original_ai = scanner_module.AIScoring.calculate
        original_final = scanner_module.FinalSignalEngine.evaluate
        original_recommendation = scanner_module.RecommendationEngine.recommend

        try:
            scanner_module.AIScoring.calculate = classmethod(
                lambda cls, token: {"score": 80, "grade": "A", "signal": "BUY"}
            )
            scanner_module.FinalSignalEngine.evaluate = classmethod(
                lambda cls, token, security: {
                    "final_score": 80, "should_signal": True, "status": "STRONG GEM",
                    "signal": "🔥 STRONG GEM", "reasons": [],
                }
            )
            scanner_module.RecommendationEngine.recommend = classmethod(
                lambda cls, token: {
                    "recommendation_score": 80, "recommendation": "BUY", "action": "BUY",
                    "confidence": 80, "risk_level": "LOW", "market_stage": "EARLY",
                    "hard_reject": False, "positive_reasons": [], "risk_flags": [],
                    "summary": "ok", "is_recommended": True,
                }
            )

            result = asyncio.run(scanner.scan("solana"))
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["liquidity"], 50000)
            self.assertEqual(result[0]["volume24h"], 50000)
            # V10: the public signal field must be the final gated result,
            # never the intermediate AI classifier.
            self.assertEqual(result[0]["signal"], result[0]["final_signal"])
            self.assertEqual(result[0]["ai_signal"], "BUY")
            self.assertEqual(result[0]["signal_source"], "final_signal_engine")
        finally:
            scanner_module.AIScoring.calculate = original_ai
            scanner_module.FinalSignalEngine.evaluate = original_final
            scanner_module.RecommendationEngine.recommend = original_recommendation


class BaseSecurityQualityTests(unittest.TestCase):
    def test_honeypot_risk_can_block_base_security(self):
        from services.security import SecurityChecker

        checker = SecurityChecker()
        async def no_code(_address):
            return None

        checker.get_base_contract_code = no_code
        result = asyncio.run(
            checker.check_base({
                "chain": "base",
                "address": "0x4200000000000000000000000000000000000006",
            })
        )
        self.assertFalse(result["should_pass"])


class AutoSignalQualityTests(unittest.TestCase):
    def make_engine(self):
        engine = AutoSignalEngine(
            bot=None,
            chat_id="test",
            max_signals_per_scan=3,
            max_signals_per_chain=2,
        )
        return engine

    def test_x_status_link_is_rejected(self):
        self.assertFalse(
            AutoSignalEngine._valid_social_url(
                "https://x.com/elonmusk/status/123"
            )
        )
        self.assertTrue(
            AutoSignalEngine._valid_social_url(
                "https://x.com/projectname"
            )
        )

    def test_telegram_invite_link_is_rejected(self):
        self.assertFalse(
            AutoSignalEngine._valid_social_url(
                "https://t.me/+abcdef"
            )
        )
        self.assertTrue(
            AutoSignalEngine._valid_social_url(
                "https://t.me/projectname"
            )
        )

    def test_signal_key_is_chain_aware(self):
        engine = self.make_engine()
        self.assertNotEqual(
            engine._signal_key({"chain": "solana", "address": "same"}),
            engine._signal_key({"chain": "base", "address": "same"}),
        )

    def test_multi_chain_selection_is_fair(self):
        engine = self.make_engine()
        candidates = [
            ((100,), {"chain": "solana", "address": "s1"}),
            ((99,), {"chain": "solana", "address": "s2"}),
            ((98,), {"chain": "solana", "address": "s3"}),
            ((97,), {"chain": "base", "address": "b1"}),
        ]
        selected, counts = engine._select_candidates(candidates)
        self.assertEqual(len(selected), 3)
        self.assertEqual(counts["solana"], 2)
        self.assertEqual(counts["base"], 1)
        self.assertIn("b1", {item[1]["address"] for item in selected})


if __name__ == "__main__":
    unittest.main()


def test_recommendation_accepts_base_chain():
    from ai.recommendation import RecommendationEngine

    token = {
        "chain": "base",
        "ai_score": 88,
        "gem_score": 82,
        "security_score": 100,
        "security_should_pass": True,
        "final_score": 86,
        "liquidity": 150_000,
        "marketcap": 500_000,
        "volume24h": 200_000,
        "total_txns": 500,
        "buy_ratio": 0.62,
        "liquidity_ratio": 0.30,
        "volume_ratio": 0.40,
        "price_change_24h": 12,
        "honeypot_available": True,
        "honeypot_detected": False,
        "sell_tax": 2,
    }

    result = RecommendationEngine.recommend(token)

    assert result["hard_reject"] is False
    assert result["security_pass"] is True
    assert result["action"] in {"BUY", "STRONG BUY", "WATCH"}


def test_recommendation_rejects_unsupported_chain():
    from ai.recommendation import RecommendationEngine

    token = {
        "chain": "ethereum",
        "ai_score": 99,
        "gem_score": 99,
        "security_score": 100,
        "security_should_pass": True,
        "final_score": 99,
        "liquidity": 1_000_000,
        "marketcap": 500_000,
        "volume24h": 1_000_000,
        "total_txns": 5_000,
        "buy_ratio": 0.70,
        "liquidity_ratio": 2.0,
        "volume_ratio": 2.0,
        "price_change_24h": 20,
    }

    result = RecommendationEngine.recommend(token)

    assert result["hard_reject"] is True
    assert result["action"] == "AVOID"


def test_whale_analyzer_does_not_claim_wallet_tracking():
    from ai.whales import WhaleAnalyzer

    result = WhaleAnalyzer().analyze({
        "holder": 2_000,
        "liquidity": 100_000,
        "marketCap": 500_000,
    })

    assert result["is_actual_whale_analysis"] is False
    assert "market support" in result["status"].lower()


def test_persistent_signal_history_survives_reload(tmp_path):
    from services.history import SignalHistory

    db = tmp_path / "history.db"
    first = SignalHistory(str(db))
    import time
    now = time.time()
    first.record("base:0xabc", "base", "0xabc", "ABC", 88, now)

    second = SignalHistory(str(db))
    loaded = second.load_recent(10_000_000)

    assert loaded["base:0xabc"] == now


def test_config_database_url_has_safe_default():
    import config
    assert config.DATABASE_URL


def test_new_bot_handlers_exist():
    from pathlib import Path

    for name in ("help.py", "status.py", "health.py"):
        assert Path("handlers", name).exists()


def test_scanner_exposes_security_confidence_fields():
    import inspect
    from services.scanner import TokenScanner

    source = inspect.getsource(TokenScanner.scan)
    assert 'security_confidence' in source
    assert 'security_evidence_score' in source


def test_signal_history_persists_and_loads(tmp_path):
    from services.history import SignalHistory

    db = tmp_path / 'history.db'
    first = SignalHistory(f'sqlite:///{db}')
    first.record('base:0xabc', 'base', '0xabc', 'TEST', 88, 1000)

    second = SignalHistory(f'sqlite:///{db}')
    loaded = second.load_recent(9999999999)
    assert loaded['base:0xabc'] == 1000
