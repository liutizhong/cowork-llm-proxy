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
