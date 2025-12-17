#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联系人提取器 - 支持多种提取方法
智能联系人提取系统，支持规则、简单、AI等多种提取方式
"""

import logging
import json
import sqlite3
import re
import html
from urllib.parse import unquote
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover
    BeautifulSoup = None  # type: ignore

# 尝试导入pandas，但不是必需的
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None

from config.settings import settings

try:  # pragma: no cover - optional, fallback to regex only
    from core.local_processor import LocalContactProcessor
except Exception:  # pragma: no cover
    LocalContactProcessor = None  # type: ignore

try:  # pragma: no cover - optional, used for procurement-style结构化抽取
    from core.structured_contact_extractor import StructuredContactExtractor
except Exception:  # pragma: no cover
    StructuredContactExtractor = None  # type: ignore

class RuleBasedExtractor:
    """基于规则的联系人提取器

    使用正则表达式模式从文本中提取联系人信息
    """

    def __init__(self) -> None:
        """初始化提取器"""
        self.logger = logging.getLogger(__name__)
        # 定义提取模式
        self.patterns: Dict[str, List[str]] = {
            'company': [
                r'采购单位[：:\s]*([^\n,，。]+?)(?=\s*(?:地址|联系人|电话|手机|邮箱|$))',
                r'代理机构[：:\s]*([^\n,，。]+?)(?=\s*(?:地址|联系人|电话|手机|邮箱|$))',
                r'中标单位[：:\s]*([^\n,，。]+?)(?=\s*(?:地址|联系人|电话|手机|邮箱|$))',
                r'(?:[^\n]*?(?:公司|集团|企业|有限公司|学校|医院|中心)[^\n]*?)'
            ],
            'name': [
                r'联系人[：:\s]*([^\s,，。\n]{2,10})',
                r'负责人[：:\s]*([^\s,，。\n]{2,10})',
                r'项目经理[：:\s]*([^\s,，。\n]{2,10})',
                r'经办人[：:\s]*([^\s,，。\n]{2,10})',
                r'项目联系人[：:\s]*([^\n,，。]+?)(?=\s*(?:电话|手机|邮箱|$))'
            ],
            'phone': [
                r'(?:电话|Tel|联系电话)[：:\s]*(0\d{2,3}[-\s]?\d{7,8})',
                r'(0\d{2,3}[-\s]?\d{7,8})'
            ],
            'mobile': [
                r'(?:手机|联系手机|移动电话)[：:\s]*(1[3-9]\d{9})',
                r'(1[3-9]\d{9})'
            ],
            'email': [
                r'(?:邮箱|Email|电子邮箱)[：:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            ],
            'address': [
                r'(?:地址|单位地址|联系地址|采购单位地址)[：:\s]*([^\n,，。]{10,100})'
            ]
        }
        self.role_keywords = {
            'buyer': ['采购人', '采购单位', '招标人', '甲方'],
            'agency': ['代理机构', '采购代理', '招标代理'],
            'supplier': ['中标人', '成交供应商', '中标供应商', '中标单位', '乙方', '供应商']
        }

    def extract_from_text(self, text: str) -> Dict[str, Any]:
        """从文本中提取联系人信息"""
        contact = {
            'company': '',
            'name': '',
            'phone': '',
            'mobile': '',
            'email': '',
            'address': ''
        }

        # 按行处理
        lines = text.split('\n')
        role = 'unknown'
        for line in lines:
            line = line.strip()
            if len(line) < 5:
                continue
            role = self._detect_role(line, role)

            # 提取各个字段
            for field, field_patterns in self.patterns.items():
                if not contact[field]:  # 如果还没提取到该字段
                    for pattern in field_patterns:
                        match = re.search(pattern, line)
                        if match:
                            # 根据字段类型处理
                            if field == 'email' and len(match.groups()) > 1:
                                value = match.group(1) if match.group(1) else match.group(2)
                            else:
                                value = match.group(1) if match.groups() else match.group(0)

                            contact[field] = self._clean_field(value, field)
                            break

        contact['role'] = role
        contact['role_label'] = self._role_label(role)
        return contact

    def _clean_field(self, value: str, field_type: str) -> str:
        """清理字段值"""
        value = value.strip()

        if field_type == 'phone':
            # 提取并格式化电话号码
            phone_match = re.search(r'(0\d{2,3})[-\s]?(\d{7,8})', value)
            if phone_match:
                return f"{phone_match.group(1)}-{phone_match.group(2)}"

        elif field_type == 'mobile':
            # 提取手机号
            mobile_match = re.search(r'(1[3-9]\d{9})', value)
            if mobile_match:
                return mobile_match.group(1)

        elif field_type == 'email':
            # 验证邮箱格式
            if '@' in value and '.' in value.split('@')[-1]:
                return value.lower()

        elif field_type == 'name' or field_type == 'company' or field_type == 'address':
            # 移除标签
            value = re.sub(r'^[：:\s]+', '', value)
            value = re.sub(r'[：:\s]+$', '', value)
            # 限制长度
            if field_type == 'name' and len(value) > 10:
                value = value[:10]
            elif field_type == 'company' and len(value) > 50:
                value = value[:50]
            elif field_type == 'address' and len(value) > 100:
                value = value[:100]

        return value

    def _detect_role(self, line: str, current_role: str) -> str:
        for role, keywords in self.role_keywords.items():
            if any(keyword in line for keyword in keywords):
                return role
        return current_role

    def _role_label(self, role: str) -> str:
        if role == 'buyer':
            return '甲方/采购人'
        if role == 'agency':
            return '代理机构'
        if role == 'supplier':
            return '乙方/中标单位'
        return ''


class SimpleExtractor:
    """简单联系人提取器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def extract_from_text(self, text: str) -> Dict[str, Any]:
        """简单的联系人提取"""
        contact = {
            'company': '',
            'name': '',
            'phone': '',
            'mobile': '',
            'email': '',
            'address': ''
        }

        # 简单的关键词提取
        lines = text.split('\n')
        for line in lines:
            if '采购单位' in line:
                contact['company'] = line.split('：')[-1].strip() if '：' in line else ''
            elif '联系人' in line:
                contact['name'] = line.split('：')[-1].strip() if '：' in line else ''
            elif '电话' in line and '手机' not in line:
                phone = re.search(r'\d{3,4}[-\s]?\d{7,8}', line)
                if phone:
                    contact['phone'] = phone.group()
            elif '手机' in line:
                mobile = re.search(r'1[3-9]\d{9}', line)
                if mobile:
                    contact['mobile'] = mobile.group()
            elif '邮箱' in line or 'Email' in line:
                email = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', line)
                if email:
                    contact['email'] = email.group()
            elif '地址' in line:
                contact['address'] = line.split('：')[-1].strip() if '：' in line else ''

        contact['role'] = ''
        contact['role_label'] = ''
        return contact


class ContactExtractor:
    """
    联系人提取器主类
    支持多种提取方法的智能切换
    """

    def __init__(self, method: str = None):
        """
        初始化联系人提取器

        Args:
            method: 提取方法 ('rule', 'simple', 'smart')
                   如果为None，则使用配置中的默认方法
        """
        self.logger = logging.getLogger(__name__)

        if not method:
            method = settings.get('contact_processing.method', 'rule')
        self.method = method

        # 基础提取器（始终可用）
        self.rule_extractor = RuleBasedExtractor()
        self.simple_extractor = SimpleExtractor()
        if method == 'simple':
            self.extractor = self.simple_extractor
        else:
            # 默认/未知均回退为规则提取器
            if method not in {'rule', 'simple'}:
                self.logger.info("未知方法 %s，使用规则提取器", method)
                self.method = 'rule'
            self.extractor = self.rule_extractor

        # 结构化采购公告提取器（可选）
        self.structured_extractor = StructuredContactExtractor() if StructuredContactExtractor else None

        # 本地智能处理器（可选）
        local_cfg = settings.get('contact_processing.local_processing', {}) or {}
        self.local_processing_enabled = bool(local_cfg.get('enabled', True))
        self.local_confidence_threshold = float(local_cfg.get('confidence_threshold', 0.3) or 0.3)
        self.local_max_contacts = int(local_cfg.get('max_contacts_per_item', 5) or 5)
        self.local_processor = None
        if self.local_processing_enabled and LocalContactProcessor:
            try:
                self.local_processor = LocalContactProcessor()
            except Exception as exc:  # noqa: BLE001
                self.logger.debug("本地联系人处理器初始化失败，将降级为规则提取: %s", exc)
                self.local_processor = None

        # 导出目录
        self.export_dir = Path("data") / "exports" / "contacts"
        self.export_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info("联系人提取器初始化完成，方法=%s, structured=%s, local=%s",
                         self.method, bool(self.structured_extractor), bool(self.local_processor))

    def extract_from_text(self, text: str, *, title: str = "", source: str = "") -> Dict[str, Any]:
        """从文本中提取联系人信息（结构化优先 + 多策略融合 + 去重合并）。"""
        normalized_text = self._normalize_text(text)
        if not normalized_text:
            return {
                'emails': [],
                'phones': [],
                'companies': [],
                'names': [],
                'addresses': [],
                'structured_contacts': [],
                'merged_contacts': [],
                'procurement_title': title or '',
                'organizations': {},
                'raw_text': ''
            }

        procurement_title = title or ''
        organizations: Dict[str, Any] = {}
        structured_contacts: List[Dict[str, Any]] = []

        # 1) 结构化采购公告抽取（如果可用）
        if self.structured_extractor:
            try:
                payload = self.structured_extractor.extract_structured_contacts({
                    'detail_content': normalized_text,
                    'title': title or ''
                }) or {}
                procurement_title = (payload.get('procurement_title') or procurement_title or '').strip()
                organizations = payload.get('organizations', {}) or {}
                structured_contacts.extend(self._contacts_from_structured(payload))
            except Exception as exc:  # noqa: BLE001
                self.logger.debug("结构化抽取失败，将降级: %s", exc)

        # 2) 本地智能处理（如果可用）
        local_contacts: List[Dict[str, Any]] = []
        if self.local_processor:
            try:
                local_infos = self.local_processor.extract_contacts_from_text(normalized_text) or []
                for info in local_infos[: self.local_max_contacts]:
                    local_contacts.append({
                        'company': (getattr(info, 'company', '') or '').strip(),
                        'name': (getattr(info, 'name', '') or '').strip(),
                        'phone': (getattr(info, 'phone', '') or '').strip(),
                        'mobile': '',
                        'email': (getattr(info, 'email', '') or '').strip(),
                        'address': (getattr(info, 'address', '') or '').strip(),
                        'role': '',
                        'role_label': '',
                        'confidence': float(getattr(info, 'confidence', 0.0) or 0.0),
                        'source': 'local',
                    })
            except Exception as exc:  # noqa: BLE001
                self.logger.debug("本地抽取失败，将降级: %s", exc)

        # 3) 规则/简单抽取作为兜底
        fallback_contacts: List[Dict[str, Any]] = []
        try:
            base = self.extractor.extract_from_text(normalized_text) or {}
            if isinstance(base, dict) and any(base.get(k) for k in ('company', 'name', 'phone', 'mobile', 'email', 'address')):
                fallback_contacts.append({
                    'company': (base.get('company') or '').strip(),
                    'name': (base.get('name') or '').strip(),
                    'phone': (base.get('phone') or '').strip(),
                    'mobile': (base.get('mobile') or '').strip(),
                    'email': (base.get('email') or '').strip(),
                    'address': (base.get('address') or '').strip(),
                    'role': (base.get('role') or '').strip(),
                    'role_label': (base.get('role_label') or '').strip(),
                    'source': self.method,
                })
        except Exception as exc:  # noqa: BLE001
            self.logger.debug("兜底抽取失败: %s", exc)

        # 4) 规则补充：直接从全文抓邮箱/电话/姓名/机构/地址（用于旧数据/无换行数据）
        emails = self._extract_emails(normalized_text)
        phones = self._extract_phones(normalized_text)
        companies = self._extract_companies(normalized_text)
        names = self._extract_names(normalized_text)
        addresses = self._extract_addresses(normalized_text)

        all_contacts = structured_contacts + local_contacts + fallback_contacts
        cleaned_contacts: List[Dict[str, Any]] = []
        for contact in all_contacts:
            if not isinstance(contact, dict):
                continue
            cleaned = {
                'company': self._clean_company(contact.get('company', '')),
                'name': self._clean_person_name(contact.get('name', '')),
                'phone': self._normalize_phone(contact.get('phone', '')),
                'mobile': self._normalize_phone(contact.get('mobile', '')),
                'email': self._normalize_email(contact.get('email', '')),
                'address': self._clean_address(contact.get('address', '')),
                'role': (contact.get('role') or '').strip(),
                'role_label': (contact.get('role_label') or '').strip(),
                'source': (contact.get('source') or '').strip(),
            }
            # 过滤明显无效的联系人
            if any(cleaned.get(k) for k in ('phone', 'mobile', 'email', 'name', 'company', 'address')):
                cleaned_contacts.append(cleaned)

        merged_contacts = self._merge_contacts(cleaned_contacts)

        # 5) 汇总为列表字段（优先保持“先出现先保留”的顺序）
        emails = self._dedupe_keep_order(
            emails + [c.get('email', '') for c in merged_contacts if c.get('email')]
        )
        phones = self._dedupe_keep_order(
            phones
            + [c.get('mobile', '') for c in merged_contacts if c.get('mobile')]
            + [c.get('phone', '') for c in merged_contacts if c.get('phone')]
        )
        companies = self._dedupe_keep_order(
            companies + [c.get('company', '') for c in merged_contacts if c.get('company')]
        )
        names = self._dedupe_keep_order(
            names + [c.get('name', '') for c in merged_contacts if c.get('name')]
        )
        addresses = self._dedupe_keep_order(
            addresses + [c.get('address', '') for c in merged_contacts if c.get('address')]
        )

        return {
            'emails': emails,
            'phones': phones,
            'companies': companies,
            'names': names,
            'addresses': addresses,
            'structured_contacts': cleaned_contacts,
            'merged_contacts': merged_contacts,
            'procurement_title': procurement_title,
            'organizations': organizations,
            'raw_text': normalized_text
        }

    def _dedupe_keep_order(self, items: List[str]) -> List[str]:
        seen: Set[str] = set()
        deduped: List[str] = []
        for item in items:
            if not item:
                continue
            value = str(item).strip()
            if not value:
                continue
            if value in seen:
                continue
            seen.add(value)
            deduped.append(value)
        return deduped

    def _normalize_text(self, text: Any) -> str:
        if text is None:
            return ""
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:  # noqa: BLE001
                return ""
        raw = text.strip()
        if not raw:
            return ""

        # 兼容某些历史数据：detail_content 可能被序列化为 JSON
        if raw.startswith('{') and raw.endswith('}'):
            try:
                payload = json.loads(raw)
                if isinstance(payload, dict):
                    for key in ('detail_content', 'content', 'text', 'html'):
                        value = payload.get(key)
                        if isinstance(value, str) and value.strip():
                            raw = value.strip()
                            break
            except Exception:
                pass

        raw = self._strip_html(raw)
        raw = raw.replace('\r\n', '\n').replace('\r', '\n')
        raw = raw.replace('\u00a0', ' ').replace('\u3000', ' ')
        raw = self._compact_labels(raw)

        # 旧数据常见：无换行导致“段落/字段”难识别，适度插入分隔符
        if '\n' not in raw and len(raw) > 300:
            raw = re.sub(r'[。；;]', lambda m: m.group(0) + '\n', raw)

        raw = re.sub(r'[ \t]+', ' ', raw)
        raw = re.sub(r'\n{3,}', '\n\n', raw)
        return raw.strip()

    def _strip_html(self, text: str) -> str:
        if not text:
            return ""
        if BeautifulSoup is None:
            return re.sub(r'<[^>]+>', ' ', text)
        # 仅在“看起来像HTML”时解析，避免误伤包含尖括号的纯文本
        if '<' not in text or '>' not in text or not re.search(r'<[a-zA-Z][^>]*>', text):
            return text
        try:
            soup = BeautifulSoup(text, 'lxml')
            for tag in soup(['script', 'style', 'noscript']):
                try:
                    tag.decompose()
                except Exception:  # noqa: BLE001
                    continue
            mailtos: List[str] = []
            for anchor in soup.select('a[href]'):
                href = (anchor.get('href') or '').strip()
                if not href:
                    continue
                if href.lower().startswith('mailto:'):
                    address = href[7:]
                    address = address.split('?', 1)[0].strip()
                    if address:
                        mailtos.append(unquote(address))

            plain = soup.get_text(separator='\n', strip=True)
            if mailtos:
                plain = plain + '\n' + '\n'.join(mailtos)
            return plain
        except Exception:  # noqa: BLE001
            return re.sub(r'<[^>]+>', ' ', text)

    def _compact_labels(self, text: str) -> str:
        if not text:
            return ""
        # 常见“电 话/邮 箱/联 系 人”写法归一
        replacements = {
            r'联\s*系\s*人': '联系人',
            r'项\s*目\s*联\s*系\s*人': '项目联系人',
            r'电\s*话': '电话',
            r'手\s*机': '手机',
            r'邮\s*箱': '邮箱',
            r'地\s*址': '地址',
            r'E\s*-\s*mail': 'Email',
        }
        for pattern, repl in replacements.items():
            text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
        return text

    def _normalize_email(self, email: Any) -> str:
        if not email:
            return ''
        value = str(email).strip()
        if not value:
            return ''
        value = value.replace('＠', '@').replace('．', '.')
        value = value.replace('（at）', '@').replace('(at)', '@').replace('[at]', '@')
        value = re.sub(r'([A-Za-z0-9._%+-]+)#([A-Za-z0-9.-]+\.[A-Za-z]{2,})', r'\1@\2', value)
        value = value.replace('。', '.')
        value = re.sub(r'\s+', '', value).lower()
        if re.fullmatch(r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}', value):
            return value
        return ''

    def _extract_emails(self, text: str) -> List[str]:
        if not text:
            return []
        scan = text
        # HTML 实体解码（例如 &#64; / &commat;）
        try:
            scan = html.unescape(scan)
        except Exception:
            pass
        scan = scan.replace('＠', '@').replace('．', '.')
        scan = scan.replace('（at）', '@').replace('(at)', '@').replace('[at]', '@')
        scan = re.sub(r'([A-Za-z0-9._%+-]+)#([A-Za-z0-9.-]+\.[A-Za-z]{2,})', r'\1@\2', scan)
        # 仅用于邮箱扫描：将中文句号替换为点，提升“xx@a。com”命中率
        scan = scan.replace('。', '.')
        # 常见“name at domain dot com”/括号写法
        scan = re.sub(r'\s+(?:at|AT)\s+', '@', scan)
        scan = re.sub(r'\s+(?:dot|DOT)\s+', '.', scan)
        scan = re.sub(r'\s*\(dot\)\s*', '.', scan, flags=re.IGNORECASE)
        scan = re.sub(r'\s*\[dot\]\s*', '.', scan, flags=re.IGNORECASE)
        scan = re.sub(r'\s*（dot）\s*', '.', scan, flags=re.IGNORECASE)
        scan = re.sub(r'\s*\{dot\}\s*', '.', scan, flags=re.IGNORECASE)
        scan = re.sub(r'\s*\(at\)\s*', '@', scan, flags=re.IGNORECASE)
        scan = re.sub(r'\s*\[at\]\s*', '@', scan, flags=re.IGNORECASE)
        scan = re.sub(r'\s*（at）\s*', '@', scan, flags=re.IGNORECASE)
        scan = re.sub(r'\s*\{at\}\s*', '@', scan, flags=re.IGNORECASE)
        scan = re.sub(r'\s*@\s*', '@', scan)
        scan = re.sub(r'\s*\.\s*', '.', scan)
        candidates = re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', scan, flags=re.IGNORECASE)
        normalized: List[str] = []
        for candidate in candidates:
            value = self._normalize_email(candidate)
            if value:
                normalized.append(value)
        return self._dedupe_keep_order(normalized)

    def _normalize_phone(self, phone: Any) -> str:
        if not phone:
            return ''
        raw = str(phone).strip()
        if not raw:
            return ''
        # 去掉常见分机表达（仅保留主号）
        raw = re.split(r'(?:转|ext\.?|#)\s*\d{1,6}$', raw, flags=re.IGNORECASE)[0]
        digits = re.sub(r'[^0-9]', '', raw)
        if not digits:
            return ''
        # 去掉国家码
        if digits.startswith('86') and len(digits) >= 13:
            digits = digits[2:]
        # 手机
        if len(digits) == 11 and digits.startswith('1'):
            return digits
        # 400/800
        if len(digits) == 10 and digits.startswith(('400', '800')):
            return f"{digits[:3]}-{digits[3:]}"
        # 座机
        if digits.startswith('0') and 10 <= len(digits) <= 12:
            # 01/02 开头多为3位区号（含0）；其余优先尝试4位区号
            area_len = 3 if digits[1] in {'1', '2'} else 4
            if len(digits) - area_len not in {7, 8}:
                area_len = 3
            area = digits[:area_len]
            number = digits[area_len:]
            if len(number) in {7, 8}:
                return f"{area}-{number}"
        # 兜底：保留可识别的长数字
        if len(digits) >= 7:
            return digits
        return ''

    def _extract_phones(self, text: str) -> List[str]:
        if not text:
            return []
        found: List[str] = []

        # 手机号（允许空格/连字符）
        for match in re.finditer(r'(?<!\d)(?:\+?86[-\s]?)?(1[3-9]\d)[-\s]?(\d{4})[-\s]?(\d{4})(?!\d)', text):
            found.append(match.group(1) + match.group(2) + match.group(3))
        found.extend(re.findall(r'(?<!\d)1[3-9]\d{9}(?!\d)', text))

        # 固话（0xx/0xxx 区号 + 7/8 位）
        for match in re.finditer(r'(?<!\d)(?:\+?86[-\s]?)?(0\d{2,3})[()（）\s\-]*?(\d{7,8})(?!\d)', text):
            prefix = text[max(0, match.start() - 6):match.start()].lower()
            if '传真' in prefix or 'fax' in prefix:
                continue
            found.append(f"{match.group(1)}-{match.group(2)}")

        # 400/800
        for match in re.finditer(r'(?<!\d)([48]00)[-\s]?(\d{3,4})[-\s]?(\d{3,4})(?!\d)', text):
            prefix = text[max(0, match.start() - 6):match.start()].lower()
            if '传真' in prefix or 'fax' in prefix:
                continue
            found.append(f"{match.group(1)}-{match.group(2)}{match.group(3)}")

        normalized: List[str] = []
        for candidate in found:
            value = self._normalize_phone(candidate)
            if value:
                normalized.append(value)
        return self._dedupe_keep_order(normalized)

    def _clean_company(self, value: Any) -> str:
        if not value:
            return ''
        text = str(value).strip()
        if not text:
            return ''
        # 兼容“机构信息 名称:xxx”这类组合串：优先抽取“名称:”后的实体
        name_match = re.search(r'名称\s*[:：]\s*([^\n,，。；;]{2,80})', text)
        if name_match:
            text = name_match.group(1).strip()
        # 去掉前缀标签
        text = re.sub(r'^(?:采购人|采购单位|招标人|代理机构|采购代理机构|名称|单位名称)\s*[:：]?\s*', '', text)
        # 去掉常见后缀标签（避免“xxx 采购单位/xxx 代理机构”）
        text = re.sub(r'\s*(?:采购单位|采购人|招标人|代理机构|采购代理机构)\s*$', '', text)
        text = text.strip(' \t\r\n:：,，。；;')
        # 明显的邮箱/域名噪声
        if '@' in text:
            return ''
        if any(token in text.lower() for token in ('example.com', 'test.com', 'localhost')):
            return ''
        if re.search(r'\b[a-zA-Z0-9._-]+\.[a-zA-Z]{2,}\b', text) and not re.search(r'[\u4e00-\u9fff]', text):
            return ''
        # 避免把人名误当机构
        if self._looks_like_person_name(text):
            return ''
        # 过长多为噪声
        if len(text) > 80:
            return text[:80]
        return text

    def _company_score(self, text: str) -> int:
        """粗略评估机构名质量，用于合并冲突时择优。"""
        if not text:
            return -10
        lower = text.lower()
        if '@' in text or any(token in lower for token in ('example.com', 'test.com', 'localhost')):
            return -10

        score = 0
        if re.search(r'\b[a-z0-9._-]+\.[a-z]{2,}\b', lower) and not re.search(r'[\u4e00-\u9fff]', text):
            score -= 5

        org_hints = (
            '有限公司', '有限责任公司', '股份有限公司', '集团', '公司',
            '大学', '学院', '学校', '医院', '中心', '研究院', '研究所',
            '政府', '委员会', '局', '厅', '处', '办', '所', '站', '队', '馆', '部'
        )
        if any(hint in text for hint in org_hints):
            score += 5
        if 4 <= len(text) <= 40:
            score += 2
        if re.search(r'[\u4e00-\u9fff]', text):
            score += 1
        return score

    def _clean_person_name(self, value: Any) -> str:
        if not value:
            return ''
        text = str(value).strip()
        if not text:
            return ''
        text = text.strip(' \t\r\n:：,，。；;')
        # 常见后缀（张老师/李主任）
        if len(text) > 12:
            text = text[:12]
        if not self._looks_like_person_name(text):
            return ''
        return text

    def _looks_like_person_name(self, text: str) -> bool:
        if not text:
            return False
        # 机构后缀/典型组织词：出现这些基本不应判为人名（避免“某某大学/XX医院/财政局”等被误判）
        org_hints = (
            '公司', '有限公司', '有限责任公司', '股份有限公司', '集团',
            '大学', '学院', '学校', '医院', '中心', '研究院', '研究所',
            '政府', '委员会', '局', '厅', '处', '办', '所', '站', '队', '馆', '部'
        )
        if any(hint in text for hint in org_hints):
            return False
        if any(token in text for token in ('采购', '招标', '代理', '项目', '公告', '联系方式', '电话', '邮箱', '地址', '名称')):
            return False
        if re.fullmatch(r'[\u4e00-\u9fff]{2,4}', text):
            return True
        if re.fullmatch(r'[\u4e00-\u9fff]{1,4}(?:老师|先生|女士|经理|主任|教授|工程师|处长|科长)', text):
            return True
        return False

    def _clean_address(self, value: Any) -> str:
        if not value:
            return ''
        text = str(value).strip()
        if not text:
            return ''
        text = re.sub(r'^(?:地址|联系地址|单位地址|采购单位地址)\s*[:：]?\s*', '', text)
        text = text.strip(' \t\r\n:：,，。；;')
        if len(text) < 6:
            return ''
        if len(text) > 120:
            return text[:120]
        return text

    def _extract_companies(self, text: str) -> List[str]:
        if not text:
            return []
        candidates: List[str] = []
        patterns = [
            r'(?:采购人|采购单位|招标人|采购单位名称)\s*[:：]?\s*([^\n,，。；;]{2,80})',
            r'(?:采购代理机构|代理机构名称|代理机构|招标代理)\s*[:：]?\s*([^\n,，。；;]{2,80})',
        ]
        for pattern in patterns:
            for match in re.findall(pattern, text):
                company = self._clean_company(match)
                if company:
                    candidates.append(company)
        # 通用兜底：常见机构后缀
        fallback = re.findall(
            r'([\u4e00-\u9fffA-Za-z0-9（）()\-]{2,50}'
            r'(?:有限公司|有限责任公司|股份有限公司|集团|公司|医院|大学|学院|学校|中心|政府|委员会|局|厅|处|办|所))',
            text
        )
        for match in fallback[:10]:
            company = self._clean_company(match)
            if company:
                candidates.append(company)
        return self._dedupe_keep_order(candidates)

    def _extract_names(self, text: str) -> List[str]:
        if not text:
            return []
        candidates: List[str] = []
        patterns = [
            r'(?:项目联系人|采购联系人|联系人|经办人|项目负责人)\s*[:：]?\s*([\u4e00-\u9fff]{2,4}(?:老师|先生|女士|经理|主任)?)',
            r'(?<![\u4e00-\u9fff])([\u4e00-\u9fff]{2,4}(?:老师|先生|女士|经理|主任))(?![\u4e00-\u9fff])',
        ]
        for pattern in patterns:
            for match in re.findall(pattern, text):
                name = self._clean_person_name(match)
                if name:
                    candidates.append(name)
        return self._dedupe_keep_order(candidates)

    def _extract_addresses(self, text: str) -> List[str]:
        if not text:
            return []
        candidates: List[str] = []
        for match in re.findall(r'(?:地址|联系地址|单位地址|采购单位地址)\s*[:：]?\s*([^\n,，。；;]{6,120})', text):
            addr = self._clean_address(match)
            if addr:
                candidates.append(addr)
        return self._dedupe_keep_order(candidates)

    def _contacts_from_structured(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        contacts: List[Dict[str, Any]] = []
        organizations = payload.get('organizations', {}) if isinstance(payload, dict) else {}
        if not isinstance(organizations, dict):
            organizations = {}

        def _pick_phone_values(values: Any) -> Tuple[str, str]:
            phone = ''
            mobile = ''
            if not isinstance(values, list):
                return phone, mobile
            for value in values:
                normalized = self._normalize_phone(value)
                if not normalized:
                    continue
                if normalized.startswith('1') and len(normalized) == 11:
                    if not mobile:
                        mobile = normalized
                else:
                    if not phone:
                        phone = normalized
            return phone, mobile

        role_map = {
            'purchaser': ('buyer', '甲方/采购人'),
            'agent': ('agency', '代理机构'),
        }

        for org_key, (role, role_label) in role_map.items():
            org = organizations.get(org_key, {}) if isinstance(organizations, dict) else {}
            if not isinstance(org, dict):
                continue
            org_name = str(org.get('name', '') or '').strip()
            org_addr = str(org.get('address', '') or '').strip()
            for item in (org.get('contacts') or []):
                if not isinstance(item, dict):
                    continue
                phone, mobile = _pick_phone_values(item.get('phones') or [])
                emails = item.get('emails') or []
                email = self._normalize_email(emails[0]) if isinstance(emails, list) and emails else ''
                contacts.append({
                    'company': org_name,
                    'name': str(item.get('name', '') or '').strip(),
                    'phone': phone,
                    'mobile': mobile,
                    'email': email,
                    'address': org_addr,
                    'role': role,
                    'role_label': role_label,
                    'source': 'structured',
                })

        # project_contacts：若存在，归为“代理机构/项目联系人”兜底
        for item in payload.get('project_contacts', []) if isinstance(payload, dict) else []:
            if not isinstance(item, dict):
                continue
            phone, mobile = '', ''
            phone, mobile = _pick_phone_values(item.get('phones') or [])
            emails = item.get('emails') or []
            email = self._normalize_email(emails[0]) if isinstance(emails, list) and emails else ''
            contacts.append({
                'company': '',
                'name': str(item.get('name', '') or '').strip(),
                'phone': phone,
                'mobile': mobile,
                'email': email,
                'address': '',
                'role': 'agency',
                'role_label': '代理机构',
                'source': 'structured',
            })

        return contacts

    def _merge_contacts(self, contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按 phone/email/name+company 合并去重联系人。"""
        if not contacts:
            return []

        buckets: Dict[str, Dict[str, Any]] = {}
        order: List[str] = []

        def _key(contact: Dict[str, Any]) -> str:
            role = (contact.get('role') or '').strip()
            mobile = contact.get('mobile') or ''
            phone = contact.get('phone') or ''
            email = contact.get('email') or ''
            name = contact.get('name') or ''
            company = contact.get('company') or ''
            for candidate in (mobile, phone):
                normalized = self._normalize_phone(candidate)
                if normalized:
                    return f"role:{role}|phone:{normalized}" if role else f"phone:{normalized}"
            normalized_email = self._normalize_email(email)
            if normalized_email:
                return f"role:{role}|email:{normalized_email}" if role else f"email:{normalized_email}"
            if name or company:
                return f"role:{role}|who:{name}|{company}" if role else f"who:{name}|{company}"
            return ""

        for contact in contacts:
            if not isinstance(contact, dict):
                continue
            key = _key(contact)
            if not key:
                continue
            if key not in buckets:
                buckets[key] = dict(contact)
                order.append(key)
                continue

            current = buckets[key]
            # 合并：缺失字段补齐；冲突时保留“更像有效值”的那个
            for field in ('company', 'name', 'phone', 'mobile', 'email', 'address', 'role', 'role_label'):
                incoming = contact.get(field) or ''
                if not incoming:
                    continue
                existing = current.get(field) or ''
                if not existing:
                    current[field] = incoming
                    continue
                if field == 'company':
                    incoming_score = self._company_score(str(incoming))
                    existing_score = self._company_score(str(existing))
                    if incoming_score > existing_score:
                        current[field] = incoming
                        continue
                    if incoming_score == existing_score and len(str(incoming)) > len(str(existing)):
                        current[field] = incoming
                        continue
                # 地址：优先更长（通常更完整）
                if field == 'address' and len(str(incoming)) > len(str(existing)):
                    current[field] = incoming

            buckets[key] = current

        merged = [buckets[k] for k in order if k in buckets]
        # 最终再做一次 phone/mobile 规范化，保证一致性
        for contact in merged:
            contact['phone'] = self._normalize_phone(contact.get('phone'))
            contact['mobile'] = self._normalize_phone(contact.get('mobile'))
            # 手机号不要混入 phone 字段
            if contact.get('phone', '').startswith('1') and len(contact.get('phone', '')) == 11:
                if not contact.get('mobile'):
                    contact['mobile'] = contact['phone']
                contact['phone'] = ''
            contact['email'] = self._normalize_email(contact.get('email'))
            contact['name'] = self._clean_person_name(contact.get('name'))
            contact['company'] = self._clean_company(contact.get('company'))
            contact['address'] = self._clean_address(contact.get('address'))
        return merged

    def extract_from_scraped_data(self, scraped_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从爬取的数据中提取联系人信息"""
        self.logger.info(f"开始提取联系人信息，共 {len(scraped_items)} 条数据")

        all_contacts = []
        processed = 0

        for item in scraped_items:
            # 获取文本
            text = item.get('detail_content') or item.get('content', '') or item.get('title', '')

            if text:
                extracted = self.extract_from_text(
                    text,
                    title=item.get('title', ''),
                    source=item.get('source', '')
                )

                if any(extracted.get(k) for k in ('emails', 'phones', 'companies', 'names', 'addresses', 'merged_contacts')):
                    merged = extracted.get('merged_contacts') or []
                    roles = []
                    for contact in merged:
                        role = (contact.get('role_label') or contact.get('role') or '').strip()
                        if role:
                            roles.append(role)
                    formatted_contact = {
                        'id': item.get('id', ''),
                        'title': item.get('title', ''),
                        'source': item.get('source', ''),
                        'link': item.get('link', ''),
                        'scraped_at': item.get('scraped_at', ''),
                        'emails': extracted.get('emails', []),
                        'phones': extracted.get('phones', []),
                        'companies': extracted.get('companies', []),
                        'names': extracted.get('names', []),
                        'addresses': extracted.get('addresses', []),
                        'structured_contacts': merged or extracted.get('structured_contacts', []),
                        'roles': self._dedupe_keep_order(roles),
                        'raw_text': extracted.get('raw_text', text),
                        'procurement_title': extracted.get('procurement_title', ''),
                        'organizations': extracted.get('organizations', {}),
                    }
                    all_contacts.append(formatted_contact)

            processed += 1
            if processed % 10 == 0:
                self.logger.info(f"已处理: {processed}/{len(scraped_items)}")

        self.logger.info(f"成功提取 {len(all_contacts)} 个联系人")
        return all_contacts

    def save_to_database(
        self,
        contacts: List[Dict[str, Any]],
        db_path: str = None,
        *,
        replace_links: Optional[List[str]] = None,
    ):
        """保存联系人到数据库"""
        if not contacts and not replace_links:
            return

        if not db_path:
            db_path = settings.get('storage.database_path', 'data/marketing.db')

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 创建表（如果不存在）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    source TEXT,
                    link TEXT,
                    scraped_at TEXT,
                    emails TEXT,
                    phones TEXT,
                    companies TEXT,
                    names TEXT,
                    addresses TEXT,
                    structured_contacts TEXT,
                    procurement_title TEXT,
                    organizations TEXT,
                    raw_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 兼容历史表结构：根据实际列决定插入字段
            cursor.execute("PRAGMA table_info(contacts)")
            existing_columns = {row[1] for row in cursor.fetchall()}

            # 轻量迁移：补齐新增字段（不破坏旧库）
            migrations = {
                "raw_text": "TEXT",
                "procurement_title": "TEXT",
                "organizations": "TEXT",
            }
            for column_name, column_type in migrations.items():
                if column_name in existing_columns:
                    continue
                try:
                    cursor.execute(f"ALTER TABLE contacts ADD COLUMN {column_name} {column_type}")
                except Exception:
                    # 老版本 SQLite/并发情况下可能失败：忽略即可
                    pass

            cursor.execute("PRAGMA table_info(contacts)")
            existing_columns = {row[1] for row in cursor.fetchall()}

            # 幂等写入：同一 link 仅保留最新一条，避免多次运行累积重复数据
            def _expand_link_variants(values: List[str]) -> List[str]:
                from urllib.parse import urlparse, urlunparse

                expanded: Set[str] = set()
                for raw_link in values:
                    if not isinstance(raw_link, str):
                        continue
                    link = raw_link.strip()
                    if not link:
                        continue

                    expanded.add(link)

                    parsed = urlparse(link)
                    if parsed.scheme and parsed.netloc:
                        normalized = urlunparse(parsed._replace(fragment="", query=""))
                        expanded.add(normalized)
                        candidates = {link, normalized}
                    else:
                        candidates = {link}

                    for candidate in candidates:
                        if candidate.startswith("http://"):
                            expanded.add("https://" + candidate[len("http://"):])
                        elif candidate.startswith("https://"):
                            expanded.add("http://" + candidate[len("https://"):])

                return sorted(expanded)

            if replace_links is not None:
                unique_links = _expand_link_variants([link for link in replace_links if isinstance(link, str)])
            else:
                links = [contact.get('link', '') for contact in contacts if contact.get('link')]
                unique_links = _expand_link_variants([link for link in links if isinstance(link, str)])
            if unique_links:
                chunk_size = 500  # SQLite 参数默认上限 999，预留余量
                for start in range(0, len(unique_links), chunk_size):
                    chunk = unique_links[start:start + chunk_size]
                    placeholders = ",".join(["?"] * len(chunk))
                    cursor.execute(f"DELETE FROM contacts WHERE link IN ({placeholders})", chunk)

            # 插入数据
            for contact in contacts:
                raw_text = contact.get('raw_text', '') or ''
                if isinstance(raw_text, str) and len(raw_text) > 5000:
                    raw_text = raw_text[:5000]

                columns = [
                    "title",
                    "source",
                    "link",
                    "scraped_at",
                    "emails",
                    "phones",
                    "companies",
                    "names",
                    "addresses",
                    "structured_contacts",
                ]
                values = [
                    contact.get("title", ""),
                    contact.get("source", ""),
                    contact.get("link", ""),
                    contact.get("scraped_at", ""),
                    json.dumps(contact.get("emails", []), ensure_ascii=False),
                    json.dumps(contact.get("phones", []), ensure_ascii=False),
                    json.dumps(contact.get("companies", []), ensure_ascii=False),
                    json.dumps(contact.get("names", []), ensure_ascii=False),
                    json.dumps(contact.get("addresses", []), ensure_ascii=False),
                    json.dumps(contact.get("structured_contacts", []), ensure_ascii=False),
                ]

                if "procurement_title" in existing_columns:
                    columns.append("procurement_title")
                    values.append(contact.get("procurement_title", "") or "")

                if "organizations" in existing_columns:
                    columns.append("organizations")
                    values.append(json.dumps(contact.get("organizations", {}) or {}, ensure_ascii=False))

                if "raw_text" in existing_columns:
                    columns.append("raw_text")
                    values.append(raw_text)

                placeholders = ",".join(["?"] * len(columns))
                cursor.execute(
                    f"INSERT INTO contacts ({', '.join(columns)}) VALUES ({placeholders})",
                    tuple(values),
                )

            conn.commit()
            conn.close()

            self.logger.info(f"保存了 {len(contacts)} 条联系人记录到数据库")

        except Exception as e:
            self.logger.error(f"保存到数据库失败: {e}")

    def export_to_json(self, contacts: List[Dict[str, Any]], filename: str = None):
        """导出联系人为JSON"""
        if not contacts:
            return

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"contacts_{timestamp}.json"

        filepath = self.export_dir / filename

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(contacts, f, ensure_ascii=False, indent=2)

            self.logger.info(f"导出 {len(contacts)} 条记录到 {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.error(f"导出JSON失败: {e}")
            return None

    def export_to_excel(self, contacts: List[Dict[str, Any]], filename: str = None):
        """导出联系人为Excel"""
        if not contacts:
            self.logger.warning("没有联系人数据可导出")
            return None

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"contacts_{timestamp}.xlsx"

        filepath = self.export_dir / filename

        # 检查依赖
        try:
            import pandas as pd
        except ImportError:
            self.logger.warning("pandas未安装，使用CSV格式导出")
            # 降级为CSV导出
            csv_filename = filename.replace('.xlsx', '.csv')
            csv_filepath = self.export_dir / csv_filename
            return self._export_to_csv_fallback(contacts, csv_filepath)

        try:
            import openpyxl
        except ImportError:
            self.logger.warning("openpyxl未安装，使用CSV格式导出")
            csv_filename = filename.replace('.xlsx', '.csv')
            csv_filepath = self.export_dir / csv_filename
            return self._export_to_csv_fallback(contacts, csv_filepath)

        try:
            # 展开联系人数据为表格形式
            rows = []
            for contact in contacts:
                # 为每个联系人的每个邮箱、电话等创建一行
                base_info = {
                    'ID': contact.get('id', ''),
                    '标题': contact.get('title', ''),
                    '来源': contact.get('source', ''),
                    '链接': contact.get('link', ''),
                    '爬取时间': contact.get('scraped_at', ''),
                    '角色': ', '.join(contact.get('roles', [])),
                    '公司': ', '.join(contact.get('companies', [])),
                    '姓名': ', '.join(contact.get('names', [])),
                    '地址': ', '.join(contact.get('addresses', []))
                }

                # 如果有多个邮箱或电话，创建多行
                emails = contact.get('emails', [])
                phones = contact.get('phones', [])

                max_items = max(len(emails), len(phones), 1)

                for i in range(max_items):
                    row = base_info.copy()
                    row['邮箱'] = emails[i] if i < len(emails) else ''
                    row['电话'] = phones[i] if i < len(phones) else ''
                    rows.append(row)

            # 创建DataFrame并导出
            df = pd.DataFrame(rows)
            df.to_excel(filepath, index=False, engine='openpyxl')

            self.logger.info(f"导出 {len(contacts)} 条记录到 {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.error(f"导出Excel失败: {e}")
            # 降级为CSV导出
            self.logger.info("降级为CSV格式导出")
            csv_filename = filename.replace('.xlsx', '.csv')
            csv_filepath = self.export_dir / csv_filename
            return self._export_to_csv_fallback(contacts, csv_filepath)

    def _export_to_csv_fallback(self, contacts: List[Dict[str, Any]], filepath: Path):
        """CSV导出降级方案"""
        try:
            import csv

            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)

                # 写入表头
                writer.writerow(['ID', '标题', '来源', '链接', '爬取时间', '角色',
                               '公司', '姓名', '地址', '邮箱', '电话'])

                # 写入数据
                for contact in contacts:
                    emails = contact.get('emails', [''])
                    phones = contact.get('phones', [''])
                    max_items = max(len(emails), len(phones), 1)

                    for i in range(max_items):
                        writer.writerow([
                            contact.get('id', ''),
                            contact.get('title', ''),
                            contact.get('source', ''),
                            contact.get('link', ''),
                            contact.get('scraped_at', ''),
                            ', '.join(contact.get('roles', [])),
                            ', '.join(contact.get('companies', [])),
                            ', '.join(contact.get('names', [])),
                            ', '.join(contact.get('addresses', [])),
                            emails[i] if i < len(emails) else '',
                            phones[i] if i < len(phones) else ''
                        ])

            self.logger.info(f"导出 {len(contacts)} 条记录到CSV: {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.error(f"导出CSV失败: {e}")
            return None

    def _quality_score_for_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        scoring_cfg = settings.get("export.quality_scoring", {}) or {}
        try:
            email_w = float(scoring_cfg.get("email_weight", 0.4) or 0.4)
            phone_w = float(scoring_cfg.get("phone_weight", 0.3) or 0.3)
            company_w = float(scoring_cfg.get("company_weight", 0.2) or 0.2)
            name_w = float(scoring_cfg.get("name_weight", 0.1) or 0.1)
        except (TypeError, ValueError):
            email_w, phone_w, company_w, name_w = 0.4, 0.3, 0.2, 0.1

        has_email = bool(record.get("emails"))
        has_phone = bool(record.get("phones"))
        has_company = bool(record.get("companies"))
        has_name = bool(record.get("names"))

        total = 0.0
        total += email_w if has_email else 0.0
        total += phone_w if has_phone else 0.0
        total += company_w if has_company else 0.0
        total += name_w if has_name else 0.0

        return {
            "total_score": round(total, 3),
            "has_email": has_email,
            "has_phone": has_phone,
            "has_company": has_company,
            "has_name": has_name,
        }

    def _annotate_quality_scores(self, contacts: List[Dict[str, Any]]) -> None:
        for contact in contacts:
            if not isinstance(contact, dict):
                continue
            contact["_quality_score"] = self._quality_score_for_record(contact)

    def _passes_tier(self, contact: Dict[str, Any], tier: str) -> bool:
        tier_cfg = settings.get(f"export.tiers.{tier}", {}) or {}

        try:
            min_confidence = float(tier_cfg.get("min_confidence", 0.0) or 0.0)
        except (TypeError, ValueError):
            min_confidence = 0.0

        score = (contact.get("_quality_score") or {}).get("total_score", 0.0) or 0.0
        try:
            score_value = float(score)
        except (TypeError, ValueError):
            score_value = 0.0

        if score_value < min_confidence:
            return False

        if bool(tier_cfg.get("require_email", False)) and not contact.get("emails"):
            return False
        if bool(tier_cfg.get("require_phone", False)) and not contact.get("phones"):
            return False
        if bool(tier_cfg.get("require_company", False)) and not contact.get("companies"):
            return False

        return True

    def _to_export_record(self, contact: Dict[str, Any], *, include_raw_text: bool) -> Dict[str, Any]:
        raw_text = contact.get("raw_text", "") or ""
        if not include_raw_text:
            raw_text = ""
        elif isinstance(raw_text, str) and len(raw_text) > 3000:
            raw_text = raw_text[:3000]

        return {
            "announcement": {
                "title": contact.get("title", "") or "",
                "source": contact.get("source", "") or "",
                "link": contact.get("link", "") or "",
                "scraped_at": contact.get("scraped_at", "") or "",
                "procurement_title": contact.get("procurement_title", "") or "",
                "organizations": contact.get("organizations", {}) or {},
            },
            "summary": {
                "emails": contact.get("emails", []) or [],
                "phones": contact.get("phones", []) or [],
                "companies": contact.get("companies", []) or [],
                "names": contact.get("names", []) or [],
                "addresses": contact.get("addresses", []) or [],
                "roles": contact.get("roles", []) or [],
            },
            "contacts": contact.get("structured_contacts", []) or [],
            "quality": contact.get("_quality_score", {}) or {},
            "raw_text": raw_text,
        }

    def export_contacts_tiered(
        self,
        contacts: List[Dict[str, Any]],
        *,
        mode: str = "tiered_json",
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """按 raw/clean/premium 三层导出联系人。

        mode:
        - tiered_json: 每层输出一个 JSON 数组文件
        - append_jsonl: 每层追加写入 JSONL（适合批处理/流水线）
        - none: 不写文件，仅返回统计
        """
        if not contacts:
            return {}

        run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self._annotate_quality_scores(contacts)

        tiers_cfg = settings.get("export.tiers", {}) or {}
        if not isinstance(tiers_cfg, dict):
            tiers_cfg = {}

        results: Dict[str, Any] = {"run_id": run_id}

        scores = [
            float((c.get("_quality_score") or {}).get("total_score", 0) or 0)
            for c in contacts
            if isinstance(c, dict)
        ]
        quality_report = {
            "avg_score": round(sum(scores) / len(scores), 3) if scores else 0.0,
            "min_score": min(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 0.0,
        }
        results["quality_report"] = quality_report

        for tier in ("raw", "clean", "premium"):
            tier_cfg = tiers_cfg.get(tier, {}) if isinstance(tiers_cfg.get(tier), dict) else {}
            enabled = bool(tier_cfg.get("enabled", True))
            if not enabled:
                continue

            if tier == "raw":
                selected = list(contacts)
            else:
                selected = [c for c in contacts if isinstance(c, dict) and self._passes_tier(c, tier)]

            export_records = [self._to_export_record(c, include_raw_text=(tier == "raw")) for c in selected if isinstance(c, dict)]

            filename = str(tier_cfg.get("filename") or f"contacts_{tier}_{{timestamp}}.json")
            filename = filename.replace("{timestamp}", run_id)

            export_path: Optional[str] = None
            if mode == "none":
                export_path = None
            elif mode == "append_jsonl":
                if filename.endswith(".json"):
                    filename = filename[:-5] + ".jsonl"
                filepath = self.export_dir / filename
                with open(filepath, "a", encoding="utf-8") as f:
                    for row in export_records:
                        f.write(json.dumps(row, ensure_ascii=False) + "\n")
                export_path = str(filepath)
            else:
                export_path = self.export_to_json(export_records, filename=filename)

            results[tier] = {"count": len(export_records), "path": export_path}

        return results

    def export_contacts_flat(
        self,
        contacts: List[Dict[str, Any]],
        *,
        mode: str = "append_jsonl",
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """扁平导出：每个结构化联系人一行（适合二次加工/导入CRM）。"""
        if not contacts:
            return {}

        flat_cfg = settings.get("export.flat", {}) or {}
        if not isinstance(flat_cfg, dict):
            flat_cfg = {}
        if not bool(flat_cfg.get("enabled", True)):
            return {}

        run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        include_raw_text = bool(flat_cfg.get("include_raw_text", False))

        filename = str(flat_cfg.get("filename") or "contacts_flat_{timestamp}.jsonl")
        filename = filename.replace("{timestamp}", run_id)
        if mode == "append_jsonl":
            if not filename.endswith(".jsonl"):
                if filename.endswith(".json"):
                    filename = filename[:-5] + ".jsonl"
                else:
                    filename = filename + ".jsonl"
        else:
            if filename.endswith(".jsonl"):
                filename = filename[:-1]  # .jsonl -> .json
            elif not filename.endswith(".json"):
                filename = filename + ".json"
        filepath = self.export_dir / filename

        rows: List[Dict[str, Any]] = []

        def _safe_first(values: Any) -> str:
            if isinstance(values, list) and values:
                return str(values[0] or "").strip()
            return ""

        for record in contacts:
            if not isinstance(record, dict):
                continue

            record_id = record.get("id", "")
            title = record.get("title", "") or ""
            source = record.get("source", "") or ""
            link = record.get("link", "") or ""
            scraped_at = record.get("scraped_at", "") or ""
            procurement_title = record.get("procurement_title", "") or ""

            record_raw_text = record.get("raw_text", "") or ""
            if not include_raw_text:
                record_raw_text = ""
            elif isinstance(record_raw_text, str) and len(record_raw_text) > 3000:
                record_raw_text = record_raw_text[:3000]

            fallback_company = _safe_first(record.get("companies"))
            fallback_name = _safe_first(record.get("names"))
            fallback_address = _safe_first(record.get("addresses"))
            fallback_email = _safe_first(record.get("emails"))
            fallback_phone = _safe_first(record.get("phones"))

            structured = record.get("structured_contacts") or []
            if not isinstance(structured, list):
                structured = []

            if not structured:
                structured = [
                    {
                        "company": fallback_company,
                        "name": fallback_name,
                        "email": fallback_email,
                        "phone": fallback_phone,
                        "mobile": "",
                        "address": fallback_address,
                        "role": "",
                        "role_label": "",
                        "source": "summary",
                    }
                ]

            for contact in structured:
                if not isinstance(contact, dict):
                    continue

                company = self._clean_company(contact.get("company") or fallback_company)
                name = self._clean_person_name(contact.get("name") or fallback_name)
                email = self._normalize_email(contact.get("email") or fallback_email)
                phone = self._normalize_phone(contact.get("phone") or fallback_phone)
                mobile = self._normalize_phone(contact.get("mobile") or "")
                address = self._clean_address(contact.get("address") or fallback_address)
                role = (contact.get("role") or "").strip()
                role_label = (contact.get("role_label") or "").strip()

                # 手机不要混入 phone 字段
                if phone.startswith("1") and len(phone) == 11 and not mobile:
                    mobile = phone
                    phone = ""

                # 质量分：按“每一行联系人”评估，而不是整条公告
                row_record = {
                    "emails": [email] if email else [],
                    "phones": [mobile or phone] if (mobile or phone) else [],
                    "companies": [company] if company else [],
                    "names": [name] if name else [],
                }
                quality = self._quality_score_for_record(row_record)
                row_record["_quality_score"] = quality
                tier = "raw"
                if self._passes_tier(row_record, "premium"):
                    tier = "premium"
                elif self._passes_tier(row_record, "clean"):
                    tier = "clean"

                rows.append(
                    {
                        "announcement_id": record_id,
                        "title": title,
                        "source": source,
                        "link": link,
                        "scraped_at": scraped_at,
                        "procurement_title": procurement_title,
                        "role": role,
                        "role_label": role_label,
                        "company": company,
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "mobile": mobile,
                        "address": address,
                        "tier": tier,
                        "quality": quality,
                        "raw_text": record_raw_text,
                    }
                )

        if not rows:
            return {}

        if mode == "none":
            return {"run_id": run_id, "flat": {"count": len(rows), "path": None}}

        if mode == "append_jsonl":
            with open(filepath, "a", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
        else:
            # 兜底：写成 JSON 数组
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=2)

        return {"run_id": run_id, "flat": {"count": len(rows), "path": str(filepath)}}

    def process_and_save(
        self,
        scraped_items: List[Dict[str, Any]],
        db_path: str = None,
        export_json: bool = True,
        export_excel: bool = None,
        *,
        export_mode: str = "tiered_json",
        export_run_id: Optional[str] = None,
    ):
        """
        处理并保存联系人信息 - 使用智能分层导出系统

        Args:
            scraped_items: 爬取的数据列表
            db_path: 数据库路径
            export_json: 是否导出JSON格式（已废弃，使用配置系统）
            export_excel: 是否导出Excel格式（已废弃，使用配置系统）

        Returns:
            List[Dict]: 提取的联系人列表
        """
        try:
            # 提取联系人
            contacts = self.extract_from_scraped_data(scraped_items)

            if not contacts:
                self.logger.warning("没有提取到联系人信息")
                return []

            self.logger.info(f"成功提取 {len(contacts)} 个联系人")

            export_results = self.export_contacts_tiered(
                contacts,
                mode=export_mode,
                run_id=export_run_id,
            )

            if export_results:
                print("\n📊 联系人导出完成:")
                print(f"📋 原始数据: {export_results.get('raw', {}).get('count', 0)} 条")
                print(f"✨ 清洁数据: {export_results.get('clean', {}).get('count', 0)} 条")
                print(f"⭐ 高级数据: {export_results.get('premium', {}).get('count', 0)} 条")
                if export_results.get('quality_report'):
                    print(f"📈 质量报告: {export_results['quality_report']}")

            # 可选：扁平导出（每个联系人一行）
            flat_run_id = None
            if isinstance(export_results, dict):
                flat_run_id = export_results.get("run_id")
            flat_results = self.export_contacts_flat(
                contacts,
                mode="append_jsonl",
                run_id=flat_run_id or export_run_id,
            )
            if flat_results.get("flat", {}).get("path"):
                print(f"🧾 扁平导出: {flat_results['flat']['count']} 条 -> {flat_results['flat']['path']}")

            # 保存到数据库（如果启用）
            if db_path and settings.get('storage.save_to_db', True):
                # 仅按“清洁层”规则过滤保存：提高现有/未来数据的可用性
                try:
                    min_confidence = float(settings.get('export.tiers.clean.min_confidence', 0.3) or 0.3)
                except (TypeError, ValueError):
                    min_confidence = 0.3
                require_email = bool(settings.get('export.tiers.clean.require_email', True))

                clean_contacts: List[Dict[str, Any]] = []
                for contact in contacts:
                    score = (contact.get('_quality_score', {}) or {}).get('total_score', 0) or 0
                    try:
                        score_value = float(score)
                    except (TypeError, ValueError):
                        score_value = 0.0
                    if score_value < min_confidence:
                        continue
                    if require_email and not contact.get('emails'):
                        continue
                    clean_contacts.append(contact)

                # 替换式写入：即使 clean_contacts 为空，也先清掉这些 link 的历史数据（避免脏数据残留）
                replace_links = [item.get('link', '') for item in scraped_items if item.get('link')]
                self.save_to_database(clean_contacts, db_path, replace_links=replace_links)
                self.logger.info(f"清洁层数据已写入 contacts 表: {db_path} ({len(clean_contacts)} 条)")

            return contacts

        except Exception as e:
            self.logger.error(f"处理联系人信息时发生错误: {e}")
            self.logger.exception("详细错误信息:")
            print(f"❌ 处理联系人失败: {e}")
            return []


# 创建全局实例（兼容旧代码）
extractor = ContactExtractor()


# 便捷函数
def extract_contacts(scraped_items: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
    """便捷的联系人提取函数"""
    return extractor.extract_from_scraped_data(scraped_items)


if __name__ == "__main__":
    # 测试数据
    test_data = [
        {
            'id': 1,
            'title': '测试公告',
            'detail_content': '采购单位：测试大学，联系人：张老师，电话：010-12345678，邮箱：test@university.edu.cn'
        }
    ]

    # 测试提取
    contacts = extractor.extract_from_scraped_data(test_data)
    print(f"提取到 {len(contacts)} 个联系人")
    if contacts:
        print(json.dumps(contacts[0], ensure_ascii=False, indent=2))
