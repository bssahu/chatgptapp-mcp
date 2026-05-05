"""ASGI entrypoint: FastAPI + OAuth routes + mounted FastMCP HTTP server."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.auth.context import reset_access_token, set_access_token
from app.auth.oauth import router as oauth_router
from app.auth import session_store
from app.mcp.server import mcp
from app.utils.logging import configure_logging
from app.vector.qdrant_client import ensure_collections

configure_logging()
logger = logging.getLogger(__name__)

mcp_http_app = mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await session_store.ensure_indexes()
    await ensure_collections()
    async with mcp_http_app.lifespan(app):
        yield


app = FastAPI(
    title="Shopping MCP Server",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(oauth_router)


@app.middleware("http")
async def bearer_token_context_middleware(request: Request, call_next):
    """Expose Authorization bearer (and optional query token) to MCP tool handlers."""
    token: str | None = None
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(None, 1)[1].strip() or None
    if not token:
        token = request.query_params.get("access_token")
    ctx = set_access_token(token)
    try:
        return await call_next(request)
    finally:
        reset_access_token(ctx)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> JSONResponse:
    return JSONResponse(
        {
            "service": "shopping-mcp-server",
            "mcp_mount": "/mcp",
            "health": "/health",
            "oauth_login": "/auth/login",
            "note": "Mount exposes Streamable HTTP MCP at /mcp (see FastMCP docs).",
        }
    )


app.mount("/mcp", mcp_http_app)
