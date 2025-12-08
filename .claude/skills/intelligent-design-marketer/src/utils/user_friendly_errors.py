#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户友好的错误处理和反馈系统
专为个人用户设计，提供清晰的错误信息和解决方案
"""

import sys
import traceback
import smtplib
import sqlite3
import requests
import time
from typing import Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
import json
from pathlib import Path

class ErrorSeverity(Enum):
    """错误严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class UserFriendlyErrorHandler:
    """用户友好的错误处理器"""

    def __init__(self, log_file: str = "logs/user_errors.log"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)
        self.error_solutions = self._load_error_solutions()

    def _load_error_solutions(self) -> Dict[str, Dict[str, str]]:
        """加载错误解决方案"""
        return {
            "connection_error": {
                "message": "网络连接出现问题",
                "reason": "无法连接到目标网站或服务",
                "solution": "请检查网络连接，确保可以访问目标网站",
                "details": [
                    "检查WiFi或网络连接是否正常",
                    "确认目标网站是否可以正常访问",
                    "检查防火墙设置是否阻止了连接",
                    "如果使用代理，请确认代理配置正确"
                ]
            },
            "email_error": {
                "message": "邮件发送失败",
                "reason": "SMTP服务器连接或配置问题",
                "solution": "请检查邮件服务器配置和网络连接",
                "details": [
                    "确认邮箱账号和密码正确",
                    "检查SMTP服务器地址和端口",
                    "确认开启了IMAP/SMTP服务",
                    "检查是否需要使用应用专用密码"
                ]
            },
            "database_error": {
                "message": "数据库操作失败",
                "reason": "数据库文件损坏或权限问题",
                "solution": "请检查数据库文件和目录权限",
                "details": [
                    "确认程序有读写数据库文件的权限",
                    "检查数据库文件是否损坏",
                    "尝试重新创建数据库",
                    "检查磁盘空间是否充足"
                ]
            },
            "parsing_error": {
                "message": "网页内容解析失败",
                "reason": "网站结构变化或反爬虫机制",
                "solution": "请检查目标网站结构或更新解析规则",
                "details": [
                    "目标网站可能更新了页面结构",
                    "网站可能增加了反爬虫机制",
                    "需要更新CSS选择器或XPath",
                    "考虑增加请求延迟或使用代理"
                ]
            },
            "file_error": {
                "message": "文件操作失败",
                "reason": "文件权限或路径问题",
                "solution": "请检查文件路径和读写权限",
                "details": [
                    "确认文件路径正确",
                    "检查文件读写权限",
                    "确认磁盘空间充足",
                    "检查文件是否被其他程序占用"
                ]
            },
            "config_error": {
                "message": "配置文件错误",
                "reason": "配置项缺失或格式错误",
                "solution": "请检查配置文件格式和必需项",
                "details": [
                    "检查JSON格式是否正确",
                    "确认必需的配置项都存在",
                    "参考示例配置文件",
                    "使用配置验证工具检查"
                ]
            }
        }

    def handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """处理错误并返回用户友好的信息"""

        error_type = self._classify_error(error)
        severity = self._determine_severity(error)

        # 获取错误解决方案
        solution_info = self.error_solutions.get(error_type, {
            "message": "发生了未知错误",
            "reason": "程序遇到了意外情况",
            "solution": "请联系技术支持获取帮助",
            "details": []
        })

        # 记录错误日志
        self._log_error(error, context, error_type, severity)

        # 返回用户友好的错误信息
        return {
            "success": False,
            "error_type": error_type,
            "severity": severity.value,
            "user_message": solution_info["message"],
            "reason": solution_info["reason"],
            "solution": solution_info["solution"],
            "detailed_steps": solution_info["details"],
            "technical_info": {
                "error_class": error.__class__.__name__,
                "error_message": str(error),
                "context": context,
                "timestamp": datetime.now().isoformat()
            }
        }

    def _classify_error(self, error: Exception) -> str:
        """分类错误类型"""
        error_name = error.__class__.__name__.lower()

        if isinstance(error, (requests.ConnectionError, requests.Timeout, requests.RequestException)):
            return "connection_error"
        elif isinstance(error, (smtplib.SMTPException, smtplib.SMTPAuthenticationError)):
            return "email_error"
        elif isinstance(error, (sqlite3.DatabaseError, sqlite3.OperationalError)):
            return "database_error"
        elif "json" in error_name or "parse" in error_name:
            return "parsing_error"
        elif isinstance(error, (FileNotFoundError, PermissionError, OSError)):
            return "file_error"
        elif "config" in error_name.lower() or "key" in error_name.lower():
            return "config_error"
        else:
            return "unknown_error"

    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """确定错误严重程度"""
        if isinstance(error, (FileNotFoundError, PermissionError)):
            return ErrorSeverity.ERROR
        elif isinstance(error, (requests.ConnectionError, smtplib.SMTPException)):
            return ErrorSeverity.WARNING
        elif isinstance(error, (sqlite3.DatabaseError, KeyboardInterrupt)):
            return ErrorSeverity.CRITICAL
        else:
            return ErrorSeverity.ERROR

    def _log_error(self, error: Exception, context: str, error_type: str, severity: ErrorSeverity):
        """记录错误日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "severity": severity.value,
            "error_type": error_type,
            "error_class": error.__class__.__name__,
            "error_message": str(error),
            "context": context,
            "traceback": traceback.format_exc()
        }

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + "\n")
                f.write("-" * 80 + "\n")
        except Exception:
            # 如果日志记录失败，至少输出到控制台
            print(f"无法写入错误日志: {timestamp} - {error}")

    def show_friendly_error(self, error_info: Dict[str, Any]):
        """显示用户友好的错误信息"""
        print("\n" + "="*60)
        print(f"❌ {error_info['user_message']}")
        print("="*60)

        print(f"\n📝 问题原因:")
        print(f"   {error_info['reason']}")

        print(f"\n💡 解决建议:")
        print(f"   {error_info['solution']}")

        if error_info['detailed_steps']:
            print(f"\n📋 详细步骤:")
            for i, step in enumerate(error_info['detailed_steps'], 1):
                print(f"   {i}. {step}")

        # 根据严重程度显示不同提示
        if error_info['severity'] == 'critical':
            print(f"\n⚠️  严重错误：程序需要停止运行")
            print(f"   请查看详细日志文件: {self.log_file}")
        elif error_info['severity'] == 'warning':
            print(f"\n⚠️  警告：程序可以继续运行，但建议解决问题")
        else:
            print(f"\nℹ️  提示：请按照上述建议解决问题后重试")

        print("\n" + "="*60)

    def get_recent_errors(self, limit: int = 10) -> list:
        """获取最近的错误记录"""
        try:
            if not self.log_file.exists():
                return []

            errors = []
            with open(self.log_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 分割日志条目
            entries = content.strip().split("-" * 80)

            for entry in entries[-limit:]:
                if entry.strip():
                    try:
                        error_data = json.loads(entry.strip())
                        errors.append(error_data)
                    except json.JSONDecodeError:
                        continue

            return errors
        except Exception:
            return []

    def generate_error_report(self) -> str:
        """生成错误统计报告"""
        errors = self.get_recent_errors(100)

        if not errors:
            return "✅ 最近没有错误记录"

        # 统计错误类型
        error_counts = {}
        severity_counts = {}

        for error in errors:
            error_type = error.get('error_type', 'unknown')
            severity = error.get('severity', 'unknown')

            error_counts[error_type] = error_counts.get(error_type, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        report = []
        report.append("📊 错误统计报告")
        report.append("=" * 50)
        report.append(f"总错误数: {len(errors)}")
        report.append(f"时间范围: {errors[-1]['timestamp']} 至 {errors[0]['timestamp']}")
        report.append("")

        report.append("📈 错误类型分布:")
        for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
            solution = self.error_solutions.get(error_type, {})
            message = solution.get('message', '未知错误')
            report.append(f"  {message}: {count}次")

        report.append("")
        report.append("🚨 严重程度分布:")
        for severity, count in severity_counts.items():
            emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🔴"}
            report.append(f"  {emoji.get(severity, '❓')} {severity}: {count}次")

        return "\n".join(report)

# 个人用户专用的简化错误处理装饰器
def handle_user_errors(context: str = "", show_error: bool = True):
    """个人用户友好的错误处理装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = UserFriendlyErrorHandler()
                error_info = handler.handle_error(e, context)

                if show_error:
                    handler.show_friendly_error(error_info)

                # 记录错误到控制台（开发模式）
                if kwargs.get('debug', False):
                    print(f"\n🔧 技术详情:")
                    print(f"   错误类型: {error_info['technical_info']['error_class']}")
                    print(f"   错误信息: {error_info['technical_info']['error_message']}")
                    if error_info['technical_info']['context']:
                        print(f"   上下文: {error_info['technical_info']['context']}")

                return {"success": False, "error": error_info}

        return wrapper
    return decorator

# 全局错误处理器实例
global_error_handler = UserFriendlyErrorHandler()

def quick_error_handler(error: Exception, context: str = "") -> Dict[str, Any]:
    """快速错误处理函数"""
    return global_error_handler.handle_error(error, context)

def show_user_error(error_info: Dict[str, Any]):
    """显示用户友好的错误信息"""
    global_error_handler.show_friendly_error(error_info)

if __name__ == "__main__":
    # 测试错误处理
    handler = UserFriendlyErrorHandler()

    # 测试不同类型的错误
    test_errors = [
        requests.ConnectionError("无法连接到服务器"),
        smtplib.SMTPAuthenticationError(535, "认证失败"),
        FileNotFoundError("配置文件不存在"),
        json.JSONDecodeError("格式错误", "test", 0)
    ]

    print("🧪 错误处理测试")
    print("="*50)

    for i, error in enumerate(test_errors, 1):
        print(f"\n测试 {i}: {error.__class__.__name__}")
        error_info = handler.handle_error(error, f"测试场景 {i}")
        handler.show_friendly_error(error_info)
        print("\n" + "💭".center(60, " "))

    # 显示错误报告
    print("\n" + handler.generate_error_report())