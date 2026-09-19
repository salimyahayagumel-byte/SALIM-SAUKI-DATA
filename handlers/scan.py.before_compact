from telegram import Update
from telegram.ext import ContextTypes

from services.scanner import TokenScanner


def money(value):
    try:
        value = float(value or 0)

        if value >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"

        if value >= 1_000:
            return f"${value / 1_000:.1f}K"

        return f"${value:,.0f}"

    except (TypeError, ValueError):
        return "$0"


def signal_emoji(signal):
    signal = str(signal or "").upper()

    if "STRONG GEM" in signal:
        return "🔥"

    if "GEM SIGNAL" in signal:
        return "🚀"

    if "EARLY GEM" in signal:
        return "👀"

    if "WATCH" in signal:
        return "🟡"

    return "⛔"


def format_signal(token):
    symbol = token.get("symbol", "N/A")
    name = token.get("name", "Unknown")

    final_score = int(
        token.get("final_score", 0)
    )

    ai_score = int(
        token.get("ai_score", 0)
    )

    gem_score = int(
        token.get("gem_score", 0)
    )

    security_score = int(
        token.get("security_score", 0)
    )

    buy_ratio = float(
        token.get("buy_ratio", 0)
    )

    total_txns = int(
        token.get("total_txns", 0)
    )

    signal = token.get(
        "final_signal",
        "⛔ NO SIGNAL"
    )

    reasons = token.get(
        "final_reasons",
        []
    )

    emoji = signal_emoji(signal)

    lines = [
        "🧠 DEX ANALYSIS BOT",
        "💎 EARLY GEM SCANNER",
        "",
        f"{emoji} {signal}",
        "",
        f"🪙 ${symbol} — {name}",
        "⛓️ Solana",
        "",
        f"🎯 FINAL SCORE: {final_score}/100",
        f"🧠 AI: {ai_score}/100",
        f"💎 GEM: {gem_score}/100",
        f"🔐 SECURITY: {security_score}/100",
        "",
        f"💰 MC: {money(token.get('marketcap'))}",
        f"💧 LIQ: {money(token.get('liquidity'))}",
        f"📈 VOL 24H: {money(token.get('volume24h'))}",
        f"🔄 TXNS: {total_txns}",
        f"🟢 BUY RATIO: {buy_ratio * 100:.1f}%",
        "",
    ]

    if reasons:
        lines.append("📋 REASONS:")

        for reason in reasons[:5]:
            lines.append(f"• {reason}")

        lines.append("")

    lines.extend(
        [
            "📄 CONTRACT:",
            f"`{token.get('address', 'N/A')}`",
            "",
            "⚠️ Wannan signal ba guarantee bane.",
            "DYOR kafin kowane trade.",
        ]
    )

    return "\n".join(lines)


async def scan(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.message is None:
        return

    query = (
        " ".join(context.args)
        if context.args
        else "sol"
    )

    await update.message.reply_text(
        "🔎 Ana scanning...\n"
        f"Query: `{query}`",
        parse_mode="Markdown"
    )

    scanner = TokenScanner()

    try:

        results = await scanner.scan(query)

    except Exception as exc:

        print(
            "Scanner error:",
            repr(exc)
        )

        await update.message.reply_text(
            "❌ Scanner Error:\n"
            f"{exc}"
        )

        return

    if not results:

        await update.message.reply_text(
            "🔎 Babu candidate da ya wuce "
            "filters a yanzu."
        )

        return

    # =========================================
    # ONLY REAL SIGNALS
    # =========================================

    signals = [
        token
        for token in results
        if token.get(
            "final_should_signal",
            False
        )
    ]

    if not signals:

        best = results[0]

        await update.message.reply_text(
            "👀 An gama scanning.\n\n"
            f"Candidates: {len(results)}\n"
            f"Best: ${best.get('symbol', 'N/A')}\n"
            f"Final Score: "
            f"{best.get('final_score', 0)}/100\n\n"
            "⛔ Babu GEM signal mai ƙarfi "
            "a wannan scan.\n\n"
            "Za mu jira confirmation maimakon "
            "tura weak signal."
        )

        return

    # =========================================
    # SEND TOP SIGNALS
    # =========================================

    for token in signals[:5]:

        try:

            await update.message.reply_text(
                format_signal(token),
                parse_mode="Markdown"
            )

        except Exception as exc:

            print(
                "Telegram signal error:",
                repr(exc)
            )
