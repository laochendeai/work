#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Retry/failed URL tracking in Redis.
"""

from __future__ import annotations

from typing import List, Tuple

from .redis_client import get_redis_client

FAILED_KEY = "crawl:failed"


async def mark_failed(url: str, reason: str) -> None:
    """Record a failed URL with its reason."""
    if not url:
        return
    client = get_redis_client()
    await client.hset(FAILED_KEY, url, reason)


async def get_failed() -> List[Tuple[str, str]]:
    """Return the list of failed URLs."""
    client = get_redis_client()
    data = await client.hgetall(FAILED_KEY)
    return [
        (
            key.decode() if isinstance(key, bytes) else key,
            value.decode() if isinstance(value, bytes) else value,
        )
        for key, value in data.items()
    ]
