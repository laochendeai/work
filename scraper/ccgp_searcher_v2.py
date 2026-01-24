#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政府采购网智能搜索爬虫 - 增强版（纯同步）
使用多种策略降低触发反爬限制的风险
"""
import logging
import random
import time
from typing import Dict, List
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class CCGPSearcherEnhanced:
    """政府采购网智能搜索爬虫 - 增强版（纯同步实现）"""

    # 搜索平台URL
    SEARCH_URL = "http://search.ccgp.gov.cn/bxsearch"

    # 随机User-Agent池
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    ]

    def __init__(self, page: Page):
        """
        初始化搜索爬虫

        Args:
            page: Playwright页面对象
        """
        self.page = page
        self._setup_user_agent()

    def _setup_user_agent(self):
        """设置随机User-Agent"""
        user_agent = random.choice(self.USER_AGENTS)
        self.page.set_extra_http_headers({
            'User-Agent': user_agent,
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.ccgp.gov.cn/',
        })
        logger.debug(f"使用User-Agent: {user_agent[:50]}...")

    def _random_delay(self, min_sec: float, max_sec: float):
        """随机延迟"""
        delay = random.uniform(min_sec, max_sec)
        logger.debug(f"延迟 {delay:.1f} 秒")
        time.sleep(delay)

    def _simulate_human_browsing(self):
        """模拟人类浏览行为"""
        # 随机滚动页面
        try:
            scroll_y = random.randint(0, 300)
            self.page.evaluate(f"window.scrollTo(0, {scroll_y});")
            self._random_delay(0.5, 1.5)
        except:
            pass

    def _is_blocked(self, page_text: str) -> bool:
        """检查是否被封禁"""
        blocked_indicators = [
            '访问过于频繁',
            '稍后再试',
            '验证码',
            'captcha',
            '人机验证',
        ]

        page_text_lower = page_text.lower()
        for indicator in blocked_indicators:
            if indicator in page_text_lower:
                return True

        return False

    def search(
        self,
        keyword: str,
        search_type: str = "fulltext",
        category: str = "engineering",
        time_range: str = "today",
        max_pages: int = 3,
        min_delay: float = 3.0,
        max_delay: float = 6.0,
    ) -> List[Dict]:
        """
        安全搜索 - 使用多种策略降低反爬风险

        Args:
            keyword: 搜索关键词
            search_type: 搜索类型 (title=搜标题, fulltext=搜全文)
            category: 品目 (engineering=工程类, goods=货物类, services=服务类)
            time_range: 时间范围 (today, 3days, 1week, 1month)
            max_pages: 最多爬取页数
            min_delay: 最小延迟（秒）
            max_delay: 最大延迟（秒）

        Returns:
            搜索结果列表
        """
        logger.info(f"开始安全搜索: 关键词='{keyword}', 品目={category}, 时间={time_range}")

        # 策略1: 先访问首页建立会话
        try:
            self.page.goto("https://www.ccgp.gov.cn/",
                          wait_until="domcontentloaded",
                          timeout=30000)
            logger.info("✅ 已访问首页")
            self._simulate_human_browsing()
            self._random_delay(2, 4)
        except Exception as e:
            logger.warning(f"访问首页失败: {e}")

        # 策略2: 访问搜索页面
        try:
            self.page.goto(self.SEARCH_URL,
                          wait_until="domcontentloaded",
                          timeout=30000)
            logger.info("✅ 搜索页面加载成功")
            self._simulate_human_browsing()
            self._random_delay(4, 7)
        except Exception as e:
            logger.error(f"❌ 访问搜索页面失败: {e}")
            return []

        # 策略3: 检查是否被封禁
        try:
            page_text = self.page.evaluate("() => document.body.innerText")
            if self._is_blocked(page_text):
                logger.error("⚠️ 检测到反爬限制")
                logger.error("建议：降低访问频率并稍后再试，或改用公开的分类列表页抓取 + 本地过滤。")
                return []
        except Exception as e:
            logger.debug(f"检查封禁状态失败: {e}")
            # 无法读取页面文本时不直接判定失败，继续尝试搜索
            pass

        # 策略4: 模拟人工操作填写表单
        self._fill_search_form_safe(keyword, category, time_range)

        # 策略5: 执行搜索
        self._perform_search_safe(search_type)

        # 策略6: 等待结果加载
        logger.info("等待搜索结果加载...")
        self._random_delay(7, 12)

        # 策略7: 分页爬取
        results = []
        for page_num in range(1, max_pages + 1):
            logger.info(f"正在爬取第 {page_num} 页...")

            page_results = self._scrape_current_page_safe()
            results.extend(page_results)

            logger.info(f"第 {page_num} 页获取到 {len(page_results)} 条结果")

            if len(page_results) == 0:
                logger.info("没有更多结果了")
                break

            # 翻页前增加较长的随机延迟
            if page_num < max_pages:
                self._random_delay(min_delay, max_delay)
                if not self._go_to_next_page_safe():
                    logger.info("没有下一页了")
                    break

        logger.info(f"搜索完成！共获取 {len(results)} 条结果")
        return results

    def _fill_search_form_safe(self, keyword: str, category: str, time_range: str):
        """安全填写搜索表单"""
        logger.info("正在填写搜索表单...")

        # 1. 点击品目
        if category == "engineering":
            try:
                self.page.click('text="工程类"', timeout=5000)
                self._random_delay(0.8, 1.5)
                logger.info("  ✅ 已选择: 工程类")
            except Exception as e:
                logger.debug(f"  ⚠️ 选择品目失败: {e}")

        # 2. 点击时间
        time_map = {
            'today': '今日',
            '3days': '近3日',
            '1week': '近1周',
            '1month': '近1月',
        }

        if time_range in time_map:
            try:
                self.page.click(f'text="{time_map[time_range]}"', timeout=5000)
                self._random_delay(0.8, 1.5)
                logger.info(f"  ✅ 已选择: {time_map[time_range]}")
            except Exception as e:
                logger.debug(f"  ⚠️ 选择时间失败: {e}")

        # 3. 输入关键词（模拟人工打字）
        try:
            input_selectors = [
                '#kw',
                'input[name="kw"]',
            ]

            for selector in input_selectors:
                try:
                    input_elem = self.page.query_selector(selector)
                    if input_elem:
                        # 清空并逐字输入
                        input_elem.fill('')
                        self._type_like_human(input_elem, keyword)
                        logger.info(f"  ✅ 已输入关键词: {keyword}")
                        self._random_delay(1, 2)
                        break
                except:
                    continue
        except Exception as e:
            logger.debug(f"  ⚠️ 输入关键词失败: {e}")

    def _type_like_human(self, element, text: str):
        """模拟人类打字（逐字输入）"""
        try:
            # 清空
            element.fill('')
            # 逐字输入
            for char in text:
                element.type(char)
                time.sleep(random.randint(80, 200) / 1000)  # 每个字符间隔80-200ms
        except Exception as e:
            # 如果逐字输入失败，直接填入
            try:
                element.fill(text)
            except:
                pass

    def _perform_search_safe(self, search_type: str):
        """安全执行搜索"""
        button_map = {
            'title': '#doSearch1',
            'fulltext': '#doSearch2',
        }

        button_selector = button_map.get(search_type, '#doSearch2')
        try:
            with self.page.expect_navigation(wait_until="domcontentloaded", timeout=30000):
                self.page.click(button_selector, timeout=5000)
            logger.info(f"  ✅ 已点击搜索按钮: {search_type}")
            self._random_delay(1, 2)
        except Exception as e:
            logger.error(f"  ❌ 点击搜索按钮失败: {e}")

    def _scrape_current_page_safe(self) -> List[Dict]:
        """安全爬取当前页面"""
        results = []

        try:
            html = self.page.content()
            soup = BeautifulSoup(html, "lxml")

            for li in soup.select("ul.vT-srch-result-list-bid > li"):
                a = li.find("a", href=True)
                if not a:
                    continue

                title = a.get_text(" ", strip=True)
                href = a.get("href", "").strip()
                if not title or not href:
                    continue

                # 构建完整URL
                if not href.startswith("http"):
                    from urllib.parse import urljoin
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

                results.append({
                    "title": title,
                    "url": href,
                    "publish_date": publish_date,
                    "buyer_name": buyer,
                    "agent_name": agent,
                    "source": "中国政府采购网搜索",
                })

        except Exception as e:
            logger.debug(f"爬取页面失败: {e}")

        # 去重（按URL）
        dedup: Dict[str, Dict] = {}
        for r in results:
            u = r.get("url") or ""
            if u and u not in dedup:
                dedup[u] = r
        return list(dedup.values())

    def _go_to_next_page_safe(self) -> bool:
        """安全翻页"""
        try:
            button = self.page.query_selector("a.next")
            if not button:
                return False

            with self.page.expect_navigation(wait_until="domcontentloaded", timeout=30000):
                button.click()
            self._random_delay(2, 4)
            return True
        except:
            return False
