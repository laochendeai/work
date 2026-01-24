"""
基础爬虫类
统一的爬虫接口
"""
import logging
import sys
from pathlib import Path
from typing import List, Dict, Generator

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.fetcher import PlaywrightFetcher
from scraper.parser import ListPageParser, DetailPageParser
from config.settings import MAX_PAGES, MAX_RETRIES, RETRY_DELAY

logger = logging.getLogger(__name__)


class BaseScraper:
    """基础爬虫类"""

    def __init__(self, source_config: Dict):
        """
        初始化爬虫

        Args:
            source_config: 数据源配置字典
                - name: 源名称
                - url: 源URL
                - list_page: 列表页路径
        """
        self.config = source_config
        self.name = source_config.get('name', '未知')
        self.base_url = source_config.get('url', '')
        self.list_path = source_config.get('list_page', '')

        # 构建列表页URL
        self.list_url = self.base_url + self.list_path

        self.fetcher = PlaywrightFetcher()
        self.list_parser = ListPageParser(self.base_url)
        self.detail_parser = DetailPageParser()

        logger.info(f"初始化爬虫: {self.name} ({self.list_url})")

    def scrape(self) -> Generator[Dict, None, None]:
        """
        执行爬取

        Yields:
            公告详情字典
        """
        try:
            # 启动浏览器
            self.fetcher.start()

            # 1. 获取列表页
            logger.info(f"正在获取列表页: {self.list_url}")
            list_html = self.fetcher.get_page(self.list_url)

            if not list_html:
                logger.error(f"获取列表页失败: {self.list_url}")
                return

            # 2. 解析列表页
            items = self.list_parser.parse_items(list_html)
            if not items:
                logger.warning(f"未找到公告条目: {self.name}")
                return

            logger.info(f"解析出 {len(items)} 个公告条目")

            # 3. 限制数量
            items = items[:MAX_PAGES * MAX_ITEMS_PER_PAGE]

            # 4. 逐个获取详情页
            for i, item in enumerate(items, 1):
                detail = self._fetch_detail_with_retry(item)
                if detail:
                    yield detail
                logger.info(f"进度: {i}/{len(items)}")

        except Exception as e:
            logger.error(f"爬取失败 {self.name}: {e}")
        finally:
            # 关闭浏览器
            self.fetcher.stop()

    def _fetch_detail_with_retry(self, item: Dict) -> Dict:
        """
        获取详情页（带重试）

        Args:
            item: 列表项字典

        Returns:
            详情页字典
        """
        url = item['url']

        for attempt in range(MAX_RETRIES):
            try:
                html = self.fetcher.get_page(url)
                if html:
                    detail = self.detail_parser.parse(html, url)
                    detail.update({
                        'list_title': item.get('title'),
                        'list_date': item.get('date'),
                        'source': self.name
                    })
                    return detail
                else:
                    logger.warning(f"获取详情页失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {url}")

            except Exception as e:
                logger.error(f"获取详情页异常 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")

            # 重试前等待
            import time
            time.sleep(RETRY_DELAY)

        return {}

    def __repr__(self):
        return f"<BaseScraper {self.name}>"
