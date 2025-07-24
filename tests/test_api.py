"""API smoke test with mocked knowledge base."""
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

os.environ["DB_URL"] = "sqlite+aiosqlite:///test_api.db"
os.environ["ANTHROPIC_API_KEY"] = "test"

from second_brain.core.config import get_settings
get_settings.cache_clear()


def test_api_endpoints():
    mock_kb = MagicMock()
    mock_kb.store = MagicMock()
    mock_kb.store.count = 42
    mock_kb.store.list_sources.return_value = [{"source": "test.md", "title": "Test"}]
    mock_kb.search.return_value = []

    with patch("second_brain.api.app.get_kb", return_value=mock_kb):
        from second_brain.api.app import app
        from httpx import ASGITransport, AsyncClient

        async def _run():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get("/health")
                assert r.status_code == 200
                assert r.json()["status"] == "ok"
                print("  GET /health .............. OK")

                r = await client.get("/api/v1/sources")
                assert r.status_code == 200
                print("  GET /sources ............. OK")

                r = await client.get("/api/v1/search?query=test")
                assert r.status_code == 200
                print("  GET /search .............. OK")

            print("\n  API smoke test passed!")

        asyncio.run(_run())


if __name__ == "__main__":
    test_api_endpoints()

if os.path.exists("test_api.db"):
    os.remove("test_api.db")
