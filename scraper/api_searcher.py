"""
政府采购网API搜索
使用内部API接口直接获取搜索结果，绕过页面反爬
"""
import logging
import time
from typing import Dict, List
import requests
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class CCGPAPISearcher:
    """政府采购网API搜索器"""

    # API基础URL
    API_BASE = "https://search.ccgp.gov.cn/api"

    def search(
        self,
        keyword: str,
        category: str = "engineering",
        time_range: str = "today",
        page: int = 1,
        page_size: int = 20,
    ) -> List[Dict]:
        """
        使用API搜索公告

        Args:
            keyword: 搜索关键词
            category: 品目 (engineering=工程类, goods=货物类, services=服务类)
            time_range: 时间范围 (today, 3days, 1week, 1month)
            page: 页码
            page_size: 每页数量

        Returns:
            搜索结果列表
        """
        # 构建请求参数
        params = self._build_params(keyword, category, time_range, page, page_size)

        try:
            # 发送请求
            response = requests.post(
                f"{self.API_BASE}/search",
                json=params,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Content-Type': 'application/json',
                    'Referer': 'https://search.ccgp.gov.cn/bxsearch',
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_response(data)
            else:
                logger.error(f"API请求失败: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"API搜索失败: {e}")
            return []

    def _build_params(self, keyword: str, category: str, time_range: str, page: int, page_size: int) -> Dict:
        """构建API请求参数"""
        # 品目映射
        category_map = {
            'engineering': ['工程类'],
            'goods': ['货物类'],
            'services': ['服务类'],
            'all': [],
        }

        # 时间范围映射
        time_map = {
            'today': '1d',
            '3days': '3d',
            '1week': '1w',
            '1month': '1m',
        }

        return {
            'keyword': keyword,
            'searchType': 'fulltext',  # fulltext 或 title
            'category': category_map.get(category, []),
            'timeRange': time_map.get(time_range, '1d'),
            'pageIndex': page,
            'pageSize': page_size,
        }

    def _parse_response(self, data: Dict) -> List[Dict]:
        """解析API响应"""
        results = []

        # 根据实际API响应格式解析
        if 'data' in data:
            items = data['data']
            if isinstance(items, list):
                for item in items:
                    result = {
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'publish_date': item.get('publishDate', ''),
                        'source': '中国政府采购网',
                    }
                    results.append(result)

        return results


class AlternativeListScraper:
    """
    备选方案：从公告列表页搜索

    直接爬取分类列表页，按关键词过滤
    """

    def __init__(self, fetcher):
        self.fetcher = fetcher

    def search_by_category(
        self,
        category: str = "zygg",  # zygg=中央公告
        keyword: str = "智能",
        max_pages: int = 3,
    ) -> List[Dict]:
        """
        通过分类列表页搜索

        Args:
            category: 分类代码
            keyword: 过滤关键词
            max_pages: 最大页数

        Returns:
            符合条件的公告列表
        """
        results = []

        # 中央公告URL
        base_url = "https://www.ccgp.gov.cn/cggg/zygg/index.htm"

        for page in range(1, max_pages + 1):
            if page == 1:
                url = base_url
            else:
                url = f"https://www.ccgp.gov.cn/cggg/zygg/index_{page}.htm"

            logger.info(f"正在爬取第 {page} 页: {url}")

            html = self.fetcher.get_page(url)
            if not html:
                continue

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')

            # 查找所有公告链接
            items = soup.find_all('a')
            for item in items:
                title = item.get_text(strip=True)
                href = item.get('href', '')

                # 过滤：标题必须包含关键词
                if keyword in title and href and 'htm' in href:
                    # 转换为绝对URL
                    if not href.startswith('http'):
                        href = f"https://www.ccgp.gov.cn{href}"

                    results.append({
                        'title': title,
                        'url': href,
                        'source': '中国政府采购网',
                    })

            time.sleep(2)  # 延迟避免被封

        logger.info(f"从列表页找到 {len(results)} 条包含'{keyword}'的公告")
        return results
