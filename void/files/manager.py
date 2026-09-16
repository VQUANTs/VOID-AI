"""Bounded, safe file indexing and extraction for VOID."""

from __future__ import annotations

import hashlib
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


class FileManager:
    TEXT_EXTENSIONS = {
        ".txt", ".md", ".markdown", ".py", ".js", ".jsx", ".ts", ".tsx",
        ".java", ".c", ".h", ".cpp", ".hpp", ".cc", ".go", ".rs", ".php",
        ".rb", ".sh", ".bash", ".json", ".csv", ".tsv", ".xml", ".html",
        ".htm", ".css", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sql",
        ".log", ".env", ".gitignore",
    }

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()

    def resolve(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("path is required")
        target = (self.root / relative_path).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise PermissionError("Path escapes the configured workspace") from exc
        if not target.is_file():
            raise FileNotFoundError(relative_path)
        return target

    def read_text(self, relative_path: str, max_chars: int = 50000) -> Dict[str, Any]:
        target = self.resolve(relative_path)
        if target.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("Text file exceeds the 2 MB read limit")
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("File is not UTF-8 text") from exc
        truncated = len(text) > max_chars
        return {
            "path": str(target.relative_to(self.root)),
            "content": text[:max_chars],
            "truncated": truncated,
            "size_bytes": target.stat().st_size,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        }

    def scan(self, max_files: int = 2000) -> Dict[str, Any]:
        ignored = {".git", "__pycache__", ".venv", "venv", "env", "node_modules", "build", ".gradle"}
        files = []
        for path in self.root.rglob("*"):
            if path.is_symlink() or not path.is_file() or any(part in ignored for part in path.relative_to(self.root).parts):
                continue
            files.append(path)
            if len(files) >= max_files:
                break
        entries = []
        for path in files:
            rel = str(path.relative_to(self.root))
            entries.append({
                "path": rel,
                "size_bytes": path.stat().st_size,
                "extension": path.suffix.lower(),
                "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            })
        return {"root": str(self.root), "count": len(entries), "files": entries}
