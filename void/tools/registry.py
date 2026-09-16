import json
import platform
import os
import subprocess
import shlex
from pathlib import Path

from ..memory import Memory
from .web import WebSearch
from ..uploads import UploadManager


class ToolRegistry:

    def __init__(self, memory=None, web=None, uploads=None):

        # Shared services may be injected by VoidCore so agent/tool calls
        # use the same memory and web context as normal chat.
        self.memory = memory or Memory()
        self.web = web or WebSearch()
        self.uploads = uploads or UploadManager()

        self.tools = {

            # --------------------------------------------------
            # Web search
            # --------------------------------------------------

            "web_search": {
                "definition": {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": (
                            "Search the web using VOID's web "
                            "search backend. Use for current "
                            "or external information."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": (
                                        "The search query."
                                    )
                                }
                            },
                            "required": ["query"]
                        }
                    }
                },
                "handler": self.web_search
            },

            # --------------------------------------------------
            # Memory search
            # --------------------------------------------------

            "memory_search": {
                "definition": {
                    "type": "function",
                    "function": {
                        "name": "memory_search",
                        "description": (
                            "Search VOID's long-term user memory."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": (
                                        "Information to search "
                                        "for in long-term memory."
                                    )
                                }
                            },
                            "required": ["query"]
                        }
                    }
                },
                "handler": self.memory_search
            },

            # --------------------------------------------------
            # Knowledge search
            # --------------------------------------------------

            "knowledge_search": {
                "definition": {
                    "type": "function",
                    "function": {
                        "name": "knowledge_search",
                        "description": (
                            "Search VOID's local knowledge base."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": (
                                        "Knowledge to search for."
                                    )
                                }
                            },
                            "required": ["query"]
                        }
                    }
                },
                "handler": self.knowledge_search
            },

            # --------------------------------------------------
            # System information
            # --------------------------------------------------

            "system_info": {
                "definition": {
                    "type": "function",
                    "function": {
                        "name": "system_info",
                        "description": (
                            "Return basic information about "
                            "the local VOID runtime environment."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                },
                "handler": self.system_info
            },

            # --------------------------------------------------
            # Project scan
            # --------------------------------------------------

            "project_scan": {
                "definition": {
                    "type": "function",
                    "function": {
                        "name": "project_scan",
                        "description": (
                            "Scan the VOID project read-only. "
                            "Return source files, Python files, "
                            "TODO/FIXME markers, imports, classes, "
                            "and functions for code analysis."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                },
                "handler": self.project_scan
            },

            # --------------------------------------------------
            # File read
            # --------------------------------------------------

            "file_read": {
                "definition": {
                    "type": "function",
                    "function": {
                        "name": "file_read",
                        "description": (
                            "Read a text file inside the VOID "
                            "project for code analysis, debugging, "
                            "and inspection. This tool is strictly "
                            "read-only."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": (
                                        "Relative path inside the "
                                        "VOID project."
                                    )
                                }
                            },
                            "required": ["path"]
                        }
                    }
                },
                "handler": self.file_read
            },

            # --------------------------------------------------
            # Static code analysis
            # --------------------------------------------------

            "code_analyze": {
                "definition": {
                    "type": "function",
                    "function": {
                        "name": "code_analyze",
                        "description": (
                            "Analyze a Python source file read-only "
                            "using static AST analysis. Report syntax "
                            "validity, imports, classes, functions, "
                            "TODO/FIXME markers, and potentially "
                            "risky calls without executing the file."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": (
                                        "Relative path to a Python "
                                        "file inside the VOID project."
                                    )
                                }
                            },
                            "required": [
                                "path"
                            ]
                        }
                    }
                },
                "handler": self.code_analyze
            },

            # --------------------------------------------------
            # Verified code analysis
            # --------------------------------------------------

            "code_verify": {
                "definition": {
                    "type": "function",
                    "function": {
                        "name": "code_verify",
                        "description": (
                            "Verify a code or architecture claim "
                            "against the actual VOID source. "
                            "Read the specified project files and "
                            "classify the claim as VERIFIED, "
                            "NOT VERIFIED, or NEEDS REVIEW. "
                            "Never invent source evidence."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "claim": {
                                    "type": "string",
                                    "description": (
                                        "The code or architecture "
                                        "claim that must be verified."
                                    )
                                },
                                "paths": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    },
                                    "description": (
                                        "Relative project file paths "
                                        "that contain the evidence."
                                    )
                                }
                            },
                            "required": [
                                "claim",
                                "paths"
                            ]
                        }
                    }
                },
                "handler": self.code_verify
            },

            # --------------------------------------------------
            # Uploaded file read
            # --------------------------------------------------

            "uploaded_file_read": {
                "definition": {
                    "type": "function",
                    "function": {
                        "name": "uploaded_file_read",
                        "description": (
                            "Inspect and read a file uploaded by "
                            "the user through VOID. Use this tool "
                            "when the user asks you to analyze, "
                            "summarize, inspect, explain, compare, "
                            "or otherwise work with an uploaded "
                            "file. Uploaded files are isolated "
                            "from the VOID source tree. Do not "
                            "execute uploaded files."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": (
                                        "The uploaded file path "
                                        "provided in the user's "
                                        "file context."
                                    )
                                }
                            },
                            "required": ["path"]
                        }
                    }
                },
                "handler": self.uploaded_file_read
            },

            # --------------------------------------------------
            # Terminal
            # --------------------------------------------------

            "terminal": {
                "definition": {
                    "type": "function",
                    "function": {
                        "name": "terminal",
                        "description": (
                            "Run a safe, read-only diagnostic "
                            "command in the local Termux "
                            "environment. Use for system "
                            "inspection, version checks, "
                            "directory inspection, and "
                            "debugging. Do not use commands "
                            "that modify, delete, install, "
                            "download, or execute arbitrary "
                            "payloads."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "description": (
                                        "A single permitted "
                                        "read-only diagnostic "
                                        "command."
                                    )
                                }
                            },
                            "required": ["command"]
                        }
                    }
                },
                "handler": self.terminal
            }
        }

        self.allowed_terminal_commands = {
            "pwd",
            "ls",
            "find",
            "whoami",
            "id",
            "uname",
            "date",
            "env",
            "printenv",
            "python",
            "python3",
            "pip",
            "pip3",
            "which",
            "command",
            "cat",
            "head",
            "tail",
            "wc",
            "file",
            "du",
            "df",
            "ps",
            "termux-info"
        }

    # --------------------------------------------------
    # Tool definitions
    # --------------------------------------------------

    def definitions(self):

        return [
            tool["definition"]
            for tool in self.tools.values()
        ]

    # --------------------------------------------------
    # Tool execution
    # --------------------------------------------------

    def execute(self, name, arguments):

        if name not in self.tools:

            raise RuntimeError(
                f"Unknown tool: {name}"
            )

        if not isinstance(arguments, dict):

            raise RuntimeError(
                "Tool arguments must be a JSON object"
            )

        handler = self.tools[name]["handler"]

        import inspect

        signature = inspect.signature(handler)

        try:
            bound = signature.bind(**arguments)
        except TypeError as error:
            raise RuntimeError(
                f"Invalid arguments for tool '{name}': {error}"
            ) from error

        return handler(*bound.args, **bound.kwargs)

    # --------------------------------------------------
    # Web
    # --------------------------------------------------

    def web_search(self, query):

        if not query:

            raise ValueError(
                "query is required"
            )

        results = self.web.search(query)

        return {
            "query": query,
            "results": results[:5]
        }

    # --------------------------------------------------
    # Long-term memory
    # --------------------------------------------------

    def memory_search(self, query):

        if not query:

            raise ValueError(
                "query is required"
            )

        rows = self.memory.search_memory(
            query,
            limit=10
        )

        results = []

        for row in rows:

            results.append({
                "id": row[0],
                "category": row[1],
                "content": row[2],
                "importance": row[3],
                "created_at": row[4],
                "updated_at": row[5]
            })

        return {
            "query": query,
            "results": results
        }

    # --------------------------------------------------
    # Knowledge
    # --------------------------------------------------

    def knowledge_search(self, query):

        if not query:

            raise ValueError(
                "query is required"
            )

        rows = self.memory.search_knowledge(
            query,
            limit=10
        )

        results = []

        for row in rows:

            results.append({
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "source": row[3],
                "category": row[4],
                "created_at": row[5]
            })

        return {
            "query": query,
            "results": results
        }

    # --------------------------------------------------
    # System information
    # --------------------------------------------------

    def system_info(self):

        return {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "pid": os.getpid()
        }

    # --------------------------------------------------
    # Project scan
    # --------------------------------------------------

    def project_scan(self):

        root = Path.cwd().resolve()

        ignored = {
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "env",
            "node_modules",
            ".gradle",
            "build"
        }

        files = []
        python_files = []
        findings = []
        python_summary = []

        max_files = 500
        max_findings = 50

        for path in root.rglob("*"):

            if not path.is_file():
                continue

            relative = path.relative_to(root)

            if any(
                part in ignored
                for part in relative.parts
            ):
                continue

            if len(files) >= max_files:
                break

            relative_str = str(relative)
            files.append(relative_str)

            if path.suffix != ".py":
                continue

            python_files.append(relative_str)

            try:
                text = path.read_text(
                    encoding="utf-8"
                )
            except (UnicodeDecodeError, OSError):
                continue

            lines = text.splitlines()

            class_count = 0
            function_count = 0
            import_count = 0

            for line_number, line in enumerate(
                lines,
                1
            ):

                stripped = line.strip()

                if (
                    stripped.startswith("import ")
                    or stripped.startswith("from ")
                ):
                    import_count += 1

                if stripped.startswith("class "):
                    class_count += 1

                if (
                    stripped.startswith("def ")
                    or stripped.startswith("async def ")
                ):
                    function_count += 1

                if (
                    "TODO" in stripped
                    or "FIXME" in stripped
                    or "XXX" in stripped
                ):
                    if len(findings) < max_findings:
                        findings.append({
                            "file": relative_str,
                            "line": line_number,
                            "text": stripped[:300]
                        })

            python_summary.append({
                "file": relative_str,
                "lines": len(lines),
                "imports": import_count,
                "classes": class_count,
                "functions": function_count
            })

        return {
            "project_root": str(root),
            "total_files": len(files),
            "python_file_count": len(python_files),
            "python_files": python_files,
            "python_summary": python_summary,
            "findings": findings,
            "limits": {
                "max_files": max_files,
                "max_findings": max_findings
            }
        }

    # --------------------------------------------------
    # File read
    # --------------------------------------------------

    def file_read(self, path):

        if not path or not path.strip():
            raise ValueError(
                "path is required"
            )

        root = Path.cwd().resolve()
        target = (root / path).resolve()

        # Never allow traversal outside VOID-AI.
        try:
            target.relative_to(root)
        except ValueError:
            raise PermissionError(
                "File path must remain inside the VOID project."
            )

        if not target.exists():
            raise FileNotFoundError(
                f"File not found: {path}"
            )

        if not target.is_file():
            raise ValueError(
                f"Not a regular file: {path}"
            )

        # Keep the first version bounded.
        max_bytes = 256 * 1024

        if target.stat().st_size > max_bytes:
            raise ValueError(
                "File is larger than the 256 KB read limit."
            )

        try:
            content = target.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            raise ValueError(
                "File is not valid UTF-8 text."
            )

        # Keep model payloads bounded.
        max_chars = 12000

        truncated = len(content) > max_chars

        if truncated:
            content = content[:max_chars]

        return {
            "path": str(
                target.relative_to(root)
            ),
            "size_bytes": target.stat().st_size,
            "truncated": truncated,
            "content": content
        }

    # --------------------------------------------------
    # Verified code analysis
    # --------------------------------------------------

    def code_analyze(self, path):

        if not isinstance(path, str) or not path.strip():
            raise ValueError(
                "path is required"
            )

        root = Path.cwd().resolve()
        target = (root / path).resolve()

        try:
            target.relative_to(root)
        except ValueError:
            raise PermissionError(
                "File path must remain inside the VOID project."
            )

        if not target.exists():
            raise FileNotFoundError(
                f"File not found: {path}"
            )

        if not target.is_file():
            raise ValueError(
                f"Not a regular file: {path}"
            )

        if target.suffix != ".py":
            raise ValueError(
                "code_analyze currently supports Python files only."
            )

        max_bytes = 256 * 1024

        if target.stat().st_size > max_bytes:
            raise ValueError(
                "File is larger than the 256 KB analysis limit."
            )

        try:
            source = target.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            raise ValueError(
                f"File is not valid UTF-8 text: {path}"
            )

        import ast

        result = {
            "path": str(target.relative_to(root)),
            "size_bytes": target.stat().st_size,
            "lines": len(source.splitlines()),
            "syntax_valid": True,
            "syntax_error": None,
            "imports": [],
            "classes": [],
            "functions": [],
            "findings": []
        }

        try:
            tree = ast.parse(
                source,
                filename=str(target)
            )
        except SyntaxError as error:
            result["syntax_valid"] = False
            result["syntax_error"] = {
                "message": error.msg,
                "line": error.lineno,
                "column": error.offset
            }
            return result

        for node in ast.walk(tree):

            if isinstance(node, ast.Import):

                for alias in node.names:
                    result["imports"].append({
                        "name": alias.name,
                        "line": node.lineno
                    })

            elif isinstance(node, ast.ImportFrom):

                result["imports"].append({
                    "name": node.module or "",
                    "line": node.lineno
                })

            elif isinstance(node, ast.ClassDef):

                result["classes"].append({
                    "name": node.name,
                    "line": node.lineno
                })

            elif isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef)
            ):

                result["functions"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "async": isinstance(
                        node,
                        ast.AsyncFunctionDef
                    )
                })

        for line_number, line in enumerate(
            source.splitlines(),
            1
        ):

            stripped = line.strip()

            if (
                "TODO" in stripped
                or "FIXME" in stripped
                or "XXX" in stripped
            ):

                result["findings"].append({
                    "type": "marker",
                    "line": line_number,
                    "text": stripped[:300]
                })

        for node in ast.walk(tree):

            if not isinstance(node, ast.Call):
                continue

            name = ""

            if isinstance(node.func, ast.Name):

                name = node.func.id

            elif isinstance(node.func, ast.Attribute):

                if isinstance(node.func.value, ast.Name):

                    name = (
                        node.func.value.id
                        + "."
                        + node.func.attr
                    )

            if name in {
                "eval",
                "exec",
                "os.system",
                "subprocess.call",
                "subprocess.run",
                "subprocess.Popen"
            }:

                result["findings"].append({
                    "type": "potentially_risky_call",
                    "line": node.lineno,
                    "name": name
                })

        result["counts"] = {
            "imports": len(result["imports"]),
            "classes": len(result["classes"]),
            "functions": len(result["functions"]),
            "findings": len(result["findings"])
        }

        result["limits"] = {
            "max_bytes": max_bytes
        }

        return result


    def code_verify(self, claim, paths):

        if not isinstance(claim, str) or not claim.strip():
            raise ValueError(
                "claim is required"
            )

        if not isinstance(paths, list) or not paths:
            raise ValueError(
                "paths must be a non-empty list"
            )

        root = Path.cwd().resolve()

        max_paths = 8
        max_file_chars = 12000
        max_total_chars = 30000

        if len(paths) > max_paths:
            raise ValueError(
                f"Maximum {max_paths} files may be verified at once."
            )

        evidence = []
        total_chars = 0

        for raw_path in paths:

            if not isinstance(raw_path, str) or not raw_path.strip():
                raise ValueError(
                    "Each path must be a non-empty string."
                )

            target = (root / raw_path).resolve()

            try:
                target.relative_to(root)
            except ValueError:
                raise PermissionError(
                    "File path must remain inside the VOID project."
                )

            if not target.exists():
                raise FileNotFoundError(
                    f"File not found: {raw_path}"
                )

            if not target.is_file():
                raise ValueError(
                    f"Not a regular file: {raw_path}"
                )

            max_bytes = 256 * 1024

            if target.stat().st_size > max_bytes:
                raise ValueError(
                    f"File is larger than the 256 KB read limit: "
                    f"{raw_path}"
                )

            try:
                content = target.read_text(
                    encoding="utf-8"
                )
            except UnicodeDecodeError:
                raise ValueError(
                    f"File is not valid UTF-8 text: {raw_path}"
                )

            remaining = max_total_chars - total_chars

            if remaining <= 0:
                break

            limit = min(
                max_file_chars,
                remaining
            )

            truncated = len(content) > limit

            if truncated:
                content = content[:limit]

            lines = content.splitlines()

            evidence.append({
                "path": str(target.relative_to(root)),
                "lines": len(lines),
                "size_bytes": target.stat().st_size,
                "truncated": truncated,
                "content": content
            })

            total_chars += len(content)

        return {
            "claim": claim.strip(),
            "status": "SOURCE_EVIDENCE_COLLECTED",
            "instruction": (
                "Judge the claim only from the supplied source "
                "evidence. If the evidence directly supports it, "
                "classify VERIFIED. If the source contradicts it, "
                "classify NOT VERIFIED. If the available source "
                "cannot establish the claim conclusively, classify "
                "NEEDS REVIEW. Do not invent missing evidence."
            ),
            "files_checked": len(evidence),
            "total_content_chars": total_chars,
            "evidence": evidence,
            "limits": {
                "max_paths": max_paths,
                "max_file_chars": max_file_chars,
                "max_total_chars": max_total_chars
            }
        }

    # --------------------------------------------------
    # Uploaded file read
    # --------------------------------------------------

    def uploaded_file_read(self, path):

        return self.uploads.inspect(path)

    # --------------------------------------------------
    # Safe terminal
    # --------------------------------------------------

    def terminal(self, command):

        if not command or not command.strip():

            raise ValueError(
                "command is required"
            )

        command = command.strip()

        try:
            parts = shlex.split(command)
        except ValueError as error:
            raise ValueError(
                f"Invalid command syntax: {error}"
            )

        if not parts:

            raise ValueError(
                "command is required"
            )

        executable = os.path.basename(parts[0])

        if executable not in self.allowed_terminal_commands:

            raise PermissionError(
                f"Terminal command not allowed: {executable}"
            )

        # Prevent shell interpretation and command chaining.
        dangerous_tokens = {
            ";",
            "&&",
            "||",
            "|",
            ">",
            ">>",
            "<",
            "$(",
            "`"
        }

        if any(
            token in command
            for token in dangerous_tokens
        ):

            raise PermissionError(
                "Shell operators and command chaining "
                "are not allowed."
            )

        try:

            completed = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                timeout=15,
                shell=False,
                cwd=os.getcwd()
            )

        except subprocess.TimeoutExpired:

            return {
                "command": command,
                "status": "timeout",
                "exit_code": None,
                "stdout": "",
                "stderr": (
                    "Command exceeded the 15 second limit."
                )
            }

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""

        # Keep tool responses small enough for the model.
        stdout = stdout[:6000]
        stderr = stderr[:3000]

        return {
            "command": command,
            "status": (
                "success"
                if completed.returncode == 0
                else "failed"
            ),
            "exit_code": completed.returncode,
            "stdout": stdout,
            "stderr": stderr
        }

    # --------------------------------------------------
    # Safe serialization
    # --------------------------------------------------

    @staticmethod
    def serialize(result):

        try:

            return json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
                default=str
            )

        except Exception as error:

            return json.dumps({
                "error": str(error)
            })
