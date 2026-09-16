#!/usr/bin/env python3
"""Small same-container reverse proxy for the Render deployment.

Public Render traffic enters PORT. VOID's API stays on 8787 and Telegram's
webhook server stays on 10001. Only this proxy is exposed publicly.
"""
from __future__ import annotations

import os
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PUBLIC_PORT = int(os.getenv("PORT", "10000"))
VOID_HOST = os.getenv("VOID_API_HOST", "127.0.0.1")
VOID_PORT = int(os.getenv("VOID_API_PORT", "8787"))
TELEGRAM_PORT = int(os.getenv("TELEGRAM_WEBHOOK_PORT", "10001"))
TELEGRAM_PATH = os.getenv("TELEGRAM_WEBHOOK_PATH", "/telegram").rstrip("/") or "/telegram"

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade",
}


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def _target(self):
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path == TELEGRAM_PATH:
            return TELEGRAM_PORT
        return VOID_PORT

    def _forward(self):
        target_port = self._target()
        body = b""
        if self.command in {"POST", "PUT", "PATCH", "DELETE"}:
            length = int(self.headers.get("Content-Length", "0"))
            if length:
                body = self.rfile.read(length)

        headers = {}
        for key, value in self.headers.items():
            if key.lower() in HOP_BY_HOP or key.lower() == "host":
                continue
            headers[key] = value
        headers["Host"] = f"{VOID_HOST}:{target_port}"
        headers["X-Forwarded-Proto"] = "https"
        headers["X-Forwarded-Host"] = self.headers.get("Host", "")

        conn = HTTPConnection(VOID_HOST, target_port, timeout=180)
        try:
            conn.request(self.command, self.path, body=body or None, headers=headers)
            response = conn.getresponse()
            payload = response.read()
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() in HOP_BY_HOP or key.lower() == "content-length":
                    continue
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if payload:
                self.wfile.write(payload)
        except Exception as exc:
            self.send_response(502)
            raw = f"proxy error: {type(exc).__name__}: {exc}".encode()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        finally:
            conn.close()

    def do_GET(self):
        self._forward()

    def do_POST(self):
        self._forward()

    def do_PUT(self):
        self._forward()

    def do_PATCH(self):
        self._forward()

    def do_DELETE(self):
        self._forward()

    def do_OPTIONS(self):
        self._forward()


if __name__ == "__main__":
    print(f"VOID Render proxy | 0.0.0.0:{PUBLIC_PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PUBLIC_PORT), ProxyHandler).serve_forever()
