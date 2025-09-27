from __future__ import annotations

import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from second_brain.core.config import get_settings
from second_brain.rag.knowledge_base import KnowledgeBase
from second_brain.storage.database import init_db, get_db, log_document, log_query, list_documents, list_queries
from second_brain.api.auth import require_api_key
from second_brain.api.metrics import MetricsMiddleware
from second_brain.api.streaming import router as streaming_router

settings = get_settings()
kb: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase:
    global kb
    if kb is None:
        kb = KnowledgeBase()
    return kb


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    await init_db()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    get_kb()
    yield


app = FastAPI(
    title="Second Brain",
    description="Personal knowledge base with RAG-powered Q&A",
    version="0.2.0",
    lifespan=lifespan,
)

# Add metrics middleware
metrics_middleware = MetricsMiddleware(app)
app.add_middleware(MetricsMiddleware)

# Add streaming routes
app.include_router(streaming_router)


@app.get("/health")
async def health():
    return {"status": "ok", "documents": get_kb().store.count}


@app.get("/metrics")
async def get_metrics():
    """Return application metrics."""
    return metrics_middleware.get_metrics()


# --- Ingest (requires API key) ---

@app.post("/api/v1/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    """Upload and ingest a single file."""
    upload_dir = Path(settings.upload_dir)
    file_path = upload_dir / file.filename

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    chunk_count = get_kb().ingest_file(file_path)
    if chunk_count == 0:
        raise HTTPException(400, f"Could not parse file: {file.filename}")

    await log_document(db, file.filename, str(file_path), file_path.suffix.lstrip("."), chunk_count)

    return {
        "filename": file.filename,
        "chunks": chunk_count,
        "total_chunks": get_kb().store.count,
    }


@app.post("/api/v1/ingest/directory")
async def ingest_directory(
    path: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    """Ingest all supported files from a directory path."""
    dir_path = Path(path)
    if not dir_path.is_dir():
        raise HTTPException(400, f"Not a directory: {path}")

    chunk_count = get_kb().ingest_directory(dir_path)
    return {
        "path": path,
        "chunks": chunk_count,
        "total_chunks": get_kb().store.count,
    }


# --- Query (requires API key) ---

@app.post("/api/v1/ask")
async def ask(
    question: str,
    top_k: int = Query(default=8, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    """Ask a question against the knowledge base."""
    result = await get_kb().ask(question, top_k=top_k)
    await log_query(db, question, result["answer"], result["context_used"])
    return result


@app.get("/api/v1/search")
async def search(
    query: str,
    top_k: int = Query(default=8, ge=1, le=20),
    _api_key: str = Depends(require_api_key),
):
    """Search the knowledge base without generating an answer."""
    results = get_kb().search(query, top_k=top_k)
    return {
        "query": query,
        "results": [
            {
                "source": r.source,
                "title": r.doc_title,
                "content": r.content[:300],
                "score": round(r.score, 3),
            }
            for r in results
        ],
    }


# --- Management (requires API key) ---

@app.get("/api/v1/documents")
async def get_documents(
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    """List all ingested documents."""
    docs = await list_documents(db)
    return [
        {
            "id": d.id,
            "title": d.title,
            "source": d.source,
            "doc_type": d.doc_type,
            "chunk_count": d.chunk_count,
            "created_at": str(d.created_at),
        }
        for d in docs
    ]


@app.delete("/api/v1/documents/{source:path}")
async def delete_document(
    source: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    """Remove a document from the knowledge base."""
    get_kb().remove_document(source)
    return {"deleted": source}


@app.get("/api/v1/sources")
async def get_sources(_api_key: str = Depends(require_api_key)):
    """List all unique sources in the vector store."""
    return get_kb().store.list_sources()


@app.get("/api/v1/history")
async def get_history(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    """Get recent query history."""
    queries = await list_queries(db, limit)
    return [
        {
            "id": q.id,
            "question": q.question,
            "answer": q.answer[:200] + "..." if len(q.answer) > 200 else q.answer,
            "sources_used": q.sources_used,
            "created_at": str(q.created_at),
        }
        for q in queries
    ]
