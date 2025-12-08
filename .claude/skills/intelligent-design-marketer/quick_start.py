#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能设计营销系统 - 个人用户快速启动脚本
一键启动所有功能，简化个人用户使用体验
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Optional
import json
import argparse

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.utils.user_friendly_errors import handle_user_errors, show_user_error
    from src.utils.config_loader import ConfigLoader
    from src.utils.logger import setup_logger
except ImportError:
    print("⚠️  模块导入失败，请确保在项目根目录运行")
    sys.exit(1)

class QuickStartManager:
    """快速启动管理器"""

    def __init__(self):
        self.processes = {}
        self.config_file = project_root / "config" / "user_config.json"
        self.logger = None
        self.setup_logging()

    def setup_logging(self):
        """设置日志"""
        try:
            log_dir = project_root / "logs"
            log_dir.mkdir(exist_ok=True)
            self.logger = setup_logger("quick_start", log_dir / "quick_start.log")
        except Exception:
            self.logger = None

    def check_requirements(self) -> bool:
        """检查系统要求"""
        print("🔍 检查系统要求...")

        # 检查Python版本
        if sys.version_info < (3, 7):
            print("❌ 需要Python 3.7或更高版本")
            return False

        # 检查必需的包
        required_packages = [
            'requests', 'beautifulsoup4', 'smtplib', 'streamlit',
            'sqlite3', 'pandas', 'plotly'
        ]

        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            print(f"❌ 缺少必需的包: {', '.join(missing_packages)}")
            print("请运行: pip install -r requirements.txt")
            return False

        # 检查配置文件
        if not self.config_file.exists():
            print("⚠️  配置文件不存在，将启动配置向导")
            return self._run_setup_wizard()

        print("✅ 系统要求检查通过")
        return True

    def _run_setup_wizard(self) -> bool:
        """运行配置向导"""
        try:
            from src.utils.user_wizard import quick_setup
            print("🚀 启动配置向导...")
            return quick_setup()
        except Exception as e:
            error_info = handle_user_errors(e, "启动配置向导")
            show_user_error(error_info)
            return False

    def start_services(self, services: List[str] = None) -> bool:
        """启动服务"""
        if services is None:
            services = ['web', 'scraper', 'monitor']

        print(f"🚀 启动服务: {', '.join(services)}")

        service_methods = {
            'web': self._start_web_interface,
            'scraper': self._start_scraper,
            'monitor': self._start_monitoring,
            'api': self._start_api_service
        }

        success_count = 0
        for service in services:
            if service in service_methods:
                try:
                    if service_methods[service]():
                        success_count += 1
                        print(f"✅ {service} 服务启动成功")
                    else:
                        print(f"❌ {service} 服务启动失败")
                except Exception as e:
                    error_info = handle_user_errors(e, f"启动{service}服务")
                    show_user_error(error_info)
            else:
                print(f"⚠️  未知服务: {service}")

        print(f"📊 服务启动完成: {success_count}/{len(services)}")
        return success_count > 0

    def _start_web_interface(self) -> bool:
        """启动Web界面"""
        try:
            web_file = project_root / "src" / "web" / "dashboard.py"
            if not web_file.exists():
                print("❌ Web界面文件不存在")
                return False

            # 使用streamlit启动
            cmd = [sys.executable, "-m", "streamlit", "run", str(web_file), "--server.port=8501"]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=project_root
            )
            self.processes['web'] = process

            # 等待启动
            time.sleep(3)
            if process.poll() is None:
                print("🌐 Web界面: http://localhost:8501")
                return True
            else:
                print("❌ Web界面启动失败")
                return False

        except Exception as e:
            print(f"❌ 启动Web界面失败: {e}")
            return False

    def _start_scraper(self) -> bool:
        """启动爬虫服务"""
        try:
            scraper_file = project_root / "scripts" / "create_scraper.py"
            if not scraper_file.exists():
                print("❌ 爬虫脚本不存在")
                return False

            cmd = [sys.executable, str(scraper_file), "--daemon"]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=project_root
            )
            self.processes['scraper'] = process

            time.sleep(2)
            if process.poll() is None:
                print("🕷️  爬虫服务启动成功")
                return True
            else:
                print("❌ 爬虫服务启动失败")
                return False

        except Exception as e:
            print(f"❌ 启动爬虫服务失败: {e}")
            return False

    def _start_monitoring(self) -> bool:
        """启动监控服务"""
        try:
            monitoring_file = project_root / "src" / "monitoring" / "metrics.py"
            if not monitoring_file.exists():
                print("⚠️  监控服务文件不存在，跳过")
                return True  # 不是必需的

            cmd = [sys.executable, str(monitoring_file)]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=project_root
            )
            self.processes['monitor'] = process

            time.sleep(2)
            if process.poll() is None:
                print("📊 监控服务启动成功")
                return True
            else:
                print("❌ 监控服务启动失败")
                return False

        except Exception as e:
            print(f"❌ 启动监控服务失败: {e}")
            return False

    def _start_api_service(self) -> bool:
        """启动API服务"""
        try:
            # 这里可以添加API服务的启动逻辑
            print("🔌 API服务暂未实现")
            return True
        except Exception as e:
            print(f"❌ 启动API服务失败: {e}")
            return False

    def stop_services(self):
        """停止所有服务"""
        print("🛑 停止服务...")

        for name, process in self.processes.items():
            try:
                if process.poll() is None:  # 进程还在运行
                    print(f"   停止 {name} 服务...")
                    process.terminate()
                    # 等待进程结束
                    process.wait(timeout=5)
                    print(f"✅ {name} 服务已停止")
                else:
                    print(f"ℹ️  {name} 服务已经停止")
            except subprocess.TimeoutExpired:
                print(f"⚠️  强制停止 {name} 服务...")
                process.kill()
            except Exception as e:
                print(f"❌ 停止 {name} 服务失败: {e}")

        self.processes.clear()

    def show_status(self):
        """显示服务状态"""
        print("📊 服务状态:")
        print("-" * 30)

        if not self.processes:
            print("   没有运行的服务")
            return

        for name, process in self.processes.items():
            if process.poll() is None:
                print(f"   ✅ {name}: 运行中")
            else:
                print(f"   ❌ {name}: 已停止")

        print()
        if 'web' in self.processes and self.processes['web'].poll() is None:
            print("🌐 Web界面: http://localhost:8501")

    def run_interactive_mode(self):
        """运行交互模式"""
        print("\n🎮 交互模式")
        print("输入 'help' 查看可用命令，输入 'quit' 退出")

        while True:
            try:
                command = input("\n> ").strip().lower()

                if command == 'quit' or command == 'exit':
                    break
                elif command == 'help':
                    self._show_help()
                elif command == 'status':
                    self.show_status()
                elif command == 'start':
                    self.start_services()
                elif command.startswith('start '):
                    services = command.split()[1:]
                    self.start_services(services)
                elif command == 'stop':
                    self.stop_services()
                elif command == 'restart':
                    self.stop_services()
                    time.sleep(2)
                    self.start_services()
                elif command == 'config':
                    self._run_setup_wizard()
                elif command == 'logs':
                    self._show_logs()
                elif command == '':
                    continue
                else:
                    print(f"❌ 未知命令: {command}，输入 'help' 查看帮助")

            except KeyboardInterrupt:
                break
            except EOFError:
                break
            except Exception as e:
                error_info = handle_user_errors(e, "执行命令")
                show_user_error(error_info)

        print("\n👋 再见！")

    def _show_help(self):
        """显示帮助信息"""
        print("\n📚 可用命令:")
        print("   help     - 显示此帮助信息")
        print("   status   - 显示服务状态")
        print("   start    - 启动所有服务")
        print("   start <service1> <service2> - 启动指定服务")
        print("   stop     - 停止所有服务")
        print("   restart  - 重启所有服务")
        print("   config   - 重新配置")
        print("   logs     - 查看日志")
        print("   quit     - 退出程序")

        print("\n📋 可用服务:")
        print("   web      - Web管理界面")
        print("   scraper  - 数据爬取服务")
        print("   monitor  - 监控服务")
        print("   api      - API服务")

    def _show_logs(self):
        """显示日志"""
        log_dir = project_root / "logs"
        if not log_dir.exists():
            print("📄 日志目录不存在")
            return

        log_files = list(log_dir.glob("*.log"))
        if not log_files:
            print("📄 没有日志文件")
            return

        print("\n📄 日志文件:")
        for log_file in log_files:
            size = log_file.stat().st_size
            print(f"   {log_file.name} ({size} bytes)")

        log_name = input("\n请输入要查看的日志文件名 (回车取消): ").strip()
        if log_name and (log_dir / log_name).exists():
            try:
                with open(log_dir / log_name, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    print(f"\n📄 {log_name} (最后20行):")
                    for line in lines[-20:]:
                        print(line.rstrip())
            except Exception as e:
                print(f"❌ 读取日志失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="智能设计营销系统 - 快速启动")
    parser.add_argument("--services", nargs="+", default=["web", "scraper"],
                       help="要启动的服务列表")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="启动交互模式")
    parser.add_argument("--daemon", "-d", action="store_true",
                       help="后台运行模式")
    parser.add_argument("--config", action="store_true",
                       help="运行配置向导")
    parser.add_argument("--status", action="store_true",
                       help="显示服务状态")

    args = parser.parse_args()

    manager = QuickStartManager()

    # 注册信号处理器
    def signal_handler(signum, frame):
        print(f"\n收到信号 {signum}，正在停止服务...")
        manager.stop_services()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 检查系统要求
        if not manager.check_requirements():
            sys.exit(1)

        # 处理不同模式
        if args.config:
            manager._run_setup_wizard()
            return

        if args.status:
            manager.show_status()
            return

        if args.interactive:
            manager.start_services(args.services)
            manager.run_interactive_mode()
        elif args.daemon:
            manager.start_services(args.services)
            print("🚀 服务已在后台启动")
            print("使用 --status 查看状态")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        else:
            # 默认模式：启动服务并显示状态
            manager.start_services(args.services)
            manager.show_status()
            print("\n按 Ctrl+C 停止服务，或使用 --interactive 进入交互模式")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

    except Exception as e:
        error_info = handle_user_errors(e, "程序启动")
        show_user_error(error_info)
        sys.exit(1)
    finally:
        manager.stop_services()

if __name__ == "__main__":
    main()