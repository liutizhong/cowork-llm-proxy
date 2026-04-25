"""GET /v1/models and GET /v1/models/{model_id}."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..config import settings

router = APIRouter()


@router.get("/models")
async def list_models(request: Request):
    registry = request.app.state.registry
    models = await registry.list_all_models()

    if settings.allowed_models:
        allowed = set(settings.allowed_models)
        models = [m for m in models if m["id"] in allowed]

    return {"object": "list", "data": models, "has_more": False}


@router.get("/models/{model_id:path}")
async def get_model(model_id: str, request: Request):
    registry = request.app.state.registry
    models = await registry.list_all_models()

    for m in models:
        if m["id"] == model_id:
            return m

    return JSONResponse(
        status_code=404,
        content={"type": "error", "error": {"type": "not_found_error", "message": f"Model '{model_id}' not found."}},
    )
