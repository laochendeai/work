#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate Playwright action DSL by clicking through quotes.toscrape.com.
"""

import asyncio

from bs4 import BeautifulSoup

from core.playwright_fetcher import fetch as playwright_fetch

TEST_URL = "https://quotes.toscrape.com/scroll"
TEST_ACTIONS = [
    {"scroll": "bottom"},
    {"wait": 1},
    {"scroll": "bottom"},
    {"wait": 1},
]


async def main():
    html = await playwright_fetch(TEST_URL, actions=TEST_ACTIONS)
    soup = BeautifulSoup(html, "html.parser")
    quotes = soup.select("div.quote")
    passed = len(quotes) > 10
    print(f"ACTIONS_TEST={'PASS' if passed else 'FAIL'} - quotes={len(quotes)}")
    if not passed:
        print(html[:1000])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
