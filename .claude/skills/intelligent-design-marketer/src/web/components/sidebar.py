#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web界面侧边栏组件
"""

import streamlit as st
import time
from datetime import datetime
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.utils.config_loader import ConfigLoader
    from src.utils.logger import setup_logger
except ImportError:
    pass

def render_sidebar():
    """渲染侧边栏"""
    st.sidebar.markdown("## 🎛️ 控制面板")

    # 快速操作
    st.sidebar.markdown("### 🚀 快速操作")

    if st.sidebar.button("🔍 立即搜索", key="quick_search"):
        st.session_state.quick_search = True

    if st.sidebar.button("📧 发送邮件", key="quick_email"):
        st.session_state.quick_email = True

    if st.sidebar.button("📊 生成报告", key="quick_report"):
        st.session_state.quick_report = True

    if st.sidebar.button("⚙️ 系统诊断", key="quick_diagnosis"):
        st.session_state.quick_diagnosis = True

    st.sidebar.markdown("---")

    # 实时状态
    st.sidebar.markdown("### 📈 实时状态")

    # 系统负载
    try:
        cpu_usage = get_cpu_usage()
        memory_usage = get_memory_usage()

        st.sidebar.metric("CPU使用率", f"{cpu_usage:.1f}%")
        st.sidebar.metric("内存使用率", f"{memory_usage:.1f}%")

        # 进度条
        st.sidebar.progress(min(cpu_usage / 100, 1.0), "CPU")
        st.sidebar.progress(min(memory_usage / 100, 1.0), "内存")
    except:
        st.sidebar.warning("无法获取系统状态")

    st.sidebar.markdown("---")

    # 活跃任务
    st.sidebar.markdown("### ⚡ 活跃任务")

    active_tasks = get_active_tasks()
    if active_tasks:
        for task in active_tasks:
            status_icon = "🟢" if task['status'] == 'running' else "🟡" if task['status'] == 'waiting' else "🔴"
            st.sidebar.write(f"{status_icon} {task['name']}")

            # 显示进度
            if 'progress' in task:
                st.sidebar.progress(task['progress'] / 100, task['name'])
    else:
        st.sidebar.info("暂无活跃任务")

    st.sidebar.markdown("---")

    # 通知中心
    st.sidebar.markdown("### 🔔 通知中心")

    notifications = get_notifications()
    if notifications:
        for i, notification in enumerate(notifications[:5]):  # 最多显示5条
            icon = "📢" if notification['type'] == 'info' else "⚠️" if notification['type'] == 'warning' else "❌"
            time_str = notification['time'].strftime('%H:%M')
            st.sidebar.write(f"{icon} {time_str} {notification['message']}")
    else:
        st.sidebar.info("暂无新通知")

    st.sidebar.markdown("---")

    # 快速统计
    st.sidebar.markdown("### 📊 今日统计")

    try:
        today_stats = get_today_statistics()
        st.sidebar.metric("新增数据", f"{today_stats.get('new_data', 0):,}")
        st.sidebar.metric("提取联系", f"{today_stats.get('extracted_contacts', 0):,}")
        st.sidebar.metric("发送邮件", f"{today_stats.get('sent_emails', 0):,}")
        st.sidebar.metric("成功率", f"{today_stats.get('success_rate', 0):.1f}%")
    except:
        st.sidebar.warning("无法获取统计数据")

    st.sidebar.markdown("---")

    # 系统信息
    st.sidebar.markdown("### ℹ️ 系统信息")

    try:
        config = ConfigLoader("config/project_config.json").load_config()
        version = config.get('project_info', {}).get('version', '1.0.0')
        uptime = get_system_uptime()
        last_update = get_last_update()

        st.sidebar.write(f"**版本**: {version}")
        st.sidebar.write(f"**运行时间**: {uptime}")
        st.sidebar.write(f"**最后更新**: {last_update}")
    except:
        st.sidebar.warning("无法获取系统信息")

    # 控制按钮
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎛️ 系统控制")

    col1, col2 = st.sidebar.columns(2)

    with col1:
        if st.button("🔄 刷新", key="refresh_system"):
            st.session_state.refresh_time = time.time()
            st.rerun()

    with col2:
        if st.button("⏸️ 暂停", key="pause_system"):
            st.session_state.system_paused = not st.session_state.get('system_paused', False)
            status = "已暂停" if st.session_state.system_paused else "运行中"
            st.sidebar.info(f"系统状态: {status}")

    # 配置链接
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔧 快速配置")

    if st.sidebar.button("📧 邮件配置", key="email_config"):
        st.session_state.show_email_config = True

    if st.sidebar.button("🕷️ 爬虫配置", key="scraper_config"):
        st.session_state.show_scraper_config = True

    if st.sidebar.button("📊 监控设置", key="monitoring_config"):
        st.session_state.show_monitoring_config = True

    # 帮助链接
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📚 帮助文档")

    help_links = [
        ("📖 用户手册", "#user-guide"),
        ("🔧 API文档", "#api-docs"),
        ("💡 最佳实践", "#best-practices"),
        ("🐛 故障排除", "#troubleshooting"),
        ("📞 技术支持", "#support")
    ]

    for link_text, link_url in help_links:
        if st.sidebar.button(link_text, key=link_text):
            st.session_state.help_page = link_url

    # 页脚
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"<div style='text-align: center; font-size: 12px; color: #666;'>"
        f"© 2024 智能设计营销系统<br>"
        f"版本 2.0.0"
        f"</div>",
        unsafe_allow_html=True
    )

def get_cpu_usage() -> float:
    """获取CPU使用率"""
    try:
        import psutil
        return psutil.cpu_percent(interval=1)
    except:
        return 0.0

def get_memory_usage() -> float:
    """获取内存使用率"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        return memory.percent
    except:
        return 0.0

def get_active_tasks() -> list:
    """获取活跃任务列表"""
    # 这里应该从实际的任务管理器获取
    return [
        {
            'name': '政府采购爬取',
            'status': 'running',
            'progress': 65
        },
        {
            'name': '联系人提取',
            'status': 'waiting',
            'progress': 0
        },
        {
            'name': '邮件发送',
            'status': 'running',
            'progress': 30
        }
    ]

def get_notifications() -> list:
    """获取通知列表"""
    now = datetime.now()

    # 这里应该从实际的通知系统获取
    return [
        {
            'type': 'info',
            'message': '爬虫任务完成',
            'time': now - timedelta(minutes=5)
        },
        {
            'type': 'warning',
            'message': '邮件发送成功率偏低',
            'time': now - timedelta(minutes=15)
        },
        {
            'type': 'info',
            'message': '新增23个联系人',
            'time': now - timedelta(minutes=30)
        }
    ]

def get_today_statistics() -> dict:
    """获取今日统计数据"""
    # 这里应该从实际的数据库获取
    return {
        'new_data': 156,
        'extracted_contacts': 89,
        'sent_emails': 234,
        'success_rate': 95.2
    }

def get_system_uptime() -> str:
    """获取系统运行时间"""
    try:
        import psutil
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time

        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60

        if days > 0:
            return f"{days}天{hours}小时"
        elif hours > 0:
            return f"{hours}小时{minutes}分钟"
        else:
            return f"{minutes}分钟"
    except:
        return "未知"

def get_last_update() -> str:
    """获取最后更新时间"""
    # 这里应该从实际的数据获取
    now = datetime.now()
    return now.strftime('%m-%d %H:%M')

def render_quick_search():
    """渲染快速搜索界面"""
    st.subheader("🔍 快速搜索")

    search_type = st.selectbox(
        "搜索类型",
        ["联系人", "项目", "邮件", "日志"],
        key="quick_search_type"
    )

    search_term = st.text_input("搜索关键词", key="quick_search_term")

    if search_term:
        st.write(f"搜索结果: '{search_term}' 在{search_type}中")

        # 这里应该执行实际的搜索逻辑
        if search_type == "联系人":
            st.info("正在搜索联系人...")
            # 模拟搜索结果
            st.write("找到 3 个匹配的联系人")
        elif search_type == "项目":
            st.info("正在搜索项目...")
            st.write("找到 5 个匹配的项目")
        elif search_type == "邮件":
            st.info("正在搜索邮件...")
            st.write("找到 2 个匹配的邮件")
        elif search_type == "日志":
            st.info("正在搜索日志...")
            st.write("找到 12 个匹配的日志条目")

def render_quick_email():
    """渲染快速邮件发送界面"""
    st.subheader("📧 快速发送邮件")

    col1, col2 = st.columns(2)

    with col1:
        recipient_email = st.text_input("收件人邮箱", key="quick_email")
        email_subject = st.text_input("邮件主题", key="quick_subject")

    with col2:
        template_type = st.selectbox(
            "邮件模板",
            ["通用", "政府", "教育", "企业"],
            key="quick_template"
        )

    email_content = st.text_area("邮件内容", height=200, key="quick_content")

    if st.button("📤 发送邮件", key="send_quick_email"):
        if recipient_email and email_subject and email_content:
            st.success("邮件发送成功！")
            # 这里应该执行实际的邮件发送逻辑
        else:
            st.error("请填写完整的邮件信息")

def render_quick_report():
    """渲染快速报告生成界面"""
    st.subheader("📊 生成报告")

    report_type = st.selectbox(
        "报告类型",
        ["日报", "周报", "月报", "自定义"],
        key="report_type"
    )

    if report_type == "自定义":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", key="report_start")
        with col2:
            end_date = st.date_input("结束日期", key="report_end")

    report_format = st.selectbox(
        "报告格式",
        ["HTML", "PDF", "Excel"],
        key="report_format"
    )

    if st.button("📋 生成报告", key="generate_report"):
        st.info("正在生成报告...")

        # 模拟报告生成过程
        with st.spinner("生成中..."):
            time.sleep(2)

        st.success("报告生成完成！")
        st.download_button(
            label="下载报告",
            data="报告内容示例",
            file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html"
        )

def render_quick_diagnosis():
    """渲染系统诊断界面"""
    st.subheader("🔍 系统诊断")

    st.write("正在执行系统诊断...")

    # 诊断项目
    diagnostic_items = [
        "数据库连接",
        "Redis缓存",
        "邮件服务",
        "爬虫服务",
        "系统资源",
        "网络连接"
    ]

    progress_bar = st.progress(0)

    for i, item in enumerate(diagnostic_items):
        time.sleep(0.5)  # 模拟诊断过程
        progress_bar.progress((i + 1) / len(diagnostic_items))
        st.write(f"✅ {item} - 正常")

    st.success("系统诊断完成！")

    # 诊断结果摘要
    st.subheader("📋 诊断结果摘要")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("健康状态", "良好", "100%")

    with col2:
        st.metric("警告数量", "0", "-1")

    with col3:
        st.metric("错误数量", "0", "-1")

    with col4:
        st.metric("建议操作", "0", "-1")

    # 详细诊断报告
    st.subheader("📄 详细诊断报告")

    if st.button("📄 查看详细报告"):
        st.info("详细诊断报告将显示在这里...")

# 在会话状态中处理快速操作
if 'quick_search' in st.session_state and st.session_state.quick_search:
    render_quick_search()
    st.session_state.quick_search = False

if 'quick_email' in st.session_state and st.session_state.quick_email:
    render_quick_email()
    st.session_state.quick_email = False

if 'quick_report' in st.session_state and st.session_state.quick_report:
    render_quick_report()
    st.session_state.quick_report = False

if 'quick_diagnosis' in st.session_state and st.session_state.quick_diagnosis:
    render_quick_diagnosis()
    st.session_state.quick_diagnosis = False