"""
公共资源交易平台搜索（bxsearch）抓取

说明：
- 该模块只做「公开页面」的检索与解析，不保证不会触发网站的访问频率限制。
- 实际使用时应降低频率、做缓存、并在出现"访问过于频繁"提示时停止重试。
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from config.settings import (
    BROWSER_NAVIGATION_TIMEOUT,
    PAGE_TURN_DELAY_MIN,
    PAGE_TURN_DELAY_MAX,
    SIMULATE_HUMAN_BEHAVIOR,
)

logger = logging.getLogger(__name__)


PIN_MU_MAP = {
    "all": 0,
    "goods": 1,
    "engineering": 2,
    "services": 3,
}

BID_SORT_MAP = {
    "all": 0,
    "central": 1,
    "local": 2,
}

SEARCH_TYPE_MAP = {
    "title": 1,
    "fulltext": 2,
}

TIME_TYPE_MAP = {
    "today": 0,
    "3days": 1,
    "1week": 2,
    "1month": 3,
    "3months": 4,
    "halfyear": 5,
    "custom": 6,
}

# bidType: 0=所有类型, 1=公开招标, 2=询价公告, 3=竞争性谈判, 4=单一来源, 5=资格预审,
#         6=邀请公告, 7=中标公告, 8=更正公告, 9=其他公告, 10=竞争性磋商, 11=成交公告, 12=终止公告
BID_TYPE_NAME_MAP = {
    "all": 0,
    "所有类型": 0,
    "公开招标": 1,
    "询价公告": 2,
    "竞争性谈判": 3,
    "单一来源": 4,
    "资格预审": 5,
    "邀请公告": 6,
    "中标公告": 7,
    "更正公告": 8,
    "其他公告": 9,
    "竞争性磋商": 10,
    "成交公告": 11,
    "终止公告": 12,
}


def _to_int(value: Union[str, int], mapping: Dict[str, int], *, name: str) -> int:
    if isinstance(value, int):
        return value
    value = (value or "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    if value.isdigit():
        return int(value)
    if value in mapping:
        return mapping[value]
    raise ValueError(f"Unsupported {name}: {value}")


def _date_to_colon(date_str: str) -> str:
    # Accept YYYY-MM-DD or YYYY:MM:DD
    s = (date_str or "").strip()
    if not s:
        return ""
    if ":" in s:
        return s
    return s.replace("-", ":")


@dataclass(frozen=True)
class BxSearchParams:
    kw: str
    search_type: Union[str, int] = "fulltext"
    bid_sort: Union[str, int] = "all"
    pin_mu: Union[str, int] = "all"
    bid_type: Union[str, int] = "all"
    time_type: Union[str, int] = "1week"
    start_date: str = ""
    end_date: str = ""


class CCGPBxSearcher:
    """bxsearch 列表页搜索器（同步）"""

    BASE_URL = "https://search.ccgp.gov.cn/bxsearch"
    RESULT_ITEM_SELECTOR = "ul.vT-srch-result-list-bid > li"
    NEXT_PAGE_SELECTOR = "a.next"

    def __init__(self, page: Page):
        self.page = page

    def build_url(self, params: BxSearchParams, page_index: int = 1) -> str:
        searchtype = _to_int(params.search_type, SEARCH_TYPE_MAP, name="search_type")
        bid_sort = _to_int(params.bid_sort, BID_SORT_MAP, name="bid_sort")
        pin_mu = _to_int(params.pin_mu, PIN_MU_MAP, name="pin_mu")
        bid_type = _to_int(params.bid_type, BID_TYPE_NAME_MAP, name="bid_type")
        time_type = _to_int(params.time_type, TIME_TYPE_MAP, name="time_type")

        start_time = _date_to_colon(params.start_date)
        end_time = _date_to_colon(params.end_date)

        # 自定义时间必须提供日期
        if time_type == 6 and (not start_time or not end_time):
            raise ValueError("custom time_type requires start_date and end_date")

        query = {
            "searchtype": str(searchtype),
            "page_index": str(page_index),
            "start_time": start_time,
            "end_time": end_time,
            "timeType": str(time_type),
            "searchparam": "",
            "searchchannel": "0",
            "dbselect": "bidx",
            "kw": params.kw or "",
            "bidSort": str(bid_sort),
            "pinMu": str(pin_mu),
            "bidType": str(bid_type),
            "buyerName": "",
            "projectId": "",
            "displayZone": "",
            "zoneId": "",
            "agentName": "",
            "pppStatus": "0",
        }

        return f"{self.BASE_URL}?{urlencode(query, safe=':')}"

    def search(self, params: BxSearchParams, max_pages: int = 5) -> List[Dict]:
        """
        执行 bxsearch 搜索，返回列表页结果（不抓详情页）

        Returns items:
            - title
            - url
            - publish_date
            - buyer_name
            - agent_name
        """
        url = self.build_url(params, page_index=1)
        logger.info(f"bxsearch: {url}")

        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_NAVIGATION_TIMEOUT)
        except PlaywrightTimeoutError:
            logger.error("bxsearch 页面加载超时")
            return []

        if self._is_blocked():
            logger.error("检测到访问频率限制（访问过于频繁/稍后再试），已停止。")
            return []

        results: List[Dict] = []
        seen: set[str] = set()

        for _ in range(max_pages):
            page_results = self._scrape_current_page()
            for r in page_results:
                u = r.get("url") or ""
                if u and u not in seen:
                    seen.add(u)
                    results.append(r)

            if not self._go_next_page():
                break

            # 翻页延迟（模拟人类浏览行为）
            delay = random.uniform(PAGE_TURN_DELAY_MIN, PAGE_TURN_DELAY_MAX)
            logger.debug(f"[翻页延迟] {delay:.1f}秒")
            time.sleep(delay)
            
            # 模拟滚动行为
            if SIMULATE_HUMAN_BEHAVIOR:
                try:
                    self.page.evaluate("window.scrollTo(0, 0)")
                    time.sleep(random.uniform(0.3, 0.6))
                    scroll_y = random.randint(200, 400)
                    self.page.evaluate(f"window.scrollBy(0, {scroll_y})")
                except Exception:
                    pass

            if self._is_blocked():
                logger.error("翻页后触发访问频率限制，已停止。")
                break

        return results

    def _is_blocked(self) -> bool:
        try:
            text = self.page.evaluate("() => document.body && document.body.innerText ? document.body.innerText : ''")
        except Exception:
            return False
        return ("访问过于频繁" in text) or ("稍后再试" in text)

    def _scrape_current_page(self) -> List[Dict]:
        html = self.page.content()
        soup = BeautifulSoup(html, "lxml")
        items: List[Dict] = []

        for li in soup.select(self.RESULT_ITEM_SELECTOR):
            a = li.find("a", href=True)
            if not a:
                continue

            title = a.get_text(" ", strip=True)
            href = (a.get("href") or "").strip()
            if not title or not href:
                continue

            if not href.startswith("http"):
                href = urljoin("https://www.ccgp.gov.cn/", href)

            info_text = ""
            span = li.find("span")
            if span:
                info_text = span.get_text(" ", strip=True)

            publish_date = ""
            buyer = ""
            agent = ""
            if info_text:
                parts = [p.strip() for p in info_text.split("|") if p.strip()]
                if parts:
                    publish_date = parts[0]
                for p in parts[1:]:
                    if p.startswith("采购人："):
                        buyer = p.replace("采购人：", "", 1).strip()
                    elif p.startswith("代理机构："):
                        agent = p.replace("代理机构：", "", 1).strip()

            items.append({
                "title": title,
                "url": href,
                "publish_date": publish_date,
                "buyer_name": buyer,
                "agent_name": agent,
                "source": "ccgp-bxsearch",
            })

        return items

    def _go_next_page(self) -> bool:
        try:
            next_button = self.page.query_selector(self.NEXT_PAGE_SELECTOR)
            if not next_button:
                return False

            with self.page.expect_navigation(wait_until="domcontentloaded", timeout=BROWSER_NAVIGATION_TIMEOUT):
                next_button.click()
            return True
        except Exception:
            return False

