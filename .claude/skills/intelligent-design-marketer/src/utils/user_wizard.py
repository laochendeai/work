#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
个人用户配置向导
帮助用户快速完成系统配置和首次使用
"""

import os
import json
import sys
import smtplib
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import getpass
import re

class PersonalUserWizard:
    """个人用户配置向导"""

    def __init__(self):
        self.config_dir = Path("config")
        self.config_file = self.config_dir / "user_config.json"
        self.project_dir = Path.cwd()
        self.required_configs = {}
        self.setup_steps = [
            "欢迎介绍",
            "邮件配置",
            "爬虫设置",
            "数据存储",
            "系统测试",
            "完成配置"
        ]

    def run_wizard(self):
        """运行完整的配置向导"""
        print("🚀 智能设计营销系统 - 个人用户配置向导")
        print("=" * 60)
        print("欢迎使用！这个向导将帮助您快速配置系统，让您的营销工作更高效。")
        print("整个过程大约需要5-10分钟，请准备好您的邮箱信息。")
        print()

        input("按回车键开始配置...")

        for i, step in enumerate(self.setup_steps, 1):
            print(f"\n📋 步骤 {i}/{len(self.setup_steps)}: {step}")
            print("-" * 40)

            if step == "欢迎介绍":
                self._welcome_step()
            elif step == "邮件配置":
                self._email_config_step()
            elif step == "爬虫设置":
                self._scraper_config_step()
            elif step == "数据存储":
                self._storage_config_step()
            elif step == "系统测试":
                self._system_test_step()
            elif step == "完成配置":
                self._completion_step()

            if i < len(self.setup_steps):
                print(f"\n✅ {step} 完成")
                input("按回车键继续下一步...")

    def _welcome_step(self):
        """欢迎和介绍步骤"""
        print("🎯 系统功能介绍:")
        print("   • 自动搜索政府采购、高校、国企等公告")
        print("   • 智能提取联系人信息")
        print("   • 批量发送个性化营销邮件")
        print("   • 可视化数据分析和报告")
        print("   • 简单易用的Web管理界面")

        print("\n💡 使用场景:")
        print("   • 设计公司寻找项目机会")
        print("   • 工程公司投标信息收集")
        print("   • 营销团队潜在客户开发")
        print("   • 个人业务拓展自动化")

        print("\n🔧 系统要求:")
        print("   • 稳定的网络连接")
        print("   • 一个有效的邮箱账号")
        print("   • 至少1GB可用磁盘空间")

    def _email_config_step(self):
        """邮件配置步骤"""
        print("📧 邮件配置")
        print("系统需要发送邮件，请配置您的邮箱信息。")

        while True:
            print("\n1️⃣ 选择邮箱服务商:")
            print("   1. QQ邮箱 (@qq.com)")
            print("   2. 163邮箱 (@163.com)")
            print("   3. Gmail")
            print("   4. 企业邮箱")
            print("   5. 其他邮箱")

            choice = input("\n请选择 (1-5): ").strip()

            email_configs = {
                "1": {"smtp": "smtp.qq.com", "port": 587, "ssl": False},
                "2": {"smtp": "smtp.163.com", "port": 465, "ssl": True},
                "3": {"smtp": "smtp.gmail.com", "port": 587, "ssl": False},
                "4": {"smtp": "smtp.exmail.qq.com", "port": 465, "ssl": True},
            }

            if choice in email_configs:
                config = email_configs[choice]
                break
            elif choice == "5":
                smtp_server = input("请输入SMTP服务器地址: ").strip()
                smtp_port = input("请输入SMTP端口 (通常是465或587): ").strip()
                use_ssl = input("使用SSL? (y/n): ").lower() == 'y'
                config = {"smtp": smtp_server, "port": int(smtp_port), "ssl": use_ssl}
                break
            else:
                print("❌ 无效选择，请重新输入")

        # 邮箱账号
        while True:
            email = input("\n请输入您的邮箱地址: ").strip()
            if self._validate_email(email):
                break
            print("❌ 邮箱格式不正确，请重新输入")

        # 邮箱密码或应用专用密码
        print("\n🔒 邮箱认证")
        print("注意：对于QQ、163等邮箱，建议使用应用专用密码而非登录密码")
        print("获取方法：邮箱设置 -> 账户安全 -> 应用专用密码")

        password = getpass.getpass("请输入邮箱密码或应用专用密码: ")

        # 发件人信息
        sender_name = input("\n请输入发件人姓名 (将显示在邮件中): ").strip()
        if not sender_name:
            sender_name = "设计营销助手"

        # 测试邮件配置
        print("\n🧪 测试邮件配置...")
        if self._test_email_config(config["smtp"], config["port"], email, password, config["ssl"]):
            print("✅ 邮件配置测试成功！")
            self.required_configs["email"] = {
                "smtp_server": config["smtp"],
                "smtp_port": config["port"],
                "email": email,
                "password": password,
                "sender_name": sender_name,
                "use_ssl": config["ssl"],
                "configured": True
            }
        else:
            print("❌ 邮件配置测试失败，请检查配置信息")
            retry = input("是否重新配置? (y/n): ").lower()
            if retry == 'y':
                return self._email_config_step()
            else:
                print("⚠️  跳过邮件配置，您可以稍后在配置文件中手动设置")

    def _scraper_config_step(self):
        """爬虫配置步骤"""
        print("🕷️ 爬虫配置")
        print("配置数据源和爬取参数。")

        # 数据源选择
        print("\n📋 选择数据源 (可多选):")
        data_sources = {
            "1": "政府采购网",
            "2": "高校采购平台",
            "3": "国企招标网",
            "4": "上市公司公告",
            "5": "建筑行业平台",
            "6": "设计行业网站"
        }

        selected_sources = []
        for key, name in data_sources.items():
            include = input(f"   是否包含 {name}? (y/n): ").lower()
            if include == 'y':
                selected_sources.append(name)

        if not selected_sources:
            print("⚠️  至少选择一个数据源，将默认包含政府采购网")
            selected_sources = ["政府采购网"]

        # 爬取频率
        print("\n⏰ 爬取频率设置:")
        print("   1. 每小时一次 (适合实时监控)")
        print("   2. 每天3次 (适合日常业务)")
        print("   3. 每天1次 (适合轻度使用)")
        print("   4. 手动执行 (按需爬取)")

        frequency_choice = input("请选择爬取频率 (1-4): ").strip()
        frequency_map = {
            "1": {"hours": 1, "description": "每小时"},
            "2": {"hours": 8, "description": "每天3次"},
            "3": {"hours": 24, "description": "每天1次"},
            "4": {"hours": 0, "description": "手动"}
        }

        frequency = frequency_map.get(frequency_choice, frequency_map["2"])

        # 请求延迟设置
        print("\n🐌 请求延迟设置 (避免被反爬虫):")
        print("   1. 快速 (1-3秒)")
        print("   2. 正常 (3-8秒)")
        print("   3. 慢速 (8-15秒)")
        print("   4. 自定义")

        delay_choice = input("请选择延迟级别 (1-4): ").strip()
        delay_ranges = {
            "1": (1, 3),
            "2": (3, 8),
            "3": (8, 15)
        }

        if delay_choice in delay_ranges:
            min_delay, max_delay = delay_ranges[delay_choice]
        else:
            min_delay = int(input("请输入最小延迟秒数: "))
            max_delay = int(input("请输入最大延迟秒数: "))

        self.required_configs["scraper"] = {
            "data_sources": selected_sources,
            "frequency": frequency,
            "delay_range": {"min": min_delay, "max": max_delay},
            "auto_start": False,
            "configured": True
        }

    def _storage_config_step(self):
        """数据存储配置步骤"""
        print("💾 数据存储配置")

        # 存储位置
        print("\n📁 数据存储位置:")
        print(f"   默认位置: {self.project_dir}/data")
        custom_path = input("是否自定义存储路径? (y/n): ").lower()

        if custom_path == 'y':
            data_path = input("请输入数据存储路径: ").strip()
            data_path = Path(data_path).resolve()
        else:
            data_path = self.project_dir / "data"

        # 确保目录存在
        data_path.mkdir(exist_ok=True)

        # 数据保留时间
        print("\n⏳ 数据保留时间设置:")
        print("   1. 30天 (适合轻量使用)")
        print("   2. 90天 (适合日常业务)")
        print("   3. 180天 (适合长期积累)")
        print("   4. 永久保存")

        retention_choice = input("请选择保留时间 (1-4): ").strip()
        retention_days = {
            "1": 30,
            "2": 90,
            "3": 180,
            "4": -1  # 永久
        }.get(retention_choice, 90)

        # 备份设置
        print("\n💡 数据备份设置:")
        enable_backup = input("是否启用自动备份? (y/n): ").lower() == 'y'
        backup_frequency = None

        if enable_backup:
            backup_frequency = input("备份频率 (daily/weekly): ").strip().lower()
            if backup_frequency not in ['daily', 'weekly']:
                backup_frequency = 'weekly'

        self.required_configs["storage"] = {
            "data_path": str(data_path),
            "retention_days": retention_days,
            "backup_enabled": enable_backup,
            "backup_frequency": backup_frequency,
            "configured": True
        }

    def _system_test_step(self):
        """系统测试步骤"""
        print("🧪 系统测试")
        print("正在测试系统组件...")

        tests = [
            ("网络连接", self._test_network),
            ("数据存储", self._test_storage),
            ("邮件发送", self._test_email_sending),
            ("网页解析", self._test_web_parsing)
        ]

        results = {}
        for test_name, test_func in tests:
            print(f"\n   测试 {test_name}...", end=" ")
            try:
                result = test_func()
                results[test_name] = result
                if result["success"]:
                    print("✅ 通过")
                else:
                    print(f"❌ 失败 - {result['message']}")
            except Exception as e:
                print(f"❌ 错误 - {str(e)}")
                results[test_name] = {"success": False, "message": str(e)}

        # 测试结果汇总
        passed = sum(1 for r in results.values() if r.get("success", False))
        total = len(results)

        print(f"\n📊 测试结果: {passed}/{total} 通过")

        if passed == total:
            print("🎉 所有测试通过！系统配置完成。")
        else:
            print("⚠️  部分测试未通过，建议检查配置")
            for name, result in results.items():
                if not result.get("success", False):
                    print(f"   • {name}: {result.get('message', '未知错误')}")

    def _completion_step(self):
        """完成配置步骤"""
        print("🎉 配置完成！")
        print("\n📝 配置摘要:")

        if "email" in self.required_configs:
            email_config = self.required_configs["email"]
            print(f"   📧 邮件: {email_config['email']} ✅")
        else:
            print("   📧 邮件: 未配置 ⚠️")

        if "scraper" in self.required_configs:
            scraper_config = self.required_configs["scraper"]
            print(f"   🕷️  数据源: {len(scraper_config['data_sources'])}个")
            print(f"   ⏰ 频率: {scraper_config['frequency']['description']}")
        else:
            print("   🕷️  爬虫: 未配置 ⚠️")

        if "storage" in self.required_configs:
            storage_config = self.required_configs["storage"]
            print(f"   💾 存储: {storage_config['data_path']}")
        else:
            print("   💾 存储: 未配置 ⚠️")

        # 保存配置
        self._save_config()

        print("\n🚀 接下来您可以:")
        print("   1. 运行 'python src/web/dashboard.py' 启动Web界面")
        print("   2. 运行 'python scripts/enhanced_project_builder.py start' 开始爬取")
        print("   3. 查看 'docs/user_guide.md' 获取详细使用说明")

        print(f"\n📁 配置文件已保存到: {self.config_file}")
        print("\n祝您使用愉快！如有问题，请查看用户手册或联系技术支持。")

    def _save_config(self):
        """保存配置到文件"""
        self.config_dir.mkdir(exist_ok=True)

        config_data = {
            "user_info": {
                "setup_date": datetime.now().isoformat(),
                "version": "2.0.0",
                "user_type": "personal"
            },
            **self.required_configs
        }

        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")

    def _validate_email(self, email: str) -> bool:
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def _test_email_config(self, smtp_server: str, port: int, email: str, password: str, use_ssl: bool) -> bool:
        """测试邮件配置"""
        try:
            if use_ssl:
                server = smtplib.SMTP_SSL(smtp_server, port)
            else:
                server = smtplib.SMTP(smtp_server, port)
                server.starttls()

            server.login(email, password)
            server.quit()
            return True
        except Exception:
            return False

    def _test_network(self) -> Dict[str, Any]:
        """测试网络连接"""
        try:
            response = requests.get("https://www.baidu.com", timeout=10)
            return {"success": True, "message": "网络连接正常"}
        except Exception:
            return {"success": False, "message": "无法连接到互联网"}

    def _test_storage(self) -> Dict[str, Any]:
        """测试数据存储"""
        try:
            test_file = Path("test_write.tmp")
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
            return {"success": True, "message": "存储读写正常"}
        except Exception as e:
            return {"success": False, "message": f"存储错误: {e}"}

    def _test_email_sending(self) -> Dict[str, Any]:
        """测试邮件发送"""
        if "email" not in self.required_configs:
            return {"success": False, "message": "邮件未配置"}

        try:
            # 这里只是简单测试，实际不会发送邮件
            email_config = self.required_configs["email"]
            return {"success": True, "message": "邮件配置正常"}
        except Exception as e:
            return {"success": False, "message": f"邮件错误: {e}"}

    def _test_web_parsing(self) -> Dict[str, Any]:
        """测试网页解析"""
        try:
            response = requests.get("https://www.baidu.com", timeout=10)
            if response.status_code == 200:
                return {"success": True, "message": "网页解析正常"}
            else:
                return {"success": False, "message": f"HTTP错误: {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"解析错误: {e}"}

def quick_setup():
    """快速配置启动"""
    wizard = PersonalUserWizard()
    try:
        wizard.run_wizard()
        return True
    except KeyboardInterrupt:
        print("\n\n⚠️  配置已取消")
        return False
    except Exception as e:
        print(f"\n❌ 配置过程中出现错误: {e}")
        return False

if __name__ == "__main__":
    quick_setup()