#!/usr/bin/env python3
"""
Standalone maintenance page for EZScore.

Usage:
    python maintenance.py
    python maintenance.py --host 127.0.0.1 --port 8501
    python maintenance.py --title "EZScore" --message "Maintenance en cours"
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html import escape


HTML_TEMPLATE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Maintenance</title>
<style>
    :root {{
        color-scheme: dark;
        --bg: #0b1020;
        --panel: #11182b;
        --text: #f4f7fb;
        --muted: #aab4c8;
        --accent: #4da3ff;
        --border: rgba(255,255,255,.10);
    }}
    * {{
        box-sizing: border-box;
    }}
    html, body {{
        height: 100%;
        margin: 0;
    }}
    body {{
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
                     "Segoe UI", sans-serif;
        background:
            radial-gradient(circle at 20% 20%, rgba(77,163,255,.16), transparent 34rem),
            radial-gradient(circle at 80% 80%, rgba(111,76,255,.12), transparent 34rem),
            var(--bg);
        color: var(--text);
        display: grid;
        place-items: center;
        padding: 2rem;
    }}
    .card {{
        width: min(760px, 100%);
        background: rgba(17,24,43,.88);
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 3rem;
        box-shadow: 0 24px 80px rgba(0,0,0,.35);
        backdrop-filter: blur(14px);
    }}
    .brand {{
        display: flex;
        align-items: center;
        gap: .9rem;
        margin-bottom: 2rem;
    }}
    .logo {{
        width: 54px;
        height: 54px;
        border-radius: 16px;
        display: grid;
        place-items: center;
        font-size: 1.8rem;
        background: rgba(77,163,255,.14);
        border: 1px solid rgba(77,163,255,.35);
    }}
    .brand h1 {{
        margin: 0;
        font-size: clamp(1.8rem, 4vw, 2.6rem);
        line-height: 1;
    }}
    .status {{
        display: inline-flex;
        align-items: center;
        gap: .6rem;
        color: var(--accent);
        font-weight: 700;
        margin-bottom: 1rem;
    }}
    .dot {{
        width: .65rem;
        height: .65rem;
        border-radius: 999px;
        background: var(--accent);
        box-shadow: 0 0 0 .35rem rgba(77,163,255,.12);
    }}
    h2 {{
        margin: 0 0 1rem 0;
        font-size: clamp(1.5rem, 3vw, 2.2rem);
    }}
    p {{
        color: var(--muted);
        line-height: 1.7;
        font-size: 1.05rem;
        margin: 0;
    }}
    .footer {{
        margin-top: 2.2rem;
        padding-top: 1.4rem;
        border-top: 1px solid var(--border);
        color: #7f8aa1;
        font-size: .9rem;
    }}
</style>
</head>
<body>
    <main class="card">
        <div class="brand">
            <div class="logo">🎸</div>
            <h1>{title}</h1>
        </div>

        <div class="status">
            <span class="dot"></span>
            Maintenance
        </div>

        <h2>Le service est temporairement indisponible.</h2>
        <p>{message}</p>

        <div class="footer">
            Merci de réessayer dans quelques instants.
        </div>
    </main>
</body>
</html>
"""


def build_page(title: str, message: str) -> bytes:
    return HTML_TEMPLATE.format(
        title=escape(title),
        message=escape(message),
    ).encode("utf-8")


class MaintenanceHandler(BaseHTTPRequestHandler):
    page: bytes = b""

    def do_GET(self) -> None:
        if self.path == "/health":
            body = b"maintenance"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(503)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(self.page)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Retry-After", "300")
        self.end_headers()
        self.wfile.write(self.page)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[maintenance] {self.address_string()} - {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serveur HTTP autonome de page de maintenance EZScore."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--title", default="EZScore")
    parser.add_argument(
        "--message",
        default="Une opération de maintenance est en cours. Le service reviendra bientôt.",
    )
    args = parser.parse_args()

    MaintenanceHandler.page = build_page(args.title, args.message)

    server = ThreadingHTTPServer((args.host, args.port), MaintenanceHandler)

    print(f"Maintenance page: http://{args.host}:{args.port}")
    print("Ctrl+C pour arrêter.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur de maintenance.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
