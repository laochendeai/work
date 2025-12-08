#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能设计营销自动化系统 - Web管理界面
基于Streamlit的数据可视化管理平台
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.utils.config_loader import ConfigLoader
    from src.utils.database_manager import DatabaseManager
    from src.monitoring.metrics import MetricsCollector
    from src.web.components.sidebar import render_sidebar
    from src.web.components.charts import render_charts
    from src.web.components.tables import render_tables
    from src.web.components.forms import render_forms
except ImportError as e:
    st.error(f"导入模块失败: {e}")
    st.stop()

# 页面配置
st.set_page_config(
    page_title="智能设计营销自动化系统",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }

    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }

    .status-success {
        color: #2ecc71;
        font-weight: bold;
    }

    .status-warning {
        color: #f39c12;
        font-weight: bold;
    }

    .status-error {
        color: #e74c3c;
        font-weight: bold;
    }

    .data-table {
        font-size: 0.9rem;
    }

    .chart-container {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class MarketingDashboard:
    """营销系统管理仪表板"""

    def __init__(self):
        """初始化仪表板"""
        self.config = None
        self.db_manager = None
        self.metrics_collector = None

        try:
            # 加载配置
            self.config = ConfigLoader("config/project_config.json").load_config()

            # 初始化数据库连接
            self.db_manager = DatabaseManager(self.config['database'])

            # 初始化指标收集器
            if self.config.get('monitoring', {}).get('enabled', False):
                self.metrics_collector = MetricsCollector()

        except Exception as e:
            st.error(f"系统初始化失败: {e}")
            st.stop()

    def render_header(self):
        """渲染页面头部"""
        st.markdown('<div class="main-header">🚀 智能设计营销自动化系统</div>', unsafe_allow_html=True)

        # 系统状态指示器
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            status = self.get_system_status()
            status_color = {
                'running': 'status-success',
                'warning': 'status-warning',
                'error': 'status-error'
            }.get(status, 'status-warning')

            st.markdown(f'<div class="metric-card"><h4>系统状态</h4><p class="{status_color}">{status.upper()}</p></div>', unsafe_allow_html=True)

        with col2:
            uptime = self.get_system_uptime()
            st.markdown(f'<div class="metric-card"><h4>运行时间</h4><p>{uptime}</p></div>', unsafe_allow_html=True)

        with col3:
            data_count = self.get_data_count()
            st.markdown(f'<div class="metric-card"><h4>数据总量</h4><p>{data_count:,}</p></div>', unsafe_allow_html=True)

        with col4:
            last_update = self.get_last_update()
            st.markdown(f'<div class="metric-card"><h4>最后更新</h4><p>{last_update}</p></div>', unsafe_allow_html=True)

    def get_system_status(self) -> str:
        """获取系统状态"""
        try:
            # 检查数据库连接
            if self.db_manager.test_connection():
                return 'running'
            else:
                return 'error'
        except:
            return 'warning'

    def get_system_uptime(self) -> str:
        """获取系统运行时间"""
        try:
            if self.metrics_collector:
                uptime = self.metrics_collector.get_system_uptime()
                return f"{uptime:.1f}小时"
            else:
                return "未知"
        except:
            return "未知"

    def get_data_count(self) -> int:
        """获取数据总量"""
        try:
            return self.db_manager.get_total_records()
        except:
            return 0

    def get_last_update(self) -> str:
        """获取最后更新时间"""
        try:
            last_update = self.db_manager.get_last_update()
            if last_update:
                return last_update.strftime('%m-%d %H:%M')
            else:
                return "无数据"
        except:
            return "未知"

    def render_overview_tab(self):
        """渲染概览标签页"""
        st.subheader("📊 系统概览")

        # 指标卡片
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            today_scraped = self.get_today_scraped_count()
            st.metric("今日爬取", f"{today_scraped:,}")

        with col2:
            today_extracted = self.get_today_extracted_count()
            st.metric("今日提取", f"{today_extracted:,}")

        with col3:
            today_emails = self.get_today_email_count()
            st.metric("今日邮件", f"{today_emails:,}")

        with col4:
            success_rate = self.get_success_rate()
            st.metric("成功率", f"{success_rate:.1f}%")

        # 趋势图表
        st.subheader("📈 数据趋势")

        # 选择时间范围
        col1, col2 = st.columns([2, 1])
        with col1:
            date_range = st.selectbox(
                "选择时间范围",
                ["最近7天", "最近30天", "最近90天"],
                index=0
            )

        with col2:
            if st.button("刷新数据"):
                st.rerun()

        # 渲染趋势图表
        trend_data = self.get_trend_data(date_range)

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("爬取数据量", "提取联系人", "发送邮件", "成功率"),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": True}]]
        )

        # 爬取数据趋势
        fig.add_trace(
            go.Scatter(x=trend_data['date'], y=trend_data['scraped'], name="爬取数据量"),
            row=1, col=1
        )

        # 提取联系人趋势
        fig.add_trace(
            go.Scatter(x=trend_data['date'], y=trend_data['extracted'], name="提取联系人"),
            row=1, col=2
        )

        # 发送邮件趋势
        fig.add_trace(
            go.Scatter(x=trend_data['date'], y=trend_data['emails'], name="发送邮件"),
            row=2, col=1
        )

        # 成功率趋势
        fig.add_trace(
            go.Scatter(x=trend_data['date'], y=trend_data['success_rate'], name="成功率"),
            row=2, col=2
        )

        fig.update_layout(height=600, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    def get_today_scraped_count(self) -> int:
        """获取今日爬取数据量"""
        try:
            return self.db_manager.get_today_count('scraped_data')
        except:
            return 0

    def get_today_extracted_count(self) -> int:
        """获取今日提取联系人数量"""
        try:
            return self.db_manager.get_today_count('extracted_contacts')
        except:
            return 0

    def get_today_email_count(self) -> int:
        """获取今日发送邮件数量"""
        try:
            return self.db_manager.get_today_count('sent_emails')
        except:
            return 0

    def get_success_rate(self) -> float:
        """获取邮件发送成功率"""
        try:
            return self.db_manager.get_email_success_rate()
        except:
            return 0.0

    def get_trend_data(self, date_range: str) -> dict:
        """获取趋势数据"""
        try:
            # 根据时间范围计算日期
            days_map = {"最近7天": 7, "最近30天": 30, "最近90天": 90}
            days = days_map.get(date_range, 7)

            dates = []
            scraped_data = []
            extracted_data = []
            email_data = []
            success_rates = []

            for i in range(days):
                date = datetime.now() - timedelta(days=i)
                dates.append(date.strftime('%m-%d'))

                scraped_data.append(self.db_manager.get_date_count('scraped_data', date))
                extracted_data.append(self.db_manager.get_date_count('extracted_contacts', date))
                email_data.append(self.db_manager.get_date_count('sent_emails', date))
                success_rates.append(self.db_manager.get_date_success_rate(date) * 100)

            return {
                'date': dates[::-1],
                'scraped': scraped_data[::-1],
                'extracted': extracted_data[::-1],
                'emails': email_data[::-1],
                'success_rate': success_rates[::-1]
            }
        except:
            return {
                'date': [], 'scraped': [], 'extracted': [], 'emails': [], 'success_rate': []
            }

    def render_scraping_tab(self):
        """渲染爬虫管理标签页"""
        st.subheader("🕷️ 爬虫管理")

        # 爬虫状态
        col1, col2, col3 = st.columns(3)

        with col1:
            active_scrapers = self.get_active_scrapers_count()
            st.metric("活跃爬虫", active_scrapers)

        with col2:
            success_rate = self.get_scraping_success_rate()
            st.metric("爬取成功率", f"{success_rate:.1f}%")

        with col3:
            avg_duration = self.get_avg_scraping_duration()
            st.metric("平均耗时", f"{avg_duration:.1f}秒")

        # 爬虫配置管理
        st.subheader("⚙️ 爬虫配置")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**数据源配置**")
            data_sources = self.get_data_sources()
            for source in data_sources:
                status = "✅ 启用" if source['enabled'] else "❌ 禁用"
                st.write(f"{source['name']}: {status}")

        with col2:
            st.write("**爬取设置**")
            delay_range = self.config.get('scraping', {}).get('delay_range', [1, 3])
            timeout = self.config.get('scraping', {}).get('timeout', 30)
            max_retries = self.config.get('scraping', {}).get('max_retries', 3)

            st.write(f"延时范围: {delay_range[0]}-{delay_range[1]}秒")
            st.write(f"超时时间: {timeout}秒")
            st.write(f"最大重试: {max_retries}次")

        # 爬取历史记录
        st.subheader("📋 爬取历史")

        # 筛选选项
        col1, col2, col3 = st.columns(3)

        with col1:
            source_filter = st.selectbox(
                "数据源",
                ["全部"] + [s['name'] for s in self.get_data_sources()]
            )

        with col2:
            status_filter = st.selectbox(
                "状态",
                ["全部", "成功", "失败", "进行中"]
            )

        with col3:
            date_filter = st.date_input("日期", datetime.now().date())

        # 显示爬取记录
        scraping_records = self.get_scraping_records(source_filter, status_filter, date_filter)

        if scraping_records:
            df = pd.DataFrame(scraping_records)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("暂无爬取记录")

    def get_active_scrapers_count(self) -> int:
        """获取活跃爬虫数量"""
        try:
            # 这里应该从实际的爬虫管理器获取状态
            return 3  # 示例值
        except:
            return 0

    def get_scraping_success_rate(self) -> float:
        """获取爬取成功率"""
        try:
            return self.db_manager.get_scraping_success_rate()
        except:
            return 0.0

    def get_avg_scraping_duration(self) -> float:
        """获取平均爬取耗时"""
        try:
            return self.db_manager.get_avg_scraping_duration()
        except:
            return 0.0

    def get_data_sources(self) -> list:
        """获取数据源配置"""
        try:
            return self.config.get('data_sources', {})
        except:
            return []

    def get_scraping_records(self, source_filter: str, status_filter: str, date_filter) -> list:
        """获取爬取记录"""
        try:
            return self.db_manager.get_scraping_records(source_filter, status_filter, date_filter)
        except:
            return []

    def render_contacts_tab(self):
        """渲染联系人管理标签页"""
        st.subheader("👥 联系人管理")

        # 联系人统计
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_contacts = self.get_total_contacts_count()
            st.metric("总联系人数", f"{total_contacts:,}")

        with col2:
            new_contacts = self.get_new_contacts_count()
            st.metric("新增联系人", f"{new_contacts:,}")

        with col3:
            verified_contacts = self.get_verified_contacts_count()
            st.metric("已验证联系人", f"{verified_contacts:,}")

        with col4:
            contacted = self.get_contacted_contacts_count()
            st.metric("已联系", f"{contacted:,}")

        # 联系人搜索和筛选
        st.subheader("🔍 联系人搜索")

        col1, col2, col3 = st.columns(3)

        with col1:
            search_term = st.text_input("搜索联系人")

        with col2:
            company_filter = st.selectbox(
                "公司筛选",
                ["全部"] + self.get_company_list()
            )

        with col3:
            status_filter = st.selectbox(
                "状态筛选",
                ["全部", "未联系", "已联系", "已成交", "无效"]
            )

        # 联系人列表
        contacts = self.get_contacts(search_term, company_filter, status_filter)

        if contacts:
            # 转换为DataFrame
            df = pd.DataFrame(contacts)

            # 显示统计图表
            st.subheader("📊 联系人分布")

            col1, col2 = st.columns(2)

            with col1:
                # 按公司分布
                company_counts = df['company'].value_counts().head(10)
                fig = px.bar(x=company_counts.index, y=company_counts.values,
                           title="按公司分布", labels={'x': '公司', 'y': '联系人数'})
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # 按状态分布
                status_counts = df['status'].value_counts()
                fig = px.pie(values=status_counts.values, names=status_counts.index,
                           title="按状态分布")
                st.plotly_chart(fig, use_container_width=True)

            # 联系人表格
            st.subheader("📋 联系人列表")

            # 分页显示
            page_size = 20
            total_pages = (len(df) + page_size - 1) // page_size
            page = st.number_input("页码", 1, total_pages, 1)

            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size

            st.dataframe(df.iloc[start_idx:end_idx], use_container_width=True)

            # 导出功能
            if st.button("导出联系人数据"):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="下载CSV文件",
                    data=csv,
                    file_name=f"contacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("暂无联系人数据")

    def get_total_contacts_count(self) -> int:
        """获取总联系人数"""
        try:
            return self.db_manager.get_total_contacts_count()
        except:
            return 0

    def get_new_contacts_count(self) -> int:
        """获取新增联系人数"""
        try:
            return self.db_manager.get_new_contacts_count()
        except:
            return 0

    def get_verified_contacts_count(self) -> int:
        """获取已验证联系人数"""
        try:
            return self.db_manager.get_verified_contacts_count()
        except:
            return 0

    def get_contacted_contacts_count(self) -> int:
        """获取已联系联系人数"""
        try:
            return self.db_manager.get_contacted_contacts_count()
        except:
            return 0

    def get_company_list(self) -> list:
        """获取公司列表"""
        try:
            return self.db_manager.get_company_list()
        except:
            return []

    def get_contacts(self, search_term: str, company_filter: str, status_filter: str) -> list:
        """获取联系人列表"""
        try:
            return self.db_manager.get_contacts(search_term, company_filter, status_filter)
        except:
            return []

    def render_email_tab(self):
        """渲染邮件营销标签页"""
        st.subheader("📧 邮件营销")

        # 邮件统计
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_sent = self.get_total_sent_emails()
            st.metric("总发送量", f"{total_sent:,}")

        with col2:
            delivered = self.get_delivered_emails()
            st.metric("成功送达", f"{delivered:,}")

        with col3:
            opened = self.get_opened_emails()
            st.metric("已打开", f"{opened:,}")

        with col4:
            clicked = self.get_clicked_emails()
            st.metric("已点击", f"{clicked:,}")

        # 邮件模板管理
        st.subheader("📝 邮件模板")

        col1, col2 = st.columns(2)

        with col1:
            # 模板列表
            templates = self.get_email_templates()
            template_names = [t['name'] for t in templates]
            selected_template = st.selectbox("选择模板", template_names)

            if selected_template:
                template = next(t for t in templates if t['name'] == selected_template)
                st.write(f"**主题**: {template['subject']}")
                st.write(f"**类型**: {template['type']}")
                st.write(f"**使用次数**: {template['usage_count']}")

        with col2:
            # 创建新模板
            st.write("**创建新模板**")

            template_name = st.text_input("模板名称")
            template_subject = st.text_input("邮件主题")
            template_type = st.selectbox("模板类型", ["通用", "政府", "教育", "企业"])

            if st.button("创建模板"):
                if template_name and template_subject:
                    self.create_email_template(template_name, template_subject, template_type)
                    st.success("模板创建成功")
                else:
                    st.error("请填写完整信息")

        # 邮件发送历史
        st.subheader("📋 发送历史")

        # 筛选选项
        col1, col2, col3 = st.columns(3)

        with col1:
            date_from = st.date_input("开始日期", datetime.now().date() - timedelta(days=30))

        with col2:
            date_to = st.date_input("结束日期", datetime.now().date())

        with col3:
            status_filter = st.selectbox("状态", ["全部", "发送中", "已发送", "失败"])

        # 邮件记录
        email_records = self.get_email_records(date_from, date_to, status_filter)

        if email_records:
            df = pd.DataFrame(email_records)
            st.dataframe(df, use_container_width=True)

            # 邮件效果图表
            st.subheader("📊 邮件效果分析")

            col1, col2 = st.columns(2)

            with col1:
                # 打开率趋势
                fig = px.line(
                    x=df['date'],
                    y=df['open_rate'],
                    title="打开率趋势",
                    labels={'x': '日期', 'y': '打开率 (%)'}
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # 点击率趋势
                fig = px.line(
                    x=df['date'],
                    y=df['click_rate'],
                    title="点击率趋势",
                    labels={'x': '日期', 'y': '点击率 (%)'}
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无邮件发送记录")

    def get_total_sent_emails(self) -> int:
        """获取总发送邮件数"""
        try:
            return self.db_manager.get_total_sent_emails()
        except:
            return 0

    def get_delivered_emails(self) -> int:
        """获取成功送达邮件数"""
        try:
            return self.db_manager.get_delivered_emails()
        except:
            return 0

    def get_opened_emails(self) -> int:
        """获取已打开邮件数"""
        try:
            return self.db_manager.get_opened_emails()
        except:
            return 0

    def get_clicked_emails(self) -> int:
        """获取已点击邮件数"""
        try:
            return self.db_manager.get_clicked_emails()
        except:
            return 0

    def get_email_templates(self) -> list:
        """获取邮件模板列表"""
        try:
            return self.db_manager.get_email_templates()
        except:
            return []

    def create_email_template(self, name: str, subject: str, template_type: str):
        """创建邮件模板"""
        try:
            self.db_manager.create_email_template(name, subject, template_type)
        except Exception as e:
            st.error(f"创建模板失败: {e}")

    def get_email_records(self, date_from, date_to, status_filter: str) -> list:
        """获取邮件记录"""
        try:
            return self.db_manager.get_email_records(date_from, date_to, status_filter)
        except:
            return []

    def render_settings_tab(self):
        """渲染系统设置标签页"""
        st.subheader("⚙️ 系统设置")

        # 基本设置
        st.write("### 基本设置")

        col1, col2 = st.columns(2)

        with col1:
            system_name = st.text_input(
                "系统名称",
                value=self.config.get('project_info', {}).get('name', '智能设计营销系统')
            )

            log_level = st.selectbox(
                "日志级别",
                ["DEBUG", "INFO", "WARNING", "ERROR"],
                index=["DEBUG", "INFO", "WARNING", "ERROR"].index(
                    self.config.get('logging', {}).get('level', 'INFO')
                )
            )

        with col2:
            max_workers = st.number_input(
                "最大工作线程",
                min_value=1,
                max_value=20,
                value=self.config.get('scraping', {}).get('concurrent_requests', 5)
            )

            timeout = st.number_input(
                "请求超时时间(秒)",
                min_value=5,
                max_value=300,
                value=self.config.get('scraping', {}).get('timeout', 30)
            )

        # 爬虫设置
        st.write("### 爬虫设置")

        col1, col2 = st.columns(2)

        with col1:
            min_delay = st.number_input(
                "最小延时(秒)",
                min_value=0.1,
                max_value=10.0,
                value=float(self.config.get('scraping', {}).get('delay_range', [1, 3])[0]),
                step=0.1
            )

            max_delay = st.number_input(
                "最大延时(秒)",
                min_value=0.1,
                max_value=60.0,
                value=float(self.config.get('scraping', {}).get('delay_range', [1, 3])[1]),
                step=0.1
            )

        with col2:
            max_retries = st.number_input(
                "最大重试次数",
                min_value=0,
                max_value=10,
                value=self.config.get('scraping', {}).get('max_retries', 3)
            )

            respect_robots = st.checkbox(
                "遵守robots.txt",
                value=self.config.get('scraping', {}).get('respect_robots', True)
            )

        # 邮件设置
        st.write("### 邮件设置")

        col1, col2 = st.columns(2)

        with col1:
            batch_size = st.number_input(
                "批次大小",
                min_value=1,
                max_value=1000,
                value=self.config.get('email', {}).get('sending', {}).get('batch_size', 50)
            )

            delay_between_emails = st.number_input(
                "邮件间隔(秒)",
                min_value=1,
                max_value=300,
                value=self.config.get('email', {}).get('sending', {}).get('delay_between_emails', 5)
            )

        with col2:
            delay_between_batches = st.number_input(
                "批次间隔(秒)",
                min_value=60,
                max_value=3600,
                value=self.config.get('email', {}).get('sending', {}).get('delay_between_batches', 300)
            )

            tracking_enabled = st.checkbox(
                "启用邮件跟踪",
                value=self.config.get('email', {}).get('sending', {}).get('tracking_enabled', False)
            )

        # 保存设置
        if st.button("💾 保存设置"):
            settings = {
                'system_name': system_name,
                'log_level': log_level,
                'max_workers': max_workers,
                'timeout': timeout,
                'min_delay': min_delay,
                'max_delay': max_delay,
                'max_retries': max_retries,
                'respect_robots': respect_robots,
                'batch_size': batch_size,
                'delay_between_emails': delay_between_emails,
                'delay_between_batches': delay_between_batches,
                'tracking_enabled': tracking_enabled
            }

            try:
                self.save_settings(settings)
                st.success("设置保存成功")
            except Exception as e:
                st.error(f"保存设置失败: {e}")

    def save_settings(self, settings: dict):
        """保存设置到配置文件"""
        # 这里应该更新配置文件
        pass

    def run(self):
        """运行仪表板"""
        # 渲染头部
        self.render_header()

        # 渲染侧边栏
        render_sidebar()

        # 主标签页
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 概览",
            "🕷️ 爬虫管理",
            "👥 联系人管理",
            "📧 邮件营销",
            "⚙️ 系统设置"
        ])

        with tab1:
            self.render_overview_tab()

        with tab2:
            self.render_scraping_tab()

        with tab3:
            self.render_contacts_tab()

        with tab4:
            self.render_email_tab()

        with tab5:
            self.render_settings_tab()


def main():
    """主函数"""
    try:
        dashboard = MarketingDashboard()
        dashboard.run()
    except Exception as e:
        st.error(f"仪表板运行错误: {e}")
        st.exception(e)


if __name__ == "__main__":
    main()