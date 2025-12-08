#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Container-only integration test pushing jobs via Redis."""

import asyncio
import json

from bs4 import BeautifulSoup

from core.queue import push_start_urls, pop_url
from core.redis_client import get_redis_client
from core.playwright_fetcher import fetch as playwright_fetch
from core.exceptions import PlaywrightFallback

TEST_URL = "https://quotes.toscrape.com/scroll"
TEST_ACTIONS = [
    {"scroll": "bottom"},
    {"wait": 1},
    {"scroll": "bottom"},
    {"wait": 1},
]
QUEUE_KEY = "crawl:queue"
FAILED_KEY = "crawl:failed"


async def main() -> int:
    client = get_redis_client()
    await client.delete(QUEUE_KEY)
    await client.delete(FAILED_KEY)

    payload = json.dumps(
        {
            "link": TEST_URL,
            "render_mode": "playwright",
            "actions": TEST_ACTIONS,
        },
        ensure_ascii=False,
    )
    await push_start_urls([payload])

    popped = await pop_url(timeout=5)
    if popped is None:
        print("CONTAINER_TEST=FAIL - queue pop timeout")
        return 1

    item = json.loads(popped)
    try:
        html = await playwright_fetch(item["link"], actions=item.get("actions"))
    except PlaywrightFallback as exc:
        print(f"CONTAINER_TEST=FAIL - fetch error: {exc}")
        return 1

    soup = BeautifulSoup(html, "html.parser")
    quotes = len(soup.select("div.quote"))
    passed = quotes > 10
    print(f"CONTAINER_TEST={'PASS' if passed else 'FAIL'} - quotes={quotes}")
    if not passed:
        print(html[:1000])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
