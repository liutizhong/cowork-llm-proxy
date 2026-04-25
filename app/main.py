"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import AuthMiddleware
from .config import settings
from .providers import build_registry
from .api import messages, models

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry = build_registry()
    app.state.registry = registry

    provider_names = [p.name for p in registry._providers]
    if not provider_names:
        logger.warning("No providers enabled. Set ENABLE_DEEPSEEK or ENABLE_DASHSCOPE.")
    else:
        logger.info("Providers: %s", ", ".join(provider_names))

    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="LLM Proxy",
    version="1.0.0",
    description="Lightweight Anthropic-compatible proxy for DeepSeek and Aliyun DashScope.",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)

app.include_router(messages.router, prefix="/v1", tags=["messages"])
app.include_router(models.router,   prefix="/v1", tags=["models"])


@app.get("/health", tags=["health"])
async def health():
    providers = [p.name for p in app.state.registry._providers]
    return {"status": "ok", "providers": providers}


@app.get("/", tags=["health"])
async def root():
    return {
        "name": "LLM Proxy",
        "version": "1.0.0",
        "endpoints": {
            "messages": "/v1/messages",
            "models":   "/v1/models",
            "health":   "/health",
            "docs":     "/docs",
        },
    }
