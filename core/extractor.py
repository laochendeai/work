#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联系人提取器
智能提取联系人信息，支持政府采购网等结构化格式
"""

import re
import logging
import json
import time
from typing import Dict, List, Any, Optional
import sqlite3
from pathlib import Path

# 导入处理器
from .ai_processor import AIContactProcessor
from .local_processor import LocalContactProcessor
from config.settings import settings

class ContactExtractor:
    """联系人提取器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_patterns()

        # 初始化处理器
        config = settings.load_user_config()
        contact_config = config.get('contact_processing', {})

        # 根据配置选择处理器
        self.processing_method = contact_config.get('method', 'local')
        self.local_processor = LocalContactProcessor()
        self.ai_processor = AIContactProcessor(config) if contact_config.get('ai_processing.enabled', False) else None

    def _setup_patterns(self):
        """设置提取模式"""
        # 邮箱模式
        self.email_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'邮箱[：:]\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'电子邮箱[：:]\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        ]

        # 电话模式 - 支持政府采购网格式
        self.phone_patterns = [
            r'1[3-9]\d{9}',  # 手机号
            r'\d{3,4}-\d{7,8}',  # 座机
            r'(\d{4}-?)?\d{7,8}',  # 座机(可选区号)
            r'电话[：:]\s*(\d{3,4}-?\d{7,8}|1[3-9]\d{9})',
            r'手机[：:]\s*(1[3-9]\d{9})',
            r'联系方式[：:]\s*([^\s]*?(\d{3,4}-?\d{7,8}|1[3-9]\d{9})[^\s]*)',
            # 政府采购网特定格式
            r'联系方式[：:：\s]*[^\d]*(\d{3,4}-?\d{7,8}|1[3-9]\d{9})',
            r'电\s*话[：:：\s]*[^\d]*(\d{3,4}-?\d{7,8}|1[3-9]\d{9})',
            r'([A-Za-z\u4e00-\u9fa5]{1,10})\s*(\d{3,4}-?\d{7,8}|1[3-9]\d{9})',
        ]

        # 姓名/联系人模式
        self.name_patterns = [
            r'联系人[：:]\s*([A-Za-z\u4e00-\u9fa5]{2,10})',
            r'负责人[：:]\s*([A-Za-z\u4e00-\u9fa5]{2,10})',
            r'项目经理[：:]\s*([A-Za-z\u4e00-\u9fa5]{2,10})',
            r'采购人[：:]\s*([A-Za-z\u4e00-\u9fa5]{2,10})',
            r'项目联系人[：:]\s*([A-Za-z\u4e00-\u9fa5]{2,10})',
            # 政府采购网特定格式
            r'名\s*称[：:：\s]*([^\s\u3000]+?)\s*?(?:地址|联系方式|电\s*话|项目联系人)',
            r'联系人[：:：\s]*([^\s\u3000]+?)(?:\s|$|\d|，|。)',
            r'([A-Za-z\u4e00-\u9fa5]{2,5})(?:\s)*(?:\d{3,4}-?\d{7,8}|1[3-9]\d{9})',
        ]

        # 公司/单位模式
        self.company_patterns = [
            r'([^\s，,。\n]+(?:公司|集团|企业|单位|学校|大学|学院|研究院|有限公司|有限责任公司|股份公司))',
            r'采购单位[：:]\s*([^\s，,。\n]+)',
            r'招标单位[：:]\s*([^\s，,。\n]+)',
            r'供应商[：:]\s*([^\s，,。\n]+)',
            r'中标单位[：:]\s*([^\s，,。\n]+)',
            r'名\s*称[：:：\s]*([^\s，,。\n]+?)(?:\s|地址|联系方式|电\s*话)',
            r'代理机构[：:：\s]*([^\s，,。\n]+?)(?:\s|地址|联系方式|电\s*话)',
        ]

        # 地址模式
        self.address_patterns = [
            r'地址[：:]\s*([^\s，,。\n]{10,100})',
            r'地\s*址[：:：\s]*([^\s，,。\n]{10,100})',
        ]

    def extract_from_text(self, text: str) -> Dict[str, Any]:
        """从文本中提取联系人信息"""
        if not text:
            return {}

        # 修复编码问题
        text = self._fix_encoding(text)

        # 使用智能处理器提取
        smart_contacts = self._extract_with_processors(text)

        # 基础提取作为补充
        result = {
            'emails': self._extract_emails(text),
            'phones': self._extract_phones(text),
            'companies': self._extract_companies(text),
            'names': self._extract_names(text),
            'addresses': self._extract_addresses(text),
            'structured_contacts': self._extract_structured_contacts(text),
            'smart_contacts': smart_contacts,  # 智能提取的结构化联系人
            'raw_text': text
        }

        # 合并和优化结果
        result = self._merge_extraction_results(result)

        return result

    def _extract_with_processors(self, text: str) -> List[Dict[str, Any]]:
        """使用处理器提取联系人信息"""
        contacts = []

        try:
            # 本地处理（始终启用）
            local_contacts = self.local_processor.extract_contacts_from_text(text)

            # 转换为字典格式
            for contact in local_contacts:
                contact_dict = {
                    'name': contact.name,
                    'company': contact.company,
                    'phone': contact.phone,
                    'email': contact.email,
                    'address': contact.address,
                    'department': contact.department,
                    'position': contact.position,
                    'confidence': contact.confidence,
                    'source': contact.source
                }
                contacts.append(contact_dict)

            # AI处理（如果启用且配置为混合模式）
            if (self.processing_method == 'hybrid' or self.processing_method == 'ai') and self.ai_processor:
                try:
                    ai_contacts = self.ai_processor.process_text_batch([text])

                    # 转换为字典格式
                    for contact in ai_contacts:
                        contact_dict = {
                            'name': contact.name,
                            'company': contact.company,
                            'phone': contact.phone,
                            'email': contact.email,
                            'address': contact.address,
                            'department': contact.department,
                            'position': contact.position,
                            'confidence': contact.confidence,
                            'source': 'ai_extraction'
                        }
                        contacts.append(contact_dict)

                except Exception as e:
                    self.logger.error(f"AI提取失败，使用本地结果: {e}")

            return contacts

        except Exception as e:
            self.logger.error(f"联系人提取失败: {e}")
            return []

    def _merge_extraction_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """合并提取结果，去重并优化"""
        all_contacts = []

        # 添加智能提取的联系人（本地+AI）
        smart_contacts = result.get('smart_contacts', [])
        for contact in smart_contacts:
            # 根据处理方法设置置信度阈值
            threshold = 0.3 if self.processing_method == 'local' else 0.5
            if contact.get('confidence', 0) > threshold:
                all_contacts.append(contact)

        # 添加基础提取的联系人（作为补充）
        basic_contacts = result.get('structured_contacts', [])
        for contact in basic_contacts:
            # 简单去重：检查是否已存在相似的联系人
            if not self._is_duplicate_contact(contact, all_contacts):
                contact['source'] = 'basic_extraction'
                contact['confidence'] = 0.2
                all_contacts.append(contact)

        # 按置信度排序
        all_contacts.sort(key=lambda x: x.get('confidence', 0), reverse=True)

        # 限制返回数量
        max_contacts = 10
        all_contacts = all_contacts[:max_contacts]

        # 更新结果
        result['merged_contacts'] = all_contacts
        result['total_contacts'] = len(all_contacts)
        result['processing_method'] = self.processing_method

        return result

    def _is_duplicate_contact(self, contact: Dict[str, Any], existing_contacts: List[Dict[str, Any]]) -> bool:
        """检查是否为重复联系人"""
        contact_name = contact.get('contact_name', '').strip()
        contact_phone = contact.get('phone', '').strip()

        if not contact_name and not contact_phone:
            return True  # 无效联系人，视为重复

        for existing in existing_contacts:
            existing_name = existing.get('name', '').strip()
            existing_phone = existing.get('phone', '').strip()

            # 姓名或电话相同则认为是重复
            if (contact_name and existing_name and contact_name == existing_name) or \
               (contact_phone and existing_phone and contact_phone == existing_phone):
                return True

        return False

    def _fix_encoding(self, text: str) -> str:
        """修复编码问题"""
        if hasattr(text, 'encode'):
            try:
                return text.encode('latin1').decode('utf-8', errors='ignore')
            except:
                try:
                    return text.encode('cp1252').decode('utf-8', errors='ignore')
                except:
                    return text
        return text

    def _extract_emails(self, text: str) -> List[str]:
        """提取邮箱"""
        emails = set()
        for pattern in self.email_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if self._is_valid_email(match):
                    emails.add(match.lower())
        return list(emails)

    def _extract_phones(self, text: str) -> List[str]:
        """提取电话号码"""
        phones = set()
        for pattern in self.phone_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    # 如果是元组，取最后一个元素（通常是电话号码）
                    match = match[-1]
                if self._is_valid_phone(match):
                    phones.add(match)
        return list(phones)

    def _extract_companies(self, text: str) -> List[str]:
        """提取公司/单位名称"""
        companies = set()
        for pattern in self.company_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                match = match.strip()
                if len(match) > 2 and len(match) < 50:
                    # 过滤一些明显不是公司的内容
                    exclude_words = ['地址', '联系方式', '电话', '项目', '采购', '中标', '公告', '名称']
                    if not any(word in match for word in exclude_words):
                        companies.add(match)
        return list(companies)

    def _extract_names(self, text: str) -> List[str]:
        """提取姓名"""
        names = set()
        for pattern in self.name_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                match = match.strip()
                if self._is_valid_name(match):
                    names.add(match)
        return list(names)

    def _extract_addresses(self, text: str) -> List[str]:
        """提取地址"""
        addresses = set()
        for pattern in self.address_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                match = match.strip()
                if len(match) > 5 and len(match) < 200:
                    addresses.add(match)
        return list(addresses)

    def _extract_structured_contacts(self, text: str) -> List[Dict[str, Any]]:
        """提取结构化联系人信息（政府采购网格式）"""
        structured_contacts = []

        # 分割文本，按数字标记的结构化信息
        sections = re.split(r'\d+\.\s*', text)

        for section in sections:
            if not section.strip():
                continue

            contact = {}
            lines = [line.strip() for line in section.split('\n') if line.strip()]

            for line in lines:
                # 名称
                if re.search(r'名称|名\s*称', line):
                    name_match = re.search(r'名称[：:：\s]*([^\s]+)', line)
                    if name_match:
                        contact['name'] = name_match.group(1).strip()
                    else:
                        # 提取冒号后的内容
                        if '：' in line or ':' in line:
                            parts = re.split(r'[：:：]', line, 1)
                            if len(parts) > 1:
                                contact['name'] = parts[1].strip()

                # 联系人
                elif re.search(r'联系人|项目联系人', line):
                    contact_match = re.search(r'(?:联系人|项目联系人)[：:：\s]*([^\s,，。]+)', line)
                    if contact_match:
                        contact['contact_name'] = contact_match.group(1).strip()

                # 电话
                elif re.search(r'联系方式|电话|电\s*话', line):
                    phone_match = re.search(r'联系方式[：:：\s]*([^\s]*?(\d{3,4}-?\d{7,8}|1[3-9]\d{9})[^\s]*)', line)
                    if not phone_match:
                        phone_match = re.search(r'电\s*话[：:：\s]*([^\s]*?(\d{3,4}-?\d{7,8}|1[3-9]\d{9})[^\s]*)', line)

                    if phone_match:
                        # 清理电话号码，去除姓名部分
                        phone_text = phone_match.group(1)
                        # 检查是否包含中文姓名
                        chinese_name_match = re.search(r'([A-Za-z\u4e00-\u9fa5]{2,5})(\d{3,4}-?\d{7,8}|1[3-9]\d{9})', phone_text)
                        if chinese_name_match:
                            if not contact.get('contact_name'):
                                contact['contact_name'] = chinese_name_match.group(1).strip()
                            contact['phone'] = chinese_name_match.group(2).strip()
                        else:
                            # 只提取电话号码部分
                            phone_number_match = re.search(r'(\d{3,4}-?\d{7,8}|1[3-9]\d{9})', phone_text)
                            if phone_number_match:
                                contact['phone'] = phone_number_match.group(1).strip()

                # 地址
                elif re.search(r'地址|地\s*址', line):
                    address_match = re.search(r'(?:地址|地\s*址)[：:：\s]*([^\s]+)', line)
                    if address_match:
                        contact['address'] = address_match.group(1).strip()

                # 公司名称/采购人
                elif re.search(r'采购人|代理机构|中标单位|名称', line):
                    company_match = re.search(r'(?:采购人|代理机构|中标单位|名称)[：:：\s]*([^\s]+)', line)
                    if company_match:
                        company = company_match.group(1).strip()
                        # 过滤掉明显不是公司的内容
                        if len(company) > 2 and not any(word in company for word in ['地址', '联系方式', '电话']):
                            contact['company'] = company

            # 如果有有效信息，添加到结果
            if any([contact.get('name'), contact.get('contact_name'), contact.get('phone'), contact.get('address'), contact.get('company')]):
                # 清理和标准化联系人信息
                cleaned_contact = {}
                for key, value in contact.items():
                    if value:
                        cleaned_contact[key] = value.strip()

                structured_contacts.append(cleaned_contact)

        return structured_contacts

    def _is_valid_email(self, email: str) -> bool:
        """验证邮箱格式"""
        if not email or '@' not in email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def _is_valid_phone(self, phone: str) -> bool:
        """验证电话号码格式"""
        if not phone:
            return False
        # 清理电话号码
        clean_phone = re.sub(r'[^\d-]', '', phone)
        if len(clean_phone) >= 7 and len(clean_phone) <= 11:
            return True
        return False

    def _is_valid_name(self, name: str) -> bool:
        """验证姓名格式"""
        if not name:
            return False
        # 排除一些明显不是姓名的内容
        exclude_words = ['公司', '有限公司', '集团', '企业', '单位', '学校', '大学', '学院', '地址', '联系方式', '电话', '项目']
        return not any(word in name for word in exclude_words) and 2 <= len(name) <= 15

    def extract_from_scraped_data(self, scraped_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从爬取的数据中提取联系人信息"""
        contacts = []

        for item in scraped_items:
            # 合并标题和详细内容
            text = f"{item.get('title', '')} {item.get('detail_content', '')}"
            contact_info = self.extract_from_text(text)

            # 创建联系人记录
            contact = {
                'id': len(contacts) + 1,
                'title': item.get('title', ''),
                'source': item.get('source', ''),
                'link': item.get('link', ''),
                'scraped_at': item.get('scraped_at', ''),
                'emails': contact_info.get('emails', []),
                'phones': contact_info.get('phones', []),
                'companies': contact_info.get('companies', []),
                'names': contact_info.get('names', []),
                'addresses': contact_info.get('addresses', []),
                'structured_contacts': contact_info.get('structured_contacts', []),
                'raw_text': contact_info.get('raw_text', ''),
            }

            # 从结构化联系人中提取更多信息
            if contact_info.get('structured_contacts'):
                # 合并结构化联系人信息到普通字段
                all_phones = set(contact['phones'])
                all_names = set(contact['names'])
                all_companies = set(contact['companies'])
                all_addresses = set(contact['addresses'])

                for struct_contact in contact_info['structured_contacts']:
                    if struct_contact.get('phone'):
                        all_phones.add(struct_contact['phone'])
                    if struct_contact.get('contact_name'):
                        all_names.add(struct_contact['contact_name'])
                    if struct_contact.get('name'):
                        all_names.add(struct_contact['name'])
                    if struct_contact.get('company'):
                        all_companies.add(struct_contact['company'])
                    if struct_contact.get('address'):
                        all_addresses.add(struct_contact['address'])

                contact['phones'] = list(all_phones)
                contact['names'] = list(all_names)
                contact['companies'] = list(all_companies)
                contact['addresses'] = list(all_addresses)

            # 如果有有效的联系人信息，添加到结果中
            if (contact['emails'] or contact['phones'] or contact['companies'] or
                contact['names'] or contact['structured_contacts']):
                contacts.append(contact)

        return contacts

    def save_to_database(self, contacts: List[Dict[str, Any]], db_path: str = None):
        """保存到数据库"""
        if not db_path:
            db_path = "data/marketing.db"

        db_path = Path(db_path)
        db_path.parent.mkdir(exist_ok=True)

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # 创建表
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
                    raw_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 插入数据
            for contact in contacts:
                cursor.execute('''
                    INSERT INTO contacts
                    (title, source, link, scraped_at, emails, phones, companies, names, addresses, structured_contacts, raw_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    contact['title'],
                    contact['source'],
                    contact['link'],
                    contact['scraped_at'],
                    json.dumps(contact['emails'], ensure_ascii=False),
                    json.dumps(contact['phones'], ensure_ascii=False),
                    json.dumps(contact['companies'], ensure_ascii=False),
                    json.dumps(contact['names'], ensure_ascii=False),
                    json.dumps(contact['addresses'], ensure_ascii=False),
                    json.dumps(contact['structured_contacts'], ensure_ascii=False),
                    contact['raw_text']
                ))

            conn.commit()
            conn.close()

            self.logger.info(f"保存了 {len(contacts)} 条联系人记录到数据库")

        except Exception as e:
            self.logger.error(f"保存到数据库失败: {e}")

    def export_to_excel(self, contacts: List[Dict[str, Any]], filename: str = None):
        """导出到Excel"""
        if not filename:
            filename = f"contacts_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"

        try:
            import pandas as pd

            # 准备数据
            df_data = []
            for contact in contacts:
                # 基础信息
                row = {
                    '标题': contact['title'],
                    '来源': contact['source'],
                    '链接': contact['link'],
                    '爬取时间': contact['scraped_at'],
                    '邮箱': '; '.join(contact['emails']),
                    '电话': '; '.join(contact['phones']),
                    '联系人': '; '.join(contact['names']),
                    '公司': '; '.join(contact['companies']),
                    '地址': '; '.join(contact['addresses'])
                }

                # 从结构化联系人中提取详细信息
                if contact.get('structured_contacts'):
                    structured_info = []
                    for i, struct_contact in enumerate(contact['structured_contacts']):
                        contact_info = []
                        if struct_contact.get('contact_name'):
                            contact_info.append(f"联系人: {struct_contact['contact_name']}")
                        if struct_contact.get('phone'):
                            contact_info.append(f"电话: {struct_contact['phone']}")
                        if struct_contact.get('company'):
                            contact_info.append(f"公司: {struct_contact['company']}")
                        if struct_contact.get('address'):
                            contact_info.append(f"地址: {struct_contact['address']}")

                        # 合并信息
                        row[f'结构化联系人{i+1}'] = ' | '.join(contact_info) if contact_info else '无详细信息'

                df_data.append(row)

            df = pd.DataFrame(df_data)
            df.to_excel(filename, index=False)
            self.logger.info(f"导出 {len(contacts)} 条记录到 {filename}")

        except ImportError:
            self.logger.error("需要安装pandas和openpyxl才能导出Excel")
        except Exception as e:
            self.logger.error(f"导出Excel失败: {e}")

    def test_extraction(self, sample_text: str = None):
        """测试提取功能"""
        if not sample_text:
            sample_text = """
            九、凡对本次公告内容提出询问，请按以下方式联系。

            1.采购人信息

            名 称：徐州市消防救援支队
            地址：徐州市云龙区柳集立交桥与G30连霍高速交叉口南480米
            联系方式：吴先生0516-83069299

            2.采购代理机构信息

            名 称：华辰中大项目管理有限公司
            地　址：徐州市泉山区山语世家A1号楼1907
            联系方式：许宁18052114767

            3.项目联系方式

            项目联系人：许宁
            电　话：　　18052114767
            """

        result = self.extract_from_text(sample_text)
        print("📊 联系人提取测试结果:")
        print(f"   邮箱: {result.get('emails', [])}")
        print(f"   电话: {result.get('phones', [])}")
        print(f"   姓名: {result.get('names', [])}")
        print(f"   公司: {result.get('companies', [])}")
        print(f"   地址: {result.get('addresses', [])}")
        print(f"   结构化联系人: {result.get('structured_contacts', [])}")
        return result

# 全局提取器实例
extractor = ContactExtractor()