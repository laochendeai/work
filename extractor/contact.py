"""
联系人提取器
从公告内容中提取联系人信息
"""
import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)


class ContactExtractor:
    """联系人提取器"""

    # 电话号码正则
    PHONE_PATTERNS = [
        r'(?:电话|手机|联系方式|联系人).*?[:：]?\s*([\d\-]{7,15})',
        r'1[3-9]\d{9}',  # 手机号
        r'0\d{2,3}-?\d{7,8}',  # 座机
        r'0\d{2,3}\d{7,8}',  # 座机（无横线）
        r'\d{3,4}-\d{7,8}',  # 简单座机格式
    ]

    # 邮箱正则
    EMAIL_PATTERNS = [
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    ]

    # 公司名称关键词
    COMPANY_KEYWORDS = [
        '公司', '有限公司', '集团', '企业', '单位',
        '采购人', '代理机构', '供应商', '中标人',
    ]

    def extract(self, content: str) -> Dict:
        """
        从公告内容中提取联系人信息

        Args:
            content: 公告正文内容

        Returns:
            联系人信息字典:
            - phones: 电话列表
            - emails: 邮箱列表
            - company: 公司名称
            - contacts: 联系人姓名列表
        """
        if not content:
            return {}

        result = {
            'phones': self._extract_phones(content),
            'emails': self._extract_emails(content),
            'company': self._extract_company(content),
            'contacts': self._extract_contacts(content),
        }

        logger.info(
            f"提取联系人: {len(result['phones'])}个电话, "
            f"{len(result['emails'])}个邮箱, "
            f"公司: {result['company'] or '未找到'}"
        )

        return result

    def _extract_phones(self, content: str) -> List[str]:
        """提取电话号码"""
        phones = []

        for pattern in self.PHONE_PATTERNS:
            matches = re.findall(pattern, content)
            for match in matches:
                # 清理号码
                phone = re.sub(r'[^\d\-]', '', match)
                if len(phone) >= 7 and len(phone) <= 15:
                    if phone not in phones:
                        phones.append(phone)

        return phones

    def _extract_emails(self, content: str) -> List[str]:
        """提取邮箱地址"""
        emails = []

        for pattern in self.EMAIL_PATTERNS:
            matches = re.findall(pattern, content)
            for match in matches:
                # 验证邮箱格式
                if self._is_valid_email(match):
                    if match.lower() not in emails:
                        emails.append(match.lower())

        return emails

    def _extract_company(self, content: str) -> str:
        """提取公司名称"""
        # 尝试多种模式

        # 模式1: 采购人/供应商名称
        patterns = [
            r'采购人[：:]\s*([^、\n]{2,30})(?:[、\n]|$)',
            r'供应商[：:]\s*([^、\n]{2,30})(?:[、\n]|$)',
            r'中标人[：:]\s*([^、\n]{2,30})(?:[、\n]|$)',
            r'代理机构[：:]\s*([^、\n]{2,30})(?:[、\n]|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                company = match.group(1).strip()
                # 检查是否包含公司关键词
                if any(kw in company for kw in self.COMPANY_KEYWORDS):
                    return company

        return ""

    def _extract_contacts(self, content: str) -> List[str]:
        """提取联系人姓名"""
        contacts = []

        # 联系人常见模式
        patterns = [
            r'联系人[：:]\s*([A-Za-z\u4e00-\u9fa5]{2,10})(?:[、\n\s]|$)',
            r'项目联系[：:]\s*([A-Za-z\u4e00-\u9fa5]{2,10})(?:[、\n\s]|$)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                name = match.strip()
                if name and len(name) >= 2 and name not in contacts:
                    contacts.append(name)

        return contacts

    def _is_valid_email(self, email: str) -> bool:
        """验证邮箱格式"""
        if not email:
            return False

        # 基本格式检查
        if '@' not in email or '.' not in email:
            return False

        # 长度检查
        if len(email) > 100 or len(email) < 5:
            return False

        # 不能以特殊字符开头或结尾
        if email[0] in '@.-' or email[-1] in '@.-':
            return False

        return True
