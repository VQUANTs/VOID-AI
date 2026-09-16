from pathlib import Path
import pytest
from void.files import FileManager


def test_file_manager_blocks_escape(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    manager = FileManager(str(tmp_path))
    assert manager.read_text("a.txt")["content"] == "hello"
    with pytest.raises(PermissionError):
        manager.resolve("../secret.txt")
