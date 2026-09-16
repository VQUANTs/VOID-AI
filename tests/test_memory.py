from void.memory import Memory


def test_conversation_isolation(tmp_path):
    memory = Memory(str(tmp_path / "memory.db"))
    memory.add("user", "alpha", "one")
    memory.add("assistant", "beta", "two")
    assert memory.recent(10, "one") == [("user", "alpha")]
    assert memory.recent(10, "two") == [("assistant", "beta")]
    memory.clear("one")
    assert memory.recent(10, "one") == []
    assert memory.recent(10, "two") == [("assistant", "beta")]
    memory.close()
