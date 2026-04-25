"""Provider registry — routes requests to the correct upstream provider."""

from __future__ import annotations

import logging

from ..config import settings
from .base import BaseProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Maintains ordered list of enabled providers.

    Routing: first provider whose `can_handle(model_id)` returns True wins.
    If no provider claims the model, raises ValueError.
    """

    def __init__(self) -> None:
        self._providers: list[BaseProvider] = []

    def register(self, provider: BaseProvider) -> None:
        self._providers.append(provider)
        logger.info("[Registry] Registered provider: %s", provider.name)

    def route(self, model_id: str) -> BaseProvider:
        for p in self._providers:
            if p.can_handle(model_id):
                return p
        names = [p.name for p in self._providers]
        raise ValueError(
            f"No provider can handle model '{model_id}'. "
            f"Enabled providers: {names}"
        )

    async def list_all_models(self) -> list[dict]:
        """Merge model lists from all providers, deduplicated by ID."""
        seen: set[str] = set()
        result: list[dict] = []
        for provider in self._providers:
            try:
                for m in await provider.list_models():
                    if m["id"] not in seen:
                        seen.add(m["id"])
                        result.append({
                            "type": "model",
                            "id": m["id"],
                            "display_name": f"{provider.display_prefix}{m.get('display_name', m['id'])}",
                            "created_at": "2024-01-01T00:00:00Z",
                            "provider": m.get("provider", provider.name.lower()),
                            "owned_by": m.get("owned_by", provider.name.lower()),
                        })
            except Exception as exc:
                logger.error("[Registry] list_models failed for %s: %s", provider.name, exc)
        return result


def build_registry() -> ProviderRegistry:
    """Instantiate enabled providers and return a configured registry."""
    from .deepseek import DeepSeekProvider
    from .dashscope import DashScopeProvider

    registry = ProviderRegistry()

    if settings.enable_deepseek and settings.deepseek_api_key:
        registry.register(DeepSeekProvider())

    if settings.enable_dashscope and settings.dashscope_api_key:
        registry.register(DashScopeProvider())

    return registry
