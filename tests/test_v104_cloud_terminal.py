import tempfile
from pathlib import Path

from services.auto_signal import AutoSignalEngine
from services.final_signal import FinalSignalEngine
from services.history import SignalHistory


def test_chain_security_thresholds_are_explicit():
    assert FinalSignalEngine.SECURITY_MIN_BY_CHAIN == {
        "solana": 90,
        "base": 69,
        "robinhood": 69,
        "arc": 69,
    }
    assert AutoSignalEngine.SECURITY_MIN_BY_CHAIN == FinalSignalEngine.SECURITY_MIN_BY_CHAIN


def test_signal_history_persists_full_token_snapshot():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "signals.db"
        store = SignalHistory(str(db))
        token = {
            "chain": "solana",
            "address": "ABC123",
            "symbol": "TEST",
            "final_signal": "🚀 GEM SIGNAL",
            "final_score": 82,
            "security_score": 94,
            "image_url": "https://example.com/logo.png",
        }
        store.record("solana:ABC123", "solana", "ABC123", "TEST", 82, token=token)
        rows = store.recent_signals(10)
        assert len(rows) == 1
        assert rows[0]["final_signal"] == "🚀 GEM SIGNAL"
        assert rows[0]["security_score"] == 94
        assert rows[0]["image_url"].endswith("logo.png")


def test_helius_api_key_builds_solana_rpc_fallback(monkeypatch):
    monkeypatch.setenv("HELIUS_API_KEY", "unit-test-helius-key")
    monkeypatch.delenv("FLUXRPC_RPC_URL", raising=False)
    monkeypatch.delenv("FLUXRPC_API_KEY", raising=False)
    monkeypatch.delenv("SOLANA_RPC_URL", raising=False)
    monkeypatch.delenv("SOLANA_RPC_URLS", raising=False)

    from services.security import SecurityChecker
    checker = SecurityChecker()
    assert any(
        url.startswith("https://mainnet.helius-rpc.com/?api-key=")
        for url in checker.rpc_urls
    )


def test_solana_security_threshold_is_strict_90():
    from services.security import SecurityChecker
    assert SecurityChecker.SECURITY_MIN_BY_CHAIN["solana"] == 90
    assert SecurityChecker.SECURITY_MIN_BY_CHAIN["base"] == 69
    assert SecurityChecker.SECURITY_MIN_BY_CHAIN["robinhood"] == 69
    assert SecurityChecker.SECURITY_MIN_BY_CHAIN["arc"] == 69


def test_dashboard_exposes_live_signal_and_ready_routes():
    from pathlib import Path
    source = Path("web/dashboard.py").read_text(encoding="utf-8")
    assert 'path == "/api/signals"' in source
    assert 'path == "/ready"' in source
    assert 'path.startswith("/api/signals/")' in source
