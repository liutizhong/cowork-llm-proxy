"""DeepSeek official API provider."""

from __future__ import annotations

from ..config import settings
from .anthropic_compat import AnthropicCompatProvider


class DeepSeekProvider(AnthropicCompatProvider):
    _name = "DeepSeek"
    _display_prefix = "DeepSeek - "
    _default_models = [
        {"id": "deepseek-v4-flash", "owned_by": "deepseek", "provider": "deepseek", "display_name": "deepseek-v4-flash"},
        {"id": "deepseek-v4-pro",   "owned_by": "deepseek", "provider": "deepseek", "display_name": "deepseek-v4-pro"},
    ]

    def __init__(self) -> None:
        super().__init__()
        self._api_key = settings.deepseek_api_key
        self._base_url = settings.deepseek_base_url
        self._models_url = settings.deepseek_models_url

    def can_handle(self, model_id: str) -> bool:
        return model_id.lower().startswith("deepseek-")
