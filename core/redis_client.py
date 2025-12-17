#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared Redis client helper.
"""

from __future__ import annotations

import asyncio
import os
import weakref
from typing import Dict

import redis.asyncio as redis

_clients_by_loop: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, redis.Redis]" = weakref.WeakKeyDictionary()
_fallback_clients: Dict[str, redis.Redis] = {}


def get_redis_client() -> redis.Redis:
    """Return an asyncio Redis client bound to the current event loop.

    redis-py asyncio client内部使用 asyncio primitives（如 Lock），它们与 event loop 绑定。
    为避免在同一进程里多次创建/切换 event loop（例如多次 `asyncio.run(...)`）导致
    “is bound to a different event loop”，这里按 event loop 维度缓存 client。
    """
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        # 理论上队列调用都在 async context 里；这里兜底，避免在同步上下文调用时报错。
        client = _fallback_clients.get(url)
        if client is None:
            client = redis.from_url(url, decode_responses=False)
            _fallback_clients[url] = client
        return client

    client = _clients_by_loop.get(loop)
    if client is None:
        client = redis.from_url(url, decode_responses=False)
        _clients_by_loop[loop] = client
    return client
