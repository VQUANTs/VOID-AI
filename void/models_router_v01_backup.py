import requests
from .config import Config


class ModelEngine:

    def __init__(self):
        self.api_key = Config.OPENROUTER_API_KEY

        # Keep model names in one place.
        # You can change them later without touching the router logic.
        self.models = {
            "fast": Config.DEFAULT_MODEL,
            "coding": Config.DEFAULT_MODEL,
            "reasoning": Config.DEFAULT_MODEL,
            "cyber": Config.DEFAULT_MODEL,
            "research": Config.DEFAULT_MODEL,
        }

        self.last_route = "fast"
        self.last_model = Config.DEFAULT_MODEL


    def choose_model(self, text):
        """
        Simple keyword router.
        We keep the first version deterministic and easy to debug.
        """

        text = text.lower()

        research_words = [
            "search the web",
            "search online",
            "latest",
            "current",
            "today",
            "recent",
            "news",
            "look it up",
        ]

        cyber_words = [
            "cybersecurity",
            "security",
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
        ]

        code_words = [
            "python",
            "javascript",
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
        ]

        reasoning_words = [
            "analyze deeply",
            "deep analysis",
            "step by step",
            "compare",
            "strategy",
            "plan",
            "architecture",
            "reasoning",
            "solve",
            "why does",
        ]

        if any(word in text for word in research_words):
            route = "research"

        elif any(word in text for word in cyber_words):
            route = "cyber"

        elif any(word in text for word in code_words):
            route = "coding"

        elif any(word in text for word in reasoning_words):
            route = "reasoning"

        else:
            route = "fast"

        self.last_route = route
        self.last_model = self.models[route]

        return self.last_model


    def get_status(self):
        return {
            "route": self.last_route,
            "model": self.last_model
        }


    def chat(self, messages, model=None, stream=False):

        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")

        # If a model was explicitly supplied, use it.
        # Otherwise route based on the latest user message.
        if model is None:

            user_text = ""

            for message in reversed(messages):
                if message.get("role") == "user":
                    user_text = message.get("content", "")
                    break

            model = self.choose_model(user_text)

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": 0.7,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://void.local",
            "X-Title": "VOID CORE",
        }

        response = requests.post(
            Config.OPENROUTER_URL,
            json=payload,
            headers=headers,
            timeout=(15, 120),
            stream=stream,
        )

        self.last_model = model

        return response
