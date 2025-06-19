from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()


class OpenAIEmbedder:
    def __init__(self, model_name: str = "text-embedding-3-small") -> None:
        import os
        import openai
        self._client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        self._model = model_name

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in resp.data]


def create_embedder(backend: str = "sentence-transformers", model: str = "all-MiniLM-L6-v2") -> Embedder:
    if backend == "sentence-transformers":
        return SentenceTransformerEmbedder(model)
    elif backend == "openai":
        return OpenAIEmbedder(model)
    raise ValueError(f"Unknown embedding backend: {backend}")
