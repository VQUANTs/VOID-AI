#!/usr/bin/env python3
"""Boot VOID-AI + 9Router + Telegram webhook in one Render Web Service."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROUTER_PORT = int(os.getenv("ROUTER9_PORT", "20128"))
VOID_PORT = int(os.getenv("VOID_API_PORT", "8787"))
TELEGRAM_PORT = int(os.getenv("TELEGRAM_WEBHOOK_PORT", "10001"))
PUBLIC_PORT = int(os.getenv("PORT", "10000"))
ROUTER = f"http://127.0.0.1:{ROUTER_PORT}"
VOID = f"http://127.0.0.1:{VOID_PORT}"

processes: list[subprocess.Popen] = []


def request(url: str, method="GET", payload=None, headers=None, timeout=20):
    data = None
    hdrs = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload).encode()
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
        return response.status, dict(response.headers), json.loads(raw.decode() or "{}")


def wait_http(url, timeout=120):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            status, _, payload = request(url, timeout=5)
            if 200 <= status < 500:
                return payload
        except Exception as exc:
            last = exc
        time.sleep(2)
    raise RuntimeError(f"Timed out waiting for {url}: {last}")


def start(cmd, env=None, name="process"):
    merged = os.environ.copy()
    if env:
        merged.update(env)
    print(f"[render] starting {name}: {' '.join(cmd)}", flush=True)
    proc = subprocess.Popen(cmd, env=merged)
    processes.append(proc)
    return proc


def router_session():
    password = os.getenv("INITIAL_PASSWORD", "")
    if not password:
        raise RuntimeError("INITIAL_PASSWORD is required for Render 9Router bootstrap")
    req = urllib.request.Request(
        ROUTER + "/api/auth/login",
        data=json.dumps({"password": password}).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        cookie = response.headers.get("Set-Cookie", "").split(";", 1)[0]
        if not cookie:
            raise RuntimeError("9Router login returned no session cookie")
        return cookie


def ensure_openrouter():
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for the Render 9Router bootstrap")

    cookie = router_session()
    headers = {"Cookie": cookie}
    _, _, listing = request(ROUTER + "/api/providers", headers=headers)
    connections = listing.get("connections", [])
    existing = next(
        (c for c in connections if str(c.get("provider", "")).lower() == "openrouter"),
        None,
    )

    payload = {
        "provider": "openrouter",
        "name": "VOID-AI-OPENROUTERKEY",
        "apiKey": api_key,
        "priority": 1,
        "testStatus": "unknown",
    }

    if existing and existing.get("id"):
        status, _, result = request(
            ROUTER + f"/api/providers/{existing['id']}",
            method="PUT",
            payload=payload,
            headers=headers,
        )
        print(f"[render] 9Router OpenRouter connection refreshed: HTTP {status}", flush=True)
        return result

    status, _, result = request(
        ROUTER + "/api/providers",
        method="POST",
        payload=payload,
        headers=headers,
    )
    if status not in (200, 201):
        raise RuntimeError(f"9Router provider creation failed: HTTP {status} {result}")
    print("[render] 9Router OpenRouter connection created", flush=True)
    return result


def set_telegram_webhook():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required for Render webhook mode")
    public_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    if not public_url:
        raise RuntimeError("RENDER_EXTERNAL_URL is not available")
    path = os.getenv("TELEGRAM_WEBHOOK_PATH", "/telegram")
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    payload = {"url": public_url + path}
    if secret:
        payload["secret_token"] = secret
    url = f"https://api.telegram.org/bot{token}/setWebhook"
    status, _, result = request(url, method="POST", payload=payload, timeout=30)
    if status != 200 or not result.get("ok"):
        raise RuntimeError(f"Telegram setWebhook failed: {result}")
    print(f"[render] Telegram webhook set to {public_url}{path}", flush=True)


def shutdown(signum, _frame):
    print(f"[render] signal {signum}; stopping stack", flush=True)
    for proc in reversed(processes):
        if proc.poll() is None:
            proc.terminate()
    deadline = time.time() + 10
    for proc in reversed(processes):
        if proc.poll() is None:
            remaining = max(0.1, deadline - time.time())
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                proc.kill()
    raise SystemExit(0)


def main():
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    router_data = os.getenv("ROUTER9_DATA_DIR", "/tmp/9router")
    Path(router_data).mkdir(parents=True, exist_ok=True)

    start(
        ["9router", "--no-browser", "--skip-update"],
        env={
            "PORT": str(ROUTER_PORT),
            "HOSTNAME": "127.0.0.1",
            "DATA_DIR": router_data,
            "BASE_URL": ROUTER,
            "NEXT_PUBLIC_BASE_URL": ROUTER,
            "AUTH_COOKIE_SECURE": "false",
            "INITIAL_PASSWORD": os.environ["INITIAL_PASSWORD"],
            "JWT_SECRET": os.environ["JWT_SECRET"],
            "API_KEY_SECRET": os.environ["API_KEY_SECRET"],
            "MACHINE_ID_SALT": os.environ["MACHINE_ID_SALT"],
            "REQUIRE_API_KEY": "false",
        },
        name="9Router",
    )

    # 9Router exposes its health endpoint under /api/health.
    # /health is not a Router9 endpoint and returns 404, which previously
    # caused the Render bootstrap to wait until it timed out.
    wait_http(ROUTER + "/api/health", timeout=150)
    ensure_openrouter()

    start(
        [sys.executable, "server.py"],
        env={
            "VOID_API_HOST": "127.0.0.1",
            "VOID_API_PORT": str(VOID_PORT),
        },
        name="VOID API",
    )
    wait_http(VOID + "/health", timeout=90)

    start(
        [sys.executable, "-m", "void.telegram_bot"],
        env={
            "TELEGRAM_MODE": "webhook",
            "PORT": str(TELEGRAM_PORT),
        },
        name="Telegram webhook",
    )
    wait_http(f"http://127.0.0.1:{TELEGRAM_PORT}/health", timeout=90)

    # Start the public Render listener before registering the Telegram webhook.
    # Telegram validates the webhook URL when setWebhook is called, so the
    # public endpoint must already be reachable at that point.
    proxy = start([sys.executable, "scripts/render_proxy.py"], name="Render proxy")
    wait_http(f"http://127.0.0.1:{PUBLIC_PORT}/health", timeout=30)

    set_telegram_webhook()
    print(f"[render] VOID-AI stack ready on public port {PUBLIC_PORT}", flush=True)

    while True:
        for proc in processes:
            code = proc.poll()
            if code is not None:
                raise RuntimeError(f"A required process exited with code {code}")
        time.sleep(2)


if __name__ == "__main__":
    main()
