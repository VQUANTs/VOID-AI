import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from void.providers import OpenAICompatibleProvider


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/v1/models":
            body = json.dumps({"data": [{"id": "demo-coder", "capabilities": ["text", "coding"]}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


def test_openai_compatible_model_discovery():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        provider = OpenAICompatibleProvider("test", f"http://127.0.0.1:{server.server_port}/v1")
        models = provider.list_models()
        assert models[0].id == "demo-coder"
        assert "coding" in models[0].capabilities
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_provider_retries_router9_input_compatibility_error():
    import json
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from threading import Thread

    class Handler(BaseHTTPRequestHandler):
        calls = []

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length))
            self.__class__.calls.append(body)
            if len(self.__class__.calls) == 1:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": {"message": 'Input required: specify "prompt" or "messages"'}}).encode())
                return
            assert body.get("prompt")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"choices": [{"message": {"role": "assistant", "content": "ok"}}]}).encode())

        def log_message(self, *_args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        provider = OpenAICompatibleProvider("router9", f"http://127.0.0.1:{server.server_port}/v1")
        response = provider.chat(
            [{"role": "user", "content": "hello"}],
            model="openrouter/openrouter/free",
            max_tokens=20,
        )
        assert response.status_code == 200
        assert len(Handler.calls) == 2
        assert Handler.calls[0]["messages"]
        assert Handler.calls[1]["messages"]
        assert Handler.calls[1]["prompt"] == "user: hello"
    finally:
        server.shutdown()
