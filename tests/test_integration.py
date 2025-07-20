"""Integration test — full pipeline with mock embedder (no model download)."""
import random

from second_brain.rag.chunker import chunk_document
from second_brain.rag.store import VectorStore


class MockEmbedder:
    def embed(self, texts):
        results = []
        for text in texts:
            vec = [0.0] * 64
            t = text.lower()
            if "kubernetes" in t or "k8s" in t or "container" in t:
                vec[0] = 1.0; vec[1] = 0.8
            if "python" in t or "code" in t or "programming" in t:
                vec[2] = 1.0; vec[3] = 0.8
            if "recipe" in t or "cook" in t or "food" in t:
                vec[4] = 1.0; vec[5] = 0.8
            random.seed(hash(text) % (2**31))
            for i in range(len(vec)):
                vec[i] += random.gauss(0, 0.05)
            norm = sum(x**2 for x in vec) ** 0.5
            if norm > 0:
                vec = [x / norm for x in vec]
            else:
                vec[0] = 1.0
            results.append(vec)
        return results


def test_ingest_and_search():
    embedder = MockEmbedder()
    store = VectorStore(collection_name="test_second_brain")

    docs = [
        ("Kubernetes notes", "Kubernetes is a container orchestration platform. Pods are the smallest unit. Services expose pods."),
        ("Python tips", "Python is great for data science. Use virtual environments. Type hints improve code quality."),
        ("Cooking notes", "The best pasta recipe uses fresh ingredients. Cook pasta al dente. Save some pasta water."),
    ]

    for title, content in docs:
        chunks = chunk_document(content, f"{title}.md", title, chunk_size=200)
        embeddings = embedder.embed([c.content for c in chunks])
        store.upsert(chunks, embeddings)

    print(f"  Ingested {store.count} chunks from {len(docs)} docs")

    # Search for kubernetes
    emb = embedder.embed(["container orchestration"])[0]
    results = store.query(emb, top_k=3)
    assert len(results) > 0
    assert "kubernetes" in results[0].doc_title.lower()
    print(f"  'container orchestration' → top: {results[0].doc_title} [{results[0].score:.3f}]")

    # Search for python
    emb = embedder.embed(["programming tips"])[0]
    results = store.query(emb, top_k=3)
    assert len(results) > 0
    assert "python" in results[0].doc_title.lower()
    print(f"  'programming tips' → top: {results[0].doc_title} [{results[0].score:.3f}]")

    # Search for cooking
    emb = embedder.embed(["food recipe"])[0]
    results = store.query(emb, top_k=3)
    assert len(results) > 0
    assert "cooking" in results[0].doc_title.lower()
    print(f"  'food recipe' → top: {results[0].doc_title} [{results[0].score:.3f}]")

    # List sources
    sources = store.list_sources()
    assert len(sources) == 3
    print(f"  Sources: {[s['title'] for s in sources]}")

    # Delete a source
    store.delete_by_source("Kubernetes notes.md")
    sources_after = store.list_sources()
    assert len(sources_after) == 2
    print(f"  After delete: {len(sources_after)} sources")

    print("\n  Integration test passed!")


if __name__ == "__main__":
    test_ingest_and_search()
