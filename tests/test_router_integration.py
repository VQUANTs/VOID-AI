import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from void.config import Config
from void.router import ModelRouter


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/v1/models":
            body = json.dumps({
                "data": [
                    {"id": "openrouter/openrouter/free", "capabilities": ["text"]},
                    {"id": "backup-model", "capabilities": ["text", "coding"]},
                ]
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        body = json.dumps({
            "choices": [{
                "message": {"role": "assistant", "content": "VOID ROUTER TEST OK"},
                "finish_reason": "stop",
            }],
            "model": payload["model"],
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def test_router9_is_single_gateway_and_default_is_selected(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    old_url = Config.ROUTER_BASE_URL
    old_default = Config.DEFAULT_MODEL
    old_openrouter = Config.OPENROUTER_BASE_URL
    old_gemini = Config.GEMINI_API_KEY
    old_groq = Config.GROQ_API_KEY
    try:
        Config.ROUTER_BASE_URL = f"http://127.0.0.1:{server.server_port}/v1"
        Config.DEFAULT_MODEL = "openrouter/openrouter/free"
        Config.OPENROUTER_BASE_URL = ""
        Config.GEMINI_API_KEY = ""
        Config.GROQ_API_KEY = ""

        router = ModelRouter()
        assert list(router.registry.providers) == ["router9"]
        models = router.refresh(force=True)
        assert any(m.id == Config.DEFAULT_MODEL for m in models)

        selected = router.choose("hello")
        assert selected.id == Config.DEFAULT_MODEL
        assert selected.provider == "router9"

        response = router.chat([
            {"role": "user", "content": "hello"}
        ])
        assert response.json()["choices"][0]["message"]["content"] == "VOID ROUTER TEST OK"
    finally:
        Config.ROUTER_BASE_URL = old_url
        Config.DEFAULT_MODEL = old_default
        Config.OPENROUTER_BASE_URL = old_openrouter
        Config.GEMINI_API_KEY = old_gemini
        Config.GROQ_API_KEY = old_groq
        server.shutdown()
        thread.join(timeout=2)
