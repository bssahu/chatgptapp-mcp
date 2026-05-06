"""Auth helpers for MCP private tools."""

from __future__ import annotations

from urllib.parse import urlencode
from typing import Any

from app.auth.context import current_access_token
from app.auth.session_store import get_session_by_access_token
from app.config import settings


def auth_required_payload() -> dict[str, Any]:
    base = settings.public_base_url.rstrip("/")
    query = urlencode(
        {
            "response_type": "code",
            "client_id": settings.mock_oauth_client_id,
            "redirect_uri": f"{base}/auth/callback",
            "scope": "profile orders:read catalog:member:read",
        }
    )
    return {
        "requires_auth": True,
        "auth_url": f"{base}/auth/authorize?{query}",
        "message": (
            "Please authenticate to access order status or member-only catalog."
        ),
    }


async def resolve_access_token(explicit_token: str | None) -> str | None:
    if explicit_token:
        return explicit_token.strip() or None
    return current_access_token.get()


async def get_session_or_auth_payload(
    explicit_access_token: str | None,
) -> dict[str, Any]:
    """Returns session document or auth-required payload dict."""
    token = await resolve_access_token(explicit_access_token)
    if not token:
        return auth_required_payload()
    session = await get_session_by_access_token(token)
    if not session:
        return auth_required_payload()
    return session
