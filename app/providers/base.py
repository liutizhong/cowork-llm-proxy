"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncGenerator


class BaseProvider(ABC):
    """A provider wraps one upstream Anthropic-compatible API.

    Each concrete provider handles:
    - Routing (deciding whether it owns a given model ID)
    - Model listing (fetching from the upstream /models endpoint)
    - Request forwarding (proxying /v1/messages with its own API key)
    """

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name (e.g. 'DeepSeek', 'DashScope')."""

    @property
    @abstractmethod
    def display_prefix(self) -> str:
        """Prefix prepended to display_name in /v1/models (e.g. 'DeepSeek - ')."""

    # ── Routing ───────────────────────────────────────────────────────────────

    @abstractmethod
    def can_handle(self, model_id: str) -> bool:
        """Return True if this provider should serve requests for model_id."""

    # ── Model listing ─────────────────────────────────────────────────────────

    @abstractmethod
    async def list_models(self) -> list[dict]:
        """Return raw model dicts from the upstream API (with 5-min cache)."""

    # ── Request forwarding ────────────────────────────────────────────────────

    @abstractmethod
    async def forward(
        self, path: str, body: dict, headers: dict
    ) -> tuple[int, dict | None, str | None]:
        """Forward a non-streaming request.

        Returns (status_code, json_body, None).
        """

    @abstractmethod
    async def forward_stream(
        self, path: str, body: dict, headers: dict
    ) -> AsyncGenerator[bytes, None]:
        """Forward a streaming request; yield raw SSE bytes from upstream."""
