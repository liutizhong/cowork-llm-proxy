"""POST /v1/messages — proxy to the appropriate provider."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _err(status: int, type_: str, msg: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"type": "error", "error": {"type": type_, "message": msg}},
    )


@router.post("/messages/count_tokens")
async def count_tokens(request: Request):
    """Stub token counter — estimates ~4 chars per token."""
    try:
        body: dict = await request.json()
    except Exception:
        return _err(400, "invalid_request_error", "Request body must be valid JSON.")

    total_chars = 0
    system = body.get("system", "")
    if isinstance(system, str):
        total_chars += len(system)
    elif isinstance(system, list):
        total_chars += sum(len(b.get("text", "")) for b in system if b.get("type") == "text")
    for msg in body.get("messages", []):
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            total_chars += sum(len(b.get("text", "")) for b in content if b.get("type") == "text")

    return JSONResponse(content={"input_tokens": max(1, total_chars // 4)})


@router.post("/messages")
async def create_message(request: Request):
    try:
        body: dict = await request.json()
    except Exception:
        return _err(400, "invalid_request_error", "Request body must be valid JSON.")

    model = body.get("model", "")
    if not model:
        return _err(400, "invalid_request_error", "Missing required field: model.")

    registry = request.app.state.registry
    try:
        provider = registry.route(model)
    except ValueError as exc:
        logger.warning("No provider for model %r — %s", model, exc)
        return _err(404, "not_found_error", str(exc))

    client_headers = dict(request.headers)
    is_stream = bool(body.get("stream", False))

    logger.info("[%s] model=%s stream=%s", provider.name, model, is_stream)

    if is_stream:
        return StreamingResponse(
            provider.forward_stream("/v1/messages", body, client_headers),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    status, json_body, _ = await provider.forward("/v1/messages", body, client_headers)
    return JSONResponse(content=json_body, status_code=status)
