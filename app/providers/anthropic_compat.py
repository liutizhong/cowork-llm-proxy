"""Generic Anthropic-compatible provider — reused by DeepSeek and DashScope.

Handles:
- Pure HTTP proxy (no SDK, no re-serialization)
- Model list fetched from an OpenAI-compatible /models endpoint
- 5-minute in-memory cache for model lists
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import AsyncGenerator

import httpx

from .base import BaseProvider

logger = logging.getLogger(__name__)

_MODEL_CACHE_TTL = 300  # seconds


class AnthropicCompatProvider(BaseProvider):
    """Proxy requests to any Anthropic-compatible upstream API.

    Subclasses only need to set class attributes and override `can_handle`.
    No extra code required.
    """

    # Subclasses override these:
    _name: str = ""
    _display_prefix: str = ""
    _base_url: str = ""          # e.g. https://api.deepseek.com/anthropic
    _api_key: str = ""
    _models_url: str = ""        # OpenAI-compat /models endpoint
    _default_models: list[dict] = []

    def __init__(self) -> None:
        self._cache: list[dict] | None = None
        self._cache_ts: float = 0.0
        self._lock = asyncio.Lock()

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._name

    @property
    def display_prefix(self) -> str:
        return self._display_prefix

    # ── Model listing ─────────────────────────────────────────────────────────

    async def list_models(self) -> list[dict]:
        async with self._lock:
            if self._cache is not None and (time.time() - self._cache_ts) < _MODEL_CACHE_TTL:
                return self._cache
            models = await self._fetch_models()
            self._cache = models
            self._cache_ts = time.time()
            return models

    async def _fetch_models(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    self._models_url,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                resp.raise_for_status()
                data = resp.json().get("data", [])
                if data:
                    logger.info("[%s] Fetched %d models", self.name, len(data))
                    return [
                        {
                            "id": m["id"],
                            "owned_by": m.get("owned_by", self.name.lower()),
                            "provider": self.name.lower(),
                            "display_name": m.get("display_name", m["id"]),
                        }
                        for m in data
                        if m.get("id")
                    ]
        except Exception as exc:
            logger.warning("[%s] Model fetch failed (%s), using defaults", self.name, exc)
        return list(self._default_models)

    # ── Request forwarding ────────────────────────────────────────────────────

    def _upstream_headers(self, client_headers: dict) -> dict:
        """Build headers for the upstream request."""
        forwarded = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        # Forward Anthropic-specific headers the client sent
        for key in ("anthropic-version", "anthropic-beta"):
            if key in client_headers:
                forwarded[key] = client_headers[key]
        return forwarded

    def _upstream_url(self, path: str) -> str:
        base = self._base_url.rstrip("/")
        return f"{base}{path}"

    async def forward(
        self, path: str, body: dict, headers: dict
    ) -> tuple[int, dict | None, str | None]:
        url = self._upstream_url(path)
        async with httpx.AsyncClient(timeout=self._timeout()) as client:
            resp = await client.post(url, json=body, headers=self._upstream_headers(headers))
            return resp.status_code, resp.json(), None

    async def forward_stream(
        self, path: str, body: dict, headers: dict
    ) -> AsyncGenerator[bytes, None]:
        url = self._upstream_url(path)
        async with httpx.AsyncClient(timeout=self._timeout()) as client:
            async with client.stream(
                "POST", url, json=body, headers=self._upstream_headers(headers)
            ) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk

    def _timeout(self) -> httpx.Timeout:
        from ..config import settings
        return httpx.Timeout(settings.timeout, connect=10)
