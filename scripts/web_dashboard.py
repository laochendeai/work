#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit Web Dashboard

运行方式：
  - `python main.py --web`
  - 或直接：`python -m streamlit run scripts/web_dashboard.py`
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# 保证从任意工作目录启动都能 import 项目模块
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from config.settings import settings
except Exception:  # pragma: no cover
    settings = None  # type: ignore

st.set_page_config(page_title="智能设计营销系统", page_icon="🚀", layout="wide")

st.title("🚀 智能设计营销系统")
st.markdown("---")

# 侧边栏
st.sidebar.title("📋 功能菜单")
page = st.sidebar.selectbox(
    "选择页面",
    [
        "系统概览",
        "数据爬取",
        "联系人管理",
        "邮件营销",
        "系统设置",
    ],
)


def _safe_metric(label: str, value):
    try:
        st.metric(label, value)
    except Exception:
        st.metric(label, "错误")

def _get_db_path() -> Path:
    if settings is None:
        return PROJECT_ROOT / "data" / "marketing.db"
    return Path(settings.get("storage.database_path", str(PROJECT_ROOT / "data" / "marketing.db")))


if page == "系统概览":
    st.header("📊 系统概览")

    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            from config.settings import settings

            _safe_metric("📧 邮件配置", "已配置" if settings.email_configured else "未配置")
        except Exception:
            _safe_metric("📧 邮件配置", "未知")

    with col2:
        db_path = _get_db_path()
        if db_path.exists():
            try:
                import sqlite3

                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM contacts")
                contact_count = cursor.fetchone()[0]
                conn.close()
                _safe_metric("👥 联系人数", contact_count)
            except Exception:
                _safe_metric("👥 联系人数", "错误")
        else:
            _safe_metric("👥 联系人数", 0)

    with col3:
        log_files = list(Path("logs").glob("*.log"))
        _safe_metric("📝 日志文件", len(log_files))

    st.info(
        """
**使用提示:**
- 运行爬虫: `python main.py --scrape`
- 提取联系人: `python main.py --extract`
- 发送邮件: `python main.py --email`
- 配置系统: `python main.py --config`
"""
    )

elif page == "数据爬取":
    st.header("🕷️ 数据爬取")
    st.info("点击下方按钮运行爬虫")

    if st.button("🚀 运行爬虫"):
        with st.spinner("正在爬取数据..."):
            try:
                from core.scraper import scraper

                scraped_items = list(scraper.scrape_all_sources())
                st.success(f"✅ 爬取完成，获得 {len(scraped_items)} 条数据")
            except Exception as e:
                st.error(f"❌ 爬取失败: {e}")

elif page == "联系人管理":
    st.header("👥 联系人管理")

    try:
        import sqlite3

        db_path = _get_db_path()
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            contacts_df = pd.read_sql_query("SELECT * FROM contacts ORDER BY created_at DESC LIMIT 50", conn)
            conn.close()

            if not contacts_df.empty:
                st.dataframe(contacts_df)
            else:
                st.info("📭 暂无联系人数据")
        else:
            st.info("📭 数据库不存在，请先运行爬虫")

    except Exception as e:
        st.error(f"❌ 读取联系人数据失败: {e}")

elif page == "邮件营销":
    st.header("📧 邮件营销")

    try:
        from config.settings import settings
        from core.emailer import emailer

        if settings.email_configured:
            st.success("✅ 邮件已配置")

            if st.button("🧪 发送测试邮件"):
                if emailer.send_test_email():
                    st.success("✅ 测试邮件发送成功")
                else:
                    st.error("❌ 测试邮件发送失败")
        else:
            st.warning("⚠️ 邮件未配置")
            st.info("请运行: python main.py --config")

    except Exception as e:
        st.error(f"❌ 邮件配置检查失败: {e}")

elif page == "系统设置":
    st.header("⚙️ 系统设置")

    st.subheader("📊 系统信息")
    col1, col2 = st.columns(2)

    with col1:
        _safe_metric("Python版本", f"{sys.version_info.major}.{sys.version_info.minor}")
        _safe_metric("工作目录", str(Path.cwd()))

    with col2:
        _safe_metric("系统类型", "智能设计营销系统")
        _safe_metric("版本", "2.0.0")

    st.subheader("📝 配置文件")

    try:
        from config.settings import settings

        config_data = settings.load_user_config()
        st.json(config_data)
    except Exception as e:
        st.error(f"❌ 读取配置失败: {e}")

st.markdown("---")
st.markdown("**智能设计营销系统 - 统一架构，拒绝代码重复**")
