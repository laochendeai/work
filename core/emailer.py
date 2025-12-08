#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件发送器
统一的邮件发送功能，整合所有邮件相关代码
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

from config.settings import settings

class EmailSender:
    """邮件发送器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_config()

    def _setup_config(self):
        """设置邮件配置"""
        self.smtp_server = settings.get('email.smtp_server', 'smtp.qq.com')
        self.smtp_port = settings.get('email.smtp_port', 587)
        self.use_ssl = settings.get('email.use_ssl', False)
        self.sender_email = settings.get('email.sender_email', '')
        self.sender_password = settings.get('email.sender_password', '')
        self.sender_name = settings.get('email.sender_name', '设计营销助手')

    def test_config(self) -> bool:
        """测试邮件配置"""
        if not self.sender_email or not self.sender_password:
            self.logger.error("邮件配置不完整：缺少发件人邮箱或密码")
            return False

        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()

            server.login(self.sender_email, self.sender_password)
            server.quit()
            self.logger.info("邮件配置测试成功")
            return True

        except Exception as e:
            self.logger.error(f"邮件配置测试失败: {e}")
            return False

    def send_single_email(self, to_email: str, subject: str, content: str,
                         html_content: str = None) -> bool:
        """发送单封邮件"""
        if not self.test_config():
            return False

        try:
            # 创建邮件对象
            if html_content:
                msg = MIMEMultipart('alternative')
                msg.attach(MIMEText(content, 'plain', 'utf-8'))
                msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            else:
                msg = MIMEText(content, 'plain', 'utf-8')

            # 设置邮件头
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = to_email
            msg['Subject'] = Header(subject, 'utf-8')

            # 发送邮件
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()

            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()

            self.logger.info(f"邮件发送成功: {to_email}")
            return True

        except Exception as e:
            self.logger.error(f"邮件发送失败 {to_email}: {e}")
            return False

    def send_batch_emails(self, emails: List[Dict[str, Any]],
                         template_type: str = 'default') -> Dict[str, Any]:
        """批量发送邮件"""
        results = {
            'total': len(emails),
            'success': 0,
            'failed': 0,
            'failed_emails': []
        }

        for email_data in emails:
            to_email = email_data.get('email', '')
            if not to_email:
                continue

            # 生成邮件内容
            subject, content, html_content = self._generate_email_content(email_data, template_type)

            if self.send_single_email(to_email, subject, content, html_content):
                results['success'] += 1
            else:
                results['failed'] += 1
                results['failed_emails'].append(to_email)

            # 避免发送太快
            import time
            time.sleep(2)

        self.logger.info(f"批量发送完成: 成功 {results['success']}, 失败 {results['failed']}")
        return results

    def _generate_email_content(self, email_data: Dict[str, Any],
                               template_type: str) -> tuple:
        """生成邮件内容"""
        templates = {
            'default': self._default_template,
            'marketing': self._marketing_template,
            'followup': self._followup_template
        }

        template_func = templates.get(template_type, self._default_template)
        return template_func(email_data)

    def _default_template(self, data: Dict[str, Any]) -> tuple:
        """默认邮件模板"""
        name = data.get('name', '您好')
        company = data.get('company', '')
        title = data.get('title', '')

        subject = "设计服务咨询"
        content = f"""
尊敬的{name}：

您好！我们是专业的设计服务团队，了解到贵公司近期有相关项目需求。

如果您需要专业的设计服务，我们很乐意为您提供帮助。

期待您的回复！

此致
敬礼！

{self.sender_name}
{self.sender_email}
"""

        html_content = f"""
<html>
<body>
    <p>尊敬的{name}：</p>
    <p>您好！我们是专业的设计服务团队，了解到贵公司近期有相关项目需求。</p>
    <p>如果您需要专业的设计服务，我们很乐意为您提供帮助。</p>
    <p>期待您的回复！</p>
    <p>此致<br>敬礼！</p>
    <p><strong>{self.sender_name}</strong><br>
    {self.sender_email}</p>
</body>
</html>
"""

        return subject, content.strip(), html_content

    def _marketing_template(self, data: Dict[str, Any]) -> tuple:
        """营销邮件模板"""
        name = data.get('name', '项目负责人')
        company = data.get('company', '')
        title = data.get('title', '')

        subject = "专业设计服务 - 项目合作机会"
        content = f"""
尊敬的{name}：

您好！

我们注意到{company}发布的《{title}》项目，我们是一家专业的工程设计公司，
在相关领域拥有丰富经验，希望能有机会参与贵公司的项目。

我们的服务包括：
- 建筑设计
- 工程设计
- 规划设计
- 室内设计
- 园林景观设计

如有合作机会，请随时联系我们。

期待与您的合作！

{self.sender_name}
{self.sender_email}
电话：[您的电话]
地址：[您的地址]
"""

        html_content = f"""
<html>
<body>
    <h2>专业设计服务 - 项目合作机会</h2>
    <p>尊敬的{name}：</p>
    <p>您好！</p>
    <p>我们注意到{company}发布的《{title}》项目，我们是一家专业的工程设计公司，在相关领域拥有丰富经验，希望能有机会参与贵公司的项目。</p>

    <h3>我们的服务包括：</h3>
    <ul>
        <li>建筑设计</li>
        <li>工程设计</li>
        <li>规划设计</li>
        <li>室内设计</li>
        <li>园林景观设计</li>
    </ul>

    <p>如有合作机会，请随时联系我们。</p>
    <p>期待与您的合作！</p>

    <hr>
    <p><strong>{self.sender_name}</strong><br>
    邮箱：{self.sender_email}<br>
    电话：[您的电话]<br>
    地址：[您的地址]</p>
</body>
</html>
"""

        return subject, content.strip(), html_content

    def _followup_template(self, data: Dict[str, Any]) -> tuple:
        """跟进邮件模板"""
        name = data.get('name', '您好')
        company = data.get('company', '')

        subject = "跟进：设计服务合作咨询"
        content = f"""
尊敬的{name}：

您好！

前段时间我们曾联系过贵公司，询问设计服务合作的可能性。
不知道贵公司近期是否有相关项目需求？

我们随时准备为您提供专业的设计服务。

祝好！

{self.sender_name}
{self.sender_email}
"""

        html_content = f"""
<html>
<body>
    <p>尊敬的{name}：</p>
    <p>您好！</p>
    <p>前段时间我们曾联系过贵公司，询问设计服务合作的可能性。不知道贵公司近期是否有相关项目需求？</p>
    <p>我们随时准备为您提供专业的设计服务。</p>
    <p>祝好！</p>
    <p><strong>{self.sender_name}</strong><br>
    {self.sender_email}</p>
</body>
</html>
"""

        return subject, content.strip(), html_content

    def send_test_email(self, to_email: str = None) -> bool:
        """发送测试邮件"""
        test_email = to_email or self.sender_email
        if not test_email:
            self.logger.error("没有设置测试邮箱地址")
            return False

        subject = "智能设计营销系统 - 测试邮件"
        content = """
这是一封测试邮件，用于验证邮件配置是否正确。

如果您收到这封邮件，说明邮件配置正常。

智能设计营销系统
"""

        return self.send_single_email(test_email, subject, content)

    def load_contacts_from_database(self, db_path: str = None) -> List[Dict[str, Any]]:
        """从数据库加载联系人"""
        if not db_path:
            db_path = settings.get('storage.database_path', 'data/marketing.db')

        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT title, source, link, scraped_at, emails, phones, companies, names
                FROM contacts
                ORDER BY created_at DESC
                LIMIT 100
            ''')

            contacts = []
            for row in cursor.fetchall():
                (title, source, link, scraped_at, emails, phones, companies, names) = row

                # 解析JSON字段
                emails = json.loads(emails) if emails else []
                phones = json.loads(phones) if phones else []
                companies = json.loads(companies) if companies else []
                names = json.loads(names) if names else []

                contacts.append({
                    'title': title,
                    'source': source,
                    'link': link,
                    'scraped_at': scraped_at,
                    'emails': emails,
                    'phones': phones,
                    'companies': companies,
                    'names': names,
                })

            conn.close()
            return contacts

        except Exception as e:
            self.logger.error(f"从数据库加载联系人失败: {e}")
            return []

# 全局邮件发送器实例
emailer = EmailSender()