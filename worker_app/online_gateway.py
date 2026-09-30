#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.client
import json
import socketserver
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

HOP_BY_HOP = {
    "connection", "proxy-connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade",
}
INTERNAL_PREFIXES = (
    "/internal/analysis/desktop",
    "/internal/analysis/worker",
)


def load_config(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class GatewayHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "EZScoreOnlineGateway/1.0"

    @property
    def config_path(self) -> Path:
        return self.server.config_path  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args) -> None:
        super().log_message(fmt, *args)

    def _maintenance(self, detail: str = "") -> None:
        html = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="20">
<title>EZScore — Maintenance</title>
<style>body{margin:0;background:#101820;color:#eef5f7;font:16px Segoe UI,Arial,sans-serif}.wrap{max-width:760px;margin:12vh auto;padding:32px}.card{background:#18242d;border:1px solid #30434f;border-radius:16px;padding:28px;box-shadow:0 20px 60px #0005}h1{margin:0 0 10px;font-size:34px}p{color:#b9c8d1;line-height:1.6}.dot{display:inline-block;width:10px;height:10px;border-radius:50%;background:#f0ad4e;margin-right:10px}.small{font-size:13px;color:#81939e}</style>
</head><body><div class="wrap"><div class="card"><h1>EZScore</h1><p><span class="dot"></span><strong>Maintenance en cours</strong></p><p>Le service sera de nouveau disponible dans quelques instants.</p><p class="small">Cette page se recharge automatiquement.</p></div></div></body></html>"""
        body = html.encode("utf-8")
        self.send_response(503)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Retry-After", "20")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _proxy(self) -> None:
        if self.path == "/__ezscore_gateway_status":
            cfg = load_config(self.config_path)
            body = json.dumps({
                "ok": True,
                "protocol": "ezscore.online-gateway.v3",
                "maintenance": bool(cfg.get("maintenance", False)),
                "backend_host": str(cfg.get("backend_host") or "127.0.0.1"),
                "backend_port": int(cfg.get("backend_port") or 8511),
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
            return
        if self.path == "/__ezscore_gateway_health":
            payload = b"OK"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)
            return
        cfg = load_config(self.config_path)
        maintenance = bool(cfg.get("maintenance", False))
        is_internal = self.path.startswith(INTERNAL_PREFIXES)
        if maintenance and not is_internal:
            self._maintenance("maintenance")
            return

        host = str(cfg.get("backend_host") or "127.0.0.1")
        port = int(cfg.get("backend_port") or 8511)
        body = None
        length = self.headers.get("Content-Length")
        if length:
            try:
                body = self.rfile.read(int(length))
            except Exception:
                body = b""

        headers = {}
        for key, value in self.headers.items():
            if key.lower() in HOP_BY_HOP:
                continue
            headers[key] = value
        headers["X-Forwarded-Proto"] = self.headers.get("X-Forwarded-Proto", "https")
        headers["X-Forwarded-Host"] = self.headers.get("Host", "")
        client_ip = self.client_address[0] if self.client_address else ""
        prior = self.headers.get("X-Forwarded-For")
        headers["X-Forwarded-For"] = f"{prior}, {client_ip}" if prior else client_ip

        conn = http.client.HTTPConnection(host, port, timeout=60)
        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            response = conn.getresponse()
        except Exception:
            conn.close()
            if is_internal:
                payload = b'{"error":"online_backend_unavailable"}'
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Retry-After", "2")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(payload)
            else:
                self._maintenance("backend unavailable")
            return

        self.send_response(response.status, response.reason)
        saw_length = False
        for key, value in response.getheaders():
            lk = key.lower()
            if lk in HOP_BY_HOP:
                continue
            if lk == "content-length":
                saw_length = True
            self.send_header(key, value)
        if not saw_length:
            self.send_header("Connection", "close")
            self.close_connection = True
        self.end_headers()
        if self.command != "HEAD":
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        conn.close()

    do_GET = _proxy
    do_POST = _proxy
    do_PUT = _proxy
    do_PATCH = _proxy
    do_DELETE = _proxy
    do_OPTIONS = _proxy
    do_HEAD = _proxy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    config_path = root / "var" / "runtime" / "online-gateway.json"
    server = ThreadingHTTPServer((args.host, args.port), GatewayHandler)
    server.daemon_threads = True
    server.config_path = config_path  # type: ignore[attr-defined]
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
