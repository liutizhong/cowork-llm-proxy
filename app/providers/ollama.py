"""Local Ollama provider — translates Anthropic Messages API ↔ OpenAI-compat format."""

from __future__ import annotations

import json
import logging
import time
from typing import AsyncGenerator

import httpx

from ..config import settings
from .base import BaseProvider

logger = logging.getLogger(__name__)

_PREFIX = "ollama-"


def _safe_model_id(name: str) -> str:
    """Convert Ollama model name to a URL-safe proxy ID.

    e.g. llama3.2:latest → ollama-llama3-2-latest
    Replaces '/', ':', and '.' with '-' to avoid URL parsing issues.
    The original name is preserved in OllamaProvider._id_to_name for routing.
    """
    safe = name.replace("/", "-").replace(":", "-").replace(".", "-")
    return f"{_PREFIX}{safe}"


def _to_openai_messages(body: dict) -> list[dict]:
    messages = []
    if body.get("system"):
        system = body["system"]
        if isinstance(system, list):
            system = " ".join(b.get("text", "") for b in system if b.get("type") == "text")
        messages.append({"role": "system", "content": system})
    for msg in body.get("messages", []):
        content = msg["content"]
        if isinstance(content, list):
            content = "".join(b.get("text", "") for b in content if b.get("type") == "text")
        messages.append({"role": msg["role"], "content": content})
    return messages


def _to_openai_body(body: dict, ollama_name: str, stream: bool = False) -> dict:
    result: dict = {
        "model": ollama_name,
        "messages": _to_openai_messages(body),
        "stream": stream,
    }
    if body.get("max_tokens"):
        result["max_tokens"] = body["max_tokens"]
    if body.get("temperature") is not None:
        result["temperature"] = body["temperature"]
    if body.get("top_p") is not None:
        result["top_p"] = body["top_p"]
    return result


def _to_anthropic_response(data: dict, model: str) -> dict:
    choice = data["choices"][0]
    content = choice["message"].get("content") or ""
    usage = data.get("usage", {})
    finish = choice.get("finish_reason", "stop")
    return {
        "id": data.get("id", f"msg_ollama_{int(time.time())}"),
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": content}],
        "stop_reason": "end_turn" if finish == "stop" else "max_tokens",
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
    }


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


class OllamaProvider(BaseProvider):
    def __init__(self) -> None:
        # Maps safe proxy ID → original Ollama model name
        self._id_to_name: dict[str, str] = {}

    @property
    def name(self) -> str:
        return "Ollama"

    @property
    def display_prefix(self) -> str:
        return "Ollama - "

    def can_handle(self, model_id: str) -> bool:
        return model_id.lower().startswith(_PREFIX)

    async def _resolve_name(self, model_id: str) -> str:
        """Return original Ollama model name for a safe proxy ID.

        Refreshes the id→name map from Ollama if the model isn't cached yet.
        """
        if model_id not in self._id_to_name:
            await self.list_models()
        return self._id_to_name.get(model_id, model_id.removeprefix(_PREFIX))

    async def list_models(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                resp.raise_for_status()
                models = []
                for m in resp.json().get("models", []):
                    safe_id = _safe_model_id(m["name"])
                    self._id_to_name[safe_id] = m["name"]
                    models.append({
                        "id": safe_id,
                        "owned_by": "ollama",
                        "provider": "ollama",
                        "display_name": m["name"],
                    })
                return models
        except Exception as exc:
            logger.warning("[Ollama] list_models failed: %s", exc)
            return []

    async def forward(
        self, path: str, body: dict, headers: dict
    ) -> tuple[int, dict | None, str | None]:
        url = f"{settings.ollama_base_url}/v1/chat/completions"
        model = body["model"]
        ollama_name = self._id_to_name.get(model, model.removeprefix(_PREFIX))
        async with httpx.AsyncClient(timeout=self._timeout()) as client:
            resp = await client.post(url, json=_to_openai_body(body, ollama_name))
            if resp.status_code != 200:
                return resp.status_code, resp.json(), None
            return 200, _to_anthropic_response(resp.json(), body["model"]), None

    async def forward_stream(
        self, path: str, body: dict, headers: dict
    ) -> AsyncGenerator[bytes, None]:
        url = f"{settings.ollama_base_url}/v1/chat/completions"
        msg_id = f"msg_ollama_{int(time.time())}"
        model = body["model"]

        # Resolve the name outside the generator body to avoid nested async HTTP
        # calls inside an async generator, which can interfere with httpx's
        # connection pool and trigger unexpected TLS upgrade attempts.
        ollama_name = self._id_to_name.get(model, model.removeprefix(_PREFIX))

        output_tokens = 0
        try:
            async with httpx.AsyncClient(timeout=self._timeout()) as client:
                async with client.stream(
                    "POST", url, json=_to_openai_body(body, ollama_name, stream=True)
                ) as resp:
                    if resp.status_code != 200:
                        err_text = await resp.aread()
                        logger.error("[Ollama] stream error %s: %s", resp.status_code, err_text)
                        yield _sse("error", {
                            "type": "error",
                            "error": {"type": "api_error", "message": f"Ollama returned {resp.status_code}"},
                        })
                        return

                    # Only yield the opening events once we know Ollama accepted the request.
                    yield _sse("message_start", {
                        "type": "message_start",
                        "message": {
                            "id": msg_id, "type": "message", "role": "assistant",
                            "content": [], "model": model, "stop_reason": None,
                            "usage": {"input_tokens": 0, "output_tokens": 0},
                        },
                    })
                    yield _sse("content_block_start", {
                        "type": "content_block_start", "index": 0,
                        "content_block": {"type": "text", "text": ""},
                    })
                    yield _sse("ping", {"type": "ping"})

                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            chunk = json.loads(payload)
                            text = chunk["choices"][0].get("delta", {}).get("content") or ""
                            if text:
                                output_tokens += 1
                                yield _sse("content_block_delta", {
                                    "type": "content_block_delta", "index": 0,
                                    "delta": {"type": "text_delta", "text": text},
                                })
                        except Exception:
                            continue

        except Exception as exc:
            logger.error("[Ollama] forward_stream failed: %s", exc)
            yield _sse("error", {
                "type": "error",
                "error": {"type": "api_error", "message": f"Ollama connection failed: {exc}"},
            })
            return

        yield _sse("content_block_stop", {"type": "content_block_stop", "index": 0})
        yield _sse("message_delta", {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": output_tokens},
        })
        yield _sse("message_stop", {"type": "message_stop"})

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(settings.timeout, connect=30)
