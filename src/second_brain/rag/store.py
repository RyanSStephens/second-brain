from __future__ import annotations

import logging
from dataclasses import dataclass

import chromadb

from second_brain.rag.chunker import Chunk

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    chunk_id: str
    content: str
    source: str
    doc_title: str
    score: float
    metadata: dict


class VectorStore:
    def __init__(
        self, collection_name: str = "second_brain", persist_dir: str | None = None
    ) -> None:
        if persist_dir:
            self._client = chromadb.PersistentClient(path=persist_dir)
        else:
            self._client = chromadb.Client()
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def count(self) -> int:
        return self._collection.count()

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        self._collection.upsert(
            ids=[c.chunk_id for c in chunks],
            documents=[c.content for c in chunks],
            embeddings=embeddings,
            metadatas=[
                {
                    "source": c.source,
                    "doc_title": c.doc_title,
                    "chunk_index": c.chunk_index,
                    "doc_type": c.doc_type,
                }
                for c in chunks
            ],
        )

    def query(self, embedding: list[float], top_k: int = 8) -> list[SearchResult]:
        if self.count == 0:
            return []
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, self.count),
            include=["documents", "metadatas", "distances"],
        )
        if not results["ids"] or not results["ids"][0]:
            return []

        search_results = []
        for i, cid in enumerate(results["ids"][0]):
            dist = results["distances"][0][i] if results["distances"] else 0.0
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            search_results.append(
                SearchResult(
                    chunk_id=cid,
                    content=results["documents"][0][i] if results["documents"] else "",
                    source=meta.get("source", ""),
                    doc_title=meta.get("doc_title", ""),
                    score=1.0 - dist,
                    metadata=meta,
                )
            )
        return search_results

    def delete_by_source(self, source: str) -> None:
        try:
            self._collection.delete(where={"source": source})
        except Exception as e:
            logger.warning("Failed to delete %s: %s", source, e)

    def list_sources(self) -> list[dict]:
        results = self._collection.get(include=["metadatas"])
        sources: dict[str, str] = {}
        if results["metadatas"]:
            for meta in results["metadatas"]:
                if meta and "source" in meta:
                    sources[meta["source"]] = meta.get("doc_title", "")
        return [{"source": s, "title": t} for s, t in sorted(sources.items())]
