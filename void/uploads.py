import mimetypes
import re
import secrets
import zipfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path


class _EPUBTextParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        if data and data.strip():
            self.parts.append(data.strip())

    def text(self):
        return " ".join(self.parts)


class UploadManager:

    MAX_FILE_BYTES = 10 * 1024 * 1024
    MAX_TEXT_CHARS = 8000

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
    # EPUB extraction
    # --------------------------------------------------

    def _extract_epub_text(self, target):

        with zipfile.ZipFile(target, "r") as archive:

            container_data = archive.read(
                "META-INF/container.xml"
            )

            container_root = ET.fromstring(
                container_data
            )

            rootfile = None

            for element in container_root.iter():

                if element.tag.endswith("rootfile"):

                    rootfile = element
                    break

            if rootfile is None:
                raise ValueError(
                    "EPUB container has no rootfile."
                )

            opf_path = rootfile.attrib.get(
                "full-path"
            )

            if not opf_path:
                raise ValueError(
                    "EPUB rootfile has no full-path."
                )

            opf_data = archive.read(opf_path)

            opf_root = ET.fromstring(
                opf_data
            )

            opf_dir = Path(opf_path).parent

            manifest = {}

            for element in opf_root.iter():

                if element.tag.endswith("item"):

                    item_id = element.attrib.get("id")
                    href = element.attrib.get("href")
                    media_type = element.attrib.get(
                        "media-type",
                        ""
                    )

                    if item_id and href:
                        manifest[item_id] = (
                            href,
                            media_type
                        )

            spine = []

            for element in opf_root.iter():

                if element.tag.endswith("itemref"):

                    item_id = element.attrib.get(
                        "idref"
                    )

                    if item_id in manifest:
                        spine.append(
                            manifest[item_id]
                        )

            if not spine:
                raise ValueError(
                    "EPUB spine contains no documents."
                )

            parts = []
            total_chars = 0

            for href, media_type in spine:

                if (
                    "html" not in media_type
                    and "xhtml" not in media_type
                ):
                    continue

                href = href.split("#", 1)[0]

                document_path = (
                    opf_dir / href
                ).as_posix()

                try:
                    raw = archive.read(
                        document_path
                    )
                except KeyError:
                    continue

                parser = _EPUBTextParser()

                parser.feed(
                    raw.decode(
                        "utf-8",
                        errors="replace"
                    )
                )

                parser.close()

                content = parser.text()

                if not content:
                    continue

                remaining = (
                    self.MAX_TEXT_CHARS
                    - total_chars
                )

                if remaining <= 0:
                    break

                content = content[:remaining]

                parts.append(content)

                total_chars += len(content)

                if total_chars >= self.MAX_TEXT_CHARS:
                    break

            return "\n\n".join(parts)


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

        # --------------------------------------------------
        # EPUB
        # --------------------------------------------------

        if target.suffix.lower() == ".epub":

            try:

                content = self._extract_epub_text(
                    target
                )

                result["text_readable"] = bool(
                    content
                )

                result["content"] = content

                if len(content) >= self.MAX_TEXT_CHARS:
                    result["truncated"] = True

                return result

            except Exception as error:

                result["error"] = (
                    f"EPUB text extraction failed: {error}"
                )

                return result


        # --------------------------------------------------
        # PDF
        # --------------------------------------------------

        if target.suffix.lower() == ".pdf":

            try:
                from pypdf import PdfReader

                reader = PdfReader(str(target))

                pages = []
                total_chars = 0

                for page_number, page in enumerate(reader.pages):

                    page_text = page.extract_text() or ""

                    if page_text:
                        pages.append(
                            f"\n--- PAGE {page_number + 1} ---\n"
                            + page_text
                        )

                        total_chars += len(page_text)

                    if total_chars >= self.MAX_TEXT_CHARS:
                        break

                content = "".join(pages)

                if len(content) > self.MAX_TEXT_CHARS:
                    content = content[:self.MAX_TEXT_CHARS]
                    result["truncated"] = True

                result["text_readable"] = bool(content)
                result["content"] = content
                result["page_count"] = len(reader.pages)

                return result

            except Exception as error:

                result["error"] = (
                    f"PDF text extraction failed: {error}"
                )

                return result

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
