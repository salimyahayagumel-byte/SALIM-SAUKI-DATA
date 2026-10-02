# SALIM SAUKI DATA V10 — Multi-Chain Signal Integrity

V10 keeps the V9.3 relaxed discovery architecture while fixing signal-label ambiguity and strengthening the final signal gate.

## Core discovery
- Solana, Base, Robinhood Chain, and Arc remain supported.
- Market cap: $10K–$1M.
- Pair age: 1 second–48 hours.
- Relaxed discovery thresholds remain chain-aware.
- Security protections remain enabled; security is never bypassed to create a signal.

## Signal integrity
- AI score labels are explicitly AI-only and no longer use BUY/STRONG BUY wording.
- `ai_signal` stores the AI classification.
- `gem_signal` stores the GEM detector classification.
- `final_signal` is the authoritative gated signal.
- `signal` is now a compatibility alias of `final_signal`.
- Automatic Telegram delivery requires an exact final status/signal pair: STRONG GEM or GEM SIGNAL.
- Security score and security pass remain hard gates.

## Safety
- No profitability guarantee is implied by any score or label.
- Early GEM/WATCH results remain analysis candidates, not automatic Telegram signals.
- Helius remains optional when other Solana RPCs are healthy.

## Validation
- Unit tests include V10 signal-integrity checks.
- Production deployment must wait until tests and real multi-chain discovery are verified.
