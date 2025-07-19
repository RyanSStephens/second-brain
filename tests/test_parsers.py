import tempfile
from pathlib import Path

from second_brain.parsers.documents import parse_file, parse_markdown, parse_text


def test_parse_markdown():
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
        f.write("# My Notes\n\nSome content here.\n\n## Section\n\nMore content.")
        f.flush()
        result = parse_markdown(Path(f.name))
    assert result["title"] == "My Notes"
    assert "Some content" in result["content"]
    assert result["doc_type"] == "markdown"


def test_parse_text():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("Just some plain text notes.")
        f.flush()
        result = parse_text(Path(f.name))
    assert "plain text" in result["content"]
    assert result["doc_type"] == "text"


def test_parse_file_unsupported():
    with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
        f.write(b"binary stuff")
        f.flush()
        result = parse_file(Path(f.name))
    assert result is None


def test_parse_file_markdown():
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
        f.write("# Test\n\nContent")
        f.flush()
        result = parse_file(Path(f.name))
    assert result is not None
    assert result["title"] == "Test"
