#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAML-style action DSL execution for Playwright.
"""

from __future__ import annotations

import asyncio
from typing import Dict, List

from core.exceptions import PlaywrightFallback


async def execute_actions(page, actions: List[Dict]) -> None:
    """Execute Playwright actions sequentially with per-action timeout."""
    if not actions:
        return
    for action in actions:
        try:
            await asyncio.wait_for(_run_action(page, action), timeout=10)
        except asyncio.TimeoutError as exc:
            raise PlaywrightFallback("action timeout") from exc


async def _run_action(page, action: Dict) -> None:
    if "click" in action:
        selector = action["click"]
        try:
            await page.wait_for_selector(selector, timeout=10_000)
            await page.click(selector)
        except Exception as exc:
            raise PlaywrightFallback(f"click failed: {selector}") from exc
        return

    if "wait" in action:
        try:
            await asyncio.sleep(float(action["wait"]))
        except Exception as exc:
            raise PlaywrightFallback("wait failed") from exc
        return

    if "scroll" in action:
        direction = action["scroll"]
        if direction == "bottom":
            script = "window.scrollTo(0, document.body.scrollHeight)"
        elif direction == "top":
            script = "window.scrollTo(0, 0)"
        else:
            raise PlaywrightFallback(f"unknown scroll direction: {direction}")
        try:
            await page.evaluate(script)
        except Exception as exc:
            raise PlaywrightFallback(f"scroll failed: {direction}") from exc
        return

    raise PlaywrightFallback(f"unknown action: {action}")
