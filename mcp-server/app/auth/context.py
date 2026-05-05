"""Request-scoped auth token for MCP tool handlers (set by ASGI middleware)."""

from __future__ import annotations

import contextvars

current_access_token: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_access_token", default=None
)


def set_access_token(token: str | None) -> contextvars.Token:
    return current_access_token.set(token)


def reset_access_token(token_ctx: contextvars.Token) -> None:
    current_access_token.reset(token_ctx)
