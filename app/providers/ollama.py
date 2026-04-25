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

_PREFIX = "ollama/"


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


def _to_openai_body(body: dict, stream: bool = False) -> dict:
    result: dict = {
        "model": body["model"].removeprefix(_PREFIX),
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
    @property
    def name(self) -> str:
        return "Ollama"

    @property
    def display_prefix(self) -> str:
        return "Ollama - "

    def can_handle(self, model_id: str) -> bool:
        return model_id.lower().startswith(_PREFIX)

    async def list_models(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                resp.raise_for_status()
                return [
                    {
                        "id": f"{_PREFIX}{m['name']}",
                        "owned_by": "ollama",
                        "provider": "ollama",
                        "display_name": m["name"],
                    }
                    for m in resp.json().get("models", [])
                ]
        except Exception as exc:
            logger.warning("[Ollama] list_models failed: %s", exc)
            return []

    async def forward(
        self, path: str, body: dict, headers: dict
    ) -> tuple[int, dict | None, str | None]:
        url = f"{settings.ollama_base_url}/v1/chat/completions"
        async with httpx.AsyncClient(timeout=self._timeout()) as client:
            resp = await client.post(url, json=_to_openai_body(body))
            if resp.status_code != 200:
                return resp.status_code, resp.json(), None
            return 200, _to_anthropic_response(resp.json(), body["model"]), None

    async def forward_stream(
        self, path: str, body: dict, headers: dict
    ) -> AsyncGenerator[bytes, None]:
        url = f"{settings.ollama_base_url}/v1/chat/completions"
        msg_id = f"msg_ollama_{int(time.time())}"
        model = body["model"]

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

        output_tokens = 0
        async with httpx.AsyncClient(timeout=self._timeout()) as client:
            async with client.stream("POST", url, json=_to_openai_body(body, stream=True)) as resp:
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

        yield _sse("content_block_stop", {"type": "content_block_stop", "index": 0})
        yield _sse("message_delta", {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": output_tokens},
        })
        yield _sse("message_stop", {"type": "message_stop"})

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(settings.timeout, connect=10)
