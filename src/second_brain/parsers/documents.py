from __future__ import annotations

from pathlib import Path


def parse_markdown(file_path: Path) -> dict:
    """Parse a markdown file, extracting frontmatter-like title and content."""
    text = file_path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")

    title = file_path.stem
    content = text

    # Try to extract title from first heading
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break

    return {
        "title": title,
        "content": content,
        "source": str(file_path),
        "doc_type": "markdown",
    }


def parse_text(file_path: Path) -> dict:
    """Parse a plain text file."""
    text = file_path.read_text(encoding="utf-8", errors="replace")
    return {
        "title": file_path.stem,
        "content": text,
        "source": str(file_path),
        "doc_type": "text",
    }


def parse_pdf(file_path: Path) -> dict:
    """Parse a PDF file using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(str(file_path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pages.append(f"[Page {i+1}]\n{text}")

    content = "\n\n".join(pages)
    title = file_path.stem

    # Try to get title from PDF metadata
    meta = reader.metadata
    if meta and meta.title:
        title = meta.title

    return {
        "title": title,
        "content": content,
        "source": str(file_path),
        "doc_type": "pdf",
    }


PARSERS = {
    ".md": parse_markdown,
    ".txt": parse_text,
    ".text": parse_text,
    ".pdf": parse_pdf,
    ".rst": parse_text,
    ".org": parse_text,
}


def parse_file(file_path: Path) -> dict | None:
    """Parse a file based on its extension. Returns None for unsupported types."""
    parser = PARSERS.get(file_path.suffix.lower())
    if parser is None:
        return None
    try:
        return parser(file_path)
    except Exception as e:
        return {
            "title": file_path.stem,
            "content": f"[Error parsing file: {e}]",
            "source": str(file_path),
            "doc_type": "error",
        }
