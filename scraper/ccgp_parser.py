"""
政府采购网公告解析器
专门针对政府采购网公告页面的智能解析
"""
import logging
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

from .table_parser import SmartTableParser

logger = logging.getLogger(__name__)


class CCGPAnnouncementParser:
    """政府采购网公告解析器"""

    def __init__(self):
        """初始化解析器"""
        # 段落识别模式
        self.section_patterns = {
            'project_info': r'(项目编号|项目名称|采购项目名称)',
            'bid_info': r'(中标(成交)?信息|中标人|供应商名称)',
            'main_content': r'(主要标的信息|货物名称|服务名称|工程名称)',
            'experts': r'(评审专家|单一来源采购人员)',
            'agency_fee': r'(代理服务费|收费标准)',
            'announcement_period': r'(公告期限)',
            'supplement': r'(其它补充事宜|其他补充事宜)',
            'contact': r'(凡对本次公告|询问|联系)',
            'buyer': r'(采购人信息|采购单位)',
            'agent': r'(采购代理机构|代理机构)',
        }

    def parse(self, html: str, url: str) -> Dict:
        """
        解析政府采购公告页面

        Args:
            html: 页面HTML内容
            url: 页面URL

        Returns:
            解析结果字典
        """
        if not html:
            return {}

        soup = BeautifulSoup(html, 'lxml')

        result = {
            'url': url,
            '_html': html,  # 供 format_for_storage 提取全文使用（避免 BeautifulSoup 无法 JSON 序列化）
            'meta': self._parse_meta(soup),
            'summary_table': self._parse_summary_table(soup),
            'content_sections': self._parse_content_sections(soup),
            'contacts': self._extract_all_contacts(soup),
        }

        logger.info(f"解析完成: {result['meta'].get('title', '')[:30]}")
        return result

    def _parse_meta(self, soup: BeautifulSoup) -> Dict:
        """解析页面元数据"""
        meta = {}

        # 1. 从meta标签提取
        meta['title'] = soup.find('meta', {'name': 'ArticleTitle'})
        if meta['title']:
            meta['title'] = meta['title']['content']

        pub_date = soup.find('meta', {'name': 'PubDate'})
        if pub_date:
            meta['publish_date'] = pub_date['content']

        # 2. 如果meta没有，从页面内容提取
        if not meta.get('title'):
            title_elem = soup.find('h2', class_='tc')
            if title_elem:
                meta['title'] = title_elem.get_text(strip=True)

        if not meta.get('publish_date'):
            pub_time = soup.find('span', id='pubTime')
            if pub_time:
                meta['publish_date'] = pub_time.get_text(strip=True)

        return meta

    def _parse_summary_table(self, soup: BeautifulSoup) -> Dict:
        """
        解析概要表格

        这个表格通常包含结构化的关键信息
        使用智能表格解析器，正确处理colspan和rowspan
        """
        # 查找概要表格
        table_div = soup.find('div', class_='table')
        if not table_div:
            return {}

        table = table_div.find('table')
        if not table:
            return {}

        # 使用智能表格解析器
        table_parser = SmartTableParser()
        parsed = table_parser.parse_table(table)

        # 返回结构化数据
        return parsed['structured']

    def _parse_content_sections(self, soup: BeautifulSoup) -> Dict:
        """
        解析详细内容的各个段落

        按照标准的中标公告结构解析
        """
        sections = {
            'project_no': '',
            'project_name': '',
            'bid_info': {},
            'main_content': '',
            'experts': [],
            'agency_fee': '',
            'announcement_period': '',
            'supplement': '',
            'contacts': {},
        }

        # 查找详细内容容器
        content_div = soup.find('div', class_='vF_detail_content')
        if not content_div:
            return sections

        # 获取所有段落
        paragraphs = content_div.find_all(['p', 'strong'])
        current_section = None

        for p in paragraphs:
            text = p.get_text(strip=True)

            # 识别段落类型
            if '项目编号' in text and 'TC' in text:
                sections['project_no'] = text.split('：')[-1].split(':')[-1].strip()
            elif '项目名称' in text and '项目编号' not in text:
                sections['project_name'] = text.split('：')[-1].split(':')[-1].strip()
            elif '中标（成交）信息' in text:
                current_section = 'bid_info'
            elif '主要标的信息' in text:
                current_section = 'main_content'
            elif '评审专家' in text:
                current_section = 'experts'
            elif '代理服务费' in text:
                current_section = 'agency_fee'
            elif '公告期限' in text:
                current_section = 'announcement_period'
            elif '其它补充事宜' in text or '其他补充事宜' in text:
                current_section = 'supplement'
            elif '凡对本次公告' in text:
                current_section = 'contacts'
            elif current_section:
                # 累积内容到当前段落
                if current_section == 'bid_info':
                    if '供应商名称' in text:
                        sections['bid_info']['supplier'] = text.split('：')[-1].split(':')[-1].strip()
                    elif '供应商地址' in text:
                        sections['bid_info']['supplier_address'] = text.split('：')[-1].split(':')[-1].strip()
                    elif '中标金额' in text or '成交金额' in text:
                        sections['bid_info']['amount'] = text.split('：')[-1].split(':')[-1].strip()
                elif current_section == 'experts':
                    experts = [e.strip() for e in text.split('、') if e.strip()]
                    sections['experts'].extend(experts)
                elif current_section == 'agency_fee':
                    sections['agency_fee'] += text + '\n'
                elif current_section == 'announcement_period':
                    sections['announcement_period'] = text
                elif current_section == 'supplement':
                    sections['supplement'] += text + '\n'
                elif current_section == 'contacts':
                    sections['contacts']['raw'] = text

        return sections

    def _extract_all_contacts(self, soup: BeautifulSoup) -> Dict:
        """
        提取所有联系人信息

        从多个来源综合提取
        """
        contacts = {
            'buyer': {},      # 采购人
            'agent': {},      # 代理机构
            'supplier': {},   # 供应商
            'project': {},    # 项目联系人
        }

        # 1. 从概要表格提取
        table_div = soup.find('div', class_='table')
        if table_div:
            contacts.update(self._extract_contacts_from_table(table_div))

        # 2. 从详细内容提取
        content_div = soup.find('div', class_='vF_detail_content')
        if content_div:
            contacts.update(self._extract_contacts_from_content(content_div))

        return contacts

    def _extract_contacts_from_table(self, table_div) -> Dict:
        """从概要表格提取联系人"""
        contacts = {
            'buyer': {},
            'agent': {},
            'project': {},
        }

        table = table_div.find('table')
        if not table:
            return contacts

        current_type = None

        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if not cells:
                continue

            key = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True) if len(cells) > 1 else ''

            # 识别联系人类型
            if '采购单位' in key and '地址' not in key and '联系方式' not in key:
                current_type = 'buyer'
                contacts['buyer'] = {'name': value}
            elif '采购单位地址' in key:
                contacts['buyer']['address'] = value
            elif '采购单位联系方式' in key:
                name, phone = self._parse_contact_info(value)
                contacts['buyer']['contact_name'] = name
                contacts['buyer']['phone'] = phone
            elif '代理机构名称' in key:
                current_type = 'agent'
                contacts['agent'] = {'name': value}
            elif '代理机构地址' in key:
                contacts['agent']['address'] = value
            elif '代理机构联系方式' in key:
                name, phone = self._parse_contact_info(value)
                contacts['agent']['contact_name'] = name
                contacts['agent']['phone'] = phone
            elif '项目联系人' in key:
                contacts['project']['names'] = [n.strip() for n in value.split('、')]
            elif '项目联系电话' in key:
                contacts['project']['phone'] = value

        return contacts

    def _extract_contacts_from_content(self, content_div) -> Dict:
        """从详细内容提取联系人"""
        contacts = {
            'buyer': {},
            'agent': {},
            'project': {},
        }

        # 查找联系方式段落
        paragraphs = content_div.find_all('p')
        in_contact_section = False
        current_type = None

        for p in paragraphs:
            text = p.get_text(strip=True)

            if '凡对本次公告' in text:
                in_contact_section = True
                continue

            if not in_contact_section:
                continue

            # 采购人信息
            if '采购人信息' in text or '1.采购人' in text:
                current_type = 'buyer'
                contacts['buyer'] = contacts.get('buyer', {})
            # 代理机构信息
            elif '代理机构' in text or '2.采购代理机构' in text:
                current_type = 'agent'
                contacts['agent'] = contacts.get('agent', {})
            # 项目联系方式
            elif '项目联系方式' in text or '3.项目' in text:
                current_type = 'project'
                contacts['project'] = contacts.get('project', {})

            # 解析具体信息
            elif current_type == 'buyer':
                if '名 称' in text or '名称' in text:
                    contacts['buyer']['name'] = text.split('：')[-1].split(':')[-1].strip()
                elif '地址' in text:
                    contacts['buyer']['address'] = text.split('：')[-1].split(':')[-1].strip()
                elif '联系方式' in text:
                    name, phone = self._parse_contact_info(text.split('：')[-1].split(':')[-1])
                    contacts['buyer']['contact_name'] = name
                    contacts['buyer']['phone'] = phone

            elif current_type == 'agent':
                if '名 称' in text or '名称' in text:
                    contacts['agent']['name'] = text.split('：')[-1].split(':')[-1].strip()
                elif '地址' in text:
                    contacts['agent']['address'] = text.split('：')[-1].split(':')[-1].strip()
                elif '联系方式' in text:
                    name, phone = self._parse_contact_info(text.split('：')[-1].split(':')[-1])
                    contacts['agent']['contact_name'] = name
                    contacts['agent']['phone'] = phone

            elif current_type == 'project':
                if '项目联系人' in text:
                    contacts['project']['names'] = [n.strip() for n in text.split('：')[-1].split(':')[-1].split('、')]
                elif '电 话' in text or '电话' in text:
                    contacts['project']['phone'] = text.split('：')[-1].split(':')[-1].strip()

        return contacts

    def _parse_contact_info(self, text: str) -> tuple:
        """
        解析联系人信息

        Returns:
            (联系人姓名, 电话号码)
        """
        # 查找电话号码
        phone_patterns = [
            r'1[3-9]\d{9}',
            r'0\d{2,3}-?\d{7,8}',
            r'\d{3,4}-\d{7,8}',
        ]

        phone = None
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group(0)
                break

        # 提取姓名（去除电话后的部分）
        name = text
        if phone:
            name = text.replace(phone, '').strip()
            # 去除标点
            name = re.sub(r'[、，,]', '', name)

        return name, phone

    def _parse_amount(self, text: str) -> Dict:
        """
        解析金额信息

        Returns:
            {'amount': 数值, 'unit': 单位, 'original': 原始文本}
        """
        # 提取数字
        numbers = re.findall(r'[\d,]+\.?\d*', text)

        if numbers:
            amount = numbers[0].replace(',', '')
            try:
                amount = float(amount)
            except:
                amount = 0

            # 识别单位
            unit = ''
            if '万元' in text:
                unit = '万元'
            elif '元' in text:
                unit = '元'

            return {
                'amount': amount,
                'unit': unit,
                'original': text
            }

        return {'original': text}

    def format_for_storage(self, parsed_data: Dict) -> Dict:
        """
        将解析数据格式化为存储格式

        Returns:
            适合存储到数据库的字典
        """
        summary = parsed_data.get('summary_table', {})
        contacts = parsed_data.get('contacts', {})
        content = parsed_data.get('content_sections', {})

        # 项目信息 - 优先从summary_table获取，如果没有则从content_sections
        project_info = summary.get('project_info', {})
        buyer_info = summary.get('buyer', {})
        agent_info = summary.get('agent', {})
        supplier_info_table = summary.get('supplier', {})
        contacts_info = summary.get('contacts', {})

        # 中标信息 - 优先从详细内容获取（表格通常没有）
        bid_info = content.get('bid_info', {})

        # 基本信息
        formatted = {
            'title': parsed_data['meta'].get('title', ''),
            'url': parsed_data.get('url', ''),
            'publish_date': parsed_data['meta'].get('publish_date', ''),
            'source': '中国政府采购网',

            # 项目信息
            'project_no': content.get('project_no', ''),
            'project_name': project_info.get('name') or content.get('project_name', ''),
            'category': project_info.get('category', ''),
            'region': project_info.get('region', ''),

            # ========== 中标人信息（重要） ==========
            'supplier': bid_info.get('supplier') or supplier_info_table.get('name', ''),
            'supplier_address': bid_info.get('supplier_address') or supplier_info_table.get('address', ''),
            'bid_amount': self._format_amount(bid_info.get('amount') or summary.get('amount', {})),

            # 采购人信息
            'buyer_name': buyer_info.get('name') or contacts.get('buyer', {}).get('name', ''),
            'buyer_address': buyer_info.get('address') or contacts.get('buyer', {}).get('address', ''),
            'buyer_contact': buyer_info.get('contact') or contacts.get('buyer', {}).get('contact_name', ''),
            'buyer_phone': self._extract_phone(buyer_info.get('contact') or contacts.get('buyer', {}).get('phone', '')),

            # 代理机构信息
            'agent_name': agent_info.get('name') or contacts.get('agent', {}).get('name', ''),
            'agent_address': agent_info.get('address') or contacts.get('agent', {}).get('address', ''),
            'agent_contact': agent_info.get('contact') or contacts.get('agent', {}).get('contact_name', ''),
            'agent_phone': self._extract_phone(agent_info.get('contact') or contacts.get('agent', {}).get('phone', '')),

            # 项目联系人
            'project_contacts': self._parse_contact_names(contacts_info.get('name') or contacts.get('project', {}).get('names', [])),
            'project_phone': contacts_info.get('phone') or contacts.get('project', {}).get('phone', ''),

            # 专家
            'experts': project_info.get('experts') or summary.get('experts', '') or ', '.join(content.get('experts', [])),

            # 完整内容
            'content': self._extract_full_text(parsed_data),
        }

        return formatted

    def _format_amount(self, amount_data: any) -> str:
        """格式化金额信息"""
        if isinstance(amount_data, dict):
            if amount_data.get('original'):
                return amount_data['original']
            elif amount_data.get('amount'):
                return f"￥{amount_data['amount']} {amount_data.get('unit', '元')}"
        return str(amount_data) if amount_data else ''

    def _extract_phone(self, text: str) -> str:
        """从文本中提取电话号码"""
        if not text:
            return ''
        # 查找电话号码
        phone_patterns = [
            r'1[3-9]\d{9}',
            r'0\d{2,3}-?\d{7,8}',
        ]
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return ''

    def _parse_contact_names(self, names: any) -> List[str]:
        """解析联系人姓名列表"""
        if isinstance(names, list):
            return names
        if isinstance(names, str):
            return [n.strip() for n in names.split('、') if n.strip()]
        return []

    def _extract_full_text(self, parsed_data: Dict) -> str:
        """提取完整文本内容"""
        html = parsed_data.get('_html') or ""
        if not html:
            return ""

        soup = BeautifulSoup(html, "lxml")
        content_div = soup.find("div", class_="vF_detail_content")
        if content_div:
            return content_div.get_text(separator='\n', strip=True)

        return ""
