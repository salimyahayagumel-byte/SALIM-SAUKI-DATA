from html import escape
from urllib.parse import quote

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


def safe_url(value):
    value = str(value or "").strip()

    if not value:
        return ""

    if not (
        value.startswith("http://")
        or value.startswith("https://")
    ):
        return ""

    return escape(value, quote=True)


def normalize_social_url(platform, value):
    """
    Convert DexScreener social information into a safe URL.

    Supports:
    - X / Twitter
    - Telegram
    """

    platform = str(platform or "").strip().lower()
    value = str(value or "").strip()

    if not value:
        return ""

    # -----------------------------------------------------
    # Already a full URL
    # -----------------------------------------------------

    if value.startswith("http://") or value.startswith("https://"):
        return safe_url(value)

    # Remove common @ prefix from handles.
    value = value.lstrip("@").strip()

    if not value:
        return ""

    # -----------------------------------------------------
    # X / Twitter
    # -----------------------------------------------------

    if platform in {
        "twitter",
        "x",
        "x.com",
    }:
        return safe_url(
            f"https://x.com/{quote(value, safe='')}"
        )

    # -----------------------------------------------------
    # Telegram
    # -----------------------------------------------------

    if platform in {
        "telegram",
        "tg",
        "t.me",
    }:
        return safe_url(
            f"https://t.me/{quote(value, safe='')}"
        )

    return ""


def extract_social_links(token):
    """
    Read social links directly from the fields already
    supplied by services/scanner.py.

    Expected DexScreener structure:

        socials = [
            {
                "platform": "twitter",
                "handle": "username"
            },
            {
                "platform": "telegram",
                "handle": "username"
            }
        ]

        websites = [
            {
                "url": "https://example.com"
            }
        ]

    The function also supports direct URL-style entries.
    """

    socials = token.get("socials") or []
    websites = token.get("websites") or []

    twitter_url = ""
    telegram_url = ""
    website_url = ""

    # =====================================================
    # SOCIALS
    # =====================================================

    if isinstance(socials, list):

        for item in socials:

            if isinstance(item, str):

                raw_url = safe_url(item)

                if not raw_url:
                    continue

                lower_url = raw_url.lower()

                if (
                    "twitter.com/" in lower_url
                    or "x.com/" in lower_url
                ):
                    if not twitter_url:
                        twitter_url = raw_url

                elif "t.me/" in lower_url:
                    if not telegram_url:
                        telegram_url = raw_url

                continue

            if not isinstance(item, dict):
                continue

            platform = str(
                item.get("platform", "")
                or item.get("type", "")
                or ""
            ).strip().lower()

            url = (
                item.get("url")
                or item.get("link")
                or ""
            )

            handle = (
                item.get("handle")
                or item.get("username")
                or ""
            )

            # Prefer an actual URL supplied by DexScreener.
            value = url or handle

            if not value:
                continue

            normalized = normalize_social_url(
                platform,
                value
            )

            if not normalized:
                continue

            if platform in {
                "twitter",
                "x",
                "x.com",
            }:
                if not twitter_url:
                    twitter_url = normalized

            elif platform in {
                "telegram",
                "tg",
                "t.me",
            }:
                if not telegram_url:
                    telegram_url = normalized

    # =====================================================
    # WEBSITES
    # =====================================================

    if isinstance(websites, list):

        for item in websites:

            if isinstance(item, str):

                normalized = safe_url(item)

                if normalized:
                    website_url = normalized
                    break

                continue

            if not isinstance(item, dict):
                continue

            value = (
                item.get("url")
                or item.get("link")
                or ""
            )

            normalized = safe_url(value)

            if normalized:
                website_url = normalized
                break

    # =====================================================
    # FALLBACK
    # =====================================================

    # If scanner ever supplies the direct fields, keep
    # supporting them for backwards compatibility.
    if not twitter_url:
        twitter_url = safe_url(
            token.get("twitter_url", "")
        )

    if not telegram_url:
        telegram_url = safe_url(
            token.get("telegram_url", "")
        )

    if not website_url:
        website_url = safe_url(
            token.get("website_url", "")
        )

    return (
        twitter_url,
        telegram_url,
        website_url,
    )


def format_signal(token):
    symbol = escape(
        str(
            token.get("symbol", "N/A")
            or "N/A"
        )
    )

    name = escape(
        str(
            token.get("name", "Unknown")
            or "Unknown"
        )
    )

    final_score = int(
        token.get("final_score", 0) or 0
    )

    ai_score = int(
        token.get("ai_score", 0) or 0
    )

    gem_score = int(
        token.get("gem_score", 0) or 0
    )

    security_score = int(
        token.get("security_score", 0) or 0
    )

    buy_ratio = float(
        token.get("buy_ratio", 0) or 0
    )

    total_txns = int(
        token.get("total_txns", 0) or 0
    )

    price_change = float(
        token.get("price_change_24h", 0) or 0
    )

    signal = str(
        token.get(
            "final_signal",
            "⛔ NO SIGNAL"
        )
        or "⛔ NO SIGNAL"
    )

    reasons = token.get(
        "final_reasons",
        []
    ) or []

    emoji = signal_emoji(signal)

    # =====================================================
    # MARKET DATA
    # =====================================================

    marketcap = money(
        token.get("marketcap", 0)
    )

    liquidity = money(
        token.get("liquidity", 0)
    )

    volume = money(
        token.get("volume24h", 0)
    )

    # =====================================================
    # SIGNAL LABEL
    # =====================================================

    signal_upper = signal.upper()

    if "STRONG GEM" in signal_upper:
        signal_label = "STRONG GEM"

    elif "GEM SIGNAL" in signal_upper:
        signal_label = "GEM SIGNAL"

    elif "EARLY GEM" in signal_upper:
        signal_label = "EARLY GEM"

    elif "WATCH" in signal_upper:
        signal_label = "WATCH"

    else:
        signal_label = signal

    signal_label = escape(signal_label)

    # =====================================================
    # ADDRESS
    # =====================================================

    address = str(
        token.get(
            "address",
            ""
        )
        or ""
    ).strip()

    # =====================================================
    # SOCIAL LINKS
    # =====================================================

    (
        twitter_url,
        telegram_url,
        website_url,
    ) = extract_social_links(token)

    social_links = []

    if twitter_url:
        social_links.append(
            f'<a href="{twitter_url}">𝕏</a>'
        )

    if telegram_url:
        social_links.append(
            f'<a href="{telegram_url}">TG</a>'
        )

    if website_url:
        social_links.append(
            f'<a href="{website_url}">WEB</a>'
        )

    # =====================================================
    # TOKEN TOOLS
    # =====================================================

    dex_url = safe_url(
        token.get("url", "")
    )

    solscan_url = ""

    if address:
        solscan_url = (
            "https://solscan.io/token/"
            + quote(address, safe="")
        )

    solscan_url = safe_url(solscan_url)

    gecko_url = ""

    if address:
        gecko_url = (
            "https://www.geckoterminal.com/"
            "solana/tokens/"
            + quote(address, safe="")
        )

    gecko_url = safe_url(gecko_url)

    gmgn_url = ""

    if address:
        gmgn_url = (
            "https://gmgn.ai/sol/token/"
            + quote(address, safe="")
        )

    gmgn_url = safe_url(gmgn_url)

    tool_links = []

    if dex_url:
        tool_links.append(
            f'<a href="{dex_url}">DS</a>'
        )

    if solscan_url:
        tool_links.append(
            f'<a href="{solscan_url}">SCAN</a>'
        )

    if gecko_url:
        tool_links.append(
            f'<a href="{gecko_url}">GT</a>'
        )

    if gmgn_url:
        tool_links.append(
            f'<a href="{gmgn_url}">GMGN</a>'
        )

    # =====================================================
    # COMPACT MESSAGE
    # =====================================================

    lines = [
        f"🪙 <b>${symbol} — {name}</b>",
        "└ 🟣 Solana",
        "",
        "<b>📊 Stats</b>",
        f"├ MC   <b>{marketcap}</b>",
        f"├ LP   <b>{liquidity}</b>",
        f"├ Vol  <b>{volume}</b>",
        f"├ TXNS <b>{total_txns:,}</b>",
        f"└ BUY  <b>{buy_ratio * 100:.1f}%</b> • "
        f"<b>{price_change:+.2f}%</b>",
        "",
        f"🧠 AI <b>{ai_score}</b> • "
        f"💎 GEM <b>{gem_score}</b> • "
        f"🔐 SEC <b>{security_score}</b> • "
        f"🎯 FINAL <b>{final_score}</b>",
        "",
        f"{emoji} <b>{signal_label}</b> • "
        f"Score <b>{final_score}/100</b>",
    ]

    # =====================================================
    # FINAL REASONS
    # =====================================================

    clean_reasons = []

    for reason in reasons[:5]:

        reason_text = str(
            reason or ""
        ).strip()

        if reason_text:
            clean_reasons.append(
                escape(reason_text)
            )

    if clean_reasons:

        lines.extend(
            [
                "",
                "📋 <b>Signal:</b> "
                + " • ".join(clean_reasons),
            ]
        )

    # =====================================================
    # SOCIALS
    # =====================================================

    if social_links:

        lines.extend(
            [
                "",
                "🔗 " + " • ".join(social_links),
            ]
        )

    # =====================================================
    # TOKEN TOOLS
    # =====================================================

    if tool_links:

        lines.append(
            "🔎 " + " • ".join(tool_links)
        )

    # =====================================================
    # CONTRACT
    # =====================================================

    if address:

        safe_address = escape(address)

        lines.extend(
            [
                "",
                f"📄 <code>{safe_address}</code>",
                "",
                "⚠️ <i>Wannan signal ba guarantee bane.</i>",
                "<i>DYOR kafin kowane trade.</i>",
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
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

        except Exception as exc:

            print(
                "Telegram signal error:",
                repr(exc)
            )
