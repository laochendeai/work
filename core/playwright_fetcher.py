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
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    viewport = {
        "width": random.randint(1024, 1920),
        "height": random.randint(600, 1080),
    }

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport=viewport,
                user_agent=user_agent,
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
            page = await context.new_page()

            stealth_helper = Stealth()
            await stealth_helper.apply_stealth_async(page)
            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )

            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            # 尽力等待网络空闲（部分站点会持续轮询导致 networkidle 永不触发）
            try:
                await page.wait_for_load_state("networkidle", timeout=8_000)
            except Exception:
                pass
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
            else:
                # 给 SPA 一点渲染时间，避免抓到空壳
                await page.wait_for_timeout(800)

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
