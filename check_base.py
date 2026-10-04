import asyncio
from services.scanner import TokenScanner


async def main():
    scanner = TokenScanner()

    results = await scanner.scan("base")

    print()
    print("=" * 70)
    print("BASE AUTO-SIGNAL DEBUG")
    print("=" * 70)

    print(f"Candidates returned: {len(results)}")

    for i, token in enumerate(results, 1):
        print()
        print(f"--- BASE TOKEN #{i} ---")

        print("Symbol:", token.get("symbol"))
        print("Address:", token.get("address"))
        print("Final:", token.get("final_score"))
        print("Final signal:", token.get("final_should_signal"))
        print("Recommendation:", token.get("recommendation_score"))
        print("Recommended:", token.get("is_recommended"))
        print("Security:", token.get("security_score"))
        print("Security pass:", token.get("security_should_pass"))
        print("GEM:", token.get("gem_score"))
        print("AI:", token.get("ai_score"))
        print("Buy ratio:", token.get("buy_ratio"))
        print("Liquidity:", token.get("liquidity"))
        print("Market cap:", token.get("market_cap"))
        print("Volume 24h:", token.get("volume_24h"))
        print("Txns:", token.get("txns"))


if __name__ == "__main__":
    asyncio.run(main())
