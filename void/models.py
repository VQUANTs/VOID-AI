"""VOID model facade.

Keeps the historical ModelEngine API while routing normal chat/tool calls
through the new capability-aware provider registry.
"""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .config import Config
from .router import ModelRouter


class ModelEngine:
    def __init__(self):
        self.router = ModelRouter()
        self.gemini_key = Config.GEMINI_API_KEY
        self.groq_key = Config.GROQ_API_KEY
        self.hf_token = Config.HF_TOKEN
        self.models = {route: list(models) for route, models in Config.MODELS.items()}
        self.last_route = "fast"
        self.last_model = ""
        self.last_provider = ""
        self.last_error = None

    def choose_route(self, text):
        return self.router.infer_route(text)

    def choose_model(self, text):
        route = self.choose_route(text)
        model = self.router.choose(text, route=route)
        self.last_route, self.last_model, self.last_provider = route, model.id, model.provider
        return model.id

    def candidates_for(self, route):
        capability = {
            "fast": "text",
            "general": "text",
            "coding": "coding",
            "reasoning": "reasoning",
            "research": "text",
            "vision": "vision",
        }.get(route)
        models = self.router.registry.all_models()
        if capability:
            matching = [
                m.id for m in models
                if capability in {c.lower() for c in m.capabilities}
            ]
            if matching:
                return matching
        return [Config.DEFAULT_MODEL]

    def refresh_models(self, force=False):
        return self.router.refresh(force=force)

    def get_status(self):
        status = self.router.status()
        status.update({
            "gemini": bool(self.gemini_key),
            "groq": bool(self.groq_key),
            "router9": bool(Config.ROUTER_BASE_URL),
            "openrouter": bool(Config.OPENROUTER_API_KEY),
            "free_models": len(status["models"]),
            "fallback": Config.FALLBACK_MODEL,
        })
        if self.last_model:
            status["model"] = self.last_model
        if self.last_provider:
            status["provider"] = self.last_provider
        return status

    def chat(self, messages, model=None, stream=False, temperature=0.7, max_tokens=None, **kwargs):
        response = self.router.chat(
            messages, model=model, stream=stream,
            temperature=temperature, max_tokens=max_tokens, **kwargs
        )
        self.last_route = self.router.last_route
        self.last_model = self.router.last_model
        self.last_provider = self.router.last_provider
        return response

    def chat_with_tools(self, messages, tools, model=None):
        return self.router.chat(messages, model=model, tools=tools, stream=False)

    def chat_with_image(self, image_bytes, mime_type, prompt):
        if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
            raise ValueError("Image data must be non-empty bytes.")
        if not mime_type:
            mime_type = "image/jpeg"
        data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt or "Analyze this image carefully."},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }]
        try:
            response = self.router.chat(
                messages, route="vision", required_capability="vision"
            )
            self.last_route = "vision"
            return response
        except Exception:
            if not self.gemini_key:
                raise
            # Gemini OpenAI-compatible endpoint fallback.
            payload = {
                "model": Config.GEMINI_MODEL,
                "messages": messages,
                "stream": False,
                "temperature": 0.7,
            }
            response = requests.post(
                Config.GEMINI_URL,
                json=payload,
                headers={"Authorization": f"Bearer {self.gemini_key}"},
                timeout=(15, 180),
            )
            response.raise_for_status()
            self.last_route, self.last_provider, self.last_model = "vision", "gemini", Config.GEMINI_MODEL
            return response

    def generate_image(self, prompt, model=None):
        if not prompt or not prompt.strip():
            raise ValueError("Image generation prompt cannot be empty.")
        model = model or Config.HF_IMAGE_MODEL
        if not self.hf_token:
            raise RuntimeError("HF_TOKEN is required for image generation.")
        from gradio_client import Client
        client = Client(model, httpx_kwargs={"timeout": 180.0})
        result = client.predict(
            prompt.strip(), 1024, 1024, 9, 42, True, api_name="/generate_image"
        )
        image_path = result[0] if isinstance(result, tuple) else result
        if not image_path or not Path(image_path).is_file():
            raise RuntimeError("Image generation returned no readable image.")
        return Path(image_path).read_bytes()

    def chat_with_video(self, video_bytes, mime_type, prompt):
        if not isinstance(video_bytes, (bytes, bytearray)) or not video_bytes:
            raise ValueError("Video data must be non-empty bytes.")
        if len(video_bytes) > 10 * 1024 * 1024:
            raise ValueError("Video exceeds the 10 MB processing limit.")
        if not self.gemini_key:
            raise RuntimeError("GEMINI_API_KEY is required for video analysis.")
        payload = {
            "contents": [{"parts": [
                {"inline_data": {"mime_type": mime_type or "video/mp4",
                                 "data": base64.b64encode(video_bytes).decode("ascii")}},
                {"text": prompt or "Analyze this video carefully."},
            ]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1200},
        }
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{Config.GEMINI_VIDEO_MODEL}:generateContent"
        )
        response = None
        last = None
        for attempt in range(3):
            try:
                response = requests.post(
                    url, json=payload,
                    headers={"x-goog-api-key": self.gemini_key, "Content-Type": "application/json"},
                    timeout=(15, 300),
                )
                if response.status_code not in {429, 500, 502, 503, 504}:
                    break
                last = response
                if attempt < 2:
                    time.sleep(2 ** attempt)
            except requests.RequestException as exc:
                if attempt == 2:
                    raise RuntimeError(f"Gemini video request failed: {exc}") from exc
                time.sleep(2 ** attempt)
        if response is None:
            if last is None:
                raise RuntimeError("Gemini video request produced no response")
            response = last
        if response.status_code in {429, 500, 502, 503, 504} and last is not None:
            response = last
        response.raise_for_status()
        data = response.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        answer = "\n".join(
            p.get("text", "").strip() for p in parts if isinstance(p.get("text"), str) and p.get("text", "").strip()
        ).strip()
        if not answer:
            raise RuntimeError("Video model returned an empty answer.")
        self.last_route, self.last_provider, self.last_model = "video", "gemini", Config.GEMINI_VIDEO_MODEL
        return answer

    @staticmethod
    def extract_tool_calls(data):
        try:
            return data["choices"][0]["message"].get("tool_calls") or []
        except (KeyError, IndexError, TypeError):
            return []

    @staticmethod
    def extract_message(data):
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("Model response has no message.")
        if not isinstance(message, dict):
            raise RuntimeError("Model response message is invalid.")
        return message

    @staticmethod
    def parse_tool_arguments(tool_call):
        function = tool_call.get("function") or {}
        raw = function.get("arguments", "{}")
        if isinstance(raw, dict):
            return raw
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid tool arguments: {exc}") from exc
        if not isinstance(value, dict):
            raise RuntimeError("Tool arguments must be a JSON object.")
        return value
