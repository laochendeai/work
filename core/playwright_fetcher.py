#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright-based fetcher with simple stealth tweaks.
"""

from __future__ import annotations

import random
from typing import Optional

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from core.actions import execute_actions
from core.exceptions import PlaywrightFallback
from core.metrics import record_page_actions


async def fetch(url: str, wait_selector: Optional[str] = None, actions: Optional[list] = None) -> str:
    """
    Fetch the rendered HTML for the given URL.
    """
    viewport = {
        "width": random.randint(1024, 1920),
        "height": random.randint(600, 1080),
    }

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport=viewport)
            page = await context.new_page()

            stealth_helper = Stealth()
            await stealth_helper.apply_stealth_async(page)
            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )

            await page.goto(url, wait_until="networkidle")
            await page.evaluate(
                """
                () => {
                    document.documentElement.setAttribute(
                        'data-stealth',
                        'navigator.webdriver=undefined'
                    );
                }
                """
            )

            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=10_000)

            if actions:
                await execute_actions(page, actions)
                record_page_actions(len(actions))

            content = await page.content()
            content = content.replace("HeadlessChrome", "Chrome")

            await context.close()
            await browser.close()

            return content
    except Exception as exc:
        raise PlaywrightFallback(str(exc))
