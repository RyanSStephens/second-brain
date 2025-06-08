# Second Brain

Personal knowledge base with RAG-powered Q&A. Dump your notes, PDFs, and markdown files, then ask questions across all of them.

## How It Works

1. **Ingest** documents (markdown, text, PDF) — they get chunked and embedded into a vector store
2. **Ask** questions in natural language — relevant chunks are retrieved and fed to an LLM
3. **Get answers** with source citations pointing back to your original documents

## Stack

- **FastAPI** — REST API
- **ChromaDB** — vector store for embeddings
- **sentence-transformers** — local embeddings (no API costs)
- **Anthropic Claude / OpenAI** — answer generation
- **SQLite** — document and query history tracking
- **pypdf** — PDF parsing

## Quick Start

```bash
cp .env.example .env
# add your LLM API key

pip install -e .

# ingest some notes
second-brain ingest ~/notes/

# start the API
second-brain serve

# or ask directly from CLI
second-brain ask "What did I write about kubernetes?"
```

## API

### Ingest
- `POST /api/v1/ingest/file` — upload a file
- `POST /api/v1/ingest/directory?path=/path` — ingest a directory

### Query
- `POST /api/v1/ask?question=...` — ask a question (RAG + LLM)
- `GET /api/v1/search?query=...` — semantic search only (no LLM)

### Management
- `GET /api/v1/documents` — list ingested documents
- `DELETE /api/v1/documents/{source}` — remove a document
- `GET /api/v1/sources` — list sources in vector store
- `GET /api/v1/history` — recent query history

## Dev

```bash
pip install -e ".[dev]"
pytest
ruff check src/
```
