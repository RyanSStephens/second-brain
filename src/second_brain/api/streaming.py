from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from second_brain.api.auth import require_api_key
from second_brain.core.config import get_settings
from second_brain.core.llm import get_llm_provider
from second_brain.rag.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/stream", tags=["streaming"])

_kb: KnowledgeBase | None = None


def _get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


async def _stream_answer(question: str, top_k: int) -> AsyncIterator[str]:
    """Stream answer as Server-Sent Events."""
    kb = _get_kb()
    results = kb.search(question, top_k=top_k)

    # Send retrieved sources first
    sources = [
        {"source": r.source, "title": r.doc_title, "score": round(r.score, 3)}
        for r in results if r.score >= 0.1
    ]
    yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

    if not results or all(r.score < 0.1 for r in results):
        yield f"event: token\ndata: I don't have relevant information to answer that.\n\n"
        yield "event: done\ndata: {}\n\n"
        return

    # Build context
    context_parts = []
    for r in results:
        if r.score >= 0.1:
            context_parts.append(f"[Source: {r.doc_title}]\n{r.content}")
    context = "\n\n---\n\n".join(context_parts)

    # Stream LLM response
    settings = get_settings()
    try:
        if settings.llm_provider == "anthropic":
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            system = "You are a helpful assistant for a personal knowledge base. Answer based on the provided context. Cite sources."
            prompt = f"Context:\n{context}\n\nQuestion: {question}"

            async with client.messages.stream(
                model=settings.llm_model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield f"event: token\ndata: {json.dumps(text)}\n\n"

        else:
            # Fallback to non-streaming for other providers
            llm = get_llm_provider()
            answer = await llm.generate(
                system="You are a helpful assistant. Answer based on context. Cite sources.",
                query=question,
                context=f"Context:\n{context}",
            )
            # Simulate streaming by chunking
            words = answer.split(" ")
            for i in range(0, len(words), 3):
                chunk = " ".join(words[i:i+3])
                if i > 0:
                    chunk = " " + chunk
                yield f"event: token\ndata: {json.dumps(chunk)}\n\n"
                await asyncio.sleep(0.02)

    except Exception as e:
        logger.error("Streaming error: %s", e)
        yield f"event: error\ndata: {json.dumps(str(e))}\n\n"

    yield "event: done\ndata: {}\n\n"


@router.get("/ask")
async def stream_ask(
    question: str,
    top_k: int = Query(default=8, ge=1, le=20),
    _api_key: str = Depends(require_api_key),
):
    """Stream an answer as Server-Sent Events."""
    return StreamingResponse(
        _stream_answer(question, top_k),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
