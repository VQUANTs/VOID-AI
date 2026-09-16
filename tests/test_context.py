from void.context import ContextEngine


def test_context_keeps_system_and_latest_messages():
    engine = ContextEngine(max_messages=4, max_chars=1000)
    history = [{"role": "user", "content": str(i)} for i in range(10)]
    result = engine.build("system", history, {"role": "user", "content": "latest"})
    assert result[0]["role"] == "system"
    assert result[-1]["content"] == "latest"
    assert len(result) <= 5
