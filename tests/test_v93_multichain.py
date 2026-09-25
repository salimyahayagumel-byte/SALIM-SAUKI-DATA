import unittest

from services.scanner import TokenScanner
from services.final_signal import FinalSignalEngine


class V93MultiChainTests(unittest.TestCase):
    def test_supported_chains_include_robinhood_and_arc(self):
        self.assertIn("robinhood", TokenScanner.SUPPORTED_CHAINS)
        self.assertIn("arc", TokenScanner.SUPPORTED_CHAINS)
        self.assertIn("robinhood", FinalSignalEngine.SUPPORTED_CHAINS)
        self.assertIn("arc", FinalSignalEngine.SUPPORTED_CHAINS)

    def test_early_evm_thresholds(self):
        self.assertEqual(TokenScanner.ROBINHOOD_MIN_MARKETCAP, 10_000)
        self.assertEqual(TokenScanner.ARC_MIN_MARKETCAP, 10_000)
        self.assertEqual(TokenScanner.BASE_MIN_LIQUIDITY, 3_000)
        self.assertEqual(TokenScanner.ROBINHOOD_MIN_LIQUIDITY, 3_000)
        self.assertEqual(TokenScanner.ARC_MIN_LIQUIDITY, 3_000)

    def test_evm_rpc_defaults(self):
        from services.security import SecurityChecker
        checker = SecurityChecker()
        self.assertIn("robinhood", checker.robinhood_rpc_url)
        self.assertIn("arc", checker.arc_rpc_url)

    def test_multichain_marketcap_and_age_window(self):
        self.assertEqual(TokenScanner.MIN_TOKEN_AGE_SECONDS, 1)
        self.assertEqual(TokenScanner.EVM_MIN_TOKEN_AGE_SECONDS, 1)
        self.assertEqual(TokenScanner.SOLANA_MIN_MARKETCAP, 10_000)
        self.assertEqual(TokenScanner.SOLANA_MIN_LIQUIDITY, 10_000)
        self.assertEqual(TokenScanner.SOLANA_MIN_VOLUME_6H, 2_000)
        self.assertEqual(TokenScanner.SOLANA_MIN_TXNS_1H, 10)

    def test_relaxed_discovery_thresholds(self):
        self.assertEqual(TokenScanner.SOLANA_MIN_LIQUIDITY, 10_000)
        self.assertEqual(TokenScanner.SOLANA_MIN_VOLUME_6H, 2_000)
        self.assertEqual(TokenScanner.SOLANA_MIN_TXNS_1H, 10)
        self.assertEqual(TokenScanner.BASE_MIN_LIQUIDITY, 3_000)
        self.assertEqual(TokenScanner.BASE_MIN_VOLUME_6H, 2_000)
        self.assertEqual(TokenScanner.BASE_MIN_TXNS_1H, 10)
        self.assertEqual(TokenScanner.ROBINHOOD_MIN_LIQUIDITY, 3_000)
        self.assertEqual(TokenScanner.ROBINHOOD_MIN_VOLUME_6H, 2_000)
        self.assertEqual(TokenScanner.ROBINHOOD_MIN_TXNS_1H, 10)
        self.assertEqual(TokenScanner.ARC_MIN_LIQUIDITY, 3_000)
        self.assertEqual(TokenScanner.ARC_MIN_VOLUME_6H, 2_000)
        self.assertEqual(TokenScanner.ARC_MIN_TXNS_1H, 10)
        self.assertEqual(TokenScanner.MIN_BUY_RATIO, 0.45)

    def test_max_marketcap_and_age_window(self):
        self.assertEqual(TokenScanner.MAX_MARKETCAP, 1_000_000)
        self.assertEqual(TokenScanner.MAX_TOKEN_AGE_SECONDS, 48 * 60 * 60)
        self.assertEqual(TokenScanner.SOLANA_MAX_MARKETCAP, 1_000_000)
        self.assertEqual(TokenScanner.BASE_MAX_MARKETCAP, 1_000_000)
        self.assertEqual(TokenScanner.ROBINHOOD_MAX_MARKETCAP, 1_000_000)
        self.assertEqual(TokenScanner.ARC_MAX_MARKETCAP, 1_000_000)


if __name__ == "__main__":
    unittest.main()
