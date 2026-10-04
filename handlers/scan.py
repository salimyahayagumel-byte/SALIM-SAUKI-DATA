from html import escape
from urllib.parse import quote

from telegram import Update
from telegram.ext import ContextTypes

from services.scanner import TokenScanner
from services.auto_signal import AutoSignalEngine


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

    lower = value.lower()

    # Do not expose arbitrary X/Twitter posts as a project's social
    # profile. DexScreener metadata can occasionally contain a post URL.
    if "x.com/" in lower or "twitter.com/" in lower:
        path = lower.split("//", 1)[-1].split("/", 1)
        path = path[1] if len(path) > 1 else ""
        parts = [part for part in path.split("/") if part]
        if not parts or parts[0] in {"status", "i", "intent", "share"}:
            return ""
        if len(parts) >= 2 and parts[1] == "status":
            return ""

    # Invite/hash-only Telegram links are not reliable public project links.
    if "t.me/" in lower:
        host_part = lower.split("t.me/", 1)[-1].split("?", 1)[0].strip("/")
        if not host_part or host_part.startswith("+"):
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
    """Use the same V7.3 professional GEM card as the auto-signal engine."""
    return AutoSignalEngine.format_signal(token)


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

            message = format_signal(token)

            image_url = str(
                token.get(
                    "image_url",
                    "",
                )
                or ""
            ).strip()

            # -------------------------------------------------
            # TOKEN IMAGE + SIGNAL
            # -------------------------------------------------
            # Use the DexScreener token image when the scanner
            # already supplied a valid HTTP/HTTPS image URL.
            # If no image is available, keep the normal text
            # signal so the scan result is never lost.
            if image_url.startswith(
                ("http://", "https://")
            ):

                try:

                    await update.message.reply_photo(
                        photo=image_url,
                        caption=message,
                        parse_mode="HTML",
                    )

                except Exception as image_exc:

                    print(
                        "Telegram image error:",
                        repr(image_exc)
                    )

                    await update.message.reply_text(
                        message,
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )

            else:

                await update.message.reply_text(
                    message,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )

        except Exception as exc:

            print(
                "Telegram signal error:",
                repr(exc)
            )
