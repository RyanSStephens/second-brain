from __future__ import annotations

import logging
from pathlib import Path

from second_brain.core.config import get_settings
from second_brain.core.llm import get_llm_provider
from second_brain.parsers.documents import parse_file
from second_brain.rag.chunker import chunk_document
from second_brain.rag.embedder import Embedder, create_embedder
from second_brain.rag.store import SearchResult, VectorStore

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful assistant for a personal knowledge base.
Answer the user's question based on the provided context from their notes and documents.
Always cite which document(s) your answer comes from.
If the context doesn't contain enough information to answer, say so clearly.
Be concise and specific."""


class KnowledgeBase:
    """Main orchestrator — ingest documents, query with RAG-powered Q&A."""

    def __init__(self) -> None:
        settings = get_settings()
        self._embedder = create_embedder(
            backend=settings.embedding_backend,
            model=settings.embedding_model,
        )
        self._store = VectorStore(
            collection_name=settings.chroma_collection,
            persist_dir=settings.chroma_persist_dir,
        )
        self._settings = settings

    @property
    def store(self) -> VectorStore:
        return self._store

    @property
    def embedder(self) -> Embedder:
        return self._embedder

    def ingest_file(self, file_path: Path) -> int:
        """Ingest a single file. Returns number of chunks created."""
        parsed = parse_file(file_path)
        if parsed is None:
            logger.warning("Unsupported file type: %s", file_path.suffix)
            return 0

        chunks = chunk_document(
            content=parsed["content"],
            source=parsed["source"],
            doc_title=parsed["title"],
            doc_type=parsed["doc_type"],
            chunk_size=self._settings.chunk_size,
            chunk_overlap=self._settings.chunk_overlap,
        )

        if not chunks:
            return 0

        embeddings = self._embedder.embed([c.content for c in chunks])
        self._store.upsert(chunks, embeddings)
        logger.info("Ingested %s: %d chunks", file_path.name, len(chunks))
        return len(chunks)

    def ingest_directory(self, dir_path: Path) -> int:
        """Ingest all supported files from a directory. Returns total chunks."""
        total = 0
        for file_path in sorted(dir_path.rglob("*")):
            if not file_path.is_file():
                continue
            if file_path.name.startswith("."):
                continue
            count = self.ingest_file(file_path)
            total += count
        return total

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        """Search the knowledge base by semantic similarity."""
        k = top_k or self._settings.top_k
        embedding = self._embedder.embed([query])[0]
        return self._store.query(embedding, top_k=k)

    async def ask(self, question: str, top_k: int | None = None) -> dict:
        """Ask a question — retrieves context and generates an answer."""
        results = self.search(question, top_k=top_k)

        if not results:
            return {
                "answer": (
                    "I don't have any relevant information "
                    "in the knowledge base to answer that."
                ),
                "sources": [],
                "context_used": 0,
            }

        # Build context from retrieved chunks
        context_parts = []
        sources_seen = set()
        for r in results:
            if r.score < 0.1:
                continue
            context_parts.append(f"[Source: {r.doc_title} ({r.source})]\n{r.content}")
            sources_seen.add(r.source)

        context = "\n\n---\n\n".join(context_parts) if context_parts else ""

        llm = get_llm_provider()
        answer = await llm.generate(
            system=SYSTEM_PROMPT,
            query=question,
            context=f"Context from your notes:\n\n{context}",
        )

        return {
            "answer": answer,
            "sources": [
                {"source": r.source, "title": r.doc_title, "score": round(r.score, 3)}
                for r in results
                if r.score >= 0.1
            ],
            "context_used": len(context_parts),
        }

    def remove_document(self, source: str) -> None:
        """Remove a document and its chunks from the knowledge base."""
        self._store.delete_by_source(source)
        logger.info("Removed document: %s", source)
