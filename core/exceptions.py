#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom exceptions shared across crawler modules.
"""

from __future__ import annotations


class PlaywrightFallback(Exception):
    """Signal that Playwright should fallback to the HTTP fetcher."""


class BlacklistedURLException(Exception):
    """Raised when trying to access a blacklisted URL."""

    def __init__(self, url: str, reason: str, severity: str = "medium"):
        self.url = url
        self.reason = reason
        self.severity = severity
        super().__init__(f"URL is blacklisted: {url} - {reason}")

