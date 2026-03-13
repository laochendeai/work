"""
详情页抓取策略。

默认优先用轻量 HTTP 抓取 HTML，失败时再回退到 Playwright。
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from typing import Dict, List, Optional

import requests

from config.settings import (
    HTTP_FETCH_ENABLED,
    HTTP_FETCH_TIMEOUT,
    USER_AGENT,
    DETAIL_WAIT_UNTIL,
    HTTP_PREFETCH_WORKERS,
)

logger = logging.getLogger(__name__)


class HybridDetailFetcher:
    """HTTP-first, browser-fallback 的详情页抓取器。"""

    def __init__(self, browser_fetcher=None):
        self.browser_fetcher = browser_fetcher
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://www.ccgp.gov.cn/",
            }
        )

    def fetch(self, url: str) -> Optional[str]:
        html = None
        if HTTP_FETCH_ENABLED:
            html = self._fetch_via_http(url)
            if html:
                return html

        return self._fetch_via_browser(url)

    def prefetch_http(self, urls: List[str], max_workers: Optional[int] = None) -> Dict[str, str]:
        normalized_urls = [url.strip() for url in urls if url and url.strip()]
        if not normalized_urls or not HTTP_FETCH_ENABLED:
            return {}

        workers = max_workers or HTTP_PREFETCH_WORKERS
        if workers <= 1:
            return {
                url: html
                for url in normalized_urls
                for html in [self._fetch_via_http(url)]
                if html
            }

        results: Dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_url = {
                executor.submit(self._fetch_via_http, url): url for url in normalized_urls
            }
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    html = future.result()
                except Exception:
                    html = None
                if html:
                    results[url] = html
        return results

    def close(self):
        self.session.close()

    def _fetch_via_http(self, url: str) -> Optional[str]:
        try:
            response = self.session.get(url, timeout=HTTP_FETCH_TIMEOUT)
            if response.status_code != 200:
                logger.debug(
                    f"HTTP详情抓取返回非200状态: {response.status_code} ({url})"
                )
                return None

            content_type = response.headers.get("Content-Type", "")
            if (
                "text/html" not in content_type
                and "application/xhtml+xml" not in content_type
            ):
                logger.debug(f"HTTP详情抓取内容类型不是HTML: {content_type} ({url})")
                return None

            response.encoding = (
                response.encoding or response.apparent_encoding or "utf-8"
            )
            html = response.text
            if self._looks_unusable(html):
                logger.debug(f"HTTP详情抓取内容疑似不可用，回退浏览器: {url}")
                return None
            return html
        except Exception as exc:
            logger.debug(f"HTTP详情抓取失败，准备回退浏览器: {url} ({exc})")
            return None

    def _fetch_via_browser(self, url: str) -> Optional[str]:
        if not self.browser_fetcher:
            return None
        return self.browser_fetcher.get_page(url, wait_for=DETAIL_WAIT_UNTIL)

    @staticmethod
    def _looks_unusable(html: str) -> bool:
        if not html or len(html) < 500:
            return True

        markers = [
            "访问过于频繁",
            "稍后再试",
            "验证码",
            "captcha",
            "403 Forbidden",
            "Just a moment",
        ]
        lowered = html.lower()
        return any(marker.lower() in lowered for marker in markers)
