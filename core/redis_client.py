#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared Redis client helper.
"""

from __future__ import annotations

import os
from typing import Optional

import redis.asyncio as redis

_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Return a cached asyncio Redis client."""
    global _client
    if _client is None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _client = redis.from_url(url, decode_responses=False)
    return _client
