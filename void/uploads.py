import mimetypes
import re
import secrets
from pathlib import Path


class UploadManager:

    MAX_FILE_BYTES = 10 * 1024 * 1024
    MAX_TEXT_CHARS = 30000

    TEXT_EXTENSIONS = {
        ".txt",
        ".md",
        ".markdown",
        ".py",
        ".json",
        ".csv",
        ".tsv",
        ".xml",
        ".html",
        ".htm",
        ".css",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".cc",
        ".go",
        ".rs",
        ".php",
        ".rb",
        ".sh",
        ".bash",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".log",
        ".sql",
        ".env",
        ".gitignore",
    }

    def __init__(self, root=None):

        if root is None:
            root = Path.cwd() / "uploads"

        self.root = Path(root).resolve()

        self.root.mkdir(
            parents=True,
            exist_ok=True
        )

    # --------------------------------------------------
    # Secure filename
    # --------------------------------------------------

    @staticmethod
    def safe_filename(filename):

        filename = str(filename or "file")

        filename = Path(filename).name

        filename = re.sub(
            r"[^A-Za-z0-9._-]",
            "_",
            filename
        )

        filename = filename.strip(".")

        if not filename:
            filename = "file"

        return filename[:180]

    # --------------------------------------------------
    # Create upload path
    # --------------------------------------------------

    def create_path(self, filename):

        safe_name = self.safe_filename(filename)

        upload_id = secrets.token_hex(12)

        directory = (
            self.root / upload_id
        ).resolve()

        directory.mkdir(
            parents=True,
            exist_ok=False
        )

        target = (
            directory / safe_name
        ).resolve()

        try:
            target.relative_to(self.root)
        except ValueError:
            raise PermissionError(
                "Upload path escaped upload directory."
            )

        return upload_id, target

    # --------------------------------------------------
    # Save downloaded bytes
    # --------------------------------------------------

    def save_bytes(self, filename, data):

        if not isinstance(data, bytes):
            raise TypeError(
                "Upload data must be bytes."
            )

        if len(data) > self.MAX_FILE_BYTES:
            raise ValueError(
                "File exceeds the 10 MB upload limit."
            )

        upload_id, target = self.create_path(
            filename
        )

        target.write_bytes(data)

        return {
            "upload_id": upload_id,
            "filename": target.name,
            "path": str(
                target.relative_to(
                    self.root.parent
                )
            ),
            "absolute_path": str(target),
            "size_bytes": len(data),
            "mime_type": (
                mimetypes.guess_type(
                    target.name
                )[0]
                or "application/octet-stream"
            )
        }

    # --------------------------------------------------
    # Resolve uploaded file
    # --------------------------------------------------

    def resolve(self, relative_path):

        if not isinstance(
            relative_path,
            str
        ) or not relative_path.strip():

            raise ValueError(
                "Uploaded file path is required."
            )

        target = (
            self.root.parent /
            relative_path
        ).resolve()

        try:
            target.relative_to(
                self.root
            )
        except ValueError:
            raise PermissionError(
                "File must remain inside the "
                "VOID upload directory."
            )

        if not target.exists():
            raise FileNotFoundError(
                f"Uploaded file not found: "
                f"{relative_path}"
            )

        if not target.is_file():
            raise ValueError(
                "Uploaded path is not a regular file."
            )

        return target

    # --------------------------------------------------
    # Inspect uploaded file
    # --------------------------------------------------

    def inspect(self, relative_path):

        target = self.resolve(
            relative_path
        )

        size = target.stat().st_size

        result = {
            "path": str(
                target.relative_to(
                    self.root.parent
                )
            ),
            "filename": target.name,
            "size_bytes": size,
            "extension": target.suffix.lower(),
            "mime_type": (
                mimetypes.guess_type(
                    target.name
                )[0]
                or "application/octet-stream"
            ),
            "text_readable": False,
            "truncated": False,
            "content": ""
        }

        if size > self.MAX_FILE_BYTES:
            raise ValueError(
                "Uploaded file exceeds the "
                "10 MB processing limit."
            )

        if target.suffix.lower() not in self.TEXT_EXTENSIONS:
            return result

        try:
            content = target.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            return result

        result["text_readable"] = True

        if len(content) > self.MAX_TEXT_CHARS:
            content = content[
                :self.MAX_TEXT_CHARS
            ]
            result["truncated"] = True

        result["content"] = content

        return result
