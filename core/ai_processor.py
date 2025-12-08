#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能联系人处理器
使用大模型进行联系人信息的智能提取、清洗和结构化
"""

import json
import logging
import time
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import requests

@dataclass
class ContactInfo:
    """结构化联系人信息"""
    name: str = ""
    company: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    department: str = ""
    position: str = ""
    confidence: float = 0.0

class AIContactProcessor:
    """AI驱动的联系人处理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()

        # 验证配置
        if not self._validate_config():
            self.logger.warning("AI处理器配置不完整，将使用基础模式")
            self.enabled = False
        else:
            self.enabled = True

    def _validate_config(self) -> bool:
        """验证AI配置"""
        ai_config = self.config.get('ai_processing', {})

        if not ai_config.get('enabled', False):
            return False

        provider = ai_config.get('provider', '')
        api_key = ai_config.get('api_key', '')

        if not provider or not api_key:
            return False

        return True

    def process_text_batch(self, texts: List[str]) -> List[ContactInfo]:
        """批量处理文本，提取结构化联系人信息"""
        if not self.enabled:
            return self._fallback_processing(texts)

        results = []
        batch_size = self.config.get('ai_processing.batch_size', 10)

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = self._process_batch_with_ai(batch)
            results.extend(batch_results)

            # 避免API频率限制
            if i + batch_size < len(texts):
                time.sleep(1)

        return results

    def _process_batch_with_ai(self, texts: List[str]) -> List[ContactInfo]:
        """使用AI处理一批文本"""
        try:
            # 构建提示词
            prompt = self._build_extraction_prompt(texts)

            # 调用AI API
            response = self._call_ai_api(prompt)

            # 解析响应
            return self._parse_ai_response(response, len(texts))

        except Exception as e:
            self.logger.error(f"AI处理失败: {e}")
            return self._fallback_processing(texts)

    def _build_extraction_prompt(self, texts: List[str]) -> str:
        """构建联系人提取提示词"""
        texts_json = json.dumps(texts, ensure_ascii=False, indent=2)

        prompt = f"""
你是一个专业的联系人信息提取助手。请从以下政府采购公告文本中提取结构化的联系人信息。

提取规则：
1. 只提取真实有效的联系人信息，忽略项目描述、技术参数等无关内容
2. 联系人通常包括：采购方联系人、代理机构联系人、项目负责人等
3. 电话号码要完整且格式正确（手机号11位，座机带区号）
4. 公司名称要完整准确，去除冗余信息
5. 如果信息不完整或不确定，请留空对应的字段
6. 为每个提取的联系人评估置信度（0.0-1.0）

文本数据：
{texts_json}

请按以下JSON格式返回结果（必须是有效的JSON数组）：
[
  {{
    "name": "联系人姓名",
    "company": "公司名称",
    "phone": "电话号码",
    "email": "邮箱地址",
    "address": "地址",
    "department": "部门",
    "position": "职位",
    "confidence": 0.95,
    "notes": "备注信息（可选）"
  }}
]

注意：
- 每个文本最多提取3个主要联系人
- 优先提取包含完整联系方式的联系人
- 如果某个文本没有找到有效联系人，返回空对象
- 置信度基于信息完整性和准确性评估
"""
        return prompt

    def _call_ai_api(self, prompt: str) -> str:
        """调用AI API"""
        ai_config = self.config.get('ai_processing', {})
        provider = ai_config.get('provider', '')

        if provider == 'openai':
            return self._call_openai_api(prompt)
        elif provider == 'claude':
            return self._call_claude_api(prompt)
        else:
            raise ValueError(f"不支持的AI提供商: {provider}")

    def _call_openai_api(self, prompt: str) -> str:
        """调用OpenAI API"""
        ai_config = self.config.get('ai_processing', {})

        headers = {
            "Authorization": f"Bearer {ai_config['api_key']}",
            "Content-Type": "application/json"
        }

        data = {
            "model": ai_config.get('model', 'gpt-3.5-turbo'),
            "messages": [
                {"role": "system", "content": "你是专业的联系人信息提取助手。"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": ai_config.get('max_tokens', 1000),
            "temperature": ai_config.get('temperature', 0.1)
        }

        base_url = ai_config.get('base_url', 'https://api.openai.com/v1')
        if not base_url.startswith('http'):
            base_url = 'https://api.openai.com/v1'

        url = f"{base_url}/chat/completions"

        response = self.session.post(
            url,
            headers=headers,
            json=data,
            timeout=ai_config.get('timeout', 30)
        )

        response.raise_for_status()
        result = response.json()

        return result['choices'][0]['message']['content']

    def _call_claude_api(self, prompt: str) -> str:
        """调用Claude API"""
        ai_config = self.config.get('ai_processing', {})

        headers = {
            "x-api-key": ai_config['api_key'],
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        data = {
            "model": ai_config.get('model', 'claude-3-haiku-20240307'),
            "max_tokens": ai_config.get('max_tokens', 1000),
            "temperature": ai_config.get('temperature', 0.1),
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        base_url = ai_config.get('base_url', 'https://api.anthropic.com')
        url = f"{base_url}/v1/messages"

        response = self.session.post(
            url,
            headers=headers,
            json=data,
            timeout=ai_config.get('timeout', 30)
        )

        response.raise_for_status()
        result = response.json()

        return result['content'][0]['text']

    def _parse_ai_response(self, response: str, expected_count: int) -> List[ContactInfo]:
        """解析AI响应"""
        try:
            # 尝试提取JSON部分
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response

            data = json.loads(json_str)

            contacts = []
            for item in data:
                if isinstance(item, dict):
                    contact = ContactInfo(
                        name=item.get('name', ''),
                        company=item.get('company', ''),
                        phone=item.get('phone', ''),
                        email=item.get('email', ''),
                        address=item.get('address', ''),
                        department=item.get('department', ''),
                        position=item.get('position', ''),
                        confidence=float(item.get('confidence', 0.0))
                    )
                    contacts.append(contact)

            return contacts

        except Exception as e:
            self.logger.error(f"解析AI响应失败: {e}")
            self.logger.debug(f"响应内容: {response}")
            return []

    def _fallback_processing(self, texts: List[str]) -> List[ContactInfo]:
        """回退到基础处理模式"""
        self.logger.info("使用基础模式处理联系人信息")

        contacts = []
        for text in texts:
            contact = self._basic_extract_contact(text)
            if contact:
                contacts.append(contact)

        return contacts

    def _basic_extract_contact(self, text: str) -> Optional[ContactInfo]:
        """基础联系人提取"""
        # 简单的正则表达式提取
        phone_pattern = r'1[3-9]\d{9}|\d{3,4}-\d{7,8}'
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

        phones = re.findall(phone_pattern, text)
        emails = re.findall(email_pattern, text)

        if phones or emails:
            contact = ContactInfo(
                phone=', '.join(phones) if phones else '',
                email=', '.join(emails) if emails else '',
                confidence=0.3  # 基础模式置信度较低
            )
            return contact

        return None

    def clean_and_standardize_contacts(self, contacts: List[ContactInfo]) -> List[ContactInfo]:
        """清洗和标准化联系人信息"""
        cleaned_contacts = []

        for contact in contacts:
            # 标准化电话号码
            if contact.phone:
                contact.phone = self._standardize_phone(contact.phone)

            # 标准化邮箱
            if contact.email:
                contact.email = self._standardize_email(contact.email)

            # 清理公司名称
            if contact.company:
                contact.company = self._clean_company_name(contact.company)

            # 清理姓名
            if contact.name:
                contact.name = self._clean_name(contact.name)

            # 验证基本信息
            if self._is_valid_contact(contact):
                cleaned_contacts.append(contact)

        # 去重
        cleaned_contacts = self._deduplicate_contacts(cleaned_contacts)

        return cleaned_contacts

    def _standardize_phone(self, phone: str) -> str:
        """标准化电话号码"""
        # 移除所有非数字字符，保留-
        phone = re.sub(r'[^\d-]', '', phone)

        # 标准化手机号格式
        if re.match(r'^1\d{10}$', phone):
            return phone

        # 标准化座机格式
        if re.match(r'^\d{3,4}-?\d{7,8}$', phone):
            if '-' not in phone:
                # 尝试添加区号分隔符
                if len(phone) == 11:
                    return f"{phone[:3]}-{phone[3:]}"
                elif len(phone) == 10:
                    return f"{phone[:3]}-{phone[3:]}"
            return phone

        return phone

    def _standardize_email(self, email: str) -> str:
        """标准化邮箱"""
        email = email.strip().lower()
        # 简单验证
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return email
        return ""

    def _clean_company_name(self, company: str) -> str:
        """清理公司名称"""
        # 移除常见的冗余信息
        company = re.sub(r'采购单位|代理机构|中标单位|供应商|名称\s*[:：]?\s*', '', company)
        company = re.sub(r'地址.*?联系方式.*', '', company)
        company = re.sub(r'\s+', ' ', company).strip()

        return company

    def _clean_name(self, name: str) -> str:
        """清理姓名"""
        # 移除常见的冗余信息
        name = re.sub(r'联系人|负责人|项目.*?联系人|电话.*?', '', name)
        name = re.sub(r'[:：\d]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()

        # 验证姓名长度
        if 2 <= len(name) <= 10 and re.search(r'[\u4e00-\u9fa5]', name):
            return name

        return ""

    def _is_valid_contact(self, contact: ContactInfo) -> bool:
        """验证联系人信息有效性"""
        # 至少要有一种联系方式
        has_contact_info = bool(
            contact.phone or contact.email or contact.name
        )

        if not has_contact_info:
            return False

        # 置信度过滤
        if contact.confidence < 0.3:
            return False

        return True

    def _deduplicate_contacts(self, contacts: List[ContactInfo]) -> List[ContactInfo]:
        """去重联系人"""
        seen = set()
        unique_contacts = []

        for contact in contacts:
            # 创建唯一标识（基于姓名+公司+电话）
            identifier = f"{contact.name}_{contact.company}_{contact.phone}"

            if identifier not in seen:
                seen.add(identifier)
                unique_contacts.append(contact)

        return unique_contacts