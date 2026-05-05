"""RAG-style answers for public vs private shopping questions."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.bedrock_client import invoke_claude_sonnet
from app.config import settings
from app.vector.qdrant_client import search_collection

logger = logging.getLogger(__name__)


def _format_context(chunks: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for i, c in enumerate(chunks, start=1):
        title = c.get("title") or "Doc"
        src = c.get("source") or ""
        text = (c.get("text") or "").strip()
        lines.append(f"[{i}] {title} ({src})\n{text}")
    return "\n\n".join(lines)


async def answer_public_question(question: str) -> dict[str, Any]:
    chunks = await search_collection(
        collection=settings.qdrant_public_collection,
        query=question,
        limit=6,
    )
    ctx = _format_context(chunks)
    system = (
        "You are a helpful shopping assistant for a general audience. "
        "Answer clearly using the CONTEXT when relevant. If CONTEXT is thin, "
        "still give safe general guidance and note assumptions."
    )
    user = f"QUESTION:\n{question}\n\nCONTEXT:\n{ctx or '(no retrieval hits)'}"
    answer, used_llm = invoke_claude_sonnet(system_prompt=system, user_prompt=user)
    warning = None
    if not used_llm:
        warning = (
            "AWS Bedrock is not configured or failed; showing retrieval-grounded summary only."
        )
        bullets = []
        for c in chunks[:5]:
            t = (c.get("text") or "").strip().replace("\n", " ")
            if t:
                bullets.append(f"- {t[:320]}{'…' if len(t) > 320 else ''}")
        retrieval_summary = "\n".join(bullets) if bullets else "(No matching documents.)"
        answer = (
            f"{answer}\n\nRetrieval-only summary:\n{retrieval_summary}"
        )
    return {
        "answer": answer,
        "retrieval": chunks,
        "used_bedrock": used_llm,
        "warning": warning,
    }


async def answer_private_member_question(question: str) -> dict[str, Any]:
    chunks = await search_collection(
        collection=settings.qdrant_private_collection,
        query=question,
        limit=6,
    )
    ctx = _format_context(chunks)
    system = (
        "You are a members-only shopping concierge. Use CONTEXT for specifics on discounts, "
        "premium SKUs, loyalty, and private FAQs. Never invent member prices."
    )
    user = f"QUESTION:\n{question}\n\nCONTEXT:\n{ctx or '(no retrieval hits)'}"
    answer, used_llm = invoke_claude_sonnet(system_prompt=system, user_prompt=user)
    warning = None
    if not used_llm:
        warning = (
            "AWS Bedrock is not configured or failed; returning retrieval snippets and a short note."
        )
        bullets = []
        for c in chunks[:5]:
            t = (c.get("text") or "").strip().replace("\n", " ")
            if t:
                bullets.append(f"- {t[:320]}{'…' if len(t) > 320 else ''}")
        retrieval_summary = "\n".join(bullets) if bullets else "(No matching documents.)"
        answer = f"{answer}\n\nRetrieval-only summary:\n{retrieval_summary}"
    return {
        "answer": answer,
        "retrieval": chunks,
        "used_bedrock": used_llm,
        "warning": warning,
    }
