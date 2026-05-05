"""In-memory catalog accessors backed by JSON sample data."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _data_path(filename: str) -> Path:
    base = Path(__file__).resolve().parent.parent / "data"
    return base / filename


@lru_cache
def load_public_catalog() -> list[dict[str, Any]]:
    path = _data_path("public_catalog.json")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_member_catalog() -> list[dict[str, Any]]:
    path = _data_path("private_member_catalog.json")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def search_public_products(query: str, limit: int = 8) -> list[dict[str, Any]]:
    q = query.lower().strip()
    items = load_public_catalog()
    if not q:
        return items[:limit]
    scored: list[tuple[int, dict[str, Any]]] = []
    for p in items:
        blob = f"{p.get('name','')} {p.get('description','')} {p.get('category','')}".lower()
        score = sum(1 for w in q.split() if w and w in blob)
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:limit]]


def search_member_products(query: str, limit: int = 8) -> list[dict[str, Any]]:
    q = query.lower().strip()
    items = load_member_catalog()
    if not q:
        return items[:limit]
    scored: list[tuple[int, dict[str, Any]]] = []
    for p in items:
        blob = f"{p.get('name','')} {p.get('description','')} {p.get('category','')}".lower()
        score = sum(1 for w in q.split() if w and w in blob)
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:limit]]
