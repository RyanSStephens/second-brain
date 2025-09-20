"""Tests for API key authentication."""
import os
from unittest.mock import patch

import pytest


def test_no_keys_configured_allows_all():
    """When no API_KEYS env var is set, all requests pass (dev mode)."""
    os.environ.pop("API_KEYS", None)
    # Re-import to reset cached keys
    from second_brain.api import auth
    auth._VALID_KEYS = None

    import asyncio
    result = asyncio.run(auth.require_api_key(None))
    assert result == "dev"


def test_valid_key_passes():
    os.environ["API_KEYS"] = "test-key-123,other-key-456"
    from second_brain.api import auth
    auth._VALID_KEYS = None

    import asyncio
    result = asyncio.run(auth.require_api_key("test-key-123"))
    assert result == "test-key-123"


def test_invalid_key_rejected():
    os.environ["API_KEYS"] = "test-key-123"
    from second_brain.api import auth
    auth._VALID_KEYS = None

    import asyncio
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth.require_api_key("wrong-key"))
    assert exc_info.value.status_code == 403


def test_missing_key_rejected():
    os.environ["API_KEYS"] = "test-key-123"
    from second_brain.api import auth
    auth._VALID_KEYS = None

    import asyncio
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth.require_api_key(None))
    assert exc_info.value.status_code == 401


def test_generate_api_key():
    from second_brain.api.auth import generate_api_key
    key = generate_api_key()
    assert len(key) > 20
    # Should be unique
    key2 = generate_api_key()
    assert key != key2
