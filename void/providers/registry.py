"""Provider and model registry for dynamic VOID model discovery."""

from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional

from .openai_compatible import OpenAICompatibleProvider, ProviderModel


class ProviderRegistry:
    def __init__(self, providers: Optional[List[OpenAICompatibleProvider]] = None):
        self.providers: Dict[str, OpenAICompatibleProvider] = {p.name: p for p in (providers or [])}
        self.models: Dict[str, ProviderModel] = {}
        self.static_models: Dict[str, ProviderModel] = {}
        self.last_refresh = 0.0
        self.errors: Dict[str, str] = {}
        self._lock = threading.RLock()

    def add(self, provider: OpenAICompatibleProvider) -> None:
        if not isinstance(provider, OpenAICompatibleProvider):
            raise TypeError("provider must be an OpenAICompatibleProvider")
        with self._lock:
            self.providers[provider.name] = provider

    def refresh(self, force: bool = False) -> List[ProviderModel]:
        with self._lock:
            if not force and self.last_refresh and time.time() - self.last_refresh < 30:
                return list(self.models.values())
            discovered: Dict[str, ProviderModel] = dict(self.static_models)
            errors: Dict[str, str] = {}
            for provider in list(self.providers.values()):
                if not provider.configured:
                    continue
                try:
                    for model in provider.list_models():
                        discovered[f"{model.provider}:{model.id}"] = model
                except Exception as exc:
                    errors[provider.name] = f"{type(exc).__name__}: {exc}"
            self.models = discovered
            self.errors = errors
            self.last_refresh = time.time()
            return list(self.models.values())

    def add_static(self, model: ProviderModel) -> None:
        if not isinstance(model, ProviderModel):
            raise TypeError("model must be a ProviderModel")
        with self._lock:
            key = f"{model.provider}:{model.id}"
            self.static_models[key] = model
            self.models[key] = model

    def all_models(self) -> List[ProviderModel]:
        with self._lock:
            return list(self.models.values())

    def find(self, model_id: str) -> Optional[ProviderModel]:
        if not isinstance(model_id, str) or not model_id.strip():
            return None
        with self._lock:
            for model in self.models.values():
                if model.id == model_id or f"{model.provider}:{model.id}" == model_id:
                    return model
        return None

    def provider_for(self, model: ProviderModel) -> OpenAICompatibleProvider:
        if not isinstance(model, ProviderModel):
            raise TypeError("model must be a ProviderModel")
        with self._lock:
            try:
                return self.providers[model.provider]
            except KeyError as exc:
                raise RuntimeError(f"No provider registered for model '{model.provider}:{model.id}'") from exc
