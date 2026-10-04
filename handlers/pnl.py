from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from services.pnl_tracker import PNLTracker


async def pnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show PNL summary, filtered PNL, or one tracked contract."""
    if update.message is None:
        return

    engine = context.application.bot_data.get("auto_signal_engine")
    tracker = getattr(engine, "pnl_tracker", None) if engine else None

    if tracker is None:
        await update.message.reply_text(
            "⚠️ PNL Tracker bai fara aiki ba tukuna.\n"
            "Da fatan ka jira Auto Signal Engine ya fara."
        )
        return

    argument = " ".join(context.args).strip() if context.args else ""
    lowered = argument.lower()

    # Useful filters while preserving the existing address lookup.
    filter_modes = {
        "summary", "winners", "winner", "profit", "profits", "green",
        "losers", "loser", "loss", "losses", "red", "breakeven", "flat",
        "zero", "2x", "5x", "10x", "best", "top", "gainers", "worst",
        "bottom", "losing",
    }

    if lowered in filter_modes:
        rows = tracker.get_pnl_rows(lowered)
        if lowered in {"summary", "all"}:
            text = tracker.format_pnl_summary(tracker.get_tracked(None))
        elif not rows:
            text = (
                "📈 <b>SALIM SAUKI DATA — PNL</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"ℹ️ Babu token a cikin filter: <b>{PNLTracker._escape(lowered)}</b>"
            )
        else:
            text = (
                "📈 <b>SALIM SAUKI DATA — PNL FILTER</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"🔎 Filter: <b>{PNLTracker._escape(lowered.upper())}</b>\n\n"
                + "\n━━━━━━━━━━━━━━━━━━━━\n".join(
                    PNLTracker.format_manual_pnl(row) for row in rows
                )
            )
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    rows = tracker.get_tracked(argument or None)

    if argument and not rows:
        await update.message.reply_text(
            "❌ Ba a samu wannan contract address a cikin PNL tracker ba.\n\n"
            f"📄 <code>{PNLTracker._escape(argument)}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if not rows:
        await update.message.reply_text(
            "📈 <b>SALIM SAUKI DATA — PNL</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "ℹ️ Babu token da aka fara tracking tukuna.\n"
            "Za a fara tracking ne bayan bot ya aika GEM signal.\n\n"
            "💡 Yi amfani da <code>/pnl summary</code> don summary.",
            parse_mode=ParseMode.HTML,
        )
        return

    title = (
        "📈 <b>SALIM SAUKI DATA — TOKEN PNL</b>"
        if argument
        else "📈 <b>SALIM SAUKI DATA — ALL PNL</b>"
    )

    parts = [title, "━━━━━━━━━━━━━━━━━━━━"]
    for index, row in enumerate(rows, start=1):
        parts.append(PNLTracker.format_manual_pnl(row))
        if index != len(rows):
            parts.append("━━━━━━━━━━━━━━━━━━━━")

    parts.extend([
        "",
        "💡 <code>/pnl summary</code> • <code>/pnl winners</code> • <code>/pnl losers</code>",
        "💡 <code>/pnl 2x</code> • <code>/pnl 5x</code> • <code>/pnl 10x</code>",
        "",
        "⚠️ <i>PNL yana amfani da Market Cap; fees/slippage/taxes ba su cikin lissafin ba.</i>",
    ])

    text = "\n".join(parts)

    # ---------------------------------------------------------
    # TOKEN IMAGE FOR /pnl <contract>
    # ---------------------------------------------------------
    # For a single contract lookup, fetch the token artwork from
    # DexScreener and send it as a Telegram photo when available.
    # The PNL text remains the source of truth; if artwork is
    # unavailable, the normal text response is sent unchanged.
    if argument and len(rows) == 1:
        image_url = ""
        try:
            row = rows[0]
            address = str(row.get("address", "") or "").strip()
            pair_address = str(row.get("pair_address", "") or "").strip()

            if address:
                pairs = await tracker.dex.tokens([address])

                selected = None

                # Prefer the exact pair used by the PNL tracker.
                if pair_address:
                    for pair in pairs:
                        if str(pair.get("pairAddress", "") or "").strip() == pair_address:
                            selected = pair
                            break

                # Otherwise use the first valid pair that has artwork.
                if selected is None:
                    for pair in pairs:
                        info = pair.get("info")
                        if isinstance(info, dict) and str(info.get("imageUrl", "") or "").strip():
                            selected = pair
                            break

                if selected is None and pairs:
                    selected = pairs[0]

                if selected:
                    info = selected.get("info")
                    if isinstance(info, dict):
                        candidate = str(info.get("imageUrl", "") or "").strip()
                        if candidate.startswith(("http://", "https://")):
                            image_url = candidate

        except Exception as image_exc:
            print("PNL image lookup error:", repr(image_exc))

        if image_url:
            try:
                short_caption = (
                    f"💎 <b>${PNLTracker._escape(rows[0].get('symbol', 'N/A'))}</b> — PNL"
                )
                if len(text) <= 1000:
                    await update.message.reply_photo(
                        photo=image_url,
                        caption=text,
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    await update.message.reply_photo(
                        photo=image_url,
                        caption=short_caption,
                        parse_mode=ParseMode.HTML,
                    )
                    await update.message.reply_text(
                        text,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True,
                    )
                return
            except Exception as image_send_exc:
                print("PNL image send error:", repr(image_send_exc))

    if len(text) <= 3800:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    header = title + "\n━━━━━━━━━━━━━━━━━━━━\n"
    chunk = header
    for row in rows:
        block = PNLTracker.format_manual_pnl(row) + "\n━━━━━━━━━━━━━━━━━━━━\n"
        if len(chunk) + len(block) > 3800:
            await update.message.reply_text(
                chunk.rstrip(),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            chunk = header + block
        else:
            chunk += block

    if chunk.strip() != header.strip():
        await update.message.reply_text(
            chunk.rstrip(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
