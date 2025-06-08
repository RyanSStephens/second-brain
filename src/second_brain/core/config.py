from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Second Brain"
    debug: bool = False

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_provider: str = "anthropic"
    llm_model: str = "claude-3-5-sonnet-20241022"

    # Embeddings
    embedding_backend: str = "sentence-transformers"
    embedding_model: str = "all-MiniLM-L6-v2"

    # RAG
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 8
    chroma_collection: str = "second_brain"
    chroma_persist_dir: str = "./chroma_data"

    # Storage
    db_url: str = "sqlite+aiosqlite:///second_brain.db"
    upload_dir: str = "./uploads"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
