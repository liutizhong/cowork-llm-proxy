from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "populate_by_name": True, "extra": "ignore"}

    # ── Proxy auth ────────────────────────────────────────────────────────────
    api_key: str = Field(alias="API_KEY")
    require_auth: bool = Field(default=True, alias="REQUIRE_AUTH")

    # ── DeepSeek ──────────────────────────────────────────────────────────────
    enable_deepseek: bool = Field(default=False, alias="ENABLE_DEEPSEEK")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    # Anthropic-compatible inference endpoint
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com/anthropic", alias="DEEPSEEK_BASE_URL"
    )
    # OpenAI-compatible model list endpoint
    deepseek_models_url: str = Field(
        default="https://api.deepseek.com/models", alias="DEEPSEEK_MODELS_URL"
    )

    # ── DashScope (Aliyun) ────────────────────────────────────────────────────
    enable_dashscope: bool = Field(default=False, alias="ENABLE_DASHSCOPE")
    dashscope_api_key: str = Field(default="", alias="DASHSCOPE_API_KEY")
    dashscope_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/apps/anthropic",
        alias="DASHSCOPE_BASE_URL",
    )
    dashscope_models_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1/models",
        alias="DASHSCOPE_MODELS_URL",
    )

    # ── Ollama (local) ────────────────────────────────────────────────────────
    enable_ollama: bool = Field(default=False, alias="ENABLE_OLLAMA")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")

    # ── Model allowlist ───────────────────────────────────────────────────────
    # Comma-separated string. Empty = expose all models.
    # Example: ALLOWED_MODELS=deepseek-v4-pro,glm-5
    # Stored as str to avoid pydantic-settings v2 JSON-parsing CSV before validators run.
    allowed_models_raw: str = Field(default="", alias="ALLOWED_MODELS")

    @property
    def allowed_models(self) -> list[str]:
        v = self.allowed_models_raw.strip()
        return [m.strip() for m in v.split(",") if m.strip()] if v else []

    # ── Server ────────────────────────────────────────────────────────────────
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    workers: int = Field(default=2, alias="WORKERS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    timeout: int = Field(default=300, alias="TIMEOUT")


settings = Settings()
