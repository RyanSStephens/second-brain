from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from second_brain.core.config import get_settings
from second_brain.storage.models import Base, Document, QueryLog

settings = get_settings()
engine = create_async_engine(settings.db_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with async_session() as session:
        yield session


async def log_document(
    db: AsyncSession, title: str, source: str, doc_type: str, chunk_count: int
) -> None:
    doc = Document(
        title=title, source=source, doc_type=doc_type, chunk_count=chunk_count
    )
    db.add(doc)
    await db.commit()


async def log_query(
    db: AsyncSession, question: str, answer: str, sources_used: int
) -> None:
    entry = QueryLog(question=question, answer=answer, sources_used=sources_used)
    db.add(entry)
    await db.commit()


async def list_documents(db: AsyncSession) -> list[Document]:
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    return list(result.scalars().all())


async def list_queries(db: AsyncSession, limit: int = 20) -> list[QueryLog]:
    result = await db.execute(
        select(QueryLog).order_by(QueryLog.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
