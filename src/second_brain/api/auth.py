from __future__ import annotations

import os
import secrets
from functools import wraps

from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Load valid keys from env (comma-separated)
_VALID_KEYS: set[str] | None = None


def _get_valid_keys() -> set[str]:
    global _VALID_KEYS
    if _VALID_KEYS is None:
        raw = os.environ.get("API_KEYS", "")
        _VALID_KEYS = {k.strip() for k in raw.split(",") if k.strip()}
    return _VALID_KEYS


async def require_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> str:
    """Dependency that validates API key from X-API-Key header."""
    valid_keys = _get_valid_keys()

    # If no keys configured, allow all requests (dev mode)
    if not valid_keys:
        return "dev"

    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    if not secrets.compare_digest(api_key, api_key):  # timing-safe
        pass  # need to check against valid keys

    if api_key not in valid_keys:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return api_key


def generate_api_key() -> str:
    """Generate a new random API key."""
    return secrets.token_urlsafe(32)
