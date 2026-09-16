"""OpenAI-compatible provider adapter used by VOID's model router."""

from __future__ import annotations

import json
import time
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional

import requests

from ..config import Config


@dataclass
class ProviderModel:
    id: str
    provider: str
    capabilities: List[str]
    context_window: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class OpenAICompatibleProvider:
    """Adapter for OpenAI-compatible /v1 APIs.

    The provider is deliberately generic so Router9 and future
    OpenAI-compatible gateways can be used without coupling VOID to their internals.
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str = "",
        timeout: tuple = (15, 180),
    ):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("provider name is required")
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("provider base_url is required")
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("provider base_url must be an absolute HTTP(S) URL")
        if not isinstance(timeout, tuple) or len(timeout) != 2 or any(float(x) <= 0 for x in timeout):
            raise ValueError("timeout must contain two positive values")
        self.name = name.strip()
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.timeout = (float(timeout[0]), float(timeout[1]))
        self.session = requests.Session()

    @property
    def configured(self) -> bool:
        # Local gateways commonly don't require a key.
        return bool(self.base_url)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key and self.api_key != "YOUR_KEY":
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        headers = self._headers()
        supplied = kwargs.pop("headers", None)
        if supplied:
            headers.update(supplied)
        return self.session.request(
            method,
            self._url(path),
            headers=headers,
            timeout=kwargs.pop("timeout", self.timeout),
            **kwargs,
        )

    @staticmethod
    def _error(response: requests.Response) -> RuntimeError:
        try:
            data = response.json()
        except Exception:
            data = response.text[:2000]
        return RuntimeError(
            f"Provider HTTP {response.status_code}: {data}"
        )

    def list_models(self) -> List[ProviderModel]:
        response = self._request("GET", "/models", timeout=(10, 30))
        if response.status_code >= 400:
            raise self._error(response)
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError(f"Provider returned invalid JSON from /models: {exc}") from exc
        if isinstance(data, dict):
            raw_models = data.get("data", [])
        elif isinstance(data, list):
            raw_models = data
        else:
            raise ProviderError("Provider /models response must be an object or list")
        if not isinstance(raw_models, list):
            raise ProviderError("Provider /models 'data' field must be a list")
        result = []
        for item in raw_models:
            if isinstance(item, str):
                model_id = item
                item = {}
            else:
                model_id = str(item.get("id", "")).strip()
            if not model_id:
                continue
            caps = self._infer_capabilities(model_id, item)
            context = item.get("context_length") or item.get("context_window")
            try:
                context = int(context) if context else None
            except (TypeError, ValueError):
                context = None
            result.append(
                ProviderModel(
                    id=model_id,
                    provider=self.name,
                    capabilities=caps,
                    context_window=context,
                    metadata=dict(item),
                )
            )
        return result

    @staticmethod
    def _infer_capabilities(model_id: str, metadata: Dict[str, Any]) -> List[str]:
        text = model_id.lower()
        declared = metadata.get("capabilities")
        if isinstance(declared, list):
            caps = [str(x) for x in declared]
        else:
            caps = ["text"]
        mapping = {
            "vision": ("vision", "vl", "vision", "multimodal", "gemini", "qwen2.5-vl"),
            "reasoning": ("reason", "thinking", "r1", "o1", "o3", "qwen3"),
            "coding": ("code", "coder", "devstral", "codestral"),
            "embedding": ("embed",),
        }
        for capability, needles in mapping.items():
            if any(n in text for n in needles) and capability not in caps:
                caps.append(capability)
        if "embedding" in caps and "text" in caps:
            caps.remove("text")
        return caps

    def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> requests.Response:
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": bool(stream),
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        last_error = None
        for attempt in range(Config.MODEL_RETRIES + 1):
            response = self._request("POST", "/chat/completions", json=payload)
            if response.status_code < 400:
                return response

            last_error = self._error(response)

            # Some OpenAI-compatible gateways occasionally reject a valid
            # `messages` body with an "Input required" compatibility error.
            # Router9 accepts `prompt` as a compatibility fallback. Preserve
            # the original messages request first; only retry this narrow case
            # with a flattened prompt derived from the conversation.
            if response.status_code == 400 and "Input required" in response.text and "messages" in response.text:
                prompt_parts = []
                for message in messages:
                    if not isinstance(message, dict):
                        continue
                    content = message.get("content", "")
                    if isinstance(content, str) and content.strip():
                        role = str(message.get("role", "user")).strip() or "user"
                        prompt_parts.append(f"{role}: {content.strip()}")
                if prompt_parts:
                    compatibility_payload = dict(payload)
                    compatibility_payload["prompt"] = "\n".join(prompt_parts)
                    compatibility_response = self._request(
                        "POST", "/chat/completions", json=compatibility_payload
                    )
                    if compatibility_response.status_code < 400:
                        return compatibility_response
                    last_error = self._error(compatibility_response)

            if response.status_code not in {429, 500, 502, 503, 504} or attempt >= Config.MODEL_RETRIES:
                raise last_error
            time.sleep(min(2 ** attempt, 4))
        raise last_error or RuntimeError("Provider request failed")

    def stream_text(self, response: requests.Response) -> Iterator[str]:
        """Yield text deltas from an OpenAI-compatible SSE response."""
        for raw in response.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw.strip()
            if line.startswith("data:"):
                line = line[5:].strip()
            if line == "[DONE]":
                break
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            for choice in payload.get("choices", []):
                delta = choice.get("delta", {})
                content = delta.get("content")
                if isinstance(content, str) and content:
                    yield content


class ProviderError(RuntimeError):
    """Raised when a provider returns an invalid or unusable response."""
