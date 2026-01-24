"""
页面解析器
解析公告列表页和详情页
"""
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from config.settings import REQUIRED_KEYWORDS, EXCLUDE_KEYWORDS, MAX_AGE_DAYS

logger = logging.getLogger(__name__)


class ListPageParser:
    """公告列表页解析器"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.parsed_url = urlparse(base_url)

    def parse_items(self, html: str) -> List[Dict]:
        """
        解析公告列表页，提取公告条目

        Args:
            html: 页面HTML内容

        Returns:
            公告条目列表，每个条目包含:
            - title: 标题
            - url: 详情页URL
            - date: 发布日期
        """
        if not html:
            return []

        soup = BeautifulSoup(html, 'lxml')
        items = []

        # 通用解析策略：尝试多种常见的列表选择器
        selectors = [
            ('a', {'class': re.compile(r'title|link|item', re.I)}),
            ('a', {'href': re.compile(r'\.(html|shtml|asp)$', re.I)}),
            ('li', {}),
            ('tr', {}),
            ('div', {'class': re.compile(r'item|list|row', re.I)}),
        ]

        for tag, attrs in selectors:
            found = self._try_parse_selector(soup, tag, attrs)
            if found:
                items.extend(found)
                if len(items) > 10:  # 找到足够多的条目就停止
                    break

        # 过滤和清洗数据
        filtered_items = self._filter_items(items)
        logger.info(f"从列表页解析出 {len(filtered_items)} 个公告")
        return filtered_items

    def _try_parse_selector(self, soup: BeautifulSoup, tag: str, attrs: Dict) -> List[Dict]:
        """尝试用特定选择器解析"""
        items = []
        elements = soup.find_all(tag, attrs=attrs, limit=100)

        for elem in elements:
            # 查找链接
            link = elem.find('a') if elem.name != 'a' else elem
            if not link:
                continue

            # 获取标题
            title = link.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            # 获取URL
            href = link.get('href', '')
            if not href:
                continue

            # 转换为绝对URL
            url = self._make_absolute_url(href)
            if not url:
                continue

            # 获取日期
            date = self._extract_date(elem)

            items.append({
                'title': title,
                'url': url,
                'date': date
            })

        return items

    def _make_absolute_url(self, url: str) -> Optional[str]:
        """将相对URL转换为绝对URL"""
        if not url:
            return None

        # 如果是完整URL，直接返回
        if url.startswith('http'):
            return url

        # 处理相对路径
        absolute = urljoin(self.base_url, url)

        # 只保留同域名的URL
        parsed = urlparse(absolute)
        if parsed.netloc and parsed.netloc != self.parsed_url.netloc:
            return None

        return absolute

    def _extract_date(self, element) -> Optional[str]:
        """从元素中提取日期"""
        # 尝试多种日期格式
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{4}\.\d{2}\.\d{2}',
            r'\d{4}/\d{2}/\d{2}',
            r'\d{4}年\d{1,2}月\d{1,2}日',
        ]

        text = element.get_text()
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        return None

    def _filter_items(self, items: List[Dict]) -> List[Dict]:
        """过滤公告条目"""
        filtered = []

        # 计算日期阈值
        date_threshold = datetime.now() - timedelta(days=MAX_AGE_DAYS)

        for item in items:
            title = item.get('title', '')

            # 检查必须包含的关键词
            has_required = any(kw in title for kw in REQUIRED_KEYWORDS)
            if not has_required:
                continue

            # 检查排除关键词
            has_excluded = any(kw in title for kw in EXCLUDE_KEYWORDS)
            if has_excluded:
                continue

            # 检查日期（如果有的话）
            date_str = item.get('date')
            if date_str:
                try:
                    # 简单的日期解析
                    date_str = re.sub(r'[年月./]', '-', date_str).replace('日', '')
                    item_date = datetime.strptime(date_str.split()[0], '%Y-%m-%d')
                    if item_date < date_threshold:
                        continue
                except:
                    pass  # 日期解析失败，忽略

            filtered.append(item)

        return filtered


class DetailPageParser:
    """公告详情页解析器"""

    def parse(self, html: str, url: str) -> Dict:
        """
        解析公告详情页

        Args:
            html: 页面HTML内容
            url: 页面URL

        Returns:
            解析结果字典:
            - title: 标题
            - content: 正文内容
            - publish_date: 发布日期
        """
        if not html:
            return {}

        soup = BeautifulSoup(html, 'lxml')

        # 提取标题
        title = self._extract_title(soup)

        # 提取正文
        content = self._extract_content(soup)

        # 提取发布日期
        publish_date = self._extract_publish_date(soup)

        result = {
            'url': url,
            'title': title,
            'content': content,
            'publish_date': publish_date,
            'scraped_at': datetime.now().isoformat()
        }

        logger.info(f"解析详情页: {title[:30]}...")
        return result

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取标题"""
        # 尝试多种标题选择器
        selectors = [
            ('h1', {}),
            ('h2', {}),
            ('title', {}),
            ('*', {'class': re.compile(r'title|heading', re.I)}),
        ]

        for tag, attrs in selectors:
            elem = soup.find(tag, attrs)
            if elem:
                title = elem.get_text(strip=True)
                if len(title) > 5:
                    return title

        return "未知标题"

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """提取正文内容"""
        # 移除不需要的标签
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.decompose()

        # 尝试找到正文容器
        content_selectors = [
            ('div', {'class': re.compile(r'content|article|detail|main', re.I)}),
            ('div', {'id': re.compile(r'content|article|detail', re.I)}),
            ('article', {}),
            ('main', {}),
        ]

        for tag, attrs in content_selectors:
            elem = soup.find(tag, attrs)
            if elem:
                return elem.get_text(separator='\n', strip=True)

        # 如果找不到特定容器，返回body的文本
        body = soup.find('body')
        if body:
            return body.get_text(separator='\n', strip=True)

        return ""

    def _extract_publish_date(self, soup: BeautifulSoup) -> Optional[str]:
        """提取发布日期"""
        # 查找包含日期的元素
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{4}\.\d{2}\.\d{2}',
            r'\d{4}/\d{2}/\d{2}',
            r'\d{4}年\d{1,2}月\d{1,2}日',
        ]

        text = soup.get_text()
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        return None
