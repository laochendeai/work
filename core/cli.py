#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能设计营销系统 - CLI 入口

保持 `python main.py` 的用法不变，但将命令行解析/分发从 main.py 抽离。
"""

import argparse
import asyncio
import os
import sys
from typing import Optional

from core.system import MarketingSystem


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="智能设计营销系统")
    parser.add_argument("--scrape", action="store_true", help="运行数据爬虫")
    parser.add_argument("--extract", action="store_true", help="提取联系人信息")
    parser.add_argument("--email", action="store_true", help="发送邮件")
    parser.add_argument("--web", action="store_true", help="启动Web界面")
    parser.add_argument("--config", action="store_true", help="系统配置")
    parser.add_argument("--status", action="store_true", help="显示系统状态")
    parser.add_argument("--export-structured", action="store_true", help="导出结构化JSON联系人")
    parser.add_argument("--db-clean", action="store_true", help="清理数据库（保留策略+去重+VACUUM）")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    parser.add_argument("--queue", action="store_true", help="运行队列worker")
    parser.add_argument("--queue-once", action="store_true", help="运行队列worker（队列空后退出）")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """CLI 主入口（返回退出码）。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    system = MarketingSystem()

    queue_env = os.getenv("QUEUE_MODE", "0") == "1"
    queue_once_env = os.getenv("QUEUE_ONCE", "0") == "1"
    no_args = (argv is None and len(sys.argv) == 1) or (argv is not None and len(argv) == 0)
    interactive_mode = args.interactive or (no_args and not queue_env and sys.stdin.isatty())

    if interactive_mode:
        # 交互模式
        print("🚀 智能设计营销系统 - 交互模式")
        print("=" * 50)

        while True:
            print("\n📋 可用操作:")
            print("1. 🕷️  运行爬虫")
            print("2. 👥 提取联系人")
            print("3. 📧 发送邮件")
            print("4. 🌐 Web界面")
            print("5. ⚙️ 系统配置")
            print("6. 📊 系统状态")
            print("7. 📄 导出结构化联系人")
            print("8. 🧹 清理数据库")
            print("9. 🚪 退出")

            choice = input("\n请选择 (1-9): ").strip()

            try:
                if choice == "1":
                    system.run_scraper()
                elif choice == "2":
                    system.run_extractor()
                elif choice == "3":
                    system.run_emailer()
                elif choice == "4":
                    system.run_web()
                elif choice == "5":
                    system.run_config()
                elif choice == "6":
                    system.show_status()
                elif choice == "7":
                    system.export_structured_contacts()
                elif choice == "8":
                    system.clean_database()
                elif choice == "9":
                    print("👋 再见！")
                    break
                else:
                    print("❌ 无效选择")
            except KeyboardInterrupt:
                print("\n👋 程序已退出")
                break
            except Exception as e:
                print(f"❌ 操作失败: {e}")

        return 0

    # 命令行模式
    # 队列 worker 为长驻服务：单独运行
    queue_once = bool(args.queue_once or queue_once_env)
    if args.queue or queue_once or queue_env:
        if queue_once:
            print("🚚 启动队列 worker（队列空后退出）...")
        else:
            print("🚚 启动队列 worker 服务...")
        try:
            asyncio.run(system._run_workers(persistent=not queue_once))
        except KeyboardInterrupt:
            print("\n👋 队列服务已停止")
        return 0

    # Web/UI 为长驻服务：单独运行
    if args.web:
        system.run_web()
        return 0

    # 交互式配置：单独运行（避免和其它动作混用导致体验混乱）
    if args.config:
        system.run_config()
        return 0

    # 允许组合执行（例如：--scrape --extract --export-structured --db-clean）
    ran_any = False

    if args.scrape:
        ran_any = True
        system.run_scraper()

    if args.extract:
        ran_any = True
        system.run_extractor()

    if args.export_structured:
        ran_any = True
        system.export_structured_contacts()

    if args.email:
        ran_any = True
        system.run_emailer()

    if args.db_clean:
        ran_any = True
        system.clean_database()

    if args.status:
        ran_any = True
        system.show_status()

    if not ran_any:
        parser.print_help()

    return 0
