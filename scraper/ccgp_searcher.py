"""
中国政府采购网智能搜索爬虫
完全模拟人工操作，支持关键词搜索和条件过滤
"""
import logging
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

from config.settings import BROWSER_TIMEOUT, BROWSER_NAVIGATION_TIMEOUT

logger = logging.getLogger(__name__)


class CCGPSearcher:
    """中国政府采购网搜索爬虫"""

    # 搜索平台URL
    SEARCH_URL = "http://search.ccgp.gov.cn/bxsearch"

    # 选择器配置
    SELECTORS = {
        # 搜索输入框
        'search_input': '#kw',

        # 搜索按钮
        'search_title_button': '#doSearch1',
        'search_fulltext_button': '#doSearch2',

        # 品目选择
        'category_item': lambda item: f'text="{item}"',
        'category_engineering': 'text="工程类"',
        'category_goods': 'text="货物类"',
        'category_services': 'text="服务类"',

        # 时间选择
        'time_today': 'text="今日"',
        'time_3days': 'text="近3日"',
        'time_1week': 'text="近1周"',
        'time_1month': 'text="近1月"',

        # 类型选择
        'type_all': 'text="所有类型"',

        # 类别选择
        'region_all': 'text="所有类别"',

        # 搜索结果
        'result_items': 'ul.vT-srch-result-list-bid > li',
        'result_link': 'ul.vT-srch-result-list-bid > li > a',

        # 分页
        'next_page': 'a.next',
    }

    def __init__(self, page: Page):
        """
        初始化搜索爬虫

        Args:
            page: Playwright页面对象
        """
        self.page = page
        self.base_url = self.SEARCH_URL

    def search(
        self,
        keyword: str,
        search_type: str = "fulltext",  # "title" or "fulltext"
        category: str = "engineering",  # "engineering", "goods", "services", "all"
        time_range: str = "today",  # "today", "3days", "1week", "1month"
        announcement_type: str = "all",  # "all", "public", "inquiry", etc.
        region: str = "all",  # "all", "central", "local"
        max_pages: int = 5,
    ) -> List[Dict]:
        """
        执行搜索

        Args:
            keyword: 搜索关键词
            search_type: 搜索类型 (title=搜标题, fulltext=搜全文)
            category: 品目 (engineering=工程类, goods=货物类, services=服务类, all=所有品目)
            time_range: 时间范围 (today, 3days, 1week, 1month)
            announcement_type: 公告类型
            region: 类别 (all, central, local)
            max_pages: 最多爬取页数

        Returns:
            搜索结果列表
        """
        logger.info(f"开始搜索: 关键词='{keyword}', 品目={category}, 时间={time_range}")

        # 1. 先访问主页，建立会话
        try:
            self.page.goto("https://www.ccgp.gov.cn/", timeout=BROWSER_NAVIGATION_TIMEOUT, wait_until="domcontentloaded")
            logger.info("已访问主页")
            time.sleep(2)
        except:
            pass

        # 2. 访问搜索页面
        try:
            self.page.goto(self.SEARCH_URL, timeout=BROWSER_NAVIGATION_TIMEOUT, wait_until="domcontentloaded")
            logger.info("搜索页面加载成功")
        except PlaywrightTimeoutError:
            logger.error("搜索页面加载超时")
            return []

        time.sleep(3)  # 等待页面完全加载和反爬检测

        # 3. 检查是否被封禁
        try:
            page_text = self.page.evaluate("() => document.body && document.body.innerText ? document.body.innerText : ''")
        except Exception:
            page_text = ""
        if "访问过于频繁" in page_text or "稍后再试" in page_text:
            logger.error("⚠️ 检测到反爬限制，请稍后再试")
            return []

        # 4. 设置过滤条件
        self._set_category(category)
        time.sleep(1)

        self._set_time_range(time_range)
        time.sleep(1)

        self._set_announcement_type(announcement_type)
        time.sleep(1)

        self._set_region(region)
        time.sleep(1)

        # 5. 输入搜索关键词
        self._input_keyword(keyword)
        time.sleep(1)

        # 6. 点击搜索按钮
        self._click_search_button(search_type)

        # 7. 等待搜索结果
        logger.info("等待搜索结果加载...")
        try:
            self.page.wait_for_selector(self.SELECTORS['result_items'], timeout=15000)
        except Exception:
            time.sleep(5)

        # 8. 爬取搜索结果
        results = []
        for page_num in range(1, max_pages + 1):
            logger.info(f"正在爬取第 {page_num} 页...")

            page_results = self._scrape_current_page()
            results.extend(page_results)

            logger.info(f"第 {page_num} 页获取到 {len(page_results)} 条结果")

            # 如果没有更多结果，退出
            if len(page_results) == 0:
                logger.info("没有更多结果了")
                break

            # 如果不是最后一页，点击下一页
            if page_num < max_pages:
                if not self._go_to_next_page():
                    logger.info("没有下一页了")
                    break

                time.sleep(3)  # 增加翻页等待时间

        logger.info(f"搜索完成！共获取 {len(results)} 条结果")
        return results

    def _set_category(self, category: str):
        """设置品目"""
        category_map = {
            'engineering': '工程类',
            'goods': '货物类',
            'services': '服务类',
            'all': '所有品目',
        }

        if category in category_map:
            text = category_map[category]
            # 查找品目行中的按钮
            # 需要通过角色或文本定位
            try:
                # 尝试点击品目标签后的按钮
                self.page.click(f'text="{text}"', timeout=5000)
                logger.info(f"已设置品目: {text}")
            except:
                logger.warning(f"设置品目失败: {text}")

    def _set_time_range(self, time_range: str):
        """设置时间范围"""
        time_map = {
            'today': '今日',
            '3days': '近3日',
            '1week': '近1周',
            '1month': '近1月',
        }

        if time_range in time_map:
            text = time_map[time_range]
            try:
                self.page.click(f'text="{text}"', timeout=5000)
                logger.info(f"已设置时间: {text}")
            except:
                logger.warning(f"设置时间失败: {text}")

    def _set_announcement_type(self, announcement_type: str):
        """设置公告类型"""
        if announcement_type == 'all':
            try:
                self.page.click('text="所有类型"', timeout=5000)
                logger.info("已设置类型: 所有类型")
            except:
                pass

    def _set_region(self, region: str):
        """设置类别"""
        if region == 'all':
            try:
                self.page.click('text="所有类别"', timeout=5000)
                logger.info("已设置类别: 所有类别")
            except:
                pass

    def _input_keyword(self, keyword: str):
        """输入搜索关键词"""
        try:
            input_elem = self.page.query_selector(self.SELECTORS['search_input'])
            if not input_elem:
                logger.warning("未找到搜索输入框")
                return

            input_elem.fill("")
            input_elem.fill(keyword)
            logger.info(f"已输入关键词: {keyword}")
        except Exception as e:
            logger.error(f"输入关键词失败: {e}")

    def _click_search_button(self, search_type: str):
        """点击搜索按钮"""
        button_map = {
            'title': self.SELECTORS['search_title_button'],
            'fulltext': self.SELECTORS['search_fulltext_button'],
        }

        selector = button_map.get(search_type, self.SELECTORS['search_fulltext_button'])
        try:
            with self.page.expect_navigation(wait_until="domcontentloaded", timeout=BROWSER_NAVIGATION_TIMEOUT):
                self.page.click(selector, timeout=5000)
            logger.info(f"已点击搜索按钮: {search_type}")
        except Exception as e:
            logger.error(f"点击搜索按钮失败: {e}")

    def _scrape_current_page(self) -> List[Dict]:
        """爬取当前页面的搜索结果"""
        results: List[Dict] = []

        try:
            self.page.wait_for_selector(self.SELECTORS['result_items'], timeout=15000)
        except Exception:
            logger.warning("等待搜索结果超时")
            return results

        html = self.page.content()
        soup = BeautifulSoup(html, "lxml")

        for li in soup.select(self.SELECTORS['result_items']):
            a = li.find("a", href=True)
            if not a:
                continue

            title = a.get_text(" ", strip=True)
            href = a.get("href", "").strip()
            if not title or not href:
                continue

            if href and not href.startswith("http"):
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
                'title': title,
                'url': href,
                'publish_date': publish_date,
                'buyer_name': buyer,
                'agent_name': agent,
                'source': '中国政府采购网搜索',
            })

        # 去重（按URL）
        dedup: Dict[str, Dict] = {}
        for r in results:
            u = r.get("url") or ""
            if u and u not in dedup:
                dedup[u] = r

        return list(dedup.values())

    def _go_to_next_page(self) -> bool:
        """翻到下一页"""
        try:
            next_button = self.page.query_selector(self.SELECTORS['next_page'])
            if not next_button:
                return False

            with self.page.expect_navigation(wait_until="domcontentloaded", timeout=BROWSER_NAVIGATION_TIMEOUT):
                next_button.click()
            return True
        except Exception as e:
            logger.debug(f"翻页失败: {e}")
            return False
