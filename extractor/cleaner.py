"""
数据清洗器
清洗和验证提取的数据
"""
import logging
import re
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class DataCleaner:
    """数据清洗器"""

    def __init__(self):
        self.seen_titles: Set[str] = set()
        self.seen_urls: Set[str] = set()

    def clean_announcement(self, announcement: Dict) -> Dict:
        """
        清洗公告数据

        Args:
            announcement: 原始公告数据

        Returns:
            清洗后的公告数据
        """
        cleaned = {}

        # 清洗标题
        cleaned['title'] = self._clean_title(announcement.get('title', ''))

        # 清洗URL
        cleaned['url'] = self._clean_url(announcement.get('url', ''))

        # 清洗内容
        cleaned['content'] = self._clean_content(announcement.get('content', ''))

        # 清洗日期
        cleaned['publish_date'] = self._clean_date(
            announcement.get('publish_date') or announcement.get('list_date')
        )

        # 保留其他字段
        for key, value in announcement.items():
            if key not in ['title', 'url', 'content', 'publish_date']:
                cleaned[key] = value

        return cleaned

    def _clean_title(self, title: str) -> str:
        """清洗标题"""
        if not title:
            return "未知标题"

        # 去除多余空白
        title = re.sub(r'\s+', ' ', title).strip()

        # 去除特殊字符
        title = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', title)

        # 限制长度
        if len(title) > 500:
            title = title[:500] + "..."

        return title

    def _clean_url(self, url: str) -> str:
        """清洗URL"""
        if not url:
            return ""

        # 去除多余空白
        url = url.strip()

        # 统一协议
        if url.startswith('//'):
            url = 'http:' + url

        return url

    def _clean_content(self, content: str) -> str:
        """清洗内容"""
        if not content:
            return ""

        # 去除多余空白
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = re.sub(r' +', ' ', content)

        # 限制长度
        if len(content) > 50000:
            content = content[:50000] + "\n...(内容过长，已截断)"

        return content.strip()

    def _clean_date(self, date_str: str) -> str:
        """清洗日期"""
        if not date_str:
            return ""

        # 去除多余空白
        date_str = date_str.strip()

        # 统一日期格式
        date_str = re.sub(r'[年月./]', '-', date_str)
        date_str = re.sub(r'日', '', date_str)

        return date_str

    def is_duplicate(self, announcement: Dict) -> bool:
        """
        检查是否重复

        Args:
            announcement: 公告数据

        Returns:
            是否重复
        """
        title = announcement.get('title', '')
        url = announcement.get('url', '')

        # 检查标题
        if title in self.seen_titles:
            return True

        # 检查URL
        if url in self.seen_urls:
            return True

        # 记录
        self.seen_titles.add(title)
        self.seen_urls.add(url)

        return False

    def clean_contacts(self, contacts: Dict) -> Dict:
        """
        清洗联系人数据

        Args:
            contacts: 原始联系人数据

        Returns:
            清洗后的联系人数据
        """
        cleaned = {}

        # 清洗电话
        phones = contacts.get('phones', [])
        cleaned['phones'] = list(set(self._clean_phones(phones)))

        # 清洗邮箱
        emails = contacts.get('emails', [])
        cleaned['emails'] = list(set(self._clean_emails(emails)))

        # 清洗公司名称
        company = contacts.get('company', '')
        cleaned['company'] = self._clean_company(company)

        # 清洗联系人
        contact_names = contacts.get('contacts', [])
        cleaned['contacts'] = list(set(self._clean_contacts(contact_names)))

        return cleaned

    def _clean_phones(self, phones: List[str]) -> List[str]:
        """清洗电话号码"""
        cleaned = []

        for phone in phones:
            # 去除非数字字符（保留横线）
            phone = re.sub(r'[^\d\-]', '', phone)

            # 验证格式
            if self._is_valid_phone(phone):
                if phone not in cleaned:
                    cleaned.append(phone)

        return cleaned

    def _clean_emails(self, emails: List[str]) -> List[str]:
        """清洗邮箱"""
        cleaned = []

        for email in emails:
            email = email.strip().lower()
            if self._is_valid_email(email):
                if email not in cleaned:
                    cleaned.append(email)

        return cleaned

    def _clean_company(self, company: str) -> str:
        """清洗公司名称"""
        if not company:
            return ""

        company = company.strip()
        # 去除多余标点
        company = re.sub(r'[、,，;；]', '', company)

        return company

    def _clean_contacts(self, contacts: List[str]) -> List[str]:
        """清洗联系人姓名"""
        cleaned = []

        for contact in contacts:
            contact = contact.strip()
            # 简单验证
            if len(contact) >= 2 and len(contact) <= 20:
                if contact not in cleaned:
                    cleaned.append(contact)

        return cleaned

    def _is_valid_phone(self, phone: str) -> bool:
        """验证电话号码"""
        if not phone:
            return False

        # 长度检查
        if len(phone) < 7 or len(phone) > 15:
            return False

        # 必须包含数字
        if not re.search(r'\d', phone):
            return False

        return True

    def _is_valid_email(self, email: str) -> bool:
        """验证邮箱"""
        if not email:
            return False

        # 基本格式检查
        if '@' not in email or '.' not in email:
            return False

        # 长度检查
        if len(email) > 100 or len(email) < 5:
            return False

        return True
