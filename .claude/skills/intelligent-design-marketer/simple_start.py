#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版启动脚本 - 专为个人用户设计
零依赖启动，自动检查和安装必要的包
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        print(f"当前版本: {sys.version}")
        return False
    print(f"✅ Python版本: {sys.version}")
    return True

def install_packages():
    """安装必要的包"""
    required_packages = [
        'requests', 'beautifulsoup4', 'lxml', 'pandas',
        'plotly', 'streamlit', 'psutil', 'colorama'
    ]

    print("🔍 检查并安装必要的包...")
    for package in required_packages:
        try:
            if package == 'beautifulsoup4':
                __import__('bs4')
            elif package == 'colorama':
                __import__('colorama')
            else:
                __import__(package.replace('-', '_'))
            print(f"✅ {package} 已安装")
        except ImportError:
            print(f"📦 安装 {package}...")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"✅ {package} 安装成功")
            except subprocess.CalledProcessError:
                print(f"❌ {package} 安装失败")
                return False

    return True

def create_basic_config():
    """创建基础配置"""
    config_dir = project_root / "config"
    config_dir.mkdir(exist_ok=True)

    config_file = config_dir / "user_config.json"
    if not config_file.exists():
        basic_config = {
            "user_info": {
                "setup_date": "2024-12-05",
                "version": "2.0.0",
                "user_type": "personal"
            },
            "email": {
                "smtp_server": "smtp.qq.com",
                "smtp_port": 587,
                "email": "",
                "password": "",
                "sender_name": "设计营销助手",
                "use_ssl": False,
                "configured": False
            },
            "scraper": {
                "data_sources": ["政府采购网", "高校采购平台"],
                "frequency": {"hours": 8, "description": "每天3次"},
                "delay_range": {"min": 3, "max": 8},
                "auto_start": False,
                "configured": True
            },
            "storage": {
                "data_path": str(project_root / "data"),
                "retention_days": 90,
                "backup_enabled": False,
                "backup_frequency": "weekly",
                "configured": True
            }
        }

        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(basic_config, f, ensure_ascii=False, indent=2)
            print("✅ 基础配置已创建")
        except Exception as e:
            print(f"❌ 创建配置失败: {e}")
            return False
    else:
        print("✅ 配置文件已存在")

    return True

def create_directories():
    """创建必要的目录"""
    directories = ["data", "logs", "config"]
    for dir_name in directories:
        dir_path = project_root / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"✅ 目录 {dir_name} 已创建")

def start_web_interface():
    """启动Web界面"""
    try:
        web_file = project_root / "src" / "web" / "dashboard.py"
        if not web_file.exists():
            # 创建简单的Web界面
            simple_web = '''import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import json
import sys

st.set_page_config(page_title="智能设计营销系统", page_icon="🚀", layout="wide")

st.title("🚀 智能设计营销系统")
st.markdown("---")

# 侧边栏
st.sidebar.title("📋 功能菜单")
page = st.sidebar.selectbox("选择页面", [
    "系统概览",
    "数据爬取",
    "联系人管理",
    "邮件营销",
    "系统设置"
])

if page == "系统概览":
    st.header("📊 系统概览")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("📧 邮件配置", "未配置" if not Path("config/user_config.json").exists() else "已配置")

    with col2:
        st.metric("📁 数据文件", len(list(Path("data").glob("*.db"))) if Path("data").exists() else 0)

    with col3:
        st.metric("📝 日志文件", len(list(Path("logs").glob("*.log"))) if Path("logs").exists() else 0)

    st.markdown("---")
    st.subheader("🎯 快速开始")

    st.info("""
    **欢迎使用智能设计营销系统！**

    这是一个专为个人用户设计的自动化营销工具，帮助您：
    - 🔍 自动搜索政府采购、高校、国企等公告
    - 👥 智能提取联系人信息
    - 📧 批量发送个性化营销邮件
    - 📊 可视化数据分析和报告

    **使用步骤：**
    1. 配置您的邮箱信息
    2. 选择要爬取的数据源
    3. 启动自动爬取服务
    4. 开始邮件营销活动
    """)

elif page == "数据爬取":
    st.header("🕷️ 数据爬取")

    st.info("爬虫功能正在开发中，敬请期待...")

    if st.button("🧪 测试网络连接"):
        try:
            import requests
            response = requests.get("https://www.baidu.com", timeout=5)
            if response.status_code == 200:
                st.success("✅ 网络连接正常")
            else:
                st.error(f"❌ 网络连接异常: {response.status_code}")
        except Exception as e:
            st.error(f"❌ 网络连接失败: {e}")

elif page == "联系人管理":
    st.header("👥 联系人管理")

    st.info("联系人管理功能正在开发中...")

elif page == "邮件营销":
    st.header("📧 邮件营销")

    config_file = Path("config/user_config.json")
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        email_config = config.get('email', {})

        st.subheader("📧 邮件配置状态")

        if email_config.get('configured'):
            st.success("✅ 邮件已配置")
            st.write(f"**SMTP服务器**: {email_config.get('smtp_server', 'N/A')}")
            st.write(f"**发件邮箱**: {email_config.get('email', 'N/A')}")
        else:
            st.warning("⚠️ 邮件未配置")
            st.info("请运行配置向导: `python simple_start.py --config`")
    else:
        st.warning("⚠️ 配置文件不存在，请先配置")

elif page == "系统设置":
    st.header("⚙️ 系统设置")

    st.subheader("📊 系统信息")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Python版本", f"{sys.version_info.major}.{sys.version_info.minor}")
        st.metric("工作目录", str(Path.cwd()))

    with col2:
        if Path("data").exists():
            size = sum(f.stat().st_size for f in Path("data").rglob('*') if f.is_file())
            st.metric("数据大小", f"{size/1024/1024:.1f} MB")

        if Path("logs").exists():
            log_count = len(list(Path("logs").glob("*.log")))
            st.metric("日志文件", log_count)

    st.markdown("---")
    st.subheader("🛠️ 系统操作")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📊 健康检查"):
            st.info("健康检查功能开发中...")

    with col2:
        if st.button("🧹 清理缓存"):
            st.info("缓存清理功能开发中...")

    with col3:
        if st.button("📋 查看日志"):
            st.info("日志查看功能开发中...")

st.markdown("---")
st.markdown("**💡 提示**: 如需帮助，请查看故障排除指南或运行 `python src/utils/health_checker.py`")
'''

            web_file.write_text(simple_web, encoding='utf-8')
            print("✅ 简单Web界面已创建")

        # 启动Streamlit
        print("🚀 启动Web界面...")
        os.system(f"cd {project_root} && {sys.executable} -m streamlit run {web_file} --server.port 8501")

    except Exception as e:
        print(f"❌ 启动Web界面失败: {e}")
        return False

def run_config_wizard():
    """运行配置向导"""
    print("🧙 配置向导正在开发中...")
    print("请稍后运行完整版本: python quick_start.py --config")

def show_menu():
    """显示菜单"""
    print("\n🚀 智能设计营销系统 - 简化版启动器")
    print("=" * 50)
    print("1. 🌐 启动Web界面")
    print("2. ⚙️ 运行配置向导")
    print("3. 📊 系统检查")
    print("4. 🚪 退出")
    print("=" * 50)

def main():
    """主函数"""
    print("🔧 正在初始化系统...")

    # 检查Python版本
    if not check_python_version():
        return

    # 安装必要的包
    if not install_packages():
        print("❌ 包安装失败，请手动安装: pip install requests beautifulsoup4 pandas plotly streamlit psutil")
        return

    # 创建目录和配置
    create_directories()
    create_basic_config()

    print("✅ 系统初始化完成！\n")

    # 处理命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--config":
            run_config_wizard()
            return
        elif sys.argv[1] == "--web":
            start_web_interface()
            return

    # 显示菜单
    while True:
        show_menu()
        choice = input("请选择 (1-4): ").strip()

        if choice == "1":
            start_web_interface()
        elif choice == "2":
            run_config_wizard()
        elif choice == "3":
            print("📊 系统检查功能开发中...")
        elif choice == "4":
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择，请重试")

if __name__ == "__main__":
    main()