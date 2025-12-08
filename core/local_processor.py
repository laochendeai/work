#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地联系人处理器
使用规则引擎和轻量级NLP进行智能联系人提取，无需调用外部API
"""

import re
import jieba
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class LocalContactInfo:
    """本地提取的联系人信息"""
    name: str = ""
    company: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    department: str = ""
    position: str = ""
    confidence: float = 0.0
    source: str = "local_extraction"

class LocalContactProcessor:
    """本地智能联系人处理器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_patterns()
        self._setup_dictionaries()

    def _setup_patterns(self):
        """设置提取模式"""
        # 职位关键词
        self.position_keywords = {
            '老师', '教授', '主任', '经理', '主管', '专员', '工程师', '设计师', '张老师', '李老师', '王老师',
            '联系人', '负责人', '项目经理', '采购人', '招标人', '代理人', '经办人', '销售经理'
        }

        # 公司类型后缀
        self.company_suffixes = {
            '公司', '集团', '企业', '单位', '学校', '大学', '学院', '研究院', '有限公司',
            '有限责任公司', '股份公司', '工程有限公司', '技术有限公司', '贸易公司', '科技'
        }

        # 部门关键词
        self.department_keywords = {
            '采购部', '招标办', '财务部', '项目部', '技术部', '设备科', '后勤部', '行政部'
        }

        # 电话模式优化
        self.phone_patterns = [
            r'1[3-9]\d{9}',  # 手机号
            r'0\d{2,3}-?\d{7,8}',  # 座机（带0开头）
            r'\d{3,4}-\d{7,8}',  # 座机
            r'400-\d{7}',  # 400电话
            r'800-\d{7}',  # 800电话
        ]

        # 邮箱模式
        self.email_patterns = [
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        ]

        # 联系方式上下文模式
        self.contact_context_patterns = [
            r'联系人[：:\s]*([^\s,，。]+)',
            r'负责人[：:\s]*([^\s,，。]+)',
            r'项目经理[：:\s]*([^\s,，。]+)',
            r'采购人[：:\s]*([^\s,，。]+)',
            r'经办人[：:\s]*([^\s,，。]+)',
            r'电话[：:\s]*(\d{3,4}-?\d{7,8}|1[3-9]\d{9})',
            r'手机[：:\s]*(1[3-9]\d{9})',
            r'联系方式[：:\s]*([^\s]*?(\d{3,4}-?\d{7,8}|1[3-9]\d{9})[^\s]*)',
        ]

    def _setup_dictionaries(self):
        """设置词汇字典"""
        # 常见姓氏（用于提高姓名识别准确率）
        self.common_surnames = {
            '王', '李', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴',
            '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗'
        }

    def process_text_batch(self, texts: List[str]) -> List[LocalContactInfo]:
        """批量处理文本"""
        results = []
        for text in texts:
            contacts = self.extract_contacts_from_text(text)
            results.extend(contacts)
        return results

    def extract_contacts_from_text(self, text: str) -> List[LocalContactInfo]:
        """从单个文本中提取联系人信息"""
        if not text or len(text.strip()) < 10:
            return []

        # 清理文本
        cleaned_text = self._clean_text(text)

        # 提取基础信息
        phones = self._extract_phones(cleaned_text)
        emails = self._extract_emails(cleaned_text)

        # 智能提取结构化信息
        structured_contacts = self._extract_structured_contacts(cleaned_text)

        # 如果没有结构化联系人，尝试模式提取
        if not structured_contacts:
            structured_contacts = self._extract_by_patterns(cleaned_text, phones, emails)

        return structured_contacts

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        # 统一标点符号
        text = text.replace('：', ':').replace('，', ',').replace('。', '.')
        # 移除特殊字符但保留中文标点
        text = re.sub(r'[^\u4e00-\u9fa5\w\s:,.()（）\-\/]', ' ', text)
        return text.strip()

    def _extract_phones(self, text: str) -> List[str]:
        """提取电话号码"""
        phones = set()

        for pattern in self.phone_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # 标准化电话格式
                if match.startswith('1'):
                    # 手机号
                    if len(match) == 11 and re.match(r'1[3-9]\d{9}', match):
                        phones.add(match)
                elif '-' in match:
                    # 座机
                    parts = match.split('-')
                    if len(parts) == 2 and len(parts[1]) >= 7:
                        phones.add(match)
                else:
                    # 可能的座机，尝试添加分隔符
                    if len(match) == 11 and match.startswith('0'):
                        formatted = f"{match[:3]}-{match[3:]}"
                        phones.add(formatted)
                    elif len(match) == 10:
                        formatted = f"{match[:3]}-{match[3:]}"
                        phones.add(formatted)

        return list(phones)

    def _extract_emails(self, text: str) -> List[str]:
        """提取邮箱"""
        emails = set()

        for pattern in self.email_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if self._is_valid_email(match):
                    emails.add(match.lower())

        return list(emails)

    def _is_valid_email(self, email: str) -> bool:
        """验证邮箱格式"""
        if not email or '@' not in email:
            return False

        # 简单验证
        parts = email.split('@')
        if len(parts) != 2:
            return False

        local, domain = parts
        if not local or not domain:
            return False

        # 检查域名是否有有效后缀
        domain_parts = domain.split('.')
        if len(domain_parts) < 2:
            return False

        return True

    def _extract_structured_contacts(self, text: str) -> List[LocalContactInfo]:
        """提取结构化联系人信息"""
        contacts = []

        # 按段落分割
        paragraphs = text.split('\n')

        for paragraph in paragraphs:
            if len(paragraph.strip()) < 20:
                continue

            contact = self._extract_from_paragraph(paragraph)
            if contact and self._is_valid_contact(contact):
                contacts.append(contact)

        # 去重
        contacts = self._deduplicate_contacts(contacts)

        # 限制每个文档最多返回5个联系人
        return contacts[:5]

    def _extract_from_paragraph(self, paragraph: str) -> Optional[LocalContactInfo]:
        """从段落中提取联系人"""
        contact = LocalContactInfo()

        # 分词
        words = jieba.lcut(paragraph)

        # 提取公司
        contact.company = self._extract_company(words, paragraph)

        # 提取姓名
        contact.name = self._extract_name(words, paragraph)

        # 提取电话
        phones = self._extract_phones(paragraph)
        if phones:
            contact.phone = phones[0]  # 取第一个电话

        # 提取邮箱
        emails = self._extract_emails(paragraph)
        if emails:
            contact.email = emails[0]  # 取第一个邮箱

        # 提取地址
        contact.address = self._extract_address(paragraph)

        # 计算置信度
        contact.confidence = self._calculate_confidence(contact)

        return contact if contact.confidence > 0.3 else None

    def _extract_company(self, words: List[str], text: str) -> str:
        """提取公司名称"""
        companies = []

        # 模式匹配
        for i in range(len(words)):
            for j in range(i+1, min(i+8, len(words))):  # 最多8个词的公司名
                company_candidate = ''.join(words[i:j+1])

                # 检查是否包含公司后缀
                if any(suffix in company_candidate for suffix in self.company_suffixes):
                    # 进一步验证合理性
                    if self._is_valid_company_name(company_candidate):
                        companies.append(company_candidate)

        # 选择最可能的公司名
        if companies:
            # 优先选择包含"有限公司"的完整公司名
            for company in companies:
                if '有限公司' in company or '有限责任公司' in company:
                    return company

            # 否则选择最长的
            return max(companies, key=len)

        # 尝试从文本中直接提取
        company_patterns = [
            r'采购单位[：:\s]*([^\s,，。]+)',
            r'代理机构[：:\s]*([^\s,，。]+)',
            r'供应商[：:\s]*([^\s,，。]+)',
            r'中标单位[：:\s]*([^\s,，。]+)',
            r'名称[：:\s]*([^\s,，。]{5,20})',
        ]

        for pattern in company_patterns:
            match = re.search(pattern, text)
            if match:
                company = match.group(1).strip()
                if self._is_valid_company_name(company):
                    return company

        return ""

    def _is_valid_company_name(self, name: str) -> bool:
        """验证公司名称的合理性"""
        # 长度检查
        if len(name) < 3 or len(name) > 50:
            return False

        # 排除明显不是公司的内容
        exclude_words = {
            '地址', '联系方式', '电话', '邮箱', '时间', '日期', '金额', '数量',
            '采购', '招标', '中标', '公告', '项目', '品目', '货物'
        }

        for word in exclude_words:
            if word in name and len(name) < 10:
                return False

        # 必须包含公司相关后缀或足够长
        if any(suffix in name for suffix in self.company_suffixes):
            return True

        # 如果不包含标准后缀，检查是否为知名机构
        known_institutions = {
            '四川大学', '清华大学', '北京大学', '浙江大学', '复旦大学',
            '政府', '医院', '学校', '研究院', '设计院'
        }

        if any(inst in name for inst in known_institutions):
            return True

        return False

    def _extract_name(self, words: List[str], text: str) -> str:
        """提取姓名"""
        names = []

        # 1. 从联系方式上下文提取
        for pattern in self.contact_context_patterns[:5]:  # 只提取姓名相关的模式
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]

                name = match.strip()
                if self._is_valid_name(name):
                    names.append(name)

        # 2. 从词序列中寻找姓名模式
        for i in range(len(words) - 1):
            # 检查是否为"姓+职务"模式
            if words[i] in self.common_surnames:
                name_candidate = words[i]

                # 检查后面是否有职务
                if i + 1 < len(words) and words[i+1] in self.position_keywords:
                    name_candidate += words[i+1]
                    names.append(name_candidate)
                elif len(words[i]) == 2 or len(words[i]) == 3:
                    # 常见中文姓名长度
                    names.append(words[i])

        # 3. 清理和选择最佳姓名
        valid_names = []
        for name in names:
            cleaned_name = self._clean_name(name)
            if cleaned_name and cleaned_name not in valid_names:
                valid_names.append(cleaned_name)

        # 优先选择包含职务的姓名
        for name in valid_names:
            if any(pos in name for pos in self.position_keywords):
                return name

        # 否则返回第一个有效姓名
        return valid_names[0] if valid_names else ""

    def _clean_name(self, name: str) -> str:
        """清理姓名"""
        if not name:
            return ""

        # 移除常见的前缀和后缀
        prefixes = ['联系人', '负责人', '先生', '女士', '老师', '经理', '主任']
        suffixes = ['先生', '女士', '经理', '主任', '工程师', '设计师']

        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):].strip()

        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)].strip()

        # 检查是否只包含中文字符和常见符号
        if re.match(r'^[\u4e00-\u9fa5]+$', name):
            return name

        # 如果包含数字或特殊字符，可能不是姓名
        if re.search(r'\d', name):
            return ""

        # 长度检查
        if 2 <= len(name) <= 4:
            return name

        return ""

    def _is_valid_name(self, name: str) -> bool:
        """验证姓名的合理性"""
        if not name or len(name) < 2 or len(name) > 10:
            return False

        # 不包含数字
        if re.search(r'\d', name):
            return False

        # 检查是否包含中文
        if not re.search(r'[\u4e00-\u9fa5]', name):
            return False

        # 排除明显不是姓名的词汇
        exclude_words = {
            '采购', '招标', '中标', '公告', '项目', '联系', '方式', '电话',
            '地址', '邮箱', '公司', '单位', '代理', '机构', '供应商'
        }

        if name in exclude_words:
            return False

        return True

    def _extract_address(self, text: str) -> str:
        """提取地址"""
        address_patterns = [
            r'地址[：:\s]*([^\s,，。]{10,100})',
            r'地\s*址[：:\s]*([^\s,，。]{10,100})',
            r'位置[：:\s]*([^\s,，。]{10,100})',
        ]

        for pattern in address_patterns:
            match = re.search(pattern, text)
            if match:
                address = match.group(1).strip()
                if self._is_valid_address(address):
                    return address

        return ""

    def _is_valid_address(self, address: str) -> bool:
        """验证地址的合理性"""
        if len(address) < 10 or len(address) > 200:
            return False

        # 检查是否包含地址特征
        address_features = {
            '省', '市', '区', '县', '街', '路', '号', '栋', '楼', '室',
            '大道', '广场', '大厦', '中心', '园区'
        }

        return any(feature in address for feature in address_features)

    def _calculate_confidence(self, contact: LocalContactInfo) -> float:
        """计算联系人的置信度"""
        score = 0.0
        max_score = 5.0

        # 姓名 (1.5分)
        if contact.name:
            if self._is_valid_name(contact.name):
                score += 1.5
                if any(pos in contact.name for pos in self.position_keywords):
                    score += 0.3  # 包含职务加分

        # 公司 (1.5分)
        if contact.company:
            if self._is_valid_company_name(contact.company):
                score += 1.5
                if '有限公司' in contact.company or '有限责任公司' in contact.company:
                    score += 0.3  # 完整公司名加分

        # 电话 (1.0分)
        if contact.phone:
            score += 1.0

        # 邮箱 (0.5分)
        if contact.email:
            score += 0.5

        # 地址 (0.5分)
        if contact.address:
            score += 0.5

        return min(score / max_score, 1.0)

    def _is_valid_contact(self, contact: LocalContactInfo) -> bool:
        """验证联系人是否有效"""
        # 至少要有姓名或公司
        if not contact.name and not contact.company:
            return False

        # 置信度过滤
        if contact.confidence < 0.3:
            return False

        return True

    def _extract_by_patterns(self, text: str, phones: List[str], emails: List[str]) -> List[LocalContactInfo]:
        """使用模式匹配提取联系人（备用方法）"""
        contacts = []

        # 尝试从文本中找到人名+电话的组合
        name_phone_pairs = []

        # 分割文本寻找人名-电话对
        sections = re.split(r'[,，。\n]', text)

        for section in sections:
            section = section.strip()
            if len(section) < 5:
                continue

            # 查找人名
            for word in jieba.lcut(section):
                if self._is_valid_name(word):
                    # 在同一段落中查找电话
                    section_phones = [p for p in phones if p in section]
                    if section_phones:
                        contact = LocalContactInfo(
                            name=word,
                            phone=section_phones[0],
                            confidence=0.6,
                            source="pattern_extraction"
                        )

                        # 尝试提取公司
                        contact.company = self._extract_company(jieba.lcut(text), text)

                        if self._is_valid_contact(contact):
                            name_phone_pairs.append(contact)

        contacts.extend(name_phone_pairs)

        # 如果没有找到人名-电话对，创建基于电话的联系人
        if not contacts and phones:
            for phone in phones[:3]:  # 最多3个
                contact = LocalContactInfo(
                    phone=phone,
                    confidence=0.4,
                    source="phone_only"
                )

                # 尝试从电话附近的文本提取姓名
                phone_context = self._get_phone_context(text, phone)
                if phone_context:
                    words = jieba.lcut(phone_context)
                    for word in words:
                        if self._is_valid_name(word):
                            contact.name = word
                            contact.confidence = 0.7
                            break

                contacts.append(contact)

        return self._deduplicate_contacts(contacts)

    def _get_phone_context(self, text: str, phone: str) -> str:
        """获取电话号码周围的上下文"""
        phone_index = text.find(phone)
        if phone_index == -1:
            return ""

        # 提取电话前后各30个字符的上下文
        start = max(0, phone_index - 30)
        end = min(len(text), phone_index + len(phone) + 30)

        return text[start:end]

    def _deduplicate_contacts(self, contacts: List[LocalContactInfo]) -> List[LocalContactInfo]:
        """去重联系人"""
        seen = set()
        unique_contacts = []

        for contact in contacts:
            # 创建唯一标识
            identifier = f"{contact.name}_{contact.company}_{contact.phone}"

            if identifier not in seen:
                seen.add(identifier)
                unique_contacts.append(contact)

        # 按置信度排序
        unique_contacts.sort(key=lambda x: x.confidence, reverse=True)

        return unique_contacts