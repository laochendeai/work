#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件营销配置工具
设置和测试邮件营销系统，支持多种SMTP服务和个性化邮件模板
"""

import argparse
import json
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging


class EmailSetup:
    """邮件营销配置类"""

    def __init__(self):
        self.smtp_configs = {
            "qq": {
                "smtp_server": "smtp.qq.com",
                "smtp_port": 587,
                "use_tls": True,
                "auth_required": True,
                "description": "QQ邮箱 SMTP 服务器"
            },
            "163": {
                "smtp_server": "smtp.163.com",
                "smtp_port": 587,
                "use_tls": True,
                "auth_required": True,
                "description": "网易邮箱 SMTP 服务器"
            },
            "gmail": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "use_tls": True,
                "auth_required": True,
                "description": "Gmail SMTP 服务器"
            },
            "outlook": {
                "smtp_server": "smtp-mail.outlook.com",
                "smtp_port": 587,
                "use_tls": True,
                "auth_required": True,
                "description": "Outlook SMTP 服务器"
            },
            "enterprise": {
                "smtp_server": "mail.enterprise.com",
                "smtp_port": 587,
                "use_tls": True,
                "auth_required": True,
                "description": "企业邮箱 SMTP 服务器"
            }
        }

        self.email_config = {
            "sender": {
                "name": "您的姓名",
                "email": "your_email@qq.com",
                "password": "your_password_or_app_password",
                "smtp_type": "qq"
            },
            "sending": {
                "batch_size": 50,
                "delay_between_emails": 5,  # 秒
                "delay_between_batches": 300,  # 5分钟
                "max_retries": 3,
                "retry_delay": 60  # 1分钟
            },
            "content": {
                "default_subject": "智能化系统集成合作洽谈",
                "signature": "此致\\n敬礼！\\n\\n[您的姓名]\\n[您的公司]\\n[电话]\\n[邮箱]",
                "attachment_dir": "assets/attachments"
            },
            "tracking": {
                "enable_open_tracking": False,
                "enable_click_tracking": False,
                "tracking_domain": ""
            },
            "compliance": {
                "include_unsubscribe_link": True,
                "compliance_notice": "本邮件由智能化系统集成商发送，如不希望收到此类邮件请回复退订。"
            }
        }

    def create_email_config(self, config_path: str = "config/email_config.json"):
        """创建邮件配置文件"""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.email_config, f, ensure_ascii=False, indent=2)

        print(f"✓ 创建邮件配置: {config_path}")

    def create_email_sender(self, output_path: str = "src/email_marketing/email_sender.py"):
        """创建邮件发送器"""
        sender_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件发送器
支持个性化邮件发送、批量发送、模板管理等功能
"""

import json
import logging
import smtplib
import ssl
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Dict, List, Any, Optional
from jinja2 import Template


class EmailSender:
    """邮件发送器类"""

    def __init__(self, config_path: str = "config/email_config.json"):
        """
        初始化邮件发送器

        Args:
            config_path: 配置文件路径
        """
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        self.smtp_config = None
        self.template_cache = {}

        # 初始化SMTP配置
        self._setup_smtp()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"配置文件加载失败: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "sender": {
                "name": "智能设计工程师",
                "email": "your_email@qq.com",
                "password": "your_password",
                "smtp_type": "qq"
            },
            "sending": {
                "batch_size": 50,
                "delay_between_emails": 5,
                "delay_between_batches": 300
            },
            "content": {
                "default_subject": "智能化系统集成合作洽谈",
                "signature": "敬礼！\\n智能设计工程师"
            }
        }

    def _setup_smtp(self):
        """设置SMTP配置"""
        sender_config = self.config.get('sender', {})
        smtp_type = sender_config.get('smtp_type', 'qq')

        # SMTP服务器配置
        smtp_configs = {
            "qq": {
                "smtp_server": "smtp.qq.com",
                "smtp_port": 587,
                "use_tls": True
            },
            "163": {
                "smtp_server": "smtp.163.com",
                "smtp_port": 587,
                "use_tls": True
            },
            "gmail": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "use_tls": True
            },
            "outlook": {
                "smtp_server": "smtp-mail.outlook.com",
                "smtp_port": 587,
                "use_tls": True
            }
        }

        self.smtp_config = smtp_configs.get(smtp_type, smtp_configs["qq"])

    def _create_smtp_connection(self) -> smtplib.SMTP:
        """创建SMTP连接"""
        try:
            # 创建SMTP连接
            smtp = smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config['smtp_port'])

            # 启用调试模式
            smtp.set_debuglevel(0)

            # 启用TLS
            if self.smtp_config.get('use_tls', True):
                smtp.starttls()

            # 登录
            sender_config = self.config.get('sender', {})
            smtp.login(sender_config['email'], sender_config['password'])

            self.logger.info(f"SMTP连接成功: {self.smtp_config['smtp_server']}")
            return smtp

        except Exception as e:
            self.logger.error(f"SMTP连接失败: {e}")
            raise

    def _load_template(self, template_name: str) -> Template:
        """加载邮件模板"""
        if template_name in self.template_cache:
            return self.template_cache[template_name]

        template_path = Path(f"templates/emails/{template_name}.html")
        if not template_path.exists():
            # 使用默认模板
            template_content = self._get_default_template()
        else:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()

        template = Template(template_content)
        self.template_cache[template_name] = template
        return template

    def _get_default_template(self) -> str:
        """获取默认邮件模板"""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ subject }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .header { background: #f4f4f4; padding: 20px; text-align: center; }
        .content { padding: 20px; }
        .footer { background: #f4f4f4; padding: 15px; text-align: center; font-size: 12px; }
        .button { background: #007cba; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h2>{{ company_name }} - 智能化系统集成专家</h2>
    </div>

    <div class="content">
        <p>尊敬的{{ contact_name }}：</p>

        <p>{{ greeting_content }}</p>

        <p>{{ service_content }}</p>

        <p>{{ project_content }}</p>

        <p>期待与您合作！</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="#" class="button">了解详情</a>
        </div>
    </div>

    <div class="footer">
        <p>{{ signature }}</p>
        {% if compliance_notice %}
        <p>{{ compliance_notice }}</p>
        {% endif %}
    </div>
</body>
</html>
        """

    def create_personalized_email(self, contact: Dict[str, Any], template_name: str = "default") -> MIMEMultipart:
        """
        创建个性化邮件

        Args:
            contact: 联系人信息
            template_name: 模板名称

        Returns:
            邮件对象
        """
        # 加载模板
        template = self._load_template(template_name)

        # 准备模板变量
        template_vars = {
            'contact_name': contact.get('name', '您好'),
            'company_name': self.config.get('sender', {}).get('name', '智能设计工程师'),
            'contact_company': contact.get('company', ''),
            'project_title': contact.get('project_title', ''),
            'greeting_content': self._get_greeting_content(contact),
            'service_content': self._get_service_content(contact),
            'project_content': self._get_project_content(contact),
            'signature': self.config.get('content', {}).get('signature', ''),
            'compliance_notice': self.config.get('compliance', {}).get('compliance_notice', ''),
            'current_date': datetime.now().strftime('%Y年%m月%d日')
        }

        # 渲染邮件内容
        html_content = template.render(**template_vars)

        # 创建邮件对象
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{self.config['sender']['name']} <{self.config['sender']['email']}>"
        msg['To'] = contact.get('email', '')
        msg['Subject'] = self._get_personalized_subject(contact)

        # 添加HTML内容
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        # 添加纯文本内容
        text_content = self._html_to_text(html_content)
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))

        # 添加附件
        self._add_attachments(msg, contact)

        return msg

    def _get_greeting_content(self, contact: Dict[str, Any]) -> str:
        """获取问候内容"""
        company = contact.get('company', '')
        if company:
            return f"我们是专业的智能化系统集成商，了解到贵单位在{company}相关项目方面有需求，特此致函洽谈合作事宜。"
        else:
            return "我们是专业的智能化系统集成商，在智能化设计、弱电工程、系统集成等领域有丰富经验，希望能与您探讨合作机会。"

    def _get_service_content(self, contact: Dict[str, Any]) -> str:
        """获取服务介绍内容"""
        return """
        我公司专业提供以下智能化系统集成服务：
        • 智能化建筑设计：包括楼宇自控、安防监控、门禁系统等
        • 弱电系统工程：综合布线、机房建设、网络系统集成
        • 智慧校园/智慧园区：一卡通、停车管理、信息发布系统
        • 会议系统：视频会议、数字会议、专业音响灯光
        • 定制化解决方案：根据客户需求提供个性化系统集成方案

        我们拥有丰富的项目经验和专业的技术团队，已成功为众多政府机关、高校、企业提供了优质的智能化系统解决方案。
        """

    def _get_project_content(self, contact: Dict[str, Any]) -> str:
        """获取项目内容"""
        project_title = contact.get('project_title', '')
        if project_title:
            return f"针对您的项目《{project_title}》，我们有成熟的解决方案和丰富的实施经验，能够为您提供高质量的服务。"
        else:
            return "我们希望能有机会为您提供智能化系统集成服务，期待您的回复和进一步沟通。"

    def _get_personalized_subject(self, contact: Dict[str, Any]) -> str:
        """获取个性化主题"""
        company = contact.get('company', '')
        name = contact.get('name', '')

        if company and name:
            return f"{company}智能化系统集成合作洽谈 - 致{name}"
        elif company:
            return f"{company}智能化系统集成合作洽谈"
        else:
            return "智能化系统集成合作洽谈"

    def _html_to_text(self, html_content: str) -> str:
        """将HTML内容转换为纯文本"""
        # 简单的HTML标签移除
        import re
        text = re.sub(r'<[^>]+>', '', html_content)
        return text.strip()

    def _add_attachments(self, msg: MIMEMultipart, contact: Dict[str, Any]):
        """添加附件"""
        attachment_dir = Path(self.config.get('content', {}).get('attachment_dir', 'assets/attachments'))

        if not attachment_dir.exists():
            return

        # 默认添加的附件
        default_attachments = ['company_profile.pdf', 'service_catalog.pdf']

        for filename in default_attachments:
            file_path = attachment_dir / filename
            if file_path.exists():
                try:
                    with open(file_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {filename}'
                        )
                        msg.attach(part)
                except Exception as e:
                    self.logger.warning(f"附件添加失败 {filename}: {e}")

    def send_email(self, contact: Dict[str, Any], template_name: str = "default") -> bool:
        """
        发送单封邮件

        Args:
            contact: 联系人信息
            template_name: 邮件模板名称

        Returns:
            发送是否成功
        """
        try:
            # 创建SMTP连接
            smtp = self._create_smtp_connection()

            # 创建邮件
            msg = self.create_personalized_email(contact, template_name)

            # 发送邮件
            smtp.send_message(msg)
            smtp.quit()

            self.logger.info(f"邮件发送成功: {contact.get('email', '')}")
            return True

        except Exception as e:
            self.logger.error(f"邮件发送失败 {contact.get('email', '')}: {e}")
            return False

    def send_batch_emails(self, contacts: List[Dict[str, Any]], template_name: str = "default") -> Dict[str, Any]:
        """
        批量发送邮件

        Args:
            contacts: 联系人列表
            template_name: 邮件模板名称

        Returns:
            发送结果统计
        """
        results = {
            'total': len(contacts),
            'success': 0,
            'failed': 0,
            'failed_contacts': []
        }

        sending_config = self.config.get('sending', {})
        batch_size = sending_config.get('batch_size', 50)
        delay_between_emails = sending_config.get('delay_between_emails', 5)
        delay_between_batches = sending_config.get('delay_between_batches', 300)

        try:
            # 创建SMTP连接
            smtp = self._create_smtp_connection()

            for i, contact in enumerate(contacts):
                try:
                    # 创建并发送邮件
                    msg = self.create_personalized_email(contact, template_name)
                    smtp.send_message(msg)

                    results['success'] += 1
                    self.logger.info(f"邮件发送成功 ({i+1}/{len(contacts)}): {contact.get('email', '')}")

                except Exception as e:
                    results['failed'] += 1
                    results['failed_contacts'].append({
                        'contact': contact,
                        'error': str(e)
                    })
                    self.logger.error(f"邮件发送失败 {contact.get('email', '')}: {e}")

                # 邮件间延时
                if i < len(contacts) - 1:
                    time.sleep(delay_between_emails)

                # 批次间延时
                if (i + 1) % batch_size == 0 and i < len(contacts) - 1:
                    self.logger.info(f"完成批次 {((i + 1) // batch_size)}，休息 {delay_between_batches} 秒")
                    time.sleep(delay_between_batches)

            smtp.quit()

        except Exception as e:
            self.logger.error(f"批量发送过程中出错: {e}")

        return results

    def test_connection(self) -> bool:
        """测试SMTP连接"""
        try:
            smtp = self._create_smtp_connection()
            smtp.quit()
            self.logger.info("SMTP连接测试成功")
            return True
        except Exception as e:
            self.logger.error(f"SMTP连接测试失败: {e}")
            return False

    def send_test_email(self, recipient_email: str) -> bool:
        """
        发送测试邮件

        Args:
            recipient_email: 收件人邮箱

        Returns:
            发送是否成功
        """
        test_contact = {
            'name': '测试用户',
            'email': recipient_email,
            'company': '测试公司',
            'project_title': '测试项目'
        }

        return self.send_email(test_contact, 'default')


def main():
    """主函数 - 用于测试"""
    # 测试配置
    config = {
        "sender": {
            "name": "智能设计工程师",
            "email": "your_email@qq.com",
            "password": "your_password",
            "smtp_type": "qq"
        },
        "sending": {
            "batch_size": 10,
            "delay_between_emails": 2,
            "delay_between_batches": 60
        }
    }

    # 创建邮件发送器
    sender = EmailSender()
    sender.config = config

    # 测试连接
    if sender.test_connection():
        print("✓ SMTP连接测试成功")

        # 发送测试邮件
        # test_email = "recipient@example.com"
        # if sender.send_test_email(test_email):
        #     print(f"✓ 测试邮件发送成功: {test_email}")
        # else:
        #     print(f"❌ 测试邮件发送失败: {test_email}")
    else:
        print("❌ SMTP连接测试失败")


if __name__ == "__main__":
    main()
'''

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(sender_code)

        print(f"✓ 创建邮件发送器: {output_path}")

    def create_email_templates(self, template_dir: str = "templates/emails"):
        """创建邮件模板"""
        template_path = Path(template_dir)
        template_path.mkdir(parents=True, exist_ok=True)

        templates = {
            "default.html": '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ subject }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }
        .content { padding: 30px; background: #f9f9f9; }
        .service-list { background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .service-item { margin: 15px 0; padding: 15px; border-left: 4px solid #667eea; background: #f0f4f8; }
        .footer { background: #333; color: white; padding: 20px; text-align: center; }
        .button { background: #667eea; color: white; padding: 12px 25px; text-decoration: none; border-radius: 25px; display: inline-block; margin: 20px 0; }
        .highlight { background: #fff3cd; padding: 15px; border-radius: 8px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>智能化系统集成解决方案</h1>
        <p>专业 | 高效 | 可靠</p>
    </div>

    <div class="content">
        <p>尊敬的{{ contact_name }}：</p>

        <div class="highlight">
            <strong>{{ greeting_content }}</strong>
        </div>

        <h3>我们的专业服务</h3>
        <div class="service-list">
            <div class="service-item">
                <strong>智能化建筑设计</strong><br>
                楼宇自控、安防监控、门禁系统、智能照明
            </div>
            <div class="service-item">
                <strong>弱电系统工程</strong><br>
                综合布线、机房建设、网络系统集成、数据中心
            </div>
            <div class="service-item">
                <strong>智慧解决方案</strong><br>
                智慧校园、智慧园区、一卡通、停车管理系统
            </div>
        </div>

        <h3>项目优势</h3>
        <ul>
            <li>✓ 10年以上行业经验</li>
            <li>✓ 专业技术团队</li>
            <li>✓ 完善的售后服务</li>
            <li>✓ 成功案例众多</li>
        </ul>

        <div style="text-align: center;">
            <a href="#" class="button">立即咨询</a>
        </div>

        <p>{{ project_content }}</p>
    </div>

    <div class="footer">
        <p>{{ signature }}</p>
        <p style="font-size: 12px; margin-top: 15px;">
            {{ compliance_notice }}
        </p>
    </div>
</body>
</html>''',

            "government.html": '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>政府采购项目合作洽谈 - {{ subject }}</title>
    <style>
        body { font-family: "Microsoft YaHei", Arial, sans-serif; line-height: 1.8; color: #2c3e50; max-width: 650px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 35px; text-align: center; }
        .content { padding: 35px; background: #ffffff; }
        .gov-badge { background: #e74c3c; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold; display: inline-block; margin: 10px 0; }
        .project-info { background: #ecf0f1; padding: 25px; border-radius: 10px; margin: 25px 0; border-left: 5px solid #3498db; }
        .qualification { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .footer { background: #34495e; color: white; padding: 25px; text-align: center; }
        .contact-info { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .button { background: #3498db; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; display: inline-block; margin: 25px 0; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <h1>政府采购项目智能化解决方案</h1>
        <p>专业供应商 | 资质齐全 | 经验丰富</p>
        <div class="gov-badge">政府采购合格供应商</div>
    </div>

    <div class="content">
        <p>尊敬的{{ contact_name }}：</p>

        <div class="project-info">
            <h3>关于项目《{{ project_title }}》</h3>
            <p>我们注意到贵单位发布的智能化建设项目，我公司在该领域具有丰富的实施经验和完善的技术方案，特此致函表达合作意向。</p>
        </div>

        <h3>公司资质与优势</h3>
        <div class="qualification">
            <ul>
                <li>✓ 电子与智能化工程专业承包资质</li>
                <li>✓ 安防工程企业资质</li>
                <li>✓ ISO9001质量管理体系认证</li>
                <li>✓ 政府采购项目实施经验50+</li>
                <li>✓ 专业工程师团队30+</li>
            </ul>
        </div>

        <h3>政府采购项目经验</h3>
        <p>我们成功实施过的政府项目包括：</p>
        <ul>
            <li>行政中心智能化系统建设</li>
            <li>公安部门安防监控系统</li>
            <li>教育系统智慧校园建设</li>
            <li>医疗机构智能化改造</li>
            <li>交通枢纽智能化系统</li>
        </ul>

        <div class="contact-info">
            <h3>项目联系方式</h3>
            <p><strong>项目负责人：</strong>王经理</p>
            <p><strong>联系电话：</strong>138-1234-5678</p>
            <p><strong>邮箱：</strong>project@company.com</p>
            <p><strong>技术支持：</strong>7×24小时响应</p>
        </div>

        <div style="text-align: center;">
            <a href="#" class="button">获取详细技术方案</a>
        </div>
    </div>

    <div class="footer">
        <p>{{ signature }}</p>
        <p style="font-size: 12px; margin-top: 15px;">
            {{ compliance_notice }}
        </p>
    </div>
</body>
</html>''',

            "university.html": '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>智慧校园建设合作 - {{ subject }}</title>
    <style>
        body { font-family: "Microsoft YaHei", Arial, sans-serif; line-height: 1.8; color: #2c3e50; max-width: 650px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #27ae60 0%, #16a085 100%); color: white; padding: 35px; text-align: center; }
        .content { padding: 35px; background: #ffffff; }
        .edu-badge { background: #e67e22; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold; display: inline-block; margin: 10px 0; }
        .campus-solution { background: #f0f8ff; padding: 25px; border-radius: 10px; margin: 25px 0; border-left: 5px solid #27ae60; }
        .case-study { background: #fff9e6; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .footer { background: #2c3e50; color: white; padding: 25px; text-align: center; }
        .button { background: #27ae60; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; display: inline-block; margin: 25px 0; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <h1>智慧校园整体解决方案</h1>
        <p>教育信息化专家 | 校园智能化领导者</p>
        <div class="edu-badge">教育信息化优质服务商</div>
    </div>

    <div class="content">
        <p>尊敬的{{ contact_name }}：</p>

        <div class="campus-solution">
            <h3>针对{{ contact_company }}智慧校园建设</h3>
            <p>我们了解到贵校在智慧校园建设方面的规划，我公司在教育信息化领域深耕多年，已成功为众多高校提供了完整的智慧校园解决方案。</p>
        </div>

        <h3>智慧校园核心系统</h3>
        <ul>
            <li><strong>智慧教学环境</strong> - 多媒体教室、录播系统、在线教学平台</li>
            <li><strong>智能管理平台</strong> - 一卡通系统、教务管理、学生管理系统</li>
            <li><strong>校园安全防护</strong> - 安防监控、门禁系统、紧急报警系统</li>
            <li><strong>智慧后勤服务</strong> - 智能宿舍、能源管理、停车管理系统</li>
            <li><strong>数字化校园网</strong> - 校园网络覆盖、数据中心建设</li>
        </ul>

        <div class="case-study">
            <h3>成功案例</h3>
            <p>我们已为以下高校提供智慧校园服务：</p>
            <ul>
                <li>XX大学智慧校园一期、二期工程</li>
                <li>XX职业技术学院智能化改造</li>
                <li>XX师范学院数字化校园建设</li>
                <li>XX理工大学一卡通系统升级</li>
            </ul>
        </div>

        <h3>教育行业优势</h3>
        <ul>
            <li>✓ 深刻理解教育行业需求</li>
            <li>✓ 丰富的校园项目实施经验</li>
            <li>✓ 符合教育部技术标准</li>
            <li>✓ 完善的培训和技术支持</li>
            <li>✓ 长期稳定的维护服务</li>
        </ul>

        <div style="text-align: center;">
            <a href="#" class="button">预约技术交流</a>
        </div>
    </div>

    <div class="footer">
        <p>{{ signature }}</p>
        <p style="font-size: 12px; margin-top: 15px;">
            {{ compliance_notice }}
        </p>
    </div>
</body>
</html>'''
        }

        for filename, content in templates.items():
            template_file = template_path / filename
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 创建邮件模板: {template_file}")

    def create_test_script(self, output_path: str = "scripts/test_email.py"):
        """创建邮件测试脚本"""
        test_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件营销系统测试脚本
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.email_marketing.email_sender import EmailSender


def test_email_config():
    """测试邮件配置"""
    print("=== 邮件配置测试 ===")

    try:
        sender = EmailSender()
        print("✓ 邮件发送器初始化成功")

        # 测试SMTP连接
        if sender.test_connection():
            print("✓ SMTP连接测试成功")
        else:
            print("❌ SMTP连接测试失败")
            return False

        return True

    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False


def test_template_rendering():
    """测试模板渲染"""
    print("\\n=== 模板渲染测试 ===")

    try:
        sender = EmailSender()

        # 测试联系人数据
        test_contact = {
            'name': '张经理',
            'email': 'zhang@company.com',
            'company': '示例大学',
            'project_title': '智慧校园建设项目',
            'phone': '13812345678'
        }

        # 测试默认模板
        msg = sender.create_personalized_email(test_contact, 'default')
        print("✓ 默认模板渲染成功")

        # 测试政府模板
        msg = sender.create_personalized_email(test_contact, 'government')
        print("✓ 政府模板渲染成功")

        # 测试高校模板
        msg = sender.create_personalized_email(test_contact, 'university')
        print("✓ 高校模板渲染成功")

        return True

    except Exception as e:
        print(f"❌ 模板渲染测试失败: {e}")
        return False


def test_personalization():
    """测试个性化功能"""
    print("\\n=== 个性化功能测试 ===")

    try:
        sender = EmailSender()

        # 测试不同类型联系人
        contacts = [
            {
                'name': '王主任',
                'email': 'wang@gov.cn',
                'company': 'XX市人民政府',
                'project_title': '行政中心智能化改造',
                'type': 'government'
            },
            {
                'name': '李教授',
                'email': 'li@university.edu.cn',
                'company': 'XX大学',
                'project_title': '智慧校园一期工程',
                'type': 'university'
            }
        ]

        for contact in contacts:
            # 政府联系人使用政府模板
            template = 'government' if contact.get('type') == 'government' else 'university'
            msg = sender.create_personalized_email(contact, template)
            print(f"✓ {contact['name']} ({contact['company']}) 个性化邮件创建成功")

        return True

    except Exception as e:
        print(f"❌ 个性化功能测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("邮件营销系统测试")
    print("=" * 50)

    all_tests_passed = True

    # 运行各项测试
    tests = [
        test_email_config,
        test_template_rendering,
        test_personalization
    ]

    for test_func in tests:
        if not test_func():
            all_tests_passed = False

    print("\\n" + "=" * 50)
    if all_tests_passed:
        print("✅ 所有测试通过！邮件营销系统配置正确。")
        print("\\n下一步：")
        print("1. 配置真实的SMTP服务器信息")
        print("2. 发送测试邮件验证功能")
        print("3. 准备联系人数据开始批量发送")
    else:
        print("❌ 部分测试失败，请检查配置。")


if __name__ == "__main__":
    main()
'''

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(test_script)

        print(f"✓ 创建邮件测试脚本: {output_path}")

    def test_smtp_connection(self, smtp_type: str = "qq", email: str = "", password: str = "") -> bool:
        """测试SMTP连接"""
        try:
            config = self.smtp_configs.get(smtp_type)
            if not config:
                print(f"❌ 不支持的SMTP类型: {smtp_type}")
                return False

            print(f"正在测试 {config['description']}...")

            # 创建连接
            if config.get('use_tls', True):
                context = ssl.create_default_context()
                server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
                server.starttls(context=context)
            else:
                server = smtplib.SMTP_SSL(config['smtp_server'], config['smtp_port'])

            # 登录测试
            if config.get('auth_required', True) and email and password:
                server.login(email, password)
                print("✓ SMTP登录成功")
            else:
                print("✓ SMTP连接成功")

            server.quit()
            return True

        except Exception as e:
            print(f"❌ SMTP连接失败: {e}")
            return False

    def setup_email_system(self, config_path: str = "config/email_config.json",
                          sender_path: str = "src/email_marketing/email_sender.py",
                          template_dir: str = "templates/emails",
                          test_script_path: str = "scripts/test_email.py"):
        """完整设置邮件营销系统"""
        print("开始设置邮件营销系统...")
        print("-" * 50)

        try:
            # 1. 创建配置文件
            self.create_email_config(config_path)

            # 2. 创建邮件发送器
            self.create_email_sender(sender_path)

            # 3. 创建邮件模板
            self.create_email_templates(template_dir)

            # 4. 创建测试脚本
            self.create_test_script(test_script_path)

            print("-" * 50)
            print("✅ 邮件营销系统设置完成！")
            print()
            print("文件位置:")
            print(f"  - 配置文件: {config_path}")
            print(f"  - 邮件发送器: {sender_path}")
            print(f"  - 邮件模板: {template_dir}")
            print(f"  - 测试脚本: {test_script_path}")
            print()
            print("下一步:")
            print("1. 编辑配置文件设置SMTP服务器信息")
            print("2. 运行测试脚本验证配置: python scripts/test_email.py")
            print("3. 发送测试邮件验证功能")
            print("4. 准备联系人数据开始邮件营销")

        except Exception as e:
            print(f"❌ 设置失败: {e}")
            raise


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="邮件营销配置工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python setup_email.py --setup
  python setup_email.py --config
  python setup_email.py --template
  python setup_email.py --test-smtp qq your_email@qq.com your_password
  python setup_email.py --test
        """
    )

    parser.add_argument(
        "--setup",
        action="store_true",
        help="完整设置邮件营销系统"
    )

    parser.add_argument(
        "--config",
        action="store_true",
        help="创建邮件配置文件"
    )

    parser.add_argument(
        "--template",
        action="store_true",
        help="创建邮件模板"
    )

    parser.add_argument(
        "--test-smtp",
        nargs=3,
        metavar=("TYPE", "EMAIL", "PASSWORD"),
        help="测试SMTP连接"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="运行邮件系统测试"
    )

    args = parser.parse_args()

    try:
        setup = EmailSetup()

        if args.setup:
            setup.setup_email_system()
        elif args.config:
            setup.create_email_config()
            print("✓ 邮件配置文件创建完成")
        elif args.template:
            setup.create_email_templates()
            print("✓ 邮件模板创建完成")
        elif args.test_smtp:
            smtp_type, email, password = args.test_smtp
            setup.test_smtp_connection(smtp_type, email, password)
        elif args.test:
            print("邮件营销系统测试")
            print("请运行: python scripts/test_email.py")
        else:
            parser.print_help()

    except Exception as e:
        print(f"❌ 操作失败: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()