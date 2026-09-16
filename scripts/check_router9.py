"""Smoke-test the local Router9 OpenAI-compatible endpoint."""
import os
import sys
import requests

base = os.getenv("VOID_ROUTER_BASE_URL", "http://127.0.0.1:20127/v1").rstrip("/")
key = os.getenv("VOID_ROUTER_API_KEY", "")
headers = {"Content-Type": "application/json"}
if key:
    headers["Authorization"] = f"Bearer {key}"

r = requests.get(f"{base}/models", headers=headers, timeout=(5, 15))
r.raise_for_status()
data = r.json()
models = data.get("data", []) if isinstance(data, dict) else data
ids = [m.get("id") for m in models if isinstance(m, dict)]
print(f"ROUTER9 OK: {len(ids)} models discovered")

model = "openrouter/openrouter/free"
if model not in ids:
    raise SystemExit(f"DEFAULT MODEL NOT EXPOSED: {model}")

r = requests.post(
    f"{base}/chat/completions",
    headers=headers,
    json={
        "model": model,
        "messages": [{"role": "user", "content": "Reply with exactly: VOID ROUTER TEST OK"}],
        "max_tokens": 200,
        "stream": False,
    },
    timeout=(15, 180),
)
r.raise_for_status()
answer = r.json()["choices"][0]["message"]["content"]
print("CHAT OK:", answer.strip())
