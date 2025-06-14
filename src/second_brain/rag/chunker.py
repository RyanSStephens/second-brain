from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import md5


@dataclass
class Chunk:
    content: str
    source: str
    doc_title: str
    chunk_index: int
    doc_type: str = "text"
    metadata: dict = field(default_factory=dict)

    @property
    def chunk_id(self) -> str:
        content_hash = md5(self.content.encode()).hexdigest()[:8]
        return f"{self.source}:{self.chunk_index}:{content_hash}"


def chunk_document(
    content: str,
    source: str,
    doc_title: str,
    doc_type: str = "text",
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[Chunk]:
    """Split document text into overlapping chunks."""
    if not content.strip():
        return []

    chunks: list[Chunk] = []
    # Split by paragraphs first, then by size
    paragraphs = content.split("\n\n")

    current_text = ""
    chunk_index = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_text) + len(para) + 2 > chunk_size and current_text:
            chunks.append(Chunk(
                content=current_text.strip(),
                source=source,
                doc_title=doc_title,
                chunk_index=chunk_index,
                doc_type=doc_type,
            ))
            chunk_index += 1

            # Keep overlap from end of current chunk
            words = current_text.split()
            overlap_words = []
            overlap_len = 0
            for w in reversed(words):
                if overlap_len + len(w) + 1 > chunk_overlap:
                    break
                overlap_words.insert(0, w)
                overlap_len += len(w) + 1
            current_text = " ".join(overlap_words) + "\n\n" + para if overlap_words else para
        else:
            current_text = current_text + "\n\n" + para if current_text else para

    # Last chunk
    if current_text.strip():
        chunks.append(Chunk(
            content=current_text.strip(),
            source=source,
            doc_title=doc_title,
            chunk_index=chunk_index,
            doc_type=doc_type,
        ))

    return chunks
