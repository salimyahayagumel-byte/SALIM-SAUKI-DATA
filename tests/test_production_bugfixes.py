import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_auto_signal_has_no_module_level_self_reference():
    tree = ast.parse((ROOT / "services" / "auto_signal.py").read_text())
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        assert not any(isinstance(x, ast.Name) and x.id == "self" for x in ast.walk(node))


def test_rpc_logs_use_safe_url():
    source = (ROOT / "services" / "security.py").read_text()
    assert 'f" {self._safe_rpc_url(rpc_url)}"' in source
    assert 'f"{self._safe_rpc_url(rpc_url)} "' in source


def test_render_has_single_polling_owner():
    source = (ROOT / "render.yaml").read_text()
    assert "salim-sauki-data-web" in source
    assert "salim-sauki-data-worker" in source
    assert 'TELEGRAM_POLLING_ENABLED' in source
    assert 'value: "false"' in source
    assert 'value: "true"' in source


def test_dex_base_discovery_is_bounded():
    source = (ROOT / "services" / "dexscreener.py").read_text()
    assert '"base microcap"' not in source
    assert '"base smallcap"' not in source
    assert '"clanker"' in source


def test_final_signal_chain_security_and_market_cap_gates():
    source = (ROOT / "services" / "final_signal.py").read_text()
    assert '"solana": 90' in source
    assert '"base": 69' in source
    assert '"robinhood": 69' in source
    assert '"arc": 69' in source
    assert "MIN_MARKET_CAP = 10_000" in source
    assert "MAX_MARKET_CAP = 1_000_000" in source
