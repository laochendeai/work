"""
智能公告解析器
支持多种公共资源交易网站格式
"""
import logging
import re
from typing import Dict, Optional
from bs4 import BeautifulSoup

from .ccgp_parser import CCGPAnnouncementParser

logger = logging.getLogger(__name__)


class SmartAnnouncementParser:
    """
    智能公告解析器

    自动识别网站类型并使用相应的解析策略
    """

    def __init__(self):
        """初始化解析器"""
        self.parsers = {
            'ccgp': CCGPAnnouncementParser(),
            # 可以添加更多网站的解析器
            # 'bidcenter': BidCenterParser(),
            # 'chinabidding': ChinaBiddingParser(),
        }

        # 网站识别模式
        self.site_patterns = {
            'ccgp': [
                r'ccgp\.gov\.cn',
                r'ccgp-.*\.gov\.cn',
            ],
            # 可以添加更多网站模式
        }

    def parse(self, html: str, url: str) -> Dict:
        """
        智能解析公告页面

        Args:
            html: 页面HTML内容
            url: 页面URL

        Returns:
            解析结果字典
        """
        if not html:
            logger.warning("HTML内容为空")
            return {}

        # 识别网站类型
        site_type = self._detect_site_type(url)

        logger.info(f"识别网站类型: {site_type}")

        # 使用相应的解析器
        parser = self.parsers.get(site_type)

        if parser:
            return parser.parse(html, url)
        else:
            # 使用通用解析器
            return self._generic_parse(html, url)

    def _detect_site_type(self, url: str) -> str:
        """
        识别网站类型

        Args:
            url: 页面URL

        Returns:
            网站类型标识
        """
        import re

        for site_type, patterns in self.site_patterns.items():
            for pattern in patterns:
                if re.search(pattern, url):
                    return site_type

        # 默认返回ccgp类型（因为大部分公共资源交易网结构类似）
        return 'ccgp'

    def _generic_parse(self, html: str, url: str) -> Dict:
        """
        通用解析器（当无法识别网站类型时使用）

        尝试提取常见的字段
        """
        soup = BeautifulSoup(html, 'lxml')

        result = {
            'url': url,
            'meta': self._generic_parse_meta(soup),
            'summary_table': {},
            'content_sections': {},
            'contacts': self._generic_extract_contacts(soup),
        }

        return result

    def _generic_parse_meta(self, soup: BeautifulSoup) -> Dict:
        """通用元数据解析"""
        meta = {}

        # 尝试多种方式提取标题
        title_selectors = [
            ('h1', {}),
            ('h2', {}),
            ('title', {}),
            ('*', {'class': re.compile(r'title', re.I)}),
        ]

        for tag, attrs in title_selectors:
            elem = soup.find(tag, attrs)
            if elem:
                title = elem.get_text(strip=True)
                if title and len(title) > 5:
                    meta['title'] = title
                    break

        # 尝试提取日期
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{4}年\d{1,2}月\d{1,2}日',
        ]

        for pattern in date_patterns:
            matches = soup.find_all(string=re.compile(pattern))
            if matches:
                meta['publish_date'] = matches[0].strip()
                break

        return meta

    def _generic_extract_contacts(self, soup: BeautifulSoup) -> Dict:
        """通用联系人提取"""
        contacts = {
            'buyer': {},
            'agent': {},
            'supplier': {},
            'project': {},
        }

        # 查找包含联系信息的文本
        text = soup.get_text()

        # 提取电话
        import re
        phones = re.findall(r'1[3-9]\d{9}', text)
        if phones:
            contacts['project']['phone'] = phones[0]

        # 提取邮箱
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if emails:
            contacts['project']['email'] = emails[0]

        return contacts
