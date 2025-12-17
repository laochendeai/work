#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结构化联系人提取器 - 专为政府采购网站设计
正确解析采购人信息、代理机构信息和项目联系方式
"""

import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

class StructuredContactExtractor:
    """结构化联系人提取器 - 专门处理政府采购网站的联系方式"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # 编译正则表达式模式
        self._compile_patterns()

    def _compile_patterns(self):
        """编译所有正则表达式模式"""

        # 采购标题提取模式 - 从开头匹配完整的标题
        self.title_patterns = [
            # 匹配完整的标题，直到日期或来源
            r'^([^0-9]{10,100}?)(?:\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{2}-\d{2}|来源|【)',
            # 匹配项目名称后的完整标题
            r'采购项目名称\s*([^\n\r]{10,100})(?=\s|,|，|。|:|：|$)',
            # 匹配公告标题（去除html标签）
            r'<title[^>]*>([^<]+)</title>',
        ]

        # 机构信息提取模式
        self.organization_section_patterns = [
            # 采购人信息部分 - 支持"九、凡对本次公告内容提出询问，请按以下方式联系。1.采购人信息"格式
            (r'(?:九、[^1]*?1\.)?\s*采购人信息[：:]?\s*\n?(.*?)(?=\s*2\.|采购代理机构信息|项目联系方式|$)', 'purchaser'),
            # 采购代理机构信息部分
            (r'(?:2\.)?\s*采购代理机构信息[：:]?\s*\n?(.*?)(?=\s*3\.|项目联系方式|其他|凡对|$)', 'agent'),
            # 项目联系方式部分
            (r'(?:3\.)?\s*项目联系方式[：:]?\s*\n?(.*?)(?=\s*其他|附件|凡对|公告|投诉|$)', 'project_contacts'),

            # 备用模式 - 没有编号的情况
            (r'采购人[：:]?\s*名\s*称\s*[：:]?\s*([^\n]+?)\s*地址\s*[：:]?\s*([^\n]+?)\s*联系方式\s*[：:]?\s*([^\n]+)', 'purchaser_direct'),
            (r'代理机构[：:]?\s*名\s*称\s*[：:]?\s*([^\n]+?)\s*地址\s*[：:]?\s*([^\n]+?)\s*联系方式\s*[：:]?\s*([^\n]+)', 'agent_direct'),

            # 简单格式 - 采购单位信息
            (r'采购单位\s*([^\n\r]+?)\s*采购单位地址\s*([^\n\r]+?)\s*采购单位联系方式\s*([^\n\r]+)', 'purchaser_simple'),
            (r'代理机构名称\s*([^\n\r]+?)\s*代理机构地址\s*([^\n\r]+?)\s*代理机构联系方式\s*([^\n\r]+)', 'agent_simple'),
        ]

        # 机构详细信息模式
        self.org_detail_patterns = {
            'name': [
                r'名\s*称\s*[:：]\s*([^\n,，。；;]+?)(?=\s|,|，|。|；|;|$)',
                r'^\s*([^\s,，。；;]{2,30}?)(?=\s|地址|联系方式|：|$)',
            ],
            'address': [
                r'地址\s*[:：]\s*([^\n,，。；;]{10,100})(?=\s|,|，|。|；|;|$)',
                r'地　址\s*[:：]\s*([^\n,，。；;]{10,100})(?=\s|,|，|。|；|;|$)',
            ]
        }

        # 联系人提取模式
        self.contact_patterns = {
            'single_contact': r'([^\n,，。；;]{2,10})\s*[:：]?\s*([^\n,，。；;]+?)\s*(?=[,，、]|$|\n)',
            'multi_contact': r'项目联系人\s*[:：]?\s*([^\n]+?)(?=\s*项目联系电话|电\s*话|手机|$)',
            'contact_list': r'[:：]?\s*([^\n,，。；;]{2,10})(?:，|,|、)([^\n,，。；;]{2,10})(?:，|,|、)',
        }

        # 电话提取模式
        self.phone_patterns = [
            r'(?:电话|手机|联系方式|项目联系电话|电\s*话)\s*[:：]?\s*([^\n\r,，。；;]+)',
            r'(1[3-9]\d{9})',  # 手机号
            r'(0\d{2,3}[-\s]?\d{7,8})',  # 固话
            r'(\d{3,4}[-/]\d{7,8})',  # 带分隔符的固话
        ]

        # 邮箱提取模式
        self.email_patterns = [
            r'(?:邮箱|Email|电子邮箱)\s*[:：]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        ]

        # 无效姓名模式
        self.invalid_name_patterns = [
            r'^(?:\d+|[a-zA-Z]+|及联系方式|项目联系人|采购单位|代理机构)$',
            r'^(?:联系人|联系方式|联系电话|电\s*话|手\s*机|邮\s*箱|电子邮箱)$',
            r'^[0-9]+$',  # 纯数字
            r'^.{1}$',    # 单个字符
            r'(?:招标|采购|代理|项目|公告|中标)',  # 包含这些关键字的通常不是人名
        ]

    def extract_procurement_title(self, content: str, title: str = None) -> str:
        """提取完整的采购标题"""

        # 如果提供了title字段，先尝试使用它
        if title and len(title) > 10:
            # 清理HTML标签
            clean_title = re.sub(r'<[^>]+>', '', title)
            if len(clean_title) > 10:
                return clean_title.strip()

        # 从内容中提取
        lines = content.split('\n')
        for line in lines[:5]:  # 只检查前5行
            line = line.strip()
            if len(line) < 10:
                continue

            # 跳过纯数字、日期行
            if re.match(r'^\d{4}[-年]\d{1,2}[-月]\d{1,2}', line):
                continue

            # 跳过来源信息
            if '来源' in line or '【' in line:
                continue

            # 如果这一行看起来像标题
            if not re.search(r'[:：]\s*\w', line) and len(line) > 10:
                # 清理HTML标签
                clean_line = re.sub(r'<[^>]+>', '', line)
                if len(clean_line) > 10:
                    return clean_line.strip()

        # 使用模式匹配
        for pattern in self.title_patterns:
            match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
            if match:
                title_text = match.group(1).strip()
                # 进一步清理
                title_text = re.sub(r'<[^>]+>', '', title_text)
                if len(title_text) > 10 and not re.search(r'^\d', title_text):
                    return title_text

        # 如果都失败了，返回第一行长文本
        for line in content.split('\n')[:3]:
            line = line.strip()
            if len(line) > 20:
                return re.sub(r'<[^>]+>', '', line)

        return ""

    def is_valid_name(self, name: str) -> bool:
        """检查姓名是否有效"""
        if not name or len(name.strip()) < 2:
            return False

        name = name.strip()

        # 机构/组织后缀：出现这些基本不是人名（避免“某某大学/XX医院/财政局”等被误判）
        org_hints = [
            '公司', '有限公司', '有限责任公司', '股份有限公司', '集团',
            '大学', '学院', '学校', '医院', '中心', '研究院', '研究所',
            '政府', '委员会', '局', '厅', '处', '办', '所', '站', '队', '馆', '部'
        ]
        if any(hint in name for hint in org_hints):
            return False

        # 检查无效模式
        for pattern in self.invalid_name_patterns:
            if re.search(pattern, name):
                return False

        # 检查是否包含数字（年龄除外）
        if re.search(r'\d{3,}', name):
            return False

        # 检查中文字符比例
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', name))
        if len(name) > 0 and chinese_chars / len(name) < 0.5:
            return False

        # 常见的无效后缀
        invalid_suffixes = ['及联系方式', '等', '有限公司', '项目', '公告']
        for suffix in invalid_suffixes:
            if name.endswith(suffix):
                return False

        return True

    def _dedupe_keep_order(self, values: List[str]) -> List[str]:
        seen = set()
        deduped: List[str] = []
        for value in values:
            v = str(value).strip()
            if not v or v in seen:
                continue
            seen.add(v)
            deduped.append(v)
        return deduped

    def _extract_phone_numbers(self, text: str) -> List[str]:
        """更可靠的电话提取：只提取号码本体，避免把“电话：xxx 传真：yyy”拼成一个长串。"""
        if not text:
            return []

        scan = str(text)
        scan = scan.replace('（', '(').replace('）', ')')

        results: List[str] = []

        # 手机（允许 +86/空格/连字符）
        for match in re.finditer(r'(?<!\d)(?:\+?86[-\s]?)?(1[3-9]\d)[-\s]?(\d{4})[-\s]?(\d{4})(?!\d)', scan):
            results.append(match.group(1) + match.group(2) + match.group(3))
        for match in re.finditer(r'(?<!\d)1[3-9]\d{9}(?!\d)', scan):
            results.append(match.group(0))

        # 固话（排除“传真”上下文）
        for match in re.finditer(r'(?<!\d)(0\d{2,3})[()（）\s\-]*?(\d{7,8})(?!\d)', scan):
            prefix = scan[max(0, match.start() - 6):match.start()].lower()
            if '传真' in prefix or 'fax' in prefix:
                continue
            results.append(f"{match.group(1)}-{match.group(2)}")

        # 400/800
        for match in re.finditer(r'(?<!\d)([48]00)[-\s]?(\d{3,4})[-\s]?(\d{3,4})(?!\d)', scan):
            prefix = scan[max(0, match.start() - 6):match.start()].lower()
            if '传真' in prefix or 'fax' in prefix:
                continue
            results.append(f"{match.group(1)}-{match.group(2)}{match.group(3)}")

        return self._dedupe_keep_order(results)

    def extract_organization_info(self, section_text: str, org_type: str) -> Dict[str, Any]:
        """从机构段落中提取信息"""
        org_info = {
            'name': '',
            'address': '',
            'contacts': []
        }

        # 提取机构名称
        for pattern in self.org_detail_patterns['name']:
            match = re.search(pattern, section_text)
            if match:
                name = match.group(1).strip()
                if len(name) > 2 and not self.is_valid_name(name):
                    org_info['name'] = name
                    break

        # 如果没找到，尝试从段落开头提取
        if not org_info['name']:
            lines = section_text.split('\n')
            for line in lines[:2]:
                line = line.strip()
                # 跳过包含联系方式的行
                if any(keyword in line for keyword in ['电话', '手机', '邮箱', '联系方式']):
                    continue
                # 提取可能的机构名
                potential_name = re.split(r'[:：,，]', line)[0].strip()
                if len(potential_name) > 3 and not self.is_valid_name(potential_name):
                    org_info['name'] = potential_name
                    break

        # 提取地址
        for pattern in self.org_detail_patterns['address']:
            match = re.search(pattern, section_text)
            if match:
                address = match.group(1).strip()
                if len(address) > 10:
                    org_info['address'] = address
                    break

        return org_info

    def extract_contacts_from_section(self, section_text: str, org_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从段落中提取联系人信息"""
        contacts = []

        # 先尝试提取多个联系人
        multi_match = re.search(self.contact_patterns['multi_contact'], section_text)
        if multi_match:
            contact_names_text = multi_match.group(1).strip()
            # 分割多个联系人姓名
            names = re.split(r'[，,、]', contact_names_text)
            valid_names = []
            for name in names:
                name = name.strip()
                if self.is_valid_name(name):
                    valid_names.append(name)

            phones = self._extract_phone_numbers(section_text)

            # 提取所有邮箱
            emails = []
            for pattern in self.email_patterns:
                matches = re.findall(pattern, section_text)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[1] if len(match) > 1 else match[0]
                    email = str(match).strip()
                    if '@' in email and email not in emails:
                        emails.append(email)

            # 为每个有效姓名创建联系人记录
            for i, name in enumerate(valid_names):
                contact = {
                    'name': name,
                    'role': '项目联系人' if org_info.get('name') else '联系人',
                    'phones': phones,  # 所有联系人共享这些电话
                    'emails': emails,  # 所有联系人共享这些邮箱
                }
                contacts.append(contact)

        # 如果没有找到多个联系人，尝试单个联系人提取
        if not contacts:
            # 尝试提取"姓名：联系方式"格式
            single_matches = re.findall(self.contact_patterns['single_contact'], section_text)
            for name, contact_info in single_matches:
                if self.is_valid_name(name):
                    phones = self._extract_phone_numbers(contact_info)

                    # 提取邮箱
                    email_matches = re.findall(self.email_patterns[0], contact_info)
                    emails = [email for email in email_matches]

                    contact = {
                        'name': name,
                        'role': '联系人',
                        'phones': phones,
                        'emails': emails,
                    }
                    contacts.append(contact)

        # 如果还是没有找到，尝试从整段中提取
        if not contacts:
            # 提取所有可能的有效姓名
            all_names = []
            for line in section_text.split('\n'):
                words = re.split(r'[，,、：:\s]+', line)
                for word in words:
                    if self.is_valid_name(word):
                        all_names.append(word)

            phones = self._extract_phone_numbers(section_text)

            emails = []
            for pattern in self.email_patterns:
                matches = re.findall(pattern, section_text)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[1] if len(match) > 1 else match[0]
                    email = str(match).strip()
                    if '@' in email and email not in emails:
                        emails.append(email)

            # 为每个姓名创建联系人
            for name in all_names[:5]:  # 最多5个联系人
                contact = {
                    'name': name,
                    'role': '联系人',
                    'phones': phones,
                    'emails': emails,
                }
                contacts.append(contact)

        return contacts

    def extract_contacts_from_text(self, contact_text: str) -> List[Dict[str, Any]]:
        """从联系方式文本中提取联系人信息"""
        contacts = []

        phones = self._extract_phone_numbers(contact_text)

        # 提取邮箱
        emails = []
        for pattern in self.email_patterns:
            matches = re.findall(pattern, contact_text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[1] if len(match) > 1 else match[0]
                email = str(match).strip()
                if '@' in email and email not in emails:
                    emails.append(email)

        # 提取姓名
        # 首先尝试分离姓名和联系方式
        # 使用分隔符分割
        parts = re.split(r'[，,；;、]', contact_text)
        names = []

        for part in parts:
            part = part.strip()
            # 移除电话号码部分
            part = re.sub(r'\d{3,4}[-\s]?\d{7,8}|1[3-9]\d{9}', '', part)
            # 移除邮箱部分
            part = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', part)
            # 清理
            part = re.sub(r'[^\u4e00-\u9fff]', '', part)

            # 检查是否是有效姓名
            if self.is_valid_name(part) and part not in names:
                names.append(part)

        # 为每个姓名创建联系人
        for name in names[:5]:  # 最多5个联系人
            contact = {
                'name': name,
                'role': '联系人',
                'phones': phones,
                'emails': emails,
            }
            contacts.append(contact)

        # 如果没有找到姓名但有联系方式，创建匿名联系人
        if not contacts and (phones or emails):
            contact = {
                'name': '',
                'role': '联系人',
                'phones': phones,
                'emails': emails,
            }
            contacts.append(contact)

        return contacts

    def extract_structured_contacts(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """提取结构化联系人信息"""
        content = item.get('detail_content') or item.get('content') or ''
        title = item.get('title', '')

        if not content:
            return {
                'procurement_title': title,
                'organizations': {
                    'purchaser': {'name': '', 'address': '', 'contacts': []},
                    'agent': {'name': '', 'address': '', 'contacts': []},
                },
                'project_contacts': []
            }

        # 提取完整标题
        procurement_title = self.extract_procurement_title(content, title)

        # 初始化结果结构
        result = {
            'procurement_title': procurement_title,
            'organizations': {
                'purchaser': {'name': '', 'address': '', 'contacts': []},
                'agent': {'name': '', 'address': '', 'contacts': []},
            },
            'project_contacts': []
        }

        # 提取各个段落
        for pattern, org_type in self.organization_section_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                if org_type.endswith('_direct'):
                    # 直接提取格式
                    if org_type == 'purchaser_direct':
                        name = match.group(1).strip()
                        address = match.group(2).strip()
                        contact_info = match.group(3).strip()

                        org_info = {
                            'name': name,
                            'address': address,
                            'contacts': []
                        }

                        # 从联系方式中提取联系人
                        contacts = self.extract_contacts_from_text(contact_info)
                        org_info['contacts'] = contacts

                        result['organizations']['purchaser'] = org_info

                    elif org_type == 'agent_direct':
                        name = match.group(1).strip()
                        address = match.group(2).strip()
                        contact_info = match.group(3).strip()

                        org_info = {
                            'name': name,
                            'address': address,
                            'contacts': []
                        }

                        # 从联系方式中提取联系人
                        contacts = self.extract_contacts_from_text(contact_info)
                        org_info['contacts'] = contacts

                        result['organizations']['agent'] = org_info

                    elif org_type == 'purchaser_simple':
                        name = match.group(1).strip()
                        address = match.group(2).strip()
                        contact_info = match.group(3).strip()

                        org_info = {
                            'name': name,
                            'address': address,
                            'contacts': []
                        }

                        # 从联系方式中提取联系人
                        contacts = self.extract_contacts_from_text(contact_info)
                        org_info['contacts'] = contacts

                        result['organizations']['purchaser'] = org_info

                    elif org_type == 'agent_simple':
                        name = match.group(1).strip()
                        address = match.group(2).strip()
                        contact_info = match.group(3).strip()

                        org_info = {
                            'name': name,
                            'address': address,
                            'contacts': []
                        }

                        # 从联系方式中提取联系人
                        contacts = self.extract_contacts_from_text(contact_info)
                        org_info['contacts'] = contacts

                        result['organizations']['agent'] = org_info

                else:
                    # 标准段落格式
                    section_text = match.group(1).strip()

                    if org_type in ['purchaser', 'agent']:
                        # 提取机构信息
                        org_info = self.extract_organization_info(section_text, org_type)

                        # 提取联系人
                        contacts = self.extract_contacts_from_section(section_text, org_info)
                        org_info['contacts'] = contacts

                        result['organizations'][org_type] = org_info

                    elif org_type == 'project_contacts':
                        # 项目联系方式可能是独立的，也可能属于代理机构
                        contacts = self.extract_contacts_from_section(section_text, {})
                        result['project_contacts'] = contacts

        # 如果没有找到结构化的信息，尝试简单提取
        if not any([result['organizations']['purchaser']['contacts'],
                   result['organizations']['agent']['contacts'],
                   result['project_contacts']]):

            # 尝试从整个内容中提取
            all_contacts = self.extract_contacts_from_section(content, {})

            # 尝试推断组织归属
            if all_contacts:
                # 查找采购单位
                purchaser_match = re.search(r'采购单位[：:\s]*([^\n,，。；;]+)', content)
                if purchaser_match:
                    purchaser_name = purchaser_match.group(1).strip()
                    result['organizations']['purchaser']['name'] = purchaser_name
                    # 将第一个联系人分配给采购单位
                    if all_contacts:
                        result['organizations']['purchaser']['contacts'] = [all_contacts[0]]

                # 查找代理机构
                agent_match = re.search(r'代理机构[：:\s]*([^\n,，。；;]+)', content)
                if agent_match and len(all_contacts) > 1:
                    agent_name = agent_match.group(1).strip()
                    result['organizations']['agent']['name'] = agent_name
                    # 将剩余联系人分配给代理机构
                    result['organizations']['agent']['contacts'] = all_contacts[1:]

        # 如果项目联系方式不为空，且代理机构联系人为空，将项目联系人归入代理机构
        if result['project_contacts'] and not result['organizations']['agent']['contacts']:
            result['organizations']['agent']['contacts'] = result['project_contacts']

        return result

    def process_scraped_data(self, scraped_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理爬取的数据"""
        self.logger.info(f"开始处理 {len(scraped_items)} 条采购记录")

        processed_data = []
        for item in scraped_items:
            structured = self.extract_structured_contacts(item)

            # 添加基本信息
            structured['id'] = item.get('id', '')
            structured['source_url'] = item.get('link', '')
            structured['scraped_at'] = item.get('scraped_at', '')
            structured['source'] = item.get('source', '')

            processed_data.append(structured)

        self.logger.info(f"成功处理 {len(processed_data)} 条记录")
        return processed_data

    def export_to_json(self, data: List[Dict[str, Any]], filename: str = None) -> str:
        """导出为JSON文件"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"structured_contacts_{timestamp}.json"

        export_path = Path("data") / "exports" / "structured" / filename
        export_path.parent.mkdir(parents=True, exist_ok=True)

        export_data = {
            'export_info': {
                'export_time': datetime.now().isoformat(),
                'total_records': len(data),
                'description': '结构化联系人数据 - 按采购人和代理机构分组'
            },
            'data': data
        }

        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"导出完成: {export_path}")
        return str(export_path)


def main():
    """测试函数"""
    logging.basicConfig(level=logging.INFO)

    # 从数据库加载测试数据
    db_path = Path("data/marketing.db")
    if not db_path.exists():
        print("数据库文件不存在")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 获取几条测试数据
    cursor.execute("""
        SELECT id, title, detail_content
        FROM scraped_data
        WHERE detail_content IS NOT NULL
        LIMIT 5
    """)

    items = []
    for row in cursor.fetchall():
        items.append({
            'id': row[0],
            'title': row[1],
            'detail_content': row[2]
        })

    conn.close()

    if not items:
        print("没有找到测试数据")
        return

    # 创建提取器并测试
    extractor = StructuredContactExtractor()

    for i, item in enumerate(items):
        print(f"\n=== 测试数据 {i+1} ===")
        print(f"标题: {item['title'][:50]}...")

        result = extractor.extract_structured_contacts(item)

        print(f"\n提取的完整标题: {result['procurement_title']}")

        # 显示采购人信息
        purchaser = result['organizations']['purchaser']
        if purchaser['name'] or purchaser['contacts']:
            print(f"\n采购人: {purchaser['name']}")
            if purchaser['address']:
                print(f"地址: {purchaser['address']}")
            for contact in purchaser['contacts']:
                print(f"  联系人: {contact['name']}")
                if contact['phones']:
                    print(f"    电话: {', '.join(contact['phones'])}")
                if contact['emails']:
                    print(f"    邮箱: {', '.join(contact['emails'])})")

        # 显示代理机构信息
        agent = result['organizations']['agent']
        if agent['name'] or agent['contacts']:
            print(f"\n代理机构: {agent['name']}")
            if agent['address']:
                print(f"地址: {agent['address']}")
            for contact in agent['contacts']:
                print(f"  联系人: {contact['name']}")
                if contact['phones']:
                    print(f"    电话: {', '.join(contact['phones'])}")
                if contact['emails']:
                    print(f"    邮箱: {', '.join(contact['emails'])})")

        print("\n" + "="*60)


if __name__ == "__main__":
    main()
