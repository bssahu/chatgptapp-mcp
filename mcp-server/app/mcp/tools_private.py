"""Authenticated MCP tools."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.shopping_agent import answer_private_member_question as run_private_rag
from app.api.mock_catalog_api import search_member_products
from app.api.mock_order_api import get_order
from app.auth.decorators import get_session_or_auth_payload
from app.config import settings
from app.vector.qdrant_client import search_collection

logger = logging.getLogger(__name__)


async def get_order_status(
    user_id: str,
    order_id: str,
    access_token: str | None = None,
) -> dict[str, Any]:
    """
    Fetch order status for the authenticated shopper using mock order APIs.

    Requires OAuth2 session. Pass `access_token` if your MCP client cannot send Authorization headers.
    The authenticated user must match `user_id`.
    """
    sess = await get_session_or_auth_payload(access_token)
    if sess.get("requires_auth"):
        return sess
    session_uid = str(sess.get("user_id"))
    if session_uid != user_id.strip():
        return {
            "error": "user_mismatch",
            "message": (
                f"Authenticated user is {session_uid} but request referenced {user_id}."
            ),
        }
    order = get_order(session_uid, order_id.strip())
    if not order:
        return {"error": "not_found", "order_id": order_id, "user_id": session_uid}
    return {
        "order_id": order.get("order_id"),
        "user_id": order.get("user_id"),
        "status": order.get("status"),
        "delivery_eta": order.get("delivery_eta"),
        "tracking_url": order.get("tracking_url"),
        "items": order.get("items"),
        "placed_at": order.get("placed_at"),
    }


async def search_member_catalog(query: str, access_token: str | None = None) -> dict[str, Any]:
    """
    Search member-only catalog JSON and the private Qdrant documentation index.

    Requires OAuth2 session (Bearer token recommended).
    """
    sess = await get_session_or_auth_payload(access_token)
    if sess.get("requires_auth"):
        return sess
    member_hits = search_member_products(query, limit=8)
    vec_hits = await search_collection(
        collection=settings.qdrant_private_collection,
        query=query,
        limit=5,
    )
    rows = []
    for p in member_hits:
        rows.append(
            {
                "product_id": p.get("product_id"),
                "name": p.get("name"),
                "description": p.get("description"),
                "member_price": p.get("member_price"),
                "msrp": p.get("msrp"),
                "category": p.get("category"),
                "public_image_url": p.get("public_image_url"),
                "availability": p.get("availability"),
                "source": "member_catalog_json",
            }
        )
    docs = []
    for h in vec_hits:
        docs.append(
            {
                "title": h.get("title"),
                "source": h.get("source"),
                "score": h.get("score"),
                "excerpt": (h.get("text") or "")[:400],
                "source_layer": "qdrant_private_docs",
            }
        )
    return {
        "authenticated_user": sess.get("user_id"),
        "query": query,
        "member_catalog_matches": rows,
        "documentation_matches": docs,
    }


async def ask_private_member_question(
    question: str,
    access_token: str | None = None,
) -> dict[str, Any]:
    """
    Members-only assistant using Claude Sonnet on Bedrock over the private Qdrant index.

    Requires OAuth2 session. Pass `access_token` when clients cannot attach Authorization headers.
    """
    sess = await get_session_or_auth_payload(access_token)
    if sess.get("requires_auth"):
        return sess
    ans = await run_private_rag(question)
    ans["authenticated_user"] = sess.get("user_id")
    return ans
