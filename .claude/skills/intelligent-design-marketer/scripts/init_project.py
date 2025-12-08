#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能设计营销自动化项目初始化脚本
一键创建完整的项目结构和配置文件
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class InputValidationError(Exception):
    """输入验证错误"""
    pass


class ProjectInitializer:
    """项目初始化器"""

    def __init__(self, project_name: str, project_type: str = "basic"):
        self.project_name = project_name
        self.project_type = project_type.lower()
        self.project_root = Path.cwd() / project_name

        # 验证项目类型
        if self.project_type not in ["basic", "comprehensive"]:
            raise InputValidationError(f"无效的项目类型: {project_type}. 支持: basic, comprehensive")

        # 验证项目名称
        if not project_name.replace('-', '').replace('_', '').isalnum():
            raise InputValidationError("项目名称只能包含字母、数字、连字符和下划线")

    def create_project_structure(self):
        """创建项目目录结构"""
        directories = [
            "src/scrapers",
            "src/extractors",
            "src/email_marketing",
            "src/data_processing",
            "src/utils",
            "config",
            "tests",
            "templates/emails",
            "templates/reports",
            "data/raw",
            "data/processed",
            "logs",
            "docs",
            "scripts"
        ]

        if self.project_type == "comprehensive":
            directories.extend([
                "src/ai_processing",
                "src/multi_source_scraping",
                "src/advanced_extraction",
                "config/environments",
                "tests/integration",
                "tests/performance",
                "monitoring",
                "docker"
            ])

        for directory in directories:
            (self.project_root / directory).mkdir(parents=True, exist_ok=True)
            print(f"✓ 创建目录: {directory}")

    def create_basic_config(self):
        """创建基础配置文件"""
        config = {
            "project_info": {
                "name": self.project_name,
                "type": self.project_type,
                "created_at": datetime.now().isoformat(),
                "version": "1.0.0"
            },
            "scraping": {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "delay_range": [1, 3],
                "timeout": 30,
                "max_retries": 3,
                "concurrent_requests": 5
            },
            "data_sources": {
                "government": {
                    "enabled": True,
                    "base_url": "https://search.ccgp.gov.cn",
                    "search_keywords": ["弱电", "智能化", "安防", "网络建设"]
                }
            },
            "extraction": {
                "contact_fields": ["phone", "email", "name", "department"],
                "company_fields": ["name", "address", "industry"],
                "project_fields": ["title", "budget", "deadline", "requirements"]
            },
            "email": {
                "smtp_server": "smtp.qq.com",
                "smtp_port": 587,
                "use_tls": True,
                "batch_size": 50,
                "delay_between_batches": 300
            },
            "database": {
                "type": "sqlite",
                "path": "data/marketing_data.db"
            }
        }

        if self.project_type == "comprehensive":
            config.update({
                "advanced_features": {
                    "ai_extraction": True,
                    "multi_source_correlation": True,
                    "intelligent_scheduling": True,
                    "performance_monitoring": True
                },
                "additional_sources": {
                    "universities": {
                        "enabled": True,
                        "targets": ["tsinghua.edu.cn", "pku.edu.cn", "fudan.edu.cn"]
                    },
                    "enterprises": {
                        "enabled": True,
                        "targets": ["huawei.com", "tencent.com", "alibaba.com"]
                    }
                }
            })

        config_file = self.project_root / "config" / "project_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print(f"✓ 创建配置文件: config/project_config.json")

    def create_main_module(self):
        """创建主应用程序模块"""
        main_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
{self.project_name} - 智能设计营销自动化系统
主程序入口
"""

import json
import logging
import schedule
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.scrapers.government_scraper import GovernmentScraper
from src.extractors.contact_extractor import ContactExtractor
from src.email_marketing.email_sender import EmailSender
from src.utils.database_manager import DatabaseManager
from src.utils.logger import setup_logger


class MarketingAutomationSystem:
    """营销自动化系统主类"""

    def __init__(self, config_path: str = "config/project_config.json"):
        """初始化系统"""
        self.config = self._load_config(config_path)
        self.logger = setup_logger("marketing_system", "logs/marketing.log")

        # 初始化组件
        self.db_manager = DatabaseManager(self.config["database"])
        self.scraper = GovernmentScraper(self.config["scraping"])
        self.extractor = ContactExtractor(self.config["extraction"])
        self.email_sender = EmailSender(self.config["email"])

        self.logger.info("营销自动化系统初始化完成")

    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"配置文件加载失败: {{e}}")
            sys.exit(1)

    def run_scraping_task(self):
        """执行爬取任务"""
        self.logger.info("开始执行爬取任务")
        try:
            # 爬取政府采购信息
            procurement_data = self.scraper.scrape_procurement()

            # 保存到数据库
            for data in procurement_data:
                self.db_manager.save_procurement(data)

            self.logger.info(f"爬取任务完成，获取 {{len(procurement_data)}} 条数据")

        except Exception as e:
            self.logger.error(f"爬取任务失败: {{e}}")

    def run_extraction_task(self):
        """执行信息提取任务"""
        self.logger.info("开始执行信息提取任务")
        try:
            # 获取未处理的采购数据
            unprocessed_data = self.db_manager.get_unprocessed_procurement()

            # 提取联系人信息
            for data in unprocessed_data:
                contacts = self.extractor.extract_contacts(data['content'])
                self.db_manager.save_contacts(data['id'], contacts)

            self.logger.info(f"信息提取任务完成，处理 {{len(unprocessed_data)}} 条数据")

        except Exception as e:
            self.logger.error(f"信息提取任务失败: {{e}}")

    def run_email_marketing_task(self):
        """执行邮件营销任务"""
        self.logger.info("开始执行邮件营销任务")
        try:
            # 获取未发送邮件的联系人
            contacts = self.db_manager.get_contacts_for_email()

            # 发送邮件
            for contact in contacts:
                success = self.email_sender.send_personalized_email(contact)
                if success:
                    self.db_manager.mark_email_sent(contact['id'])

            self.logger.info(f"邮件营销任务完成，发送 {{len(contacts)}} 封邮件")

        except Exception as e:
            self.logger.error(f"邮件营销任务失败: {{e}}")

    def setup_schedule(self):
        """设置定时任务"""
        # 每小时执行爬取任务
        schedule.every().hour.do(self.run_scraping_task)

        # 每30分钟执行信息提取任务
        schedule.every(30).minutes.do(self.run_extraction_task)

        # 每天上午9点执行邮件营销任务
        schedule.every().day.at("09:00").do(self.run_email_marketing_task)

        self.logger.info("定时任务设置完成")

    def run(self):
        """运行主程序"""
        self.logger.info("启动营销自动化系统")

        # 设置定时任务
        self.setup_schedule()

        # 执行一次初始化任务
        self.run_scraping_task()
        self.run_extraction_task()

        # 主循环
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="智能设计营销自动化系统")
    parser.add_argument("--config", default="config/project_config.json",
                       help="配置文件路径")
    parser.add_argument("--task", choices=["scraping", "extraction", "email", "all"],
                       default="all", help="执行特定任务")

    args = parser.parse_args()

    system = MarketingAutomationSystem(args.config)

    if args.task == "all":
        system.run()
    elif args.task == "scraping":
        system.run_scraping_task()
    elif args.task == "extraction":
        system.run_extraction_task()
    elif args.task == "email":
        system.run_email_marketing_task()


if __name__ == "__main__":
    main()
'''

        main_file = self.project_root / "src" / "main.py"
        with open(main_file, 'w', encoding='utf-8') as f:
            f.write(main_content)

        print(f"✓ 创建主程序: src/main.py")

    def create_requirements(self):
        """创建依赖文件"""
        basic_requirements = [
            "requests>=2.28.0",
            "beautifulsoup4>=4.11.0",
            "lxml>=4.9.0",
            "pandas>=1.5.0",
            "sqlite3",
            "schedule>=1.2.0",
            "smtplib",
            "email-validator>=2.0.0",
            "python-dotenv>=0.19.0"
        ]

        comprehensive_requirements = basic_requirements + [
            "scikit-learn>=1.1.0",
            "nltk>=3.7",
            "jieba>=0.42.1",
            "redis>=4.3.0",
            "celery>=5.2.0",
            "fastapi>=0.85.0",
            "uvicorn>=0.18.0",
            "pydantic>=1.10.0",
            "sqlalchemy>=1.4.0",
            "alembic>=1.8.0",
            "monitoring-client>=0.1.0"
        ]

        requirements = comprehensive_requirements if self.project_type == "comprehensive" else basic_requirements

        req_file = self.project_root / "requirements.txt"
        with open(req_file, 'w', encoding='utf-8') as f:
            for req in requirements:
                f.write(f"{req}\n")

        print(f"✓ 创建依赖文件: requirements.txt")

    def create_readme(self):
        """创建项目说明文档"""
        readme_content = f'''# {self.project_name}

智能设计营销自动化系统 - 专为智能化设计工程师打造的自动化营销工具

## 项目概述

本项目是一个自动化的营销系统，专门用于：
- 爬取政府采购、高校、国企、上市公司中标公告
- 提取联系人信息和项目需求
- 自动化邮件营销跟进

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置系统

编辑 `config/project_config.json` 文件，配置：
- 爬虫参数和目标网站
- 邮件SMTP设置
- 数据库配置
- 提取规则

### 3. 运行系统

```bash
# 运行完整系统
python src/main.py

# 执行特定任务
python src/main.py --task scraping
python src/main.py --task extraction
python src/main.py --task email
```

## 项目结构

```
{self.project_name}/
├── src/                    # 源代码目录
│   ├── scrapers/          # 爬虫模块
│   ├── extractors/        # 信息提取模块
│   ├── email_marketing/   # 邮件营销模块
│   └── utils/             # 工具模块
├── config/                # 配置文件
├── data/                  # 数据存储
├── logs/                  # 日志文件
├── tests/                 # 测试文件
└── scripts/               # 脚本工具
```

## 主要功能

### 1. 自动爬取
- 政府采购网站信息采集
- 多数据源支持和配置
- 反爬虫策略处理

### 2. 智能提取
- 联系人信息自动识别
- 项目需求关键词提取
- 数据清洗和标准化

### 3. 邮件营销
- 个性化邮件模板
- 批量邮件发送
- 发送效果跟踪

## 开发指南

### 添加新的数据源

1. 在 `src/scrapers/` 目录下创建新的爬虫文件
2. 继承基础爬虫类并实现特定逻辑
3. 在配置文件中添加数据源配置

### 自定义提取规则

1. 修改 `config/project_config.json` 中的提取规则
2. 在 `src/extractors/` 中实现自定义提取器
3. 使用测试数据验证提取效果

### 扩展邮件功能

1. 在 `templates/emails/` 中添加新的邮件模板
2. 修改 `src/email_marketing/` 中的发送逻辑
3. 配置SMTP服务器设置

## 注意事项

- 遵守网站robots.txt协议
- 合理控制爬取频率
- 确保邮件发送符合相关法规
- 定期备份重要数据

## 技术支持

如有问题请查看日志文件 `logs/` 或联系技术支持。

---

创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
项目类型: {self.project_type}
'''

        readme_file = self.project_root / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)

        print(f"✓ 创建说明文档: README.md")

    def initialize_project(self):
        """执行完整的项目初始化"""
        try:
            print(f"开始初始化项目: {self.project_name}")
            print(f"项目类型: {self.project_type}")
            print("-" * 50)

            self.create_project_structure()
            self.create_basic_config()
            self.create_main_module()
            self.create_requirements()
            self.create_readme()

            print("-" * 50)
            print(f"✅ 项目 '{self.project_name}' 初始化完成！")
            print()
            print("下一步操作:")
            print(f"1. cd {self.project_name}")
            print("2. pip install -r requirements.txt")
            print("3. 编辑 config/project_config.json 配置文件")
            print("4. 运行系统: python src/main.py")

        except Exception as e:
            print(f"❌ 项目初始化失败: {e}")
            sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="智能设计营销自动化项目初始化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python init_project.py --name "my-marketing-system"
  python init_project.py --name "advanced-system" --type comprehensive
  python init_project.py --name "test-project" --type basic
        """
    )

    parser.add_argument(
        "--name",
        required=True,
        help="项目名称"
    )

    parser.add_argument(
        "--type",
        choices=["basic", "comprehensive"],
        default="basic",
        help="项目类型 (默认: basic)"
    )

    args = parser.parse_args()

    try:
        initializer = ProjectInitializer(args.name, args.type)
        initializer.initialize_project()

    except InputValidationError as e:
        print(f"❌ 输入错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()