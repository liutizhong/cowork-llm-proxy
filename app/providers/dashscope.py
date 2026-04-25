"""Alibaba Cloud DashScope provider (Anthropic-compatible)."""

from __future__ import annotations

from ..config import settings
from .anthropic_compat import AnthropicCompatProvider

_DASHSCOPE_PREFIXES = ("glm-", "kimi-", "minimax-", "qwen-")


class DashScopeProvider(AnthropicCompatProvider):
    _name = "DashScope"
    _display_prefix = "Aliyun - "
    _default_models = [
        {"id": "glm-5",         "owned_by": "dashscope", "provider": "dashscope", "display_name": "GLM-5"},
        {"id": "glm-5.1",       "owned_by": "dashscope", "provider": "dashscope", "display_name": "GLM-5.1"},
        {"id": "glm-4.7",       "owned_by": "dashscope", "provider": "dashscope", "display_name": "GLM-4.7"},
        {"id": "kimi-k2.5",     "owned_by": "dashscope", "provider": "dashscope", "display_name": "Kimi K2.5"},
        {"id": "minimax-m2.5",  "owned_by": "dashscope", "provider": "dashscope", "display_name": "MiniMax M2.5"},
    ]

    def __init__(self) -> None:
        super().__init__()
        self._api_key = settings.dashscope_api_key
        self._base_url = settings.dashscope_base_url
        self._models_url = settings.dashscope_models_url

    def can_handle(self, model_id: str) -> bool:
        lower = model_id.lower()
        return any(lower.startswith(p) for p in _DASHSCOPE_PREFIXES)
