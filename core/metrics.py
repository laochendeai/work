#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prometheus metrics helpers."""

from __future__ import annotations

import threading
from typing import Literal

from prometheus_client import Counter, start_http_server

_METRICS_STARTED = False
_LOCK = threading.Lock()


crawler_requests_total = Counter(
    "crawler_requests_total",
    "Total crawl attempts partitioned by mode and status",
    labelnames=("mode", "status"),
)

crawler_fallback_total = Counter(
    "crawler_fallback_total",
    "Number of Playwright fallbacks triggered",
)

crawler_page_actions_total = Counter(
    "crawler_page_actions_total",
    "Number of YAML page actions executed",
)


def start_metrics_server(port: int = 8000) -> None:
    global _METRICS_STARTED
    if _METRICS_STARTED:
        return
    with _LOCK:
        if _METRICS_STARTED:
            return
        start_http_server(port)
        _METRICS_STARTED = True


def record_request(mode: Literal["http", "playwright"], status: Literal["success", "fail"]) -> None:
    crawler_requests_total.labels(mode=mode, status=status).inc()


def record_fallback() -> None:
    crawler_fallback_total.inc()


def record_page_actions(count: int) -> None:
    if count > 0:
        crawler_page_actions_total.inc(count)
