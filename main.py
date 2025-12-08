#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能设计营销系统 - 统一启动入口
唯一入口，整合所有功能，杜绝重复代码
"""

import argparse
import asyncio
import json
import logging
import os
import random
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from core.scraper import scraper
from core.extractor import extractor
from core.emailer import emailer
from core import playwright_fetcher
from core.exceptions import PlaywrightFallback
from core.queue import push_start_urls, pop_url, requeue_url
from core.retry import mark_failed, get_failed
from core.metrics import start_metrics_server, record_request, record_fallback

class MarketingSystem:
    """智能设计营销系统主类"""

    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        start_metrics_server()

    def setup_logging(self):
        """设置日志"""
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(logs_dir / 'marketing.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

    def run_scraper(self):
        """运行爬虫"""
        print("🕷️  启动数据爬虫...")

        # 测试网络连接（可选）
        if not scraper.test_connection():
            print("⚠️  网络连接测试失败，但仍尝试爬取")
        else:
            print("✅ 网络连接正常")

        # 爬取数据
        scraped_items = list(scraper.scrape_all_sources())
        print(f"✅ 爬取完成，获得 {len(scraped_items)} 条数据")

        if scraped_items:
            asyncio.run(self._process_queue(scraped_items))
            scraped_items = self._reload_details(scraped_items)

            print("👥 提取联系人信息...")
            contacts = extractor.extract_from_scraped_data(scraped_items)
            print(f"✅ 提取到 {len(contacts)} 个有效联系人")

            # 保存到数据库
            if contacts:
                extractor.save_to_database(contacts)

                # 导出Excel
                try:
                    extractor.export_to_excel(contacts)
                except Exception as e:
                    print(f"⚠️  Excel导出失败: {e}")

        stats = scraper.get_scraping_stats()
        print(f"📦 当前待提取详情: {stats.get('pending_detail_extraction', 0)} 条, 总计 {stats.get('scraped_data_total', 0)} 条")
        last_cleanup = stats.get('retention', {}).get('last_cleanup', {})
        if last_cleanup.get('expired') or last_cleanup.get('overflow'):
            print(f"🧹 本轮清理: 过期 {last_cleanup.get('expired', 0)} 条, 超限 {last_cleanup.get('overflow', 0)} 条")

        return len(scraped_items)

    async def _process_queue(self, scraped_items):
        """把待抓取详情推入队列并并发处理"""
        payloads = []
        for item in scraped_items:
            link = item.get('link')
            if not link:
                continue
            payload = {
                'link': link,
                'render_mode': item.get('render_mode', ''),
                'wait_selector': item.get('wait_selector'),
                'source': item.get('source', '')
            }
            actions = item.get('actions')
            if actions:
                payload['actions'] = actions
            payloads.append(json.dumps(payload, ensure_ascii=False))

        await push_start_urls(payloads)
        await self._run_workers(persistent=False)

    async def _run_workers(self, persistent: bool) -> None:
        worker_count = int(os.getenv('WORKERS', '4'))
        tasks = [
            asyncio.create_task(self._queue_worker(i, persistent=persistent))
            for i in range(worker_count)
        ]
        await asyncio.gather(*tasks)

    async def _queue_worker(self, worker_id: int, persistent: bool = False):
        """单个 Redis worker"""
        while True:
            payload = await pop_url(timeout=5)
            if payload is None:
                if persistent:
                    await asyncio.sleep(1)
                    continue
                break
            await asyncio.sleep(random.uniform(0.5, 1.5))
            item = json.loads(payload)
            try:
                await self._process_single_item(item)
            except PlaywrightFallback:
                record_fallback()
                downgraded = dict(item)
                downgraded['render_mode'] = 'http'
                downgraded.pop('wait_selector', None)
                downgraded.pop('actions', None)
                await requeue_url(json.dumps(downgraded, ensure_ascii=False))
            except Exception as exc:
                await mark_failed(item.get('link', ''), str(exc))

    async def _process_single_item(self, item: dict):
        """根据 render_mode 处理单条记录"""
        link = item.get('link')
        if not link:
            raise ValueError("missing link")

        if item.get('render_mode') == 'playwright':
            wait_selector = item.get('wait_selector')
            actions = item.get('actions')
            try:
                html = await playwright_fetcher.fetch(link, wait_selector, actions)
            except PlaywrightFallback:
                record_request('playwright', 'fail')
                raise
            record_request('playwright', 'success')
            item['detail_content'] = html
            item['detail_scraped_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            scraper._update_detail_content(item)
        else:
            try:
                detail_item = scraper.scrape_detail({'link': link, 'source': item.get('source', 'detail')})
            except Exception:
                record_request('http', 'fail')
                raise
            if detail_item.get('detail_content'):
                record_request('http', 'success')
                scraper._update_detail_content(detail_item)
            else:
                record_request('http', 'fail')
                raise ValueError("empty detail content")

    def _reload_details(self, items):
        """从数据库加载详情内容"""
        db_path = settings.get('storage.database_path', 'data/marketing.db')
        if not Path(db_path).exists():
            return []
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        refreshed = []
        for item in items:
            link = item.get('link')
            if not link:
                continue
            cursor.execute("SELECT detail_content FROM scraped_data WHERE link = ?", (link,))
            row = cursor.fetchone()
            if row and row[0]:
                updated = dict(item)
                updated['detail_content'] = row[0]
                refreshed.append(updated)
        conn.close()
        return refreshed

    def run_extractor(self):
        """运行联系人提取器"""
        print("👥 启动联系人提取...")

        try:
            # 从数据库加载爬取的数据
            import sqlite3
            db_path = settings.get('storage.database_path', 'data/marketing.db')

            if not Path(db_path).exists():
                print("❌ 数据库不存在，请先运行爬虫")
                return 0

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, title, source, link, scraped_at, detail_content
                FROM scraped_data
                WHERE detail_content IS NOT NULL AND processed = 0
                ORDER BY datetime(COALESCE(detail_scraped_at, scraped_at)) DESC
                LIMIT 100
            ''')

            scraped_items = []
            for row in cursor.fetchall():
                scraped_items.append({
                    'id': row[0],
                    'title': row[1],
                    'source': row[2],
                    'link': row[3],
                    'scraped_at': row[4],
                    'detail_content': row[5]
                })

            conn.close()

            if not scraped_items:
                print("❌ 没有找到可提取的数据")
                return 0

            # 提取联系人
            contacts = extractor.extract_from_scraped_data(scraped_items)
            print(f"✅ 提取到 {len(contacts)} 个有效联系人")

            # 保存到数据库
            extractor.save_to_database(contacts)

            # 导出Excel
            extractor.export_to_excel(contacts)

            # 标记这些记录已处理，避免二次重复提取
            try:
                scraper.mark_items_processed([item['id'] for item in scraped_items if 'id' in item])
            except Exception as mark_err:
                print(f"⚠️  更新处理状态失败: {mark_err}")

            return len(contacts)

        except Exception as e:
            print(f"❌ 提取联系人失败: {e}")
            return 0

    def run_emailer(self):
        """运行邮件发送"""
        print("📧 启动邮件发送...")

        # 检查邮件配置
        if not settings.email_configured:
            print("❌ 邮件未配置，请先配置邮件信息")
            print("💡 运行: python main.py --config")
            return

        # 测试邮件配置
        if not emailer.test_config():
            print("❌ 邮件配置测试失败，请检查配置信息")
            return

        # 加载联系人
        contacts = emailer.load_contacts_from_database()
        if not contacts:
            print("❌ 没有找到联系人数据")
            return

        print(f"📋 找到 {len(contacts)} 个联系人")

        # 准备邮件数据
        emails_to_send = []
        for contact in contacts[:10]:  # 限制发送数量
            if contact['emails']:
                emails_to_send.append({
                    'email': contact['emails'][0],
                    'name': contact['names'][0] if contact['names'] else '项目负责人',
                    'company': contact['companies'][0] if contact['companies'] else '',
                    'title': contact['title']
                })

        if not emails_to_send:
            print("❌ 没有找到有效的邮箱地址")
            return

        # 发送测试邮件
        print("🧪 发送测试邮件...")
        if emailer.send_test_email():
            print("✅ 测试邮件发送成功")
        else:
            print("❌ 测试邮件发送失败")
            return

        # 询问是否批量发送
        send_batch = input("\n📤 是否发送批量邮件? (y/N): ").lower()
        if send_batch == 'y':
            print(f"📧 准备发送 {len(emails_to_send)} 封邮件...")
            results = emailer.send_batch_emails(emails_to_send, 'marketing')
            print(f"✅ 发送完成: 成功 {results['success']}, 失败 {results['failed']}")

    def run_web(self):
        """启动Web界面"""
        print("🌐 启动Web界面...")

        try:
            # 创建简单的Web界面
            web_content = '''
import streamlit as st
import sys
import os
from pathlib import Path
import pandas as pd

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

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
        # 检查邮件配置
        try:
            from config.settings import settings
            email_configured = settings.email_configured
            st.metric("📧 邮件配置", "已配置" if email_configured else "未配置")
        except:
            st.metric("📧 邮件配置", "未知")

    with col2:
        # 检查数据库文件
        db_path = Path("data/marketing.db")
        if db_path.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM contacts")
                contact_count = cursor.fetchone()[0]
                st.metric("👥 联系人数", contact_count)
                conn.close()
            except:
                st.metric("👥 联系人数", "错误")
        else:
            st.metric("👥 联系人数", 0)

    with col3:
        # 检查日志文件
        log_files = list(Path("logs").glob("*.log"))
        st.metric("📝 日志文件", len(log_files))

    st.info("""
    **💡 使用提示:**
    - 运行爬虫: `python main.py --scrape`
    - 提取联系人: `python main.py --extract`
    - 发送邮件: `python main.py --email`
    - 配置系统: `python main.py --config`
    """)

elif page == "数据爬取":
    st.header("🕷️ 数据爬取")

    st.info("💡 点击下方按钮运行爬虫")

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
        from core.extractor import extractor
        import sqlite3

        db_path = Path("data/marketing.db")
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
        st.metric("Python版本", f"{sys.version_info.major}.{sys.version_info.minor}")
        st.metric("工作目录", str(Path.cwd()))

    with col2:
        st.metric("系统类型", "智能设计营销系统")
        st.metric("版本", "2.0.0")

    st.subheader("📝 配置文件")

    try:
        from config.settings import settings
        config_data = settings.load_user_config()
        st.json(config_data)
    except Exception as e:
        st.error(f"❌ 读取配置失败: {e}")

st.markdown("---")
st.markdown("**🚀 智能设计营销系统 - 统一架构，拒绝代码重复**")
'''

            # 保存Web文件
            web_file = Path("web_dashboard.py")
            web_file.write_text(web_content, encoding='utf-8')

            # 启动Streamlit
            import subprocess
            print(f"🌐 Web界面启动: http://localhost:8501")
            print("💡 按 Ctrl+C 停止服务")

            subprocess.run([sys.executable, "-m", "streamlit", "run", str(web_file)])

        except Exception as e:
            print(f"❌ 启动Web界面失败: {e}")
            print("💡 请安装streamlit: pip install streamlit")

    def run_config(self):
        """运行配置向导"""
        print("⚙️ 系统配置向导")

        # 用户信息配置
        print("\n📋 配置用户信息:")
        name = input("姓名: ").strip() or "设计用户"
        email = input("邮箱: ").strip()
        company = input("公司/单位: ").strip()

        settings.set('user_info.name', name)
        settings.set('user_info.email', email)
        settings.set('user_info.company', company)

        # 邮件配置
        print("\n📧 配置邮件发送:")
        if not settings.email_configured:
            smtp_server = input("SMTP服务器 (默认: smtp.qq.com): ").strip() or "smtp.qq.com"
            smtp_port = int(input("SMTP端口 (默认: 587): ").strip() or "587")
            sender_email = input("发件邮箱: ").strip()
            sender_password = input("邮箱密码/应用专用密码: ").strip()
            sender_name = input("发件人姓名 (默认: 设计营销助手): ").strip() or "设计营销助手"

            settings.set('email.smtp_server', smtp_server)
            settings.set('email.smtp_port', smtp_port)
            settings.set('email.sender_email', sender_email)
            settings.set('email.sender_password', sender_password)
            settings.set('email.sender_name', sender_name)

            # 测试邮件配置
            print("\n🧪 测试邮件配置...")
            if emailer.test_config():
                print("✅ 邮件配置测试成功")
                settings.set('email.configured', True)
            else:
                print("❌ 邮件配置测试失败")
                settings.set('email.configured', False)

        # AI处理配置
        print("\n🤖 配置AI智能处理:")
        ai_enabled = input("启用AI智能联系人提取? (y/N): ").lower() == 'y'
        settings.set('ai_processing.enabled', ai_enabled)

        if ai_enabled:
            print("\n   AI提供商选择:")
            print("   1. OpenAI (推荐)")
            print("   2. 自定义OpenAI兼容接口")

            provider_choice = input("   选择 (1-2): ").strip()
            if provider_choice == "2":
                provider = "openai"  # 使用openai兼容格式
                base_url = input("   API基础URL: ").strip()
                settings.set('ai_processing.provider', provider)
                settings.set('ai_processing.base_url', base_url)
            else:
                provider = "openai"
                settings.set('ai_processing.provider', provider)
                settings.set('ai_processing.base_url', '')

            api_key = input("   API密钥: ").strip()
            model = input("   模型 (默认: gpt-3.5-turbo): ").strip() or "gpt-3.5-turbo"

            settings.set('ai_processing.api_key', api_key)
            settings.set('ai_processing.model', model)

            print("\n   高级配置 (使用默认值):")
            batch_size = input("   批处理大小 (默认: 10): ").strip()
            if batch_size:
                settings.set('ai_processing.batch_size', int(batch_size))

            max_tokens = input("   最大令牌数 (默认: 1000): ").strip()
            if max_tokens:
                settings.set('ai_processing.max_tokens', int(max_tokens))

        # 数据源配置
        print("\n🕷️ 配置数据源:")
        sources = settings.get('scraper.sources', {})

        for source_id, source_config in sources.items():
            enabled = input(f"启用 {source_config['name']}? (y/N): ").lower() == 'y'
            settings.set(f'scraper.sources.{source_id}.enabled', enabled)

        print("\n✅ 配置完成！")

    def show_status(self):
        """显示系统状态"""
        print("📊 系统状态")
        print("=" * 40)

        # 基本信息
        print(f"🏢 用户信息:")
        print(f"   姓名: {settings.get('user_info.name', '未配置')}")
        print(f"   邮箱: {settings.get('user_info.email', '未配置')}")
        print(f"   公司: {settings.get('user_info.company', '未配置')}")

        # 邮件配置
        print(f"\n📧 邮件配置: {'✅ 已配置' if settings.email_configured else '❌ 未配置'}")

        # AI配置
        ai_config = settings.get('ai_processing', {})
        ai_enabled = ai_config.get('enabled', False)
        ai_configured = bool(ai_enabled and ai_config.get('api_key'))

        print(f"\n🤖 AI智能处理: {'✅ 已配置' if ai_configured else '❌ 未配置'}")
        if ai_configured:
            print(f"   提供商: {ai_config.get('provider', 'N/A')}")
            print(f"   模型: {ai_config.get('model', 'N/A')}")

        # 数据源
        print(f"\n🕷️  数据源:")
        for source_id, source_config in settings.enabled_sources.items():
            print(f"   ✅ {source_config['name']}")

        stats = scraper.get_scraping_stats()
        print(f"\n📈 爬取统计:")
        print(f"   今日新增: {stats.get('today_count', 0)} 条")
        print(f"   总计入库: {stats.get('total_count', 0)} 条")
        print(f"   待提取详情: {stats.get('pending_detail_extraction', 0)} 条")
        print(f"   已处理详情: {stats.get('processed_detail_items', 0)} 条")
        if stats.get('oldest_pending_timestamp'):
            print(f"   最老待处理: {stats['oldest_pending_timestamp']}")
        retention_info = stats.get('retention', {})
        retention_cfg = retention_info.get('config', {}) or {}
        print(f"   保留策略: 最多 {retention_cfg.get('scraped_data_max_records', '∞')} 条, {retention_cfg.get('scraped_data_max_age_days', '∞')} 天")
        last_cleanup = retention_info.get('last_cleanup', {}) or {}
        if last_cleanup.get('expired') or last_cleanup.get('overflow'):
            print(f"   最近清理: 过期 {last_cleanup.get('expired', 0)} 条, 超限 {last_cleanup.get('overflow', 0)} 条")

        # 数据库状态
        db_path = "data/marketing.db"
        db_file = Path(db_path)
        if db_file.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # 检查contacts表
                try:
                    cursor.execute("SELECT COUNT(*) FROM contacts")
                    contact_count = cursor.fetchone()[0]
                except:
                    contact_count = 0

                # 检查去重表
                try:
                    cursor.execute("SELECT COUNT(*) FROM scraped_items_hash")
                    hash_count = cursor.fetchone()[0]
                except:
                    hash_count = 0

                conn.close()
                print(f"\n📊 数据库状态:")
                print(f"   联系人: {contact_count} 条")
                print(f"   去重记录: {hash_count} 条")
                print(f"   文件大小: {db_file.stat().st_size/1024:.1f} KB")
            except Exception as e:
                print(f"\n❌ 数据库读取失败: {e}")
        else:
            print(f"\n📊 数据库: 不存在")

    def cleanup_duplicates(self):
        """清理重复文件"""
        print("🧹 清理重复文件...")

        # 需要删除的重复文件列表
        duplicate_files = [
            "simple_start.py",
            "start_now.py",
            "quick_start.py",
            "procurement_scraper.py",
            "procurement_scraper_v2.py",
            "procurement_scraper_v3.py",
            "procurement_scraper_final.py",
            "procurement_scraper_robust.py",
            "procurement_scraper_simple.py",
            "multi_source_scraper.py",
            "scraper.py",
            "debug_contact_extraction.py",
            "test_demo.py",
            "test_environment.py"
        ]

        deleted_count = 0
        for file in duplicate_files:
            file_path = Path(file)
            if file_path.exists():
                try:
                    file_path.unlink()
                    print(f"   🗑️  删除: {file}")
                    deleted_count += 1
                except Exception as e:
                    print(f"   ❌ 无法删除 {file}: {e}")

        print(f"\n✅ 清理完成，删除了 {deleted_count} 个重复文件")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="智能设计营销系统")
    parser.add_argument("--scrape", action="store_true", help="运行数据爬虫")
    parser.add_argument("--extract", action="store_true", help="提取联系人信息")
    parser.add_argument("--email", action="store_true", help="发送邮件")
    parser.add_argument("--web", action="store_true", help="启动Web界面")
    parser.add_argument("--config", action="store_true", help="系统配置")
    parser.add_argument("--status", action="store_true", help="显示系统状态")
    parser.add_argument("--cleanup", action="store_true", help="清理重复文件")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    parser.add_argument("--queue", action="store_true", help="运行队列worker")

    args = parser.parse_args()

    system = MarketingSystem()

    queue_env = os.getenv("QUEUE_MODE", "0") == "1"
    interactive_mode = args.interactive or (len(sys.argv) == 1 and not queue_env and sys.stdin.isatty())

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
            print("7. 🧹 清理重复文件")
            print("8. 🚪 退出")

            choice = input("\n请选择 (1-8): ").strip()

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
                    system.cleanup_duplicates()
                elif choice == "8":
                    print("👋 再见！")
                    break
                else:
                    print("❌ 无效选择")
            except KeyboardInterrupt:
                print("\n👋 程序已退出")
                break
            except Exception as e:
                print(f"❌ 操作失败: {e}")

    else:
        # 命令行模式
        if args.scrape:
            system.run_scraper()
        elif args.extract:
            system.run_extractor()
        elif args.email:
            system.run_emailer()
        elif args.web:
            system.run_web()
        elif args.config:
            system.run_config()
        elif args.status:
            system.show_status()
        elif args.cleanup:
            system.cleanup_duplicates()
        elif args.queue or queue_env:
            print("🚚 启动队列 worker 服务...")
            try:
                asyncio.run(system._run_workers(persistent=True))
            except KeyboardInterrupt:
                print("\n👋 队列服务已停止")
        else:
            parser.print_help()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"❌ 程序运行失败: {e}")
        sys.exit(1)
