from types import SimpleNamespace

from void.config import Config
from void.models import ModelEngine


def test_video_falls_back_to_next_gemini_model(monkeypatch):
    engine = ModelEngine()
    engine.gemini_key = "test-key"
    monkeypatch.setattr(Config, "GEMINI_VIDEO_MODEL", "gemini-primary")
    monkeypatch.setattr(Config, "GEMINI_VIDEO_MODELS", ("gemini-primary", "gemini-backup"))

    calls = []

    class Resp:
        def __init__(self, status, payload=None):
            self.status_code = status
            self._payload = payload or {}
            self.text = "service unavailable" if status >= 400 else ""

        def json(self):
            return self._payload

        def raise_for_status(self):
            raise AssertionError("unexpected raise_for_status")

    responses = [
        Resp(503), Resp(503), Resp(503),
        Resp(200, {"candidates": [{"content": {"parts": [{"text": "backup video works"}]}}]}),
    ]

    def fake_post(url, **kwargs):
        calls.append(url)
        return responses.pop(0)

    monkeypatch.setattr("void.models.requests.post", fake_post)
    monkeypatch.setattr("void.models.time.sleep", lambda *_: None)

    answer = engine.chat_with_video(b"video", "video/mp4", "analyze")

    assert answer == "backup video works"
    assert engine.last_model == "gemini-backup"
    assert calls[0].endswith("/gemini-primary:generateContent")
    assert calls[-1].endswith("/gemini-backup:generateContent")
