"""API key authentication middleware."""

from __future__ import annotations

import hmac
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings

logger = logging.getLogger(__name__)

_SKIP_PATHS = {"/health", "/"}


def _error(msg: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"type": "error", "error": {"type": "authentication_error", "message": msg}},
    )


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.require_auth or request.url.path in _SKIP_PATHS:
            return await call_next(request)

        # Accept x-api-key OR Authorization: Bearer <key>
        key = request.headers.get("x-api-key") or _bearer(request)

        if not key:
            return _error("Missing API key. Provide x-api-key header or Authorization: Bearer <key>.")

        if not hmac.compare_digest(key, settings.api_key):
            logger.warning("Invalid API key from %s", request.client)
            return _error("Invalid API key.")

        return await call_next(request)


def _bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None
