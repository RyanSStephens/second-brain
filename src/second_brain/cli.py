from __future__ import annotations

import argparse
import logging
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="second-brain — personal knowledge base with Q&A"
    )
    subparsers = parser.add_subparsers(dest="command")

    # serve
    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8000)

    # ingest
    ingest_parser = subparsers.add_parser(
        "ingest", help="Ingest files into the knowledge base"
    )
    ingest_parser.add_argument(
        "paths", nargs="+", help="Files or directories to ingest"
    )

    # ask
    ask_parser = subparsers.add_parser(
        "ask", help="Ask a question from the command line"
    )
    ask_parser.add_argument("question", nargs="+")

    # search
    search_parser = subparsers.add_parser(
        "search", help="Search without generating an answer"
    )
    search_parser.add_argument("query", nargs="+")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.command == "serve":
        _run_server(args.host, args.port)
    elif args.command == "ingest":
        _run_ingest(args.paths)
    elif args.command == "ask":
        _run_ask(" ".join(args.question))
    elif args.command == "search":
        _run_search(" ".join(args.query))
    else:
        parser.print_help()


def _run_server(host: str, port: int) -> None:
    import uvicorn

    uvicorn.run("second_brain.api.app:app", host=host, port=port, reload=True)


def _run_ingest(paths: list[str]) -> None:
    from second_brain.rag.knowledge_base import KnowledgeBase

    kb = KnowledgeBase()
    total = 0
    for p in paths:
        path = Path(p)
        if path.is_file():
            count = kb.ingest_file(path)
            print(f"  {path.name}: {count} chunks")
            total += count
        elif path.is_dir():
            count = kb.ingest_directory(path)
            print(f"  {path}: {count} chunks")
            total += count
        else:
            print(f"  {p}: not found, skipping")
    print(f"\nTotal: {total} chunks ingested. Store has {kb.store.count} chunks.")


def _run_ask(question: str) -> None:
    import asyncio

    from second_brain.rag.knowledge_base import KnowledgeBase

    kb = KnowledgeBase()
    result = asyncio.run(kb.ask(question))
    print(f"\n{result['answer']}\n")
    if result["sources"]:
        print("Sources:")
        for s in result["sources"]:
            print(f"  [{s['score']}] {s['title']} ({s['source']})")


def _run_search(query: str) -> None:
    from second_brain.rag.knowledge_base import KnowledgeBase

    kb = KnowledgeBase()
    results = kb.search(query)
    if not results:
        print("No results found.")
        return
    for r in results:
        print(f"\n[{r.score:.3f}] {r.doc_title} ({r.source})")
        print(f"  {r.content[:200]}...")


if __name__ == "__main__":
    main()
