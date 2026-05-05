"""Anthropic Claude via AWS Bedrock with graceful degradation."""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings

logger = logging.getLogger(__name__)


def _bedrock_configured() -> bool:
    mid = (settings.bedrock_model_id or "").strip()
    ak = (settings.aws_access_key_id or "").strip()
    sk = (settings.aws_secret_access_key or "").strip()
    return bool(mid and ak and sk)


def _client():
    kwargs: dict[str, Any] = {"region_name": settings.aws_region}
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    if settings.aws_session_token:
        kwargs["aws_session_token"] = settings.aws_session_token
    return boto3.client("bedrock-runtime", **kwargs)


def invoke_claude_sonnet(
    *,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 900,
) -> tuple[str, bool]:
    """
    Returns (text, used_bedrock).
    If Bedrock is not configured or invocation fails, returns fallback message with used_bedrock=False.
    """
    if not _bedrock_configured():
        logger.warning("Bedrock not configured; skipping LLM synthesis.")
        return (
            "[Bedrock not configured] Provide AWS credentials and BEDROCK_MODEL_ID for full answers.",
            False,
        )
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    try:
        resp = _client().invoke_model(
            modelId=settings.bedrock_model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(resp["body"].read())
        parts = payload.get("content") or []
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        return (text.strip() or "(empty model response)", True)
    except (ClientError, BotoCoreError, json.JSONDecodeError, KeyError) as e:
        logger.exception("Bedrock invocation failed: %s", e)
        return (
            f"[Bedrock error] {type(e).__name__}: {e}. Showing retrieval context only.",
            False,
        )
