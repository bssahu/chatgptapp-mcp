"""Ingest markdown files into the private member Qdrant collection."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from qdrant_client.http import models as qmodels

from app.config import settings
from app.vector.qdrant_client import embed_query, ensure_collections, get_qdrant

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _read_docs(folder: Path) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for p in sorted(folder.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        rows.append((p.name, str(p), text))
    return rows


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        default=str(Path(__file__).resolve().parent.parent / "data" / "private_docs"),
    )
    args = parser.parse_args()
    folder = Path(args.data_dir)
    await ensure_collections()
    docs = _read_docs(folder)
    if not docs:
        logger.error("No markdown files in %s", folder)
        sys.exit(1)

    client = get_qdrant()
    coll = settings.qdrant_private_collection
    points: list[qmodels.PointStruct] = []
    for i, (title, source, text) in enumerate(docs):
        vec = embed_query(text[:8000])
        pid = i + 1
        points.append(
            qmodels.PointStruct(
                id=pid,
                vector=vec,
                payload={
                    "title": title,
                    "source": source,
                    "text": text,
                    "visibility": "private_member",
                },
            )
        )
    client.upsert(collection_name=coll, points=points)
    logger.info("Uploaded %s points to %s", len(points), coll)


if __name__ == "__main__":
    asyncio.run(main())
