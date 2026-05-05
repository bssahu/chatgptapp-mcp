"""Qdrant vector search helpers for public and private doc collections."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import settings

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None
_embed_model = None


def get_qdrant() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url, prefer_grpc=False)
    return _client


def _get_embedder():
    global _embed_model
    if _embed_model is None:
        from fastembed import TextEmbedding

        _embed_model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _embed_model


def embed_query(text: str) -> list[float]:
    """Blocking embedding call — run via asyncio.to_thread from async tools."""
    model = _get_embedder()
    vectors = list(model.embed(text))
    return vectors[0].tolist()


async def search_collection(
    *,
    collection: str,
    query: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    if not query.strip():
        return []

    def _run() -> list[dict[str, Any]]:
        vec = embed_query(query)
        client = get_qdrant()
        res = client.query_points(
            collection_name=collection,
            query=vec,
            limit=limit,
            with_payload=True,
        )
        out: list[dict[str, Any]] = []
        for h in res.points or []:
            payload = h.payload or {}
            out.append(
                {
                    "score": float(h.score or 0.0),
                    "title": payload.get("title"),
                    "source": payload.get("source"),
                    "text": payload.get("text"),
                    "visibility": payload.get("visibility"),
                }
            )
        return out

    return await asyncio.to_thread(_run)


async def ensure_collections(vector_size: int = 384) -> None:
    """Create collections if missing (idempotent)."""

    def _run() -> None:
        client = get_qdrant()
        for name in (
            settings.qdrant_public_collection,
            settings.qdrant_private_collection,
        ):
            try:
                client.get_collection(name)
            except Exception:
                logger.info("Creating Qdrant collection %s", name)
                client.create_collection(
                    collection_name=name,
                    vectors_config=qmodels.VectorParams(
                        size=vector_size,
                        distance=qmodels.Distance.COSINE,
                    ),
                )

    await asyncio.to_thread(_run)
