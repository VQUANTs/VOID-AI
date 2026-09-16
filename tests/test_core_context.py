from void.core import VoidCore


def test_build_messages_contains_current_user_once(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    core = VoidCore()
    messages = core.build_messages("hello", "chat-1")
    users = [m for m in messages if m.get("role") == "user" and m.get("content") == "hello"]
    assert len(users) == 1
    core.memory.close()
