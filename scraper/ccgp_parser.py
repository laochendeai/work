"""
公共资源交易网公告解析器
专门针对公共资源交易网公告页面的智能解析
"""
import logging
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

from .table_parser import SmartTableParser

logger = logging.getLogger(__name__)


class CCGPAnnouncementParser:
    """公共资源交易网公告解析器"""

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
        解析公共资源交易公告页面

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
        }

        # 预先解析内容段落，以便获取专家名单
        content_sections = self._parse_content_sections(soup)
        result['content_sections'] = content_sections

        # 提取联系人
        contacts = self._extract_all_contacts(soup)
        
        # 过滤评审专家（避免误将专家识别为联系人）
        experts_list = content_sections.get('experts', [])
        if experts_list:
            self._filter_experts(contacts, experts_list)
        
        result['contacts'] = contacts

        # 调试日志：检查是否提取到了采购人电话
        if contacts.get('buyer', {}).get('phone'):
            logger.debug(f"提取到采购人电话: {contacts['buyer']['phone']}")
        else:
            logger.debug("未提取到采购人电话")

        logger.info(f"解析完成: {result['meta'].get('title', '')[:30]}")
        return result

    def _filter_experts(self, contacts: Dict, experts: List[str]):
        """从联系人中移除评审专家"""
        expert_set = set(experts)
        
        # 检查并清理各角色的联系人
        for role in ['agent', 'buyer', 'project']:
            if role not in contacts: continue
            
            # 检查主要联系人
            name = contacts[role].get('contact_name')
            if name and name in expert_set:
                logger.warning(f"移除误识别为联系人的专家: {name} (role={role})")
                contacts[role]['contact_name'] = ''
            
            # 检查联系人列表
            if 'contacts_list' in contacts[role]:
                new_list = []
                for c in contacts[role]['contacts_list']:
                    if c.get('name') in expert_set:
                        logger.warning(f"移除误识别为联系人的专家(列表): {c.get('name')} (role={role})")
                        continue
                    new_list.append(c)
                contacts[role]['contacts_list'] = new_list


    def _parse_meta(self, soup: BeautifulSoup) -> Dict:
        """解析页面元数据"""
        meta = {}

        # 1. 从meta标签提取
        title_meta = soup.find('meta', {'name': 'ArticleTitle'})
        if title_meta:
            meta['title'] = title_meta['content']

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
                name, phone, email = self._parse_contact_info(value)
                contacts['buyer']['contact_name'] = name
                contacts['buyer']['phone'] = phone
                contacts['buyer']['email'] = email
            elif '代理机构名称' in key:
                current_type = 'agent'
                contacts['agent'] = {'name': value}
            elif '代理机构地址' in key:
                contacts['agent']['address'] = value
            elif '代理机构联系方式' in key or '代理机构联系人' in key:
                # 支持多人格式: "黄丹彤16620120513、崔世杰15800204406"
                raw_parts = [p.strip() for p in re.split(r'[、，,]', value) if p.strip()]
                agent_contacts = []
                first_phone = ''
                first_name = ''
                for part in raw_parts:
                    name, phone, email = self._parse_contact_info(part)
                    if name or phone:
                        agent_contacts.append({'name': name, 'phone': phone, 'email': email})
                        if not first_phone and phone:
                            first_phone = phone
                        if not first_name and name:
                            first_name = name
                
                # 保存详情列表（供后续提取多个联系人）
                contacts['agent']['contacts_list'] = agent_contacts
                # 保持向后兼容：第一个联系人
                contacts['agent']['contact_name'] = first_name
                contacts['agent']['phone'] = first_phone
                if agent_contacts and agent_contacts[0].get('email'):
                    contacts['agent']['email'] = agent_contacts[0]['email']
            elif '项目联系人' in key:
                raw_names = [n.strip() for n in value.split('、')]
                details = []
                for raw in raw_names:
                    name, phone, _ = self._parse_contact_info(raw)
                    if name:
                        details.append({'name': name, 'phone': phone})
                contacts['project']['details'] = details
                contacts['project']['names'] = [d['name'] for d in details]
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

            # 头部检测（自动开启联系人区域）
            # 采购人信息
            if '采购人信息' in text or '1.采购人' in text:
                in_contact_section = True
                current_type = 'buyer'
                contacts['buyer'] = contacts.get('buyer', {})
            # 代理机构信息
            elif '代理机构' in text or '2.采购代理机构' in text:
                in_contact_section = True
                current_type = 'agent'
                contacts['agent'] = contacts.get('agent', {})
            # 项目联系方式
            elif '项目联系方式' in text or '3.项目' in text:
                in_contact_section = True
                current_type = 'project'
                contacts['project'] = contacts.get('project', {})

            if not in_contact_section:
                continue

            # 解析具体信息
            elif current_type == 'buyer':
                if '名 称' in text or '名称' in text:
                    contacts['buyer']['name'] = text.split('：')[-1].split(':')[-1].strip()
                elif '地址' in text:
                    contacts['buyer']['address'] = text.split('：')[-1].split(':')[-1].strip()
                elif '电 话' in text or '电话' in text:
                    phone = self._extract_phone(text)
                    if phone:
                        contacts['buyer']['phone'] = phone
                elif '联系方式' in text:
                    raw_value = text.split('：')[-1].split(':')[-1].strip()
                    # 如果联系方式只是一个电话号码，直接使用
                    phone = self._extract_phone(raw_value)
                    if phone:
                        contacts['buyer']['phone'] = phone
                        # 去掉电话后剩下的可能是联系人姓名
                        name_part = raw_value.replace(phone, '').strip()
                        name_part = re.sub(r'[、，,：:]', '', name_part).strip()
                        if name_part:
                            contacts['buyer']['contact_name'] = name_part
                    else:
                        # 没有电话，可能是联系人姓名
                        name, phone, email = self._parse_contact_info(raw_value)
                        contacts['buyer']['contact_name'] = name
                        contacts['buyer']['phone'] = phone
                        contacts['buyer']['email'] = email

            elif current_type == 'agent':
                if '名 称' in text or '名称' in text:
                    contacts['agent']['name'] = text.split('：')[-1].split(':')[-1].strip()
                elif '地址' in text:
                    contacts['agent']['address'] = text.split('：')[-1].split(':')[-1].strip()
                elif '电 话' in text or '电话' in text:
                    phone_list = self._extract_extended_phones(text)
                    if phone_list:
                        # 格式化为逗号分隔字符串以保持兼容
                        combined_phone = ", ".join(phone_list)
                        contacts['agent']['phone'] = combined_phone
                        
                        # 回填
                        if contacts['agent'].get('contacts_list'):
                            for c in contacts['agent']['contacts_list']:
                                if not c.get('phone'):
                                    c['phone'] = combined_phone

                elif '联系方式' in text or '联系人' in text:
                    raw_value = text.split('：')[-1].split(':')[-1].strip()
                    logger.info(f"DEBUG_AGENT_RAW: {raw_value}")
                    
                    # 1. 提取所有电话（含扩展逻辑）
                    all_phones = self._extract_extended_phones(raw_value)
                    
                    # 2. 提取所有姓名（移除电话后分割）
                    # 临时移除电话号码以便提取姓名
                    temp_text = raw_value
                    for p in all_phones:
                        # 简单移除（注意避免部分匹配误删，这里简化处理）
                        # 更严谨的做法是按位置移除，但这里假设电话都在后面或中间
                        pass 
                    
                    # 使用正则移除类似电话的数字串
                    text_no_phone = re.sub(r'0\d{2,3}-?\d{7,8}', '', raw_value)
                    text_no_phone = re.sub(r'\d{7,13}', '', text_no_phone) # 移除长数字
                    
                    # 分割姓名
                    raw_names = [n.strip() for n in re.split(r'[、，,;\s\\]', text_no_phone) if n.strip()]
                    # 过滤掉非名字（如纯符号）
                    clean_names = []
                    for n in raw_names:
                        n = re.sub(r'[^\u4e00-\u9fa5a-zA-Z]', '', n) # 仅保留汉字和字母
                        if len(n) >= 2: # 名字通常至少2个字
                            clean_names.append(n)
                            
                    # 3. 关联逻辑：全量关联（Pooling）
                    combined_phone = ", ".join(all_phones)
                    agent_contacts = []
                    
                    # 如果有名字
                    if clean_names:
                        for name in clean_names:
                            agent_contacts.append({
                                'name': name,
                                'phone': combined_phone,
                                'email': '' # 暂不支持复杂邮箱匹配
                            })
                    # 如果没名字但有电话（可能是只有一张公司名片？）
                    elif all_phones:
                        # 尝试找前面可能的单一名
                        pass
                        
                    # 更新结果
                    contacts['agent']['contacts_list'] = agent_contacts
                    if agent_contacts:
                        contacts['agent']['contact_name'] = agent_contacts[0]['name']
                        contacts['agent']['phone'] = agent_contacts[0]['phone']
                    elif all_phones: # 只有电话
                         contacts['agent']['phone'] = combined_phone

            elif current_type == 'project':
                if '项目联系人' in text:
                    raw_names = [n.strip() for n in text.split('：')[-1].split(':')[-1].split('、')]
                    details = []
                    for raw in raw_names:
                        name, phone, _ = self._parse_contact_info(raw)
                        if name:
                            details.append({'name': name, 'phone': phone})
                    contacts['project']['details'] = details
                    # Keep legacy format for fallback
                    contacts['project']['names'] = [d['name'] for d in details]
                elif '电 话' in text or '电话' in text:
                    contacts['project']['phone'] = text.split('：')[-1].split(':')[-1].strip()

        return contacts

    def _parse_contact_info(self, text: str) -> tuple:
        """
        解析联系人信息

        Returns:
            (联系人姓名, 电话号码, 邮箱)
        """
        # 查找电话号码
        phone_patterns = [
            r'1[3-9]\d{9}',
            r'0\d{2,3}-?\d{7,8}',
            r'\d{3,4}-\d{7,8}',
        ]

        phone = ''
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group(0)
                break

        # 查找邮箱
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email = ''
        match_email = re.search(email_pattern, text)
        if match_email:
            email = match_email.group(0)

        # 提取姓名（去除电话及邮箱后的部分）
        name = text
        if phone:
            name = name.replace(phone, '')
        if email:
            name = name.replace(email, '')
            
        name = name.strip()
        # 去除标点和特殊字符
        name = re.sub(r'[、，,：:]', '', name).strip()

        return name, phone, email

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

    def _extract_extended_phones(self, text: str) -> List[str]:
        """
        增强型电话提取：支持 "010-88888888\8889" 或 "010-88888888、88887777" 等缩写格式
        """
        if not text:
            return []
            
        phones = []
        
        # 1. 提取标准全号码
        # 0xxx-xxxxxxx, 1xxxxxxxxxx
        standard_patterns = [
            r'(0\d{2,3}-?\d{7,8})', # 座机 group 1
            r'(1[3-9]\d{9})'        # 手机 group 2
        ]
        
        # 查找所有全号码的位置和值
        matches = [] # list of (start, end, phone_str, type)
        for p in standard_patterns:
            for m in re.finditer(p, text):
                matches.append((m.start(), m.end(), m.group(), 'std'))
        
        # 排序
        matches.sort(key=lambda x: x[0])
        
        # 如果没有基础号码，直接返回空（无法进行缩写扩展）
        if not matches:
            return []
            
        # 收集结果，并处理缩写
        # 逻辑：对于每个全号码，向后查找紧跟的“缩写后缀”
        
        processed_phones = set()
        
        for i, (start, end, main_phone, _) in enumerate(matches):
            if main_phone not in processed_phones:
                phones.append(main_phone)
                processed_phones.add(main_phone)
            
            # 向后看：查找分隔符 + 短数字
            # 定义搜索范围：从当前电话结束位置开始，到下一个电话开始位置（或字符串末尾）
            next_start = matches[i+1][0] if i+1 < len(matches) else len(text)
            substring = text[end:next_start]
            
            # 在 substring 中查找可能是后缀的数字
            # 模式：分隔符(、, \ / space) + 数字(4-8位)
            # 注意：\ 是特殊字符，需要转义
            suffix_iter = re.finditer(r'[\\/、，,;\s]+(\d{4,8})\b', substring)
            
            for sm in suffix_iter:
                suffix = sm.group(1)
                # 构造扩展号码
                # 规则：如果是座机，替换后N位；如果是手机，也可以替换？
                # 这里主要针对座机 010-81168617 / 8612 -> 010-81168612
                
                if '-' in main_phone:
                    prefix, number = main_phone.split('-', 1)
                    if len(suffix) <= len(number):
                        new_number = number[:-len(suffix)] + suffix
                        full_new = f"{prefix}-{new_number}"
                        if full_new not in processed_phones:
                            phones.append(full_new)
                            processed_phones.add(full_new)
                else:
                    # 手机或无区号座机，直接替换尾部
                    if len(suffix) < len(main_phone):
                        new_phone = main_phone[:-len(suffix)] + suffix
                        if new_phone not in processed_phones:
                            phones.append(new_phone)
                            processed_phones.add(new_phone)
                            
        return phones

    def _extract_phones(self, text: str) -> List[str]:
        """从文本中提取所有电话号码（代理到增强版）"""
        return self._extract_extended_phones(text)

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
            'source': '中国公共资源交易网',

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
            # For buyer_phone: try direct phone first, then extract from contact field
            'buyer_phone': self._format_phones(
                contacts.get('buyer', {}).get('phone', '') or
                self._extract_phones(buyer_info.get('contact', ''))
            ),
            'buyer_email': contacts.get('buyer', {}).get('email', ''),

            # 代理机构信息
            'agent_name': agent_info.get('name') or contacts.get('agent', {}).get('name', ''),
            'agent_address': agent_info.get('address') or contacts.get('agent', {}).get('address', ''),
            'agent_contact': agent_info.get('contact') or contacts.get('agent', {}).get('contact_name', ''),
            # For agent_phone: try direct phone first, then extract from contact field
            'agent_phone': self._format_phones(
                contacts.get('agent', {}).get('phone', '') or
                self._extract_phones(agent_info.get('contact', ''))
            ),
            'agent_email': contacts.get('agent', {}).get('email', ''),
            # 代理机构联系人列表（支持多人）
            'agent_contacts_list': contacts.get('agent', {}).get('contacts_list', []),

            # 项目联系人
            'project_contacts': (
                contacts_info.get('details') or 
                contacts.get('project', {}).get('details') or 
                self._parse_contact_names(contacts_info.get('name') or contacts.get('project', {}).get('names', []))
            ),
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

    def _extract_phones(self, text: str) -> List[str]:
        """从文本中提取所有电话号码"""
        if not text:
            return []
        
        phones = []
        # 查找电话号码
        phone_patterns = [
            r'1[3-9]\d{9}',
            r'0\d{2,3}-?\d{7,8}',
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                if m not in phones:
                    phones.append(m)
        return phones

    def _extract_phone(self, text: str) -> str:
        """从文本中提取电话号码（兼容旧接口，返回第一个）"""
        phones = self._extract_phones(text)
        return phones[0] if phones else ''

    def _format_phones(self, phones: any) -> str:
        """格式化电话列表为字符串"""
        if isinstance(phones, str):
            # 尝试再次提取
            extracted = self._extract_phones(phones)
            return ", ".join(extracted) if extracted else phones
        if isinstance(phones, list):
            return ", ".join(phones)
        return ""

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
