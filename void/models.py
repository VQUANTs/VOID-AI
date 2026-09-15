import base64
import json
import requests
import time

from .config import Config


class ModelEngine:

    def __init__(self):

        self.gemini_key = Config.GEMINI_API_KEY
        self.groq_key = Config.GROQ_API_KEY

        self.models = {
            route: list(models)
            for route, models in Config.MODELS.items()
        }

        self.last_route = "fast"
        self.last_model = Config.GEMINI_MODEL
        self.last_provider = "gemini"
        self.last_error = None

    # --------------------------------------------------
    # Routing
    # --------------------------------------------------

    def choose_route(self, text):

        text = text.lower()

        research_words = [
            "search the web",
            "search online",
            "look it up",
            "latest",
            "current",
            "today",
            "recent",
            "news",
            "source",
            "sources",
            "research"
        ]

        cyber_words = [
            "cybersecurity",
            "cyber security",
            "vulnerability",
            "exploit",
            "ctf",
            "malware",
            "reverse engineering",
            "sql injection",
            "xss",
            "buffer overflow",
            "nmap",
            "wireshark",
            "burp",
            "pentest",
            "penetration test",
            "security analysis",
            "security audit"
        ]

        coding_words = [
            "python",
            "javascript",
            "typescript",
            "java",
            "c++",
            "c#",
            "program",
            "code",
            "function",
            "debug",
            "error",
            "bug",
            "script",
            "api",
            "android",
            "termux",
            "compile",
            "compiler"
        ]

        reasoning_words = [
            "analyze deeply",
            "deep analysis",
            "step by step",
            "compare",
            "strategy",
            "architecture",
            "reasoning",
            "solve",
            "why does",
            "why is",
            "design",
            "plan",
            "complex"
        ]

        if any(x in text for x in research_words):
            return "research"

        if any(x in text for x in cyber_words):
            return "cyber"

        if any(x in text for x in coding_words):
            return "coding"

        if any(x in text for x in reasoning_words):
            return "reasoning"

        return "fast"

    # --------------------------------------------------
    # Model selection
    # --------------------------------------------------

    def choose_model(self, text):

        route = self.choose_route(text)

        self.last_route = route
        self.last_model = Config.GEMINI_MODEL
        self.last_provider = "gemini"

        return Config.GEMINI_MODEL

    def candidates_for(self, route):

        return [
            Config.GEMINI_MODEL,
            Config.GROQ_MODEL
        ]

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    def get_status(self):

        return {
            "route": self.last_route,
            "model": self.last_model,
            "provider": self.last_provider,
            "candidates": [
                Config.GEMINI_MODEL,
                Config.GROQ_MODEL
            ],
            "fallback": Config.GROQ_MODEL,
            "gemini": bool(self.gemini_key),
            "groq": bool(self.groq_key),
            "openrouter": False,
            "free_models": 0,
            "error": self.last_error
        }

    # --------------------------------------------------
    # Gemini request
    # --------------------------------------------------

    def _gemini_request(
        self,
        messages,
        stream=False,
        tools=None,
        tool_choice=None
    ):

        payload = {
            "model": Config.GEMINI_MODEL,
            "messages": messages,
            "stream": stream,
            "temperature": 0.7
        }

        if tools:
            payload["tools"] = tools

        if tool_choice is not None:
            payload["tool_choice"] = tool_choice

        headers = {
            "Authorization":
            f"Bearer {self.gemini_key}",
            "Content-Type":
            "application/json"
        }

        return requests.post(
            Config.GEMINI_URL,
            json=payload,
            headers=headers,
            timeout=(15, 180),
            stream=stream
        )

    # --------------------------------------------------
    # Gemini image request
    # --------------------------------------------------

    def chat_with_image(
        self,
        image_bytes,
        mime_type,
        prompt
    ):

        if not isinstance(image_bytes, (bytes, bytearray)):
            raise RuntimeError(
                "Image data must be bytes."
            )

        if not mime_type:
            mime_type = "image/jpeg"

        image_base64 = base64.b64encode(
            image_bytes
        ).decode("ascii")

        image_url = (
            f"data:{mime_type};base64,"
            f"{image_base64}"
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ]

        # --------------------------------------------------
        # Primary: Gemini Vision
        # --------------------------------------------------

        if self.gemini_key:

            response = self._gemini_request(
                messages,
                stream=False
            )

            # Gemini rate limits and transient server errors
            # should fall through to the Groq vision model.
            if response.status_code not in {
                408,
                429,
                500,
                502,
                503,
                504
            }:

                self._check_response(response)

                self.last_route = "vision"
                self.last_provider = "gemini"
                self.last_model = Config.GEMINI_MODEL
                self.last_error = None

                return response

        # --------------------------------------------------
        # Fallback: Groq Vision
        # --------------------------------------------------

        if not self.groq_key:
            if self.gemini_key:
                self._check_response(response)

            raise RuntimeError(
                "No vision provider is available. "
                "GEMINI_API_KEY and GROQ_API_KEY are missing."
            )

        response = self._groq_request(
            messages,
            stream=False,
            model=Config.GROQ_VISION_MODEL
        )

        self._check_response(response)

        self.last_route = "vision"
        self.last_provider = "groq"
        self.last_model = Config.GROQ_VISION_MODEL
        self.last_error = None

        return response

    # --------------------------------------------------
    # Groq request
    # --------------------------------------------------

    # --------------------------------------------------
    # Gemini video request
    # --------------------------------------------------

    def chat_with_video(
        self,
        video_bytes,
        mime_type,
        prompt
    ):

        if not isinstance(
            video_bytes,
            (bytes, bytearray)
        ):
            raise RuntimeError(
                "Video data must be bytes."
            )

        if not video_bytes:
            raise RuntimeError(
                "Video data is empty."
            )

        if not mime_type:
            mime_type = "video/mp4"

        if not self.gemini_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        # Gemini inline video requests are intended
        # for smaller one-off videos.
        if len(video_bytes) > 10 * 1024 * 1024:
            raise RuntimeError(
                "Video exceeds VOID's 10 MB video limit."
            )

        video_base64 = base64.b64encode(
            video_bytes
        ).decode("ascii")

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": video_base64
                            }
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1200
            }
        }

        url = (
            "https://generativelanguage.googleapis.com/"
            "v1beta/models/"
            f"{Config.GEMINI_VIDEO_MODEL}:generateContent"
        )

        headers = {
            "x-goog-api-key": self.gemini_key,
            "Content-Type": "application/json"
        }

        # Retry temporary Gemini availability/rate-limit errors.
        # Do not retry permanent request/authentication errors.
        retry_statuses = {
            429, 500, 502, 503, 504
        }

        response = None

        for attempt in range(3):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=(15, 300)
                )
            except requests.RequestException as error:
                if attempt == 2:
                    raise RuntimeError(
                        f"Gemini video request failed: {error}"
                    )
                time.sleep(2 ** attempt)
                continue

            if response.status_code not in retry_statuses:
                break

            if attempt < 2:
                time.sleep(2 ** attempt)

        if response is None:
            raise RuntimeError(
                "Gemini video request returned no response."
            )

        if response.status_code >= 400:
            try:
                error_data = response.json()
            except Exception:
                error_data = response.text

            raise RuntimeError(
                f"Gemini video HTTP error "
                f"{response.status_code}: "
                f"{error_data}"
            )

        try:
            data = response.json()
        except Exception as e:
            raise RuntimeError(
                f"Invalid JSON response from video model: {e}"
            )

        candidates = data.get("candidates")

        if not candidates:
            raise RuntimeError(
                "Video model returned no candidates."
            )

        content = (
            candidates[0]
            .get("content", {})
        )

        parts = content.get("parts", [])

        answers = []

        for part in parts:

            text = part.get("text")

            if isinstance(text, str) and text.strip():
                answers.append(text.strip())

        answer = "\n".join(answers).strip()

        if not answer:
            raise RuntimeError(
                "Video model returned an empty answer."
            )

        self.last_route = "video"
        self.last_provider = "gemini"
        self.last_model = Config.GEMINI_VIDEO_MODEL
        self.last_error = None

        return answer

    def _groq_request(
        self,
        messages,
        stream=False,
        tools=None,
        tool_choice=None,
        model=None
    ):

        if model is None:
            model = Config.GROQ_MODEL

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": 0.7,
            "max_tokens": 1000
        }

        if tools:
            payload["tools"] = tools

        if tool_choice is not None:
            payload["tool_choice"] = tool_choice

        headers = {
            "Authorization":
            f"Bearer {self.groq_key}",
            "Content-Type":
            "application/json"
        }

        return requests.post(
            Config.GROQ_URL,
            json=payload,
            headers=headers,
            timeout=(15, 180),
            stream=stream
        )

    # --------------------------------------------------
    # Response validation
    # --------------------------------------------------

    def _check_response(self, response):

        response.raise_for_status()

        try:
            data = response.json()
        except Exception:
            return

        if isinstance(data, dict):

            if data.get("error"):

                error = data["error"]

                if isinstance(error, dict):

                    message = error.get(
                        "message",
                        str(error)
                    )

                    code = error.get(
                        "code",
                        ""
                    )

                    raise RuntimeError(
                        f"{message} (code={code})"
                    )

                raise RuntimeError(
                    str(error)
                )

            if "choices" not in data:

                raise RuntimeError(
                    "Response contains no choices"
                )

            if not data["choices"]:

                raise RuntimeError(
                    "Response contains empty choices"
                )

    # --------------------------------------------------
    # Generic provider request
    # --------------------------------------------------

    def _request(
        self,
        messages,
        stream=False,
        tools=None,
        tool_choice=None
    ):

        errors = []

        # ----------------------------------------------
        # PRIMARY: GEMINI
        # ----------------------------------------------

        if self.gemini_key:

            try:

                response = self._gemini_request(
                    messages,
                    stream=stream,
                    tools=tools,
                    tool_choice=tool_choice
                )

                self._check_response(response)

                self.last_provider = "gemini"
                self.last_model = Config.GEMINI_MODEL

                return response

            except Exception as error:

                errors.append(
                    f"Gemini: {error}"
                )

        # ----------------------------------------------
        # FALLBACK: GROQ
        # ----------------------------------------------

        if self.groq_key:

            try:

                response = self._groq_request(
                    messages,
                    stream=stream,
                    tools=tools,
                    tool_choice=tool_choice
                )

                self._check_response(response)

                self.last_provider = "groq"
                self.last_model = Config.GROQ_MODEL

                self.last_error = (
                    "; ".join(errors)
                    if errors
                    else None
                )

                return response

            except Exception as error:

                errors.append(
                    f"Groq: {error}"
                )

        if errors:

            self.last_error = "; ".join(errors)

        else:

            self.last_error = (
                "No model API keys are configured."
            )

        raise RuntimeError(
            "All model providers failed.\n"
            + self.last_error
        )

    # --------------------------------------------------
    # Chat
    # --------------------------------------------------

    def chat(
        self,
        messages,
        model=None,
        stream=False
    ):

        return self._chat_request(
            messages,
            model=model,
            stream=stream
        )

    # --------------------------------------------------
    # Tool calling
    # --------------------------------------------------

    def chat_with_tools(
        self,
        messages,
        tools,
        model=None
    ):

        return self._chat_request(
            messages,
            model=model,
            stream=False,
            tools=tools
        )

    # --------------------------------------------------
    # Main request
    # --------------------------------------------------

    def _chat_request(
        self,
        messages,
        model=None,
        stream=False,
        tools=None
    ):

        if not self.gemini_key and not self.groq_key:

            raise RuntimeError(
                "Neither GEMINI_API_KEY nor "
                "GROQ_API_KEY is configured."
            )

        self.last_error = None

        user_text = ""

        for message in reversed(messages):

            if message.get("role") == "user":

                content = message.get(
                    "content",
                    ""
                )

                if isinstance(content, str):
                    user_text = content

                break

        self.last_route = (
            "custom"
            if model
            else self.choose_route(user_text)
        )

        response = self._request(
            messages,
            stream=stream,
            tools=tools
        )

        return response

    # --------------------------------------------------
    # Tool response helpers
    # --------------------------------------------------

    @staticmethod
    def extract_tool_calls(data):

        choices = data.get(
            "choices",
            []
        )

        if not choices:
            return []

        message = choices[0].get(
            "message",
            {}
        )

        calls = message.get(
            "tool_calls"
        )

        if not calls:
            return []

        return calls

    @staticmethod
    def extract_message(data):

        choices = data.get(
            "choices",
            []
        )

        if not choices:

            raise RuntimeError(
                "Model returned no choices"
            )

        message = choices[0].get(
            "message"
        )

        if not message:

            raise RuntimeError(
                "Model response has no message"
            )

        return message

    @staticmethod
    def parse_tool_arguments(tool_call):

        function = tool_call.get(
            "function",
            {}
        )

        raw = function.get(
            "arguments",
            "{}"
        )

        if isinstance(raw, dict):
            return raw

        try:

            arguments = json.loads(raw)

        except json.JSONDecodeError as error:

            raise RuntimeError(
                "Invalid tool arguments: "
                + str(error)
            )

        if not isinstance(arguments, dict):

            raise RuntimeError(
                "Tool arguments must be a JSON object"
            )

        return arguments
