from second_brain.rag.chunker import chunk_document


def test_chunk_basic():
    content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = chunk_document(content, "test.md", "Test Doc", chunk_size=30)
    assert len(chunks) >= 1
    assert all(c.source == "test.md" for c in chunks)
    assert all(c.doc_title == "Test Doc" for c in chunks)


def test_chunk_empty():
    chunks = chunk_document("", "test.md", "Empty")
    assert chunks == []


def test_chunk_single_paragraph():
    chunks = chunk_document("Hello world.", "test.md", "Test", chunk_size=1000)
    assert len(chunks) == 1
    assert chunks[0].content == "Hello world."


def test_chunk_ids_unique():
    content = "Para one.\n\nPara two.\n\nPara three.\n\nPara four."
    chunks = chunk_document(content, "test.md", "Test", chunk_size=20)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids)), "Chunk IDs must be unique"


def test_chunk_preserves_content():
    content = "A" * 200 + "\n\n" + "B" * 200 + "\n\n" + "C" * 200
    chunks = chunk_document(content, "test.md", "Test", chunk_size=250)
    combined = " ".join(c.content for c in chunks)
    assert "A" in combined
    assert "B" in combined
    assert "C" in combined
