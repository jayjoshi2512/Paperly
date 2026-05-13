"""Singleton rate limiter instance shared across all routers."""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Key function: rate limit per client IP address.
limiter = Limiter(key_func=get_remote_address)
