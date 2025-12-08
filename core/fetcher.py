#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""高级HTTP抓取器，提供HTTP/2、异步并发和自动退避能力"""

import asyncio
import logging
import random
import time
from typing import Iterable, Dict, Optional, Any, List, Callable

import httpx
from tenacity import AsyncRetrying, Retrying, RetryError, retry_if_exception, stop_after_attempt, wait_random_exponential

class FetchError(Exception):
    """网络抓取异常，包含HTTP状态等上下文"""

    def __init__(self, message: str, *, status_code: Optional[int] = None, url: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.url = url


class AdvancedFetcher:
    """封装httpx的现代抓取器，支持HTTP/2、自动重试和批量抓取"""

    DEFAULT_USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        concurrency: int = 10,
        max_connections: int = 30,
        max_keepalive_connections: int = 10,
        retry_attempts: int = 3,
        backoff_min: float = 0.5,
        backoff_max: float = 10.0,
        http2: bool = True,
        user_agents: Optional[List[str]] = None,
        base_headers: Optional[Dict[str, str]] = None,
        retry_for_statuses: Optional[Iterable[int]] = None,
        respect_retry_after: bool = True,
    ):
        self.logger = logging.getLogger(__name__)
        self.timeout = httpx.Timeout(timeout)
        self.concurrency = concurrency
        self.retry_attempts = retry_attempts
        self.backoff_min = backoff_min
        self.backoff_max = backoff_max
        self.http2 = http2
        self.user_agents = user_agents or self.DEFAULT_USER_AGENTS
        self.retry_for_statuses = set(retry_for_statuses or [408, 425, 429, 500, 502, 503, 504])
        self.respect_retry_after = respect_retry_after
        self.limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections
        )
        self.base_headers = base_headers or {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Sec-CH-UA': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': '"Windows"',
            'Upgrade-Insecure-Requests': '1'
        }
        self.client = httpx.Client(
            http2=self.http2,
            limits=self.limits,
            timeout=self.timeout,
            follow_redirects=True
        )

    def _should_retry(self, exc: Exception) -> bool:
        if isinstance(exc, httpx.HTTPStatusError):
            response = exc.response
            if response is None:
                return False
            return response.status_code in self.retry_for_statuses
        return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))

    def _retry_kwargs(self) -> Dict[str, Any]:
        return {
            'stop': stop_after_attempt(self.retry_attempts),
            'wait': wait_random_exponential(
                multiplier=max(self.backoff_min, 0.1),
                max=self.backoff_max
            ),
            'retry': retry_if_exception(self._should_retry),
            'reraise': True
        }

    def _handle_response(self, response: httpx.Response):
        if response.status_code in self.retry_for_statuses and self.respect_retry_after:
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                try:
                    delay = int(retry_after)
                    time.sleep(min(delay, 30))
                except ValueError:
                    pass
        if response.status_code >= 400:
            response.raise_for_status()

    def _build_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = self.base_headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def fetch(self, url: str, *, method: str = 'GET', **kwargs) -> httpx.Response:
        """同步抓取单个URL"""
        headers = kwargs.pop('headers', None)
        try:
            for attempt in Retrying(**self._retry_kwargs()):
                with attempt:
                    response = self.client.request(
                        method,
                        url,
                        headers=self._build_headers(headers),
                        **kwargs
                    )
                    self._handle_response(response)
                    return response
        except RetryError as exc:
            last_exc = exc.last_attempt.exception()
            status_code = None
            if isinstance(last_exc, httpx.HTTPStatusError) and last_exc.response is not None:
                status_code = last_exc.response.status_code
            self.logger.error("请求 %s 失败: %s", url, last_exc)
            raise FetchError(str(last_exc), status_code=status_code, url=url) from last_exc
        except Exception as exc:  # noqa: BLE001
            status_code = None
            if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
                status_code = exc.response.status_code
            self.logger.error("请求 %s 异常: %s", url, exc)
            raise FetchError(str(exc), status_code=status_code, url=url) from exc

    def fetch_many(
        self,
        urls: Iterable[str],
        *,
        method: str = 'GET',
        concurrency: Optional[int] = None,
        failure_callback: Optional[Callable[[str, Optional[int], str], None]] = None,
        **kwargs
    ) -> Dict[str, Optional[httpx.Response]]:
        """批量并发抓取，返回URL->响应的映射"""
        url_list = [url for url in urls if url]
        if not url_list:
            return {}
        limit = concurrency or self.concurrency
        return asyncio.run(self._fetch_many_async(url_list, method, limit, failure_callback=failure_callback, **kwargs))

    async def _fetch_many_async(
        self,
        urls: List[str],
        method: str,
        concurrency: int,
        failure_callback: Optional[Callable[[str, Optional[int], str], None]] = None,
        **kwargs
    ) -> Dict[str, Optional[httpx.Response]]:
        semaphore = asyncio.Semaphore(max(concurrency, 1))
        results: Dict[str, Optional[httpx.Response]] = {}
        headers = kwargs.pop('headers', None)

        async with httpx.AsyncClient(
            http2=self.http2,
            limits=self.limits,
            timeout=self.timeout,
            follow_redirects=True
        ) as client:

            async def _fetch_single(url: str):
                async with semaphore:
                    try:
                        async for attempt in AsyncRetrying(**self._retry_kwargs()):
                            with attempt:
                                response = await client.request(
                                    method,
                                    url,
                                    headers=self._build_headers(headers),
                                    **kwargs
                                )
                                self._handle_response(response)
                                results[url] = response
                                return
                    except RetryError as exc:
                        last_exc = exc.last_attempt.exception()
                        status_code = None
                        if isinstance(last_exc, httpx.HTTPStatusError) and last_exc.response is not None:
                            status_code = last_exc.response.status_code
                        self.logger.warning("批量请求 %s 重试耗尽: %s", url, last_exc)
                        if failure_callback:
                            failure_callback(url, status_code, str(last_exc))
                        results[url] = None
                    except httpx.HTTPStatusError as exc:
                        status_code = exc.response.status_code if exc.response else None
                        self.logger.warning("批量请求 %s 状态异常: %s", url, exc)
                        if failure_callback:
                            failure_callback(url, status_code, str(exc))
                        results[url] = None
                    except Exception as exc:  # noqa: BLE001
                        self.logger.warning("批量请求 %s 失败: %s", url, exc)
                        if failure_callback:
                            failure_callback(url, None, str(exc))
                        results[url] = None

            await asyncio.gather(*[_fetch_single(url) for url in urls])

        # 确保所有URL都有记录
        for url in urls:
            results.setdefault(url, None)
        return results

    def close(self):
        """关闭底层客户端"""
        self.client.close()
