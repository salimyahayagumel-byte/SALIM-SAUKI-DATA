import asyncio
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# =========================================================
# PROJECT ROOT
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Make project-root packages such as "services" importable
# when dashboard.py is started directly with:
# python web/dashboard.py
import sys

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.scanner import TokenScanner


# =========================================================
# SALIM SAUKI DATA
# WEB DASHBOARD SERVER
# NO FASTAPI
# NO UVICORN
# NO PYDANTIC
# =========================================================

HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
PORT = int(os.getenv("DASHBOARD_PORT", "8000"))

TEMPLATE_FILE = BASE_DIR / "templates" / "dashboard.html"
STATIC_DIR = BASE_DIR / "static"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("salim-dashboard")


# =========================================================
# GLOBAL SCANNER
# =========================================================

scanner = TokenScanner()

# Prevent multiple scans from running at the same time.
scan_lock = threading.Lock()


# =========================================================
# JSON HELPERS
# =========================================================

def clean_value(value):
    """
    Convert values into JSON-safe values.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(key): clean_value(val)
            for key, val in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            clean_value(item)
            for item in value
        ]

    try:
        return str(value)
    except Exception:
        return None


def json_response(handler, data, status=200):
    """
    Send JSON response.
    """

    payload = json.dumps(
        clean_value(data),
        ensure_ascii=False,
    ).encode("utf-8")

    handler.send_response(status)

    handler.send_header(
        "Content-Type",
        "application/json; charset=utf-8",
    )

    handler.send_header(
        "Content-Length",
        str(len(payload)),
    )

    handler.send_header(
        "Cache-Control",
        "no-cache, no-store, must-revalidate",
    )

    handler.send_header(
        "Pragma",
        "no-cache",
    )

    handler.end_headers()

    try:
        handler.wfile.write(payload)
    except (BrokenPipeError, ConnectionResetError):
        pass


# =========================================================
# ASYNC SCAN
# =========================================================

def run_scan(query="sol"):
    """
    Run TokenScanner.scan() from normal HTTP thread.
    """

    async def execute():
        return await scanner.scan(query=query)

    return asyncio.run(execute())


# =========================================================
# SCAN WORKER
# =========================================================

def perform_scan(query="sol"):
    """
    Execute scanner safely.

    Only one scan is allowed at a time.
    """

    acquired = scan_lock.acquire(
        blocking=True,
        timeout=180,
    )

    if not acquired:
        return {
            "success": False,
            "error": "A scan is already running.",
            "tokens": [],
        }

    try:
        logger.info(
            "🔎 Dashboard scan started: %s",
            query,
        )

        tokens = run_scan(query=query)

        if tokens is None:
            tokens = []

        logger.info(
            "✅ Dashboard scan finished: %s tokens",
            len(tokens),
        )

        return {
            "success": True,
            "count": len(tokens),
            "tokens": clean_value(tokens),
        }

    except Exception as exc:
        logger.exception(
            "❌ Dashboard scan failed"
        )

        return {
            "success": False,
            "error": str(exc),
            "tokens": [],
        }

    finally:
        scan_lock.release()


# =========================================================
# HTML
# =========================================================

def load_dashboard():
    """
    Load dashboard HTML.
    """

    if not TEMPLATE_FILE.exists():
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SALIM SAUKI DATA</title>
</head>
<body>
    <h1>SALIM SAUKI DATA</h1>
    <p>dashboard.html not found.</p>
</body>
</html>
"""

    try:
        return TEMPLATE_FILE.read_text(
            encoding="utf-8"
        )

    except Exception as exc:
        logger.exception(
            "❌ Failed to load dashboard.html"
        )

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SALIM SAUKI DATA</title>
</head>
<body>
    <h1>SALIM SAUKI DATA</h1>
    <p>Dashboard loading error: {str(exc)}</p>
</body>
</html>
"""


# =========================================================
# STATIC FILE
# =========================================================

def content_type(path):
    """
    Return HTTP content type.
    """

    suffix = path.suffix.lower()

    mapping = {
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
    }

    return mapping.get(
        suffix,
        "application/octet-stream",
    )


# =========================================================
# DASHBOARD HTTP HANDLER
# =========================================================

class DashboardHandler(BaseHTTPRequestHandler):

    server_version = "SALIM-SAUKI-DATA/1.0"

    # -----------------------------------------------------
    # LOGGING
    # -----------------------------------------------------

    def log_message(self, format_string, *args):
        logger.info(
            "%s - %s",
            self.address_string(),
            format_string % args,
        )

    # -----------------------------------------------------
    # HEAD
    # -----------------------------------------------------

    def do_HEAD(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            if not TEMPLATE_FILE.exists():
                self.send_error(
                    404,
                    "Dashboard not found",
                )
                return

            try:
                payload = TEMPLATE_FILE.read_bytes()

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    "text/html; charset=utf-8",
                )

                self.send_header(
                    "Content-Length",
                    str(len(payload)),
                )

                self.end_headers()

            except Exception:
                self.send_error(
                    500,
                    "Dashboard error",
                )

            return

        if path.startswith("/static/"):
            relative = path[len("/static/"):]

            requested = (
                STATIC_DIR / relative
            ).resolve()

            try:
                requested.relative_to(
                    STATIC_DIR.resolve()
                )

            except ValueError:
                self.send_error(
                    403,
                    "Forbidden",
                )
                return

            if not requested.exists():
                self.send_error(
                    404,
                    "Static file not found",
                )
                return

            if not requested.is_file():
                self.send_error(
                    400,
                    "Invalid static file",
                )
                return

            try:
                payload = requested.read_bytes()

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    content_type(requested),
                )

                self.send_header(
                    "Content-Length",
                    str(len(payload)),
                )

                self.end_headers()

            except Exception:
                self.send_error(
                    500,
                    "Static file error",
                )

            return

        if path == "/api/health":
            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8",
            )

            self.end_headers()

            return

        self.send_error(
            404,
            "Not found",
        )

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Dashboard
        if path == "/":
            self.send_dashboard()
            return

        # Health check
        if path == "/api/health":
            json_response(
                self,
                {
                    "success": True,
                    "status": "online",
                    "bot": "SALIM SAUKI DATA",
                    "scanner": "online",
                },
            )
            return

        # Scanner API
        if path == "/api/scan":
            self.handle_scan(
                parsed.query
            )
            return

        # Static files
        if path.startswith("/static/"):
            self.send_static(path)
            return

        # Not found
        json_response(
            self,
            {
                "success": False,
                "error": "Not found",
            },
            status=404,
        )

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/scan":
            self.handle_scan(
                parsed.query
            )
            return

        json_response(
            self,
            {
                "success": False,
                "error": "Not found",
            },
            status=404,
        )

    # =====================================================
    # SEND DASHBOARD
    # =====================================================

    def send_dashboard(self):
        try:
            html = load_dashboard()

            payload = html.encode(
                "utf-8"
            )

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8",
            )

            self.send_header(
                "Content-Length",
                str(len(payload)),
            )

            self.send_header(
                "Cache-Control",
                "no-cache",
            )

            self.end_headers()

            self.wfile.write(payload)

        except (
            BrokenPipeError,
            ConnectionResetError,
        ):
            pass

        except Exception as exc:
            logger.exception(
                "❌ Dashboard HTML error"
            )

            json_response(
                self,
                {
                    "success": False,
                    "error": str(exc),
                },
                status=500,
            )

    # =====================================================
    # SEND STATIC
    # =====================================================

    def send_static(self, request_path):
        relative = request_path[
            len("/static/"):
        :]

        requested = (
            STATIC_DIR / relative
        ).resolve()

        # Security:
        # Prevent ../ path traversal.
        try:
            requested.relative_to(
                STATIC_DIR.resolve()
            )

        except ValueError:
            json_response(
                self,
                {
                    "success": False,
                    "error": "Forbidden",
                },
                status=403,
            )
            return

        if not requested.exists():
            json_response(
                self,
                {
                    "success": False,
                    "error": "Static file not found",
                },
                status=404,
            )
            return

        if not requested.is_file():
            json_response(
                self,
                {
                    "success": False,
                    "error": "Invalid static file",
                },
                status=400,
            )
            return

        try:
            payload = requested.read_bytes()

            self.send_response(200)

            self.send_header(
                "Content-Type",
                content_type(requested),
            )

            self.send_header(
                "Content-Length",
                str(len(payload)),
            )

            self.send_header(
                "Cache-Control",
                "no-cache",
            )

            self.end_headers()

            self.wfile.write(payload)

        except (
            BrokenPipeError,
            ConnectionResetError,
        ):
            pass

        except Exception as exc:
            logger.exception(
                "❌ Static file error"
            )

            json_response(
                self,
                {
                    "success": False,
                    "error": str(exc),
                },
                status=500,
            )

    # =====================================================
    # HANDLE SCAN
    # =====================================================

    def handle_scan(self, query_string):
        params = parse_qs(
            query_string
        )

        query = (
            params.get(
                "q",
                ["sol"],
            )[0]
            or "sol"
        ).strip()

        if not query:
            query = "sol"

        logger.info(
            "📡 API scan request: %s",
            query,
        )

        result = perform_scan(
            query=query
        )

        # -------------------------------------------------
        # IMPORTANT
        #
        # dashboard.js expects the successful
        # /api/scan response to be an ARRAY.
        #
        # Therefore return:
        #
        # [
        #     {...},
        #     {...}
        # ]
        #
        # instead of:
        #
        # {
        #     "success": true,
        #     "tokens": [...]
        # }
        # -------------------------------------------------

        if result.get(
            "success",
            False,
        ):
            tokens = result.get(
                "tokens",
                [],
            )

            if not isinstance(
                tokens,
                list,
            ):
                tokens = []

            json_response(
                self,
                tokens,
                status=200,
            )

            return

        error = result.get(
            "error",
            "Scan failed.",
        )

        status = 500

        if (
            error
            == "A scan is already running."
        ):
            status = 409

        json_response(
            self,
            {
                "success": False,
                "error": error,
                "tokens": [],
            },
            status=status,
        )


# =========================================================
# SERVER
# =========================================================

def create_server():
    return ThreadingHTTPServer(
        (HOST, PORT),
        DashboardHandler,
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "========================================"
    )

    print(
        "🧠 SALIM SAUKI DATA"
    )

    print(
        "💎 AI SOLANA GEM SCANNER"
    )

    print(
        "========================================"
    )

    print(
        "🌐 Dashboard:"
    )

    print(
        f"http://127.0.0.1:{PORT}"
    )

    print(
        "========================================"
    )

    print(
        "📡 API:"
    )

    print(
        f"http://127.0.0.1:{PORT}/api/scan"
    )

    print(
        "========================================"
    )

    server = create_server()

    try:

        logger.info(
            "🚀 Dashboard server started on %s:%s",
            HOST,
            PORT,
        )

        server.serve_forever()

    except KeyboardInterrupt:

        print(
            "\n🛑 Dashboard stopped."
        )

    finally:

        server.server_close()

        print(
            "✅ Dashboard server closed."
        )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    main()
