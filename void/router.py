"""Capability-aware model routing with provider discovery and fallback."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .config import Config
from .providers import OpenAICompatibleProvider, ProviderRegistry
from .providers.openai_compatible import ProviderModel


class ModelRouter:
    ROUTES = ("fast", "reasoning", "coding", "research", "vision", "general")

    def __init__(self):
        # Router9 is the only model gateway used by the normal VOID router.
        # Upstream provider credentials/models stay behind Router9.
        providers = []
        if Config.ROUTER_BASE_URL:
            providers.append(OpenAICompatibleProvider(
                "router9",
                Config.ROUTER_BASE_URL,
                Config.ROUTER_API_KEY,
                timeout=(15, Config.MODEL_TIMEOUT),
            ))
        self.registry = ProviderRegistry(providers)

        self.last_route = "fast"
        self.last_model = ""
        self.last_provider = ""
        self.last_error = None
        self.last_context_window = None

    def refresh(self, force=False):
        return self.registry.refresh(force=force)

    @staticmethod
    def infer_route(text: str) -> str:
        text = (text or "").lower()
        if any(x in text for x in ("image", "screenshot", "photo", "picture", "vision")):
            return "vision"
        if any(x in text for x in ("latest", "current", "today", "recent", "research", "source", "search")):
            return "research"
        if any(x in text for x in ("code", "python", "javascript", "typescript", "debug", "bug", "compile", "android", "termux", "api")):
            return "coding"
        if any(x in text for x in ("deeply", "architecture", "reason", "analyze", "compare", "solve", "design", "plan")):
            return "reasoning"
        return "fast"

    def _score(self, model, route: str) -> int:
        caps = set(c.lower() for c in model.capabilities)
        score = 0
        if route == "vision":
            score += 100 if "vision" in caps else -100
        elif route == "coding":
            score += 50 if "coding" in caps else 0
        elif route == "reasoning":
            score += 50 if "reasoning" in caps else 0
        elif route == "research":
            score += 20 if "text" in caps else 0
        else:
            score += 10 if "text" in caps else 0
        if model.context_window:
            score += min(model.context_window // 10000, 20)
        return score

    def choose(self, text: str, route: Optional[str] = None, required_capability: Optional[str] = None):
        route = route or self.infer_route(text)
        models = self.registry.all_models()
        if not models:
            self.refresh(force=True)
            models = self.registry.all_models()
        capability = required_capability
        if capability is None:
            capability = {
                "vision": "vision",
                "coding": "coding",
                "reasoning": "reasoning",
            }.get(route)

        if capability:
            filtered = [
                m for m in models
                if capability.lower() in {c.lower() for c in m.capabilities}
            ]
            if filtered:
                models = filtered
            elif route == "vision":
                raise RuntimeError("No vision-capable model is available through Router9.")

        if not models:
            raise RuntimeError(
                "No models discovered. Configure VOID_ROUTER_BASE_URL "
                "and verify the Router9 /models endpoint."
            )

        # Router9's OpenRouter/free virtual model is intentionally preferred for
        # ordinary text. For specialist routes, choose a discovered model that
        # actually advertises the required capability.
        selected = None
        if route in {"fast", "general", "research"} and not required_capability:
            selected = next((m for m in models if m.id == Config.DEFAULT_MODEL), None)
        if selected is None:
            selected = max(models, key=lambda m: self._score(m, route))
        self.last_route = route
        self.last_model = selected.id
        self.last_provider = selected.provider
        self.last_context_window = selected.context_window
        return selected

    def chat(self, messages, model: Optional[str] = None, route: Optional[str] = None,
             stream: bool = False, tools=None, tool_choice=None, temperature: float = 0.7,
             max_tokens: Optional[int] = None, required_capability: Optional[str] = None):
        if model:
            selected = self.registry.find(model)
            if selected is None:
                self.refresh(force=True)
                selected = self.registry.find(model)
            if selected is None:
                # Accept provider:model syntax even before discovery.
                if ":" in model:
                    provider_name, raw_model = model.split(":", 1)
                    provider = self.registry.providers.get(provider_name)
                    if provider:
                        selected = ProviderModel(
                            id=raw_model, provider=provider_name,
                            capabilities=["text"]
                        )
                if selected is None:
                    raise RuntimeError(f"Model not found: {model}")
        else:
            selected = self.choose(
                next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), ""),
                route=route,
                required_capability=required_capability,
            )
        provider = self.registry.provider_for(selected)
        try:
            response = provider.chat(
                messages=messages,
                model=selected.id,
                stream=stream,
                tools=tools,
                tool_choice=tool_choice,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self.last_model = selected.id
            self.last_provider = selected.provider
            self.last_context_window = selected.context_window
            self.last_error = None
            return response
        except Exception as exc:
            self.last_error = f"{selected.provider}/{selected.id}: {exc}"
            # One fallback attempt with another discovered model.
            fallback_capability = required_capability or {
                "vision": "vision",
                "coding": "coding",
                "reasoning": "reasoning",
            }.get(route)
            candidates = [
                m for m in self.registry.all_models()
                if m.id != selected.id
                and (not fallback_capability or fallback_capability.lower() in {c.lower() for c in m.capabilities})
            ]
            if not candidates:
                raise
            fallback = max(candidates, key=lambda m: self._score(m, route or self.last_route))
            try:
                response = self.registry.provider_for(fallback).chat(
                    messages=messages, model=fallback.id, stream=stream,
                    tools=tools, tool_choice=tool_choice,
                    temperature=temperature, max_tokens=max_tokens,
                )
                self.last_model = fallback.id
                self.last_provider = fallback.provider
                self.last_context_window = fallback.context_window
                return response
            except Exception as fallback_exc:
                raise RuntimeError(
                    f"Primary model failed: {exc}; fallback failed: {fallback_exc}"
                ) from fallback_exc

    def status(self) -> Dict[str, Any]:
        return {
            "route": self.last_route,
            "model": self.last_model or "none",
            "provider": self.last_provider or "none",
            "providers": list(self.registry.providers),
            "models": [m.id for m in self.registry.all_models()],
            "model_count": len(self.registry.models),
            "provider_errors": dict(self.registry.errors),
            "error": self.last_error,
            "context_window": self.last_context_window,
        }
