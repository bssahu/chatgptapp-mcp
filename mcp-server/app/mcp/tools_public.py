"""Public MCP tools (no authentication)."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.shopping_agent import answer_public_question
from app.api.mock_catalog_api import search_public_products
from app.config import settings
from app.vector.qdrant_client import search_collection

logger = logging.getLogger(__name__)


async def search_public_catalog(query: str) -> dict[str, Any]:
    """
    Search the public product catalog JSON and the public Qdrant documentation index.

    Returns product name, description, price, image URL, and whether the hit came from catalog or vector search.
    """
    catalog_hits = search_public_products(query, limit=8)
    vec_hits = await search_collection(
        collection=settings.qdrant_public_collection,
        query=query,
        limit=5,
    )
    catalog_rows: list[dict[str, Any]] = []
    for p in catalog_hits:
        catalog_rows.append(
            {
                "product_id": p.get("product_id"),
                "name": p.get("name"),
                "description": p.get("description"),
                "price": p.get("price"),
                "category": p.get("category"),
                "public_image_url": p.get("public_image_url"),
                "availability": p.get("availability"),
                "source": "public_catalog_json",
            }
        )
    vector_rows: list[dict[str, Any]] = []
    for h in vec_hits:
        vector_rows.append(
            {
                "title": h.get("title"),
                "source": h.get("source"),
                "score": h.get("score"),
                "excerpt": (h.get("text") or "")[:400],
                "source_layer": "qdrant_public_docs",
            }
        )
    return {
        "query": query,
        "catalog_matches": catalog_rows,
        "documentation_matches": vector_rows,
    }


async def ask_public_product_question(question: str) -> dict[str, Any]:
    """
    Answer general shopping or product policy questions using Claude Sonnet on Bedrock with retrieval
    from the public Qdrant index. If Bedrock is not configured, returns retrieval-only context with a warning.
    """
    return await answer_public_question(question)
