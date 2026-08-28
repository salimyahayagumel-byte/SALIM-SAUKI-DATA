from telegram import Update
from telegram.ext import ContextTypes

from services.scanner import TokenScanner


async def analyze(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Telegram /analyze command.

    Example:
        /analyze sol
        /analyze bonk
        /analyze <contract>
    """

    if update.message is None:
        return

    # =========================================
    # CHECK QUERY
    # =========================================

    if len(context.args) == 0:

        await update.message.reply_text(
            "🧠 SALIM SAUKI DATA\n\n"
            "Amfani:\n"
            "/analyze <token>\n\n"
            "Misalai:\n"
            "/analyze sol\n"
            "/analyze bonk\n"
            "/analyze <contract>"
        )

        return

    query = " ".join(
        context.args
    ).strip()

    # =========================================
    # ANALYZE
    # =========================================

    try:

        scanner = TokenScanner()

        results = await scanner.scan(
            query
        )

        if not results:

            await update.message.reply_text(
                "❌ Ba a sami token candidate ba.\n\n"
                f"🔎 Query: {query}\n\n"
                "Gwada wani token ko contract."
            )

            return

        # =====================================
        # BEST RESULT
        # =====================================

        token = results[0]

        symbol = token.get(
            "symbol",
            "N/A"
        )

        name = token.get(
            "name",
            "Unknown"
        )

        address = token.get(
            "address",
            "N/A"
        )

        # =====================================
        # MARKET DATA
        # =====================================

        marketcap = float(
            token.get(
                "marketcap",
                0
            ) or 0
        )

        liquidity = float(
            token.get(
                "liquidity",
                0
            ) or 0
        )

        volume = float(
            token.get(
                "volume24h",
                0
            ) or 0
        )

        total_txns = int(
            token.get(
                "total_txns",
                0
            ) or 0
        )

        buy_ratio = float(
            token.get(
                "buy_ratio",
                0
            ) or 0
        )

        price_change = float(
            token.get(
                "price_change_24h",
                0
            ) or 0
        )

        # =====================================
        # SCORES
        # =====================================

        ai_score = int(
            token.get(
                "ai_score",
                0
            ) or 0
        )

        gem_score = int(
            token.get(
                "gem_score",
                0
            ) or 0
        )

        security_score = int(
            token.get(
                "security_score",
                0
            ) or 0
        )

        final_score = int(
            token.get(
                "final_score",
                0
            ) or 0
        )

        # =====================================
        # FINAL SIGNAL
        # =====================================

        final_signal = token.get(
            "final_signal",
            "⛔ NO SIGNAL"
        )

        should_signal = bool(
            token.get(
                "final_should_signal",
                False
            )
        )

        # =====================================
        # RECOMMENDATION
        # =====================================

        recommendation = token.get(
            "recommendation",
            "⛔ NO RECOMMENDATION"
        )

        recommendation_score = int(
            token.get(
                "recommendation_score",
                0
            ) or 0
        )

        confidence = int(
            token.get(
                "recommendation_confidence",
                0
            ) or 0
        )

        risk = token.get(
            "recommendation_risk",
            "⚪ UNKNOWN"
        )

        # =====================================
        # REASONS
        # =====================================

        positive_reasons = token.get(
            "recommendation_positive_reasons",
            []
        ) or []

        risk_flags = token.get(
            "recommendation_risk_flags",
            []
        ) or []

        final_reasons = token.get(
            "final_reasons",
            []
        ) or []

        # =====================================
        # FORMAT POSITIVE REASONS
        # =====================================

        if positive_reasons:

            positive_text = "\n".join(
                f"• {reason}"
                for reason in positive_reasons
            )

        else:

            positive_text = "• Babu positive reason."

        # =====================================
        # FORMAT RISK FLAGS
        # =====================================

        if risk_flags:

            risk_text = "\n".join(
                f"• {reason}"
                for reason in risk_flags
            )

        else:

            risk_text = "• Babu major risk flag."

        # =====================================
        # FORMAT FINAL REASONS
        # =====================================

        if final_reasons:

            final_reason_text = "\n".join(
                f"• {reason}"
                for reason in final_reasons
            )

        else:

            final_reason_text = "• Babu additional reason."

        # =====================================
        # BUY RATIO
        # =====================================

        buy_percent = (
            buy_ratio * 100
        )

        # =====================================
        # STATUS
        # =====================================

        if should_signal:

            signal_status = (
                "🟢 SIGNAL CONFIRMED"
            )

        else:

            signal_status = (
                "🔴 SIGNAL NOT CONFIRMED"
            )

        # =====================================
        # MESSAGE
        # =====================================

        text = (
            "🧠 SALIM SAUKI DATA\n"
            "💎 AI TOKEN ANALYSIS V5\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"

            f"🪙 ${symbol} — {name}\n"
            f"⛓️ Chain: {token.get('chain_name', 'Solana')}\n\n"

            "📊 MARKET DATA\n"
            f"💰 MC: ${marketcap:,.0f}\n"
            f"💧 LIQ: ${liquidity:,.0f}\n"
            f"📈 VOL 24H: ${volume:,.0f}\n"
            f"🔄 TXNS: {total_txns}\n"
            f"🟢 BUY RATIO: {buy_percent:.1f}%\n"
            f"📊 24H CHANGE: {price_change:.2f}%\n\n"

            "🧠 AI ANALYSIS\n"
            f"🤖 AI: {ai_score}/100\n"
            f"💎 GEM: {gem_score}/100\n"
            f"🔐 SECURITY: {security_score}/100\n"
            f"🎯 FINAL: {final_score}/100\n\n"

            "🚀 SIGNAL\n"
            f"{final_signal}\n"
            f"{signal_status}\n\n"

            "🤖 RECOMMENDATION\n"
            f"{recommendation}\n"
            f"📊 Score: {recommendation_score}/100\n"
            f"🎯 Confidence: {confidence}%\n"
            f"🛡 Risk: {risk}\n\n"

            "✅ POSITIVE FACTORS\n"
            f"{positive_text}\n\n"

            "⚠️ RISK FLAGS\n"
            f"{risk_text}\n\n"

            "📋 FINAL REASONS\n"
            f"{final_reason_text}\n\n"

            "📄 CONTRACT ADDRESS\n"
            f"{address}\n\n"

            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ Wannan analysis ba guarantee bane.\n"
            "DYOR kafin kowane trade."
        )

        await update.message.reply_text(
            text
        )

    except Exception as exc:

        print(
            "Analyze handler error:",
            repr(exc)
        )

        await update.message.reply_text(
            "❌ An samu matsala yayin analysis.\n\n"
            f"🔎 Query: {query}\n"
            "Gwada sake komawa bayan ɗan lokaci."
        )
