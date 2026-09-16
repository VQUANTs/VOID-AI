from void.api import VoidAPI


class FakeCore:
    def ask(self, text, conversation_id="default", model=None, temperature=0.7, max_tokens=None):
        return "ok:" + text

    def model_status(self):
        return {}

    class Memory:
        def stats(self):
            return {"messages": 0, "memories": 0, "knowledge": 0}

    memory = Memory()


def test_api_chat_requires_message():
    api = VoidAPI(FakeCore())
    assert api.chat({"message": "hello"}) == {"answer": "ok:hello", "mode": "chat", "conversation_id": "default"}

class FakeModel:
    last_model = "router9/test"
    def get_status(self):
        return {"models": ["router9/test"], "route": "fast", "model": self.last_model, "provider": "router9"}
    def chat(self, messages, model=None, **kwargs):
        import requests
        r = requests.Response(); r.status_code = 200; r._content = b'{"choices":[{"message":{"content":"v1 ok"}}]}'; return r

class FakeCoreFull(FakeCore):
    def __init__(self):
        self.model = FakeModel()
        self.tools = type("T", (), {"definitions": lambda self: []})()
        self.agent = None
        self.memory = type("M", (), {"stats": lambda self: {"messages": 0, "memories": 0, "knowledge": 0}, "clear": lambda self, cid: None})()
    def ask_messages(self, messages, conversation_id="default", model=None, temperature=0.7, max_tokens=None):
        return "v1 ok"
    def run_agent(self, text, conversation_id="default"):
        return "agent ok"
    def run_task(self, text, conversation_id="default"):
        return {"id":"abc123","status":"completed","result":"task ok"}
    def ask_image_generation(self, *args, **kwargs):
        return b"PNG"

def test_api_modes_and_models():
    api = VoidAPI(FakeCoreFull())
    assert api.models()["count"] == 1
    assert api.chat({"message":"x", "mode":"agent"})["answer"] == "agent ok"
    assert api.chat({"message":"x", "mode":"task"})["task"]["status"] == "completed"

def test_openai_compatible_message_history_and_model():
    api = VoidAPI(FakeCoreFull())
    result = api.core.ask_messages([{"role":"user","content":"hello"}], model="router9/test", max_tokens=50)
    assert result == "v1 ok"


def test_models_refreshes_empty_registry():
    class Model: 
        def get_status(self):
            return {"models": ["router9/test"]}
        def refresh_models(self, force=False):
            return []
    class Core:
        model = Model()
    api = VoidAPI(Core())
    result = api.models()
    assert result["count"] == 1
    assert result["models"][0]["id"] == "router9/test"

def test_browser_status_uses_nested_model_status():
    from void import api as api_module
    html = api_module.WEB_APP
    assert "status.model&&typeof status.model==='object'" in html
    assert "m.total_usage" in html
    assert "m.context_available||m.context_window" in html
    assert "Array.isArray(m.models)" in html
