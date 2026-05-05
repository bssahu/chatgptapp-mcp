"""Mock order API using orders.json."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _orders_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "orders.json"


@lru_cache
def load_orders() -> list[dict[str, Any]]:
    path = _orders_path()
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def get_order(user_id: str, order_id: str) -> dict[str, Any] | None:
    for o in load_orders():
        if o.get("order_id") == order_id and o.get("user_id") == user_id:
            return o
    return None
