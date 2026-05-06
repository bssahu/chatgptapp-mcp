"""MongoDB-backed OAuth codes, sessions, and access tokens."""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


def get_db() -> AsyncIOMotorDatabase:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_uri)
    return _client[settings.mongodb_db]


async def ensure_indexes() -> None:
    db = get_db()
    await db.oauth_codes.create_index("code", unique=True)
    await db.oauth_codes.create_index("expires_at", expireAfterSeconds=0)
    await db.sessions.create_index("session_id", unique=True)
    await db.sessions.create_index("access_token", unique=True)
    await db.sessions.create_index("expires_at", expireAfterSeconds=0)


async def store_oauth_code(
    *,
    code: str,
    user_id: str,
    redirect_uri: str,
    client_id: str,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
    ttl_seconds: int = 600,
) -> None:
    db = get_db()
    now = datetime.now(tz=UTC)
    doc = {
        "code": code,
        "user_id": user_id,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "created_at": now,
        "expires_at": now + timedelta(seconds=ttl_seconds),
    }
    await db.oauth_codes.insert_one(doc)


async def consume_oauth_code(code: str) -> dict[str, Any] | None:
    db = get_db()
    doc = await db.oauth_codes.find_one_and_delete({"code": code})
    if not doc:
        return None
    return doc


async def create_session(
    *,
    user_id: str,
    ttl_seconds: int = 86400,
) -> tuple[str, str, datetime]:
    """Returns session_id, access_token, expires_at."""
    db = get_db()
    session_id = secrets.token_urlsafe(32)
    access_token = secrets.token_urlsafe(48)
    now = datetime.now(tz=UTC)
    expires_at = now + timedelta(seconds=ttl_seconds)
    await db.sessions.insert_one(
        {
            "session_id": session_id,
            "user_id": user_id,
            "access_token": access_token,
            "created_at": now,
            "expires_at": expires_at,
        }
    )
    return session_id, access_token, expires_at


async def get_session_by_access_token(access_token: str) -> dict[str, Any] | None:
    if not access_token:
        return None
    db = get_db()
    doc = await db.sessions.find_one({"access_token": access_token})
    if not doc:
        return None
    exp: datetime | None = doc.get("expires_at")
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)
    if exp and exp < datetime.now(tz=UTC):
        await db.sessions.delete_one({"_id": doc["_id"]})
        return None
    return doc


async def get_session_by_session_id(session_id: str) -> dict[str, Any] | None:
    if not session_id:
        return None
    db = get_db()
    doc = await db.sessions.find_one({"session_id": session_id})
    if not doc:
        return None
    exp: datetime | None = doc.get("expires_at")
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)
    if exp and exp < datetime.now(tz=UTC):
        await db.sessions.delete_one({"_id": doc["_id"]})
        return None
    return doc


async def delete_session_by_access_token(access_token: str) -> bool:
    db = get_db()
    res = await db.sessions.delete_one({"access_token": access_token})
    return res.deleted_count > 0


async def delete_session_by_session_id(session_id: str) -> bool:
    db = get_db()
    res = await db.sessions.delete_one({"session_id": session_id})
    return res.deleted_count > 0
