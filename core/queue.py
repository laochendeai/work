#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis-backed crawl queue.
"""

from __future__ import annotations

from typing import List, Optional

from .redis_client import get_redis_client

QUEUE_KEY = "crawl:queue"


async def push_start_urls(urls: List[str]) -> None:
    """Push URLs to the left side of the queue."""
    if not urls:
        return
    client = get_redis_client()
    await client.lpush(QUEUE_KEY, *urls)


async def pop_url(timeout: int = 5) -> Optional[str]:
    """Pop URLs from the right side of the queue."""
    client = get_redis_client()
    result = await client.brpop(QUEUE_KEY, timeout=timeout)
    if result is None:
        return None
    _, value = result
    return value.decode() if isinstance(value, bytes) else value


async def requeue_url(payload: str) -> None:
    """Push a payload back to the left for higher priority."""
    client = get_redis_client()
    await client.lpush(QUEUE_KEY, payload)
