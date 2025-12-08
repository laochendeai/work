#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom exceptions shared across crawler modules.
"""

from __future__ import annotations


class PlaywrightFallback(Exception):
    """Signal that Playwright should fallback to the HTTP fetcher."""

