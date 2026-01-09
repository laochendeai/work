#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit Web Dashboard V2 - 美化增强版

功能增强：
- 新增数据导出页面
- 新增数据库管理页面  
- 新增系统日志页面
- 增强系统概览显示
- 全新的现代化 UI 设计
"""

import sys
import json
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

# 页面配置
st.set_page_config(
    page_title="智能设计营销系统",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# 自定义 CSS 样式
st.markdown("""
<style>
    /* 侧边栏固定展开 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #6366f1 0%, #8b5cf6 100%) !important;
        min-width: 300px !important;
        max-width: 300px !important;
    }

    /* 防止侧边栏折叠 */
    [data-testid="stSidebar"] > div:first-child {
        width: 300px !important;
    }

    /* 隐藏折叠按钮 - 多种选择器 */
    [data-testid="collapsedControl"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        width: 0 !important;
        height: 0 !important;
        position: absolute !important;
        left: -9999px !important;
    }

    [data-testid="stSidebarControl"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
    }

    /* 隐藏侧边栏中的按钮 */
    [data-testid="stSidebar"] button[kind="icon"] {
        display: none !important;
    }

    [data-testid="stSidebar"] button[aria-label*="collapse" i] {
        display: none !important;
    }

    /* 隐藏 Streamlit 默认的汉堡菜单 */
    .katex-mathml {
        display: none !important;
    }

    /* 主容器样式 */
    .main {
        padding: 2rem;
    }

    /* 标题样式 */
    h1 {
        color: #1f2937;
        font-weight: 700;
        padding-bottom: 1rem;
        border-bottom: 3px solid #6366f1;
    }
    
    h2 {
        color: #374151;
        font-weight: 600;
        margin-top: 2rem;
    }
    
    h3 {
        color: #4b5563;
        font-weight: 500;
    }
    
    /* 指标卡片样式 */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.8rem;
    }
    
    /* 按钮样式 */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: 500;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    /* 信息框样式 */
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid;
    }
    
    /* 数据表格样式 */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* 进度条样式 */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #6366f1, #8b5cf6);
    }
    
    /* 成功消息样式 */
    .success-message {
        padding: 1rem;
        border-radius: 8px;
        background-color: #d1fae5;
        color: #065f46;
        border-left: 4px solid #10b981;
        margin: 1rem 0;
    }
    
    /* 错误消息样式 */
    .error-message {
        padding: 1rem;
        border-radius: 8px;
        background-color: #fee2e2;
        color: #991b1b;
        border-left: 4px solid #ef4444;
        margin: 1rem 0;
    }
    
    /* 页面容器 */
    .page-container {
        background-color: #f9fafb;
        padding: 2rem;
        border-radius: 12px;
        margin: 1rem 0;
    }
    
    /* 卡片容器 */
    .card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    /* 页面图标 */
    .page-icon {
        font-size: 2rem;
        margin-right: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ==================== 工具函数 ====================

def get_project_root():
    """获取项目根目录"""
    return Path(__file__).resolve().parents[1]


def get_db_path():
    """获取数据库路径"""
    project_root = get_project_root()
    return project_root / "data" / "marketing.db"


def get_logs_path():
    """获取日志目录路径"""
    project_root = get_project_root()
    return project_root / "logs"


def safe_metric(label, value, delta=None, help_text=None):
    """安全地显示指标"""
    try:
        if delta is not None:
            st.metric(label, value, delta, help=help_text)
        else:
            st.metric(label, value, help=help_text)
    except Exception as e:
        st.metric(label, f"错误: {e}")


def load_settings():
    """加载系统配置"""
    try:
        sys.path.insert(0, str(get_project_root()))
        from config.settings import settings
        return settings
    except Exception:
        return None


# ==================== 系统概览页面 ====================

def render_overview_page():
    """渲染系统概览页面"""
    st.markdown('<h1 style="margin-top:0;">📊 系统概览</h1>', unsafe_allow_html=True)
    
    settings = load_settings()
    
    # 顶部指标卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        try:
            if settings and settings.email_configured:
                safe_metric("📧 邮件配置", "✅ 已配置", "系统可以发送邮件")
            else:
                safe_metric("📧 邮件配置", "❌ 未配置", "请配置邮件功能")
        except Exception:
            safe_metric("📧 邮件配置", "未知")
    
    with col2:
        try:
            db_path = get_db_path()
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                # 联系人数量
                cursor.execute("SELECT COUNT(*) FROM contacts")
                contact_count = cursor.fetchone()[0]
                
                # 爬取数据数量
                cursor.execute("SELECT COUNT(*) FROM scraped_data")
                scraped_count = cursor.fetchone()[0]
                
                conn.close()
                
                safe_metric("👥 联系人", contact_count, f"数据: {scraped_count} 条", "数据库中的联系人和爬取数据")
            else:
                safe_metric("👥 联系人", 0, "数据库不存在")
        except Exception as e:
            safe_metric("👥 联系人", f"错误: {e}")
    
    with col3:
        try:
            logs_path = get_logs_path()
            if logs_path.exists():
                log_files = list(logs_path.glob("*.log"))
                total_size = sum(f.stat().st_size for f in log_files)
                size_mb = total_size / (1024 * 1024)
                safe_metric("📝 日志文件", len(log_files), f"{size_mb:.1f} MB", "系统日志文件")
            else:
                safe_metric("📝 日志文件", 0)
        except Exception:
            safe_metric("📝 日志文件", "错误")
    
    with col4:
        try:
            # 数据源配置数量
            sources_file = get_project_root() / "config" / "sources.yaml"
            if sources_file.exists():
                import yaml
                with open(sources_file) as f:
                    sources_data = yaml.safe_load(f)
                    enabled_count = sum(1 for s in sources_data if s.get('enabled', True))
                    total_count = len(sources_data)
                    safe_metric("🌐 数据源", enabled_count, f"总计: {total_count}", "已启用的数据源")
            else:
                safe_metric("🌐 数据源", "配置文件不存在")
        except Exception:
            safe_metric("🌐 数据源", "错误")
    
    st.markdown("---")
    
    # 快捷操作区域
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🕷️ 数据爬取")
        st.write("从政府采购网站爬取最新招标信息")
        if st.button("🚀 运行爬虫", key="overview_scrape"):
            st.session_state.show_scraping = True
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 👥 提取联系人")
        st.write("从爬取的数据中提取联系人信息")
        if st.button("🔄 提取联系人", key="overview_extract"):
            st.session_state.show_extract = True
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 📧 发送邮件")
        st.write("向联系人发送营销邮件")
        if st.button("✉️ 发送邮件", key="overview_email"):
            st.session_state.show_email = True
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 最近活动
    st.markdown('<div class="page-container">', unsafe_allow_html=True)
    st.markdown("#### 📈 最近活动")
    
    try:
        db_path = get_db_path()
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            
            # 最近爬取的数据
            recent_scraped = pd.read_sql_query("""
                SELECT source, title, created_at 
                FROM scraped_data 
                ORDER BY created_at DESC 
                LIMIT 5
            """, conn)
            
            if not recent_scraped.empty:
                recent_scraped['created_at'] = pd.to_datetime(recent_scraped['created_at'])
                st.dataframe(recent_scraped, use_container_width=True, hide_index=True)
            else:
                st.info("暂无最近活动")
            
            conn.close()
    except Exception as e:
        st.error(f"读取最近活动失败: {e}")
    
    st.markdown('</div>', unsafe_allow_html=True)


# ==================== 数据爬取页面 ====================

def render_scraping_page():
    """渲染数据爬取页面"""
    st.markdown('<h1 style="margin-top:0;">🕷️ 数据爬取</h1>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 📋 爬取配置")
        
        keyword = st.text_input("关键词", placeholder="输入搜索关键词")
        max_items = st.slider("最大爬取数量", 10, 1000, 100)
        source_filter = st.multiselect(
            "数据源筛选",
            ["全部", "中央", "省级", "市级"],
            default=["全部"]
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 📊 当前状态")
        
        try:
            from core.system import MarketingSystem
            system = MarketingSystem()
            # 这里可以添加实时状态显示
            st.info("✅ 爬虫引擎就绪")
        except Exception as e:
            st.error(f"❌ 爬虫初始化失败: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 开始爬取", type="primary", use_container_width=True):
            with st.spinner("正在爬取数据..."):
                try:
                    from core.scraper import scraper
                    results = list(scraper.scrape_all_sources())
                    st.success(f"✅ 爬取完成！获得 {len(results)} 条数据")
                except Exception as e:
                    st.error(f"❌ 爬取失败: {e}")
    
    with col2:
        if st.button("⏸️ 暂停爬取", use_container_width=True):
            st.info("爬取暂停功能开发中...")
    
    with col3:
        if st.button("🔄 查看进度", use_container_width=True):
            st.info("实时进度监控开发中...")


# ==================== 联系人管理页面 ====================

def render_contacts_page():
    """渲染联系人管理页面"""
    st.markdown('<h1 style="margin-top:0;">👥 联系人管理</h1>', unsafe_allow_html=True)
    
    # 筛选和搜索
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_keyword = st.text_input("🔍 搜索", placeholder="搜索姓名、单位、电话...")
    
    with col2:
        filter_source = st.selectbox("📂 数据来源", ["全部", "网站爬取", "手动添加", "导入"])
    
    with col3:
        sort_by = st.selectbox("📊 排序方式", ["最新", "姓名", "单位"])
    
    st.markdown("---")
    
    try:
        db_path = get_db_path()
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            
            # 构建查询
            query = "SELECT * FROM contacts"
            params = []
            
            if search_keyword:
                query += " WHERE name LIKE ? OR company LIKE ? OR phone LIKE ?"
                params.extend([f"%{search_keyword}%"] * 3)
            
            query += " ORDER BY created_at DESC LIMIT 100"
            
            contacts_df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if not contacts_df.empty:
                st.dataframe(contacts_df, use_container_width=True, hide_index=True)
                
                # 批量操作
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("📥 导出选中"):
                        st.info("导出功能开发中...")
                with col2:
                    if st.button("✉️ 批量发送邮件"):
                        st.info("批量发送功能开发中...")
                with col3:
                    if st.button("🗑️ 删除选中"):
                        st.info("删除功能开发中...")
            else:
                st.markdown('<div class="card" style="text-align:center;">', unsafe_allow_html=True)
                st.markdown("#### 📭 暂无联系人数据")
                st.write("请先运行数据爬取，然后提取联系人信息")
                if st.button("🚀 开始爬取数据"):
                    st.session_state.show_scraping = True
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card" style="text-align:center;">', unsafe_allow_html=True)
            st.markdown("#### 📭 数据库不存在")
            st.write("请先运行数据爬取创建数据库")
            st.markdown('</div>', unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"❌ 读取联系人数据失败: {e}")


# ==================== 邮件营销页面 ====================

def render_email_page():
    """渲染邮件营销页面"""
    st.markdown('<h1 style="margin-top:0;">📧 邮件营销</h1>', unsafe_allow_html=True)
    
    settings = load_settings()
    
    # 邮件配置状态
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### ⚙️ 邮件配置")
        
        if settings and settings.email_configured:
            st.success("✅ 邮件已配置")
            
            # 显示配置信息（脱敏）
            try:
                config = settings.load_user_config()
                email_config = config.get('email', {})
                if email_config.get('smtp_server'):
                    st.write(f"**SMTP 服务器**: {email_config['smtp_server']}")
                if email_config.get('smtp_port'):
                    st.write(f"**端口**: {email_config['smtp_port']}")
                if email_config.get('sender'):
                    sender = email_config['sender']
                    masked_sender = sender[:3] + '***' + sender[sender.index('@'):] if '@' in sender else '***'
                    st.write(f"**发件人**: {masked_sender}")
            except Exception:
                pass
        else:
            st.warning("⚠️ 邮件未配置")
            st.info("请运行以下命令配置邮件：")
            st.code("python main.py --config", language="bash")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🧪 测试邮件")
        
        if settings and settings.email_configured:
            test_recipient = st.text_input("收件人", placeholder="test@example.com")
            
            if st.button("📤 发送测试邮件", type="primary"):
                try:
                    from core.emailer import emailer
                    if emailer.send_test_email():
                        st.success("✅ 测试邮件发送成功")
                    else:
                        st.error("❌ 测试邮件发送失败")
                except Exception as e:
                    st.error(f"❌ 发送失败: {e}")
        else:
            st.info("请先配置邮件功能")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 批量发送区域
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### ✉️ 批量发送")
    
    col1, col2 = st.columns(2)
    
    with col1:
        email_template = st.text_area(
            "邮件模板",
            value="""尊敬的 {name}：

您好！

我们注意到贵单位近期发布的 {keyword} 相关采购信息，特此联系。

期待与您合作！

此致
敬礼""",
            height=200,
            help="可使用 {name}, {company}, {keyword} 等变量"
        )
    
    with col2:
        st.markdown("#### 📊 发送统计")
        st.metric("待发送", "0")
        st.metric("已发送", "0")
        st.metric("发送成功", "0")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 预览邮件"):
            st.info("预览功能开发中...")
    
    with col2:
        if st.button("🚀 开始发送", type="primary"):
            st.info("批量发送功能开发中...")
    
    with col3:
        if st.button("📊 查看历史"):
            st.info("发送历史功能开发中...")
    
    st.markdown('</div>', unsafe_allow_html=True)


# ==================== 数据导出页面 ====================

def render_export_page():
    """渲染数据导出页面"""
    st.markdown('<h1 style="margin-top:0;">📥 数据导出</h1>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 导出设置")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        export_type = st.selectbox(
            "导出类型",
            ["联系人", "爬取数据", "结构化数据", "全部数据"]
        )
    
    with col2:
        export_format = st.selectbox(
            "导出格式",
            ["Excel (.xlsx)", "CSV (.csv)", "JSON (.json)", "SQL (.sql)"]
        )
    
    with col3:
        date_range = st.selectbox(
            "时间范围",
            ["全部", "今天", "最近7天", "最近30天", "自定义"]
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 导出预览
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 📋 导出预览")
    
    try:
        db_path = get_db_path()
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            
            if export_type == "联系人":
                df = pd.read_sql_query("SELECT * FROM contacts LIMIT 10", conn)
            elif export_type == "爬取数据":
                df = pd.read_sql_query("SELECT * FROM scraped_data LIMIT 10", conn)
            elif export_type == "结构化数据":
                df = pd.read_sql_query("SELECT * FROM structured_contacts LIMIT 10", conn)
            else:
                df = pd.DataFrame()
            
            conn.close()
            
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                st.caption(f"显示前 10 条记录，共 {len(df)} 条")
            else:
                st.info("该类型暂无数据")
        else:
            st.info("数据库不存在")
    
    except Exception as e:
        st.error(f"读取数据失败: {e}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 导出按钮
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 导出文件", type="primary", use_container_width=True):
            try:
                db_path = get_db_path()
                if db_path.exists():
                    conn = sqlite3.connect(str(db_path))
                    
                    if export_type == "联系人":
                        df = pd.read_sql_query("SELECT * FROM contacts", conn)
                    elif export_type == "爬取数据":
                        df = pd.read_sql_query("SELECT * FROM scraped_data", conn)
                    else:
                        df = pd.DataFrame()
                    
                    conn.close()
                    
                    if not df.empty:
                        # 生成文件名
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        if export_format.startswith("Excel"):
                            file_name = f"export_{timestamp}.xlsx"
                            df.to_excel(file_name, index=False)
                        elif export_format.startswith("CSV"):
                            file_name = f"export_{timestamp}.csv"
                            df.to_csv(file_name, index=False, encoding='utf-8-sig')
                        elif export_format.startswith("JSON"):
                            file_name = f"export_{timestamp}.json"
                            df.to_json(file_name, orient='records', force_ascii=False, indent=2)
                        
                        st.success(f"✅ 导出成功！文件：{file_name}")
                        
                        # 提供下载
                        with open(file_name, 'rb') as f:
                            st.download_button(
                                label="⬇️ 下载文件",
                                data=f,
                                file_name=file_name,
                                mime='application/octet-stream'
                            )
                    else:
                        st.warning("没有数据可导出")
            except Exception as e:
                st.error(f"导出失败: {e}")
    
    with col2:
        if st.button("📋 复制到剪贴板", use_container_width=True):
            st.info("复制功能开发中...")
    
    with col3:
        if st.button("🔄 重置筛选", use_container_width=True):
            st.rerun()


# ==================== 数据库管理页面 ====================

def render_database_page():
    """渲染数据库管理页面"""
    st.markdown('<h1 style="margin-top:0;">🗄️ 数据库管理</h1>', unsafe_allow_html=True)
    
    # 数据库状态
    col1, col2, col3, col4 = st.columns(4)
    
    try:
        db_path = get_db_path()
        
        with col1:
            if db_path.exists():
                file_size = db_path.stat().st_size / (1024 * 1024)
                safe_metric("💾 数据库大小", f"{file_size:.2f} MB")
            else:
                safe_metric("💾 数据库大小", "不存在")
        
        with col2:
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                # 统计各表记录数
                tables = ['contacts', 'scraped_data', 'structured_contacts']
                total_records = 0
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        total_records += cursor.fetchone()[0]
                    except:
                        pass
                
                conn.close()
                safe_metric("📊 总记录数", f"{total_records:,}")
            else:
                safe_metric("📊 总记录数", "0")
        
        with col3:
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                conn.close()
                safe_metric("📋 表数量", table_count)
            else:
                safe_metric("📋 表数量", "0")
        
        with col4:
            last_backup = "无"
            safe_metric("🔄 最后备份", last_backup)
    
    except Exception as e:
        st.error(f"读取数据库状态失败: {e}")
    
    st.markdown("---")
    
    # 数据库操作
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🧹 数据清理")
        
        st.write("清理数据库可以提高性能和节省空间")
        
        clean_options = st.multiselect(
            "选择清理选项",
            [
                "删除重复数据",
                "清理无效联系人",
                "删除旧数据（>90天）",
                "优化数据库（VACUUM）"
            ],
            default=["优化数据库（VACUUM）"]
        )
        
        if st.button("🚀 开始清理", type="primary"):
            try:
                from core.system import MarketingSystem
                system = MarketingSystem()
                system.clean_database()
                st.success("✅ 数据库清理完成！")
            except Exception as e:
                st.error(f"❌ 清理失败: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 💾 备份与恢复")
        
        st.write("定期备份数据可以防止数据丢失")
        
        backup_path = st.text_input("备份路径", value="./backups/")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 创建备份"):
                st.info("备份功能开发中...")
        
        with col2:
            if st.button("📤 恢复备份"):
                st.info("恢复功能开发中...")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 数据库详细信息
    with st.expander("🔍 查看数据库详情"):
        try:
            db_path = get_db_path()
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                tables = cursor.fetchall()
                
                for table_name, in tables:
                    st.markdown(f"##### 📋 {table_name}")
                    
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    
                    col_info = []
                    for col in columns:
                        col_info.append({
                            "列名": col[1],
                            "类型": col[2],
                            "非空": "是" if col[3] else "否",
                            "默认值": col[4] if col[4] else "-",
                        })
                    
                    st.dataframe(pd.DataFrame(col_info), use_container_width=True, hide_index=True)
                    
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    st.caption(f"记录数: {count:,}")
                    
                    st.markdown("---")
                
                conn.close()
        except Exception as e:
            st.error(f"读取数据库详情失败: {e}")


# ==================== 系统日志页面 ====================

def render_logs_page():
    """渲染系统日志页面"""
    st.markdown('<h1 style="margin-top:0;">📋 系统日志</h1>', unsafe_allow_html=True)
    
    # 日志文件选择
    logs_path = get_logs_path()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if logs_path.exists():
            log_files = [f.name for f in logs_path.glob("*.log")]
            selected_log = st.selectbox("选择日志文件", log_files) if log_files else None
        else:
            st.warning("日志目录不存在")
            selected_log = None
    
    with col2:
        log_level = st.selectbox("日志级别", ["全部", "INFO", "WARNING", "ERROR", "DEBUG"])
    
    with col3:
        auto_refresh = st.checkbox("自动刷新", value=False)
    
    st.markdown("---")
    
    if selected_log:
        log_file_path = logs_path / selected_log
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                # 读取最后 1000 行
                lines = f.readlines()[-1000:]
                
                # 筛选日志级别
                if log_level != "全部":
                    lines = [l for l in lines if log_level in l]
                
                # 显示日志
                st.code(''.join(lines), language=None, line_numbers=True)
                
                st.caption(f"显示最后 {len(lines)} 行")
        
        except Exception as e:
            st.error(f"读取日志文件失败: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 日志操作
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 刷新日志"):
                st.rerun()
        
        with col2:
            if st.button("📥 下载日志"):
                try:
                    with open(log_file_path, 'r', encoding='utf-8') as f:
                        st.download_button(
                            label="⬇️ 下载",
                            data=f,
                            file_name=selected_log,
                            mime='text/plain'
                        )
                except Exception as e:
                    st.error(f"下载失败: {e}")
        
        with col3:
            if st.button("🗑️ 清空日志"):
                st.warning("清空日志功能开发中...")
    else:
        st.markdown('<div class="card" style="text-align:center;">', unsafe_allow_html=True)
        st.markdown("#### 📭 暂无日志文件")
        st.write("系统运行时会自动生成日志文件")
        st.markdown('</div>', unsafe_allow_html=True)


# ==================== 系统设置页面 ====================

def render_settings_page():
    """渲染系统设置页面"""
    st.markdown('<h1 style="margin-top:0;">⚙️ 系统设置</h1>', unsafe_allow_html=True)
    
    # 系统信息
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 📊 系统信息")
        
        safe_metric("Python版本", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        safe_metric("工作目录", str(get_project_root()))
        safe_metric("系统类型", "智能设计营销系统")
        safe_metric("版本", "3.0.0")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🔧 配置信息")
        
        try:
            settings = load_settings()
            if settings:
                config_data = settings.load_user_config()
                st.json(config_data)
        except Exception as e:
            st.error(f"读取配置失败: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 快捷命令
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### ⚡ 命令行快捷方式")
    
    st.markdown("""
    | 功能 | 命令 |
    |------|------|
    | 运行爬虫 | `python main.py --scrape` |
    | 提取联系人 | `python main.py --extract` |
    | 发送邮件 | `python main.py --email` |
    | 系统配置 | `python main.py --config` |
    | 查看状态 | `python main.py --status` |
    | 清理数据库 | `python main.py --db-clean` |
    """)
    
    st.markdown('</div>', unsafe_allow_html=True)


# ==================== 主程序 ====================

def main():
    """主程序"""
    
    # 侧边栏
    with st.sidebar:
        st.markdown("""
        # 🚀 智能设计营销系统
        
        ---
        """)
        
        page = st.selectbox(
            "📋 功能菜单",
            [
                "📊 系统概览",
                "🕷️ 数据爬取",
                "👥 联系人管理",
                "📧 邮件营销",
                "📥 数据导出",
                "🗄️ 数据库管理",
                "📋 系统日志",
                "⚙️ 系统设置",
            ],
        )
        
        st.markdown("---")

        # 添加 JavaScript 来隐藏折叠按钮
        st.markdown("""
        <script>
        // 隐藏侧边栏折叠按钮
        function hideCollapseButton() {
            const buttons = document.querySelectorAll('[data-testid="stSidebar"] button');
            buttons.forEach(btn => {
                const ariaLabel = btn.getAttribute('aria-label') || '';
                if (ariaLabel.toLowerCase().includes('collapse') ||
                    btn.getAttribute('kind') === 'icon') {
                    btn.style.display = 'none';
                    btn.style.visibility = 'hidden';
                    btn.style.opacity = '0';
                    btn.style.width = '0';
                    btn.style.height = '0';
                }
            });

            // 隐藏特定的控制元素
            const controls = document.querySelectorAll('[data-testid="collapsedControl"], [data-testid="stSidebarControl"]');
            controls.forEach(ctrl => {
                ctrl.style.display = 'none';
                ctrl.style.visibility = 'hidden';
            });
        }

        // 页面加载时执行
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', hideCollapseButton);
        } else {
            hideCollapseButton();
        }

        // 使用 MutationObserver 监听 DOM 变化
        const observer = new MutationObserver(hideCollapseButton);
        observer.observe(document.body, { childList: true, subtree: true });
        </script>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # 系统状态指示器
        st.markdown("### 🔴 系统状态")
        
        try:
            db_path = get_db_path()
            if db_path.exists():
                st.success("✅ 数据库正常")
            else:
                st.warning("⚠️ 数据库不存在")
            
            settings = load_settings()
            if settings and settings.email_configured:
                st.success("✅ 邮件已配置")
            else:
                st.warning("⚠️ 邮件未配置")
        except Exception:
            st.error("❌ 系统检查失败")
        
        st.markdown("---")
        
        # 快捷操作
        st.markdown("### ⚡ 快捷操作")
        
        if st.button("🔄 刷新页面"):
            st.rerun()
        
        if st.button("📖 使用文档"):
            st.info("文档功能开发中...")
    
    # 路由到对应页面
    if "系统概览" in page:
        render_overview_page()
    elif "数据爬取" in page:
        render_scraping_page()
    elif "联系人管理" in page:
        render_contacts_page()
    elif "邮件营销" in page:
        render_email_page()
    elif "数据导出" in page:
        render_export_page()
    elif "数据库管理" in page:
        render_database_page()
    elif "系统日志" in page:
        render_logs_page()
    elif "系统设置" in page:
        render_settings_page()
    
    # 页脚
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #6b7280; padding: 1rem;'>
        <b>智能设计营销系统 v3.0</b> | 统一架构 · 拒绝代码重复
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
