#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统健康检查工具
专为个人用户设计，自动诊断常见问题并提供解决方案
"""

import os
import sys
import json
import sqlite3
import smtplib
import requests
import subprocess
import time
import psutil
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime, timedelta

class SystemHealthChecker:
    """系统健康检查器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.issues = []
        self.warnings = []
        self.suggestions = []
        self.check_results = {}

    def run_full_check(self) -> Dict[str, Any]:
        """运行完整的健康检查"""
        print("🔍 开始系统健康检查...")
        print("=" * 60)

        checks = [
            ("环境检查", self._check_environment),
            ("配置文件", self._check_configuration),
            ("网络连接", self._check_network),
            ("数据库", self._check_database),
            ("邮件服务", self._check_email_service),
            ("磁盘空间", self._check_disk_space),
            ("系统资源", self._check_system_resources),
            ("文件权限", self._check_file_permissions),
            ("依赖包", self._check_dependencies),
            ("日志文件", self._check_log_files)
        ]

        for check_name, check_func in checks:
            print(f"\n🔍 检查 {check_name}...", end=" ")
            try:
                result = check_func()
                self.check_results[check_name] = result
                status = "✅ 通过" if result.get("status") == "ok" else "❌ 问题"
                print(f"{status}")

                if result.get("issues"):
                    for issue in result["issues"]:
                        self.issues.append(f"{check_name}: {issue}")

                if result.get("warnings"):
                    for warning in result["warnings"]:
                        self.warnings.append(f"{check_name}: {warning}")

                if result.get("suggestions"):
                    for suggestion in result["suggestions"]:
                        self.suggestions.append(f"{check_name}: {suggestion}")

            except Exception as e:
                print(f"❌ 错误")
                self.issues.append(f"{check_name}: 检查过程中出错 - {str(e)}")
                self.check_results[check_name] = {
                    "status": "error",
                    "message": str(e)
                }

        return self._generate_report()

    def _check_environment(self) -> Dict[str, Any]:
        """检查运行环境"""
        result = {"status": "ok", "issues": [], "warnings": [], "suggestions": []}

        # Python版本检查
        if sys.version_info < (3, 7):
            result["status"] = "error"
            result["issues"].append(f"Python版本过低: {sys.version_info}，需要3.7+")
        elif sys.version_info < (3, 8):
            result["warnings"].append("建议升级到Python 3.8+以获得更好性能")

        # 操作系统检查
        if os.name == 'nt':
            result["warnings"].append("Windows系统可能需要额外配置")

        # 工作目录检查
        if "intelligent-design-marketer" not in str(self.project_root):
            result["issues"].append("未在正确的项目目录中运行")

        return result

    def _check_configuration(self) -> Dict[str, Any]:
        """检查配置文件"""
        result = {"status": "ok", "issues": [], "warnings": [], "suggestions": []}

        config_files = [
            "config/user_config.json",
            "config/project_config.json",
            "config/email_config.json"
        ]

        missing_files = []
        for config_file in config_files:
            file_path = self.project_root / config_file
            if not file_path.exists():
                missing_files.append(config_file)

        if missing_files:
            result["status"] = "warning"
            result["issues"].append(f"缺少配置文件: {', '.join(missing_files)}")
            result["suggestions"].append("运行配置向导: python quick_start.py --config")

        # 检查配置文件格式
        user_config = self.project_root / "config/user_config.json"
        if user_config.exists():
            try:
                with open(user_config, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 检查必需的配置项
                required_keys = ["email", "scraper", "storage"]
                for key in required_keys:
                    if key not in config:
                        result["warnings"].append(f"配置文件缺少 {key} 部分")

            except json.JSONDecodeError as e:
                result["status"] = "error"
                result["issues"].append(f"配置文件格式错误: {e}")

        return result

    def _check_network(self) -> Dict[str, Any]:
        """检查网络连接"""
        result = {"status": "ok", "issues": [], "warnings": [], "suggestions": []}

        test_urls = [
            ("百度", "https://www.baidu.com"),
            ("GitHub", "https://github.com"),
            ("政府采购网", "http://www.ccgp.gov.cn")
        ]

        failed_sites = []
        for name, url in test_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    failed_sites.append(f"{name} (HTTP {response.status_code})")
            except Exception:
                failed_sites.append(name)

        if failed_sites:
            result["status"] = "warning"
            result["issues"].append(f"无法访问: {', '.join(failed_sites)}")
            result["suggestions"].append("检查网络连接和防火墙设置")

        return result

    def _check_database(self) -> Dict[str, Any]:
        """检查数据库"""
        result = {"status": "ok", "issues": [], "warnings": [], "suggestions": []}

        db_files = list(self.project_root.glob("**/*.db"))

        if not db_files:
            result["warnings"].append("未找到数据库文件")
            result["suggestions"].append("首次运行时会自动创建数据库")
            return result

        for db_file in db_files:
            try:
                conn = sqlite3.connect(str(db_file))
                cursor = conn.cursor()

                # 检查数据库完整性
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()[0]

                if integrity_result != "ok":
                    result["status"] = "error"
                    result["issues"].append(f"数据库 {db_file.name} 完整性检查失败")

                # 检查数据库大小
                db_size = db_file.stat().st_size / (1024 * 1024)  # MB
                if db_size > 100:  # 超过100MB
                    result["warnings"].append(f"数据库 {db_file.name} 较大 ({db_size:.1f}MB)")
                    result["suggestions"].append("考虑清理旧数据或启用数据压缩")

                conn.close()

            except Exception as e:
                result["status"] = "error"
                result["issues"].append(f"数据库 {db_file.name} 检查失败: {e}")

        return result

    def _check_email_service(self) -> Dict[str, Any]:
        """检查邮件服务"""
        result = {"status": "ok", "issues": [], "warnings": [], "suggestions": []}

        user_config = self.project_root / "config/user_config.json"
        if not user_config.exists():
            result["warnings"].append("邮件服务未配置")
            return result

        try:
            with open(user_config, 'r', encoding='utf-8') as f:
                config = json.load(f)

            email_config = config.get("email", {})

            # 检查必需的配置项
            required_fields = ["smtp_server", "smtp_port", "email", "password"]
            missing_fields = [field for field in required_fields if not email_config.get(field)]

            if missing_fields:
                result["status"] = "warning"
                result["issues"].append(f"邮件配置缺少: {', '.join(missing_fields)}")
                result["suggestions"].append("完成邮件配置: python quick_start.py --config")
                return result

            # 测试SMTP连接
            try:
                server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
                server.starttls()
                server.login(email_config["email"], email_config["password"])
                server.quit()
                result["status"] = "ok"
            except Exception as e:
                result["status"] = "error"
                result["issues"].append(f"SMTP连接失败: {e}")
                result["suggestions"].append("检查邮箱配置和网络连接")

        except Exception as e:
            result["status"] = "error"
            result["issues"].append(f"邮件配置检查失败: {e}")

        return result

    def _check_disk_space(self) -> Dict[str, Any]:
        """检查磁盘空间"""
        result = {"status": "ok", "issues": [], "warnings": [], "suggestions": []}

        try:
            disk_usage = psutil.disk_usage(str(self.project_root))
            free_space_gb = disk_usage.free / (1024**3)
            total_space_gb = disk_usage.total / (1024**3)
            usage_percent = (disk_usage.used / disk_usage.total) * 100

            if free_space_gb < 1:  # 少于1GB
                result["status"] = "error"
                result["issues"].append(f"磁盘空间不足: 仅剩 {free_space_gb:.1f}GB")
            elif free_space_gb < 5:  # 少于5GB
                result["status"] = "warning"
                result["warnings"].append(f"磁盘空间较少: 剩余 {free_space_gb:.1f}GB")
                result["suggestions"].append("清理不必要的文件")

            if usage_percent > 90:
                result["warnings"].append(f"磁盘使用率过高: {usage_percent:.1f}%")

        except Exception as e:
            result["status"] = "error"
            result["issues"].append(f"磁盘空间检查失败: {e}")

        return result

    def _check_system_resources(self) -> Dict[str, Any]:
        """检查系统资源"""
        result = {"status": "ok", "issues": [], "warnings": [], "suggestions": []}

        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 80:
                result["warnings"].append(f"CPU使用率较高: {cpu_percent:.1f}%")

            # 内存使用率
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                result["warnings"].append(f"内存使用率较高: {memory.percent:.1f}%")
                result["suggestions"].append("关闭不必要的程序")

            # 检查是否有足够的内存用于爬虫
            available_gb = memory.available / (1024**3)
            if available_gb < 0.5:  # 少于512MB
                result["issues"].append(f"可用内存不足: {available_gb:.1f}GB")

        except Exception as e:
            result["status"] = "error"
            result["issues"].append(f"系统资源检查失败: {e}")

        return result

    def _check_file_permissions(self) -> Dict[str, Any]:
        """检查文件权限"""
        result = {"status": "ok", "issues": [], "warnings": [], "suggestions": []}

        important_dirs = [
            "config",
            "data",
            "logs",
            "src"
        ]

        for dir_name in important_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                # 检查写权限
                test_file = dir_path / "permission_test.tmp"
                try:
                    test_file.write_text("test")
                    test_file.unlink()
                except PermissionError:
                    result["status"] = "error"
                    result["issues"].append(f"目录 {dir_name} 没有写权限")
                except Exception as e:
                    result["warnings"].append(f"目录 {dir_name} 权限检查异常: {e}")
            else:
                result["suggestions"].append(f"创建目录: {dir_name}")

        return result

    def _check_dependencies(self) -> Dict[str, Any]:
        """检查依赖包"""
        result = {"status": "ok", "issues": [], "warnings": [], "suggestions": []}

        required_packages = [
            'requests',
            'beautifulsoup4',
            'lxml',
            'pandas',
            'plotly',
            'streamlit',
            'psutil',
            'smtplib'
        ]

        missing_packages = []
        outdated_packages = []

        for package in required_packages:
            try:
                if package == 'smtplib':
                    import smtplib
                else:
                    __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            result["status"] = "error"
            result["issues"].append(f"缺少依赖包: {', '.join(missing_packages)}")
            result["suggestions"].append("运行: pip install -r requirements.txt")

        # 检查pip版本
        try:
            pip_version = subprocess.check_output([sys.executable, "-m", "pip", "--version"],
                                                text=True)
            if "old" in pip_version.lower() or "out" in pip_version.lower():
                result["warnings"].append("建议升级pip版本")
        except:
            pass

        return result

    def _check_log_files(self) -> Dict[str, Any]:
        """检查日志文件"""
        result = {"status": "ok", "issues": [], "warnings": [], "suggestions": []}

        log_dir = self.project_root / "logs"
        if not log_dir.exists():
            result["suggestions"].append("创建日志目录")
            return result

        log_files = list(log_dir.glob("*.log"))

        if not log_files:
            result["warnings"].append("没有日志文件")
            return result

        # 检查日志文件大小
        large_logs = []
        for log_file in log_files:
            size_mb = log_file.stat().st_size / (1024 * 1024)
            if size_mb > 50:  # 超过50MB
                large_logs.append(f"{log_file.name} ({size_mb:.1f}MB)")

        if large_logs:
            result["warnings"].append(f"日志文件过大: {', '.join(large_logs)}")
            result["suggestions"].append("清理或轮转日志文件")

        # 检查最近的错误日志
        recent_errors = 0
        one_day_ago = datetime.now() - timedelta(days=1)

        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if 'ERROR' in line or 'error' in line:
                            # 简单的时间检查
                            if '2024' in line:  # 假设是2024年的日志
                                recent_errors += 1
            except:
                pass

        if recent_errors > 10:
            result["warnings"].append(f"最近24小时有 {recent_errors} 个错误")
            result["suggestions"].append("检查错误日志并解决问题")

        return result

    def _generate_report(self) -> Dict[str, Any]:
        """生成检查报告"""
        total_checks = len(self.check_results)
        ok_checks = sum(1 for result in self.check_results.values()
                       if result.get("status") == "ok")
        error_count = len(self.issues)
        warning_count = len(self.warnings)

        overall_status = "excellent"
        if error_count > 0:
            overall_status = "error"
        elif warning_count > 3:
            overall_status = "warning"
        elif warning_count > 0:
            overall_status = "good"

        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "summary": {
                "total_checks": total_checks,
                "passed_checks": ok_checks,
                "issues": error_count,
                "warnings": warning_count
            },
            "details": self.check_results,
            "issues": self.issues,
            "warnings": self.warnings,
            "suggestions": self.suggestions
        }

        return report

    def display_report(self, report: Dict[str, Any]):
        """显示检查报告"""
        print(f"\n📊 系统健康检查报告")
        print("=" * 60)
        print(f"检查时间: {report['timestamp'][:19]}")

        # 状态显示
        status_emoji = {
            "excellent": "🟢",
            "good": "🟡",
            "warning": "🟠",
            "error": "🔴"
        }

        status_text = {
            "excellent": "优秀",
            "good": "良好",
            "warning": "需要关注",
            "error": "存在问题"
        }

        print(f"\n{status_emoji[report['overall_status']]} 整体状态: {status_text[report['overall_status']]}")

        # 汇总信息
        summary = report["summary"]
        print(f"\n📈 汇总信息:")
        print(f"   检查项目: {summary['total_checks']}")
        print(f"   通过检查: {summary['passed_checks']}")
        print(f"   发现问题: {summary['issues']}")
        print(f"   警告信息: {summary['warnings']}")

        # 问题列表
        if report["issues"]:
            print(f"\n❌ 发现的问题:")
            for i, issue in enumerate(report["issues"], 1):
                print(f"   {i}. {issue}")

        # 警告列表
        if report["warnings"]:
            print(f"\n⚠️  警告信息:")
            for i, warning in enumerate(report["warnings"], 1):
                print(f"   {i}. {warning}")

        # 建议列表
        if report["suggestions"]:
            print(f"\n💡 改进建议:")
            for i, suggestion in enumerate(report["suggestions"], 1):
                print(f"   {i}. {suggestion}")

        # 详细结果
        print(f"\n🔍 详细检查结果:")
        for check_name, result in report["details"].items():
            status = result.get("status", "unknown")
            status_emoji = {
                "ok": "✅",
                "warning": "⚠️",
                "error": "❌"
            }.get(status, "❓")

            print(f"   {status_emoji} {check_name}: {status}")
            if result.get("message"):
                print(f"      {result['message']}")

    def save_report(self, report: Dict[str, Any], filename: str = None):
        """保存报告到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"health_check_{timestamp}.json"

        report_file = self.project_root / "logs" / filename
        report_file.parent.mkdir(exist_ok=True)

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\n📄 报告已保存到: {report_file}")
        except Exception as e:
            print(f"\n❌ 保存报告失败: {e}")

    def quick_fix(self, report: Dict[str, Any]) -> bool:
        """尝试自动修复一些常见问题"""
        print("\n🔧 尝试自动修复...")

        fixes_applied = []

        # 创建缺失的目录
        dirs_to_create = ["config", "data", "logs"]
        for dir_name in dirs_to_create:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                try:
                    dir_path.mkdir(exist_ok=True)
                    fixes_applied.append(f"创建目录: {dir_name}")
                except Exception as e:
                    print(f"❌ 无法创建目录 {dir_name}: {e}")

        # 清理过大的日志文件
        log_dir = self.project_root / "logs"
        if log_dir.exists():
            for log_file in log_dir.glob("*.log"):
                size_mb = log_file.stat().st_size / (1024 * 1024)
                if size_mb > 50:
                    try:
                        # 备份并清空大日志文件
                        backup_file = log_file.with_suffix(f".{datetime.now().strftime('%Y%m%d')}.bak")
                        log_file.rename(backup_file)
                        fixes_applied.append(f"备份大日志文件: {log_file.name}")
                    except Exception as e:
                        print(f"❌ 无法处理日志文件 {log_file.name}: {e}")

        if fixes_applied:
            print("\n✅ 应用的修复:")
            for fix in fixes_applied:
                print(f"   • {fix}")
            return True
        else:
            print("\nℹ️  没有发现可自动修复的问题")
            return False

def main():
    """主函数"""
    print("🏥 智能设计营销系统 - 健康检查工具")
    print("=" * 60)

    checker = SystemHealthChecker()

    # 运行完整检查
    report = checker.run_full_check()

    # 显示报告
    checker.display_report(report)

    # 保存报告
    checker.save_report(report)

    # 尝试自动修复
    if report["overall_status"] in ["warning", "error"]:
        auto_fix = input("\n🔧 是否尝试自动修复问题? (y/n): ").lower()
        if auto_fix == 'y':
            checker.quick_fix(report)

    print(f"\n🏁 检查完成！")
    print("如需详细信息，请查看保存的报告文件")

if __name__ == "__main__":
    main()